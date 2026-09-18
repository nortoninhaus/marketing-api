"""
Request models with strict validation.

Platform is an enum (not a free-text string), dates are validated,
and the model rejects invalid combinations at the Pydantic layer
rather than letting them reach external APIs.
"""

from datetime import date
from enum import Enum
from typing import List, Optional, Dict, Any, Literal

from pydantic import BaseModel, Field, model_validator


class Platform(str, Enum):
    """Supported marketing platforms — typed and discoverable."""

    META_ADS = "meta_ads"
    META_ORGANIC = "meta_organic"
    GOOGLE_ADS = "google_ads"
    GA4 = "ga4"
    SEARCH_CONSOLE = "search_console"
    TIKTOK_ADS = "tiktok_ads"
    TIKTOK_ORGANIC = "tiktok_organic"
    LINKEDIN_ADS = "linkedin_ads"
    LINKEDIN_ORGANIC = "linkedin_organic"
    X_ADS = "x_ads"
    X_ORGANIC = "x_organic"
    YOUTUBE = "youtube"
    GOOGLE_PLAY = "google_play"
    APPLE_APP_STORE = "apple_app_store"
    APPLE_ADS = "apple_ads"
    THREADS = "threads"
    SPOTIFY_ADS = "spotify_ads"
    PINTEREST_ADS = "pinterest_ads"
    PINTEREST_ORGANIC = "pinterest_organic"
    SHOPIFY = "shopify"
    GHL = "ghl"


    @classmethod
    def ads_platforms(cls) -> list["Platform"]:
        return [cls.META_ADS, cls.GOOGLE_ADS, cls.TIKTOK_ADS, cls.LINKEDIN_ADS, cls.X_ADS, cls.APPLE_ADS, cls.SPOTIFY_ADS, cls.PINTEREST_ADS]

    @classmethod
    def organic_platforms(cls) -> list["Platform"]:
        return [cls.META_ORGANIC, cls.TIKTOK_ORGANIC, cls.LINKEDIN_ORGANIC, cls.X_ORGANIC, cls.YOUTUBE, cls.THREADS, cls.PINTEREST_ORGANIC]

    @classmethod
    def app_store_platforms(cls) -> list["Platform"]:
        return [cls.GOOGLE_PLAY, cls.APPLE_APP_STORE]



class DataRequest(BaseModel):
    """Unified request for any marketing platform."""

    platform: Platform = Field(..., description="Target marketing platform (enum value)")
    start_date: date = Field(..., description="Start date for data range (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date for data range (YYYY-MM-DD)")
    metrics: List[str] = Field(..., min_length=1, description="List of metrics to retrieve")
    
    # --- Multi-tenancy fields ---
    client_id: str = Field(..., description="ID of the client/agency")
    user_id: str = Field(..., description="ID of the user making the request")
    account_id: str = Field(..., description="Ad account ID, page ID, or property ID for the platform")
    
    # Optional dynamic credentials for the request (e.g., per-user OAuth tokens)
    # If not provided, the API will attempt to fetch from storage (Firestore) or fallback to global settings
    credentials: Optional[Dict[str, Any]] = Field(None, description="Dynamic credentials for the platform")

    post_id: Optional[str] = Field(None, description="Specific post/content ID (organic platforms)")
    video_id: Optional[str] = Field(None, description="Specific video ID (TikTok/YouTube)")
    app_id: Optional[str] = Field(None, description="App package name or ID (app store platforms)")
    dimensions: Optional[List[str]] = Field(None, description="List of dimensions to group by")
    dry_run: bool = Field(False, description="If true, only validate parameters/metrics without fetching upstream data")
    write_to_bq: bool = Field(False, description="If true, write results to BigQuery")
    limit: Optional[int] = Field(None, description="Maximum number of items to return")
    next_page_token: Optional[str] = Field(None, description="Cursor for the next page of results")
    filters: Optional[Dict[str, Any]] = Field(None, description="Dynamic key-value filters or expressions")
    action_attribution_windows: Optional[List[str]] = Field(None, description="Attribution windows for Meta Ads (e.g. ['7d_click', '1d_view'])")
    write_to_bq: bool = Field(False, description="Whether to also sync this fetch to BigQuery")

    @model_validator(mode="after")
    def validate_date_range(self) -> "DataRequest":
        if self.start_date > self.end_date:
            raise ValueError(f"start_date ({self.start_date}) must be on or before end_date ({self.end_date})")
        return self

    @model_validator(mode="after")
    def validate_platform_parameters(self) -> "DataRequest":
        from app.metrics import validate_platform_params
        errors = validate_platform_params(
            self.platform.value,
            self.account_id,
            self.post_id,
            self.video_id,
            self.app_id
        )
        if errors:
            raise ValueError(" | ".join(errors))
        return self


