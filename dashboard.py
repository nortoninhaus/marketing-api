# ponytail: simple, dynamic marketing dashboard connecting to the API directly with period comparison and custom CSS styling
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import json
import os
import re
import textwrap
import calendar
import html
import hashlib
import hmac
import time
import altair as alt
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
import jwt
from google.cloud import firestore

# Load env variables for local defaults
load_dotenv()

# Import configurations, authenticators, API wrappers, and utilities
from dashboard.config import (
    DEFAULT_API_KEY,
    DEFAULT_API_URL,
    CAMPAIGN_DATA_TIMEOUT,
    FIREBASE_PROJECT_ID,
    DASHBOARD_USERS_COLLECTION,
    DASHBOARD_JWT_SECRET,
    DASHBOARD_JWT_HOURS,
    DASHBOARD_AUTH_COOKIE,
    DASHBOARD_AUTH_QUERY_PARAM,
    PASSWORD_ALGORITHM,
    PASSWORD_ITERATIONS,
    PLATFORM_TYPES,
    META_PUBLISHER_LABELS,
    DIMENSION_VALUE_LABELS,
)

from dashboard.auth import (
    get_firestore_client,
    hash_dashboard_password,
    verify_dashboard_password,
    normalize_dashboard_accounts,
    authenticate_dashboard_user,
    create_dashboard_token,
    decode_dashboard_token,
    dashboard_query_token,
    clear_dashboard_query_token,
    dashboard_auth_cookie_bridge,
    dashboard_allowed_account_ids,
    filter_dashboard_connections,
    connection_account_label,
    require_dashboard_login,
    dashboard_auth_self_check,
)

from dashboard.api import (
    fetch_connections_from_api,
    fetch_schema_from_api,
    fetch_campaign_data_from_api,
    fetch_meta_aggregate_insights,
    fetch_meta_ad_previews,
    fetch_meta_filter_rows,
    process_api_response,
)

from dashboard.utils import (
    extract_metric,
    translate_dimension_value,
    translate_meta_result_indicator,
    clean_region_name,
    clean_campaign_name,
    meta_base_campaign_name,
    meta_campaigns_with_impressions,
    select_meta_ad_winners,
    fetch_meta_detail_rows,
    enrich_meta_campaign_summary,
    build_meta_campaign_total_row,
    meta_detail_table_config,
    dashboard_filter_options,
    apply_dashboard_filters,
    campaign_title,
    get_prior_month_range,
    get_current_month_range,
)

from dashboard.ui import (
    theme_chart,
    show_theme_table,
    get_kpi_card_html,
    render_dashboard_empty_state,
)

from dashboard.analytics import (
    log_query_execution,
    log_filter_application,
    log_demographics_check,
)

DASHBOARD_CACHE_VERSION = 4


if os.getenv("DASHBOARD_AUTH_SELF_CHECK") == "1":
    dashboard_auth_self_check()
    raise SystemExit("dashboard auth self-check passed")


def toggle_theme():
    st.session_state["theme_switch"] = not st.session_state.get("theme_switch", True)


# Determine sidebar collapse state dynamically to hide it automatically once query runs
initial_sidebar = "collapsed" if st.session_state.get("query_run", False) else "expanded"

# Page config to force wide layout
st.set_page_config(
    page_title="Inhaus Marketing API - Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state=initial_sidebar
)

theme_mode = "Oscuro" if st.session_state.get("theme_switch", True) else "Claro"
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
/* When sidebar is expanded, hide stHeader completely so it never creates a ghost/double button */
.stApp:has([data-testid="stSidebar"][aria-expanded="true"]) [data-testid="stHeader"] {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
}

