import re
import json
from copy import deepcopy
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

from dashboard.config import (
    DEFAULT_API_URL,
    CAMPAIGN_DATA_TIMEOUT,
    META_PUBLISHER_LABELS
)
from dashboard.utils import (
    extract_metric,
    translate_dimension_value,
    clean_campaign_name,
    meta_base_campaign_name
)


@st.cache_data(ttl=60, show_spinner=False)
def fetch_connections_from_api(platform_key, client_id, api_key):
    try:
        url = f"{DEFAULT_API_URL}/api/v1/oauth/connections"
        headers = {
            "accept": "*/*",
            "x-api-key": api_key,
            "origin": "https://inhaus-marketing-api.web.app",
            "referer": "https://inhaus-marketing-api.web.app/",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        }
        params = {"platform": platform_key, "client_id": client_id}
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            connections = res.json()
            if connections or not client_id or client_id == "client_1":
                return connections
            params = {"platform": platform_key}
            res = requests.get(url, headers=headers, params=params, timeout=10)
            if res.status_code == 200:
                return res.json()
        return []
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_schema_from_api(platform_key, api_key):
    try:
        url = f"{DEFAULT_API_URL}/api/v1/schema/{platform_key}"
        headers = {
            "accept": "*/*",
            "x-api-key": api_key,
            "origin": "https://inhaus-marketing-api.web.app",
            "referer": "https://inhaus-marketing-api.web.app/"
        }
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            schema = res.json()
            metrics = schema.get("metrics", [])
            dimensions = schema.get("dimensions", [])

            # Normalize to list of dicts with name
            norm_metrics = []
            for m in metrics:
                if isinstance(m, dict):
                    norm_metrics.append({"name": m.get("name", ""), "description": m.get("description", "")})
                else:
                    norm_metrics.append({"name": str(m), "description": ""})

            norm_dimensions = []
            for d in dimensions:
                if isinstance(d, dict):
                    norm_dimensions.append({"name": d.get("name", ""), "description": d.get("description", "")})
                else:
                    norm_dimensions.append({"name": str(d), "description": ""})

            return {"metrics": norm_metrics, "dimensions": norm_dimensions}
        return {"metrics": [], "dimensions": []}
    except Exception:
        return {"metrics": [], "dimensions": []}


@st.cache_data(ttl=120, show_spinner=False)
def fetch_campaign_data_from_api(platform_key, client_id, user_id, account_id, start_date, end_date, metrics, dimensions, opt_filters, write_to_bq, api_key, show_errors=True, timeout=CAMPAIGN_DATA_TIMEOUT):
    url = f"{DEFAULT_API_URL}/api/v1/campaign-data"
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
    }
    payload = {
        "platform": platform_key,
        "client_id": client_id,
        "user_id": user_id,
        "account_id": account_id,
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "metrics": metrics
    }
    if dimensions:
        payload["dimensions"] = dimensions
    if write_to_bq:
        payload["write_to_bq"] = True

    # Append optional platform specific filters
    payload.update(opt_filters)

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=timeout)
        if res.status_code == 200:
            return res.json().get("data", [])
        else:
            if show_errors:
                st.error(f"Error de API ({res.status_code}): {res.text}")
            return []
    except Exception as e:
        if show_errors:
            st.error(f"Error de conexión con la API: {e}")
        return []


def _meta_proxy_get(client_id, account_id, api_key, path, params, timeout=30):
    return requests.post(
        f"{DEFAULT_API_URL}/api/v1/meta-proxy",
        headers={
            "accept": "*/*",
            "content-type": "application/json",
            "x-api-key": api_key,
            "origin": "https://inhaus-marketing-api.web.app",
            "referer": "https://inhaus-marketing-api.web.app/",
        },
        json={
            "client_id": client_id,
            "account_id": account_id,
            "path": path,
            "method": "GET",
            "params": params,
        },
        timeout=timeout,
    )


