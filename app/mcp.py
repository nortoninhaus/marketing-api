"""
MCP Server — Exposes the Inhaus Marketing API as agent-callable tools.

Run standalone:
    .venv/bin/python -m app.mcp

Or use as a stdio transport for IDE / agent integrations.
"""

import asyncio
import logging
import time as _time
from enum import Enum
from functools import wraps
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config import settings
from app.metrics import (
    COMMENT_SUPPORTED_PLATFORMS,
    METRIC_TRANSLATION_MAP,
    UNIT_CONVERSIONS,
    get_default_metrics,
    get_metric_compatibility_table,
    get_platform_type,
    get_supported_generic_metrics,
    translate_to_generic,
    translate_to_native,
    validate_metrics,
)

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
        "multi-tenant gateway to 15 marketing and analytics platforms "
        "(Meta Ads, Google Ads, TikTok, LinkedIn, YouTube, GA4, and more). "
        "Use the tools below to discover platforms, inspect schemas, "
        "fetch campaign/organic data, and run cross-platform comparisons. "
        "IMPORTANT: Use generic metric names (impressions, clicks, spend, "
        "conversions, engagement, followers, sessions, users, pageviews, "
        "bounce_rate, downloads, ratings) when calling summarize_performance "
        "or compare_platforms — the system will translate them automatically."
    ),
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"
HEADERS = {"X-API-Key": settings.api_key}
TIMEOUT = httpx.Timeout(60.0, connect=15.0)

VALID_PLATFORMS = [
    "meta_ads", "meta_organic", "google_ads", "ga4",
    "tiktok_ads", "tiktok_organic", "linkedin_ads", "linkedin_organic",
    "x_ads", "x_organic", "youtube", "google_play",
    "apple_app_store", "apple_ads", "threads",
]

# ---------------------------------------------------------------------------
# Observability: tool call latency tracking
# ---------------------------------------------------------------------------
_tool_call_stats: dict[str, list[float]] = {}


def _track_latency(tool_name: str):
    """Decorator that logs and tracks latency for MCP tool calls."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = _time.monotonic()
            request_id = f"{tool_name}_{int(start * 1000) % 100000}"
            logger.info(f"[{request_id}] Tool call started: {tool_name}")
            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (_time.monotonic() - start) * 1000
                logger.info(f"[{request_id}] Tool call completed: {tool_name} ({elapsed_ms:.0f}ms)")
                _tool_call_stats.setdefault(tool_name, []).append(elapsed_ms)
                # Keep only last 100 measurements per tool
                if len(_tool_call_stats[tool_name]) > 100:
                    _tool_call_stats[tool_name] = _tool_call_stats[tool_name][-100:]
                return result
            except Exception as e:
                elapsed_ms = (_time.monotonic() - start) * 1000
                logger.error(f"[{request_id}] Tool call FAILED: {tool_name} ({elapsed_ms:.0f}ms) — {e}")
                raise
        return wrapper
    return decorator


# ---------------------------------------------------------------------------
# HTTP helpers with retry
# ---------------------------------------------------------------------------
_MAX_RETRIES = 2
_RETRY_BACKOFF_BASE = 1.0  # seconds


async def _get(path: str, params: dict | None = None) -> dict:
    """Issue an authenticated GET to the FastAPI backend with retry."""
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.get(
                    f"{BASE_URL}{path}", headers=HEADERS, params=params
                )
                resp.raise_for_status()
                return resp.json()
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"GET {path} attempt {attempt + 1} failed ({e}), retrying in {wait}s…")
                await asyncio.sleep(wait)
            else:
                logger.error(f"GET {path} failed after {_MAX_RETRIES + 1} attempts: {e}")
        except httpx.HTTPStatusError:
            raise  # Don't retry HTTP 4xx/5xx
    raise last_error  # type: ignore[misc]


async def _post(path: str, payload: dict, timeout: float = 60.0) -> dict:
    """Issue an authenticated POST to the FastAPI backend with retry."""
    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=15.0)) as client:
                resp = await client.post(
                    f"{BASE_URL}{path}", headers=HEADERS, json=payload
                )
                resp.raise_for_status()
                return resp.json()
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_BASE * (2 ** attempt)
                logger.warning(f"POST {path} attempt {attempt + 1} failed ({e}), retrying in {wait}s…")
                await asyncio.sleep(wait)
            else:
                logger.error(f"POST {path} failed after {_MAX_RETRIES + 1} attempts: {e}")
        except httpx.HTTPStatusError:
            raise
    raise last_error  # type: ignore[misc]


# ===================================================================
# TOOL 1 — Health Check
# ===================================================================
@mcp.tool()
@_track_latency("check_api_health")
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
@_track_latency("list_platforms")
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
        - generic_metrics: list of supported generic metric names
          (use these with summarize_performance / compare_platforms)
        - supports_comments: whether get_comments works for this platform
        - description: short summary
    """
    platforms = await _get("/api/v1/platforms")

    # Enrich with generic metric info and tool support
    for p in platforms:
        pname = p.get("platform", "")
        p["generic_metrics"] = get_supported_generic_metrics(pname)
        p["supports_comments"] = pname in COMMENT_SUPPORTED_PLATFORMS
        p["supports_batch"] = True  # All platforms support batch

    return platforms


