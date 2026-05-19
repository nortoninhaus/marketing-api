"""
Apple connectors — App Store Connect and Search Ads.
"""

from typing import List, Dict, Any, Optional
import jwt
import time
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)

class AppleAppStoreConnector(BaseConnector):
    platform_name = "apple_app_store"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        issuer_id = creds.get("issuer_id", settings.apple_issuer_id)
        key_id = creds.get("key_id", settings.apple_key_id)
        private_key_path = creds.get("private_key_path", settings.apple_private_key_path)
        app_id = request.account_id if request and request.account_id else creds.get("app_id")
        
        return {
            "issuer_id": issuer_id,
            "key_id": key_id,
            "private_key_path": private_key_path,
            "app_id": app_id
        }

    def _generate_token(self, creds: Dict[str, Any]) -> str:
        with open(creds["private_key_path"], 'r') as f:
            private_key = f.read()
        return jwt.encode(
            {"iss": creds["issuer_id"], "iat": int(time.time()), "exp": int(time.time()) + 1200, "aud": "appstoreconnect-v1"},
            private_key, algorithm="ES256", headers={"kid": creds["key_id"]}
        )

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        token = self._generate_token(creds)
        headers = {"Authorization": f"Bearer {token}"}
        app_id = creds["app_id"]
        url = f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}/appStoreVersions"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return [CampaignData(
            campaign_name="Apple App Store",
            date=request.start_date.strftime("%Y-%m-%d"),
            metrics={"versions": len(data.get("data", []))}
        )]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["downloads", "impressions", "sessions", "crashes"],
            "dimensions": ["app_id", "country", "date"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            token = self._generate_token(creds)
            url = "https://api.appstoreconnect.apple.com/v1/apps"
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

class AppleAdsConnector(BaseConnector):
    platform_name = "apple_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token", settings.apple_ads_access_token)
        org_id = request.account_id if request and request.account_id else creds.get("org_id")
        
        return {
            "access_token": access_token,
            "org_id": org_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds["access_token"]
        org_id = creds["org_id"]
        url = "https://api.searchads.apple.com/api/v4/reports/campaigns"
        headers = {"Authorization": f"Bearer {access_token}", "X-AP-Context": org_id}
        params = {
            "startTime": request.start_date.strftime("%Y-%m-%d"),
            "endTime": request.end_date.strftime("%Y-%m-%d"),
            "granularity": "DAILY"
        }
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("data", []):
            results.append(CampaignData(
                campaign_name=item.get("campaignName", "Unknown"),
                date=request.start_date.strftime("%Y-%m-%d"),
                metrics=item.get("metrics", {})
            ))
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "taps", "installs", "spend", "avgCPA"],
            "dimensions": ["campaignId", "campaignName", "date"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = "https://api.searchads.apple.com/api/v4/campaigns"
            headers = {
                "Authorization": f"Bearer {creds['access_token']}",
                "X-AP-Context": creds["org_id"]
            }
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