/* Reset stSidebarCollapseButton span container to prevent double borders */
[data-testid="stSidebarCollapseButton"],
span[data-testid="stSidebarCollapseButton"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* Sidebar collapse/expand toggle button styling & position */
[data-testid="stHeader"] {
    background-color: transparent !important;
    box-shadow: none !important;
    height: 0px !important;
    min-height: 0px !important;
    overflow: visible !important;
    position: absolute !important;
    top: 21px !important;
    left: 16px !important;
    z-index: 9999 !important;
}

[data-testid="stHeader"] button,
[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] button {
    background: rgba(2, 86, 158, 0.12) !important;
    border: 1px solid rgba(2, 86, 158, 0.3) !important;
    border-radius: 8px !important;
    color: #02569e !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

[data-testid="stHeader"] button:hover,
[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] button:hover {
    background: #02569e !important;
    color: #FFFFFF !important;
    border-color: #02569e !important;
}

[data-testid="stHeader"] button svg,
[data-testid="stHeader"] [data-testid="stSidebarCollapseButton"] button svg {
    color: currentColor !important;
    fill: currentColor !important;
    stroke: currentColor !important;
    width: 18px !important;
    height: 18px !important;
}

/* Sidebar close button inside sidebar header */
[data-testid="stSidebarHeader"] {
    min-height: 0px !important;
    height: auto !important;
    padding: 12px 16px 0px 16px !important;
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarHeader"] button {
    position: static !important;
    top: auto !important;
    left: auto !important;
    margin: 0 !important;
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 8px !important;
    color: #8A97A8 !important;
    width: 32px !important;
    height: 32px !important;
    min-width: 32px !important;
    min-height: 32px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarHeader"] [data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarHeader"] button:hover {
    background: rgba(255, 255, 255, 0.14) !important;
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button svg,
[data-testid="stSidebarHeader"] button svg {
    color: currentColor !important;
    fill: currentColor !important;
    stroke: currentColor !important;
    width: 18px !important;
    height: 18px !important;
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
.block-container,
[data-testid="stMainBlockContainer"] {
    padding-top: 0.5rem !important;
    padding-bottom: 2rem !important;
    position: relative !important;
}

/* Collapse empty download slot container completely in block flow */
.block-container > div:first-child:has(> div:empty),
.block-container > div[data-testid="stElementContainer"]:has(> div:empty),
[data-testid="stMainBlockContainer"] > div:first-child:has(> div:empty) {
    display: none !important;
    height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
}

/* Position download slot inline inside header next to API Directa */
.block-container > div[data-testid="stElementContainer"]:has([data-testid="stPopover"]),
[data-testid="stMainBlockContainer"] > div[data-testid="stElementContainer"]:has([data-testid="stPopover"]),
div[data-testid="stElementContainer"]:has([data-testid="stPopover"]),
div[data-testid="stElementContainer"]:has([data-testid="stPopoverButton"]) {
    position: absolute !important;
    left: auto !important;
    right: 140px !important;
    top: 22px !important;
    z-index: 9999 !important;
    margin: 0 !important;
    padding: 0 !important;
    width: auto !important;
    height: 0 !important;
    display: flex !important;
    justify-content: flex-end !important;
}

div[data-testid="stElementContainer"]:has([data-testid="stPopover"]) > div,
[data-testid="stPopover"],
[data-testid="stPopoverButton"] {
    position: relative !important;
    left: auto !important;
    right: auto !important;
    width: auto !important;
    display: inline-flex !important;
}

[data-testid="stPopoverButton"],
[data-testid="stDownloadButton"] button {
    background-color: #02569e !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 4px 12px !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    height: 28px !important;
    min-height: 28px !important;
    line-height: 1 !important;
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    box-shadow: 0 2px 6px rgba(2, 86, 158, 0.3) !important;
}
[data-testid="stPopoverButton"] *,
[data-testid="stDownloadButton"] button * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}
[data-testid="stPopoverBody"] {
    background-color: #FFFFFF !important;
}
[data-testid="stPopoverBody"] > div {
    background-color: #FFFFFF !important;
}

/* Sidebar Wrapper */
[data-testid="stSidebar"] {
    background-color: #121823 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    position: relative !important;
}
[data-testid="stSidebarHeader"] {
    min-height: 0px !important;
    height: auto !important;
    padding: 0px !important;
}
[data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
    padding-bottom: 80px !important;
}
[data-testid="stSidebar"] [data-testid="stImage"] {
    display: flex !important;
    justify-content: center !important;
    margin: -1rem auto 10px !important;
}
[data-testid="stSidebar"] [data-testid="stImage"] > div {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stImage"] img {
    display: block !important;
    margin: 0 auto !important;
}
[data-testid="stSidebarHeader"] {
    position: relative !important;
    overflow: visible !important;
}
[data-testid="stSidebarHeader"] button {
    position: absolute !important;
    top: 10px !important;
    right: -17px !important;
    z-index: 1000 !important;
    width: 34px !important;
    height: 34px !important;
    padding: 0 !important;
    border: 1px solid rgba(255,255,255,0.16) !important;
    border-radius: 8px !important;
    background: #0F172A !important;
    color: #FFFFFF !important;
    box-shadow: 0 5px 14px rgba(0,0,0,0.18) !important;
}
[data-testid="stSidebarHeader"] button svg,
[data-testid="stSidebarHeader"] button svg * {
    width: 18px !important;
    height: 18px !important;
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}
.inhaus-logout-btn {
    border: 1px solid rgba(255, 75, 75, 0.4) !important;
    color: #FF4B4B !important;
    background-color: transparent !important;
    width: 100% !important;
    transition: all 0.3s ease !important;
}
.inhaus-logout-btn:hover {
    border-color: #FF4B4B !important;
    background-color: rgba(255, 75, 75, 0.1) !important;
    color: #FF4B4B !important;
}


:root {
    --inhaus-polygon-gradient: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Cdefs%3E%3ClinearGradient id='g' x1='0' y1='0' x2='20.5' y2='20.5' gradientUnits='userSpaceOnUse'%3E%3Cstop stop-color='white'/%3E%3Cstop offset='.84506' stop-color='white' stop-opacity='.99'/%3E%3Cstop offset='.9506' stop-color='white' stop-opacity='0'/%3E%3Cstop offset='1' stop-color='white' stop-opacity='0'/%3E%3C/linearGradient%3E%3C/defs%3E%3Cpath d='M0 0H40L0 40V0Z' fill='url(%23g)'/%3E%3C/svg%3E");
}

.inhaus-theme-wipe {
    position: fixed;
    inset: 0;
    z-index: 2147483647;
    pointer-events: none;
    mask: var(--inhaus-polygon-gradient) top left / 0 no-repeat;
    mask-origin: top left;
    animation: inhaus-theme-scale 1.5s cubic-bezier(0.16, 1, 0.3, 1) both;
}

.inhaus-theme-wipe.inhaus-to-dark { background: #0A0D13; }
.inhaus-theme-wipe.inhaus-to-light { background: #F8F9FC; }

::view-transition-group(root) {
    animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);
}

::view-transition-new(root) {
    mask: var(--inhaus-polygon-gradient) top left / 0 no-repeat;
    mask-origin: top left;
    animation: inhaus-theme-scale 1.5s both;
}

::view-transition-old(root) {
    animation: none;
    z-index: -1;
}

@keyframes inhaus-theme-scale {
    to { mask-size: 200vmax; }
}

@media (prefers-reduced-motion: reduce) {
    ::view-transition-group(root),
    ::view-transition-new(root),
    .inhaus-theme-wipe {
        animation-duration: 1ms !important;
    }
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
    position: relative;
}
.custom-header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    min-width: fit-content !important;
}
.agency {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-left: 44px;
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
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    min-width: fit-content !important;
}
.stamp .live {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #02569e;
    box-shadow: 0 0 0 0 rgba(2,86,158,0.6);
    animation: pulse 2s infinite;
}
@keyframes pulse {
0% { box-shadow: 0 0 0 0 rgba(2,86,158,0.5); }
70% { box-shadow: 0 0 0 8px rgba(2,86,158,0); }
100% { box-shadow: 0 0 0 0 rgba(2,86,158,0); }
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
color: #02569e;
font-size: 24px;
margin-top: 20px;
font-weight: 800;
}
.spinner {
border: 6px solid rgba(255, 255, 255, 0.1);
width: 70px;
height: 70px;
border-radius: 50%;
border-left-color: #02569e;
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
    color: #02569e;
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
    color: #02569e;
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
    background: rgba(2,86,158,0.14);
    color: #02569e;
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

/* Multiselect tag styling */
[data-baseweb="tag"],
[data-baseweb="select"] [data-baseweb="tag"] {
    background-color: #02569e !important;
    border-radius: 6px !important;
    max-width: 100% !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    padding: 2px 8px !important;
    box-sizing: border-box !important;
}
[data-baseweb="tag"] *,
[data-baseweb="select"] [data-baseweb="tag"] *,
[data-baseweb="select"] [data-baseweb="tag"] span,
[data-baseweb="select"] [data-baseweb="tag"] div,
[data-baseweb="select"] [data-baseweb="tag"] svg,
[data-baseweb="select"] [data-baseweb="tag"] path {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}
[data-baseweb="tag"] > span,
[data-baseweb="tag"] [title],
[data-baseweb="select"] [data-baseweb="tag"] span {
    text-align: left !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    max-width: 180px !important;
    min-width: 0 !important;
    flex: 1 1 auto !important;
    margin: 0 !important;
    padding: 0 4px 0 2px !important;
    display: inline-block !important;
}

</style>
""", unsafe_allow_html=True)

if theme_mode == "Claro":
    st.markdown("""
    <style>
    .stApp { background-color: #F8F9FC !important; color: #1E293B !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF !important; border-right: 1px solid rgba(15,23,42,0.08) !important; }
    
    /* Invert logo in sidebar for light mode */
    [data-testid="stSidebar"] img {
        filter: invert(1) brightness(0.25) !important;
    }

    .st-key-login_card {
        background: #FFFFFF !important;
        border-color: rgba(15,23,42,0.14) !important;
        box-shadow: 0 12px 30px rgba(15,23,42,0.08) !important;
    }
    .st-key-login_card [data-testid="stTextInputRootElement"] {
        background: #FFFFFF !important;
        border-color: rgba(15,23,42,0.18) !important;
    }
    .st-key-login_card [data-testid="stTextInputRootElement"]:focus-within {
        border-color: #02569e !important;
        box-shadow: 0 0 0 1px #02569e !important;
    }
    .st-key-login_card [data-testid="stTextInputIcon"],
    .st-key-login_card [data-testid="stTextInputRootElement"] > button,
    .st-key-login_card [data-testid="stTextInputRootElement"] [data-testid="stIconMaterial"] {
        background: transparent !important;
        color: #475569 !important;
    }

    /* Fix sidebar close button (<<) in Light Mode */
    [data-testid="stSidebarHeader"] button,
    [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {
        background: #F1F5F9 !important;
        border: 1px solid rgba(15,23,42,0.15) !important;
        color: #0F172A !important;
    }
    [data-testid="stSidebarHeader"] button svg,
    [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button svg {
        fill: #0F172A !important;
        stroke: #0F172A !important;
        color: #0F172A !important;
    }
    [data-testid="stSidebarHeader"] button:hover,
    [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover {
        background: #02569e !important;
        color: #FFFFFF !important;
        border-color: #02569e !important;
    }
    [data-testid="stSidebarHeader"] button:hover svg,
    [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button:hover svg {
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        color: #FFFFFF !important;
    }
    
    /* Globally override input, textarea, and select box colors in light mode */
    input,
    textarea,
    [data-baseweb="input"],
    [data-baseweb="input"] > div,
    [data-baseweb="select"],
    [data-baseweb="select"] > div:first-child,
    [data-testid="stDateInput"] > div {
        background: #FFFFFF !important;
        color: #0F172A !important;
        border-color: rgba(15,23,42,0.16) !important;
    }
    input::placeholder,
    textarea::placeholder { color: #475569 !important; }

    /* Fix selectbox placeholders and value containers in Light Mode */
    [data-baseweb="select"] [data-baseweb="value-container"] div:not([data-baseweb="tag"]):not([data-baseweb="tag"] *),
    [data-baseweb="select"] [data-baseweb="value-container"] span:not([data-baseweb="tag"]):not([data-baseweb="tag"] *),
    [data-baseweb="select"] [data-baseweb="placeholder"],
    [data-baseweb="select"] input::placeholder,
    [data-baseweb="select"] [role="combobox"] * {
        color: #0F172A !important;
    }
    
    /* Ensure inner selectbox containers don't create opaque white overlays over tags */
    [data-baseweb="select"] div:not([data-baseweb="tag"]):not([data-baseweb="tag"] *) {
        background-color: transparent !important;
        color: #0F172A !important;
    }
    
    /* Ensure text inside selectbox container is dark, except multiselect tags */
    [data-baseweb="select"] span:not([data-baseweb="tag"]):not([data-baseweb="tag"] *),
    [data-baseweb="select"] input {
        color: #0F172A !important;
    }
    [data-baseweb="select"] svg:not([data-baseweb="tag"] *):not([data-baseweb="tag"]) {
        fill: #0F172A !important;
    }
    
    /* Multiselect tags in light mode */
    [data-baseweb="tag"],
    [data-baseweb="select"] [data-baseweb="tag"],
    [data-baseweb="select"] span[data-baseweb="tag"] {
        background: #02569e !important;
        background-color: #02569e !important;
        border-radius: 6px !important;
        max-width: 100% !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        padding: 2px 8px !important;
        margin: 2px 4px 2px 0 !important;
        box-sizing: border-box !important;
        position: relative !important;
        z-index: 2 !important;
    }
    [data-baseweb="tag"] *,
    [data-baseweb="select"] [data-baseweb="tag"] *,
    [data-baseweb="select"] [data-baseweb="tag"] span,
    [data-baseweb="select"] [data-baseweb="tag"] div,
    [data-baseweb="select"] [data-baseweb="tag"] svg,
    [data-baseweb="select"] [data-baseweb="tag"] path {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }
    [data-baseweb="tag"] > span,
    [data-baseweb="tag"] [title],
    [data-baseweb="select"] [data-baseweb="tag"] span {
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: 180px !important;
        min-width: 0 !important;
        flex: 1 1 auto !important;
        margin: 0 !important;
        padding: 0 4px 0 2px !important;
        display: inline-block !important;
    }
    
    /* Dropdown popover menu in light mode */
    [data-baseweb="popover"] {
        background-color: #FFFFFF !important;
    }
    [data-baseweb="menu"] {
        background-color: #FFFFFF !important;
        border: 1px solid rgba(15,23,42,0.08) !important;
    }
    [data-baseweb="menu"] [role="option"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
    }
    [data-baseweb="menu"] [role="option"]:hover,
    [data-baseweb="menu"] [role="option"][aria-selected="true"] {
        background-color: #F1F5F9 !important;
        color: #02569e !important;
    }
    
    /* Expander / Accordion styling in Light Mode */
    [data-testid="stExpander"],
    details,
    [data-baseweb="accordion"],
    div[data-testid="stExpanderDetails"] {
        background-color: #FFFFFF !important;
        border: 1px solid rgba(15,23,42,0.12) !important;
        border-radius: 10px !important;
        color: #0F172A !important;
    }
    summary,
    details summary,
    [data-testid="stExpander"] summary {
        background-color: #F8F9FC !important;
        color: #0F172A !important;
        border-radius: 10px !important;
    }
    summary *,
    details summary *,
    [data-testid="stExpander"] summary * {
        color: #0F172A !important;
        fill: #0F172A !important;
        stroke: #0F172A !important;
    }
    
    /* Buttons in Light Mode (Consultar API, submit buttons, form buttons) */
    .stButton > button,
    [data-testid="stFormSubmitButton"] > button,
    button[kind="primary"],
    button[kind="secondary"] {
        background-color: #02569e !important;
        color: #FFFFFF !important;
        border: 1px solid #02569e !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
    .stButton > button *,
    [data-testid="stFormSubmitButton"] > button * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    .stButton > button:hover,
    [data-testid="stFormSubmitButton"] > button:hover {
        background-color: #01437d !important;
        border-color: #01437d !important;
        color: #FFFFFF !important;
    }

    /* Checkbox labels and icons in Light Mode */
    [data-testid="stCheckbox"] label,
    [data-testid="stCheckbox"] span,
    [data-testid="stCheckbox"] p {
        color: #0F172A !important;
    }
    [data-testid="stCheckbox"] input:checked + div {
        background-color: #02569e !important;
        border-color: #02569e !important;
    }

    /* Sidebar collapse button and all header/sidebar icon SVGs */
    [data-testid="stExpandSidebarButton"],
    [data-testid="stExpandSidebarButton"] *,
    button[aria-label="Close sidebar"] svg,
    button[aria-label="Open sidebar"] svg,
    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarHeader"] svg,
    button[title="Close sidebar"] svg,
    .stSidebarCollapseButton svg,
    button[aria-label="Close sidebar"] svg *,
    button[aria-label="Open sidebar"] svg *,
    [data-testid="stSidebarCollapseButton"] svg *,
    [data-testid="stSidebarHeader"] svg *,
    button[title="Close sidebar"] svg *,
    .stSidebarCollapseButton svg * {
        color: #0F172A !important;
        fill: #0F172A !important;
        stroke: #0F172A !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebarHeader"] button {
        background: #0F172A !important;
        color: #FFFFFF !important;
        border-color: rgba(15,23,42,0.18) !important;
    }
    [data-testid="stSidebarHeader"] button svg,
    [data-testid="stSidebarHeader"] button svg * {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
    }
    
    /* Keep tooltip content readable (white text on dark background) */
    div[data-testid="stTooltipContent"] *,
    div[role="tooltip"] *,
    .stTooltipHoverTarget * {
        color: #FFFFFF !important;
    }
    
    [data-testid="stHeader"] button, [data-testid="stHeader"] svg { color: #0F172A !important; fill: #0F172A !important; stroke: #0F172A !important; }
    h1, h2, h3, h4, .sipy-word { color: #0F172A !important; }
    .custom-header { border-bottom-color: rgba(15,23,42,0.08); }
    .agency img, .inhaus-login-logo { filter: invert(1) brightness(0.25); }
    .agency .div-bar { background: rgba(15,23,42,0.12); }
    .agency .who, .stamp, .lede, .kpi .lab, .hero-card .lab { color: #64748B; }
    .loading-overlay { background-color: rgba(248,249,252,0.95); }
    .spinner { border-color: rgba(15,23,42,0.08); border-left-color: #02569e; }
    .loading-text, .eyebrow, .hero-card .big { color: #02569e; }
    .hero-card { background: linear-gradient(165deg, #FFFFFF, #F1F5F9); border-color: rgba(15,23,42,0.08); color: #1E293B; box-shadow: 0 4px 15px rgba(15,23,42,0.04); }
    .kpi, .stTable { background: #FFFFFF !important; border-color: rgba(15,23,42,0.08) !important; color: #1E293B; box-shadow: 0 4px 12px rgba(15,23,42,0.03); }
    .kpi .val { color: #0F172A; }
    .kpi .sub { color: #94A3B8; }
    .delta.up { background: rgba(2,86,158,0.1); color: #02569e; }
    .delta.down { background: rgba(220,38,38,0.1); color: #DC2626; }
    .stApp label, .stApp p, [data-testid="stWidgetLabel"], [data-testid="stMarkdownContainer"] { color: #0F172A; }
    [data-testid="stDataFrame"] { background: #FFFFFF !important; color: #0F172A !important; }
    .theme-table { background: #FFFFFF; color: #0F172A; border-color: rgba(15,23,42,0.08); }
    .theme-table th, .theme-table td { border-bottom-color: rgba(15,23,42,0.08); }
    .theme-table th { background: #F1F5F9; color: #64748B; }
    
    /* Specific override for the logout button in light mode to keep it red */
    .inhaus-logout-btn {
        color: #FF4B4B !important;
        background-color: transparent !important;
        border-color: rgba(255, 75, 75, 0.4) !important;
    }
    .inhaus-logout-btn:hover {
        background-color: rgba(255, 75, 75, 0.1) !important;
        border-color: #FF4B4B !important;
    }
    </style>
    """, unsafe_allow_html=True)

st.html("""
<script>
(function() {
    const parentDoc = window.parent.document;
    const parentWin = window.parent;
    const version = "polygon-gradient-v7";
    if (parentDoc.__inhausSidebarEnhancer === version) return;
    parentDoc.__inhausSidebarEnhancer = version;

    if (!parentWin.__inhausNavListener) {
        parentWin.__inhausNavListener = (event) => {
            if (event.source !== parentWin && event.data && event.data.type === "inhaus-navigate" && event.data.url) {
                parentWin.location.href = event.data.url;
            }
        };
        parentWin.addEventListener("message", parentWin.__inhausNavListener);
    }

    const collapseSidebar = () => {
        const collapseBtn = parentDoc.querySelector(
            'button[aria-label="Close sidebar"], button[title="Close sidebar"]'
        );
        if (collapseBtn) collapseBtn.click();
    };

    const showThemeFallback = (goingDark) => {
        const wipe = parentDoc.createElement("div");
        wipe.className = "inhaus-theme-wipe " + (goingDark ? "inhaus-to-dark" : "inhaus-to-light");
        parentDoc.body.appendChild(wipe);
        wipe.addEventListener("animationend", () => wipe.remove(), { once: true });
        setTimeout(() => wipe.remove(), 1800);
    };

    const waitForThemeChange = (expectedIcon) => new Promise((resolve) => {
        let observer;
        let timeout;
        const changed = () => Array.from(
            parentDoc.querySelectorAll('.st-key-theme_switch_button button')
        ).some((button) => button.textContent.includes(expectedIcon));
        const done = () => {
            if (observer) observer.disconnect();
            if (timeout) parentWin.clearTimeout(timeout);
            resolve();
        };
        if (changed()) {
            done();
            return;
        }
        observer = new parentWin.MutationObserver(() => {
            if (changed()) done();
        });
        observer.observe(parentDoc.body, { childList: true, subtree: true, characterData: true });
        timeout = parentWin.setTimeout(done, 2000);
    });

    const startThemeTransition = (event) => {
        const button = event.target.closest("button");
        if (!button || !button.textContent.match(/[☀☾]/)) return;
        const goingDark = button.textContent.includes("☀");
        if (typeof parentDoc.startViewTransition === "function") {
            try {
                parentDoc.startViewTransition(
                    () => waitForThemeChange(goingDark ? "☾" : "☀")
                );
                return;
            } catch (_) {
                // Fall through for browsers that expose but cannot start view transitions.
            }
        }
        showThemeFallback(goingDark);
    };

    const tagLogoutButton = () => {
        const buttons = parentDoc.querySelectorAll('[data-testid="stSidebar"] button');
        buttons.forEach(btn => {
            if (btn.textContent && btn.textContent.includes("Cerrar Sesión")) {
                btn.classList.add("inhaus-logout-btn");
                const container = btn.closest(".element-container");
                if (container) {
                    container.classList.add("inhaus-logout-container");
                }
            }
        });
    };
    tagLogoutButton();
    setInterval(tagLogoutButton, 300);

    parentDoc.addEventListener("click", startThemeTransition, true);
    parentDoc.addEventListener("pointerdown", (event) => {
        const sidebar = event.target.closest('[data-testid="stSidebar"]');
        const sidebarControl = event.target.closest('[data-testid="stSidebarCollapseButton"], button[aria-label="Open sidebar"], button[aria-label="Close sidebar"]');
        if (!sidebar && !sidebarControl) collapseSidebar();
    });
})();
</script>
""", unsafe_allow_javascript=True)

theme_icon = "☾" if theme_mode == "Oscuro" else "☀"
dashboard_user = require_dashboard_login(theme_icon, toggle_theme)
current_username = dashboard_user.get("username") if dashboard_user else None

# SIDEBAR FILTERS (Acts as the collapsible Hamburger Menu on the left)
st.sidebar.image("https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg", width=180)
st.sidebar.button(theme_icon, key="theme_switch_button", help="Cambiar tema", on_click=toggle_theme)

st.sidebar.markdown("### Configuración de Consulta")

# Hidden admin defaults
api_key = DEFAULT_API_KEY
client_id = dashboard_user.get("client_id") or "client_1"
user_id = dashboard_user.get("user_id") or "user_1"

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
    default=[],
)
if not selected_platform_labels:
    st.sidebar.warning("Selecciona al menos una plataforma.")
    if st.session_state.get("query_run", False):
        st.session_state["query_run"] = False
        st.rerun()
    st.session_state["query_run"] = False
    render_dashboard_empty_state("Abre el menú lateral y elige plataforma, cuenta y rango de fechas para cargar el reporte.")
    st.stop()

selected_platform_keys = [k for k, v in platform_labels.items() if v in selected_platform_labels]
platform_configs = []

for selected_platform_key in selected_platform_keys:
    platform_label = platform_labels[selected_platform_key]
    with st.sidebar.expander(platform_label, expanded=len(selected_platform_keys) == 1):
        sidebar_cache = st.session_state.setdefault("sidebar_api_cache", {})
        connections = fetch_connections_from_api(selected_platform_key, client_id, api_key)
        connections = filter_dashboard_connections(connections, dashboard_user, selected_platform_key)
        allowed_account_ids = dashboard_allowed_account_ids(dashboard_user, selected_platform_key)
        if allowed_account_ids == []:
            st.warning("Tu usuario no tiene cuentas asignadas para esta plataforma.")
            continue
        if connections:
            connection_options = {connection_account_label(c, selected_platform_key): c["account_id"] for c in connections}
            selected_conn_label = st.selectbox("Cuentas Conectadas", [""] + list(connection_options.keys()), key=f"conn_{selected_platform_key}")
            default_account_id = connection_options.get(selected_conn_label, "")
        else:
            fallback_accounts = allowed_account_ids or []
            fallback_account_options = {connection_account_label({"account_id": account_id}, selected_platform_key): account_id for account_id in fallback_accounts}
            selected_fallback_label = st.selectbox("Cuentas permitidas", [""] + list(fallback_account_options), key=f"allowed_account_{selected_platform_key}") if allowed_account_ids else ""
            default_account_id = fallback_account_options.get(selected_fallback_label, "")

        if connections:
            account_id_value = default_account_id
        else:
            account_key = f"account_{selected_platform_key}"
            prev_conn_key = f"prev_conn_{selected_platform_key}"
            if st.session_state.get(prev_conn_key) != default_account_id:
                st.session_state[account_key] = default_account_id
                st.session_state[prev_conn_key] = default_account_id
            account_id_value = default_account_id if allowed_account_ids else st.text_input("ID de cuenta", key=account_key)
        if not account_id_value:
            st.warning("Selecciona una cuenta.")
            continue
        schema_key = ("schema", DASHBOARD_CACHE_VERSION, selected_platform_key, api_key)
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
        if selected_platform_key == "meta_ads":
            applied_api_filters = st.session_state.get("meta_applied_api_filters", {})
            if applied_api_filters:
                opt_filters_value["filters"] = applied_api_filters
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

if not platform_configs:
    if st.session_state.get("query_run", False):
        st.session_state["query_run"] = False
        st.rerun()
    st.session_state["query_run"] = False
    render_dashboard_empty_state("Selecciona una cuenta disponible en el menú lateral para continuar.")
    st.stop()

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
default_start, _ = get_current_month_range(today)
date_range = st.sidebar.date_input("Rango de Fechas a Consultar", [default_start, today])
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
else:
    start_date, end_date = default_start, today

# Execute Button in Sidebar to prevent auto-loading until clicked
execute_query = st.sidebar.button("🚀 Consultar API", use_container_width=True)

if st.sidebar.button("🔒 Cerrar Sesión", key="logout_button", use_container_width=True):
    st.session_state.pop("dashboard_auth_token", None)
    st.session_state.pop("dashboard_user", None)
    dashboard_auth_cookie_bridge(clear=True)
    st.stop()

# MAIN DISPLAY (Occupies full wide screen)
download_slot = st.empty()

# Header
st.markdown(f"""
<div class="custom-header">
    <div class="agency">
        <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg" alt="Inhaus">
        <span class="div-bar"></span>
        <span class="who">Dashboard de Pauta &middot; Conexión de API</span>
    </div>
    <div class="custom-header-right">
        <span class="stamp"><span class="live"></span> API Directa</span>
    </div>
</div>
""", unsafe_allow_html=True)

if execute_query:
    log_query_execution(
        current_username,
        platform_key,
        account_id,
        start_date.isoformat(),
        end_date.isoformat(),
        write_to_bq,
    )
    st.session_state.query_run = True
    st.session_state.force_query_fetch = True
    st.rerun()

if not st.session_state.get("query_run", False):
    render_dashboard_empty_state("Configura tus parámetros de consulta en el menú lateral y presiona Consultar API.")
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
        standard_metrics = ["impressions", "clicks", "spend", "conversions", "lead", "reach", "post_engagement", "__results__", "cost_per_result"]
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
    DASHBOARD_CACHE_VERSION,
    client_id, user_id,
    start_date.isoformat(), end_date.isoformat(),
    bool(write_to_bq), tuple(query_configs),
)

st.session_state.setdefault("dashboard_query_cache", {})
force_query_fetch = st.session_state.pop("force_query_fetch", False)
if force_query_fetch:
    st.session_state["active_query_key"] = query_key
active_query_key = st.session_state.get("active_query_key", query_key)
if active_query_key[0] != DASHBOARD_CACHE_VERSION:
    active_query_key = query_key
    st.session_state["active_query_key"] = query_key

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
            cfg["opt_filters"], False, api_key, show_errors=False
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
        "request_metrics": platform_configs[0]["request_metrics"],
        "request_dimensions": platform_configs[0]["request_dimensions"],
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

for frame in (df_curr, df_prev):
    if "results" not in frame.columns:
        frame["results"] = frame.get("__results__", 0)
    if "cost_per_result" not in frame.columns:
        frame["cost_per_result"] = 0.0
    if "result_indicator" not in frame.columns:
        frame["result_indicator"] = ""
    if "post_engagement" not in frame.columns:
        frame["post_engagement"] = 0

raw_df_curr = df_curr.copy()

if platform_key == "meta_ads" and not df_curr.empty:
    eligible_campaigns = meta_campaigns_with_impressions(df_curr)
    eligible_previous_campaigns = meta_campaigns_with_impressions(df_prev)
    df_curr = df_curr[
        df_curr["campaign_name"].astype(str).apply(meta_base_campaign_name).isin(eligible_campaigns)
    ].copy()
    if not df_prev.empty:
        df_prev = df_prev[
            df_prev["campaign_name"].astype(str).apply(meta_base_campaign_name).isin(
                eligible_previous_campaigns
            )
        ].copy()

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
    if not raw_df_curr.empty:
        st.warning("ℹ️ La API retornó registros para el periodo seleccionado, pero ninguna campaña registra impresiones o métricas de alcance relevantes en estas fechas. Intenta ajustar el rango de fechas o los filtros.")
    else:
        st.error("No se recibió información de la API para el periodo actual. Verifica las credenciales, plataforma o ID de cuenta en el menú lateral.")
    st.stop()
else:
    applied_campaign_filter = []
    applied_adset_filter = []
    applied_ad_filter = "Todos"
    if platform_key == "meta_ads":
        st.session_state.setdefault("meta_filter_rows_cache", {})
        filter_cache_key = (client_id, account_id, api_key)
        if force_query_fetch or filter_cache_key not in st.session_state["meta_filter_rows_cache"]:
            st.session_state["meta_filter_rows_cache"][filter_cache_key] = fetch_meta_filter_rows(client_id, account_id, api_key)
        filter_rows, filter_error = st.session_state["meta_filter_rows_cache"][filter_cache_key]
        meta_filter_df = pd.DataFrame(filter_rows)
        if not meta_filter_df.empty:
            campaign_names = set(df_curr["campaign_name"].dropna().astype(str).apply(meta_base_campaign_name))
            meta_filter_df["base_campaign_name"] = meta_filter_df["campaign_name"].astype(str).apply(meta_base_campaign_name)
            meta_filter_df = meta_filter_df[meta_filter_df["base_campaign_name"].isin(campaign_names)]
        if filter_error:
            st.info(filter_error)

        campaign_col, adset_col, ad_col, apply_col = st.columns([2, 2, 2, 1])
        with campaign_col:
            campaign_options = sorted({
                meta_base_campaign_name(value)
                for value in df_curr["campaign_name"].dropna().astype(str)
                if meta_base_campaign_name(value)
            })
            current_campaign_filter = st.session_state.get("meta_campaign_filter", [])
            if isinstance(current_campaign_filter, str):
                current_campaign_filter = [] if current_campaign_filter == "Todos" else [current_campaign_filter]
            current_campaign_filter = [meta_base_campaign_name(value) for value in current_campaign_filter]
            st.session_state["meta_campaign_filter"] = [value for value in current_campaign_filter if value in campaign_options]
            campaign_filter = st.multiselect("Campañas", campaign_options, key="meta_campaign_filter")

        filtered_meta_rows = meta_filter_df
        if campaign_filter and not filtered_meta_rows.empty:
            filtered_meta_rows = filtered_meta_rows[filtered_meta_rows["base_campaign_name"].isin({meta_base_campaign_name(value) for value in campaign_filter})]
        with adset_col:
            adset_options = dashboard_filter_options(filtered_meta_rows, "adset_name")[1:]
            current_adset_filter = st.session_state.get("meta_adset_filter", [])
            if isinstance(current_adset_filter, str):
                current_adset_filter = [] if current_adset_filter == "Todos" else [current_adset_filter]
            st.session_state["meta_adset_filter"] = [value for value in current_adset_filter if value in adset_options]
            adset_filter = st.multiselect("Conjuntos de anuncios", adset_options, placeholder="Todos", key="meta_adset_filter")

        filtered_ad_rows = filtered_meta_rows
        if adset_filter and not filtered_ad_rows.empty:
            filtered_ad_rows = filtered_ad_rows[filtered_ad_rows["adset_name"].isin(adset_filter)]
        with ad_col:
            ad_options = dashboard_filter_options(filtered_ad_rows, "ad_name")
            if st.session_state.get("meta_ad_filter") not in ad_options:
                st.session_state["meta_ad_filter"] = "Todos"
            ad_filter = st.selectbox("Anuncio", ad_options, key="meta_ad_filter")

        with apply_col:
            st.markdown("<div style='height: 1.75rem'></div>", unsafe_allow_html=True)
            if st.button("Aplicar filtros", type="primary", use_container_width=True):
                applied_api_filters = {}
                if campaign_filter and not filtered_meta_rows.empty:
                    applied_api_filters["campaign.id"] = filtered_meta_rows["campaign_id"].dropna().astype(str).unique().tolist()
                if adset_filter and not filtered_meta_rows.empty:
                    applied_api_filters["adset.id"] = filtered_meta_rows[filtered_meta_rows["adset_name"].isin(adset_filter)]["adset_id"].dropna().astype(str).unique().tolist()
                if ad_filter != "Todos" and not filtered_ad_rows.empty:
                    applied_api_filters["ad.id"] = filtered_ad_rows[filtered_ad_rows["ad_name"] == ad_filter]["ad_id"].dropna().astype(str).unique().tolist()
                log_filter_application(
                    current_username,
                    campaign_filter,
                    adset_filter,
                    ad_filter,
                    applied_api_filters,
                )
                st.session_state["meta_applied_campaign_filter"] = campaign_filter
                st.session_state["meta_applied_adset_filter"] = adset_filter
                st.session_state["meta_applied_ad_filter"] = ad_filter
                if applied_api_filters:
                    st.session_state["meta_applied_api_filters"] = applied_api_filters
                else:
                    st.session_state.pop("meta_applied_api_filters", None)
                st.session_state.force_query_fetch = True
                st.rerun()

        applied_campaign_filter = st.session_state.get("meta_applied_campaign_filter", [])
        applied_adset_filter = st.session_state.get("meta_applied_adset_filter", [])
        if isinstance(applied_adset_filter, str):
            applied_adset_filter = [] if applied_adset_filter == "Todos" else [applied_adset_filter]
        applied_ad_filter = st.session_state.get("meta_applied_ad_filter", "Todos")
        filtered_meta_rows = meta_filter_df
        if applied_campaign_filter and not filtered_meta_rows.empty:
            filtered_meta_rows = filtered_meta_rows[filtered_meta_rows["base_campaign_name"].isin({meta_base_campaign_name(value) for value in applied_campaign_filter})]
        filtered_ad_rows = filtered_meta_rows
    if applied_adset_filter and not filtered_ad_rows.empty:
        filtered_ad_rows = filtered_ad_rows[filtered_ad_rows["adset_name"].isin(applied_adset_filter)]

    detail_curr_rows = []
    detail_prev_rows = []
    if applied_campaign_filter or applied_adset_filter or applied_ad_filter != "Todos":
        st.session_state.setdefault("meta_detail_cache", {})
        detail_cache_key = (
            active_query_key,
            tuple(applied_campaign_filter),
            tuple(applied_adset_filter),
            applied_ad_filter,
            tuple(filtered_meta_rows["campaign_id"].dropna().astype(str).unique().tolist()) if not filtered_meta_rows.empty else (),
            tuple(filtered_ad_rows["adset_id"].dropna().astype(str).unique().tolist()) if not filtered_ad_rows.empty else (),
        )
        if force_query_fetch or detail_cache_key not in st.session_state["meta_detail_cache"]:
            detail_curr_rows, detail_prev_rows = fetch_meta_detail_rows(
                fetch_campaign_data_from_api,
                platform_key,
                client_id,
                user_id,
                account_id,
                start_date,
                end_date,
                prev_start_date,
                prev_end_date,
                active_context.get("request_metrics"),
                active_context.get("request_dimensions", []),
                active_context.get("opt_filters", {}),
                applied_adset_filter,
                applied_ad_filter,
                filtered_meta_rows,
                filtered_ad_rows,
                api_key,
            )
            st.session_state["meta_detail_cache"][detail_cache_key] = (detail_curr_rows, detail_prev_rows)
        else:
            detail_curr_rows, detail_prev_rows = st.session_state["meta_detail_cache"][detail_cache_key]
        if detail_curr_rows:
            df_curr = process_api_response(detail_curr_rows, platform_key, client_id, user_id)
            df_prev = process_api_response(detail_prev_rows, platform_key, client_id, user_id) if detail_prev_rows else pd.DataFrame()
        df_curr = apply_dashboard_filters(df_curr, applied_campaign_filter, applied_adset_filter, applied_ad_filter)
        df_prev = apply_dashboard_filters(df_prev, applied_campaign_filter, applied_adset_filter, applied_ad_filter)
        if applied_campaign_filter:
            st.caption(f"Campañas: {campaign_title(applied_campaign_filter, selected_platform_label)}")

identity_config = (("base_campaign_name", "Campaña"),)
detail_title = "Detalle de Campañas y Resultados"
meta_detail_level = "campaign"
if platform_key == "meta_ads":
    identity_config, detail_title = meta_detail_table_config(
        applied_campaign_filter,
        applied_adset_filter,
        applied_ad_filter,
        set(df_curr.columns) | {"base_campaign_name"},
    )
    meta_detail_level = {
        "base_campaign_name": "campaign",
        "adset_name": "adset",
        "ad_name": "ad",
    }[identity_config[-1][0]]

current_account_insights = []
previous_account_insights = []
campaign_aggregate_insights = []
adset_aggregate_insights = []
ad_aggregate_insights = []
aggregate_errors = []
if platform_key == "meta_ads":
    aggregate_filters = opt_filters.get("filters", {}) if isinstance(opt_filters, dict) else {}
    applied_aggregate_filters = {
        **aggregate_filters,
        **st.session_state.get("meta_applied_api_filters", {}),
    }
    st.session_state.setdefault("meta_insights_cache", {})
    insights_cache_key = (
        active_query_key,
        meta_detail_level,
        json.dumps(applied_aggregate_filters, sort_keys=True),
    )
    if force_query_fetch or insights_cache_key not in st.session_state["meta_insights_cache"]:
        aggregate_requests = [
            ("account", start_date, end_date, current_account_insights, aggregate_filters),
            ("account", prev_start_date, prev_end_date, previous_account_insights, aggregate_filters),
            ("campaign", start_date, end_date, campaign_aggregate_insights, applied_aggregate_filters),
            ("ad", start_date, end_date, ad_aggregate_insights, applied_aggregate_filters),
        ]
        if meta_detail_level == "adset":
            aggregate_requests.append((
                "adset",
                start_date,
                end_date,
                adset_aggregate_insights,
                applied_aggregate_filters,
            ))

        for insight_level, period_start, period_end, target, request_filters in aggregate_requests:
            insight_rows, insight_error = fetch_meta_aggregate_insights(
                client_id,
                account_id,
                period_start,
                period_end,
                insight_level,
                request_filters,
                api_key,
            )
            target.extend(insight_rows)
            if insight_error:
                aggregate_errors.append(insight_error)
        st.session_state["meta_insights_cache"][insights_cache_key] = (
            current_account_insights,
            previous_account_insights,
            campaign_aggregate_insights,
            adset_aggregate_insights,
            ad_aggregate_insights,
            aggregate_errors,
        )
    else:
        (
            current_account_insights,
            previous_account_insights,
            campaign_aggregate_insights,
            adset_aggregate_insights,
            ad_aggregate_insights,
            aggregate_errors,
        ) = st.session_state["meta_insights_cache"][insights_cache_key]
    if aggregate_errors:
        st.info(aggregate_errors[0])

export_slug = re.sub(r"[^a-z0-9]+", "-", selected_platform_label.lower()).strip("-")
export_name = f"{export_slug}_{start_date:%Y-%m-%d}_{end_date:%Y-%m-%d}"
csv_export_frame = {"frame": df_curr}

with download_slot.container():
    with st.popover("Descargar", icon=":material/download:", width="content"):
        # ponytail: PDF export stays disabled until browser capture is reliable.
        st.download_button(
            "Descargar CSV",
            data=lambda: csv_export_frame["frame"].to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{export_name}.csv",
            mime="text/csv;charset=utf-8",
            on_click="ignore",
            icon=":material/download:",
            width="stretch",
        )
# HERO RENDER (Clean, full width, no Sipy logo)
title_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
display_title = campaign_title(applied_campaign_filter, selected_platform_label) if platform_key == "meta_ads" else selected_platform_label
st.markdown(f"""
<h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: {title_color};">{display_title} &middot; {account_disp}</h1>
<p class="lede" style="margin-top: 15px;">
    Resultados del <b>{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}</b>.<br/>
    Comparado contra mes anterior completo: <b>{prev_start_date.strftime('%d/%m/%Y')} al {prev_end_date.strftime('%d/%m/%Y')}</b>.
</p>
""", unsafe_allow_html=True)

# Primary KPI calculations
if platform_type == "ads":
    curr_primary = df_curr["lead"].sum()
    prev_primary = df_prev["lead"].sum() if not df_prev.empty else 0
    primary_label = "Clientes Potenciales"
    total_spend_curr = df_curr["spend"].sum()
    lead_cost_per_result = total_spend_curr / curr_primary if curr_primary > 0 else 0.0
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
if platform_type == "ads":
    st.markdown(f"""
    <div class="hero-card" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;">
      <div><div class="lab">{primary_label}</div><div class="big">{curr_primary:,.0f}</div></div>
      <div><div class="lab">Costo por resultado</div><div class="big">${lead_cost_per_result:,.2f}</div></div>
      <div><div class="lab">Importe gastado</div><div class="big">${total_spend_curr:,.2f}</div></div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div class="hero-card">
      <div class="lab">{primary_label}</div>
      <div class="big">{curr_primary:,}</div>
    </div>
    """, unsafe_allow_html=True)

# Render grid KPIs based on platform type
st.markdown("### Métricas clave con comparación")

if platform_type == "ads":
    total_impressions_curr = df_curr["impressions"].sum()
    total_clicks_curr = df_curr["clicks"].sum()
    total_reach_curr = current_account_insights[0]["reach"] if current_account_insights else None

    avg_ctr_curr = total_clicks_curr / total_impressions_curr if total_impressions_curr > 0 else 0.0
    avg_cpc_curr = total_spend_curr / total_clicks_curr if total_clicks_curr > 0 else 0.0

    total_spend_prev = df_prev["spend"].sum() if not df_prev.empty else 0.0
    total_impressions_prev = df_prev["impressions"].sum() if not df_prev.empty else 0.0
    total_clicks_prev = df_prev["clicks"].sum() if not df_prev.empty else 0.0
    total_reach_prev = previous_account_insights[0]["reach"] if previous_account_insights else None

    avg_ctr_prev = total_clicks_prev / total_impressions_prev if total_impressions_prev > 0 else 0.0
    avg_cpc_prev = total_spend_prev / total_clicks_prev if total_clicks_prev > 0 else 0.0

    kpis_layout = '<div class="kpis">\n'
    kpis_layout += get_kpi_card_html("Inversión Total", f"${total_spend_curr:,.2f}", "Gasto total en pauta", total_spend_curr, total_spend_prev, lower_is_better=True) + "\n"
    kpis_layout += get_kpi_card_html("Impresiones Totales", f"{total_impressions_curr:,}", "Vistas acumuladas", total_impressions_curr, total_impressions_prev) + "\n"
    kpis_layout += get_kpi_card_html("Clics", f"{total_clicks_curr:,}", "Interacciones con anuncios", total_clicks_curr, total_clicks_prev) + "\n"
    reach_value = f"{total_reach_curr:,.0f}" if total_reach_curr is not None else "—"
    kpis_layout += get_kpi_card_html("Alcance Total", reach_value, "Usuarios únicos alcanzados", total_reach_curr or 0.0, total_reach_prev or 0.0) + "\n"
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

if platform_key == "meta_ads" and st.checkbox("Cargar datos demográficos", value=False):
    log_demographics_check(current_username, platform_key, account_id)
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
            else:
                st.info("Meta no devolvió regiones para este rango.")
    else:
        st.info("Meta no devolvió datos oficiales para este rango.")

# Historical charts disabled; uncomment this block to restore them.
# st.markdown("### Tendencias Históricas")
# col_chart_left, col_chart_right = st.columns(2)

# with col_chart_left:
#     df_trend = df_curr.groupby("date").agg({
#         "spend": "sum", "conversions": "sum", "sessions": "sum", "pageviews": "sum", "downloads": "sum", "impressions": "sum", "engagement": "sum"
#     }).reset_index().sort_values("date")

#     # Render custom Altair line chart with Dual Y-Axis so both metrics are visible on their own scale
#     if not df_trend.empty:
#         base = alt.Chart(df_trend).encode(
#             x=alt.X('date:T', axis=alt.Axis(format='%Y-%m-%d', title='Fecha', labelAngle=-45))
#         )

#         if platform_type == "ads":
#             st.markdown("#### Inversión vs. conversiones diarias (eje dual)")
#             left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
#                 y=alt.Y('spend:Q', title='Inversión ($)', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
#             )
#             right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
#                 y=alt.Y('conversions:Q', title='Conversiones', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
#             )
#             dual_chart = alt.layer(left_line, right_line).resolve_scale(
#                 y='independent'
#             ).properties(height=350)
#             st.altair_chart(theme_chart(dual_chart), use_container_width=True)

#         elif platform_type == "analytics":
#             st.markdown("#### Sesiones vs. páginas vistas (eje dual)")
#             left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
#                 y=alt.Y('sessions:Q', title='Sesiones', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
#             )
#             right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
#                 y=alt.Y('pageviews:Q', title='Páginas Vistas', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
#             )
#             dual_chart = alt.layer(left_line, right_line).resolve_scale(
#                 y='independent'
#             ).properties(height=350)
#             st.altair_chart(theme_chart(dual_chart), use_container_width=True)

#         elif platform_type == "app_store":
#             st.markdown("#### Descargas Diarias")
#             line_chart = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
#                 y=alt.Y('downloads:Q', title='Descargas')
#             ).properties(height=350)
#             st.altair_chart(theme_chart(line_chart), use_container_width=True)

#         else: # organic
#             st.markdown("#### Impresiones vs. interacciones (eje dual)")
#             left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
#                 y=alt.Y('impressions:Q', title='Impresiones', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
#             )
#             right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
#                 y=alt.Y('engagement:Q', title='Interacciones', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
#             )
#             dual_chart = alt.layer(left_line, right_line).resolve_scale(
#                 y='independent'
#             ).properties(height=350)
#             st.altair_chart(theme_chart(dual_chart), use_container_width=True)

# with col_chart_right:
#     # Render Campaign Distribution as a Horizontal Bar Chart so long labels are readable
#     if platform_type == "ads":
#         st.markdown("#### Distribución de Conversiones por Campaña")
#         df_camp = df_curr.groupby("campaign_name")["conversions"].sum().reset_index()
#         df_camp = df_camp.sort_values("conversions", ascending=False).head(10)
#         df_camp["campaign_label"] = df_camp["campaign_name"].apply(clean_campaign_name)

#         chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
#             x=alt.X('conversions:Q', title='Conversiones'),
#             y=alt.Y('campaign_label:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
#         ).properties(height=350)
#         st.altair_chart(theme_chart(chart_camp), use_container_width=True)

#     elif platform_type == "analytics":
#         st.markdown("#### Sesiones por Campaña/Fuente")
#         df_camp = df_curr.groupby("campaign_name")["sessions"].sum().reset_index()
#         df_camp = df_camp.sort_values("sessions", ascending=False).head(10)

#         chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
#             x=alt.X('sessions:Q', title='Sesiones'),
#             y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
#         ).properties(height=350)
#         st.altair_chart(theme_chart(chart_camp), use_container_width=True)

#     else: # organic / app_store
#         st.markdown("#### Alcance / Distribución por Publicación")
#         target_metric = "reach" if platform_type != "app_store" else "downloads"
#         df_camp = df_curr.groupby("campaign_name")[target_metric].sum().reset_index()
#         df_camp = df_camp.sort_values(target_metric, ascending=False).head(10)

#         chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
#             x=alt.X(f"{target_metric}:Q", title='Alcance / Volumen'),
#             y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
#         ).properties(height=350)
#         st.altair_chart(theme_chart(chart_camp), use_container_width=True)

# CAMPAIGN BREAKDOWN TABLE
df_table = df_curr.copy()
identity_sources = [column for column, _ in identity_config]
identity_labels = [label for _, label in identity_config]
st.markdown(f"### {detail_title}")

group_keys = ["campaign_name", "platform"]
for dim in selected_dimensions:
    if dim in df_table.columns and dim not in group_keys:
        group_keys.append(dim)
for column in identity_sources:
    if column in df_table.columns and column not in group_keys:
        group_keys.append(column)

if platform_type == "ads":
    ad_hashtag_rows = []
    if "result_indicator" in df_table.columns and "result_indicator" not in group_keys:
        group_keys.append("result_indicator")
    df_table = df_table.groupby(group_keys).agg({
        "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum", "lead": "sum",
        "reach": "sum", "post_engagement": "sum", "results": "sum", "cost_per_result": "mean",
    }).reset_index()
    meta_platforms = set(META_PUBLISHER_LABELS.values()) | {"meta_ads"}
    meta_table = df_table[df_table["platform"].isin(meta_platforms)].copy()
    if platform_key == "meta_ads" and not meta_table.empty:
        meta_table["base_campaign_name"] = meta_table["campaign_name"].apply(meta_base_campaign_name)
        campaign_summary = (
            meta_table
            .sort_values(["results", "result_indicator"], ascending=[False, False])
            .groupby(identity_sources).agg({
                "result_indicator": "first",
                "spend": "sum", "impressions": "sum", "clicks": "sum",
                "results": "sum", "cost_per_result": "mean",
            })
            .reset_index()
        )
        campaign_summary["result_label"] = campaign_summary["result_indicator"].apply(translate_meta_result_indicator)
        result_type_options = dashboard_filter_options(campaign_summary, "result_label")[1:]
        selected_result_types = st.multiselect(
            "Tipo de resultado",
            result_type_options,
            placeholder="Todos",
            key=f"meta_result_type_filter_{meta_detail_level}",
        )
        if selected_result_types:
            campaign_summary = campaign_summary[
                campaign_summary["result_label"].isin(selected_result_types)
            ].copy()
        campaign_summary["cpm"] = campaign_summary["spend"].mul(1000).div(campaign_summary["impressions"]).where(campaign_summary["impressions"].gt(0), 0)
        campaign_summary["cpc"] = campaign_summary["spend"].div(campaign_summary["clicks"]).where(campaign_summary["clicks"].gt(0), 0)
        campaign_summary = campaign_summary.sort_values("results", ascending=False)
        native_rows_by_level = {
            "campaign": campaign_aggregate_insights,
            "adset": adset_aggregate_insights,
            "ad": ad_aggregate_insights,
        }
        campaign_summary = enrich_meta_campaign_summary(
            campaign_summary,
            native_rows_by_level[meta_detail_level],
            filter_rows,
            meta_detail_level,
        )
        total_row = build_meta_campaign_total_row(
            campaign_summary,
            identity_labels=identity_labels,
        )
        for column in ("results", "impressions", "clicks"):
            campaign_summary[column] = campaign_summary[column].apply(lambda x: f"{x:,.0f}")
        campaign_summary["cost_per_result"] = campaign_summary["cost_per_result"].apply(
            lambda value: f"${value:,.2f}" if pd.notna(value) else "N/D"
        )
        for column in ("cpm", "cpc", "spend"):
            campaign_summary[column] = campaign_summary[column].apply(lambda x: f"${x:,.2f}")
        campaign_summary = campaign_summary[
            identity_sources + [
                "result_label",
                "results",
                "cost_per_result",
                "cpm",
                "impressions",
                "clicks",
                "cpc",
                "budget_display",
                "spend",
            ]
        ].rename(columns={
            **dict(identity_config),
            "result_label": "Tipo de resultado",
            "results": "Resultados",
            "cost_per_result": "Costo por resultado",
            "cpm": "CPM",
            "impressions": "Impresiones",
            "clicks": "Clics",
            "cpc": "CPC",
            "budget_display": "Presupuesto",
            "spend": "Importe gastado",
        })
        campaign_summary = pd.concat([campaign_summary, pd.DataFrame([total_row])], ignore_index=True)
        csv_export_frame["frame"] = campaign_summary

        show_theme_table(campaign_summary, merge_total_cells=True)
        ranking_specs = (
            ("clientes potenciales", "lead", "Clientes potenciales"),
            ("alcance", "reach", "Alcance"),
            ("interacciones", "post_engagement", "Interacciones"),
        )
        campaign_ranking_summary = (
            meta_table.groupby("base_campaign_name")
            .agg(
                platform=("platform", lambda values: " / ".join(dict.fromkeys(values))),
                lead=("lead", "sum"),
                reach=("reach", "sum"),
                post_engagement=("post_engagement", "sum"),
                spend=("spend", "sum"),
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                conversions=("conversions", "sum"),
            )
            .reset_index()
        )
        campaign_reach_by_name = {
            meta_base_campaign_name(row["campaign_name"]): row["reach"]
            for row in campaign_aggregate_insights
        }
        campaign_ranking_summary["reach"] = (
            campaign_ranking_summary["base_campaign_name"]
            .map(campaign_reach_by_name)
            .fillna(0)
        )
        ranked_campaigns_by_metric = {
            metric: campaign_ranking_summary.sort_values(metric, ascending=False).head(3)
            for _, metric, _ in ranking_specs
        }
        ranked_campaign_names = {
            metric: ranked_campaigns_by_metric[metric]["base_campaign_name"].tolist()
            for _, metric, _ in ranking_specs
        }
        ad_winners = select_meta_ad_winners(ad_aggregate_insights, ranked_campaign_names)
        preview_targets = tuple(
            (
                metric,
                campaign_name,
                ad_winners[(metric, campaign_name)]["ad_id"],
                ad_winners[(metric, campaign_name)]["ad_name"],
            )
            for _, metric, _ in ranking_specs
            for campaign_name in ranked_campaign_names[metric]
            if (metric, campaign_name) in ad_winners
        )
        preview_cache = st.session_state.setdefault("meta_preview_cache", {})
        preview_key = (client_id, account_id, preview_targets, api_key)
        if preview_key not in preview_cache:
            preview_cache[preview_key] = fetch_meta_ad_previews(
                client_id,
                account_id,
                preview_targets,
                api_key,
            )
        previews, preview_error = preview_cache[preview_key]
        previews_by_campaign = {
            (p["ranking_metric"], p["campaign_name"]): p
            for p in previews
        }
        campaign_metrics = meta_table.groupby("base_campaign_name").agg({
            "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum"
        }).to_dict("index")

        if preview_error:
            st.info(preview_error)

        ranking_rows = (
            (ranking_name, metric, metric_label, idx, row)
            for ranking_name, metric, metric_label in ranking_specs
            for idx, row in enumerate(
                ranked_campaigns_by_metric[metric].itertuples(index=False),
                start=1,
            )
        )
        for ranking_name, metric, metric_label, idx, row in ranking_rows:
            if idx == 1:
                st.markdown(f"### Ranking: top campañas por {ranking_name} (Meta)")
                rank_cols = st.columns(3)
            preview = previews_by_campaign.get((metric, row.base_campaign_name))
            ctr = row.clicks / row.impressions if row.impressions else 0
            cpc = row.spend / row.clicks if row.clicks else 0
            cpa = row.spend / row.conversions if row.conversions else 0
            metric_rows = [(metric_label, f"{getattr(row, metric):,.0f}")]
            metric_rows.extend([
                ("Inversión", f"${row.spend:,.2f}"),
                ("Conversiones", f"{row.conversions:,.0f}"),
            ])
            if metric != "lead":
                metric_rows.append(("Clientes potenciales", f"{row.lead:,.0f}"))
            metric_rows.extend([
                ("Clics", f"{row.clicks:,.0f}"),
                ("Impresiones", f"{row.impressions:,.0f}"),
                ("CTR", f"{ctr:.2%}"),
                ("CPC", f"${cpc:,.2f}"),
                ("CPA", f"${cpa:,.2f}"),
            ])
            metrics_html = "".join(
                '<div style="display:flex; justify-content:space-between; '
                'border-bottom:1px dashed #e5e7eb; padding-bottom:6px;">'
                f"<span>{label}</span><b>{value}</b></div>"
                for label, value in metric_rows
            )
            body = preview["body"] if preview and preview.get("body") else "<div style='height:320px;display:grid;place-items:center;color:#8A97A8;background:#0A0D13;border-radius:10px;'>Preview no disponible</div>"
            raw_ad_name = str(preview.get("ad_name", "")) if preview else ""
            ad_name = html.escape(raw_ad_name)
            campaign_name = html.escape(str(row.base_campaign_name))
            if "Facebook Ads" in row.platform and "Instagram Ads" in row.platform:
                source = "FB/IG"
            elif "Instagram Ads" in row.platform:
                source = "IG"
            else:
                source = "FB"
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
                    {metrics_html}
                </div>
            </div>
            """
            with rank_cols[(idx - 1) % 4]:
                components.html(components_html, height=690, scrolling=True)

        for preview in {p["ad_id"]: p for p in previews}.values():
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
