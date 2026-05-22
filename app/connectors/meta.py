"""
Meta (Facebook/Instagram) connectors — Ads and Organic.
"""

from typing import List, Dict, Any, Optional

from facebook_business.session import FacebookSession
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
        session = FacebookSession(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=creds["access_token"]
        )
        api = FacebookAdsApi(session)
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
            session = FacebookSession(
                app_id=settings.meta_app_id,
                app_secret=settings.meta_app_secret,
                access_token=creds["access_token"]
            )
            api = FacebookAdsApi(session)
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
        session = FacebookSession(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=creds["access_token"]
        )
        api = FacebookAdsApi(session)
        page = Page(creds["page_id"], api=api)
        
        since_str = request.start_date.strftime("%Y-%m-%d")
        until_str = request.end_date.strftime("%Y-%m-%d")

        if request.post_id:
            post = page.get_posts(params={"ids": request.post_id})[0]
            insights = post.get_insights(params={
                "metric": ",".join(request.metrics),
                "since": since_str,
                "until": until_str
            })
            campaign_name = f"Post_{request.post_id}"
        else:
            insights = page.get_insights(params={
                "metric": ",".join(request.metrics),
                "since": since_str,
                "until": until_str
            })
            campaign_name = "Page_Insights"
        # Page Insights returns one object per metric, each with `name` and `values`
        # e.g. {"name": "page_impressions", "period": "day", "values": [{"value": 100, "end_time": "..."}]}
        # We aggregate all metrics into daily CampaignData rows
        daily_data: Dict[str, Dict[str, Any]] = {}
        
        for insight in insights:
            metric_name = insight.get("name", "unknown")
            values_list = insight.get("values", [])
            for val_entry in values_list:
                end_time = val_entry.get("end_time", since_str)
                day = end_time[:10] if end_time else since_str
                if day not in daily_data:
                    daily_data[day] = {}
                daily_data[day][metric_name] = val_entry.get("value", 0)
        
        if not daily_data:
            return []
        
        return [
            CampaignData(
                campaign_name=campaign_name,
                date=day,
                metrics=metrics_dict
            ) for day, metrics_dict in sorted(daily_data.items())
        ]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "page_media_view",
                "page_post_engagements",
                "page_views_total",
                "page_daily_follows",
                "post_media_view",
                "post_clicks"
            ],
            "dimensions": ["post_id", "date_start"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            session = FacebookSession(
                app_id=settings.meta_app_id,
                app_secret=settings.meta_app_secret,
                access_token=creds["access_token"]
            )
            api = FacebookAdsApi(session)
            page = Page(creds["page_id"], api=api)
            page.api_get(fields=["name"])
            return True
        except Exception:
            return False
