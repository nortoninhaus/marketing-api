"""
Google Ads connector.
Supports dynamic GAQL query construction based on requested dimensions,
search_stream for improved performance, and dynamic client/OAuth credentials.
"""

from typing import List, Dict, Any, Optional
import logging
from google.ads.googleads.client import GoogleAdsClient

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)


class GoogleAdsConnector(BaseConnector):
    platform_name = "google_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        developer_token = creds.get("developer_token") or settings.google_ads_developer_token
        client_id = creds.get("client_id") or settings.google_client_id or settings.google_ads_client_id
        client_secret = creds.get("client_secret") or settings.google_client_secret or settings.google_ads_client_secret
        refresh_token = creds.get("refresh_token") or settings.google_ads_refresh_token
        
        # Use account_id as the primary target for google ads queries
        customer_id = request.account_id if request and request.account_id else creds.get("customer_id")
        if customer_id:
            customer_id = str(customer_id).replace("-", "")
            
        login_customer_id = creds.get("login_customer_id")
        if login_customer_id:
            login_customer_id = str(login_customer_id).replace("-", "")
            
        # Omit login_customer_id if it is empty, not provided, or matches target customer_id
        if not login_customer_id or login_customer_id == customer_id:
            login_customer_id = None
        
        return {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "login_customer_id": login_customer_id,
            "customer_id": customer_id
        }

    def _build_client(self, creds: Dict[str, Any]) -> GoogleAdsClient:
        if creds.get("access_token"):
            from google.oauth2.credentials import Credentials
            token_credentials = Credentials(
                token=creds["access_token"],
                refresh_token=creds.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=creds["client_id"],
                client_secret=creds["client_secret"]
            )
            return GoogleAdsClient(
                credentials=token_credentials,
                developer_token=creds["developer_token"],
                login_customer_id=creds.get("login_customer_id"),
                use_proto_plus=True
            )
        client_dict = {
            "developer_token": creds["developer_token"],
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "use_proto_plus": True
        }
        if creds.get("login_customer_id"):
            client_dict["login_customer_id"] = creds["login_customer_id"]
        return GoogleAdsClient.load_from_dict(client_dict)

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        client = self._build_client(creds)
        ga_service = client.get_service("GoogleAdsService")
        start_str = request.start_date.strftime("%Y-%m-%d")
        end_str = request.end_date.strftime("%Y-%m-%d")

        # Determine target query table and select dimensions based on requested dimensions
        resource = "campaign"
        select_dims = ["campaign.name", "segments.date"]
        
        if request.dimensions:
            if any("ad_group.name" in d or "ad_group" in d for d in request.dimensions):
                resource = "ad_group"
                select_dims.append("ad_group.name")
            elif any("keyword" in d or "ad_group_criterion" in d for d in request.dimensions):
                resource = "keyword_view"
                select_dims.append("ad_group.name")
                select_dims.append("ad_group_criterion.keyword.text")

        # Build metrics select list
        metric_fields = [f"metrics.{m}" for m in request.metrics]
        query_fields = select_dims + metric_fields
        
        query = f"""
            SELECT {', '.join(query_fields)} 
            FROM {resource} 
            WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
        """
        
        # Use search_stream to fetch records in dynamic chunks
        response_stream = ga_service.search_stream(customer_id=creds["customer_id"], query=query)
        results = []
        
        for batch in response_stream:
            for row in batch.results:
                metrics_dict = {}
                for m in request.metrics:
                    try:
                        metrics_dict[m] = getattr(row.metrics, m, 0)
                    except Exception:
                        metrics_dict[m] = 0

                # Reconstruct descriptive campaign_name based on level
                name = row.campaign.name
                if resource == "ad_group" and hasattr(row, "ad_group") and hasattr(row.ad_group, "name"):
                    name = f"{name} | {row.ad_group.name}"
                elif resource == "keyword_view":
                    kw_part = ""
                    if hasattr(row, "ad_group_criterion") and hasattr(row.ad_group_criterion, "keyword") and hasattr(row.ad_group_criterion.keyword, "text"):
                        kw_part = f" | KW: {row.ad_group_criterion.keyword.text}"
                    ag_part = f" | {row.ad_group.name}" if hasattr(row, "ad_group") and hasattr(row.ad_group, "name") else ""
                    name = f"{name}{ag_part}{kw_part}"

                date_val = str(row.segments.date) if hasattr(row.segments, "date") else start_str
                
                results.append(CampaignData(
                    campaign_name=name,
                    date=date_val,
                    metrics=metrics_dict
                ))
                
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "impressions", 
                "clicks", 
                "cost_micros", 
                "conversions", 
                "all_conversions",
                "conversions_value",
                "all_conversions_value",
                "interactions",
                "engagements",
                "video_views",
                "active_view_impressions",
                "conversions_from_interactions_rate",
                "interaction_rate",
                "average_cpc",
                "average_cpm",
                "ctr",
                "bounce_rate",
                "active_view_measurability",
                "active_view_viewability",
                "video_quartile_25_rate",
                "video_quartile_50_rate",
                "video_quartile_75_rate",
                "video_quartile_100_rate",
                "cost_per_conversion",
                "cost_per_all_conversions",
                "all_conversions_from_interactions_rate",
                "value_per_conversion",
                "value_per_all_conversion",
                "active_view_cpm",
                "active_view_ctr"
            ],
            "dimensions": ["campaign.name", "segments.date", "ad_group.name", "ad_group_criterion.keyword.text"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            client = self._build_client(creds)
            ga_service = client.get_service("GoogleAdsService")
            query = "SELECT campaign.id FROM campaign LIMIT 1"
            ga_service.search(customer_id=creds["customer_id"], query=query)
            return True
        except Exception:
            return False
