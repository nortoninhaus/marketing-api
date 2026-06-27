"""
X (Twitter) connectors — Ads and Organic.
"""

from typing import List, Dict, Any, Optional
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)

class XAdsConnector(BaseConnector):
    platform_name = "x_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token", settings.x_ads_access_token)
        account_id = request.account_id if request and request.account_id else creds.get("account_id")
        
        return {
            "access_token": access_token,
            "account_id": account_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        account_id = creds["account_id"]
        access_token = creds["access_token"]
        start_str = request.start_date.strftime("%Y-%m-%d")
        end_str = request.end_date.strftime("%Y-%m-%d")
        
        # 1. Determine entity type based on requested dimensions
        entity = "CAMPAIGN"
        list_endpoint = "campaigns"
        if request.dimensions:
            dim_lower = [d.lower() for d in request.dimensions]
            if any("line_item" in d for d in dim_lower):
                entity = "LINE_ITEM"
                list_endpoint = "line_items"
            elif any(d in ("ad_id", "ad_name", "promoted_tweet") for d in dim_lower):
                entity = "PROMOTED_TWEET"
                list_endpoint = "promoted_tweets"
                
        # 2. Fetch active entity IDs
        list_url = f"https://ads-api.twitter.com/12/accounts/{account_id}/{list_endpoint}"
        headers = {"Authorization": f"Bearer {access_token}"}
        list_response = requests.get(list_url, headers=headers, timeout=30)
        self._record_rate_limit(list_response.headers)
        list_response.raise_for_status()
        list_data = list_response.json().get("data", [])
        
        entity_ids = [item["id"] for item in list_data if "id" in item]
        if not entity_ids:
            return []
            
        # Optional filtering from request filters
        if request.filters:
            for filter_key, filter_val in request.filters.items():
                if filter_key in ("campaign_ids", "line_item_ids", "promoted_tweet_ids", "entity_ids"):
                    target_ids = filter_val if isinstance(filter_val, list) else [filter_val]
                    entity_ids = [eid for eid in entity_ids if eid in target_ids]
                    
        if not entity_ids:
            return []
            
        # 3. Fetch Stats — batch entity IDs in groups of 10 to avoid URI too long
        stats_url = f"https://ads-api.twitter.com/12/stats/accounts/{account_id}"
        batch_size = 10
        
        # 4. Generate Date Sequence
        from datetime import timedelta
        dates_seq = []
        curr = request.start_date
        while curr <= request.end_date:
            dates_seq.append(curr.strftime("%Y-%m-%d"))
            curr += timedelta(days=1)
            
        results = []
        
        for batch_start in range(0, len(entity_ids), batch_size):
            batch_ids = entity_ids[batch_start:batch_start + batch_size]
            entity_ids_str = ",".join(batch_ids)
            
            params = {
                "entity": entity,
                "entity_ids": entity_ids_str,
                "start_time": start_str,
                "end_time": end_str,
                "granularity": "DAY",
                "metric_groups": "BILLING,ENGAGEMENT"
            }
            
            response = requests.get(stats_url, headers=headers, params=params, timeout=30)
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json()
            
            data_items = data.get("data", {})
            
            # Parse based on structure
            items_list = []
            if isinstance(data_items, dict):
                for v in data_items.values():
                    if isinstance(v, list):
                        items_list.extend(v)
                    elif isinstance(v, dict):
                        items_list.append(v)
            elif isinstance(data_items, list):
                items_list = data_items
                
            for item in items_list:
                entity_id = item.get("id", "Unknown")
                metrics_block = item.get("id_data", [{}])[0].get("metrics", {}) if item.get("id_data") else item.get("metrics", {})
                if not metrics_block:
                    continue
                    
                for idx, date_str in enumerate(dates_seq):
                    # Extract base metrics safely for calculation
                    def get_val_at_idx(key_name, divisor=1.0):
                        val_list = metrics_block.get(key_name, [])
                        if isinstance(val_list, list) and idx < len(val_list):
                            try:
                                return float(val_list[idx]) / divisor
                            except Exception:
                                return 0.0
                        elif isinstance(val_list, (int, float)):
                            return (float(val_list) if idx == 0 else 0.0) / divisor
                        return 0.0

                    clicks = get_val_at_idx("clicks")
                    impressions = get_val_at_idx("impressions")
                    spend = get_val_at_idx("billed_charge_local_micro", 1_000_000.0)

                    metrics_dict = {}
                    for m in request.metrics:
                        if m == "ctr":
                            metrics_dict["ctr"] = clicks / impressions if impressions > 0 else 0.0
                        elif m == "cpc":
                            metrics_dict["cpc"] = spend / clicks if clicks > 0 else 0.0
                        elif m == "cpm":
                            metrics_dict["cpm"] = (spend / impressions) * 1000.0 if impressions > 0 else 0.0
                        elif m == "roas":
                            # X Ads API does not provide conversion value data for ROAS calculation
                            metrics_dict["roas"] = None
                        else:
                            val_list = metrics_block.get(m, [])
                            if m == "spend" and "billed_charge_local_micro" in metrics_block:
                                val_list = metrics_block["billed_charge_local_micro"]
                                
                            val = 0
                            if isinstance(val_list, list) and idx < len(val_list):
                                val = val_list[idx]
                            elif isinstance(val_list, (int, float)):
                                val = val_list if idx == 0 else 0
                                
                            if m == "spend" and "billed_charge_local_micro" in metrics_block:
                                val = float(val) / 1_000_000.0
                                
                            metrics_dict[m] = val
                        
                    results.append(CampaignData(
                        campaign_name=entity_id,
                        date=date_str,
                        metrics=metrics_dict
                    ))
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "spend", "engagements", "ctr", "cpc", "cpm", "roas"],
            "dimensions": ["campaign_id", "line_item_id", "promoted_tweet_id", "date"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = f"https://ads-api.twitter.com/12/accounts/{creds['account_id']}/campaigns"
            headers = {"Authorization": f"Bearer {creds['access_token']}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

class XOrganicConnector(BaseConnector):
    platform_name = "x_organic"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        bearer_token = creds.get("bearer_token", settings.x_bearer_token)
        
        return {
            "bearer_token": bearer_token
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        bearer_token = creds["bearer_token"]
        headers = {"Authorization": f"Bearer {bearer_token}"}
        
        if request.post_id:
            url = f"https://api.twitter.com/2/tweets/{request.post_id}?tweet.fields=public_metrics,created_at"
            response = requests.get(url, headers=headers, timeout=30)
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json().get("data", {})
            metrics = data.get("public_metrics", {})
            return [CampaignData(
                campaign_name=f"Tweet_{request.post_id}",
                date=data.get("created_at", request.start_date.strftime("%Y-%m-%d"))[:10],
                metrics={m: metrics.get(m, 0) for m in request.metrics}
            )]
        else:
            me_url = "https://api.twitter.com/2/users/me"
            me_response = requests.get(me_url, headers=headers, timeout=30)
            self._record_rate_limit(me_response.headers)
            me_response.raise_for_status()
            user_data = me_response.json().get("data", {})
            user_id = user_data.get("id")
            
            if not user_id:
                return []
                
            tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
            params = {
                "tweet.fields": "public_metrics,created_at",
                "max_results": 20
            }
            tweets_response = requests.get(tweets_url, headers=headers, params=params, timeout=30)
            self._record_rate_limit(tweets_response.headers)
            tweets_response.raise_for_status()
            tweets_data = tweets_response.json().get("data", [])
            
            results = []
            for tweet in tweets_data:
                metrics = tweet.get("public_metrics", {})
                results.append(CampaignData(
                    campaign_name=f"Tweet_{tweet['id']}",
                    date=tweet.get("created_at", request.start_date.strftime("%Y-%m-%d"))[:10],
                    metrics={m: metrics.get(m, 0) for m in request.metrics}
                ))
            return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["retweet_count", "reply_count", "like_count", "quote_count", "impression_count"],
            "dimensions": ["tweet_id", "created_at"],
            "metadata": {
                "comment_support": True,
            },
        }

    def fetch_comments(self, tweet_id: str, bearer_token: str) -> list:
        """Fetch replies to a tweet using X API v2 search endpoint."""
        from app.models.responses import CommentData

        comments: list = []
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        params = {
            "query": f"conversation_id:{tweet_id}",
            "tweet.fields": "author_id,created_at,public_metrics,in_reply_to_user_id",
            "expansions": "author_id",
            "user.fields": "username,name",
            "max_results": 100,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json()

            # Build author lookup
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

            for tweet in data.get("data", []):
                author_id = tweet.get("author_id", "")
                author_info = users.get(author_id, {})
                public_metrics = tweet.get("public_metrics", {})

                comments.append(CommentData(
                    comment_id=tweet.get("id", ""),
                    text=tweet.get("text", ""),
                    author=author_info.get("username", author_id),
                    timestamp=tweet.get("created_at", ""),
                    like_count=public_metrics.get("like_count", 0),
                    reply_count=public_metrics.get("reply_count", 0),
                ))

        except Exception as e:
            logger.error(f"X/Twitter comments fetch error for tweet {tweet_id}: {e}")

        return comments

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = "https://api.twitter.com/2/users/me"
            headers = {"Authorization": f"Bearer {creds['bearer_token']}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
