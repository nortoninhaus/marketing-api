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
        
        # 1. Determine pivot breakdown based on requested dimensions
        pivot = "CAMPAIGN"
        if request.dimensions:
            dim_lower = [d.lower() for d in request.dimensions]
            if "creative" in dim_lower:
                pivot = "CREATIVE"
            elif "campaign_group" in dim_lower:
                pivot = "CAMPAIGN_GROUP"
                
        # 2. Build REST versioned URL
        account_urn = ad_account_id if ad_account_id.startswith("urn:li:") else f"urn:li:sponsoredAdAccount:{ad_account_id}"
        
        url = (
            f"https://api.linkedin.com/rest/adAnalytics?q=analytics"
            f"&pivot={pivot}"
            f"&dateRange.start.day={request.start_date.day}&dateRange.start.month={request.start_date.month}&dateRange.start.year={request.start_date.year}"
            f"&dateRange.end.day={request.end_date.day}&dateRange.end.month={request.end_date.month}&dateRange.end.year={request.end_date.year}"
            f"&accounts=List({account_urn})"
        )
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202405",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("elements", []):
            campaign_name = item.get("campaign", item.get("creative", item.get("campaignGroup", "Unknown")))
            date_range = item.get("dateRange", {})
            day_start = date_range.get("start", {})
            
            if day_start and "year" in day_start and "month" in day_start and "day" in day_start:
                date_str = f"{day_start['year']}-{day_start['month']:02d}-{day_start['day']:02d}"
            else:
                date_str = start_str
                
            results.append(CampaignData(
                campaign_name=str(campaign_name),
                date=date_str,
                metrics={m: item.get(m, 0) for m in request.metrics}
            ))
            
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "costInLocalCurrency", "externalId"],
            "dimensions": ["campaign", "creative", "campaign_group", "dateRange"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            account_urn = creds["ad_account_id"]
            if not account_urn.startswith("urn:li:"):
                account_urn = f"urn:li:sponsoredAdAccount:{account_urn}"
            url = f"https://api.linkedin.com/rest/adAccountsV2/{account_urn.split(':')[-1]}"
            headers = {
                "Authorization": f"Bearer {creds['access_token']}",
                "LinkedIn-Version": "202405",
                "X-Restli-Protocol-Version": "2.0.0"
            }
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
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "LinkedIn-Version": "202405",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        if request.post_id:
            post_urn = request.post_id if request.post_id.startswith("urn:li:") else f"urn:li:share:{request.post_id}"
            url = f"https://api.linkedin.com/rest/posts/{post_urn}"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            return [CampaignData(
                campaign_name=f"Post_{request.post_id}",
                date=start_str,
                metrics={m: data.get(m, 0) for m in request.metrics}
            )]
        else:
            org_urn = org_id if org_id.startswith("urn:li:") else f"urn:li:organization:{org_id}"
            url = f"https://api.linkedin.com/rest/organizationalEntityShareStatistics?q=organizationalEntity&organizationalEntity={org_urn}&timeIntervals.timeGranularityType=DAY"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            elements = data.get("elements", [])
            results = []
            for item in elements:
                time_range = item.get("timeRange", {})
                day_start = time_range.get("start", {})
                if day_start and "year" in day_start and "month" in day_start and "day" in day_start:
                    date_str = f"{day_start['year']}-{day_start['month']:02d}-{day_start['day']:02d}"
                else:
                    date_str = start_str
                    
                # The stats are nested in totalShareStatistics
                stats = item.get("totalShareStatistics", {})
                results.append(CampaignData(
                    campaign_name="LinkedIn_Page",
                    date=date_str,
                    metrics={m: stats.get(m, 0) for m in request.metrics}
                ))
            if not results:
                # Return empty metrics fallback if no stats returned
                results.append(CampaignData(
                    campaign_name="LinkedIn_Page",
                    date=start_str,
                    metrics={m: 0 for m in request.metrics}
                ))
            return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["shareCount", "clickCount", "engagement", "impressionCount", "likeCount"],
            "dimensions": ["organization", "timeRange"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            org_urn = creds["organization_id"]
            if not org_urn.startswith("urn:li:"):
                org_urn = f"urn:li:organization:{org_urn}"
            url = f"https://api.linkedin.com/rest/organizations/{org_urn.split(':')[-1]}"
            headers = {
                "Authorization": f"Bearer {creds['access_token']}",
                "LinkedIn-Version": "202405",
                "X-Restli-Protocol-Version": "2.0.0"
            }
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
