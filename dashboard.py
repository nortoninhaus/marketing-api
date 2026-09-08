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
import time
import math
import numpy as np
import altair as alt
from typing import Any, Optional
from contextlib import nullcontext
from datetime import datetime, date, timedelta
from dotenv import load_dotenv

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
    fetch_benchmarking_from_api,
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
    select_meta_top_ads,
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
    inject_gtag_script,
    log_query_execution,
    log_filter_application,
    log_demographics_check,
)

from dashboard.reporting import (
    build_report_payload,
    render_report,
)

from dashboard.reporting import (
    REPORT_TEMPLATES,
    template_report_html,
    segmented_pdf_download_html,
)
from dashboard.styles import inject_dashboard_styles
from dashboard.onboarding import (
    has_seen_onboarding_persisted,
    persist_onboarding_seen_to_client,
    show_onboarding_dialog,
)
from dashboard.views.generic_ads import render_generic_ads_platform_tab
from dashboard.views.meta_ads import render_meta_ads_platform_tab
from dashboard.analytics import log_query_execution

DASHBOARD_CACHE_VERSION = 7


if os.getenv("DASHBOARD_AUTH_SELF_CHECK") == "1":
    dashboard_auth_self_check()
    raise SystemExit("dashboard auth self-check passed")


def toggle_theme():
    st.session_state["theme_switch"] = not st.session_state.get("theme_switch", True)


def log_demographics_toggle(user_id, platform_key, account_id):
    if st.session_state.get("load_demographics"):
        log_demographics_check(user_id, platform_key, account_id)



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


inject_dashboard_styles(theme_mode)
inject_gtag_script()
theme_icon = "☾" if theme_mode == "Oscuro" else "☀"
dashboard_user = require_dashboard_login(theme_icon, toggle_theme)
current_username = dashboard_user.get("username") if dashboard_user else None


if not has_seen_onboarding_persisted(dashboard_user):
    persist_onboarding_seen_to_client(current_username)
    show_onboarding_dialog(current_username)

