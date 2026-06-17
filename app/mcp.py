"""
MCP Server — Exposes the Inhaus Marketing API as agent-callable tools.

Run standalone:
    .venv/bin/python -m app.mcp

Or use as a stdio transport for IDE / agent integrations.
"""

import asyncio
import logging
from enum import Enum
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

from app.config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP] %(levelname)s  %(message)s",
)
logger = logging.getLogger("inhaus-mcp")

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "Inhaus Marketing API",
    instructions=(
        "You are connected to the Inhaus Marketing Data API — a unified, "
        "multi-tenant gateway to 14 marketing and analytics platforms "
        "(Meta Ads, Google Ads, TikTok, LinkedIn, YouTube, GA4, and more). "
        "Use the tools below to discover platforms, inspect schemas, "
        "fetch campaign/organic data, and run cross-platform comparisons."
    ),
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": settings.api_key}
TIMEOUT = httpx.Timeout(30.0, connect=10.0)

VALID_PLATFORMS = [
    "meta_ads", "meta_organic", "google_ads", "ga4",
    "tiktok_ads", "tiktok_organic", "linkedin_ads", "linkedin_organic",
    "x_ads", "x_organic", "youtube", "google_play",
    "apple_app_store", "apple_ads", "threads",
]

METRIC_TRANSLATION_MAP = {
    "meta_ads": {
        "spend": "spend",
        "clicks": "clicks",
        "impressions": "impressions",
        "conversions": "conversions"
    },
    "google_ads": {
        "spend": "cost_micros",
        "clicks": "clicks",
        "impressions": "impressions",
        "conversions": "conversions"
    },
    "tiktok_ads": {
        "spend": "spend",
        "clicks": "clicks",
        "impressions": "impressions",
        "conversions": "conversion"
    },
    "linkedin_ads": {
        "spend": "costInLocalCurrency",
        "clicks": "clicks",
        "impressions": "impressions"
    },
    "apple_ads": {
        "spend": "spend",
        "clicks": "taps",
        "impressions": "impressions",
        "conversions": "installs"
    },
    "ga4": {
        "sessions": "sessions",
        "users": "activeUsers",
        "pageviews": "screenPageViews",
        "bounce_rate": "bounceRate",
        "conversions": "conversions"
    },
    "google_play": {
        "downloads": "installs",
        "ratings": "rating"
    },
    "apple_app_store": {
        "downloads": "downloads",
        "impressions": "impressions",
        "sessions": "sessions"
    },
    "tiktok_organic": {
        "impressions": "view_count",
        "engagement": "like_count",
        "followers": "follower_count"
    },
    "linkedin_organic": {
        "impressions": "impressionCount",
        "clicks": "clickCount",
        "engagement": "engagement"
    },
    "x_organic": {
        "impressions": "impression_count",
        "engagement": "like_count"
    },
    "youtube": {
        "impressions": "views",
        "engagement": "likeCount",
        "followers": "subscribersGained"
    },
    "threads": {
        "impressions": "views",
        "engagement": "likes",
        "followers": "followers_count"
    }
}

def _translate_metric_to_native(platform: str, metric: str) -> str:
    """Translate a generic metric name to the platform-specific native metric name."""
    if platform in METRIC_TRANSLATION_MAP:
        return METRIC_TRANSLATION_MAP[platform].get(metric, metric)
    return metric

def _translate_metric_to_generic(platform: str, native_metric: str) -> str:
    """Translate a platform-specific native metric name back to its generic name."""
    if platform in METRIC_TRANSLATION_MAP:
        for generic, native in METRIC_TRANSLATION_MAP[platform].items():
            if native == native_metric:
                return generic
    return native_metric


async def _get(path: str, params: dict | None = None) -> dict:
    """Issue an authenticated GET to the FastAPI backend."""
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}{path}", headers=HEADERS, params=params
        )
        resp.raise_for_status()
        return resp.json()


