"""
LinkedIn connectors — Ads and Organic.
"""

from typing import List, Dict, Any, Optional
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)

class LinkedInAdsConnector(BaseConnector):
    platform_name = "linkedin_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token", settings.linkedin_access_token)
        ad_account_id = request.account_id if request and request.account_id else creds.get("ad_account_id")
        
        return {
            "access_token": access_token,
            "ad_account_id": ad_account_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        ad_account_id = creds["ad_account_id"]
        access_token = creds["access_token"]
        
        start_str = request.start_date.strftime("%Y-%m-%d")
        end_str = request.end_date.strftime("%Y-%m-%d")
        
        url = f"https://api.linkedin.com/v2/adAnalytics?q=analytics&dateRange.start.day={start_str}&dateRange.end.day={end_str}&campaign={ad_account_id}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("elements", []):
            results.append(CampaignData(
                campaign_name=item.get("campaign", "Unknown"),
                date=start_str,
                metrics={m: item.get(m, 0) for m in request.metrics}
            ))
            
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "costInLocalCurrency", "externalId"],
            "dimensions": ["campaign", "dateRange"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = f"https://api.linkedin.com/v2/adAccountsV2/{creds['ad_account_id']}"
            headers = {"Authorization": f"Bearer {creds['access_token']}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False

class LinkedInOrganicConnector(BaseConnector):
    platform_name = "linkedin_organic"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token", settings.linkedin_access_token)
        organization_id = request.account_id if request and request.account_id else creds.get("organization_id")
        
        return {
            "access_token": access_token,
            "organization_id": organization_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        org_id = creds["organization_id"]
        access_token = creds["access_token"]
        
        start_str = request.start_date.strftime("%Y-%m-%d")
        
        if request.post_id:
            url = f"https://api.linkedin.com/v2/shares/{request.post_id}"
        else:
            url = f"https://api.linkedin.com/v2/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity=urn:li:organization:{org_id}&timeIntervals.timeGranularityType=DAY"
            
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        elements = data.get("elements", [{}])
        metrics_dict = elements[0] if elements else {}
        
        return [CampaignData(
            campaign_name=f"Post_{request.post_id}" if request.post_id else "LinkedIn_Page",
            date=start_str,
            metrics=metrics_dict
        )]

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["shareCount", "clickCount", "engagement", "impressionCount", "likeCount"],
            "dimensions": ["organization", "timeRange"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = f"https://api.linkedin.com/v2/organizations/{creds['organization_id']}"
            headers = {"Authorization": f"Bearer {creds['access_token']}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
