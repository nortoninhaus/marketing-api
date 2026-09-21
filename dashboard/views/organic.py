import streamlit as st
import pandas as pd
import numpy as np

from dashboard.ui import get_kpi_card_html


def render_organic_platform_tab(
    cfg,
    df_curr_all,
    df_prev_all,
    start_date,
    end_date,
    prev_start_date,
    prev_end_date,
    theme_mode,
):
    plat_key = cfg["platform_key"]
    plat_label = cfg["platform_label"]
    account_id = cfg["account_id"]

    if "source_platform" in df_curr_all.columns:
        df_curr_p = df_curr_all[df_curr_all["source_platform"] == plat_key].copy()
    elif "platform" in df_curr_all.columns:
        df_curr_p = df_curr_all[df_curr_all["platform"] == plat_key].copy()
    else:
        df_curr_p = df_curr_all.copy()

    if isinstance(df_prev_all, pd.DataFrame) and not df_prev_all.empty:
        if "source_platform" in df_prev_all.columns:
            df_prev_p = df_prev_all[df_prev_all["source_platform"] == plat_key].copy()
        elif "platform" in df_prev_all.columns:
            df_prev_p = df_prev_all[df_prev_all["platform"] == plat_key].copy()
        else:
            df_prev_p = df_prev_all.copy()
    else:
        df_prev_p = pd.DataFrame()

    non_numeric_cols = {
        "platform", "source_platform", "campaign_name", "date", "client_id", "user_id",
        "page_id", "permalink", "url", "source_metrics", "account_id"
    }
    for df_target in (df_curr_p, df_prev_p):
        if isinstance(df_target, pd.DataFrame) and not df_target.empty:
            for c in df_target.columns:
                if c not in non_numeric_cols:
                    df_target[c] = pd.to_numeric(df_target[c], errors="coerce").fillna(0)

    organic_metric_cols = [
        col for col in [
            "page_media_view", "page_total_media_view_unique", "page_post_engagements",
            "page_views_total", "page_follows", "impressions", "reach", "engagement",
            "post_engagement", "followers", "pageviews", "likes", "comments", "shares",
            "video_views", "profile_visits", "views", "clicks"
        ] if col in df_curr_p.columns
    ]

    if not df_curr_p.empty and organic_metric_cols:
        df_curr_p = df_curr_p[df_curr_p[organic_metric_cols].sum(axis=1) > 0].copy()

    if df_curr_p.empty:
        st.warning(f"ℹ️ No se registraron datos activos con métricas mayores a 0 para {plat_label} en este periodo.")
        return

    title_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
    st.markdown(f"""
    <h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: {title_color};">{plat_label} &middot; {account_id}</h1>
    <p class="lede" style="margin-top: 15px;">
        Resultados orgánicos del <b>{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}</b>.<br/>
        Comparado contra periodo anterior: <b>{prev_start_date.strftime('%d/%m/%Y')} al {prev_end_date.strftime('%d/%m/%Y')}</b>.
    </p>
    """, unsafe_allow_html=True)

    # Metric extractions with fallback priorities
    def _sum_metric(df, cols):
        if not isinstance(df, pd.DataFrame) or df.empty:
            return 0
        for col in cols:
            if col in df.columns:
                val = int(df[col].sum())
                if val > 0:
                    return val
        return 0

    media_views_curr = _sum_metric(df_curr_p, ["page_media_view", "impressions", "views", "video_views"])
    media_views_prev = _sum_metric(df_prev_p, ["page_media_view", "impressions", "views", "video_views"])

    reach_curr = _sum_metric(df_curr_p, ["page_total_media_view_unique", "reach", "impressions"])
    reach_prev = _sum_metric(df_prev_p, ["page_total_media_view_unique", "reach", "impressions"])

    engagements_curr = _sum_metric(df_curr_p, ["page_post_engagements", "post_engagement", "engagement"])
    engagements_prev = _sum_metric(df_prev_p, ["page_post_engagements", "post_engagement", "engagement"])

    pageviews_curr = _sum_metric(df_curr_p, ["page_views_total", "pageviews", "profile_visits"])
    pageviews_prev = _sum_metric(df_prev_p, ["page_views_total", "pageviews", "profile_visits"])

    follows_curr = _sum_metric(df_curr_p, ["page_follows", "followers"])
    follows_prev = _sum_metric(df_prev_p, ["page_follows", "followers"])

    likes_curr = _sum_metric(df_curr_p, ["likes"])
    likes_prev = _sum_metric(df_prev_p, ["likes"])

    comments_curr = _sum_metric(df_curr_p, ["comments"])
    comments_prev = _sum_metric(df_prev_p, ["comments"])

    shares_curr = _sum_metric(df_curr_p, ["shares"])
    shares_prev = _sum_metric(df_prev_p, ["shares"])

    clicks_curr = _sum_metric(df_curr_p, ["clicks"])
    clicks_prev = _sum_metric(df_prev_p, ["clicks"])

    # Hero Card
    hero_html = f"""
    <div class="hero-card" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;">
      <div><div class="lab">Visualizaciones Totales</div><div class="big">{media_views_curr:,}</div></div>
      <div><div class="lab">Interacciones Totales</div><div class="big">{engagements_curr:,}</div></div>
      <div><div class="lab">Nuevos Seguidores</div><div class="big">{follows_curr:,}</div></div>
    </div>
    """
    st.markdown(hero_html, unsafe_allow_html=True)

    # KPIs Grid
    st.markdown("### Métricas clave orgánicas con comparación")
    kpis_layout = '<div class="kpis">\n'
    kpis_layout += get_kpi_card_html("Visualizaciones", f"{media_views_curr:,}", "Vistas de contenido/medios", media_views_curr, media_views_prev) + "\n"
    kpis_layout += get_kpi_card_html("Alcance Único", f"{reach_curr:,}", "Personas alcanzadas", reach_curr, reach_prev) + "\n"
    kpis_layout += get_kpi_card_html("Interacciones con Posts", f"{engagements_curr:,}", "Interacciones y engagement", engagements_curr, engagements_prev) + "\n"
    kpis_layout += get_kpi_card_html("Visitas a Página/Perfil", f"{pageviews_curr:,}", "Visitas recibidas", pageviews_curr, pageviews_prev) + "\n"
    kpis_layout += get_kpi_card_html("Nuevos Seguidores", f"{follows_curr:,}", "Seguidores ganados", follows_curr, follows_prev) + "\n"
    if likes_curr > 0 or likes_prev > 0:
        kpis_layout += get_kpi_card_html("Reacciones / Me Gusta", f"{likes_curr:,}", "Likes en contenido", likes_curr, likes_prev) + "\n"
    if comments_curr > 0 or comments_prev > 0:
        kpis_layout += get_kpi_card_html("Comentarios", f"{comments_curr:,}", "Comentarios en publicaciones", comments_curr, comments_prev) + "\n"
    if shares_curr > 0 or shares_prev > 0:
        kpis_layout += get_kpi_card_html("Compartidos", f"{shares_curr:,}", "Publicaciones compartidas", shares_curr, shares_prev) + "\n"
    if clicks_curr > 0 or clicks_prev > 0:
        kpis_layout += get_kpi_card_html("Clics en Publicaciones", f"{clicks_curr:,}", "Clics en enlaces / posts", clicks_curr, clicks_prev) + "\n"
    kpis_layout += '</div>'
    st.markdown(kpis_layout, unsafe_allow_html=True)

    # Daily Trend Line Chart
    if "date" in df_curr_p.columns and len(df_curr_p["date"].dropna().unique()) > 1:
        st.markdown("### Tendencia Diaria")
        trend_df = df_curr_p.copy()
        trend_df["date"] = pd.to_datetime(trend_df["date"]).dt.date
        trend_agg = {}
        for col in ["impressions", "page_media_view", "reach", "page_total_media_view_unique", "engagement", "page_post_engagements", "page_views_total", "page_follows", "followers"]:
            if col in trend_df.columns:
                trend_agg[col] = "sum"
        if trend_agg:
            daily_chart_data = trend_df.groupby("date", as_index=False).agg(trend_agg)
            plot_df = pd.DataFrame({"Fecha": daily_chart_data["date"]})
            if "page_media_view" in daily_chart_data.columns:
                plot_df["Visualizaciones"] = daily_chart_data["page_media_view"]
            elif "impressions" in daily_chart_data.columns:
                plot_df["Visualizaciones"] = daily_chart_data["impressions"]
            if "page_total_media_view_unique" in daily_chart_data.columns:
                plot_df["Alcance"] = daily_chart_data["page_total_media_view_unique"]
            elif "reach" in daily_chart_data.columns:
                plot_df["Alcance"] = daily_chart_data["reach"]
            if "page_post_engagements" in daily_chart_data.columns:
                plot_df["Interacciones"] = daily_chart_data["page_post_engagements"]
            elif "engagement" in daily_chart_data.columns:
                plot_df["Interacciones"] = daily_chart_data["engagement"]
            plot_df = plot_df.set_index("Fecha")
            st.line_chart(plot_df, width="stretch")

    # Detail Table
    st.markdown("### Detalle por Contenido e Insights")
    group_cols = ["campaign_name"]
    for extra_col in ["permalink", "url", "page_id"]:
        if extra_col in df_curr_p.columns and extra_col not in group_cols:
            group_cols.append(extra_col)

    agg_dict = {}
    for m in [
        "page_media_view", "page_total_media_view_unique", "page_post_engagements",
        "page_views_total", "page_follows", "impressions", "reach", "engagement",
        "post_engagement", "followers", "pageviews", "likes", "comments", "shares", "clicks"
    ]:
        if m in df_curr_p.columns:
            agg_dict[m] = "sum"

    if agg_dict:
        df_table = df_curr_p.groupby(group_cols, as_index=False).agg(agg_dict)
    else:
        df_table = df_curr_p[group_cols].drop_duplicates().copy()

    # Formatted display columns
    rename_cols = {
        "campaign_name": "Contenido / Insights",
        "page_media_view": "Visualizaciones",
        "page_total_media_view_unique": "Alcance Único",
        "page_post_engagements": "Interacciones",
        "page_views_total": "Visitas a Página",
        "page_follows": "Seguidores",
        "impressions": "Visualizaciones (Total)",
        "reach": "Alcance (Total)",
        "engagement": "Interacciones (Total)",
        "likes": "Me Gusta",
        "comments": "Comentarios",
        "shares": "Compartidos",
        "clicks": "Clics",
        "permalink": "Enlace",
        "url": "URL",
    }

    display_renames = {k: v for k, v in rename_cols.items() if k in df_table.columns}
    df_display = df_table.rename(columns=display_renames)

    st.dataframe(df_display, width="stretch", hide_index=True)