async def _post(path: str, payload: dict, timeout: float = 30.0) -> dict:
    """Issue an authenticated POST to the FastAPI backend."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=10.0)) as client:
        resp = await client.post(
            f"{BASE_URL}{path}", headers=HEADERS, json=payload
        )
        resp.raise_for_status()
        return resp.json()


# ===================================================================
# TOOL 1 — Health Check
# ===================================================================
@mcp.tool()
async def check_api_health(deep: bool = False) -> dict:
    """
    Check the health and readiness of the Marketing API.

    Returns the API version, how many platforms are configured,
    and a per-platform status map.

    Args:
        deep: If True, each configured platform runs a live connectivity
              ping against its upstream API. This is slower but confirms
              actual reachability (not just configuration presence).

    Returns:
        A dict with keys: status, version, platforms_configured,
        platforms_total, details (per-platform status strings).
    """
    params = {"deep": "true"} if deep else {}
    return await _get("/health", params=params)


# ===================================================================
# TOOL 2 — List Platforms
# ===================================================================
@mcp.tool()
async def list_platforms() -> list[dict]:
    """
    Discover every supported marketing platform and its current state.

    Use this first to learn which platforms are available, which ones
    are configured with credentials, what metrics each platform
    supports, and whether a platform is of type 'ads', 'organic',
    'analytics', or 'app_store'.

    Returns:
        A list of platform objects, each containing:
        - platform: enum key (e.g. "meta_ads")
        - display_name: human-readable name
        - type: one of ads | organic | analytics | app_store
        - configured: boolean
        - available_metrics: list of metric name strings
        - description: short summary
    """
    return await _get("/api/v1/platforms")


# ===================================================================
# TOOL 3 — Get Platform Schema
# ===================================================================
@mcp.tool()
async def get_platform_schema(platform: str) -> dict:
    """
    Retrieve the full metric and dimension schema for a platform.

    Call this before fetching data so you know exactly which metric
    names are valid for the 'metrics' parameter of get_marketing_data.

    Args:
        platform: Platform enum value. One of:
                  meta_ads, meta_organic, google_ads, ga4,
                  tiktok_ads, tiktok_organic, linkedin_ads,
                  linkedin_organic, x_ads, x_organic, youtube,
                  google_play, apple_app_store, apple_ads.

    Returns:
        A dict with keys: platform, metrics (list), dimensions (list),
        metadata (dict with platform-specific info like API version).
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}
    return await _get(f"/api/v1/schema/{platform}")