def _meta_indicator_value(entries, indicator):
    for entry in entries or []:
        if indicator and str(entry.get("indicator") or "") != indicator:
            continue
        values = entry.get("values") or []
        if values and isinstance(values, list) and len(values) > 0:
            try:
                first = values[0]
                val = first.get("value") if isinstance(first, dict) else first
                if val is not None:
                    return float(val)
            except (KeyError, TypeError, ValueError):
                pass
        if "value" in entry and entry["value"] is not None:
            try:
                return float(entry["value"])
            except (TypeError, ValueError):
                pass
    if indicator and entries:
        return _meta_indicator_value(entries, "")
    return None


def _meta_minor_currency(value):
    if value in (None, ""):
        return None
    try:
        return float(value) / 100
    except (TypeError, ValueError):
        return None


@st.cache_data(ttl=300, show_spinner=False)
def fetch_meta_aggregate_insights(
    client_id,
    account_id,
    start_date,
    end_date,
    level,
    api_filters,
    api_key,
):
    account_edge = account_id if str(account_id).startswith("act_") else f"act_{account_id}"
    fields = ["impressions", "reach", "results", "cost_per_result"]
    if level in ("campaign", "adset", "ad"):
        fields += ["campaign_id", "campaign_name"]
    if level in ("adset", "ad"):
        fields += ["adset_id", "adset_name"]
    if level == "ad":
        fields += ["ad_id", "ad_name", "actions"]

    params = {
        "fields": ",".join(fields),
        "level": level,
        "time_range": json.dumps({
            "since": start_date.isoformat(),
            "until": end_date.isoformat(),
        }),
        "limit": 500,
    }
    if api_filters:
        params["filtering"] = json.dumps([
            {
                "field": field,
                "operator": "IN" if isinstance(value, list) else "EQUAL",
                "value": value if isinstance(value, list) else [value],
            }
            for field, value in api_filters.items()
        ])

    rows = []
    seen_cursors = set()
    try:
        while True:
            response = _meta_proxy_get(
                client_id,
                account_id,
                api_key,
                f"{account_edge}/insights",
                params,
            )
            if response.status_code != 200:
                return [], f"No se pudieron cargar insights Meta ({response.status_code})."

            payload = response.json()
            for insight in payload.get("data", []):
                actions = insight.get("actions") or []
                result_entries = insight.get("results") or []
                result_indicator = (
                    str(result_entries[0].get("indicator") or "")
                    if result_entries else ""
                )
                result_value = _meta_indicator_value(result_entries, result_indicator)
                result_cost = _meta_indicator_value(
                    insight.get("cost_per_result"), result_indicator
                )
                rows.append({
                    "campaign_id": insight.get("campaign_id") or "",
                    "campaign_name": insight.get("campaign_name") or "",
                    "adset_id": insight.get("adset_id") or "",
                    "adset_name": insight.get("adset_name") or "",
                    "ad_id": insight.get("ad_id") or "",
                    "ad_name": insight.get("ad_name") or "",
                    "impressions": extract_metric(insight, ["impressions"]),
                    "reach": extract_metric(insight, ["reach"]),
                    "result_indicator": result_indicator,
                    "results": result_value,
                    "cost_per_result": result_cost,
                    "lead": sum(
                        extract_metric(action, ["value"])
                        for action in actions
                        if action.get("action_type") in {
                            "lead",
                            "onsite_conversion.lead_grouped",
                            "offsite_conversion.fb_pixel_lead",
                        }
                    ),
                    "post_engagement": sum(
                        extract_metric(action, ["value"])
                        for action in actions
                        if action.get("action_type") == "post_engagement"
                    ),
                })

            after = (payload.get("paging") or {}).get("cursors", {}).get("after")
            if not after or after in seen_cursors:
                break
            seen_cursors.add(after)
            params["after"] = after
        return rows, None
    except Exception as e:
        return [], f"Error cargando insights Meta: {e}"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_meta_ad_previews(client_id, account_id, preview_targets, api_key):
    targets = tuple(target for target in preview_targets if target[2])
    if not targets:
        return [], None

    hydrated_ads = {}
    previews = []
    try:
        for ranking_metric, campaign_name, ad_id, fallback_ad_name in targets:
            if ad_id not in hydrated_ads:
                ad_response = _meta_proxy_get(
                    client_id,
                    account_id,
                    api_key,
                    str(ad_id),
                    {
                        "fields": (
                            "id,name,campaign{id,name},"
                            "creative{effective_object_story_id,object_story_spec}"
                        )
                    },
                )
                if ad_response.status_code != 200:
                    continue
                ad = ad_response.json()

                preview_response = _meta_proxy_get(
                    client_id,
                    account_id,
                    api_key,
                    f"{ad_id}/previews",
                    {"ad_format": "DESKTOP_FEED_STANDARD"},
                )
                preview_data = (
                    preview_response.json().get("data", [])
                    if preview_response.status_code == 200
                    else []
                )
                body = preview_data[0].get("body", "") if preview_data else ""

                creative = ad.get("creative") or {}
                story = creative.get("object_story_spec") or {}
                post_text = " ".join(filter(None, (
                    story.get("message"),
                    (story.get("link_data") or {}).get("message"),
                    (story.get("video_data") or {}).get("message"),
                )))
                post_id = creative.get("effective_object_story_id")
                if post_id:
                    post_response = _meta_proxy_get(
                        client_id,
                        account_id,
                        api_key,
                        post_id,
                        {"fields": "message,story,caption,created_time"},
                        timeout=20,
                    )
                    if post_response.status_code == 200:
                        post = post_response.json()
                        post_text = " ".join(filter(None, (
                            post_text,
                            post.get("message"),
                            post.get("story"),
                            post.get("caption"),
                        )))

                hydrated_ads[ad_id] = {
                    "ad_name": ad.get("name") or fallback_ad_name or "",
                    "body": body,
                    "post_message": post_text,
                }

            hydrated = hydrated_ads[ad_id]
            previews.append({
                "ranking_metric": ranking_metric,
                "campaign_name": campaign_name,
                "campaign_label": clean_campaign_name(campaign_name),
                "ad_id": ad_id,
                **hydrated,
            })

        return previews, None if previews else "No se encontraron previews para los anuncios seleccionados."
    except Exception as e:
        return [], f"Error cargando previews Meta: {e}"


