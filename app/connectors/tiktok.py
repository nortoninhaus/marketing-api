"""
TikTok connectors (Ads and Organic).
"""

from typing import List, Dict, Any, Optional
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)

class TikTokAdsConnector(BaseConnector):
    platform_name = "tiktok_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token", settings.tiktok_ads_access_token)
        advertiser_id = request.account_id if request and request.account_id else creds.get("advertiser_id")
        
        return {
            "access_token": access_token,
            "advertiser_id": advertiser_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        advertiser_id = creds["advertiser_id"]
        access_token = creds["access_token"]
        
        url = "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/"
        headers = {"Access-Token": access_token}
        results = []
        
        # Query both AUCTION_CAMPAIGN and RESERVATION_CAMPAIGN to cover all campaign types
        import json
        success_count = 0
        errors = []
        
        for data_level in ["AUCTION_CAMPAIGN", "RESERVATION_CAMPAIGN"]:
            page = 1
            page_size = 1000
            while True:
                params = {
                    "advertiser_id": advertiser_id,
                    "report_type": "BASIC",
                    "data_level": data_level,
                    "dimensions": '["campaign_id", "stat_time_day"]',
                    "metrics": json.dumps(request.metrics),
                    "start_date": request.start_date.strftime("%Y-%m-%d"),
                    "end_date": request.end_date.strftime("%Y-%m-%d"),
                    "page": page,
                    "page_size": page_size
                }
                try:
                    response = requests.get(url, params=params, headers=headers, timeout=30)
                    self._record_rate_limit(response.headers)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data.get("code", 0) != 0:
                        msg = data.get("message", "Unknown error")
                        code = data.get("code")
                        # Check if this is just an unsupported data level error
                        if code == 40002 and "Unsupported data_level" in msg:
                            logger.info(f"TikTok Ads data level {data_level} not supported for advertiser {advertiser_id}.")
                            break
                        
                        logger.warning(f"TikTok Ads API error for level {data_level}: code={code}, message={msg}")
                        errors.append(f"{data_level} API error: {msg} (code {code})")
                        break
                    else:
                        success_count += 1
                        page_items = data.get("data", {}).get("list", [])
                        for item in page_items:
                            results.append(CampaignData(
                                campaign_name=item.get("metrics", {}).get("campaign_name", item.get("dimensions", {}).get("campaign_id")),
                                date=item.get("dimensions", {}).get("stat_time_day"),
                                metrics=item.get("metrics", {})
                            ))
                        # Check if there are more pages
                        page_info = data.get("data", {}).get("page_info", {})
                        total_page = page_info.get("total_page", 1)
                        if page >= total_page or not page_items:
                            break
                        page += 1
                except Exception as e:
                    logger.warning(f"TikTok Ads query failed for level {data_level}: {e}")
                    errors.append(f"{data_level} query failed: {e}")
                    break
                
        if success_count == 0 and errors:
            raise ValueError(f"TikTok Ads query failed: {'; '.join(errors)}")
            
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "spend", 
                "impressions", 
                "clicks", 
                "reach",
                "conversion", 
                "cost_per_conversion",
                "conversion_rate",
                "ctr",
                "cpc",
                "cpm",
                "frequency",
                "video_play_actions",
                "video_watched_2s",
                "video_watched_6s",
                "video_views_p25",
                "video_views_p50",
                "video_views_p75",
                "video_views_p100"
            ],
            "dimensions": ["campaign_id", "stat_time_day", "adgroup_id", "ad_id"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
            params = {"advertiser_ids": f'["{creds["advertiser_id"]}"]'}
            headers = {"Access-Token": creds["access_token"]}
            response = requests.get(url, params=params, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

class TikTokOrganicConnector(BaseConnector):
    platform_name = "tiktok_organic"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token", settings.tiktok_access_token)
        open_id = request.account_id if request and request.account_id else creds.get("open_id")
        
        return {
            "access_token": access_token,
            "open_id": open_id,
            "account_name": creds.get("account_name", "TikTok Profile")
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds["access_token"]
        open_id = creds.get("open_id") or request.account_id
        
        # Check if this is a Business Center asset connection
        is_bc_asset = creds.get("is_bc_asset") == True
        
        # Determine if they are asking for profile-level metrics
        profile_metrics = {"follower_count", "profile_views"}
        requested_metrics = set(request.metrics)
        wants_profile_only = bool(requested_metrics & profile_metrics) and not request.video_id
        
        if wants_profile_only:
            if is_bc_asset:
                # Fetch real profile data from the Business API
                bc_profile_url = "https://business-api.tiktok.com/open_api/v1.3/business/get/"
                bc_headers = {"Access-Token": access_token}
                bc_params = {"business_id": open_id}
                profile_metrics = {}
                try:
                    bc_response = requests.get(bc_profile_url, params=bc_params, headers=bc_headers, timeout=30)
                    self._record_rate_limit(bc_response.headers)
                    bc_response.raise_for_status()
                    bc_data = bc_response.json()
                    if bc_data.get("code", 0) == 0:
                        bc_info = bc_data.get("data", {})
                        profile_metrics["follower_count"] = bc_info.get("follower_count")
                        profile_metrics["profile_views"] = bc_info.get("profile_views")
                    else:
                        logger.warning(f"TikTok Business profile API returned code {bc_data.get('code')}: {bc_data.get('message')}")
                        profile_metrics["follower_count"] = None
                        profile_metrics["profile_views"] = None
                except Exception as e:
                    logger.warning(f"Failed to fetch TikTok Business profile metrics: {e}")
                    profile_metrics["follower_count"] = None
                    profile_metrics["profile_views"] = None
                return [CampaignData(
                    campaign_name=creds.get("account_name", "TikTok Brand Account"),
                    date=request.start_date.strftime("%Y-%m-%d"),
                    metrics=profile_metrics
                )]
            else:
                base_url = "https://open-sandbox.tiktokapis.com" if settings.use_tiktok_sandbox else "https://open.tiktokapis.com"
                url = f"{base_url}/v2/user/info/"
                headers = {"Authorization": f"Bearer {access_token}"}
                response = requests.get(url, headers=headers, params={"fields": "follower_count,display_name"}, timeout=30)
                self._record_rate_limit(response.headers)
                response.raise_for_status()
                user_data = response.json().get("data", {}).get("user", {})
                return [CampaignData(
                    campaign_name=user_data.get("display_name") or "TikTok User",
                    date=request.start_date.strftime("%Y-%m-%d"),
                    metrics={
                        "follower_count": user_data.get("follower_count", 0),
                        "profile_views": 0
                    }
                )]
        
        if is_bc_asset:
            url = "https://business-api.tiktok.com/open_api/v1.3/business/video/list/"
            headers = {"Access-Token": access_token}
            
            metric_to_field = {
                "view_count": "video_views",
                "like_count": "likes",
                "comment_count": "comments",
                "share_count": "shares"
            }
            requested_fields = ["item_id", "title", "create_time"]
            for m in request.metrics:
                if m in metric_to_field:
                    requested_fields.append(metric_to_field[m])
                    
            import json
            from datetime import datetime
            params = {
                "business_id": open_id,
                "fields": json.dumps(requested_fields)
            }
            response = requests.get(url, params=params, headers=headers, timeout=30)
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code", 0) != 0:
                logger.warning(f"TikTok Business Organic API error: code={data.get('code')}, message={data.get('message')}")
                raise ValueError(f"TikTok Organic API error: {data.get('message')} (code {data.get('code')})")
                
            videos = data.get("data", {}).get("list", [])
            return [CampaignData(
                campaign_name=v.get("title", f"Video_{v.get('item_id')}")[:50],
                date=datetime.fromtimestamp(v.get("create_time", 0)).strftime("%Y-%m-%d") if v.get("create_time") else request.start_date.strftime("%Y-%m-%d"),
                metrics={
                    "view_count": v.get("video_views", 0),
                    "like_count": v.get("likes", 0),
                    "comment_count": v.get("comments", 0),
                    "share_count": v.get("shares", 0)
                }
            ) for v in videos]
        else:
            base_url = "https://open-sandbox.tiktokapis.com" if settings.use_tiktok_sandbox else "https://open.tiktokapis.com"
            url = f"{base_url}/v2/video/list/"
            headers = {"Authorization": f"Bearer {access_token}"}
            
            metric_to_field = {
                "view_count": "view_count",
                "like_count": "like_count",
                "comment_count": "comment_count",
                "share_count": "share_count"
            }
            requested_fields = ["id", "title", "create_time"]
            for m in request.metrics:
                if m in metric_to_field:
                    requested_fields.append(metric_to_field[m])
            
            params = {"fields": ",".join(requested_fields)}
            response = requests.get(url, headers=headers, params=params, timeout=30)
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json()
            
            videos = data.get("data", {}).get("videos", [])
            return [CampaignData(
                campaign_name=v.get("title", f"Video_{v.get('id')}")[:50],
                date=request.start_date.strftime("%Y-%m-%d"),
                metrics={
                    "view_count": v.get("view_count", 0),
                    "like_count": v.get("like_count", 0),
                    "comment_count": v.get("comment_count", 0),
                    "share_count": v.get("share_count", 0)
                }
            ) for v in videos]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["view_count", "like_count", "comment_count", "share_count", "follower_count", "profile_views"],
            "dimensions": ["video_id", "create_time"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            base_url = "https://open-sandbox.tiktokapis.com" if settings.use_tiktok_sandbox else "https://open.tiktokapis.com"
            url = f"{base_url}/v2/user/info/"
            headers = {"Authorization": f"Bearer {creds['access_token']}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