# ===================================================================
# TOOL 4 — Get Marketing Data (single platform)
# ===================================================================
@mcp.tool()
async def get_marketing_data(
    platform: str,
    start_date: str,
    end_date: str,
    metrics: list[str],
    client_id: str,
    user_id: str,
    account_id: str,
    post_id: str | None = None,
    video_id: str | None = None,
    app_id: str | None = None,
) -> dict:
    """
    Fetch campaign or content performance data from a single platform.

    This is the primary data-retrieval tool.  Supply the platform,
    a date range, and the metrics you want (use get_platform_schema
    to discover valid metric names).

    Args:
        platform:   Platform enum value (e.g. "meta_ads", "ga4").
        start_date: Start of the date range in YYYY-MM-DD format.
        end_date:   End of the date range in YYYY-MM-DD format.
        metrics:    List of metric names to retrieve.
                    Must contain at least one metric.
                    Example: ["impressions", "clicks", "spend"]
        client_id:  Unique ID of the agency client / tenant.
        user_id:    ID of the user making the request.
        account_id: Platform-specific account identifier
                    (Ad Account ID, GA4 Property ID, Page ID, etc.).
        post_id:    (Optional) Specific post or content ID.
                    Only relevant for organic platforms.
        video_id:   (Optional) Specific video ID.
                    Only relevant for YouTube or TikTok Organic.
        app_id:     (Optional) App package name or store ID.
                    Only relevant for Google Play / Apple App Store.

    Returns:
        A dict with keys: status, request_id, timestamp, platform,
        date_range, data (list of campaign objects), errors, metadata.
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    payload = {
        "platform": platform,
        "start_date": start_date,
        "end_date": end_date,
        "metrics": metrics,
        "client_id": client_id,
        "user_id": user_id,
        "account_id": account_id,
    }
    if post_id:
        payload["post_id"] = post_id
    if video_id:
        payload["video_id"] = video_id
    if app_id:
        payload["app_id"] = app_id

    return await _post("/api/v1/campaign-data", payload)


# ===================================================================
# TOOL 5 — Batch Marketing Data (multi-platform)
# ===================================================================
@mcp.tool()
async def get_batch_marketing_data(requests: list[dict]) -> dict:
    """
    Fetch marketing data from multiple platforms in a single call.

    All sub-requests run concurrently on the server. If some
    platforms fail, the response will have status "partial" with
    successful results and structured errors for the failures.

    Args:
        requests: A list of request dicts, each containing:
            - platform (str): platform enum value
            - start_date (str): YYYY-MM-DD
            - end_date (str): YYYY-MM-DD
            - metrics (list[str]): at least one metric
            - client_id (str)
            - user_id (str)
            - account_id (str)
            - post_id (str, optional)
            - video_id (str, optional)
            - app_id (str, optional)

        Maximum 14 sub-requests per batch (one per platform).

    Returns:
        A dict with keys: status, request_id, timestamp, results
        (list of per-platform responses), total_platforms,
        successful_platforms, failed_platforms.
    """
    return await _post("/api/v1/batch", {"requests": requests}, timeout=90.0)


# ===================================================================
# TOOL 6 — Compare Platforms
# ===================================================================
@mcp.tool()
async def compare_platforms(
    platforms: list[str],
    start_date: str,
    end_date: str,
    metrics: list[str],
    client_id: str,
    user_id: str,
    account_ids: dict[str, str],
) -> dict:
    """
    Compare performance across multiple platforms side-by-side.

    This is a convenience tool that internally uses the batch
    endpoint but restructures the response into a comparison table.

    Args:
        platforms:   List of platform enum values to compare.
                     Example: ["meta_ads", "google_ads", "tiktok_ads"]
        start_date:  Start of the date range (YYYY-MM-DD).
        end_date:    End of the date range (YYYY-MM-DD).
        metrics:     Metrics to compare across platforms.
                     Example: ["impressions", "clicks", "spend"]
        client_id:   Client/tenant ID.
        user_id:     Requesting user ID.
        account_ids: Mapping of platform → account ID.
                     Example: {"meta_ads": "act_123", "google_ads": "456"}

    Returns:
        A dict with:
        - comparison: per-platform metric totals
        - date_range: the requested range
        - platforms_compared: count
        - errors: list of platforms that failed
    """
    # Validate
    for p in platforms:
        if p not in VALID_PLATFORMS:
            return {"error": f"Invalid platform '{p}'. Must be one of: {VALID_PLATFORMS}"}
        if p not in account_ids:
            return {"error": f"Missing account_id for platform '{p}' in account_ids map."}

    # Build batch sub-requests with translated metrics
    sub_requests = [
        {
            "platform": p,
            "start_date": start_date,
            "end_date": end_date,
            "metrics": list(set([_translate_metric_to_native(p, m) for m in metrics])),
            "client_id": client_id,
            "user_id": user_id,
            "account_id": account_ids[p],
        }
        for p in platforms
    ]

    raw = await _post("/api/v1/batch", {"requests": sub_requests}, timeout=90.0)

    # Restructure into a comparison view
    comparison: dict[str, dict] = {}
    errors: list[dict] = []

    for result in raw.get("results", []):
        plat = result.get("platform", "unknown")
        if result.get("status") != "success":
            errors.append({"platform": plat, "errors": result.get("errors", [])})
            continue

        # Aggregate metrics across all campaign rows
        totals: dict[str, float] = {m: 0 for m in metrics}
        for row in result.get("data", []):
            row_metrics = row.get("metrics", {})
            for m in metrics:
                native_m = _translate_metric_to_native(plat, m)
                val = row_metrics.get(native_m)
                if val is not None:
                    try:
                        val_float = float(val)
                        if plat == "google_ads" and native_m == "cost_micros":
                            val_float = val_float / 1000000.0
                        totals[m] += val_float
                    except (ValueError, TypeError):
                        pass
        comparison[plat] = totals

    return {
        "comparison": comparison,
        "date_range": {"start": start_date, "end": end_date},
        "platforms_compared": len(comparison),
        "errors": errors,
    }


# ===================================================================
# TOOL 7 — List Available Metrics
# ===================================================================
@mcp.tool()
async def list_available_metrics(platform: str) -> dict:
    """
    Quickly list just the metric names supported by a platform.

    This is a lightweight alternative to get_platform_schema when
    you only need to know which metrics you can request.

    Args:
        platform: Platform enum value (e.g. "meta_ads").

    Returns:
        A dict with keys: platform, metrics (list of strings),
        total_metrics (int).
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    schema = await _get(f"/api/v1/schema/{platform}")
    raw_metrics = schema.get("metrics", [])
    names = [m["name"] if isinstance(m, dict) else m for m in raw_metrics]
    return {
        "platform": platform,
        "metrics": names,
        "total_metrics": len(names),
    }


