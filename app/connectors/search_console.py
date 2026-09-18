"""Search Console read-only reporting using the existing OAuth credential store."""
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.connectors.base import BaseConnector
from app.models.requests import DataRequest, SearchConsoleQueryRequest
from app.models.responses import CampaignData


def search_console_url(account_id: str) -> str:
    return f"https://www.googleapis.com/webmasters/v3/sites/{quote(account_id, safe='')}/searchAnalytics/query"


def report_response(response: httpx.Response) -> dict:
    if not response.is_success:
        status = response.status_code if response.status_code in {400, 401, 403, 404, 429} else 502
        raise HTTPException(status_code=status, detail=f"Search Console request failed (HTTP {response.status_code}). Check property access and reconnect if authorization expired.")
    try:
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("Invalid report")
        return data
    except ValueError:
        raise HTTPException(status_code=502, detail="Search Console returned an invalid response.") from None


class SearchConsoleConnector(BaseConnector):
    platform_name = "search_console"

    def get_schema(self):
        return {"metrics": ["clicks", "impressions", "ctr", "position"],
                "dimensions": ["date", "query", "country", "page", "device"]}

    def fetch_data(self, request: DataRequest):
        if set(request.metrics) - set(self.get_schema()["metrics"]):
            raise ValueError("Unsupported Search Console metric")
        if request.filters and set(request.filters) != {"query"}:
            raise ValueError("Search Console only supports an exact query filter")
        query = SearchConsoleQueryRequest(
            client_id=request.client_id, account_id=request.account_id,
            start_date=request.start_date, end_date=request.end_date,
            dimensions=request.dimensions or [], query=(request.filters or {}).get("query"),
            row_limit=request.limit if request.limit is not None else 1000,
            start_row=int(request.next_page_token or 0))
        token = self.get_credentials(request).get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Connect Search Console before querying this property.")
        try:
            response = httpx.post(search_console_url(query.account_id), json=query.upstream_body(),
                                  headers={"Authorization": f"Bearer {token}"}, timeout=30)
        except httpx.RequestError:
            raise HTTPException(status_code=502, detail="Search Console is temporarily unreachable.") from None
        report = report_response(response)
        results = []
        for row in report.get("rows", []):
            dimensions = dict(zip(query.dimensions, row.get("keys", [])))
            results.append(CampaignData(
                campaign_name=" | ".join(str(v) for k, v in dimensions.items() if k != "date") or "Search Console",
                date=dimensions.get("date", request.start_date.isoformat()), dimensions=dimensions,
                metrics={metric: row[metric] for metric in request.metrics}))
        return results
