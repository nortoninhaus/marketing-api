"""
Google Analytics 4 connector.
"""

from typing import List, Dict, Any, Optional

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric, Dimension

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest
from app.models.responses import CampaignData
from app.config import settings

class GA4Connector(BaseConnector):
    platform_name = "ga4"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        creds = super().get_credentials(request)
        
        # Use account_id as the property_id for GA4
        property_id = request.account_id if request and request.account_id else creds.get("property_id")
        
        return {
            "property_id": property_id
        }

    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        creds = self.get_credentials(request)
        client = BetaAnalyticsDataClient()
        req = RunReportRequest(
            property=f"properties/{creds['property_id']}",
            date_ranges=[DateRange(
                start_date=request.start_date.strftime("%Y-%m-%d"),
                end_date=request.end_date.strftime("%Y-%m-%d")
            )],
            metrics=[Metric(name=m) for m in request.metrics],
            dimensions=[Dimension(name="date")]
        )
        response = client.run_report(req)
        results = []
        for row in response.rows:
            date_val = row.dimension_values[0].value
            metrics_dict = {request.metrics[i]: row.metric_values[i].value for i in range(len(request.metrics))}
            results.append(CampaignData(campaign_name="GA4_Report", date=date_val, metrics=metrics_dict))
        return results

    def get_schema(self) -> Dict[str, Any]:
        return {
            "metrics": ["activeUsers", "screenPageViews", "sessions", "totalRevenue"],
            "dimensions": ["date", "pagePath", "sourceMedium"]
        }

    def ping(self) -> bool:
        try:
            creds = self.get_credentials()
            client = BetaAnalyticsDataClient()
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
