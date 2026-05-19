"""
Meta (Facebook/Instagram) connectors — Ads and Organic.
"""

from typing import List, Dict, Any, Optional

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.page import Page

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

class MetaAdsConnector(BaseConnector):
    platform_name = "meta_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        if not access_token:
            access_token = settings.meta_access_token
            
        ad_account_id = request.account_id if request else creds.get("ad_account_id")
            
        return {
            "access_token": access_token,
            "ad_account_id": ad_account_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        api = FacebookAdsApi(access_token=creds["access_token"])
        account = AdAccount(creds["ad_account_id"], api=api)
        
        insights = account.get_insights(
            fields=request.metrics,
            params={
                "time_range": {
                    "since": request.start_date.strftime("%Y-%m-%d"),
                    "until": request.end_date.strftime("%Y-%m-%d")
                },
                "level": "campaign"
            }
        )
        return [
            CampaignData(
                campaign_name=i.get("campaign_name", "Unknown"),
                date=i.get("date_start", request.start_date.strftime("%Y-%m-%d")),
                metrics={m: i.get(m) for m in request.metrics}
            ) for i in insights
        ]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "spend", "reach", "conversions"],
            "dimensions": ["campaign_name", "adset_name", "ad_name", "date_start"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            api = FacebookAdsApi(access_token=creds["access_token"])
            account = AdAccount(creds["ad_account_id"], api=api)
            account.get_insights(params={"limit": 1})
            return True
        except Exception:
            return False

class MetaOrganicConnector(BaseConnector):
    platform_name = "meta_organic"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        if not access_token:
            access_token = settings.meta_access_token
            
        page_id = request.account_id if request else creds.get("page_id")
            
        return {
            "access_token": access_token,
            "page_id": page_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        api = FacebookAdsApi(access_token=creds["access_token"])
        page = Page(creds["page_id"], api=api)
        
        since_str = request.start_date.strftime("%Y-%m-%d")
        until_str = request.end_date.strftime("%Y-%m-%d")

        if request.post_id:
            post = page.get_posts(params={"ids": request.post_id})[0]
            insights = post.get_insights(fields=request.metrics, params={"since": since_str, "until": until_str})
            campaign_name = f"Post_{request.post_id}"
        else:
            insights = page.get_insights(fields=request.metrics, params={"since": since_str, "until": until_str})
            campaign_name = "Page_Insights"
        
        return [
            CampaignData(
                campaign_name=campaign_name,
                date=since_str,
                metrics={m: i.get(m) for m in request.metrics}
            ) for i in insights
        ]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["page_impressions", "page_engagements", "page_post_engagements"],
            "dimensions": ["post_id", "date_start"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            api = FacebookAdsApi(access_token=creds["access_token"])
            page = Page(creds["page_id"], api=api)
            page.api_get(fields=["name"])
            return True
        except Exception:
            return False
