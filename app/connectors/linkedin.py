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
        
        # Paginate through results using start/count
        results = []
        start = 0
        count = 500
        
        while True:
            paginated_url = f"{url}&start={start}&count={count}"
            response = requests.get(paginated_url, headers=headers, timeout=30)
            self._record_rate_limit(response.headers)
            response.raise_for_status()
            data = response.json()
            
            elements = data.get("elements", [])
            for item in elements:
                campaign_name = item.get("campaign", item.get("creative", item.get("campaignGroup", "Unknown")))
                date_range = item.get("dateRange", {})
                day_start = date_range.get("start", {})
                
                if day_start and "year" in day_start and "month" in day_start and "day" in day_start:
                    date_str = f"{day_start['year']}-{day_start['month']:02d}-{day_start['day']:02d}"
                else:
                    date_str = start_str
                    
                metrics_dict = {}
                clicks = float(item.get("clicks", 0))
                impressions = float(item.get("impressions", 0))
                cost = float(item.get("costInLocalCurrency", 0))
                
                for m in request.metrics:
                    if m == "ctr":
                        metrics_dict["ctr"] = clicks / impressions if impressions > 0 else 0.0
                    elif m == "cpc":
                        metrics_dict["cpc"] = cost / clicks if clicks > 0 else 0.0
                    elif m == "cpm":
                        metrics_dict["cpm"] = (cost / impressions) * 1000.0 if impressions > 0 else 0.0
                    elif m == "roas":
                        # Calculate ROAS = conversion_value / cost if conversion value data is available
                        conversion_value = item.get("conversionValueInLocalCurrency")
                        if conversion_value is not None and cost > 0:
                            metrics_dict["roas"] = float(conversion_value) / cost
                        else:
                            metrics_dict["roas"] = None
                    elif m == "conversions":
                        # Map to externalWebsiteConversions + oneClickLeads (not externalId)
                        ext_conversions = float(item.get("externalWebsiteConversions", 0))
                        one_click_leads = float(item.get("oneClickLeads", 0))
                        metrics_dict["conversions"] = ext_conversions + one_click_leads
                    else:
                        metrics_dict[m] = item.get(m, 0)
                        
                results.append(CampaignData(
                    campaign_name=str(campaign_name),
                    date=date_str,
                    metrics=metrics_dict
                ))
            
            # Check if there are more pages
            paging = data.get("paging", {})
            total = paging.get("total", len(elements))
            start += count
            if start >= total or not elements:
                break
            
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "costInLocalCurrency", "externalWebsiteConversions", "oneClickLeads", "ctr", "cpc", "cpm", "roas", "conversions"],
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
            self._record_rate_limit(response.headers)
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
            self._record_rate_limit(response.headers)
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
