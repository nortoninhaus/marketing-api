"""
Response models optimized for both human dashboards and agentic consumption.

Every response includes request_id, timestamp, and structured metadata
so agents can reason about data freshness, errors, and pagination.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.models.requests import Platform


class CampaignData(BaseModel):
    """Single campaign/content data point with normalized metrics."""

    campaign_name: str = Field(..., description="Campaign or content name")
    date: str = Field(..., description="Date for this data point (YYYY-MM-DD)")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Key-value metric data")


class PaginationInfo(BaseModel):
    """Pagination metadata for large result sets."""

    page: int = 1
    page_size: int = 100
    total_count: Optional[int] = None
    has_next: bool = False
    next_page_token: Optional[str] = None


class ErrorDetail(BaseModel):
    """Structured error for agentic error handling."""

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    platform: Optional[str] = None
    retryable: bool = False
    rate_limit_remaining: Optional[int] = Field(None, description="Remaining rate limit quota if available")


class DataResponse(BaseModel):
    """
    Agent-ready response with full metadata.

    Agents use `request_id` for dedup, `status` for branching logic,
    `errors` for structured retry decisions, and `metadata` for
    data-quality reasoning.
    """

    status: Literal["success", "partial", "error"] = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    platform: Platform
    date_range: Dict[str, str] = Field(default_factory=dict)
    data: List[CampaignData] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Platform API version, data freshness, quota remaining, etc.",
    )
    errors: List[ErrorDetail] = Field(default_factory=list)
    pagination: Optional[PaginationInfo] = None
    rate_limit_remaining: Optional[int] = None


class CommentData(BaseModel):
    """Single comment with optional nested replies."""

    comment_id: str = Field(..., description="Platform-native comment ID")
    text: str = Field("", description="Comment text content")
    author: str = Field("", description="Author username or name")
    timestamp: str = Field("", description="ISO-8601 timestamp of the comment")
    like_count: int = Field(0, description="Number of likes on this comment")
    reply_count: int = Field(0, description="Number of replies to this comment")
    replies: List["CommentData"] = Field(default_factory=list, description="Nested reply comments")


class CommentsResponse(BaseModel):
    """Response model for comment-fetching endpoints."""

    status: Literal["success", "partial", "error"] = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    platform: Platform
    post_id: str = ""
    total_comments: int = 0
    comments: List[CommentData] = Field(default_factory=list)
    errors: List[ErrorDetail] = Field(default_factory=list)
    rate_limit_remaining: Optional[int] = None
    next_page_token: Optional[str] = None


class BatchDataResponse(BaseModel):
    """Aggregated response for multi-platform batch queries."""

    status: Literal["success", "partial", "error"] = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    results: List[DataResponse] = Field(default_factory=list)
    total_platforms: int = 0
    successful_platforms: int = 0
    failed_platforms: int = 0
    rate_limit_remaining: Optional[int] = None


class PlatformInfo(BaseModel):
    """Platform metadata for the discovery endpoint."""

    platform: Platform
    display_name: str
    type: Literal["ads", "organic", "analytics", "app_store"]
    configured: bool = False
    available_metrics: List[str] = Field(default_factory=list)
    generic_metrics: List[str] = Field(default_factory=list)
    supports_comments: bool = False
    supports_batch: bool = True
    description: str = ""
    api_version: Optional[str] = None


class HealthResponse(BaseModel):
    """Deep health check response."""

    status: str
    version: str
    platforms_configured: int
    platforms_total: int = 19  # 19 platforms (including pinterest/shopify)
    details: Dict[str, str] = Field(default_factory=dict)


class SchemaResponse(BaseModel):
    """Platform schema discovery response."""

    platform: Platform
    metrics: List[Any] = Field(..., description="Available metrics (strings or dicts with name/description)")
    dimensions: List[Any] = Field(..., description="Available dimensions (strings or dicts with name/description)")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResponse(BaseModel):
    """Unified validation response."""

    valid: bool
    platform: Platform
    valid_metrics: List[str] = Field(default_factory=list)
    invalid_metrics: List[str] = Field(default_factory=list)
    translations: Optional[Dict[str, Optional[str]]] = None
    native_metrics_to_request: Optional[List[str]] = None
    parameter_errors: List[str] = Field(default_factory=list)


class CredentialStatusDetails(BaseModel):
    """Details of credential status for a platform."""

    has_credentials: bool
    credential_type: Literal["oauth", "api_key", "service_account", "none"]
    details: str
    last_refreshed: Optional[str] = None


class CredentialStatusResponse(BaseModel):
    """Response showing client credential status across all platforms."""

    client_id: str
    platforms: Dict[str, CredentialStatusDetails]

