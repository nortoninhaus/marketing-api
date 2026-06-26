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
        vendor_number = creds.get("vendor_number", getattr(settings, "apple_vendor_number", None))
        
        return {
            "issuer_id": issuer_id,
            "key_id": key_id,
            "private_key_path": private_key_path,
            "app_id": app_id,
            "vendor_number": vendor_number
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
        vendor_number = creds.get("vendor_number")
        
        # If vendor_number is available, attempt to query the sales reports
        if vendor_number:
            try:
                date_str = request.start_date.strftime("%Y-%m-%d")
                url = "https://api.appstoreconnect.apple.com/v1/salesReports"
                params = {
                    "filter[frequency]": "DAILY",
                    "filter[reportSubType]": "SUMMARY",
                    "filter[reportType]": "SALES",
                    "filter[vendorNumber]": vendor_number,
                    "filter[reportDate]": date_str
                }
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 200:
                    import gzip
                    import io
                    import csv
                    
                    content = gzip.decompress(response.content).decode("utf-8")
                    reader = csv.DictReader(io.StringIO(content), delimiter="\t")
                    
                    downloads = 0
                    for row in reader:
                        if row.get("Apple Identifier") == app_id or row.get("Title") == app_id:
                            units = int(row.get("Units", 0))
                            if row.get("Product Type Identifier") in ("1", "1F", "1T", "7"):
                                downloads += units
                                
                    metrics_dict = {"downloads": downloads}
                    metrics_dict = {m: metrics_dict.get(m, 0) for m in request.metrics}
                    return [CampaignData(
                        campaign_name="Apple App Store Sales",
                        date=date_str,
                        metrics=metrics_dict
                    )]
            except Exception as e:
                logger.error(f"Failed to fetch real App Store Sales Report: {e}. Falling back to version-check.")

        # Fallback implementation: list versions
        url = f"https://api.appstoreconnect.apple.com/v1/apps/{app_id}/appStoreVersions"
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Return a version-based metrics dictionary
        results_count = len(data.get("data", []))
        metrics_dict = {}
        for m in request.metrics:
            if m == "downloads":
                metrics_dict["downloads"] = results_count
            else:
                metrics_dict[m] = 0
                
        return [CampaignData(
            campaign_name="Apple App Store (Version Fallback)",
            date=request.start_date.strftime("%Y-%m-%d"),
            metrics=metrics_dict
        )]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["downloads"],
            "dimensions": ["app_id", "country", "date"],
            "metadata": {
                "unavailable_metrics_note": "impressions, sessions, and crashes require the App Store Connect Analytics Reports API which is not yet implemented."
            }
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
        
        url = "https://api.searchads.apple.com/api/v5/reports/campaigns"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-AP-Context": org_id,
            "Content-Type": "application/json"
        }
        
        # Build selector payload
        payload = {
            "startTime": request.start_date.strftime("%Y-%m-%d"),
            "endTime": request.end_date.strftime("%Y-%m-%d"),
            "granularity": "DAILY",
            "selector": {
                "fields": ["campaignId", "campaignName", "impressions", "taps", "installs", "spend", "avgCPA"],
                "orderBy": [{"field": "campaignId", "sortOrder": "ASCENDING"}]
            }
        }
        
        # Apple Search Ads API v5 reporting is POST
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        reporting_rows = data.get("data", {}).get("reportingDataResponse", [])
        
        for row_obj in reporting_rows:
            row = row_obj.get("row", {})
            campaign_name = row.get("campaignName", "Unknown")
            granularity_data = row.get("granularity", [])
            
            for day_data in granularity_data:
                date_str = day_data.get("date", request.start_date.strftime("%Y-%m-%d"))
                metrics_dict = {}
                
                impressions = float(day_data.get("impressions", 0))
                taps = float(day_data.get("taps", 0))
                spend = float(day_data.get("spend", 0))
                
                for m in request.metrics:
                    if m == "ctr":
                        metrics_dict["ctr"] = taps / impressions if impressions > 0 else 0.0
                    elif m == "cpc":
                        metrics_dict["cpc"] = spend / taps if taps > 0 else 0.0
                    elif m == "cpm":
                        metrics_dict["cpm"] = (spend / impressions) * 1000.0 if impressions > 0 else 0.0
                    elif m == "roas":
                        # Apple Search Ads does not provide conversion value data for ROAS calculation
                        metrics_dict["roas"] = None
                    else:
                        metrics_dict[m] = day_data.get(m, 0)
                
                results.append(CampaignData(
                    campaign_name=campaign_name,
                    date=date_str,
                    metrics=metrics_dict
                ))
                
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "taps", "installs", "spend", "avgCPA", "ctr", "cpc", "cpm", "roas"],
            "dimensions": ["campaignId", "campaignName", "date"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = "https://api.searchads.apple.com/api/v5/campaigns"
            headers = {
                "Authorization": f"Bearer {creds['access_token']}",
                "X-AP-Context": creds["org_id"]
            }
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
