"""
Spotify Ads connector.
Supports aggregate campaign performance reporting via the Spotify Partner Ads API.
"""

from typing import List, Dict, Any, Optional
import requests
import logging

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

logger = logging.getLogger(__name__)


class SpotifyAdsConnector(BaseConnector):
    platform_name = "spotify_ads"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        ad_account_id = request.account_id if request and request.account_id else (creds.get("ad_account_id") if creds else None)
        client_id = creds.get("client_id", getattr(settings, "spotify_client_id", None)) if creds else getattr(settings, "spotify_client_id", None)
        client_secret = creds.get("client_secret", getattr(settings, "spotify_client_secret", None)) if creds else getattr(settings, "spotify_client_secret", None)
        
        return {
            "access_token": access_token,
            "ad_account_id": ad_account_id,
            "client_id": client_id,
            "client_secret": client_secret
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        access_token = creds.get("access_token")
        ad_account_id = creds.get("ad_account_id")
        
        if not access_token:
            raise ValueError("Spotify Ads access token is required.")
        if not ad_account_id:
            raise ValueError("Spotify Ads ad_account_id is required.")

        start_str = request.start_date.strftime("%Y-%m-%d")
        end_str = request.end_date.strftime("%Y-%m-%d")
        
        # Native Spotify Ads API aggregate reports endpoint
        url = f"https://api-partner.spotify.com/ads/v3/ad_accounts/{ad_account_id}/reports/aggregate"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Map requested metrics to Spotify uppercase metrics
        spotify_metrics = []
        for m in request.metrics:
            if m == "impressions":
                spotify_metrics.append("IMPRESSIONS")
            elif m == "clicks":
                spotify_metrics.append("CLICKS")
            elif m == "spend":
                spotify_metrics.append("SPEND")
            elif m == "reach":
                spotify_metrics.append("REACH")
            elif m == "frequency":
                spotify_metrics.append("FREQUENCY")
                
        if not spotify_metrics:
            spotify_metrics = ["IMPRESSIONS"]
            
        params = {
            "start_date": start_str,
            "end_date": end_str,
            "metrics": ",".join(spotify_metrics)
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        # Track rate limits if headers are returned
        self._record_rate_limit(response.headers)
        
        response.raise_for_status()
        data = response.json()
        
        results = []
        campaigns_data = data.get("data", [])
        for item in campaigns_data:
            campaign_name = item.get("campaign_name", "Spotify_Campaign")
            date_val = item.get("date", start_str)
            metrics_raw = item.get("metrics", {})
            
            metrics_dict = {}
            for m in request.metrics:
                native_key = m.upper()
                metrics_dict[m] = metrics_raw.get(native_key, 0)
                
            results.append(CampaignData(
                campaign_name=campaign_name,
                date=date_val,
                metrics=metrics_dict
            ))
            
        if not results and campaigns_data:
            # Reconstruct fallback if no matching rows parsed but structures present
            results.append(CampaignData(
                campaign_name="Spotify_Campaign",
                date=start_str,
                metrics={m: 0 for m in request.metrics}
            ))
            
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["impressions", "clicks", "spend", "frequency", "reach"],
            "dimensions": ["campaign_id", "campaign_name", "date"],
            "metadata": {
                "api_version": "v3"
            }
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            url = f"https://api-partner.spotify.com/ads/v3/ad_accounts/{creds['ad_account_id']}"
            headers = {"Authorization": f"Bearer {creds['access_token']}"}
            response = requests.get(url, headers=headers, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
