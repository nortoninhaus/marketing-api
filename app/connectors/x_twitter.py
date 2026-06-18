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
        url = f"https://ads-api.twitter.com/12/stats/accounts/{account_id}/campaigns"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"start_time": start_str, "end_time": end_str, "entity": "CAMPAIGN", "granularity": "DAY"}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("data", []):
            results.append(CampaignData(
                campaign_name=item.get("id", "Unknown"),
                date=start_str,
                metrics={m: item.get(m, 0) for m in request.metrics}
            ))
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "spend", "engagements"],
            "dimensions": ["campaign_id", "date"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = f"https://ads-api.twitter.com/12/accounts/{creds['account_id']}"
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
        if request.post_id:
            url = f"https://api.twitter.com/2/tweets/{request.post_id}?tweet.fields=public_metrics,created_at"
        else:
            url = "https://api.twitter.com/2/users/me"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return [CampaignData(
            campaign_name=f"Tweet_{request.post_id}" if request.post_id else "X_Account",
            date=request.start_date.strftime("%Y-%m-%d"),
            metrics=data.get("data", {})
        )]

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
