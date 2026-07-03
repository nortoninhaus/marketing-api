# ponytail: simple, dynamic marketing dashboard connecting to the API directly with period comparison and custom CSS styling
import streamlit as st
import pandas as pd
import requests
import json
import os
import re
import textwrap
import calendar
import html
import altair as alt
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

# Load env variables for local defaults
load_dotenv()
DEFAULT_API_KEY = os.getenv("API_KEY", "dev-key-change-me")
DEFAULT_API_URL = "https://inhaus-marketing-api-btdf7nijqa-uc.a.run.app"

# Determine sidebar collapse state dynamically to hide it automatically once query runs
initial_sidebar = "collapsed" if st.session_state.get("query_run", False) else "expanded"

# Page config to force wide layout
st.set_page_config(
    page_title="Inhaus Marketing API - Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state=initial_sidebar
)

dark_theme = st.sidebar.toggle("☀️ / 🌙", value=st.session_state.get("theme_mode", "Oscuro") == "Oscuro", key="theme_switch")
theme_mode = "Oscuro" if dark_theme else "Claro"
st.session_state.theme_mode = theme_mode
chart_bg = "#FFFFFF" if theme_mode == "Claro" else "#0A0D13"
text_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
grid_color = "rgba(15,23,42,0.10)" if theme_mode == "Claro" else "rgba(255,255,255,0.05)"

# Custom premium styling matching sipy_dashboard.html
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800&display=swap');

/* Hide Streamlit Deploy button and standard Footer */
div.stAppDeployButton {display: none !important;}
footer {visibility: hidden !important;}

/* Clean up header background and shadow so it's transparent, but keep container
   intact so the sidebar toggle/hamburger button is visible in the top-left */
[data-testid="stHeader"] {
background-color: transparent !important;
box-shadow: none !important;
}
[data-testid="stHeader"] button, [data-testid="stHeader"] svg {
color: #EAF0F7 !important;
fill: #EAF0F7 !important;
stroke: #EAF0F7 !important;
}

/* Hide the 3-dots Menu button specifically */
#MainMenu {visibility: hidden !important;}

/* Main App Wrapper */
.stApp {
    background-color: #0A0D13 !important;
    color: #EAF0F7 !important;
    font-family: 'Manrope', sans-serif !important;
}

/* Remove default Streamlit top padding and container margins */
.block-container {
    padding-top: 1.5rem !important;
    padding-bottom: 2rem !important;
}

/* Sidebar Wrapper */
[data-testid="stSidebar"] {
    background-color: #121823 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Typography Overrides */
h1, h2, h3, .sipy-word {
    font-family: 'Sora', sans-serif !important;
    font-weight: 800 !important;
}

/* Custom Topbar Header styling */
.custom-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 0px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    margin-bottom: 30px;
}
.agency {
    display: flex;
    align-items: center;
    gap: 12px;
}
.agency img {
height: 26px;
width: auto;
}
.agency .div-bar {
    width: 1px;
    height: 22px;
    background: rgba(255,255,255,0.14);
}
.agency .who {
    font-size: 12px;
    color: #8A97A8;
    font-weight: 600;
    letter-spacing: .02em;
}
.stamp {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 12px;
    color: #8A97A8;
    font-weight: 600;
}
.stamp .live {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #1AE08C;
    box-shadow: 0 0 0 0 rgba(26,224,140,0.6);
    animation: pulse 2s infinite;
}
@keyframes pulse {
0% { box-shadow: 0 0 0 0 rgba(26,224,140,0.5); }
70% { box-shadow: 0 0 0 8px rgba(26,224,140,0); }
100% { box-shadow: 0 0 0 0 rgba(26,224,140,0); }
}

.loading-overlay {
position: fixed;
top: 0;
left: 0;
width: 100vw;
height: 100vh;
background-color: rgba(10, 13, 19, 0.95);
z-index: 999999;
display: flex;
flex-direction: column;
align-items: center;
justify-content: center;
}
.loading-text {
font-family: 'Sora', sans-serif;
color: #1AE08C;
font-size: 24px;
margin-top: 20px;
font-weight: 800;
}
.spinner {
border: 6px solid rgba(255, 255, 255, 0.1);
width: 70px;
height: 70px;
border-radius: 50%;
border-left-color: #1AE08C;
animation: spin 1s linear infinite;
}
@keyframes spin {
0% { transform: rotate(0deg); }
100% { transform: rotate(360deg); }
}

/* Brand styling */
.eyebrow {
    font-size: 11px;
    font-weight: 800;
    letter-spacing: .2em;
    text-transform: uppercase;
    color: #1AE08C;
}
.lede {
    color: #8A97A8;
    font-size: 15px;
    max-width: 800px;
    font-weight: 500;
    line-height: 1.5;
    margin-bottom: 20px;
}

