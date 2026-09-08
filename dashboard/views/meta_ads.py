import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import numpy as np
import altair as alt
import html
import json
import re
from typing import Any, Optional
from datetime import datetime, date, timedelta

from dashboard.config import META_PUBLISHER_LABELS
from dashboard.auth import (
    dashboard_allowed_account_ids,
    filter_dashboard_connections,
    connection_account_label,
)
from dashboard.api import (
    fetch_connections_from_api,
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
)
from dashboard.ui import (
    theme_chart,
    show_theme_table,
    get_kpi_card_html,
)
from dashboard.analytics import log_filter_application
from dashboard.reporting import (
    REPORT_TEMPLATES,
    template_report_html,
    segmented_pdf_download_html,
)

def render_meta_ads_platform_tab(
    cfg,
    df_curr_all,
    df_prev_all,
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
):
    plat_key = cfg.get("platform_key", "meta_ads")
    plat_label = cfg.get("platform_label", "Meta Ads (Facebook/IG)")
    account_id = cfg.get("account_id", "")
    platform_type = cfg.get("platform_type", "ads")

    meta_platforms = set(META_PUBLISHER_LABELS.values()) | {"meta_ads"}
    if "source_platform" in df_curr_all.columns:
        df_curr = df_curr_all[df_curr_all["source_platform"] == plat_key].copy()
    elif "platform" in df_curr_all.columns:
        df_curr = df_curr_all[df_curr_all["platform"].isin(meta_platforms)].copy()
    else:
        df_curr = df_curr_all.copy()

    if isinstance(df_prev_all, pd.DataFrame) and not df_prev_all.empty:
        if "source_platform" in df_prev_all.columns:
            df_prev = df_prev_all[df_prev_all["source_platform"] == plat_key].copy()
        elif "platform" in df_prev_all.columns:
            df_prev = df_prev_all[df_prev_all["platform"].isin(meta_platforms)].copy()
        else:
            df_prev = df_prev_all.copy()
    else:
        df_prev = pd.DataFrame()

    if plat_key == "meta_ads" and not df_curr.empty:
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

    if df_curr.empty:
        st.warning("ℹ️ La API retornó registros para el periodo seleccionado, pero ninguna campaña registra impresiones o métricas de alcance relevantes en estas fechas. Intenta ajustar el rango de fechas o los filtros.")
        return
    applied_campaign_filter = []
    applied_adset_filter = []
    applied_ad_filter = "Todos"
    if plat_key == "meta_ads":
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
                plat_key,
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
            df_curr = process_api_response(detail_curr_rows, plat_key, client_id, user_id)
            df_prev = process_api_response(detail_prev_rows, plat_key, client_id, user_id) if detail_prev_rows else pd.DataFrame()
        df_curr = apply_dashboard_filters(df_curr, applied_campaign_filter, applied_adset_filter, applied_ad_filter)
        df_prev = apply_dashboard_filters(df_prev, applied_campaign_filter, applied_adset_filter, applied_ad_filter)
        if applied_campaign_filter:
            st.caption(f"Campañas: {campaign_title(applied_campaign_filter, plat_label)}")

    identity_config = (("base_campaign_name", "Campaña"),)
    detail_title = "Detalle de Campañas y Resultados"
    meta_detail_level = "campaign"
    if plat_key == "meta_ads":
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
    if plat_key == "meta_ads":
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

    export_slug = re.sub(r"[^a-z0-9]+", "-", plat_label.lower()).strip("-")
    export_name = f"{export_slug}_{start_date:%Y-%m-%d}_{end_date:%Y-%m-%d}"
    csv_export_frame = {"frame": df_curr}

    # HERO RENDER (Clean, full width, no Sipy logo)
    title_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
    display_title = campaign_title(applied_campaign_filter, plat_label) if plat_key == "meta_ads" else plat_label
    st.markdown(f"""
    <h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: {title_color};">{display_title} &middot; {account_id}</h1>
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

    load_demographics = plat_key == "meta_ads" and st.checkbox(
        "Cargar datos demográficos",
        value=False,
        key="load_demographics",
        on_change=log_demographics_toggle,
        args=(current_username, plat_key, account_id),
    )
    if load_demographics:
        official_key = (
            plat_key, client_id, user_id, account_id,
            start_date.isoformat(), end_date.isoformat(),
            json.dumps(opt_filters, sort_keys=True, default=str),
        )
        st.session_state.setdefault("meta_official_cache", {})
        if official_key not in st.session_state["meta_official_cache"]:
            with st.spinner("Cargando datos oficiales de Facebook Ads... puede tardar unos minutos."):
                age_data = fetch_campaign_data_from_api(
                    plat_key, client_id, user_id, account_id,
                    start_date, end_date, ["impressions", "reach"], ["age"],
                    opt_filters, False, api_key, False, 180
                )
                gender_data = fetch_campaign_data_from_api(
                    plat_key, client_id, user_id, account_id,
                    start_date, end_date, ["impressions", "reach"], ["gender"],
                    opt_filters, False, api_key, False, 180
                )
                region_data = fetch_campaign_data_from_api(
                    plat_key, client_id, user_id, account_id,
                    start_date, end_date, ["impressions", "reach"], ["region"],
                    opt_filters, False, api_key, False, 180
                )
                st.session_state["meta_official_cache"][official_key] = (age_data, gender_data, region_data)
        age_data, gender_data, region_data = st.session_state["meta_official_cache"][official_key]

        df_age = process_api_response(age_data, plat_key, client_id, user_id) if age_data else pd.DataFrame()
        df_gender = process_api_response(gender_data, plat_key, client_id, user_id) if gender_data else pd.DataFrame()
        df_region = process_api_response(region_data, plat_key, client_id, user_id) if region_data else pd.DataFrame()

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
        if plat_key == "meta_ads" and not meta_table.empty:
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
            cached_previews = preview_cache.get(preview_key, ([], None))[0] or []
            if preview_key not in preview_cache or not any((p.get("url") or p.get("image_url")) for p in cached_previews) or any("post_created_time" not in p or "post_platform" not in p for p in cached_previews) or any("facebook_url" not in p or "instagram_url" not in p for p in cached_previews):
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

        platform_key = plat_key
        if platform_key != "meta_ads":
            csv_export_frame["frame"] = df_table

        if plat_key == "meta_organic":
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

    if plat_key != "meta_ads":
        st.dataframe(df_table, width="stretch", hide_index=True)

    with download_slot.container():
        @st.dialog("Descargar Reporte", width="small")
        def _show_download_dialog(
            export_name=export_name,
            chart_bg=chart_bg,
            csv_export_frame=csv_export_frame,
            df_curr=df_curr,
            df_prev=df_prev,
            selected_platform_label=plat_label,
            account_disp=account_id,
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            platform_key=plat_key,
            selected_platform_keys=selected_platform_keys,
            client_id=client_id,
            user_id=user_id,
            api_key=api_key,
            dashboard_user=dashboard_user,
        ):
            if not bool(dashboard_user.get("can_download", False)):
                st.error("Tu usuario no tiene permisos para descargar reportes. Solicita acceso a dpineda@inhauscorp.com.")
                return

            can_download_reports = bool(
                dashboard_user.get(
                    "can_download_reports",
                    dashboard_user.get("can_download_reportes", dashboard_user.get("puede_descargar_reportes", False)),
                )
            )
            can_download_csv = bool(
                dashboard_user.get(
                    "can_download_csv",
                    dashboard_user.get("puede_descargar_csv", False),
                )
            )

            if not can_download_reports and not can_download_csv:
                st.info("Tu usuario no tiene permisos habilitados para descargar reportes ni archivos CSV. Solicita acceso a dpineda@inhauscorp.com.")
                return

            if can_download_reports:
                st.markdown("#### Reportes")
                st.caption("Descarga el reporte ejecutivo consolidado en formato PDF o HTML interactivo.")
                st.html(
                    segmented_pdf_download_html(export_name, chart_bg),
                    unsafe_allow_javascript=True,
                    width="stretch",
                )

            if can_download_csv:
                st.markdown("#### Exportación CSV")
                st.caption("Descarga la tabla de datos procesados en formato CSV compatible con Excel.")
                st.download_button(
                    "Descargar CSV",
                    data=lambda: csv_export_frame["frame"].to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"{export_name}.csv",
                    mime="text/csv;charset=utf-8",
                    on_click="ignore",
                    icon=":material/download:",
                    width="stretch",
                )

            if not can_download_reports:
                return

            st.markdown("##### Plantilla HTML")
            report_template = st.selectbox("Template HTML", list(REPORT_TEMPLATES.keys()))
            html_export_context = {
                "Plataformas": selected_platform_label,
                "Cuenta": account_disp,
                "Fechas": f"{start_date:%d/%m/%Y} – {end_date:%d/%m/%Y}",
                "account_id": str(account_id),
                "platform": str(platform_key),
                "start_date": f"{start_date:%Y-%m-%d}",
                "end_date": f"{end_date:%Y-%m-%d}",
            }
            curr_frame_export = df_curr if isinstance(df_curr, pd.DataFrame) and not df_curr.empty else csv_export_frame["frame"]
            prev_frame_export = df_prev if isinstance(df_prev, pd.DataFrame) and not df_prev.empty else None

            include_tiktok = False
            tiktok_account_id = ""
            tiktok_account_name = ""
            if "tiktok_ads" not in selected_platform_keys:
                include_tiktok = st.checkbox("¿Deseas agregar datos de TikTok?", value=False, key="export_add_tiktok")
                if include_tiktok:
                    tt_connections = fetch_connections_from_api("tiktok_ads", client_id, api_key)
                    tt_connections = filter_dashboard_connections(tt_connections, dashboard_user, "tiktok_ads")
                    tt_allowed_ids = dashboard_allowed_account_ids(dashboard_user, "tiktok_ads")
                    if tt_connections:
                        tt_options = {connection_account_label(c, "tiktok_ads"): (c["account_id"], connection_account_label(c, "tiktok_ads")) for c in tt_connections}
                        selected_tt_label = st.selectbox("Cuenta de TikTok Ads", [""] + list(tt_options.keys()), key="export_conn_tiktok_ads")
                        if selected_tt_label:
                            tiktok_account_id, tiktok_account_name = tt_options[selected_tt_label]
                    else:
                        tt_fallback = tt_allowed_ids or []
                        tt_fallback_options = {connection_account_label({"account_id": a_id}, "tiktok_ads"): a_id for a_id in tt_fallback}
                        selected_tt_label = st.selectbox("Cuenta de TikTok Ads", [""] + list(tt_fallback_options.keys()), key="export_allowed_tiktok_ads") if tt_allowed_ids else ""
                        if selected_tt_label:
                            tiktok_account_id = tt_fallback_options[selected_tt_label]
                            tiktok_account_name = selected_tt_label
                        elif not tt_allowed_ids:
                            tiktok_account_id = st.text_input("ID de cuenta de TikTok Ads", key="export_account_tiktok_ads")
                            tiktok_account_name = f"TikTok Ads: {tiktok_account_id}"

            def _build_download_html(
                curr_df=curr_frame_export,
                prev_df=prev_frame_export,
                tpl=report_template,
                ctx=html_export_context,
                exp_df=csv_export_frame,
                add_tt=include_tiktok,
                tt_acc_id=tiktok_account_id,
                tt_acc_name=tiktok_account_name,
                c_id=client_id,
                u_id=user_id,
                s_date=start_date,
                e_date=end_date,
                key=api_key,
                meta_ads=tuple(ad_aggregate_insights),
            ) -> bytes:
                final_df = curr_df
                final_ctx = dict(ctx)
                final_connections = [{
                    "account_id": str(ctx.get("account_id", "")),
                    "account_name": str(ctx.get("Cuenta", "")),
                    "platform": str(ctx.get("platform", "meta_ads")),
                }]
                platforms_list = [str(ctx.get("platform", "meta_ads"))]
                df_tt = None
                ad_records = []

                # Enrich final_df with Meta ad / post entities and previews
                meta_acc_id = str(ctx.get("account_id", ""))
                meta_platform = str(ctx.get("platform", "meta_ads"))
                if meta_platform == "meta_ads" and meta_acc_id:
                    all_ad_insights = list(meta_ads)
                    if not all_ad_insights:
                        try:
                            active_meta_filters = st.session_state.get("meta_applied_api_filters", {})
                            all_ad_insights, _ = fetch_meta_aggregate_insights(
                                c_id, meta_acc_id, s_date, e_date, "ad", active_meta_filters, key
                            )
                        except Exception as ex_ads:
                            print(f"Error fetching ad insights for export: {ex_ads}")
                            all_ad_insights = []

                    if all_ad_insights:
                        active_ad_insights = [
                            row for row in all_ad_insights
                            if extract_metric(row, ["impressions", "reach", "spend", "clicks", "post_engagement"]) > 0
                        ]
                        if active_ad_insights:
                            all_ad_insights = active_ad_insights

                    if all_ad_insights and isinstance(curr_df, pd.DataFrame) and not curr_df.empty:
                        valid_campaign_ids = {str(x) for x in curr_df["campaign_id"].dropna().unique()} if "campaign_id" in curr_df else set()
                        valid_campaign_names = {str(x) for x in curr_df["campaign_name"].dropna().unique()} if "campaign_name" in curr_df else set()
                        valid_base_campaigns = {meta_base_campaign_name(x) for x in valid_campaign_names if x}
                        if valid_campaign_ids or valid_campaign_names or valid_base_campaigns:
                            matching_ads = []
                            for row in all_ad_insights:
                                r_cid = str(row.get("campaign_id") or "")
                                r_cname = str(row.get("campaign_name") or "")
                                r_base = meta_base_campaign_name(r_cname)
                                if (valid_campaign_ids and r_cid in valid_campaign_ids) or \
                                   (valid_campaign_names and r_cname in valid_campaign_names) or \
                                   (valid_base_campaigns and r_base in valid_base_campaigns):
                                    matching_ads.append(row)
                            if matching_ads:
                                all_ad_insights = matching_ads

                    if all_ad_insights:
                        unique_ads = {}
                        for metric, top_ads in select_meta_top_ads(
                            all_ad_insights, ("reach", "post_engagement"), limit=3
                        ).items():
                            for row in top_ads:
                                ad_id = str(row["ad_id"])
                                unique_ads.setdefault(ad_id, (
                                    metric,
                                    row.get("campaign_name", ""),
                                    ad_id,
                                    row.get("ad_name", ""),
                                ))
                        previews_by_ad = {}
                        if unique_ads:
                            for p_key, p_val in st.session_state.get("meta_preview_cache", {}).items():
                                if isinstance(p_val, tuple) and p_val[0]:
                                    for p in p_val[0]:
                                        if p.get("ad_id"):
                                            previews_by_ad[str(p["ad_id"])] = p
                            missing_targets = tuple(
                                t for t in unique_ads.values()
                                if str(t[2]) not in previews_by_ad
                                or not (previews_by_ad[str(t[2])].get("url") or previews_by_ad[str(t[2])].get("image_url"))
                                or "post_created_time" not in previews_by_ad[str(t[2])]
                                or "post_platform" not in previews_by_ad[str(t[2])]
                                or "facebook_url" not in previews_by_ad[str(t[2])]
                                or "instagram_url" not in previews_by_ad[str(t[2])]
                            )
                            if missing_targets:
                                fetched_p, _ = fetch_meta_ad_previews(c_id, meta_acc_id, missing_targets[:10], key)
                                for p in (fetched_p or []):
                                    if p.get("ad_id"):
                                        previews_by_ad[str(p["ad_id"])] = p

                        for row in all_ad_insights:
                            ad_id = str(row.get("ad_id") or "")
                            preview = previews_by_ad.get(ad_id) or {}
                            post_platform = str(preview.get("post_platform") or "").lower()
                            ad_name = preview.get("ad_name") or row.get("ad_name") or ""
                            post_msg = preview.get("post_message") or ""
                            post_url = preview.get("url") or ""
                            imp_val = extract_metric(row, ["impressions"])
                            reach_val = extract_metric(row, ["reach"])
                            eng_val = extract_metric(row, ["post_engagement", "engagement"])
                            click_val = extract_metric(row, ["clicks"])
                            spend_val = extract_metric(row, ["spend"])
                            lead_val = extract_metric(row, ["lead"])
                            clean_title = post_msg or "Publicación"
                            ad_records.append({
                                "platform": post_platform or "meta_ads",
                                "source_platform": "meta_ads",
                                "publisher_platform": post_platform,
                                "name": clean_title,
                                "ad_name": ad_name,
                                "campaign_name": row.get("campaign_name", ""),
                                "ad_id": ad_id,
                                "post_message": post_msg,
                                "post_title": clean_title,
                                "url": post_url,
                                "facebook_url": preview.get("facebook_url") or "",
                                "instagram_url": preview.get("instagram_url") or "",
                                "image_url": preview.get("image_url") or "",
                                "post_created_time": preview.get("post_created_time") or "",
                                "post_platform": post_platform,
                                "body": preview.get("body") or "",
                                "impressions": imp_val,
                                "reach": reach_val,
                                "engagement": eng_val,
                                "post_engagement": eng_val,
                                "clicks": click_val,
                                "views": imp_val,
                                "spend": spend_val,
                                "lead": lead_val,
                                "source_metrics": {
                                    "impressions": imp_val,
                                    "reach": reach_val,
                                    "engagement": eng_val,
                                    "post_engagement": eng_val,
                                    "clicks": click_val,
                                    "views": imp_val,
                                    "spend": spend_val,
                                    "lead": lead_val,
                                },
                            })
                # Calculate 3 calendar months for real historical evolution
                p1_start, p1_end = get_prior_month_range(s_date)
                p2_start, p2_end = get_prior_month_range(p1_start)
                spanish_months = {
                    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
                    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
                    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
                }
                monthly_evolution = {
                    "months": [
                        {"key": "m2", "label": spanish_months[p2_start.month], "year": p2_start.year},
                        {"key": "m1", "label": spanish_months[p1_start.month], "year": p1_start.year},
                        {"key": "m0", "label": spanish_months[s_date.month], "year": s_date.year},
                    ],
                    "networks": {
                        "facebook": {
                            "impressions": {"m2": 0.0, "m1": 0.0, "m0": 0.0},
                            "reach": {"m2": 0.0, "m1": 0.0, "m0": 0.0},
                        },
                        "instagram": {
                            "impressions": {"m2": 0.0, "m1": 0.0, "m0": 0.0},
                            "reach": {"m2": 0.0, "m1": 0.0, "m0": 0.0},
                        },
                    }
                }

                # Fetch Meta history for M-1 and M-2 with publisher_platform
                meta_acc_id = str(ctx.get("account_id", ""))
                meta_platform = str(ctx.get("platform", "meta_ads"))
                if meta_platform == "meta_ads" and meta_acc_id:
                    try:
                        def _filter_meta_pub(df: pd.DataFrame, target: str) -> pd.DataFrame:
                            if not isinstance(df, pd.DataFrame) or df.empty or "publisher_platform" not in df.columns:
                                return pd.DataFrame()
                            pubs = df["publisher_platform"].astype(str).str.lower().str.strip()
                            if target == "instagram":
                                return df[pubs.isin(["instagram", "threads"])]
                            elif target == "facebook":
                                return df[~pubs.isin(["instagram", "threads"])]
                            return df[pubs == target]

                        if isinstance(curr_df, pd.DataFrame) and not curr_df.empty:
                            for pub in ("facebook", "instagram"):
                                pub_df = _filter_meta_pub(curr_df, pub)
                                if not pub_df.empty:
                                    if "impressions" in pub_df.columns:
                                        monthly_evolution["networks"][pub]["impressions"]["m0"] = float(pub_df["impressions"].sum())
                                    if "reach" in pub_df.columns:
                                        monthly_evolution["networks"][pub]["reach"]["m0"] = float(pub_df["reach"].sum())

                        for period_tag, (p_start, p_end) in (("m1", (p1_start, p1_end)), ("m2", (p2_start, p2_end))):
                            m_rows = fetch_campaign_data_from_api(
                                "meta_ads", c_id, u_id, meta_acc_id,
                                p_start, p_end, ["impressions", "reach", "spend"], ["publisher_platform"],
                                {}, False, key, show_errors=False
                            )
                            if m_rows:
                                m_df = process_api_response(m_rows, "meta_ads", c_id, u_id)
                                if isinstance(m_df, pd.DataFrame) and not m_df.empty:
                                    for pub in ("facebook", "instagram"):
                                        pub_df = _filter_meta_pub(m_df, pub)
                                        if not pub_df.empty:
                                            if "impressions" in pub_df.columns:
                                                monthly_evolution["networks"][pub]["impressions"][period_tag] = float(pub_df["impressions"].sum())
                                            if "reach" in pub_df.columns:
                                                monthly_evolution["networks"][pub]["reach"][period_tag] = float(pub_df["reach"].sum())
                    except Exception as ex:
                        print(f"Error fetching Meta historical evolution: {ex}")

                if add_tt and tt_acc_id:
                    try:
                        tt_metrics = [
                            "spend", "impressions", "clicks", "reach", "conversion",
                            "cost_per_conversion", "conversion_rate", "ctr", "cpc", "cpm",
                            "frequency", "video_play_actions", "video_watched_2s",
                            "video_watched_6s", "video_views_p25", "video_views_p50",
                            "video_views_p75", "video_views_p100"
                        ]
                        tt_dimensions = []
                        tt_rows = fetch_campaign_data_from_api(
                            "tiktok_ads", c_id, u_id, str(tt_acc_id),
                            s_date, e_date, tt_metrics, tt_dimensions,
                            {}, False, key, show_errors=False
                        )
                        if tt_rows:
                            df_tt = process_api_response(tt_rows, "tiktok_ads", c_id, u_id)
                            if isinstance(df_tt, pd.DataFrame) and not df_tt.empty:
                                if isinstance(final_df, pd.DataFrame) and not final_df.empty:
                                    final_df = pd.concat([final_df, df_tt], ignore_index=True)
                                else:
                                    final_df = df_tt
                        final_connections.append({
                            "account_id": str(tt_acc_id),
                            "account_name": str(tt_acc_name or f"TikTok Ads: {tt_acc_id}"),
                            "platform": "tiktok_ads",
                        })
                        platforms_list.append("tiktok_ads")

                        # TikTok historical evolution for M-0, M-1, M-2
                        monthly_evolution["networks"]["tiktok"] = {
                            "impressions": {"m2": 0.0, "m1": 0.0, "m0": 0.0},
                            "reach": {"m2": 0.0, "m1": 0.0, "m0": 0.0},
                        }
                        if isinstance(df_tt, pd.DataFrame) and not df_tt.empty:
                            if "impressions" in df_tt.columns:
                                monthly_evolution["networks"]["tiktok"]["impressions"]["m0"] = float(df_tt["impressions"].sum())
                            if "reach" in df_tt.columns:
                                monthly_evolution["networks"]["tiktok"]["reach"]["m0"] = float(df_tt["reach"].sum())

                        for period_tag, (p_start, p_end) in (("m1", (p1_start, p1_end)), ("m2", (p2_start, p2_end))):
                            tt_m_rows = fetch_campaign_data_from_api(
                                "tiktok_ads", c_id, u_id, str(tt_acc_id),
                                p_start, p_end, ["impressions", "reach", "spend"], [],
                                {}, False, key, show_errors=False
                            )
                            if tt_m_rows:
                                tt_m_df = process_api_response(tt_m_rows, "tiktok_ads", c_id, u_id)
                                if isinstance(tt_m_df, pd.DataFrame) and not tt_m_df.empty:
                                    if "impressions" in tt_m_df.columns:
                                        monthly_evolution["networks"]["tiktok"]["impressions"][period_tag] = float(tt_m_df["impressions"].sum())
                                    if "reach" in tt_m_df.columns:
                                        monthly_evolution["networks"]["tiktok"]["reach"][period_tag] = float(tt_m_df["reach"].sum())
                    except Exception as ex:
                        print(f"Error fetching TikTok Ads for export: {ex}")
                content_rows = list(ad_records)
                if isinstance(df_tt, pd.DataFrame) and not df_tt.empty:
                    content_rows.extend(df_tt.to_dict("records"))
                breakdowns_opt = {"monthly_evolution": monthly_evolution}
                ig_raw = str(st.session_state.get("benchmark_ig_input") or "parmalatecuador, toniec, lalecheraec, vita_ecuador")
                fb_raw = str(st.session_state.get("benchmark_fb_input") or "parmalatecuador, ToniLacteosEc, LaLecheraEcuador, VitaEcuador")
                ig_comps = [u.strip().lstrip("@") for u in re.split(r"[,\n]+", ig_raw) if u.strip()]
                fb_comps = [p.strip() for p in re.split(r"[,\n]+", fb_raw) if p.strip()]
                effective_client_id = c_id or client_id or "client_1"
                if can_benchmark and (ig_comps or fb_comps):
                    try:
                        bench_res = fetch_benchmarking_from_api(
                            effective_client_id, u_id, str(ctx.get("account_id", "")), ig_comps, fb_comps, key, show_errors=False
                        )
                        if bench_res and isinstance(bench_res, dict) and (bench_res.get("instagram") or bench_res.get("facebook")):
                            breakdowns_opt["benchmarking"] = bench_res
                            breakdowns_opt["competition"] = bench_res
                    except Exception as ex:
                        print(f"Error fetching benchmarking data: {ex}")

                return template_report_html(
                    final_df,
                    tpl,
                    final_ctx,
                    previous_frame=prev_df,
                    export_table=exp_df["frame"],
                    optional={"breakdowns": breakdowns_opt, "content_rows": content_rows},
                ).encode("utf-8")

            st.download_button(
                "Descargar HTML",
                data=_build_download_html,
                file_name=f"{export_name}_{report_template.lower().replace(' ', '-')}.html",
                mime="text/html;charset=utf-8",
                on_click="ignore",
                icon=":material/download:",
                width="stretch",
            )

        can_download = bool(dashboard_user.get("can_download", False)) if dashboard_user else False
        if can_download:
            if st.button("", icon=":material/download:", key="btn_download_modal", help="Descargar reporte"):
                _show_download_dialog()



