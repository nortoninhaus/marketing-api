"""
Centralized metric translation and validation for the Marketing API.

Provides:
- Complete METRIC_TRANSLATION_MAP for all 15 platforms
- Unit conversions (e.g. cost_micros → dollars)
- Default metric sets by platform type
- Metric validation against platform schemas
- Bi-directional translation (generic ↔ native)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Generic → Native metric translation for every platform
# ---------------------------------------------------------------------------
# Keys are generic (agent-facing) names.
# Values are the platform-native metric names accepted by each connector.
# A value of None means the metric is not supported on that platform.

METRIC_TRANSLATION_MAP: dict[str, dict[str, str | None]] = {
    # ── Ads platforms ──────────────────────────────────────────────────
    "meta_ads": {
        "impressions": "impressions",
        "clicks": "clicks",
        "spend": "spend",
        "conversions": "conversions",
        "reach": "reach",
        "ctr": "ctr",
        "cpc": "cpc",
        "cpm": "cpm",
        "engagement": None,
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "google_ads": {
        "impressions": "impressions",
        "clicks": "clicks",
        "spend": "cost_micros",  # Requires unit conversion (÷ 1,000,000)
        "conversions": "conversions",
        "reach": None,
        "ctr": "ctr",
        "cpc": "average_cpc",
        "cpm": "average_cpm",
        "engagement": "engagements",
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": "bounce_rate",
        "downloads": None,
        "ratings": None,
    },
    "tiktok_ads": {
        "impressions": "impressions",
        "clicks": "clicks",
        "spend": "spend",
        "conversions": "conversion",  # singular on TikTok
        "reach": "reach",
        "ctr": "ctr",
        "cpc": "cpc",
        "cpm": "cpm",
        "engagement": None,
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "linkedin_ads": {
        "impressions": "impressions",
        "clicks": "clicks",
        "spend": "costInLocalCurrency",
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": None,
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "apple_ads": {
        "impressions": "impressions",
        "clicks": "taps",
        "spend": "spend",
        "conversions": "installs",
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": None,
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "x_ads": {
        "impressions": "impressions",
        "clicks": "clicks",
        "spend": "spend",
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "engagements",
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },

    # ── Organic platforms ──────────────────────────────────────────────
    "meta_organic": {
        "impressions": "views",  # IG: impressions deprecated July 2024
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": "reach",
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "total_interactions",
        "followers": "follower_count",
        "sessions": None,
        "users": None,
        "pageviews": "profile_views",
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "tiktok_organic": {
        "impressions": "view_count",
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "like_count",
        "followers": "follower_count",
        "sessions": None,
        "users": None,
        "pageviews": "profile_views",
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "linkedin_organic": {
        "impressions": "impressionCount",
        "clicks": "clickCount",
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "engagement",
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "x_organic": {
        "impressions": "impression_count",
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "like_count",
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "youtube": {
        "impressions": "views",
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "likes",
        "followers": "subscribersGained",
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },
    "threads": {
        "impressions": "views",
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "likes",
        "followers": "followers_count",
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": None,
        "ratings": None,
    },

    # ── Analytics ──────────────────────────────────────────────────────
    "ga4": {
        "impressions": None,
        "clicks": None,
        "spend": None,
        "conversions": "conversions",
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": "engagedSessions",
        "followers": None,
        "sessions": "sessions",
        "users": "activeUsers",
        "pageviews": "screenPageViews",
        "bounce_rate": "bounceRate",
        "downloads": None,
        "ratings": None,
    },

    # ── App Store platforms ────────────────────────────────────────────
    "google_play": {
        "impressions": None,
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": None,
        "followers": None,
        "sessions": None,
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": "installs",
        "ratings": "rating",
    },
    "apple_app_store": {
        "impressions": "impressions",
        "clicks": None,
        "spend": None,
        "conversions": None,
        "reach": None,
        "ctr": None,
        "cpc": None,
        "cpm": None,
        "engagement": None,
        "followers": None,
        "sessions": "sessions",
        "users": None,
        "pageviews": None,
        "bounce_rate": None,
        "downloads": "downloads",
        "ratings": None,
    },
}

# ---------------------------------------------------------------------------
# Unit conversions: (platform, native_metric) → divisor
# After fetching the raw value, divide by this number.
# ---------------------------------------------------------------------------
UNIT_CONVERSIONS: dict[tuple[str, str], float] = {
    ("google_ads", "cost_micros"): 1_000_000.0,
}

# ---------------------------------------------------------------------------
# Default generic metrics per platform type
# ---------------------------------------------------------------------------
DEFAULT_METRICS_BY_TYPE: dict[str, list[str]] = {
    "ads": ["impressions", "clicks", "spend", "conversions"],
    "organic": ["impressions", "engagement", "followers", "reach"],
    "analytics": ["sessions", "users", "pageviews", "bounce_rate"],
    "app_store": ["downloads", "ratings"],
}

# ---------------------------------------------------------------------------
# Platform → type mapping
# ---------------------------------------------------------------------------
PLATFORM_TYPES: dict[str, str] = {
    "meta_ads": "ads",
    "google_ads": "ads",
    "tiktok_ads": "ads",
    "linkedin_ads": "ads",
    "apple_ads": "ads",
    "x_ads": "ads",
    "meta_organic": "organic",
    "tiktok_organic": "organic",
    "linkedin_organic": "organic",
    "x_organic": "organic",
    "youtube": "organic",
    "threads": "organic",
    "ga4": "analytics",
    "google_play": "app_store",
    "apple_app_store": "app_store",
}

# ---------------------------------------------------------------------------
# Supported platforms for comments
# ---------------------------------------------------------------------------
COMMENT_SUPPORTED_PLATFORMS: list[str] = [
    "meta_ads", "meta_organic", "threads", "youtube", "x_organic",
]


# ===================================================================
# Public API
# ===================================================================

def get_platform_type(platform: str) -> str:
    """Return the platform type: 'ads', 'organic', 'analytics', or 'app_store'."""
    return PLATFORM_TYPES.get(platform, "ads")


def get_default_metrics(platform: str) -> list[str]:
    """Return the default generic metrics appropriate for the platform's type."""
    ptype = get_platform_type(platform)
    return list(DEFAULT_METRICS_BY_TYPE.get(ptype, []))