class BatchDataRequest(BaseModel):
    """Multi-platform batch request — agents send one call, get all platforms."""

    requests: List[DataRequest] = Field(..., min_length=1, max_length=16, description="List of platform requests")


class CommentsRequest(BaseModel):
    """Request payload for fetching comments."""
    platform: Platform = Field(..., description="Target platform (meta_ads, meta_organic, threads)")
    post_id: str = Field(..., description="Native post/media ID to fetch comments for")
    client_id: str = Field("client_1", description="ID of the client/agency")
    user_id: str = Field("user_1", description="ID of the user making the request")
    account_id: str = Field("", description="Platform-specific account identifier (optional)")
    limit: Optional[int] = Field(None, description="Maximum number of items to return")
    next_page_token: Optional[str] = Field(None, description="Cursor for the next page of results")


class ValidationRequest(BaseModel):
    """Payload to validate parameters and metrics without fetching data."""
    platform: Platform = Field(..., description="Platform to validate against")
    metrics: List[str] = Field(..., description="List of metrics to validate")
    use_generic_names: bool = Field(False, description="If true, metrics are validated as generic names")
    client_id: Optional[str] = Field(None, description="ID of the client for semantic credential checks")
    account_id: str = Field("", description="Platform account ID to validate format")
    post_id: Optional[str] = Field(None, description="Specific post/content ID")
    video_id: Optional[str] = Field(None, description="Specific video ID")
    app_id: Optional[str] = Field(None, description="App store ID or package name")


class TikTokProxyRequest(BaseModel):
    """Generic proxy request model for executing any TikTok Marketing API endpoint."""
    client_id: str = Field(..., description="ID of the client/agency")
    account_id: str = Field(..., description="Advertiser ID (account_id)")
    path: str = Field(..., description="The TikTok API path (e.g. campaign/get/)")
    method: str = Field("GET", description="HTTP method: GET or POST")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    json_body: Optional[Dict[str, Any]] = Field(None, description="JSON body for POST requests")


class TikTokOrganicProxyRequest(BaseModel):
    """Generic proxy request model for executing any TikTok Organic/Display API endpoint."""
    client_id: str = Field(..., description="ID of the client/agency")
    account_id: str = Field(..., description="Organic profile account_id (open_id or BC asset ID)")
    path: str = Field(..., description="The TikTok API path (e.g. business/video/list/ or v2/video/list/)")
    method: str = Field("GET", description="HTTP method: GET or POST")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    json_body: Optional[Dict[str, Any]] = Field(None, description="JSON body for POST requests")


class PlatformProxyRequest(BaseModel):
    """Generic proxy request model for executing arbitrary platform API calls."""
    client_id: str = Field(..., description="ID of the client/agency")
    account_id: str = Field(..., description="Platform-specific account/advertiser/property/store identifier")
    path: str = Field(..., description="The API path/endpoint to call")
    method: str = Field("GET", description="HTTP method (e.g., GET, POST, PUT, DELETE)")
    params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    json_body: Optional[Dict[str, Any]] = Field(None, description="JSON body for write requests")
    headers: Optional[Dict[str, str]] = Field(None, description="Optional custom headers")







def validate_search_console_site(value: str) -> str:
    """Accept Search Console domain and URL-prefix properties, not arbitrary URLs."""
    import re
    from urllib.parse import urlsplit

    domain = value.removeprefix("sc-domain:") if value.startswith("sc-domain:") else None
    if domain is None:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.netloc != parsed.hostname or any(c.isspace() for c in value)):
            raise ValueError("account_id must be a Search Console URL-prefix or sc-domain property")
        domain = parsed.hostname
    if not re.fullmatch(r"(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", domain):
        raise ValueError("account_id must contain a valid property domain")
    return value


class SearchConsoleQueryRequest(BaseModel):
    """Read-only Search Analytics query; no caller-controlled upstream URL or headers."""

    model_config = {"extra": "forbid"}
    client_id: str = Field("client_1", min_length=1)
    account_id: str
    start_date: date
    end_date: date
    dimensions: List[Literal["date", "query", "country", "page", "device"]] = Field(default_factory=list, max_length=5)
    query: Optional[str] = Field(None, min_length=1, max_length=4096, description="Exact, case-sensitive Google search query filter")
    row_limit: int = Field(1000, ge=1, le=25000)
    start_row: int = Field(0, ge=0)

    @model_validator(mode="after")
    def validate_query(self):
        validate_search_console_site(self.account_id)
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("dimensions must be unique")
        return self

    def upstream_body(self) -> Dict[str, Any]:
        body = {"startDate": self.start_date.isoformat(), "endDate": self.end_date.isoformat(),
                "dimensions": self.dimensions, "type": "web", "dataState": "final",
                "rowLimit": self.row_limit, "startRow": self.start_row}
        if self.query is not None:
            body["dimensionFilterGroups"] = [{"filters": [{"dimension": "query", "operator": "equals", "expression": self.query}]}]
        return body
