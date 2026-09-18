import streamlit as st
import pandas as pd
import numpy as np

from dashboard.ui import get_kpi_card_html


def render_generic_ads_platform_tab(
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
        "result_indicator", "advertising_channel_type", "campaign.advertising_channel_type",
        "campaign_type", "channel_type", "objective_type", "bidding_strategy_type",
        "campaign.bidding_strategy_type", "ad_group_name", "ad_name", "keyword", "status", "source_metrics"
    }
    for df_target in (df_curr_p, df_prev_p):
        if isinstance(df_target, pd.DataFrame) and not df_target.empty:
            for c in df_target.columns:
                if c not in non_numeric_cols:
                    df_target[c] = pd.to_numeric(df_target[c], errors="coerce").fillna(0)

    if not df_curr_p.empty:
        metric_cols = [col for col in ["impressions", "clicks", "spend", "conversions", "conversion", "engagement", "reach", "video_play_actions", "video_views", "video_watched_2s", "video_watched_6s", "results", "views", "follows", "profile_visits"] if col in df_curr_p.columns]
        if metric_cols:
            df_curr_p = df_curr_p[df_curr_p[metric_cols].sum(axis=1) > 0].copy()

    if df_curr_p.empty:
        st.warning(f"ℹ️ No se registraron datos activos con métricas mayores a 0 para {plat_label} en este periodo.")
        return

    title_color = "#0F172A" if theme_mode == "Claro" else "#EAF0F7"
    st.markdown(f"""
    <h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: {title_color};">{plat_label} &middot; {account_id}</h1>
    <p class="lede" style="margin-top: 15px;">
        Resultados del <b>{start_date.strftime('%d/%m/%Y')} al {end_date.strftime('%d/%m/%Y')}</b>.<br/>
        Comparado contra mes anterior completo: <b>{prev_start_date.strftime('%d/%m/%Y')} al {prev_end_date.strftime('%d/%m/%Y')}</b>.
    </p>
    """, unsafe_allow_html=True)

    if "spend" not in df_curr_p.columns or df_curr_p["spend"].sum() == 0:
        if "cost_micros" in df_curr_p.columns:
            df_curr_p["spend"] = pd.to_numeric(df_curr_p["cost_micros"], errors="coerce").fillna(0) / 1_000_000.0
        elif "cost" in df_curr_p.columns:
            df_curr_p["spend"] = pd.to_numeric(df_curr_p["cost"], errors="coerce").fillna(0)

    if not df_prev_p.empty and ("spend" not in df_prev_p.columns or df_prev_p["spend"].sum() == 0):
        if "cost_micros" in df_prev_p.columns:
            df_prev_p["spend"] = pd.to_numeric(df_prev_p["cost_micros"], errors="coerce").fillna(0) / 1_000_000.0
        elif "cost" in df_prev_p.columns:
            df_prev_p["spend"] = pd.to_numeric(df_prev_p["cost"], errors="coerce").fillna(0)

    total_spend_curr = df_curr_p["spend"].sum() if "spend" in df_curr_p.columns else 0.0
    total_conversions_curr = df_curr_p["conversions"].sum() if "conversions" in df_curr_p.columns else 0.0
    total_impressions_curr = df_curr_p["impressions"].sum() if "impressions" in df_curr_p.columns else 0
    total_clicks_curr = df_curr_p["clicks"].sum() if "clicks" in df_curr_p.columns else 0

    cpa_curr = total_spend_curr / total_conversions_curr if total_conversions_curr > 0 else 0.0
    avg_ctr_curr = total_clicks_curr / total_impressions_curr if total_impressions_curr > 0 else 0.0
    avg_cpc_curr = total_spend_curr / total_clicks_curr if total_clicks_curr > 0 else 0.0

    total_spend_prev = df_prev_p["spend"].sum() if (not df_prev_p.empty and "spend" in df_prev_p.columns) else 0.0
    total_conversions_prev = df_prev_p["conversions"].sum() if (not df_prev_p.empty and "conversions" in df_prev_p.columns) else 0.0
    total_impressions_prev = df_prev_p["impressions"].sum() if (not df_prev_p.empty and "impressions" in df_prev_p.columns) else 0
    total_clicks_prev = df_prev_p["clicks"].sum() if (not df_prev_p.empty and "clicks" in df_prev_p.columns) else 0

    avg_ctr_prev = total_clicks_prev / total_impressions_prev if total_impressions_prev > 0 else 0.0
    avg_cpc_prev = total_spend_prev / total_clicks_prev if total_clicks_prev > 0 else 0.0

    avg_cpm_curr = (total_spend_curr * 1000 / total_impressions_curr) if total_impressions_curr > 0 else 0.0
    avg_cpm_prev = (total_spend_prev * 1000 / total_impressions_prev) if total_impressions_prev > 0 else 0.0

    if total_conversions_curr > 0:
        hero_html = f"""
        <div class="hero-card" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;">
          <div><div class="lab">Conversiones Totales</div><div class="big">{total_conversions_curr:,.0f}</div></div>
          <div><div class="lab">Costo por Conversión (CPA)</div><div class="big">${cpa_curr:,.2f}</div></div>
          <div><div class="lab">Importe Gastado</div><div class="big">${total_spend_curr:,.2f}</div></div>
        </div>
        """
    else:
        hero_html = f"""
        <div class="hero-card" style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;">
          <div><div class="lab">Clics / Interacciones</div><div class="big">{total_clicks_curr:,}</div></div>
          <div><div class="lab">Costo por Clic (CPC)</div><div class="big">${avg_cpc_curr:,.2f}</div></div>
          <div><div class="lab">Importe Gastado</div><div class="big">${total_spend_curr:,.2f}</div></div>
        </div>
        """

    st.markdown(hero_html, unsafe_allow_html=True)

    st.markdown("### Métricas clave con comparación")
    kpis_layout = '<div class="kpis">\n'
    kpis_layout += get_kpi_card_html("Inversión Total", f"${total_spend_curr:,.2f}", "Gasto total en pauta", total_spend_curr, total_spend_prev, lower_is_better=True) + "\n"
    kpis_layout += get_kpi_card_html("Impresiones Totales", f"{total_impressions_curr:,}", "Vistas acumuladas", total_impressions_curr, total_impressions_prev) + "\n"
    kpis_layout += get_kpi_card_html("Clics", f"{total_clicks_curr:,}", "Interacciones con anuncios", total_clicks_curr, total_clicks_prev) + "\n"
    if total_conversions_curr > 0:
        kpis_layout += get_kpi_card_html("Conversiones", f"{total_conversions_curr:,.0f}", "Acciones de conversión logradas", total_conversions_curr, total_conversions_prev) + "\n"
        kpis_layout += get_kpi_card_html("CPA Promedio", f"${cpa_curr:,.2f}", "Costo por conversión", cpa_curr, (total_spend_prev / total_conversions_prev) if total_conversions_prev > 0 else 0.0, lower_is_better=True) + "\n"
    else:
        kpis_layout += get_kpi_card_html("CPM Promedio", f"${avg_cpm_curr:,.2f}", "Costo por mil impresiones", avg_cpm_curr, avg_cpm_prev, lower_is_better=True) + "\n"
    kpis_layout += get_kpi_card_html("CTR Promedio", f"{avg_ctr_curr:.2%}", "Tasa de clics/impresión", avg_ctr_curr, avg_ctr_prev) + "\n"
    kpis_layout += get_kpi_card_html("CPC Promedio", f"${avg_cpc_curr:,.2f}", "Costo promedio por clic", avg_cpc_curr, avg_cpc_prev, lower_is_better=True) + "\n"
    if "video_play_actions" in df_curr_p.columns:
        tot_plays = int(pd.to_numeric(df_curr_p["video_play_actions"], errors="coerce").fillna(0).sum())
        if tot_plays > 0:
            tot_plays_prev = int(pd.to_numeric(df_prev_p["video_play_actions"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "video_play_actions" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Reproducciones Video", f"{tot_plays:,}", "Vistas totales de video", tot_plays, tot_plays_prev) + "\n"
    if "views" in df_curr_p.columns:
        tot_views = int(pd.to_numeric(df_curr_p["views"], errors="coerce").fillna(0).sum())
        if tot_views > 0:
            tot_views_prev = int(pd.to_numeric(df_prev_p["views"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "views" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Visualizaciones", f"{tot_views:,}", "Reproducciones de video", tot_views, tot_views_prev) + "\n"
    if "watchTimeMinutes" in df_curr_p.columns:
        tot_wt = float(pd.to_numeric(df_curr_p["watchTimeMinutes"], errors="coerce").fillna(0).sum())
        if tot_wt > 0:
            tot_wt_prev = float(pd.to_numeric(df_prev_p["watchTimeMinutes"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "watchTimeMinutes" in df_prev_p.columns) else 0.0
            kpis_layout += get_kpi_card_html("Minutos Visualizados", f"{tot_wt:,.0f} min", "Tiempo total de reproducción", tot_wt, tot_wt_prev) + "\n"
    if "subscribersGained" in df_curr_p.columns:
        tot_subs = int(pd.to_numeric(df_curr_p["subscribersGained"], errors="coerce").fillna(0).sum())
        if tot_subs > 0:
            tot_subs_prev = int(pd.to_numeric(df_prev_p["subscribersGained"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "subscribersGained" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Nuevos Suscriptores", f"{tot_subs:,}", "Suscriptores ganados en el canal", tot_subs, tot_subs_prev) + "\n"
    if "likes" in df_curr_p.columns:
        tot_likes = int(pd.to_numeric(df_curr_p["likes"], errors="coerce").fillna(0).sum())
        if tot_likes > 0:
            tot_likes_prev = int(pd.to_numeric(df_prev_p["likes"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "likes" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Me Gusta", f"{tot_likes:,}", "Likes en publicaciones o videos", tot_likes, tot_likes_prev) + "\n"
    if "comments" in df_curr_p.columns:
        tot_comments = int(pd.to_numeric(df_curr_p["comments"], errors="coerce").fillna(0).sum())
        if tot_comments > 0:
            tot_comments_prev = int(pd.to_numeric(df_prev_p["comments"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "comments" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Comentarios", f"{tot_comments:,}", "Comentarios recibidos", tot_comments, tot_comments_prev) + "\n"
    if "follows" in df_curr_p.columns:
        tot_follows = int(pd.to_numeric(df_curr_p["follows"], errors="coerce").fillna(0).sum())
        if tot_follows > 0:
            tot_follows_prev = int(pd.to_numeric(df_prev_p["follows"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "follows" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Seguidores Ganados", f"{tot_follows:,}", "Nuevos seguidores TikTok", tot_follows, tot_follows_prev) + "\n"
    if "profile_visits" in df_curr_p.columns:
        tot_visits = int(pd.to_numeric(df_curr_p["profile_visits"], errors="coerce").fillna(0).sum())
        if tot_visits > 0:
            tot_visits_prev = int(pd.to_numeric(df_prev_p["profile_visits"], errors="coerce").fillna(0).sum()) if (not df_prev_p.empty and "profile_visits" in df_prev_p.columns) else 0
            kpis_layout += get_kpi_card_html("Visitas al Perfil", f"{tot_visits:,}", "Clics al perfil de TikTok", tot_visits, tot_visits_prev) + "\n"
    kpis_layout += '</div>'
    st.markdown(kpis_layout, unsafe_allow_html=True)

    st.markdown("### Detalle de Campañas y Resultados")
    group_cols = ["campaign_name"]
    for extra_dim in ["advertising_channel_type", "campaign.advertising_channel_type", "campaign_type", "channel_type", "objective_type", "bidding_strategy_type", "campaign.bidding_strategy_type", "ad_group_name", "ad_name", "keyword"]:
        if extra_dim in df_curr_p.columns and extra_dim not in group_cols:
            group_cols.append(extra_dim)

    agg_dict = {
        "spend": "sum",
        "impressions": "sum",
        "clicks": "sum",
        "conversions": "sum",
    }
    for m in ["reach", "video_play_actions", "views", "watchTimeMinutes", "subscribersGained", "likes", "comments", "follows", "profile_visits"]:
        if m in df_curr_p.columns:
            agg_dict[m] = "sum"

    df_table = df_curr_p.groupby(group_cols, as_index=False).agg(agg_dict)

    active_mask = (df_table["spend"] > 0) | (df_table["impressions"] > 0) | (df_table["clicks"] > 0) | (df_table["conversions"] > 0)
    for m in ["reach", "video_play_actions", "follows", "profile_visits"]:
        if m in df_table.columns:
            active_mask |= (df_table[m] > 0)
    df_table = df_table[active_mask].copy()

    if not df_table.empty:
        df_table["CTR"] = (df_table["clicks"] / df_table["impressions"]).apply(lambda x: f"{x:.2%}" if x > 0 else "0.00%")
        df_table["CPC"] = (df_table["spend"] / df_table["clicks"]).apply(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
        df_table["CPM"] = (df_table["spend"] * 1000 / df_table["impressions"]).apply(lambda x: f"${x:,.2f}" if x > 0 else "$0.00")
        if df_table["conversions"].sum() > 0:
            df_table["CPA"] = (df_table["spend"] / df_table["conversions"]).apply(lambda x: f"${x:,.2f}" if (pd.notna(x) and x > 0 and not np.isinf(x)) else "—")
        else:
            df_table["CPA"] = "—"
        df_table["Inversión"] = df_table["spend"].apply(lambda x: f"${x:,.2f}")
        df_table["Impresiones"] = df_table["impressions"].apply(lambda x: f"{x:,}")
        df_table["Clics"] = df_table["clicks"].apply(lambda x: f"{x:,}")
        df_table["Conversiones"] = df_table["conversions"].apply(lambda x: f"{x:,.0f}")
        if "video_play_actions" in df_table.columns:
            df_table["Reproducciones"] = pd.to_numeric(df_table["video_play_actions"], errors="coerce").fillna(0).apply(lambda x: f"{int(x):,}")
        if "follows" in df_table.columns:
            df_table["Seguidores"] = pd.to_numeric(df_table["follows"], errors="coerce").fillna(0).apply(lambda x: f"{int(x):,}")
        if "profile_visits" in df_table.columns:
            df_table["Visitas Perfil"] = pd.to_numeric(df_table["profile_visits"], errors="coerce").fillna(0).apply(lambda x: f"{int(x):,}")

        rename_map = {
            "campaign_name": "Campaña",
            "advertising_channel_type": "Tipo de Campaña",
            "campaign.advertising_channel_type": "Tipo de Campaña",
            "channel_type": "Tipo de Campaña",
            "campaign_type": "Tipo de Campaña",
            "objective_type": "Objetivo de Campaña",
            "bidding_strategy_type": "Estrategia de Puja",
            "campaign.bidding_strategy_type": "Estrategia de Puja",
            "ad_group_name": "Grupo de Anuncios",
            "ad_name": "Anuncio",
            "keyword": "Palabra Clave",
        }

        applied_renames = {}
        for old_c, new_c in rename_map.items():
            if old_c in df_table.columns and new_c not in df_table.columns and new_c not in applied_renames.values():
                applied_renames[old_c] = new_c
        df_table = df_table.rename(columns=applied_renames)
        df_table = df_table.loc[:, ~df_table.columns.duplicated()].copy()

        if "Tipo de Campaña" not in df_table.columns:
            if "Objetivo de Campaña" in df_table.columns:
                df_table["Tipo de Campaña"] = df_table["Objetivo de Campaña"]
            elif plat_key == "google_ads":
                def infer_google_channel(name):
                    n = str(name).lower()
                    if "performance max" in n or "pmax" in n or "rendimiento" in n:
                        return "Rendimiento Máximo (PMax)"
                    if "demand gen" in n or "demanda" in n or "suscriptores" in n:
                        return "Generación de Demanda"
                    if "video" in n or "vídeo" in n or "visualizaciones" in n or "bumper" in n or "shorts" in n:
                        return "Video"
                    if "display" in n:
                        return "Display"
                    if "inteligente" in n or "smart" in n:
                        return "Inteligente"
                    return "Búsqueda (Search)"
                df_table["Tipo de Campaña"] = df_table["Campaña"].apply(infer_google_channel)
            elif plat_key == "tiktok_ads":
                def infer_tiktok_channel(name):
                    n = str(name).lower()
                    if "reach" in n or "alcance" in n:
                        return "Alcance (Reach)"
                    if "lead" in n:
                        return "Generación de Leads"
                    if "video" in n or "view" in n:
                        return "Visualizaciones de Video"
                    if "conversion" in n:
                        return "Conversiones"
                    return "Tráfico (Traffic)"
                df_table["Tipo de Campaña"] = df_table["Campaña"].apply(infer_tiktok_channel)

        df_table = df_table.loc[:, ~df_table.columns.duplicated()].copy()

        raw_display_cols = ["Campaña", "Tipo de Campaña", "Objetivo de Campaña", "Estrategia de Puja", "Grupo de Anuncios", "Anuncio", "Palabra Clave", "Inversión", "Impresiones", "Clics", "Reproducciones", "Seguidores", "Visitas Perfil", "CTR", "CPC", "CPM"]
        if df_curr_p["conversions"].sum() > 0:
            raw_display_cols.extend(["Conversiones", "CPA"])

        display_cols = []
        for c in raw_display_cols:
            if c in df_table.columns and c not in display_cols:
                display_cols.append(c)

        st.dataframe(df_table[display_cols], width="stretch", hide_index=True)
