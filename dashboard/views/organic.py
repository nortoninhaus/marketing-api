import re
import html
import streamlit as st
import pandas as pd
import numpy as np

from dashboard.api import fetch_meta_post_preview
from dashboard.ui import get_kpi_card_html


def _clean_post_title(raw_name: str, message: str = "") -> str:
    """Clean technical prefixes and raw IDs from organic post titles."""
    if message and str(message).strip():
        first_line = str(message).strip().split("\n")[0].strip()
        return first_line[:80] + ("..." if len(first_line) > 80 else "")
    clean = re.sub(r"^(Post_|IG_Post_)?([0-9]+_)+", "", str(raw_name)).strip()
    clean = re.sub(r"^[0-9]+$", "Publicación", clean)
    clean = clean.replace("_", " ").strip()
    return clean or "Publicación"


def render_organic_platform_tab(
    cfg,
    df_curr_all,
    df_prev_all,
    start_date,
    end_date,
    prev_start_date,
    prev_end_date,
    theme_mode,
    client_id=None,
    api_key=None,
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

    # Fallback extraction from source_metrics if raw columns are 0 or missing
    for df_target in (df_curr_p, df_prev_p):
        if isinstance(df_target, pd.DataFrame) and not df_target.empty and "source_metrics" in df_target.columns:
            for m_key in ["page_media_view", "page_follows", "page_total_media_view_unique", "page_post_engagements", "page_views_total"]:
                if m_key not in df_target.columns or df_target[m_key].sum() == 0:
                    try:
                        extracted = df_target["source_metrics"].apply(
                            lambda m: float(m.get(m_key, 0)) if isinstance(m, dict) and m.get(m_key) is not None and not isinstance(m.get(m_key), dict) else 0.0
                        )
                        if extracted.sum() > 0:
                            df_target[m_key] = extracted
                    except Exception:
                        pass

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
                val = int(pd.to_numeric(df[col], errors="coerce").fillna(0).sum())
                if val > 0:
                    return val
        if "source_metrics" in df.columns:
            for col in cols:
                try:
                    val = int(df["source_metrics"].apply(
                        lambda m: float(m.get(col, 0)) if isinstance(m, dict) and m.get(col) is not None and not isinstance(m.get(col), dict) else (
                            float(sum(float(v) for v in m[col].values() if v is not None)) if isinstance(m, dict) and isinstance(m.get(col), dict) else 0.0
                        )
                    ).sum())
                    if val > 0:
                        return val
                except Exception:
                    pass
        return 0

    def _extract_followers(df):
        if not isinstance(df, pd.DataFrame) or df.empty:
            return 0, "Seguidores ganados"
        for fcol in ["page_follows", "followers", "follower_count"]:
            series = None
            if fcol in df.columns and df[fcol].sum() > 0:
                s = pd.to_numeric(df[fcol], errors="coerce").fillna(0)
                series = s[s > 0]
            elif "source_metrics" in df.columns:
                try:
                    extracted = df["source_metrics"].apply(
                        lambda m: float(m.get(fcol, 0)) if isinstance(m, dict) and m.get(fcol) is not None else 0.0
                    )
                    series = extracted[extracted > 0]
                except Exception:
                    pass
            if series is not None and len(series) > 0:
                earliest = series.iloc[0]
                latest = series.iloc[-1]
                net = int(latest - earliest)
                if net > 0:
                    return net, f"Nuevos en el periodo (Total: {int(latest):,})"
                elif int(latest) > 0:
                    return int(latest), "Total seguidores acumulados"
        return _sum_metric(df, ["page_follows", "followers"]), "Seguidores ganados"

    media_views_curr = _sum_metric(df_curr_p, ["page_media_view", "impressions", "views", "video_views"])
    media_views_prev = _sum_metric(df_prev_p, ["page_media_view", "impressions", "views", "video_views"])

    reach_curr = _sum_metric(df_curr_p, ["page_total_media_view_unique", "reach", "impressions"])
    reach_prev = _sum_metric(df_prev_p, ["page_total_media_view_unique", "reach", "impressions"])

    engagements_curr = _sum_metric(df_curr_p, ["page_post_engagements", "post_engagement", "engagement"])
    engagements_prev = _sum_metric(df_prev_p, ["page_post_engagements", "post_engagement", "engagement"])

    pageviews_curr = _sum_metric(df_curr_p, ["page_views_total", "pageviews", "profile_visits"])
    pageviews_prev = _sum_metric(df_prev_p, ["page_views_total", "pageviews", "profile_visits"])

    follows_curr, follows_sub = _extract_followers(df_curr_p)
    follows_prev, _ = _extract_followers(df_prev_p)

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
    kpis_layout += get_kpi_card_html("Nuevos Seguidores", f"{follows_curr:,}", follows_sub, follows_curr, follows_prev) + "\n"
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
            if "page_media_view" in daily_chart_data.columns and daily_chart_data["page_media_view"].sum() > 0:
                plot_df["Visualizaciones"] = daily_chart_data["page_media_view"]
            elif "impressions" in daily_chart_data.columns:
                plot_df["Visualizaciones"] = daily_chart_data["impressions"]
            if "page_total_media_view_unique" in daily_chart_data.columns and daily_chart_data["page_total_media_view_unique"].sum() > 0:
                plot_df["Alcance"] = daily_chart_data["page_total_media_view_unique"]
            elif "reach" in daily_chart_data.columns:
                plot_df["Alcance"] = daily_chart_data["reach"]
            if "page_post_engagements" in daily_chart_data.columns and daily_chart_data["page_post_engagements"].sum() > 0:
                plot_df["Interacciones"] = daily_chart_data["page_post_engagements"]
            elif "engagement" in daily_chart_data.columns:
                plot_df["Interacciones"] = daily_chart_data["engagement"]
            plot_df = plot_df.set_index("Fecha")
            st.line_chart(plot_df, width="stretch")

    # Recent Posts / Content Section (Top 3 por visualizaciones / alcance)
    posts_mask = df_curr_p["campaign_name"].astype(str).str.contains("Post_", case=False, na=False)
    posts_df = df_curr_p[posts_mask].copy()
    if not posts_df.empty:
        # Sort by visualizaciones or alcance descending
        sort_col = "page_media_view"
        for candidate in ["page_media_view", "views", "page_total_media_view_unique", "reach", "clicks"]:
            if candidate in posts_df.columns and posts_df[candidate].sum() > 0:
                sort_col = candidate
                break

        posts_df = posts_df.sort_values(by=sort_col, ascending=False)
        display_posts = posts_df.head(3)

        st.markdown("### 📌 Top 3 Publicaciones")
        cols = st.columns(len(display_posts))
        for col_idx, (_, post_row) in enumerate(display_posts.iterrows()):
            rank = col_idx + 1
            with cols[col_idx]:
                with st.container(border=True):
                    post_id = str(post_row.get("post_id") or "")
                    if not post_id or post_id == "nan":
                        m = re.search(r"^(?:Post_|IG_Post_)?([0-9_]+)", str(post_row.get("campaign_name", "")))
                        if m:
                            post_id = m.group(1).rstrip("_")

                    image_url = str(post_row.get("image_url") or "").strip()
                    if image_url == "nan":
                        image_url = ""
                    message = str(post_row.get("message") or "").strip()
                    if message == "nan":
                        message = ""
                    permalink = str(post_row.get("permalink") or post_row.get("url") or "").strip()
                    if permalink == "nan":
                        permalink = ""

                    if (not image_url or not message) and (post_id or permalink):
                        preview_data = fetch_meta_post_preview(client_id, account_id, post_id, api_key, permalink=permalink)
                        if preview_data:
                            if not image_url and preview_data.get("image_url"):
                                image_url = preview_data["image_url"]
                            if not message and preview_data.get("message"):
                                message = preview_data["message"]
                            if not permalink and preview_data.get("permalink"):
                                permalink = preview_data["permalink"]

                    if image_url:
                        escaped_img = html.escape(image_url)
                        st.markdown(f"""
                        <div style="width: 100%; height: 280px; overflow: hidden; border-radius: 8px; margin-bottom: 10px; background: #0b0f19;">
                            <img src="{escaped_img}" style="width: 100%; height: 100%; object-fit: cover; object-position: center;" alt="Preview" />
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                        <div style="width: 100%; height: 280px; border-radius: 8px; margin-bottom: 10px; background: #1e293b; display: grid; place-items: center; color: #94a3b8; font-size: 0.9rem;">
                            Sin imagen disponible
                        </div>
                        """, unsafe_allow_html=True)

                    clean_title = _clean_post_title(post_row.get("campaign_name", ""), message=message)
                    escaped_title = html.escape(clean_title)
                    st.markdown(f"""
                    <div style="font-weight: 700; font-size: 1rem; line-height: 1.35; height: 2.7em; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; margin-bottom: 4px;">
                        #{rank} &middot; {escaped_title}
                    </div>
                    """, unsafe_allow_html=True)

                    if "date" in post_row and pd.notna(post_row["date"]):
                        st.caption(f"📅 {pd.to_datetime(post_row['date']).strftime('%d/%m/%Y')}")

                    v = int(post_row.get("page_media_view", post_row.get("views", 0)))
                    r = int(post_row.get("page_total_media_view_unique", post_row.get("reach", 0)))
                    c = int(post_row.get("clicks", 0))
                    e = int(post_row.get("page_post_engagements", post_row.get("engagement", 0)))

                    metric_items = [f"👁️ **{v:,}** vistas"]
                    if r > 0:
                        metric_items.append(f"👥 **{r:,}** alcance")
                    if e > 0 or (r == 0 and c == 0):
                        metric_items.append(f"💬 **{e:,}** interac.")
                    if c > 0:
                        metric_items.append(f"🖱️ **{c:,}** clics")
                    st.write(" &nbsp;|&nbsp; ".join(metric_items[:3]))

                    if permalink:
                        st.link_button("Ver publicación ↗", permalink, width="stretch")
    else:
        # Fallback to page permalink when only Page_Insights is present
        page_urls = df_curr_p["permalink"].dropna().tolist() if "permalink" in df_curr_p.columns else []
        if not page_urls and "url" in df_curr_p.columns:
            page_urls = df_curr_p["url"].dropna().tolist()
        if page_urls:
            page_url = page_urls[0]
            st.markdown("### 🔗 Enlace a la Página / Perfil")
            st.link_button(f"Abrir {plat_label} en Facebook / Meta ↗", str(page_url))

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

    if "Contenido / Insights" in df_display.columns:
        df_display["Contenido / Insights"] = df_display["Contenido / Insights"].apply(
            lambda n: _clean_post_title(n) if "Post_" in str(n) else n
        )

    column_config = {}
    if "Enlace" in df_display.columns:
        column_config["Enlace"] = st.column_config.LinkColumn(
            "Enlace",
            help="Enlace directo a la publicación o página",
            validate=r"^https?://.*",
            display_text="Abrir enlace ↗",
        )
    if "URL" in df_display.columns:
        column_config["URL"] = st.column_config.LinkColumn(
            "URL",
            display_text="Ver página ↗",
        )

    st.dataframe(df_display, width="stretch", hide_index=True, column_config=column_config)