@st.cache_data(ttl=300, show_spinner=False)
def fetch_meta_filter_rows(client_id, account_id, api_key):
    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/",
    }
    url = f"{DEFAULT_API_URL}/api/v1/meta-proxy"
    account_edge = account_id if str(account_id).startswith("act_") else f"act_{account_id}"
    rows = []
    after = None
    try:
        # ponytail: cap option hydration at 5 pages; paginate more if accounts exceed ~2500 ads.
        for _ in range(5):
            params = {
                "fields": (
                    "id,name,"
                    "campaign{id,name,daily_budget,lifetime_budget},"
                    "adset{id,name,daily_budget,lifetime_budget}"
                ),
                "limit": 500,
            }
            if after:
                params["after"] = after
            res = requests.post(url, headers=headers, json={
                "client_id": client_id,
                "account_id": account_id,
                "path": f"{account_edge}/ads",
                "method": "GET",
                "params": params,
            }, timeout=30)
            if res.status_code != 200:
                return [], f"No se pudieron cargar filtros Meta ({res.status_code})."
            body = res.json()
            for ad in body.get("data", []):
                campaign = ad.get("campaign") or {}
                adset = ad.get("adset") or {}
                if campaign.get("name"):
                    rows.append({
                        "campaign_id": campaign.get("id", ""),
                        "campaign_name": campaign.get("name", ""),
                        "adset_id": adset.get("id", ""),
                        "adset_name": adset.get("name", ""),
                        "ad_id": ad.get("id", ""),
                        "ad_name": ad.get("name", ""),
                        "campaign_daily_budget": _meta_minor_currency(
                            campaign.get("daily_budget")
                        ),
                        "campaign_lifetime_budget": _meta_minor_currency(
                            campaign.get("lifetime_budget")
                        ),
                        "adset_daily_budget": _meta_minor_currency(
                            adset.get("daily_budget")
                        ),
                        "adset_lifetime_budget": _meta_minor_currency(
                            adset.get("lifetime_budget")
                        ),
                    })
            paging = body.get("paging", {})
            after = (paging.get("cursors") or {}).get("after")
            if not after or not paging.get("next"):
                break
        return rows, None
    except Exception as e:
        return [], f"Error cargando filtros Meta: {e}"