# SIDEBAR FILTERS (Acts as the collapsible Hamburger Menu on the left)
st.sidebar.image("https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg", width=180)
st.sidebar.button(theme_icon, key="theme_switch_button", help="Cambiar tema", on_click=toggle_theme)
if st.sidebar.button("❓ Guía de Ayuda", key="btn_show_guide", help="Ver guía de uso y cómo solicitar acceso a cuentas", width="stretch"):
    show_onboarding_dialog()

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
    help="Selecciona las plataformas que deseas consultar (Meta Ads, TikTok Ads, etc.). Si requieres acceso a una plataforma adicional, contacta a tu administrador o escribe a dpineda@inhauscorp.com.",
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
            st.warning("Tu usuario no tiene cuentas asignadas para esta plataforma. Solicita acceso a tu administrador o envía un correo a dpineda@inhauscorp.com.")
            continue
        if connections:
            connection_options = {connection_account_label(c, selected_platform_key): c["account_id"] for c in connections}
            conn_keys = list(connection_options.keys())
            conn_choices = conn_keys if len(conn_keys) == 1 else ([""] + conn_keys)
            selected_conn_label = st.selectbox(
                "Cuentas Conectadas",
                conn_choices,
                key=f"conn_{selected_platform_key}",
                help="Cuentas publicitarias asignadas a tu usuario por el administrador.\n\n💡 ¿Necesitas acceso a más cuentas?\nLos usuarios no pueden agregar cuentas directamente. Solicítalo a quien te otorgó acceso o envía un correo a dpineda@inhauscorp.com.",
            )
            default_account_id = connection_options.get(selected_conn_label, "")
        else:
            fallback_accounts = allowed_account_ids or []
            fallback_account_options = {connection_account_label({"account_id": acc_id}, selected_platform_key): acc_id for acc_id in fallback_accounts}
            fallback_keys = list(fallback_account_options.keys())
            fallback_choices = fallback_keys if len(fallback_keys) == 1 else ([""] + fallback_keys)
            selected_fallback_label = st.selectbox(
                "Cuentas permitidas",
                fallback_choices,
                key=f"allowed_account_{selected_platform_key}",
                help="Cuentas autorizadas para tu perfil. Para solicitar cuentas adicionales, contacta al administrador o escribe a dpineda@inhauscorp.com.",
            ) if allowed_account_ids else ""
            default_account_id = fallback_account_options.get(selected_fallback_label, "")

        if connections:
            account_id_value = default_account_id
        else:
            account_key = f"account_{selected_platform_key}"
            prev_conn_key = f"prev_conn_{selected_platform_key}"
            if st.session_state.get(prev_conn_key) != default_account_id:
                st.session_state[account_key] = default_account_id
                st.session_state[prev_conn_key] = default_account_id
            account_id_value = default_account_id if allowed_account_ids else st.text_input(
                "ID de cuenta",
                key=account_key,
                help="Identificador numérico de la cuenta. Recuerda que tu usuario debe tener permisos autorizados por el administrador o vía dpineda@inhauscorp.com.",
            )
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
        widget_metrics_key = f"metrics_{selected_platform_key}"

        if selected_platform_key == "tiktok_ads":
            # Exclude non-existent metrics from choices
            metrics_list = [m for m in metrics_list if m.get("name") not in ("video_views", "followers", "views")]

        platform_preferred_metrics = {
            "meta_ads": ["spend", "impressions", "reach", "post_engagement", "video_views", "followers", "clicks", "conversions", "__results__", "cost_per_result"],
            "tiktok_ads": [
                "spend", "impressions", "clicks", "reach", "conversion", "cost_per_conversion",
                "conversion_rate", "ctr", "cpc", "cpm", "frequency", "follows", "profile_visits",
                "likes", "comments", "shares", "video_play_actions", "video_watched_2s",
                "video_watched_6s", "video_views_p25", "video_views_p50", "video_views_p75", "video_views_p100"
            ],
            "google_ads": [
                "impressions", "clicks", "cost_micros", "conversions", "roas", "all_conversions",
                "conversions_value", "all_conversions_value", "interactions", "engagements", "video_views",
                "active_view_impressions", "conversions_from_interactions_rate", "interaction_rate",
                "average_cpc", "average_cpm", "ctr", "bounce_rate", "active_view_measurability",
                "active_view_viewability", "video_quartile_25_rate", "video_quartile_50_rate",
                "video_quartile_75_rate", "video_quartile_100_rate", "cost_per_conversion",
                "cost_per_all_conversions", "all_conversions_from_interactions_rate",
                "value_per_conversion", "value_per_all_conversion", "active_view_cpm", "active_view_ctr"
            ],
        }
        avail_metric_names = [m["name"] for m in metrics_list]
        pref = platform_preferred_metrics.get(selected_platform_key, [])
        smart_defaults = [m for m in pref if m in avail_metric_names] or ([m["name"] for m in metrics_list] if metrics_list else ["impressions"])

        if selected_platform_key == "tiktok_ads":
            # Migrate any legacy/invalid names in session state to official TikTok metrics
            for k in (metrics_key, widget_metrics_key):
                if k in st.session_state and isinstance(st.session_state[k], list):
                    mapped = []
                    for m in st.session_state[k]:
                        if m in ("followers", "follower"):
                            target = "follows"
                        elif m in ("video_views", "views"):
                            target = "video_play_actions"
                        else:
                            target = m
                        if target in avail_metric_names and target not in mapped:
                            mapped.append(target)
                    for def_m in ("follows", "profile_visits", "likes", "comments", "shares", "video_play_actions", "video_watched_2s", "video_watched_6s"):
                        if def_m in avail_metric_names and def_m not in mapped:
                            mapped.append(def_m)
                    st.session_state[k] = mapped

        if metrics_key not in st.session_state or not st.session_state[metrics_key]:
            st.session_state[metrics_key] = smart_defaults
        else:
            if selected_platform_key == "tiktok_ads":
                for essential in ("spend", "impressions", "clicks", "reach", "conversion", "follows", "profile_visits", "likes", "comments", "shares", "video_play_actions"):
                    if essential in avail_metric_names and essential not in st.session_state[metrics_key]:
                        st.session_state[metrics_key].append(essential)
            else:
                for essential in ("spend", "impressions", "reach", "post_engagement", "video_views", "followers"):
                    if essential in avail_metric_names and essential not in st.session_state[metrics_key]:
                        st.session_state[metrics_key].append(essential)
        if dimensions_key not in st.session_state:
            st.session_state[dimensions_key] = []

        selected_metrics_value = st.multiselect(
            "Métricas *",
            options=[m["name"] for m in metrics_list],
            default=st.session_state[metrics_key],
            key=f"metrics_{selected_platform_key}",
            help="Métricas de rendimiento a consultar. El selector incluye por defecto las métricas oficiales recomendadas. Puedes buscar y agregar métricas adicionales escribiendo aquí.",
        )
        selected_dimensions_value = st.multiselect(
            "Dimensiones (Opcional)",
            options=[d["name"] for d in dimensions_list],
            default=st.session_state[dimensions_key],
            key=f"dimensions_{selected_platform_key}",
            help="Nivel de granularidad para desglosar la información (por campaña, conjunto de anuncios o anuncio).",
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
write_to_bq = st.sidebar.checkbox(
    "Escribir resultados a BigQuery (write_to_bq)",
    value=False,
    help="Guarda una copia de los datos consultados en BigQuery para análisis histórico y persistencia de reportes.",
)

# Date Pickers
today = date.today()
default_start, _ = get_current_month_range(today)
date_range = st.sidebar.date_input(
    "Rango de Fechas a Consultar",
    [default_start, today],
    help="Periodo a auditar. Las métricas del dashboard compararán automáticamente estas cifras contra el mes anterior completo equivalente.",
)
is_date_range_complete = False
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
    is_date_range_complete = True
elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
    start_date = end_date = date_range[0]
    is_date_range_complete = False
else:
    start_date, end_date = default_start, today
    is_date_range_complete = True

if not is_date_range_complete:
    st.sidebar.info("🗓️ Selecciona la fecha de fin en el calendario para completar el rango.")

# Benchmarking / Competitors Section
can_benchmark = bool(dashboard_user.get("can_benchmark", False)) if dashboard_user else False
if can_benchmark:
    with st.sidebar.expander("🔍 Competidores (Benchmarking)", expanded=False):
        st.caption("Escribe los usernames de Instagram y nombres de página de Facebook para analizar competidores.")
        st.text_area(
            "Competidores Instagram (@usernames)",
            value=st.session_state.get("benchmark_ig_input", "parmalatecuador, toniec, lalecheraec, vita_ecuador"),
            help="Usernames de Instagram separados por coma o salto de línea",
            key="benchmark_ig_input",
        )
        st.text_area(
            "Competidores Facebook (Páginas/Usernames)",
            value=st.session_state.get("benchmark_fb_input", "parmalatecuador, ToniLacteosEc, LaLecheraEcuador, VitaEcuador"),
            help="Usernames o nombres de página de Facebook separados por coma o salto de línea",
            key="benchmark_fb_input",
        )

# Execute Button in Sidebar to prevent auto-loading until clicked
execute_query = st.sidebar.button("🚀 Consultar API", width="stretch", help="Ejecuta la consulta en tiempo real contra las APIs oficiales de cada plataforma seleccionada.")

if st.session_state.get("query_run", False):
    applied_start = st.session_state.get("applied_start_date")
    applied_end = st.session_state.get("applied_end_date")
    if is_date_range_complete and (start_date != applied_start or end_date != applied_end):
        st.sidebar.caption("⚡ Haz clic en **Consultar API** para aplicar las nuevas fechas.")

if st.sidebar.button("🔒 Cerrar Sesión", key="logout_button", width="stretch"):
    st.session_state.pop("dashboard_auth_token", None)
    st.session_state.pop("dashboard_user", None)
    dashboard_auth_cookie_bridge(clear=True)
    st.stop()

# MAIN DISPLAY (Occupies full wide screen)
header_left, header_right = st.columns([0.84, 0.16], vertical_alignment="center")
with header_right:
    col_dl, col_live = st.columns([0.30, 0.70], vertical_alignment="center", gap="small")
    with col_dl:
        download_slot = st.empty()
    with col_live:
        st.markdown('<div class="header-live-badge"><span class="stamp"><span class="live"></span> API Directa</span></div>', unsafe_allow_html=True)
with header_left:
    st.markdown("""
<div class="custom-header">
    <div class="agency">
        <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg" alt="Inhaus">
        <span class="div-bar"></span>
        <span class="who">Dashboard de Pauta &middot; Conexión de API</span>
    </div>
</div>
""", unsafe_allow_html=True)

if execute_query:
    if not is_date_range_complete:
        st.sidebar.warning("⚠️ Debes seleccionar ambas fechas (inicio y fin) en el calendario antes de consultar.")
        st.stop()
    if start_date > end_date:
        st.sidebar.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin.")
        st.stop()

    log_query_execution(
        current_username,
        platform_key,
        account_id,
        start_date.isoformat(),
        end_date.isoformat(),
        write_to_bq,
    )

    st.session_state.setdefault("dashboard_query_cache", {})
    st.session_state.force_query_fetch = False

    st.session_state["applied_start_date"] = start_date
    st.session_state["applied_end_date"] = end_date
    st.session_state["applied_platform_configs"] = platform_configs
    st.session_state["applied_write_to_bq"] = write_to_bq
    st.session_state["applied_platform_key"] = platform_key
    st.session_state["applied_account_id"] = account_id
    st.session_state.query_run = True
    st.rerun()

if not st.session_state.get("query_run", False):
    render_dashboard_empty_state("Configura tus parámetros de consulta en el menú lateral y presiona Consultar API.")
    st.stop()
else:
    # Use the parameters committed when "Consultar API" was clicked
    start_date = st.session_state.get("applied_start_date", start_date)
    end_date = st.session_state.get("applied_end_date", end_date)
    platform_configs = st.session_state.get("applied_platform_configs", platform_configs)
    write_to_bq = st.session_state.get("applied_write_to_bq", write_to_bq)
    platform_key = st.session_state.get("applied_platform_key", platform_key)
    account_id = st.session_state.get("applied_account_id", account_id)

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
        standard_metrics = [
            "impressions", "clicks", "spend", "cost_micros", "cost", "conversions", "lead", "reach",
            "post_engagement", "engagement", "__results__", "cost_per_result",
            "video_play_actions", "video_views", "views", "followers", "follows",
            "average_cpc", "average_cpm", "ctr", "interaction_rate",
        ]
    elif cfg["platform_type"] == "analytics":
        standard_metrics = ["sessions", "users", "pageviews", "bounce_rate"]
    elif cfg["platform_type"] == "app_store":
        standard_metrics = ["downloads", "ratings"]
    else:
        standard_metrics = ["impressions", "engagement", "followers", "reach"]
    for metric in standard_metrics:
        if metric not in request_metrics and metric in metric_names:
            request_metrics.append(metric)

    if cfg["platform_key"] == "tiktok_ads":
        invalid_tiktok = {"video_views", "views", "followers", "conversions"}
        request_metrics = [m for m in request_metrics if m not in invalid_tiktok]
        if "video_play_actions" in metric_names and "video_play_actions" not in request_metrics:
            request_metrics.append("video_play_actions")

    request_dimensions = list(cfg["selected_dimensions"])
    if cfg["platform_key"] == "meta_ads" and "publisher_platform" in dimension_names and "publisher_platform" not in request_dimensions:
        request_dimensions.append("publisher_platform")
    if cfg["platform_key"] == "google_ads" and "campaign.advertising_channel_type" in dimension_names and "campaign.advertising_channel_type" not in request_dimensions:
        request_dimensions.append("campaign.advertising_channel_type")

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
if force_query_fetch or st.session_state.get("active_query_key") != query_key:
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
    account_disp = platform_configs[0]["account_id"] if len(platform_configs) == 1 else " | ".join(f"{cfg['platform_label']}: {cfg['account_id']}" for cfg in platform_configs)
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
        "platform_configs": platform_configs,
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
    st.stop()
else:
    platform_configs_active = active_context.get("platform_configs", platform_configs)
    has_multiple_platforms = len(platform_configs_active) > 1

    if has_multiple_platforms:
        platform_tabs = st.tabs([f"📊 {cfg['platform_label']}" for cfg in platform_configs_active])
        for p_idx, cfg in enumerate(platform_configs_active):
            with platform_tabs[p_idx]:
                if cfg["platform_key"] == "meta_ads":
                    render_meta_ads_platform_tab(
                        cfg,
                        df_curr,
                        df_prev,
                        client_id,
                        user_id,
                        api_key,
                        start_date,
                        end_date,
                        prev_start_date,
                        prev_end_date,
                        force_query_fetch,
                        active_query_key,
                        opt_filters,
                        theme_mode,
                        current_username,
                        selected_platform_keys,
                        dashboard_user,
                        download_slot,
                        chart_bg,
                    )
                else:
                    render_generic_ads_platform_tab(
                        cfg,
                        df_curr,
                        df_prev,
                        start_date,
                        end_date,
                        prev_start_date,
                        prev_end_date,
                        theme_mode,
                    )
    else:
        cfg = platform_configs_active[0]
        if cfg["platform_key"] == "meta_ads":
            render_meta_ads_platform_tab(
                cfg,
                df_curr,
                df_prev,
                client_id,
                user_id,
                api_key,
                start_date,
                end_date,
                prev_start_date,
                prev_end_date,
                force_query_fetch,
                active_query_key,
                opt_filters,
                theme_mode,
                current_username,
                selected_platform_keys,
                dashboard_user,
                download_slot,
                chart_bg,
            )
        else:
            render_generic_ads_platform_tab(
                cfg,
                df_curr,
                df_prev,
                start_date,
                end_date,
                prev_start_date,
                prev_end_date,
                theme_mode,
            )