# ===================================================================
# TOOL 3 — Get Platform Schema
# ===================================================================
@mcp.tool()
@_track_latency("get_platform_schema")
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
                  google_play, apple_app_store, apple_ads, threads.

    Returns:
        A dict with keys: platform, metrics (list), dimensions (list),
        metadata (dict with platform-specific info like API version),
        generic_metrics (list of generic names usable with
        summarize_performance / compare_platforms).
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    schema = await _get(f"/api/v1/schema/{platform}")
    schema["generic_metrics"] = get_supported_generic_metrics(platform)
    return schema


# ===================================================================
# TOOL 4 — Get Marketing Data (single platform)
# ===================================================================
@mcp.tool()
@_track_latency("get_marketing_data")
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

    IMPORTANT: For this tool, use the platform's NATIVE metric names
    (from get_platform_schema), not the generic names.

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
        If any requested metrics are invalid, a 'warnings' key will
        contain details about which metrics were skipped.
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    if not metrics:
        return {"error": "At least one metric is required."}

    from app.metrics import validate_platform_params
    param_errors = validate_platform_params(
        platform, account_id, post_id=post_id, video_id=video_id, app_id=app_id
    )
    if param_errors:
        return {"error": " | ".join(param_errors)}

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
@_track_latency("get_batch_marketing_data")
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

        Maximum 15 sub-requests per batch (one per platform).

    Returns:
        A dict with keys: status, request_id, timestamp, results
        (list of per-platform responses), total_platforms,
        successful_platforms, failed_platforms.
    """
    return await _post("/api/v1/batch", {"requests": requests}, timeout=120.0)


# ===================================================================
# TOOL 6 — Compare Platforms
# ===================================================================
@mcp.tool()
@_track_latency("compare_platforms")
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

    Uses GENERIC metric names (impressions, clicks, spend, conversions,
    engagement, followers, etc.) and automatically translates them to
    each platform's native names. Unsupported metrics for a platform
    are reported in the 'warnings' field rather than causing failures.

    Args:
        platforms:   List of platform enum values to compare.
                     Example: ["meta_ads", "google_ads", "tiktok_ads"]
        start_date:  Start of the date range (YYYY-MM-DD).
        end_date:    End of the date range (YYYY-MM-DD).
        metrics:     Generic metric names to compare across platforms.
                     Example: ["impressions", "clicks", "spend"]
                     Supported: impressions, clicks, spend, conversions,
                     reach, engagement, followers, sessions, users,
                     pageviews, bounce_rate, downloads, ratings.
        client_id:   Client/tenant ID.
        user_id:     Requesting user ID.
        account_ids: Mapping of platform → account ID.
                     Example: {"meta_ads": "act_123", "google_ads": "456"}

    Returns:
        A dict with:
        - comparison: per-platform metric totals (using generic names)
        - date_range: the requested range
        - platforms_compared: count
        - warnings: metrics unsupported on specific platforms
        - errors: list of platforms that failed
    """
    # Validate
    warnings: list[dict] = []
    for p in platforms:
        if p not in VALID_PLATFORMS:
            return {"error": f"Invalid platform '{p}'. Must be one of: {VALID_PLATFORMS}"}
        if p not in account_ids:
            return {"error": f"Missing account_id for platform '{p}' in account_ids map."}

    # Build batch sub-requests with translated metrics per platform
    sub_requests = []
    platform_metric_map: dict[str, list[str]] = {}
    for p in platforms:
        native_metrics, metric_errors = validate_metrics(p, metrics)
        for err in metric_errors:
            warnings.append({"platform": p, **err})

        if not native_metrics:
            warnings.append({
                "platform": p,
                "metric": "all",
                "message": f"No supported metrics for platform '{p}'. It will be skipped.",
            })
            continue

        platform_metric_map[p] = native_metrics
        sub_requests.append({
            "platform": p,
            "start_date": start_date,
            "end_date": end_date,
            "metrics": native_metrics,
            "client_id": client_id,
            "user_id": user_id,
            "account_id": account_ids[p],
        })

    if not sub_requests:
        return {
            "comparison": {},
            "date_range": {"start": start_date, "end": end_date},
            "platforms_compared": 0,
            "warnings": warnings,
            "errors": [],
        }

    raw = await _post("/api/v1/batch", {"requests": sub_requests}, timeout=120.0)

    # Restructure into a comparison view with generic names
    comparison: dict[str, dict] = {}
    errors: list[dict] = []

    for result in raw.get("results", []):
        plat = result.get("platform", "unknown")
        if result.get("status") != "success":
            errors.append({"platform": plat, "errors": result.get("errors", [])})
            continue

        # Aggregate metrics across all campaign rows
        totals: dict[str, float] = {m: 0 for m in metrics}
        has_data: dict[str, bool] = {m: False for m in metrics}

        for row in result.get("data", []):
            row_metrics = row.get("metrics", {})
            for generic_m in metrics:
                native_m = METRIC_TRANSLATION_MAP.get(plat, {}).get(generic_m)
                if native_m is None:
                    continue  # Not supported — already warned
                val = row_metrics.get(native_m)
                if val is not None:
                    try:
                        val_float = float(val)
                        # Apply unit conversion
                        divisor = UNIT_CONVERSIONS.get((plat, native_m))
                        if divisor:
                            val_float = val_float / divisor
                        totals[generic_m] += val_float
                        has_data[generic_m] = True
                    except (ValueError, TypeError):
                        pass

        # Replace metrics with no data with None instead of 0
        for m in metrics:
            if not has_data.get(m, False):
                platform_map = METRIC_TRANSLATION_MAP.get(plat, {})
                if platform_map.get(m) is None:
                    totals[m] = None  # type: ignore[assignment]

        comparison[plat] = totals

    return {
        "comparison": comparison,
        "date_range": {"start": start_date, "end": end_date},
        "platforms_compared": len(comparison),
        "warnings": warnings,
        "errors": errors,
    }


