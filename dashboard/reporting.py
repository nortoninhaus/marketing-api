"""Build account-scoped data for standalone dashboard reports."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from numbers import Number
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from dashboard.api import fetch_campaign_data_from_api, process_api_response


_TEMPLATE_DIR = Path(__file__).with_name("report_templates")
_TEMPLATE_FILES = {
    "nutri": "nutri.html",
    "adriana_hoyos": "adriana_hoyos.html",
    "artz": "artz.html",
    "shamuna": "shamuna.html",
}
_DATA_MARKER = "<!-- REPORT_DATA -->"
_REFERENCE_IDENTITIES = ("nutri", "adriana hoyos", "artz", "shamuna")
_ASSET_HOSTS = frozenset()
_SENSITIVE_KEYS = {
    "api_key", "authorization", "client_id", "client_secret", "credential", "credentials",
    "password", "refresh_token", "secret", "token", "user_id",
}
_CANONICAL_ALIASES = {
    "clicks": {"clicks", "unique_clicks"},
    "conversions": {"actions", "add_to_cart", "conversions", "lead", "purchase"},
    "engagement": {"accounts_engaged", "comments", "engagement", "likes", "saved", "shares", "total_interactions"},
    "impressions": {"impressions", "reach", "views"},
    "likes": {"like_count", "likes"},
    "comments": {"comment_count", "comments"},
    "reach": {"impressions", "reach", "views"},
    "results": {"__results__", "results"},
    "spend": {"cost", "social_spend", "spend"},
}


def _sensitive_key(key: Any) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(key).casefold()).strip("_")
    return (
        normalized in _SENSITIVE_KEYS
        or normalized.endswith(("_api_key", "_password", "_secret", "_token"))
    )


def _json_value(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
            if not _sensitive_key(key)
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    try:
        return None if pd.isna(value) else value
    except (TypeError, ValueError):
        return value


def _records(
    frame: pd.DataFrame | None,
    supplied_metrics: set[str] | None = None,
) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    records = [_json_value(row) for row in frame.to_dict("records")]
    if supplied_metrics is not None:
        for row in records:
            if "source_metrics" not in row:
                row["source_metrics"] = {
                    metric: row[metric]
                    for metric in supplied_metrics
                    if metric in row and not _sensitive_key(metric)
                }
    return records


def safe_asset_url(url: str, allowed_hosts: set[str] | frozenset[str] = _ASSET_HOSTS) -> str | None:
    """Return an HTTPS URL only when its exact hostname is explicitly trusted."""
    try:
        parsed = urlparse(str(url))
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    trusted = {allowed.lower() for allowed in allowed_hosts}
    if parsed.scheme != "https" or not host or host not in trusted or parsed.username or parsed.password:
        return None
    return str(url)


def _safe_json(payload: dict[str, Any]) -> str:
    return (
        json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":"), default=_json_value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _load_template(template_name: str) -> str:
    filename = _TEMPLATE_FILES.get(template_name)
    if not filename:
        raise ValueError(f"Unknown report template: {template_name}")
    base = _TEMPLATE_DIR.resolve()
    path = (_TEMPLATE_DIR / filename).resolve()
    if path.parent != base:
        raise ValueError("Report template path is outside the allowlisted directory")
    source = path.read_text(encoding="utf-8")
    if source.count(_DATA_MARKER) != 1:
        raise ValueError("Report template must contain exactly one data marker")
    lowered = source.casefold()
    if any(re.search(rf"\b{re.escape(identity)}\b", lowered) for identity in _REFERENCE_IDENTITIES):
        raise ValueError("Report template contains reference-client content")
    asset_urls = re.findall(r"\b(?:src|href)\s*=\s*['\"]([^'\"]+)['\"]", source, re.I)
    asset_urls += re.findall(r"\burl\(\s*['\"]?([^)'\"]+)", source, re.I)
    for url in asset_urls:
        if not url.startswith("#") and safe_asset_url(url) is None:
            raise ValueError("Report template contains an unsafe asset URL")
    return source


def render_report(template_name: str, payload: dict[str, Any]) -> str:
    """Load one allowlisted template and inject a single inert JSON payload."""
    bootstrap = f'''<script id="report-data" type="application/json">{_safe_json(payload)}</script>
<script>
(() => {{
  window.REPORT_DATA = JSON.parse(document.getElementById("report-data").textContent);
  window.reportText = (element, value) => {{ if (element) element.textContent = value == null ? "" : String(value); }};
  window.reportNumbers = values => (Array.isArray(values) ? values : []).map(Number).filter(Number.isFinite);
}})();
</script>'''
    return _load_template(template_name).replace(_DATA_MARKER, bootstrap)


def _metric_value(row: dict[str, Any], metric: str) -> tuple[bool, Number | None]:
    source_metrics = row.get("source_metrics")
    if isinstance(source_metrics, dict):
        value = source_metrics.get(metric)
        if isinstance(value, Number) and not isinstance(value, bool):
            return True, value
        aliases = _CANONICAL_ALIASES.get(metric, {metric})
        if not any(alias in source_metrics for alias in aliases):
            return False, None
        value = row.get(metric)
    elif metric in row:
        value = row[metric]
    else:
        return False, None
    return isinstance(value, Number) and not isinstance(value, bool), value


def _metric_names(*record_groups: list[dict[str, Any]]) -> list[str]:
    names: set[str] = set()
    for records in record_groups:
        for row in records:
            source_metrics = row.get("source_metrics")
            if isinstance(source_metrics, dict):
                names.update(source_metrics)
            else:
                names.update(
                    key for key, value in row.items()
                    if isinstance(value, Number) and not isinstance(value, bool)
                )
    return sorted(names)


def _summarize(records: list[dict[str, Any]], metrics: list[str]) -> tuple[dict[str, Number], dict[str, bool]]:
    summary: dict[str, Number] = {}
    availability: dict[str, bool] = {}
    for metric in metrics:
        values = [value for row in records for present, value in [_metric_value(row, metric)] if present]
        availability[metric] = bool(values)
        if values:
            summary[metric] = sum(value for value in values if value is not None)
    return summary, availability


def _account_meta(query_context: dict[str, Any]) -> tuple[list[dict[str, str]], str]:
    accounts = []
    for connection in query_context.get("connections", []):
        platform = str(connection.get("platform") or connection.get("platform_key") or "account")
        account_id = str(connection.get("account_id") or "unknown")
        name = next(
            (str(connection[key]) for key in ("account_name", "name", "display_name") if connection.get(key)),
            f"{platform.replace('_', ' ').title()} account {account_id}",
        )
        accounts.append({"account_id": account_id, "name": name, "platform": platform})
    distinct_names = list(dict.fromkeys(account["name"] for account in accounts))
    return accounts, " + ".join(distinct_names) if distinct_names else "Selected account"


def _period(query_context: dict[str, Any], prefix: str = "") -> dict[str, str | None]:
    start = query_context.get(f"{prefix}start_date")
    end = query_context.get(f"{prefix}end_date")
    return {"start": _json_value(start), "end": _json_value(end)}


def _normalize_platform(p: Any) -> str:
    s = str(p or "").strip().lower()
    if "meta" in s or "facebook" in s or "instagram" in s:
        return "meta_ads"
    if "analytics" in s or "ga4" in s:
        return "google_analytics"
    if "google" in s:
        return "google_ads"
    if "tiktok" in s:
        return "tiktok"
    if "pinterest" in s:
        return "pinterest_ads"
    if "linkedin" in s:
        return "linkedin_ads"
    return s.replace(" ", "_")


def _platform_rows(records: list[dict[str, Any]], platform: str) -> list[dict[str, Any]]:
    norm_target = _normalize_platform(platform)
    scoped = [
        row for row in records
        if _normalize_platform(row.get("source_platform") or row.get("platform") or "") == norm_target
        or str(row.get("source_platform") or row.get("platform") or "") == platform
    ]
    if scoped:
        return scoped
    if all(not (row.get("source_platform") or row.get("platform")) for row in records):
        return records
    return []


def _metric_available(records: list[dict[str, Any]], metric: str) -> bool:
    return _summarize(records, [metric])[1][metric]


def _select_scoped_summaries(
    metrics: list[str],
    platforms: list[str],
    current: list[dict[str, Any]],
    export: list[dict[str, Any]],
    supplemental: list[dict[str, Any]],
) -> tuple[dict[str, Number], dict[str, bool], dict[str, dict[str, Number]]]:
    summary: dict[str, Number] = {}
    availability: dict[str, bool] = {}
    by_platform: dict[str, dict[str, Number]] = {platform: {} for platform in platforms}
    unscoped_export = [row for row in export if not (row.get("source_platform") or row.get("platform"))]

    for metric in metrics:
        if not _metric_available(current, metric) and _metric_available(unscoped_export, metric):
            summary[metric] = _summarize(unscoped_export, [metric])[0][metric]
            availability[metric] = True
            continue
        total: Number = 0
        found = False
        for platform in platforms:
            for records in (
                _platform_rows(current, platform),
                _platform_rows(export, platform),
                _platform_rows(supplemental, platform),
            ):
                value, available = _summarize(records, [metric])
                if available[metric]:
                    by_platform[platform][metric] = value[metric]
                    total += value[metric]
                    found = True
                    break
        if not found:
            for records in (current, export, supplemental):
                value, available = _summarize(records, [metric])
                if available[metric]:
                    total = value[metric]
                    found = True
                    if platforms:
                        by_platform[platforms[0]][metric] = total
                    break
        availability[metric] = found
        if found:
            summary[metric] = total
    return summary, availability, {platform: values for platform, values in by_platform.items() if values}


def _deltas(current: dict[str, Number], previous: dict[str, Number]) -> dict[str, float | None]:
    return {
        metric: None if previous.get(metric) in (None, 0) else round((value - previous[metric]) / previous[metric] * 100, 4)
        for metric, value in current.items()
    }


def _rate(numerator: Number | None, denominator: Number | None, factor: int = 1) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    return round(numerator / denominator * factor, 4)


def _rates(summary: dict[str, Number]) -> dict[str, float]:
    candidates = {
        "conversion_rate": _rate(summary.get("conversions"), summary.get("clicks"), 100),
        "cpa": _rate(summary.get("spend"), summary.get("conversions")),
        "cpc": _rate(summary.get("spend"), summary.get("clicks")),
        "cpm": _rate(summary.get("spend"), summary.get("impressions"), 1000),
        "ctr": _rate(summary.get("clicks"), summary.get("impressions"), 100),
    }
    return {name: value for name, value in candidates.items() if value is not None}


def _daily_series(
    metrics: list[str],
    *record_groups: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str], dict[str, Number]] = {}
    for records in record_groups:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in records:
            if not row.get("date"):
                continue
            platform = str(row.get("source_platform") or row.get("platform") or "unscoped")
            day = pd.to_datetime(row["date"]).isoformat()
            grouped.setdefault((day, platform), []).append(row)
        for key, rows in grouped.items():
            for metric, value in _summarize(rows, metrics)[0].items():
                selected.setdefault(key, {}).setdefault(metric, value)
    return [
        {"date": day, "platform": platform, "metrics": values}
        for (day, platform), values in sorted(selected.items())
        if values
    ]


def _narratives(company_name: str, summary: dict[str, Number], period: dict[str, str | None]) -> list[str]:
    if "impressions" not in summary or not period["start"] or not period["end"]:
        return []
    return [
        f"{company_name} recorded {summary['impressions']:g} impressions during "
        f"{period['start']} to {period['end']}."
    ]


def _supported_metrics(config: dict[str, Any]) -> set[str]:
    return {
        str(metric.get("name") if isinstance(metric, dict) else metric)
        for metric in config.get("metrics_list", [])
    }


def _fetch_supplemental(
    metrics: list[str],
    current_rows: list[dict[str, Any]],
    export_rows: list[dict[str, Any]],
    query_context: dict[str, Any],
    client_id: str,
    user_id: str,
    api_key: str,
) -> list[dict[str, Any]]:
    if not all((client_id, user_id, api_key, query_context.get("start_date"), query_context.get("end_date"))):
        return []
    unscoped_export = [row for row in export_rows if not (row.get("source_platform") or row.get("platform"))]
    supplemental: list[dict[str, Any]] = []
    for config in query_context.get("platform_configs", []):
        platform = str(config["platform_key"])
        current_platform = _platform_rows(current_rows, platform)
        export_platform = _platform_rows(export_rows, platform)
        requested = sorted(
            metric
            for metric in set(metrics) & _supported_metrics(config)
            if not _metric_available(current_platform, metric)
            and not _metric_available(export_platform, metric)
            and not (not _metric_available(current_rows, metric) and _metric_available(unscoped_export, metric))
        )
        if not requested:
            continue
        try:
            raw_rows = fetch_campaign_data_from_api(
                config["platform_key"],
                client_id,
                user_id,
                config["account_id"],
                query_context["start_date"],
                query_context["end_date"],
                requested,
                [],
                config.get("opt_filters", {}),
                False,
                api_key,
                show_errors=False,
            )
            supplemental.extend(_records(process_api_response(raw_rows, config["platform_key"], client_id, user_id)))
        except Exception:
            continue
    return supplemental


def build_report_payload(
    template_name: str,
    current: pd.DataFrame,
    previous: pd.DataFrame | None = None,
    export_table: pd.DataFrame | None = None,
    query_context: dict[str, Any] | None = None,
    optional: dict[str, Any] | None = None,
    client_id: str = "",
    user_id: str = "",
    api_key: str = "",
) -> dict[str, Any]:
    """Normalize dashboard state without leaking credentials into the report."""
    query_context = query_context or {}
    current_rows = _records(current)
    previous_rows = _records(previous)
    export_supplied_metrics = {
        metric for metric in query_context.get("export_supplied_metrics", [])
        if not _sensitive_key(metric)
    }
    if export_table is not None:
        export_supplied_metrics.update(
            metric for metric in export_table.attrs.get("supplied_metrics", [])
            if not _sensitive_key(metric)
        )
    export_rows = _records(export_table, export_supplied_metrics)
    template_requirements = query_context.get("required_metrics_by_template", {})
    required_metrics = [
        metric
        for metric in template_requirements.get(template_name, query_context.get("required_metrics", []))
        if not _sensitive_key(metric)
    ]
    metrics = sorted(set(_metric_names(current_rows, previous_rows, export_rows)) | set(required_metrics))
    supplemental_rows = _fetch_supplemental(
        metrics,
        current_rows,
        export_rows,
        query_context,
        client_id,
        user_id,
        api_key,
    )
    summary_previous, _ = _summarize(previous_rows, metrics)
    accounts, company_name = _account_meta(query_context)
    platforms = list(dict.fromkeys(
        [account["platform"] for account in accounts]
        + [str(row.get("source_platform") or row.get("platform")) for row in current_rows if row.get("source_platform") or row.get("platform")]
    ))
    summary, metric_availability, by_platform = _select_scoped_summaries(
        metrics, platforms, current_rows, export_rows, supplemental_rows
    )
    period = _period(query_context)
    daily_series = _daily_series(metrics, current_rows, export_rows, supplemental_rows)
    daily_series_metrics = {
        metric: any(metric in item["metrics"] for item in daily_series)
        for metric in metrics
    }
    narratives = _narratives(company_name, summary, period)
    breakdowns = _json_value((optional or {}).get("breakdowns", {}))

    return {
        "meta": {
            "company_name": company_name,
            "accounts": accounts,
            "platforms": platforms,
            "filters": _json_value(query_context.get("filters", {})),
            "period": period,
            "previous_period": _period(query_context, "previous_"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
        "rows": {"current": current_rows, "prior": previous_rows, "supplemental": supplemental_rows},
        "summary": summary,
        "summary_previous": summary_previous,
        "rates": _rates(summary),
        "deltas": _deltas(summary, summary_previous),
        "by_platform": by_platform,
        "daily_series": daily_series,
        "breakdowns": breakdowns,
        "tables": {"export": export_rows},
        "narratives": narratives,
        "availability": {
            "metrics": metric_availability,
            "summary": bool(summary),
            "daily_series": bool(daily_series),
            "daily_series_metrics": daily_series_metrics,
            "breakdowns": bool(breakdowns),
            "export_table": bool(export_rows),
            "narratives": bool(narratives),
        },
    }
