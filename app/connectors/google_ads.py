"""
Google Ads connector.
"""

from typing import List, Dict, Any, Optional
from google.ads.googleads.client import GoogleAdsClient

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

class GoogleAdsConnector(BaseConnector):
    platform_name = "google_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        developer_token = creds.get("developer_token", settings.google_ads_developer_token)
        client_id = creds.get("client_id", settings.google_ads_client_id)
        client_secret = creds.get("client_secret", settings.google_ads_client_secret)
        refresh_token = creds.get("refresh_token", settings.google_ads_refresh_token)
        
        # Use account_id as the primary target for google ads queries
        customer_id = request.account_id if request and request.account_id else creds.get("customer_id")
        login_customer_id = creds.get("login_customer_id")
        
        return {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "login_customer_id": login_customer_id,
            "customer_id": customer_id
        }

    def _build_client(self, creds: Dict[str, Any]) -> GoogleAdsClient:
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
        query = f"""
            SELECT campaign.name, segments.date, {', '.join([f'metrics.{m}' for m in request.metrics])} 
            FROM campaign WHERE segments.date BETWEEN '{start_str}' AND '{end_str}'
        """
        response = ga_service.search(customer_id=creds["customer_id"], query=query)
        results = []
        for row in response:
            metrics_dict = {m: getattr(row.metrics, m, 0) for m in request.metrics}
            results.append(CampaignData(
                campaign_name=row.campaign.name,
                date=str(row.segments.date),
                metrics=metrics_dict
            ))
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "cost_micros", "conversions", "all_conversions"],
            "dimensions": ["campaign.name", "segments.date", "ad_group.name"]
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