/* Goal Card Styling */
.hero-card {
    background: linear-gradient(165deg, #161E2B, #0F1620);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 24px;
    padding: 30px;
    position: relative;
    overflow: hidden;
    margin-bottom: 25px;
}
.hero-card .lab {
    font-size: 12px;
    color: #8A97A8;
    font-weight: 700;
    letter-spacing: .02em;
}
.hero-card .big {
    font-family: 'Sora', sans-serif;
    font-weight: 800;
    font-size: 60px;
    line-height: .9;
    letter-spacing: -.04em;
    margin-top: 6px;
    color: #1AE08C;
}

/* KPI Grid Styling */
.kpis {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 14px;
    margin-top: 10px;
    margin-bottom: 25px;
}
.kpi {
    background: #121823;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    min-height: 140px;
}
.kpi .lab {
    font-size: 12px;
    color: #8A97A8;
    font-weight: 700;
}
.kpi .val {
    font-family: 'Sora', sans-serif;
    font-weight: 800;
    font-size: 28px;
    letter-spacing: -.03em;
    margin-top: 10px;
    color: #EAF0F7;
}
.kpi .sub {
    font-size: 12px;
    color: #5E6A7A;
    font-weight: 600;
    margin-top: 7px;
}

/* Table overrides to fit dark theme */
.stTable {
    background-color: #121823 !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 18px !important;
}

/* Custom dynamic indicators */
.delta {
    display: inline-flex;
    align-items: center;
    gap: 3px;
    font-size: 11px;
    font-weight: 800;
    padding: 3px 8px;
    border-radius: 6px;
    margin-top: 9px;
    width: fit-content;
}
.delta.up {
    background: rgba(26,224,140,0.14);
    color: #1AE08C;
}
.delta.down {
background: rgba(255,107,107,0.14);
color: #FF6B6B;
}
.stApp label, .stApp p, [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"] {
color: #EAF0F7;
}
[data-testid="stDataFrame"] {
background: #0A0D13 !important;
color: #EAF0F7 !important;
}
.theme-table {
width: 100%;
border-collapse: collapse;
background: #0A0D13;
color: #EAF0F7;
border: 1px solid rgba(255,255,255,0.08);
border-radius: 8px;
overflow: hidden;
}
.theme-table th, .theme-table td {
padding: 12px 14px;
border-bottom: 1px solid rgba(255,255,255,0.08);
text-align: left;
}
.theme-table th {
background: #121823;
color: #8A97A8;
font-weight: 800;
}

</style>
""", unsafe_allow_html=True)

if theme_mode == "Claro":
    st.markdown("""
    <style>
    .stApp { background-color: #F8F9FC !important; color: #1E293B !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid rgba(15,23,42,0.08) !important; }
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: #FFFFFF !important;
        color: #0F172A !important;
        border-color: rgba(15,23,42,0.14) !important;
    }
    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder { color: #64748B !important; }
    [data-testid="stSidebar"] svg { color: #0F172A !important; fill: #0F172A !important; }
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: #10B981 !important;
        color: #FFFFFF !important;
    }
    [data-testid="stHeader"] button, [data-testid="stHeader"] svg { color: #0F172A !important; fill: #0F172A !important; stroke: #0F172A !important; }
    h1, h2, h3, h4, .sipy-word { color: #0F172A !important; }
    .custom-header { border-bottom-color: rgba(15,23,42,0.08); }
    .agency img { filter: invert(1) brightness(0.25); }
    .agency .div-bar { background: rgba(15,23,42,0.12); }
    .agency .who, .stamp, .lede, .kpi .lab, .hero-card .lab { color: #64748B; }
    .loading-overlay { background-color: rgba(248,249,252,0.95); }
    .spinner { border-color: rgba(15,23,42,0.08); border-left-color: #059669; }
    .loading-text, .eyebrow, .hero-card .big { color: #059669; }
    .hero-card { background: linear-gradient(165deg, #FFFFFF, #F1F5F9); border-color: rgba(15,23,42,0.08); color: #1E293B; box-shadow: 0 4px 15px rgba(15,23,42,0.04); }
    .kpi, .stTable { background: #FFFFFF !important; border-color: rgba(15,23,42,0.08) !important; color: #1E293B; box-shadow: 0 4px 12px rgba(15,23,42,0.03); }
    .kpi .val { color: #0F172A; }
    .kpi .sub { color: #94A3B8; }
    .delta.up { background: rgba(5,150,105,0.1); color: #059669; }
    .delta.down { background: rgba(220,38,38,0.1); color: #DC2626; }
    .stApp label, .stApp p, [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"] { color: #0F172A; }
    [data-testid="stDataFrame"] { background: #FFFFFF !important; color: #0F172A !important; }
    .theme-table { background: #FFFFFF; color: #0F172A; border-color: rgba(15,23,42,0.08); }
    .theme-table th, .theme-table td { border-bottom-color: rgba(15,23,42,0.08); }
    .theme-table th { background: #F1F5F9; color: #64748B; }
    </style>
    """, unsafe_allow_html=True)

# Helper function to extract metrics robustly
def extract_metric(metrics, keys):
    for key in keys:
        if key in metrics and metrics[key] is not None:
            try:
                return float(metrics[key])
            except ValueError:
                pass
    return 0.0

DIMENSION_VALUE_LABELS = {
    "gender": {
        "male": "Masculino",
        "female": "Femenino",
        "unknown": "Desconocido",
        "unmapped": "Desconocido",
        "not_specified": "No especificado",
    }
}

META_PUBLISHER_LABELS = {
    "facebook": "Facebook Ads",
    "instagram": "Instagram Ads",
    "audience_network": "Audience Network",
    "messenger": "Messenger Ads",
}

def translate_dimension_value(column, value):
    if value is None:
        return "Desconocido"
    text = str(value)
    return DIMENSION_VALUE_LABELS.get(column, {}).get(text.lower(), text)

def clean_region_name(value):
    return re.sub(r"\s+Province$", "", str(value)).replace("Province", "Provincia").strip()

def clean_campaign_name(value):
    text = re.sub(r"[_/|-]+", " ", str(value))
    text = re.sub(r"\b(normal|mundial|automatico|autom[aá]tico|fb|ig|facebook|instagram|interaccion|interacción|alcance|impresiones)\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}[.-]\d{1,2}[.-]\d{2,4}\b|\b20\d{2}\b", " ", text)
    return re.sub(r"\s+", " ", text).strip().title() or str(value)

def meta_base_campaign_name(value):
    return re.sub(r"_(facebook|instagram|audience_network|messenger)$", "", str(value), flags=re.I)

# Platform Types definition
PLATFORM_TYPES = {
    "meta_ads": "ads",
    "google_ads": "ads",
    "tiktok_ads": "ads",
    "linkedin_ads": "ads",
    "apple_ads": "ads",
    "x_ads": "ads",
    "spotify_ads": "ads",
    "pinterest_ads": "ads",
    "meta_organic": "organic",
    "tiktok_organic": "organic",
    "linkedin_organic": "organic",
    "x_organic": "organic",
    "youtube": "organic",
    "threads": "organic",
    "pinterest_organic": "organic",
    "ga4": "analytics",
    "shopify": "analytics",
    "ghl": "analytics",
    "google_play": "app_store",
    "apple_app_store": "app_store",
}

# API Call logic
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
def fetch_campaign_data_from_api(platform_key, client_id, user_id, account_id, start_date, end_date, metrics, dimensions, opt_filters, write_to_bq, api_key, show_errors=True, timeout=45):
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

# Get previous calendar month start and end dates
def get_prior_month_range(start_date):
    if start_date.month == 1:
        prev_month = 12
        prev_year = start_date.year - 1
    else:
        prev_month = start_date.month - 1
        prev_year = start_date.year
        
    prev_start = date(prev_year, prev_month, 1)
    last_day = calendar.monthrange(prev_year, prev_month)[1]
    prev_end = date(prev_year, prev_month, last_day)
    return prev_start, prev_end

def theme_chart(chart):
    return chart.properties(background=chart_bg).configure_view(
        strokeOpacity=0,
        fill=chart_bg,
    ).configure_axis(
        gridColor=grid_color,
        labelColor=text_color,
        titleColor=text_color,
    ).configure_legend(
        labelColor=text_color,
        titleColor=text_color,
    )

def show_theme_table(df):
    st.markdown(df.to_html(index=False, classes="theme-table"), unsafe_allow_html=True)

# SIDEBAR FILTERS (Acts as the collapsible Hamburger Menu on the left)
st.sidebar.image("https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg", width=120)
st.sidebar.markdown("### Configuración de Consulta")

# API key setup
api_key = st.sidebar.text_input("X-API-Key", value=DEFAULT_API_KEY, type="password")

# Client & User setup
client_id = st.sidebar.text_input("ID de cliente", value="client_1")
user_id = st.sidebar.text_input("ID de usuario", value="user_1")

# Platform Selection
platform_labels = {
    "meta_ads": "Meta Ads (Facebook/IG)",
    "google_ads": "Google Ads",
    "tiktok_ads": "TikTok Ads",
    "linkedin_ads": "LinkedIn Ads",
    "apple_ads": "Apple Search Ads",
    "x_ads": "X Ads",
    "spotify_ads": "Spotify Ads",
    "pinterest_ads": "Pinterest Ads",
    "meta_organic": "Meta Orgánico",
    "tiktok_organic": "TikTok Orgánico",
    "linkedin_organic": "LinkedIn Orgánico",
    "x_organic": "X Orgánico",
    "youtube": "YouTube Analytics",
    "threads": "Threads Orgánico",
    "pinterest_organic": "Pinterest Orgánico",
    "ga4": "Google Analytics 4",
    "shopify": "Shopify Store",
    "ghl": "GoHighLevel (GHL)",
    "google_play": "Google Play Store",
    "apple_app_store": "Apple App Store",
}
selected_platform_labels = st.sidebar.multiselect(
    "Plataforma",
    list(platform_labels.values()),
    default=[platform_labels["meta_ads"]],
)
if not selected_platform_labels:
    st.sidebar.warning("Selecciona al menos una plataforma.")
    selected_platform_labels = [platform_labels["meta_ads"]]

selected_platform_keys = [k for k, v in platform_labels.items() if v in selected_platform_labels]
platform_configs = []

for selected_platform_key in selected_platform_keys:
    platform_label = platform_labels[selected_platform_key]
    with st.sidebar.expander(platform_label, expanded=len(selected_platform_keys) == 1):
        sidebar_cache = st.session_state.setdefault("sidebar_api_cache", {})
        connections_key = ("connections", selected_platform_key, client_id, api_key)
        if connections_key not in sidebar_cache:
            sidebar_cache[connections_key] = fetch_connections_from_api(selected_platform_key, client_id, api_key)
        connections = sidebar_cache[connections_key]
        if connections:
            connection_options = {f"{c['account_name']} ({c['account_id']})": c["account_id"] for c in connections}
            selected_conn_label = st.selectbox("Cuentas Conectadas", list(connection_options.keys()), key=f"conn_{selected_platform_key}")
            default_account_id = connection_options[selected_conn_label]
        else:
            default_account_id = "act_1229232368796008" if selected_platform_key == "meta_ads" else "account_1"

        account_key = f"account_{selected_platform_key}"
        prev_conn_key = f"prev_conn_{selected_platform_key}"
        if st.session_state.get(prev_conn_key) != default_account_id:
            st.session_state[account_key] = default_account_id
            st.session_state[prev_conn_key] = default_account_id
        account_id_value = st.text_input("ID de cuenta", key=account_key)
        schema_key = ("schema", selected_platform_key, api_key)
        if schema_key not in sidebar_cache:
            sidebar_cache[schema_key] = fetch_schema_from_api(selected_platform_key, api_key)
        schema_data = sidebar_cache[schema_key]
        metrics_list = schema_data.get("metrics", [])
        dimensions_list = schema_data.get("dimensions", [])
        metrics_key = f"selected_metrics_{selected_platform_key}"
        dimensions_key = f"selected_dimensions_{selected_platform_key}"
        if metrics_key not in st.session_state or not st.session_state[metrics_key]:
            st.session_state[metrics_key] = [m["name"] for m in metrics_list[:8]] if metrics_list else ["impressions"]
        if dimensions_key not in st.session_state:
            st.session_state[dimensions_key] = []

        selected_metrics_value = st.multiselect(
            "Métricas *",
            options=[m["name"] for m in metrics_list],
            default=st.session_state[metrics_key],
            key=f"metrics_{selected_platform_key}",
            help="Selecciona las métricas a consultar",
        )
        selected_dimensions_value = st.multiselect(
            "Dimensiones (Opcional)",
            options=[d["name"] for d in dimensions_list],
            default=st.session_state[dimensions_key],
            key=f"dimensions_{selected_platform_key}",
            help="Selecciona dimensiones para desglosar",
        )

        platform_type_value = PLATFORM_TYPES.get(selected_platform_key, "ads")
        opt_filters_value = {}
        if platform_type_value == "organic":
            post_id = st.text_input("ID de publicación", value="", placeholder="ID de publicación (opcional)", key=f"post_{selected_platform_key}")
            video_id = st.text_input("ID de video", value="", placeholder="ID de video (opcional)", key=f"video_{selected_platform_key}")
            if post_id:
                opt_filters_value["post_id"] = post_id
            if video_id:
                opt_filters_value["video_id"] = video_id
        elif platform_type_value == "app_store":
            app_id = st.text_input("ID de app", value="", placeholder="ID de app / paquete (opcional)", key=f"app_{selected_platform_key}")
            if app_id:
                opt_filters_value["app_id"] = app_id

        platform_configs.append({
            "platform_key": selected_platform_key,
            "platform_label": platform_label,
            "platform_type": platform_type_value,
            "connections": connections,
            "account_id": account_id_value,
            "metrics_list": metrics_list,
            "dimensions_list": dimensions_list,
            "selected_metrics": selected_metrics_value,
            "selected_dimensions": selected_dimensions_value,
            "opt_filters": opt_filters_value,
        })

platform_key = platform_configs[0]["platform_key"]
platform_type = platform_configs[0]["platform_type"]
selected_platform_label = " + ".join(cfg["platform_label"] for cfg in platform_configs)
connections = platform_configs[0]["connections"]
account_id = platform_configs[0]["account_id"]
selected_metrics = platform_configs[0]["selected_metrics"]
selected_dimensions = platform_configs[0]["selected_dimensions"]
metrics_list = platform_configs[0]["metrics_list"]
opt_filters = platform_configs[0]["opt_filters"]
# Write to BQ checkbox
write_to_bq = st.sidebar.checkbox("Escribir resultados a BigQuery (write_to_bq)", value=False)

# Date Pickers
today = date.today()
default_start = today - timedelta(days=30)
date_range = st.sidebar.date_input("Rango de Fechas a Consultar", [default_start, today])
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
else:
    start_date, end_date = default_start, today

st.sidebar.markdown("---")
# Execute Button in Sidebar to prevent auto-loading until clicked
execute_query = st.sidebar.button("🚀 Consultar API", use_container_width=True)

# MAIN DISPLAY (Occupies full wide screen)
# Header
st.markdown(f"""
<div class="custom-header">
    <div class="agency">
        <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg" alt="Inhaus">
        <span class="div-bar"></span>
        <span class="who">Dashboard de Pauta &middot; Conexión de API</span>
    </div>
    <span class="stamp"><span class="live"></span> API Directa</span>
</div>
""", unsafe_allow_html=True)

if execute_query:
    st.session_state.query_run = True
    st.session_state.force_query_fetch = True
    st.rerun()

if not st.session_state.get("query_run", False):
    st.info("Configura tus parámetros de consulta en el menú hamburguesa lateral izquierdo y presiona el botón 'Consultar API de Producción' para cargar la visualización en pantalla completa.")
    st.stop()
else:
    # Render the fullscreen loading overlay first to block the screen
    loading_placeholder = st.empty()
        
    # Calculate comparison month (previous calendar month)
    prev_start_date, prev_end_date = get_prior_month_range(start_date)
    
# Ensure standard KPI metrics requested in payload even unchecked
query_configs = []
for cfg in platform_configs:
    metric_names = [x["name"] for x in cfg["metrics_list"]]
    dimension_names = [x["name"] for x in cfg["dimensions_list"]]
    request_metrics = list(cfg["selected_metrics"])
    if cfg["platform_type"] == "ads":
        standard_metrics = ["impressions", "clicks", "spend", "conversions", "reach"]
    elif cfg["platform_type"] == "analytics":
        standard_metrics = ["sessions", "users", "pageviews", "bounce_rate"]
    elif cfg["platform_type"] == "app_store":
        standard_metrics = ["downloads", "ratings"]
    else:
        standard_metrics = ["impressions", "engagement", "followers", "reach"]
    for metric in standard_metrics:
        if metric not in request_metrics and metric in metric_names:
            request_metrics.append(metric)

    request_dimensions = list(cfg["selected_dimensions"])
    if cfg["platform_key"] == "meta_ads" and "publisher_platform" in dimension_names and "publisher_platform" not in request_dimensions:
        request_dimensions.append("publisher_platform")

    cfg["request_metrics"] = request_metrics
    cfg["request_dimensions"] = request_dimensions
    query_configs.append((
        cfg["platform_key"], cfg["account_id"], tuple(request_metrics), tuple(request_dimensions),
        json.dumps(cfg["opt_filters"], sort_keys=True, default=str),
    ))

query_key = (
    client_id, user_id,
    start_date.isoformat(), end_date.isoformat(),
    bool(write_to_bq), tuple(query_configs),
)

st.session_state.setdefault("dashboard_query_cache", {})
force_query_fetch = st.session_state.pop("force_query_fetch", False)
if force_query_fetch:
    st.session_state["active_query_key"] = query_key
active_query_key = st.session_state.get("active_query_key", query_key)

if force_query_fetch or active_query_key not in st.session_state["dashboard_query_cache"]:
    curr_frames = []
    prev_frames = []
    for idx, cfg in enumerate(platform_configs, start=1):
        loading_placeholder.markdown(f"""
        <div class="loading-overlay">
            <div class="spinner"></div>
            <div class="loading-text">{idx}/{len(platform_configs)}: Consultando {cfg['platform_label']}...</div>
        </div>
        """, unsafe_allow_html=True)

        curr_rows = fetch_campaign_data_from_api(
            cfg["platform_key"], client_id, user_id, cfg["account_id"],
            start_date, end_date, cfg["request_metrics"], cfg["request_dimensions"],
            cfg["opt_filters"], write_to_bq, api_key
        )
        prev_rows = fetch_campaign_data_from_api(
            cfg["platform_key"], client_id, user_id, cfg["account_id"],
            prev_start_date, prev_end_date, cfg["request_metrics"], cfg["request_dimensions"],
            cfg["opt_filters"], False, api_key
        )
        if curr_rows:
            curr_frames.append(process_api_response(curr_rows, cfg["platform_key"], client_id, user_id))
        if prev_rows:
            prev_frames.append(process_api_response(prev_rows, cfg["platform_key"], client_id, user_id))

    df_curr = pd.concat(curr_frames, ignore_index=True) if curr_frames else pd.DataFrame()
    df_prev = pd.concat(prev_frames, ignore_index=True) if prev_frames else pd.DataFrame()
    account_disp = " | ".join(f"{cfg['platform_label']}: {cfg['account_id']}" for cfg in platform_configs)
    active_context = {
        "platform_key": platform_key,
        "platform_type": platform_type,
        "selected_platform_label": selected_platform_label,
        "account_id": account_id,
        "account_disp": account_disp,
        "selected_dimensions": selected_dimensions,
        "opt_filters": opt_filters,
    }
    st.session_state["dashboard_query_cache"][query_key] = (df_curr, df_prev, active_context)
    active_query_key = query_key
    loading_placeholder.empty()
else:
    df_curr, df_prev, active_context = st.session_state["dashboard_query_cache"][active_query_key]

platform_key = active_context["platform_key"]
platform_type = active_context["platform_type"]
selected_platform_label = active_context["selected_platform_label"]
account_id = active_context["account_id"]
account_disp = active_context["account_disp"]
selected_dimensions = active_context["selected_dimensions"]
opt_filters = active_context["opt_filters"]
    
# Inject JavaScript to automatically collapse the sidebar menu if it is expanded
import streamlit.components.v1 as components
components.html("""
    <script>
    (function() {
        const parentDoc = window.parent.document;
        const collapseSidebar = () => {
            const collapseBtn = parentDoc.querySelector(
                '[data-testid="stSidebarCollapseButton"], button[aria-label="Close sidebar"], button[title="Close sidebar"]'
            );
            if (collapseBtn) collapseBtn.click();
        };
        collapseSidebar();
        setTimeout(collapseSidebar, 200);
        setTimeout(collapseSidebar, 500);
    })();
    </script>
""", height=0, width=0)

if df_curr.empty:
    st.error("No se recibió información de la API para el periodo actual. Verifica las credenciales, plataforma o ID de cuenta en el menú lateral.")
else:
    # HERO RENDER (Clean, full width, no Sipy logo)
    title_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
    st.markdown(f"""
    <h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: {title_color};">{selected_platform_label} &middot; {account_disp}</h1>
    <p class="lede" style="margin-top: 15px;">
        Resultados del <b>{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}</b>.<br/>
        Comparado contra mes anterior completo: <b>{prev_start_date.strftime('%d/%m/%Y')} al {prev_end_date.strftime('%d/%m/%Y')}</b>.
    </p>
    """, unsafe_allow_html=True)

    # Primary KPI calculations
    if platform_type == "ads":
        curr_primary = df_curr["conversions"].sum()
        prev_primary = df_prev["conversions"].sum() if not df_prev.empty else 0
        primary_label = "Conversiones Totales"
    elif platform_type == "analytics":
        curr_primary = df_curr["sessions"].sum()
        prev_primary = df_prev["sessions"].sum() if not df_prev.empty else 0
        primary_label = "Sesiones Totales"
    elif platform_type == "app_store":
        curr_primary = df_curr["downloads"].sum()
        prev_primary = df_prev["downloads"].sum() if not df_prev.empty else 0
        primary_label = "Descargas Totales"
    else:
        curr_primary = df_curr["engagement"].sum()
        prev_primary = df_prev["engagement"].sum() if not df_prev.empty else 0
        primary_label = "Interacciones totales"
        
    # Draw primary KPI card (Full width summary)
    st.markdown(f"""
    <div class="hero-card">
        <div class="lab">{primary_label}</div>
        <div class="big">{curr_primary:,}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # KPI Card HTML Builder (completely single line to prevent markdown indent formatting issues)
    def get_kpi_card_html(label, value_str, sub_str, curr_val, prev_val, lower_is_better=False):
        delta_html = ""
        if prev_val and prev_val > 0:
            pct_change = ((curr_val - prev_val) / prev_val) * 100
            is_good = pct_change < 0 if lower_is_better else pct_change > 0
            delta_class = "up" if is_good else "down"
            arrow = "&#9650;" if pct_change > 0 else "&#9660;"
            delta_html = f'<div class="delta {delta_class}">{arrow} {pct_change:+.1f}% vs. ant.</div>'
        else:
            delta_html = '<div class="delta up" style="background: rgba(255,255,255,0.06); color: #8A97A8;">N/D vs. ant.</div>'
        return f'<div class="kpi"><div><div class="lab">{label}</div><div class="val">{value_str}</div><div class="sub">{sub_str}</div></div>{delta_html}</div>'

    # Render grid KPIs based on platform type
    st.markdown("### Métricas clave con comparación")
    
    if platform_type == "ads":
        total_spend_curr = df_curr["spend"].sum()
        total_impressions_curr = df_curr["impressions"].sum()
        total_clicks_curr = df_curr["clicks"].sum()
        total_conversions_curr = df_curr["conversions"].sum()
        
        avg_ctr_curr = total_clicks_curr / total_impressions_curr if total_impressions_curr > 0 else 0.0
        avg_cpc_curr = total_spend_curr / total_clicks_curr if total_clicks_curr > 0 else 0.0
        cpa_curr = total_spend_curr / total_conversions_curr if total_conversions_curr > 0 else 0.0

        total_spend_prev = df_prev["spend"].sum() if not df_prev.empty else 0.0
        total_impressions_prev = df_prev["impressions"].sum() if not df_prev.empty else 0.0
        total_clicks_prev = df_prev["clicks"].sum() if not df_prev.empty else 0.0
        total_conversions_prev = df_prev["conversions"].sum() if not df_prev.empty else 0.0
        
        avg_ctr_prev = total_clicks_prev / total_impressions_prev if total_impressions_prev > 0 else 0.0
        avg_cpc_prev = total_spend_prev / total_clicks_prev if total_clicks_prev > 0 else 0.0
        cpa_prev = total_spend_prev / total_conversions_prev if total_conversions_prev > 0 else 0.0

        kpis_layout = '<div class="kpis">\n'
        kpis_layout += get_kpi_card_html("Inversión Total", f"${total_spend_curr:,.2f}", "Gasto total en pauta", total_spend_curr, total_spend_prev, lower_is_better=True) + "\n"
        kpis_layout += get_kpi_card_html("Impresiones Totales", f"{total_impressions_curr:,}", "Vistas acumuladas", total_impressions_curr, total_impressions_prev) + "\n"
        kpis_layout += get_kpi_card_html("Clics", f"{total_clicks_curr:,}", "Interacciones con anuncios", total_clicks_curr, total_clicks_prev) + "\n"
        kpis_layout += get_kpi_card_html("Costo por Conversión (CPA)", f"${cpa_curr:,.2f}", "Costo unitario", cpa_curr, cpa_prev, lower_is_better=True) + "\n"
        kpis_layout += get_kpi_card_html("CTR Promedio", f"{avg_ctr_curr:.2%}", "Tasa de clics/impresión", avg_ctr_curr, avg_ctr_prev) + "\n"
        kpis_layout += get_kpi_card_html("CPC Promedio", f"${avg_cpc_curr:,.2f}", "Costo promedio por clic", avg_cpc_curr, avg_cpc_prev, lower_is_better=True) + "\n"
        kpis_layout += '</div>'
    elif platform_type == "analytics":
        total_sessions_curr = df_curr["sessions"].sum()
        total_users_curr = df_curr["users"].sum()
        total_pageviews_curr = df_curr["pageviews"].sum()
        avg_bounce_curr = df_curr["bounce_rate"].mean()

        total_sessions_prev = df_prev["sessions"].sum() if not df_prev.empty else 0.0
        total_users_prev = df_prev["users"].sum() if not df_prev.empty else 0.0
        total_pageviews_prev = df_prev["pageviews"].sum() if not df_prev.empty else 0.0
        avg_bounce_prev = df_prev["bounce_rate"].mean() if not df_prev.empty else 0.0

        kpis_layout = '<div class="kpis">\n'
        kpis_layout += get_kpi_card_html("Sesiones Totales", f"{total_sessions_curr:,}", "Visitas del sitio", total_sessions_curr, total_sessions_prev) + "\n"
        kpis_layout += get_kpi_card_html("Usuarios Únicos", f"{total_users_curr:,}", "Visitantes únicos", total_users_curr, total_users_prev) + "\n"
        kpis_layout += get_kpi_card_html("Páginas Vistas", f"{total_pageviews_curr:,}", "Cargas de página", total_pageviews_curr, total_pageviews_prev) + "\n"
        kpis_layout += get_kpi_card_html("Porcentaje de Rebote", f"{avg_bounce_curr:.1f}%", "Visitas de una sola página", avg_bounce_curr, avg_bounce_prev, lower_is_better=True) + "\n"
        kpis_layout += '</div>'
    elif platform_type == "app_store":
        total_downloads_curr = df_curr["downloads"].sum()
        avg_ratings_curr = df_curr["ratings"].mean()

        total_downloads_prev = df_prev["downloads"].sum() if not df_prev.empty else 0.0
        avg_ratings_prev = df_prev["ratings"].mean() if not df_prev.empty else 0.0

        kpis_layout = '<div class="kpis">\n'
        kpis_layout += get_kpi_card_html("Descargas Totales", f"{total_downloads_curr:,}", "Instalaciones de app", total_downloads_curr, total_downloads_prev) + "\n"
        kpis_layout += get_kpi_card_html("Calificación Promedio", f"{avg_ratings_curr:.2f} ★", "Opiniones de usuarios", avg_ratings_curr, avg_ratings_prev) + "\n"
        kpis_layout += '</div>'
    else: # organic
        total_impressions_curr = df_curr["impressions"].sum()
        total_engagement_curr = df_curr["engagement"].sum()
        total_followers_curr = df_curr["followers"].sum()
        total_reach_curr = df_curr["reach"].sum()

        total_impressions_prev = df_prev["impressions"].sum() if not df_prev.empty else 0.0
        total_engagement_prev = df_prev["engagement"].sum() if not df_prev.empty else 0.0
        total_followers_prev = df_prev["followers"].sum() if not df_prev.empty else 0.0
        total_reach_prev = df_prev["reach"].sum() if not df_prev.empty else 0.0

        kpis_layout = '<div class="kpis">\n'
        kpis_layout += get_kpi_card_html("Impresiones Orgánicas", f"{total_impressions_curr:,}", "Visualizaciones de contenido", total_impressions_curr, total_impressions_prev) + "\n"
        kpis_layout += get_kpi_card_html("Interacciones", f"{total_engagement_curr:,}", "Me gusta, compartidos, comentarios", total_engagement_curr, total_engagement_prev) + "\n"
        kpis_layout += get_kpi_card_html("Seguidores Totales", f"{total_followers_curr:,}", "Comunidad", total_followers_curr, total_followers_prev) + "\n"
        kpis_layout += get_kpi_card_html("Alcance Orgánico", f"{total_reach_curr:,}", "Usuarios únicos alcanzados", total_reach_curr, total_reach_prev) + "\n"
        kpis_layout += '</div>'

    st.markdown(kpis_layout, unsafe_allow_html=True)

    if platform_key == "meta_ads" and st.checkbox("Cargar datos oficiales de Facebook Ads (puede tardar)", value=False):
        official_key = (
            platform_key, client_id, user_id, account_id,
            start_date.isoformat(), end_date.isoformat(),
            json.dumps(opt_filters, sort_keys=True, default=str),
        )
        st.session_state.setdefault("meta_official_cache", {})
        if official_key not in st.session_state["meta_official_cache"]:
            with st.spinner("Cargando datos oficiales de Facebook Ads... puede tardar unos minutos."):
                age_data = fetch_campaign_data_from_api(
                    platform_key, client_id, user_id, account_id,
                    start_date, end_date, ["impressions", "reach"], ["age"],
                    opt_filters, False, api_key, False, 180
                )
                gender_data = fetch_campaign_data_from_api(
                    platform_key, client_id, user_id, account_id,
                    start_date, end_date, ["impressions", "reach"], ["gender"],
                    opt_filters, False, api_key, False, 180
                )
                region_data = fetch_campaign_data_from_api(
                    platform_key, client_id, user_id, account_id,
                    start_date, end_date, ["impressions", "reach"], ["region"],
                    opt_filters, False, api_key, False, 180
                )
                st.session_state["meta_official_cache"][official_key] = (age_data, gender_data, region_data)
        age_data, gender_data, region_data = st.session_state["meta_official_cache"][official_key]

        df_age = process_api_response(age_data, platform_key, client_id, user_id) if age_data else pd.DataFrame()
        df_gender = process_api_response(gender_data, platform_key, client_id, user_id) if gender_data else pd.DataFrame()
        df_region = process_api_response(region_data, platform_key, client_id, user_id) if region_data else pd.DataFrame()

        def ensure_breakdown_column(df, column):
            if df.empty:
                return df
            if column not in df.columns:
                parts = df["campaign_name"].astype(str).str.rsplit("_", n=1, expand=True)
                if len(parts.columns) == 2:
                    df[column] = parts[1]
            if column in df.columns:
                df[column] = df[column].apply(lambda value: translate_dimension_value(column, value))
                if column == "region":
                    df[column] = df[column].apply(clean_region_name)
            return df

        df_age = ensure_breakdown_column(df_age, "age")
        df_gender = ensure_breakdown_column(df_gender, "gender")
        df_region = ensure_breakdown_column(df_region, "region")

        if not df_age.empty or not df_gender.empty or not df_region.empty:
            st.markdown("### Datos oficiales de Facebook Ads")
            age_col, gender_col, region_col = st.columns([1, 1, 1.3])

            for df_breakdown, col_name, title, col in [
                (df_age, "age", "Edad", age_col),
                (df_gender, "gender", "Género", gender_col),
            ]:
                with col:
                    if col_name in df_breakdown.columns:
                        metric = "reach" if df_breakdown["reach"].sum() else "impressions"
                        chart_data = df_breakdown.groupby(col_name)[metric].sum().reset_index()
                        total = chart_data[metric].sum()
                        chart_data["share"] = chart_data[metric] / total if total else 0
                        chart = alt.Chart(chart_data).mark_bar(cornerRadiusEnd=4).encode(
                        x=alt.X(f"{col_name}:N", title=title),
                        y=alt.Y("share:Q", title="% audiencia", axis=alt.Axis(format="%")),
                        tooltip=[col_name, alt.Tooltip("share:Q", format=".2%")]
                        ).properties(height=300)
                        st.markdown(f"#### {title}")
                        st.altair_chart(theme_chart(chart), use_container_width=True)
                    else:
                        st.info(f"Meta no devolvió {title.lower()} para este rango.")

            with region_col:
                if "region" in df_region.columns:
                    metric = "reach" if df_region["reach"].sum() else "impressions"
                    table = df_region.groupby("region")[metric].sum().sort_values(ascending=False).head(10)
                    total = df_region[metric].sum()
                    table = (table / total).reset_index(name="%") if total else table.reset_index(name="%")
                    region_chart = alt.Chart(table).mark_bar(color="#5C9DFF", cornerRadiusEnd=4).encode(
                        x=alt.X("%:Q", title="% audiencia", axis=alt.Axis(format="%")),
                        y=alt.Y("region:N", sort="-x", title=None),
                        tooltip=["region", alt.Tooltip("%:Q", format=".2%")],
                    ).properties(height=300)
                    st.markdown("#### Regiones principales")
                    st.altair_chart(theme_chart(region_chart), use_container_width=True)
                    table["%"] = table["%"].apply(lambda x: f"{x:.2%}")
                    st.markdown("#### Top 10 regiones")
                    show_theme_table(table.rename(columns={"region": "Región"}))
                else:
                    st.info("Meta no devolvió regiones para este rango.")
        else:
            st.info("Meta no devolvió datos oficiales para este rango.")

    # CHARTS SECTION
    st.markdown("### Tendencias Históricas")
    col_chart_left, col_chart_right = st.columns(2)
    
    with col_chart_left:
        df_trend = df_curr.groupby("date").agg({
            "spend": "sum", "conversions": "sum", "sessions": "sum", "pageviews": "sum", "downloads": "sum", "impressions": "sum", "engagement": "sum"
        }).reset_index().sort_values("date")
        
        # Render custom Altair line chart with Dual Y-Axis so both metrics are visible on their own scale
        if not df_trend.empty:
            base = alt.Chart(df_trend).encode(
                x=alt.X('date:T', axis=alt.Axis(format='%Y-%m-%d', title='Fecha', labelAngle=-45))
            )
            
            if platform_type == "ads":
                st.markdown("#### Inversión vs. conversiones diarias (eje dual)")
                left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                    y=alt.Y('spend:Q', title='Inversión ($)', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
                )
                right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
                    y=alt.Y('conversions:Q', title='Conversiones', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
                )
                dual_chart = alt.layer(left_line, right_line).resolve_scale(
                    y='independent'
                ).properties(height=350)
                st.altair_chart(theme_chart(dual_chart), use_container_width=True)
                
            elif platform_type == "analytics":
                st.markdown("#### Sesiones vs. páginas vistas (eje dual)")
                left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                    y=alt.Y('sessions:Q', title='Sesiones', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
                )
                right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
                    y=alt.Y('pageviews:Q', title='Páginas Vistas', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
                )
                dual_chart = alt.layer(left_line, right_line).resolve_scale(
                    y='independent'
                ).properties(height=350)
                st.altair_chart(theme_chart(dual_chart), use_container_width=True)
                
            elif platform_type == "app_store":
                st.markdown("#### Descargas Diarias")
                line_chart = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                    y=alt.Y('downloads:Q', title='Descargas')
                ).properties(height=350)
                st.altair_chart(theme_chart(line_chart), use_container_width=True)
                
            else: # organic
                st.markdown("#### Impresiones vs. interacciones (eje dual)")
                left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                    y=alt.Y('impressions:Q', title='Impresiones', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
                )
                right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
                    y=alt.Y('engagement:Q', title='Interacciones', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
                )
                dual_chart = alt.layer(left_line, right_line).resolve_scale(
                    y='independent'
                ).properties(height=350)
                st.altair_chart(theme_chart(dual_chart), use_container_width=True)
                
    with col_chart_right:
        # Render Campaign Distribution as a Horizontal Bar Chart so long labels are readable
        if platform_type == "ads":
            st.markdown("#### Distribución de Conversiones por Campaña")
            df_camp = df_curr.groupby("campaign_name")["conversions"].sum().reset_index()
            df_camp = df_camp.sort_values("conversions", ascending=False).head(10)
            df_camp["campaign_label"] = df_camp["campaign_name"].apply(clean_campaign_name)
            
            chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                x=alt.X('conversions:Q', title='Conversiones'),
                y=alt.Y('campaign_label:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
            ).properties(height=350)
            st.altair_chart(theme_chart(chart_camp), use_container_width=True)
            
        elif platform_type == "analytics":
            st.markdown("#### Sesiones por Campaña/Fuente")
            df_camp = df_curr.groupby("campaign_name")["sessions"].sum().reset_index()
            df_camp = df_camp.sort_values("sessions", ascending=False).head(10)
            
            chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                x=alt.X('sessions:Q', title='Sesiones'),
                y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
            ).properties(height=350)
            st.altair_chart(theme_chart(chart_camp), use_container_width=True)
            
        else: # organic / app_store
            st.markdown("#### Alcance / Distribución por Publicación")
            target_metric = "reach" if platform_type != "app_store" else "downloads"
            df_camp = df_curr.groupby("campaign_name")[target_metric].sum().reset_index()
            df_camp = df_camp.sort_values(target_metric, ascending=False).head(10)
            
            chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                x=alt.X(f"{target_metric}:Q", title='Alcance / Volumen'),
                y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
            ).properties(height=350)
            st.altair_chart(theme_chart(chart_camp), use_container_width=True)
            
    # CAMPAIGN BREAKDOWN TABLE
    st.markdown("### Detalle de Campañas y Resultados")
    
    df_table = df_curr.copy()

    group_keys = ["campaign_name", "platform"]
    for dim in selected_dimensions:
        if dim in df_table.columns and dim not in group_keys:
            group_keys.append(dim)
            
    if platform_type == "ads":
        df_table = df_table.groupby(group_keys).agg({
            "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum"
        }).reset_index()
        meta_platforms = set(META_PUBLISHER_LABELS.values()) | {"meta_ads"}
        meta_table = df_table[df_table["platform"].isin(meta_platforms)].copy()
        if platform_key == "meta_ads" and not meta_table.empty:
            meta_table["base_campaign_name"] = meta_table["campaign_name"].apply(meta_base_campaign_name)
            ranked_campaigns = meta_table.groupby(["base_campaign_name", "platform"]).agg({
                "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum"
            }).reset_index()
            rank_metric = "conversions" if ranked_campaigns["conversions"].sum() else ("clicks" if ranked_campaigns["clicks"].sum() else "impressions")
            metric_label = {"conversions": "conversiones", "clicks": "clics", "impressions": "impresiones"}[rank_metric]
            ranked_campaigns = ranked_campaigns.sort_values(rank_metric, ascending=False).head(8)
            campaign_summary = ranked_campaigns[["base_campaign_name", "platform", "impressions", rank_metric]].copy()
            campaign_summary["campaign_label"] = campaign_summary["base_campaign_name"].apply(clean_campaign_name)
            campaign_summary["impressions"] = campaign_summary["impressions"].apply(lambda x: f"{x:,.0f}")
            campaign_summary[rank_metric] = campaign_summary[rank_metric].apply(lambda x: f"{x:,.0f}")
            campaign_summary = campaign_summary[["campaign_label", "platform", "impressions", rank_metric]].rename(columns={
                "campaign_label": "Campaña",
                "platform": "Plataforma",
                "impressions": "Impresiones",
                rank_metric: metric_label.capitalize(),
            })

            st.markdown("### Desempeño de campañas destacadas")
            show_theme_table(campaign_summary)
            preview_names = tuple(dict.fromkeys(ranked_campaigns["base_campaign_name"]))
            # ponytail: Meta previews cost one Graph call each; paginate this if accounts need more than 8 cards.
            preview_cache = st.session_state.setdefault("meta_preview_cache", {})
            preview_key = (client_id, account_id, preview_names, api_key)
            if preview_key not in preview_cache:
                preview_cache[preview_key] = fetch_meta_campaign_previews(client_id, account_id, preview_names, api_key)
            previews, preview_error = preview_cache[preview_key]
            previews_by_campaign = {p["campaign_name"]: p for p in previews}
            campaign_metrics = meta_table.groupby("base_campaign_name").agg({
                "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum"
            }).to_dict("index")

            st.markdown(f"### Ranking: top campañas por {metric_label} (Meta)")
            if preview_error:
                st.info(preview_error)

            rank_cols = st.columns(4)
            for idx, row in enumerate(ranked_campaigns.itertuples(index=False), start=1):
                preview = previews_by_campaign.get(row.base_campaign_name)
                ctr = row.clicks / row.impressions if row.impressions else 0
                cpc = row.spend / row.clicks if row.clicks else 0
                cpa = row.spend / row.conversions if row.conversions else 0
                body = preview["body"] if preview else "<div style='height:320px;display:grid;place-items:center;color:#8A97A8;background:#0A0D13;border-radius:10px;'>Preview no disponible</div>"
                raw_ad_name = str(preview.get("ad_name", "")) if preview else ""
                ad_name = html.escape(raw_ad_name)
                campaign_name = html.escape(clean_campaign_name(row.base_campaign_name))
                source_text = f" {row.platform} {row.base_campaign_name} {raw_ad_name} ".lower()
                if row.platform == "Instagram Ads":
                    source = "IG"
                elif row.platform == "Facebook Ads":
                    source = "FB"
                else:
                        is_ig = any(token in source_text for token in ("instagram", " instagram ", "/ig", " ig ", "-ig", "_ig"))
                        source = "FB/IG" if "fb-ig" in source_text or "facebook/ig" in source_text else ("IG" if is_ig else "FB")
                source_color = {"IG": "#E1306C", "FB": "#1877F2", "FB/IG": "#4f46e5"}.get(source, "#4f46e5")
                components_html = f"""
                <div style="font-family: Arial, sans-serif; background:#fff; border:1px solid #e5e7eb; border-radius:14px; padding:14px; position:relative; color:#111827;">
                    <div style="position:absolute; top:10px; right:10px; display:flex; gap:7px; z-index:2;">
                        <span style="background:#111827; color:#fff; min-width:32px; height:32px; padding:0 7px; border-radius:999px; display:grid; place-items:center; font-weight:800; font-size:13px;">#{idx}</span>
                        <span style="background:{source_color}; color:#fff; min-width:32px; height:32px; padding:0 7px; border-radius:999px; display:grid; place-items:center; font-weight:800; font-size:12px;">{source}</span>
                    </div>
                    <div style="height:330px; overflow:hidden; border-radius:10px; border:1px solid #eef0f3; background:#f8fafc;">{body}</div>
                    <div style="margin-top:12px; color:#0b3f91; font-weight:800; font-size:14px; line-height:1.25;">{campaign_name}</div>
                    <div style="margin-top:4px; color:#6b7280; font-size:12px; min-height:16px;">{ad_name}</div>
                    <div style="margin-top:14px; display:grid; gap:8px; font-size:13px;">
                        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #e5e7eb; padding-bottom:6px;"><span>Inversión</span><b>${row.spend:,.2f}</b></div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #e5e7eb; padding-bottom:6px;"><span>Conversiones</span><b>{row.conversions:,.0f}</b></div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #e5e7eb; padding-bottom:6px;"><span>Clics</span><b>{row.clicks:,.0f}</b></div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #e5e7eb; padding-bottom:6px;"><span>Impresiones</span><b>{row.impressions:,.0f}</b></div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #e5e7eb; padding-bottom:6px;"><span>CTR</span><b>{ctr:.2%}</b></div>
                        <div style="display:flex; justify-content:space-between; border-bottom:1px dashed #e5e7eb; padding-bottom:6px;"><span>CPC</span><b>${cpc:,.2f}</b></div>
                        <div style="display:flex; justify-content:space-between;"><span>CPA</span><b>${cpa:,.2f}</b></div>
                    </div>
                </div>
                """
                with rank_cols[(idx - 1) % 4]:
                    components.html(components_html, height=690, scrolling=True)

            ad_hashtag_rows = []
            for preview in previews:
                metrics = campaign_metrics.get(preview.get("campaign_name"), {})
                text = " ".join([
                    str(preview.get("campaign_name", "")),
                    str(preview.get("ad_name", "")),
                    str(preview.get("post_message", "")),
                    re.sub(r"<[^>]+>", " ", str(preview.get("body", ""))),
                ])
                for tag in re.findall(r"#[\wáéíóúÁÉÍÓÚñÑ]+", text):
                    ad_hashtag_rows.append({
                        "Hashtag": tag.lower(),
                        "Posts": 1,
                        "Visualizaciones": metrics.get("impressions", 0),
                        "Me gusta": metrics.get("likes", metrics.get("clicks", 0)),
                        "Comentarios": metrics.get("comments", 0),
                    })

            if ad_hashtag_rows:
                st.markdown("### Ranking de hashtags (Instagram)")
                hashtag_table = pd.DataFrame(ad_hashtag_rows).groupby("Hashtag").sum(numeric_only=True).reset_index()
                show_theme_table(hashtag_table.sort_values(["Visualizaciones", "Posts"], ascending=False).head(10))

        df_table["CTR"] = (df_table["clicks"] / df_table["impressions"]).apply(lambda x: f"{x:.2%}" if x > 0 else "0.00%")
        df_table["CPC"] = (df_table["spend"] / df_table["clicks"]).apply(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
        df_table["CPA"] = (df_table["spend"] / df_table["conversions"]).apply(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
        df_table["spend"] = df_table["spend"].apply(lambda x: f"${x:,.2f}")
        df_table["impressions"] = df_table["impressions"].apply(lambda x: f"{x:,}")
        df_table["clicks"] = df_table["clicks"].apply(lambda x: f"{x:,}")
        df_table["conversions"] = df_table["conversions"].apply(lambda x: f"{x:,}")
        df_table = df_table.rename(columns={"campaign_name": "Campaña", "platform": "Plataforma", "spend": "Inversión", "impressions": "Impresiones", "clicks": "Clics", "conversions": "Conversiones"})
    elif platform_type == "analytics":
        df_table = df_table.groupby(group_keys).agg({
            "sessions": "sum", "users": "sum", "pageviews": "sum"
        }).reset_index()
        df_table["sessions"] = df_table["sessions"].apply(lambda x: f"{x:,}")
        df_table["users"] = df_table["users"].apply(lambda x: f"{x:,}")
        df_table["pageviews"] = df_table["pageviews"].apply(lambda x: f"{x:,}")
        df_table = df_table.rename(columns={"campaign_name": "Dimensión/Campaña", "platform": "Plataforma", "sessions": "Sesiones", "users": "Usuarios", "pageviews": "Páginas Vistas"})
    else:
        df_table = df_table.groupby(group_keys).agg({
            "impressions": "sum", "engagement": "sum", "reach": "sum"
        }).reset_index()
        df_table["impressions"] = df_table["impressions"].apply(lambda x: f"{x:,}")
        df_table["engagement"] = df_table["engagement"].apply(lambda x: f"{x:,}")
        df_table["reach"] = df_table["reach"].apply(lambda x: f"{x:,}")
        df_table = df_table.rename(columns={"campaign_name": "Publicación", "platform": "Plataforma", "impressions": "Impresiones", "engagement": "Interacciones", "reach": "Alcance"})
        
    if platform_key == "meta_organic":
        st.markdown("### Ranking: top publicaciones por interacciones (Meta)")
        post_metric = "engagement" if df_curr["engagement"].sum() else ("reach" if df_curr["reach"].sum() else "impressions")
        top_posts = df_curr.groupby("campaign_name").agg({
            "impressions": "sum", "engagement": "sum", "reach": "sum"
        }).reset_index().sort_values(post_metric, ascending=False).head(8)
        top_posts = top_posts.rename(columns={
            "campaign_name": "Publicación",
            "impressions": "Impresiones",
            "engagement": "Interacciones",
            "reach": "Alcance",
        })
        show_theme_table(top_posts)

        text_col = "caption" if "caption" in df_curr.columns else "campaign_name"
        hashtag_rows = []
        for row in df_curr.itertuples(index=False):
            text = str(getattr(row, text_col, ""))
            for tag in re.findall(r"#[\wáéíóúÁÉÍÓÚñÑ]+", text):
                hashtag_rows.append({
                    "hashtag": tag.lower(),
                    "posts": 1,
                    "views": getattr(row, "impressions", 0),
                    "likes": getattr(row, "likes", 0),
                    "comments": getattr(row, "comments", 0),
                })
        if hashtag_rows:
            hashtag_df = pd.DataFrame(hashtag_rows).groupby("hashtag").agg({
                "posts": "sum", "views": "sum", "likes": "sum", "comments": "sum"
            }).reset_index().sort_values(["views", "likes"], ascending=False).head(10)
            hashtag_df = hashtag_df.rename(columns={
                "hashtag": "Hashtag",
                "posts": "Posts",
                "views": "Visualizaciones",
                "likes": "Me gusta",
                "comments": "Comentarios",
            })
            st.markdown("### Ranking de hashtags (Instagram)")
            show_theme_table(hashtag_df)

        st.dataframe(df_table, width="stretch", hide_index=True)
