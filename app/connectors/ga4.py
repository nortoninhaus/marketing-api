"""
Google Analytics 4 connector.
Supports dynamic credentials resolution via OAuth, parameterized report dimensions,
and graceful quota limit error handling.
"""

from typing import List, Dict, Any, Optional
import logging
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension
from google.oauth2.credentials import Credentials
from google.api_core.exceptions import ResourceExhausted
from fastapi import HTTPException

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData, ErrorDetail
from app.config import settings

logger = logging.getLogger(__name__)


class GA4Connector(BaseConnector):
    platform_name = "ga4"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        access_token = creds.get("access_token") if creds else None
        refresh_token = creds.get("refresh_token") if creds else None
        # Use account_id as the property_id for GA4
        property_id = request.account_id if request and request.account_id else (creds.get("property_id") if creds else None)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "property_id": property_id
        }

    def _build_client(self, creds: Dict[str, Any]) -> BetaAnalyticsDataClient:
        """Initializes client with OAuth credentials if present, else defaults to environment credentials."""
        if creds.get("access_token"):
            token_credentials = Credentials(
                token=creds["access_token"],
                refresh_token=creds.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret
            )
            return BetaAnalyticsDataClient(credentials=token_credentials)
        return BetaAnalyticsDataClient()

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        client = self._build_client(creds)
        
        # Build dimensions parameter (defaulting to date)
        dims = ["date"]
        if request.dimensions:
            for dim in request.dimensions:
                if dim != "date":
                    dims.append(dim)
                    
        req = RunReportRequest(
            property=f"properties/{creds['property_id']}",
            date_ranges=[DateRange(
                start_date=request.start_date.strftime("%Y-%m-%d"),
                end_date=request.end_date.strftime("%Y-%m-%d")
            )],
            metrics=[Metric(name=m) for m in request.metrics],
            dimensions=[Dimension(name=d) for d in dims]
        )
        
        try:
            response = client.run_report(req)
        except ResourceExhausted as re:
            logger.error(f"GA4 API Quota Exhausted: {re}")
            raise HTTPException(
                status_code=429,
                detail="Google Analytics 4 API quota exhausted. Please try again later."
            ) from re
            
        results = []
        for row in response.rows:
            # Reconstruct date and dimensions
            date_val = request.start_date.strftime("%Y-%m-%d")
            other_dims = []
            
            for idx, header in enumerate(response.dimension_headers):
                dim_name = header.name
                val = row.dimension_values[idx].value
                if dim_name == "date":
                    date_val = f"{val[:4]}-{val[4:6]}-{val[6:]}" if len(val) == 8 else val
                else:
                    other_dims.append(val)
                    
            campaign_name = " | ".join(other_dims) if other_dims else "GA4_Report"
            
            metrics_dict = {}
            for i, m in enumerate(request.metrics):
                try:
                    val = row.metric_values[i].value
                    metrics_dict[m] = float(val) if "." in str(val) else int(val)
                except Exception:
                    metrics_dict[m] = 0
                    
            results.append(CampaignData(
                campaign_name=campaign_name,
                date=date_val,
                metrics=metrics_dict
            ))
            
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": [
                "activeUsers",
                "screenPageViews",
                "sessions",
                "totalRevenue",
                "bounceRate",
                "engagedSessions",
                "engagementRate",
                "averageSessionDuration",
                "conversions",
                "eventCount"
            ],
            "dimensions": ["date", "pagePath", "sessionSourceMedium", "country", "deviceCategory"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            client = self._build_client(creds)
            req = RunReportRequest(
                property=f"properties/{creds['property_id']}",
                date_ranges=[DateRange(start_date="yesterday", end_date="today")],
                metrics=[Metric(name="activeUsers")],
                limit=1
            )
            client.run_report(req)
            return True
        except Exception:
            return False
