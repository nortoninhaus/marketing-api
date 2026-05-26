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
        for data_level in ["AUCTION_CAMPAIGN", "RESERVATION_CAMPAIGN"]:
            params = {
                "advertiser_id": advertiser_id,
                "report_type": "BASIC",
                "data_level": data_level,
                "dimensions": '["campaign_id", "stat_time_day"]',
                "metrics": json.dumps(request.metrics),
                "start_date": request.start_date.strftime("%Y-%m-%d"),
                "end_date": request.end_date.strftime("%Y-%m-%d")
            }
            try:
                response = requests.get(url, params=params, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data.get("code") == 0 or "data" in data:
                    for item in data.get("data", {}).get("list", []):
                        results.append(CampaignData(
                            campaign_name=item.get("metrics", {}).get("campaign_name", item.get("dimensions", {}).get("campaign_id")),
                            date=item.get("dimensions", {}).get("stat_time_day"),
                            metrics=item.get("metrics", {})
                        ))
            except Exception as e:
                logger.warning(f"TikTok Ads query failed for level {data_level}: {e}")
                # If AUCTION fails but RESERVATION succeeds, or vice-versa, we keep going unless both fail
                if not results and data_level == "RESERVATION_CAMPAIGN":
                    raise
                    
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
                "play_video_3s",
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
            "open_id": open_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds["access_token"]
        
        # TikTok Display API or Video List API
        base_url = "https://open-sandbox.tiktokapis.com" if settings.use_tiktok_sandbox else "https://open.tiktokapis.com"
        url = f"{base_url}/v2/video/list/"
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers, timeout=30)
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
            "metrics": ["view_count", "like_count", "comment_count", "share_count"],
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
