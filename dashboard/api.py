import re
import json
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


# Meta ad previews through the existing backend proxy
@st.cache_data(ttl=300, show_spinner=False)
def fetch_meta_campaign_previews(client_id, account_id, campaign_names, api_key):
    campaign_names = tuple(name for name in campaign_names if name and name != "N/A")
    if not campaign_names:
        return [], None

    headers = {
        "accept": "*/*",
        "content-type": "application/json",
        "x-api-key": api_key,
        "origin": "https://inhaus-marketing-api.web.app",
        "referer": "https://inhaus-marketing-api.web.app/",
    }
    url = f"{DEFAULT_API_URL}/api/v1/meta-proxy"
    account_edge = account_id if str(account_id).startswith("act_") else f"act_{account_id}"

    def meta_get(path, params, timeout=30):
        return requests.post(url, headers=headers, json={
            "client_id": client_id,
            "account_id": account_id,
            "path": path,
            "method": "GET",
            "params": params,
        }, timeout=timeout)

    try:
        ads_res = meta_get(f"{account_edge}/ads", {
            "fields": "id,name,campaign{id,name},creative{effective_object_story_id,object_story_spec}",
            "limit": 200,
        })
        if ads_res.status_code != 200:
            return [], f"No se pudieron cargar anuncios Meta ({ads_res.status_code})."

        wanted = set(campaign_names)
        ads_by_campaign = {}
        for ad in ads_res.json().get("data", []):
            campaign_name = (ad.get("campaign") or {}).get("name")
            if campaign_name in wanted and campaign_name not in ads_by_campaign:
                ads_by_campaign[campaign_name] = ad

        previews = []
        for campaign_name in campaign_names:
            ad = ads_by_campaign.get(campaign_name)
            if not ad:
                continue
            preview_res = meta_get(f"{ad['id']}/previews", {"ad_format": "DESKTOP_FEED_STANDARD"}, timeout=20)
            if preview_res.status_code != 200:
                continue
            body = (preview_res.json().get("data") or [{}])[0].get("body")
            creative = ad.get("creative") or {}
            story = creative.get("object_story_spec") or {}
            post_text = " ".join(str(part or "") for part in [
                story.get("message"),
                story.get("link_data", {}).get("message") if isinstance(story.get("link_data"), dict) else "",
                story.get("video_data", {}).get("message") if isinstance(story.get("video_data"), dict) else "",
            ])
            post_id = creative.get("effective_object_story_id")
            if post_id:
                post_res = meta_get(post_id, {"fields": "message,story,caption,created_time"}, timeout=20)
                if post_res.status_code == 200:
                    post_json = post_res.json()
                    post_text = " ".join([post_text, str(post_json.get("message") or ""), str(post_json.get("story") or ""), str(post_json.get("caption") or "")])
            if body:
                previews.append({
                    "campaign_name": campaign_name,
                    "campaign_label": clean_campaign_name(campaign_name),
                    "ad_name": ad.get("name") or "",
                    "body": body,
                    "post_message": post_text,
                })

        return previews, None if previews else "No se encontraron previews para las campañas del resultado."
    except Exception as e:
        return [], f"Error cargando previews Meta: {e}"


# Process the API result list into a pandas dataframe
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
                "fields": "id,name,campaign{id,name},adset{id,name}",
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
            "client_id": client_id,
            "user_id": user_id,
            "campaign_name": item.get("campaign_name", "N/A"),
            "date": pd.to_datetime(item.get("date", datetime.now())),
            "spend": spend,
            "impressions": int(impressions),
            "clicks": int(clicks),
            "conversions": int(conversions),
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
        for key, val in item.get("dimensions", {}).items():
            row[key] = translate_dimension_value(key, val)

        for key, val in item.items():
            if key not in ["metrics", "dimensions", "platform", "client_id", "user_id"]:
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
            "platform", "client_id", "user_id", "campaign_name", "date", "spend", "impressions", "clicks", "conversions",
            "sessions", "users", "pageviews", "bounce_rate", "downloads", "ratings", "engagement", "followers", "reach", "likes", "comments"
        ])
    return df