def process_api_response(api_data, platform_key, client_id, user_id):
    flat_rows = []
    for item in api_data:
        metrics = item.get("metrics", {})

        spend = extract_metric(metrics, ["spend", "social_spend", "cost"])
        impressions = extract_metric(metrics, ["impressions", "views", "reach"])
        clicks = extract_metric(metrics, ["clicks", "unique_clicks"])
        conversions = extract_metric(metrics, ["conversions", "actions", "purchase", "lead", "add_to_cart"])
        leads = extract_metric(metrics, ["lead"])
        post_engagement = extract_metric(metrics, ["post_engagement"])
        results = extract_metric(metrics, ["__results__", "results"])
        cost_per_result = extract_metric(metrics, ["cost_per_result"])
        if results > 0 and not cost_per_result:
            cost_per_result = spend / results
        result_indicator = str(metrics.get("result_indicator") or "")

        sessions = extract_metric(metrics, ["sessions"])
        users = extract_metric(metrics, ["users"])
        pageviews = extract_metric(metrics, ["pageviews"])
        bounce_rate = extract_metric(metrics, ["bounce_rate"])

        downloads = extract_metric(metrics, ["downloads"])
        ratings = extract_metric(metrics, ["ratings"])

        likes = extract_metric(metrics, ["likes", "like_count"])
        comments = extract_metric(metrics, ["comments", "comment_count"])
        engagement = extract_metric(metrics, ["engagement", "total_interactions", "accounts_engaged"])
        if not engagement:
            engagement = likes + comments + extract_metric(metrics, ["shares", "saved"])
        followers = extract_metric(metrics, ["followers"])
        reach = extract_metric(metrics, ["reach", "impressions", "views"])

        # Include dynamic fields from dimensions if present
        row = {
            "platform": platform_key,
            "source_platform": platform_key,
            "source_metrics": deepcopy(metrics),
            "client_id": client_id,
            "user_id": user_id,
            "campaign_name": item.get("campaign_name", "N/A"),
            "date": pd.to_datetime(item.get("date", datetime.now())),
            "spend": spend,
            "impressions": int(impressions),
            "clicks": int(clicks),
            "conversions": int(conversions),
            "lead": int(leads),
            "post_engagement": int(post_engagement),
            "results": int(results),
            "cost_per_result": cost_per_result,
            "result_indicator": result_indicator,
            "sessions": int(sessions),
            "users": int(users),
            "pageviews": int(pageviews),
            "bounce_rate": bounce_rate,
            "downloads": int(downloads),
            "ratings": ratings,
            "engagement": int(engagement),
            "followers": int(followers),
            "reach": int(reach),
            "likes": int(likes),
            "comments": int(comments),
        }
        # Add dimensions to the row dict dynamically
        protected_source_fields = {"source_platform", "source_metrics"}
        for key, val in item.get("dimensions", {}).items():
            if key not in protected_source_fields:
                row[key] = translate_dimension_value(key, val)

        for key, val in item.items():
            if key not in {"metrics", "dimensions", "platform", "client_id", "user_id", *protected_source_fields}:
                row[key] = translate_dimension_value(key, val)

        if platform_key == "meta_ads":
            publisher = str(row.get("publisher_platform", "")).lower()
            if not publisher:
                match = re.search(r"_(facebook|instagram|audience_network|messenger)$", str(row["campaign_name"]), re.I)
                publisher = match.group(1).lower() if match else ""
            if publisher:
                row["platform"] = META_PUBLISHER_LABELS.get(publisher, publisher.replace("_", " ").title())

        flat_rows.append(row)

    df = pd.DataFrame(flat_rows)
    if df.empty:
        return pd.DataFrame(columns=[
            "platform", "source_platform", "source_metrics", "client_id", "user_id", "campaign_name", "date", "spend", "impressions", "clicks", "conversions", "lead", "results", "cost_per_result", "result_indicator",
            "sessions", "users", "pageviews", "bounce_rate", "downloads", "ratings", "engagement", "post_engagement", "followers", "reach", "likes", "comments"
        ])
    return df
