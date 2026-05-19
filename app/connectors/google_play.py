"""
Google Play connector.
"""

from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

class GooglePlayConnector(BaseConnector):
    platform_name = "google_play"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        service_account_json = creds.get("service_account_json", settings.google_play_service_account_json)
        package_name = request.account_id if request and request.account_id else creds.get("package_name")
        
        return {
            "service_account_json": service_account_json,
            "package_name": package_name
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        credentials = service_account.Credentials.from_service_account_file(creds["service_account_json"])
        service = build("androidpublisher", "v3", credentials=credentials)
        package_name = creds["package_name"]
        reviews = service.reviews().list(packageName=package_name).execute()
        return [CampaignData(
            campaign_name="Google Play",
            date=request.start_date.strftime("%Y-%m-%d"),
            metrics={"reviews_count": len(reviews.get("reviews", []))}
        )]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["reviews_count", "rating", "installs", "uninstalls"],
            "dimensions": ["package_name", "date", "country"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            credentials = service_account.Credentials.from_service_account_file(creds["service_account_json"])
            service = build("androidpublisher", "v3", credentials=credentials)
            service.reviews().list(packageName=creds["package_name"], maxResults=1).execute()
            return True
        except Exception:
            return False