def translate_to_native(platform: str, generic_metrics: list[str]) -> list[str]:
    """
    Translate a list of generic metric names to platform-native names.

    Metrics that have no translation (unsupported on the platform) are
    silently dropped. Metrics that are already native (not in the generic
    map) are passed through unchanged.

    Returns:
        List of native metric names (deduplicated, order preserved).
    """
    platform_map = METRIC_TRANSLATION_MAP.get(platform, {})
    seen: set[str] = set()
    native: list[str] = []
    for m in generic_metrics:
        if m in platform_map:
            native_name = platform_map[m]
            if native_name is not None and native_name not in seen:
                native.append(native_name)
                seen.add(native_name)
        else:
            # Not a known generic metric — pass through as-is (could be native already)
            if m not in seen:
                native.append(m)
                seen.add(m)
    return native


def translate_to_generic(platform: str, native_metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Translate a dict of {native_metric: value} back to generic names.

    Also applies unit conversions (e.g. cost_micros → spend in dollars).

    Returns:
        Dict with generic metric names as keys.
    """
    platform_map = METRIC_TRANSLATION_MAP.get(platform, {})
    # Build reverse map: native → generic
    reverse_map: dict[str, str] = {}
    for generic, native in platform_map.items():
        if native is not None:
            reverse_map[native] = generic

    result: dict[str, Any] = {}
    for native_name, value in native_metrics.items():
        generic_name = reverse_map.get(native_name, native_name)

        # Apply unit conversion if needed
        if value is not None:
            divisor = UNIT_CONVERSIONS.get((platform, native_name))
            if divisor is not None:
                try:
                    value = float(value) / divisor
                except (ValueError, TypeError):
                    pass

        result[generic_name] = value

    return result


def validate_metrics(
    platform: str, generic_metrics: list[str]
) -> tuple[list[str], list[dict[str, str]]]:
    """
    Validate which generic metrics are supported on a platform.

    Returns:
        (valid_native_metrics, errors)
        - valid_native_metrics: list of native metric names that are valid
        - errors: list of dicts with 'metric' and 'message' for unsupported ones
    """
    platform_map = METRIC_TRANSLATION_MAP.get(platform)
    if platform_map is None:
        return (
            list(generic_metrics),
            [{"metric": "all", "message": f"No translation map for platform '{platform}'. Metrics will be passed as-is."}],
        )

    valid: list[str] = []
    errors: list[dict[str, str]] = []
    for m in generic_metrics:
        if m in platform_map:
            native = platform_map[m]
            if native is None:
                errors.append({
                    "metric": m,
                    "message": f"Metric '{m}' is not supported on platform '{platform}'.",
                })
            else:
                valid.append(native)
        else:
            # Unknown generic metric — pass through (might be a native name)
            valid.append(m)

    return valid, errors


def get_supported_generic_metrics(platform: str) -> list[str]:
    """Return the list of generic metric names supported on this platform."""
    platform_map = METRIC_TRANSLATION_MAP.get(platform, {})
    return [generic for generic, native in platform_map.items() if native is not None]


def get_metric_compatibility_table() -> dict[str, dict[str, str | None]]:
    """
    Build a cross-platform metric compatibility table.

    Returns:
        {generic_metric: {platform: native_name_or_None}}
    """
    # Collect all generic metric names
    all_generics: set[str] = set()
    for platform_map in METRIC_TRANSLATION_MAP.values():
        all_generics.update(platform_map.keys())

    table: dict[str, dict[str, str | None]] = {}
    for generic in sorted(all_generics):
        table[generic] = {}
        for platform in METRIC_TRANSLATION_MAP:
            table[generic][platform] = METRIC_TRANSLATION_MAP[platform].get(generic)

    return table


def validate_platform_params(
    platform: str,
    account_id: str,
    post_id: str | None = None,
    video_id: str | None = None,
    app_id: str | None = None,
) -> list[str]:
    """
    Validate platform-specific parameters (account_id format and presence of optional parameters).

    Returns a list of error strings (empty if valid).
    """
    import re
    errors: list[str] = []

    # 1. Allowed optional parameters mapping
    allowed_params = {
        "meta_ads": {"post_id"},  # Allowed post_id for ads creative comments/targets
        "meta_organic": {"post_id"},
        "google_ads": set(),
        "ga4": set(),
        "tiktok_ads": set(),
        "tiktok_organic": {"video_id"},
        "linkedin_ads": set(),
        "linkedin_organic": {"post_id"},
        "x_ads": set(),
        "x_organic": {"post_id"},
        "youtube": {"video_id"},
        "google_play": {"app_id"},
        "apple_app_store": {"app_id"},
        "apple_ads": set(),
        "threads": {"post_id"},
    }

    supported = allowed_params.get(platform, set())

    # Check for invalid parameters (preventing silent errors)
    if post_id and "post_id" not in supported:
        errors.append(f"El parámetro 'post_id' no es válido para la plataforma {platform}")
    if video_id and "video_id" not in supported:
        errors.append(f"El parámetro 'video_id' no es válido para la plataforma {platform}")
    if app_id and "app_id" not in supported:
        errors.append(f"El parámetro 'app_id' no es válido para la plataforma {platform}")

    # 2. account_id format validation
    if account_id:
        if platform == "meta_ads":
            if not re.match(r"^(act_)?\d+$", account_id):
                errors.append("El formato de account_id para meta_ads debe ser 'act_xxxxxxxxxxxxx' o un número de cuenta.")
        elif platform == "google_ads":
            clean_acc = account_id.replace("-", "")
            if not re.match(r"^\d{10}$", clean_acc):
                errors.append("El formato de account_id para google_ads debe ser de 10 dígitos (ej. 123-456-7890 o 1234567890).")
        elif platform == "tiktok_ads":
            if not re.match(r"^\d+$", account_id):
                errors.append("El formato de account_id para tiktok_ads debe ser un identificador numérico.")
        elif platform == "ga4":
            if not re.match(r"^(properties/)?\d+$", account_id):
                errors.append("El formato de account_id para ga4 debe ser 'properties/xxxxxxxxx' o un número de propiedad.")
        elif platform == "apple_app_store":
            if not re.match(r"^\d+$", account_id):
                errors.append("El formato de account_id para apple_app_store debe ser un ID numérico de aplicación.")
        elif platform == "google_play":
            if not re.match(r"^[a-zA-Z0-9_]+(\.[a-zA-Z0-9_]+)+$", account_id):
                errors.append("El formato de account_id para google_play debe ser el package name de la app (ej. com.example.app).")

    return errors