# ===================================================================
# TOOL 8 — Summarize Platform Performance
# ===================================================================
@mcp.tool()
async def summarize_performance(
    platform: str,
    start_date: str,
    end_date: str,
    client_id: str,
    user_id: str,
    account_id: str,
) -> dict:
    """
    Get a high-level performance summary for a single platform.

    Automatically requests the platform's most common metrics,
    aggregates them across all campaigns, and returns a concise
    summary dict. Useful for quick status checks and dashboards.

    Args:
        platform:   Platform enum value.
        start_date: YYYY-MM-DD.
        end_date:   YYYY-MM-DD.
        client_id:  Client/tenant ID.
        user_id:    Requesting user ID.
        account_id: Platform-specific account identifier.

    Returns:
        A dict with: platform, date_range, total_campaigns,
        aggregated_metrics (totals across all campaigns),
        status.
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    # Determine default metrics based on platform type
    DEFAULT_METRICS = {
        "ads": ["impressions", "clicks", "spend", "conversions"],
        "organic": ["impressions", "reach", "engagement", "followers"],
        "analytics": ["sessions", "users", "pageviews", "bounce_rate"],
        "app_store": ["downloads", "revenue", "ratings", "active_users"],
    }

    ptype = "ads"
    if "organic" in platform or platform == "youtube":
        ptype = "organic"
    elif platform == "ga4":
        ptype = "analytics"
    elif platform in ("google_play", "apple_app_store"):
        ptype = "app_store"

    generic_metrics = DEFAULT_METRICS[ptype]
    native_metrics = []
    for m in generic_metrics:
        if platform in METRIC_TRANSLATION_MAP:
            if m in METRIC_TRANSLATION_MAP[platform]:
                native_metrics.append(METRIC_TRANSLATION_MAP[platform][m])
        else:
            native_metrics.append(m)

    try:
        result = await _post("/api/v1/campaign-data", {
            "platform": platform,
            "start_date": start_date,
            "end_date": end_date,
            "metrics": native_metrics,
            "client_id": client_id,
            "user_id": user_id,
            "account_id": account_id,
        })
    except httpx.HTTPStatusError as exc:
        return {
            "platform": platform,
            "status": "error",
            "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
        }

    # Aggregate
    totals: dict[str, float] = {}
    campaigns = result.get("data", [])
    for row in campaigns:
        row_metrics = row.get("metrics", {})
        for native_m in native_metrics:
            generic_m = _translate_metric_to_generic(platform, native_m)
            val = row_metrics.get(native_m)
            if val is not None:
                try:
                    val_float = float(val)
                    if platform == "google_ads" and native_m == "cost_micros":
                        val_float = val_float / 1000000.0
                    
                    if generic_m not in totals:
                        totals[generic_m] = 0.0
                    totals[generic_m] += val_float
                except (ValueError, TypeError):
                    pass

    return {
        "platform": platform,
        "date_range": {"start": start_date, "end": end_date},
        "total_campaigns": len(campaigns),
        "aggregated_metrics": totals,
        "status": result.get("status", "unknown"),
    }


# ===================================================================
# TOOL 9 — Get Comments
# ===================================================================
@mcp.tool()
async def get_comments(
    platform: str,
    post_id: str,
    client_id: str,
    user_id: str,
    account_id: str = "",
) -> dict:
    """
    Fetch comments/replies for a specific post.
    Works for platforms that support comments: meta_ads, meta_organic, threads.

    Args:
        platform:  Platform enum value (must be meta_ads, meta_organic, or threads).
        post_id:   The platform-native identifier of the post/media.
        client_id: Client/tenant identifier.
        user_id:   Requesting user ID.
        account_id: Platform-specific account identifier (optional).

    Returns:
        A dict with: status, platform, post_id, total_comments, comments (list), errors.
    """
    if platform not in ("meta_ads", "meta_organic", "threads"):
        return {"error": f"Comments are not supported for platform '{platform}'. Supported: meta_ads, meta_organic, threads"}

    payload = {
        "platform": platform,
        "post_id": post_id,
        "client_id": client_id,
        "user_id": user_id,
        "account_id": account_id,
    }
    return await _post("/api/v1/comments", payload)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()