# ===================================================================
# TOOL 7 — List Available Metrics
# ===================================================================
@mcp.tool()
@_track_latency("list_available_metrics")
async def list_available_metrics(platform: str) -> dict:
    """
    Quickly list just the metric names supported by a platform.

    Returns both the platform's native metric names and the
    generic names that can be used with summarize_performance
    and compare_platforms.

    Args:
        platform: Platform enum value (e.g. "meta_ads").

    Returns:
        A dict with keys: platform, native_metrics (list of strings),
        generic_metrics (list of generic names), total_metrics (int).
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    schema = await _get(f"/api/v1/schema/{platform}")
    raw_metrics = schema.get("metrics", [])
    names = [m["name"] if isinstance(m, dict) else m for m in raw_metrics]
    return {
        "platform": platform,
        "native_metrics": names,
        "generic_metrics": get_supported_generic_metrics(platform),
        "total_metrics": len(names),
    }


# ===================================================================
# TOOL 8 — Summarize Platform Performance
# ===================================================================
@mcp.tool()
@_track_latency("summarize_performance")
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

    Automatically selects the most relevant metrics for the platform
    type (ads, organic, analytics, app_store), translates them to
    native names, fetches data, and returns aggregated totals using
    generic metric names.

    Args:
        platform:   Platform enum value.
        start_date: YYYY-MM-DD.
        end_date:   YYYY-MM-DD.
        client_id:  Client/tenant ID.
        user_id:    Requesting user ID.
        account_id: Platform-specific account identifier.

    Returns:
        A dict with: platform, platform_type, date_range,
        total_campaigns, aggregated_metrics (totals with generic names),
        unsupported_metrics (list of metrics not available),
        status.
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    # Get default generic metrics for this platform type
    generic_metrics = get_default_metrics(platform)
    ptype = get_platform_type(platform)

    # Translate to native, tracking which ones are supported
    native_metrics, metric_errors = validate_metrics(platform, generic_metrics)
    unsupported = [e["metric"] for e in metric_errors]

    if not native_metrics:
        return {
            "platform": platform,
            "platform_type": ptype,
            "status": "error",
            "error": f"No supported metrics found for platform '{platform}'. "
                     f"Attempted: {generic_metrics}",
            "unsupported_metrics": unsupported,
        }

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
    except (httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout) as exc:
        return {
            "platform": platform,
            "platform_type": ptype,
            "status": "error",
            "error": f"Connection error: {exc}",
        }
    except httpx.HTTPStatusError as exc:
        return {
            "platform": platform,
            "platform_type": ptype,
            "status": "error",
            "error": f"HTTP {exc.response.status_code}: {exc.response.text}",
        }

    # Aggregate with generic names and unit conversions
    totals: dict[str, float] = {}
    campaigns = result.get("data", [])
    for row in campaigns:
        row_metrics = row.get("metrics", {})
        translated = translate_to_generic(platform, row_metrics)
        for generic_name, value in translated.items():
            if value is not None and generic_name in generic_metrics:
                try:
                    val_float = float(value)
                    totals[generic_name] = totals.get(generic_name, 0.0) + val_float
                except (ValueError, TypeError):
                    pass

    return {
        "platform": platform,
        "platform_type": ptype,
        "date_range": {"start": start_date, "end": end_date},
        "total_campaigns": len(campaigns),
        "aggregated_metrics": totals,
        "unsupported_metrics": unsupported,
        "status": result.get("status", "unknown"),
    }


# ===================================================================
# TOOL 9 — Get Comments
# ===================================================================
@mcp.tool()
@_track_latency("get_comments")
async def get_comments(
    platform: str,
    post_id: str,
    client_id: str,
    user_id: str,
    account_id: str = "",
) -> dict:
    """
    Fetch comments/replies for a specific post.

    Works for platforms that support comments:
    meta_ads, meta_organic, threads, youtube, x_organic.

    Args:
        platform:  Platform enum value.
        post_id:   The platform-native identifier of the post/media.
                   For YouTube, use the video ID.
                   For X/Twitter, use the tweet ID.
        client_id: Client/tenant identifier.
        user_id:   Requesting user ID.
        account_id: Platform-specific account identifier (optional).

    Returns:
        A dict with: status, platform, post_id, total_comments,
        comments (list), errors.
    """
    if platform not in COMMENT_SUPPORTED_PLATFORMS:
        return {
            "error": (
                f"Comments are not supported for platform '{platform}'. "
                f"Supported: {COMMENT_SUPPORTED_PLATFORMS}"
            )
        }

    payload = {
        "platform": platform,
        "post_id": post_id,
        "client_id": client_id,
        "user_id": user_id,
        "account_id": account_id,
    }
    return await _post("/api/v1/comments", payload)


# ===================================================================
# TOOL 10 — Validate Request (Dry Run)
# ===================================================================
@mcp.tool()
@_track_latency("validate_request")
async def validate_request(
    platform: str,
    metrics: list[str],
    use_generic_names: bool = False,
) -> dict:
    """
    Validate whether a set of metrics are valid for a platform
    WITHOUT making an actual API call.

    Use this to check metric names before calling get_marketing_data,
    summarize_performance, or compare_platforms.

    Args:
        platform:          Platform enum value (e.g. "meta_ads").
        metrics:           List of metric names to validate.
        use_generic_names: If True, validates metrics as generic names
                           and shows what they translate to. If False,
                           validates them as native platform names.

    Returns:
        A dict with:
        - valid: True if all metrics are supported
        - platform: the platform checked
        - valid_metrics: list of metrics that are valid
        - invalid_metrics: list of metrics that are NOT valid
        - translations: (if use_generic_names) mapping of generic → native
    """
    if platform not in VALID_PLATFORMS:
        return {"error": f"Invalid platform '{platform}'. Must be one of: {VALID_PLATFORMS}"}

    if use_generic_names:
        native_metrics, errors = validate_metrics(platform, metrics)
        translations = {}
        for m in metrics:
            native = METRIC_TRANSLATION_MAP.get(platform, {}).get(m)
            translations[m] = native  # None if unsupported

        return {
            "valid": len(errors) == 0,
            "platform": platform,
            "valid_metrics": [m for m in metrics if translations.get(m) is not None],
            "invalid_metrics": [e["metric"] for e in errors],
            "translations": translations,
            "native_metrics_to_request": native_metrics,
        }
    else:
        # Validate against schema
        schema = await _get(f"/api/v1/schema/{platform}")
        raw_metrics = schema.get("metrics", [])
        schema_names = {m["name"] if isinstance(m, dict) else m for m in raw_metrics}

        valid = [m for m in metrics if m in schema_names]
        invalid = [m for m in metrics if m not in schema_names]

        return {
            "valid": len(invalid) == 0,
            "platform": platform,
            "valid_metrics": valid,
            "invalid_metrics": invalid,
            "available_metrics": sorted(schema_names),
        }


# ===================================================================
# TOOL 11 — Get Metric Compatibility
# ===================================================================
@mcp.tool()
@_track_latency("get_metric_compatibility")
async def get_metric_compatibility() -> dict:
    """
    Show which generic metrics are supported on which platforms.

    Use this to plan cross-platform comparisons and understand
    which metrics can be compared across platforms.

    Returns:
        A dict where keys are generic metric names and values are
        dicts mapping platform → native metric name (or null if
        unsupported).
    """
    return get_metric_compatibility_table()


# ===================================================================
# TOOL 12 — Get Credential Status
# ===================================================================
@mcp.tool()
@_track_latency("get_credential_status")
async def get_credential_status(client_id: str) -> dict:
    """
    Check the credentials configuration status for each platform for a client.

    Use this for debugging to see which platforms have active OAuth connections
    or manual credentials configured in Firestore.

    Args:
        client_id: Unique client/tenant identifier.

    Returns:
        A dict showing credential status (has_credentials, type, details)
        per platform.
    """
    return await _get("/api/v1/credentials/status", params={"client_id": client_id})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    mcp.run()

