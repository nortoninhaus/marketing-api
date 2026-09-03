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

DASHBOARD_CACHE_VERSION = 7


if os.getenv("DASHBOARD_AUTH_SELF_CHECK") == "1":
    dashboard_auth_self_check()
    raise SystemExit("dashboard auth self-check passed")


def toggle_theme():
    st.session_state["theme_switch"] = not st.session_state.get("theme_switch", True)


def log_demographics_toggle(user_id, platform_key, account_id):
    if st.session_state.get("load_demographics"):
        log_demographics_check(user_id, platform_key, account_id)


REPORT_TEMPLATES = {
    "Nutri": "nutri",
    "Adriana Hoyos": "adriana_hoyos",
    "ARTZ": "artz",
    "Shamuna": "shamuna",
}


def template_report_html(
    frame: pd.DataFrame,
    template_name: str,
    report_context: dict[str, Any],
    previous_frame: pd.DataFrame | None = None,
    export_table: pd.DataFrame | None = None,
    optional: dict[str, Any] | None = None,
) -> str:
    template_key = REPORT_TEMPLATES.get(template_name, template_name.lower().replace(" ", "_"))
    account_name = str(report_context.get("Cuenta", report_context.get("account_name", "")))
    account_id = str(report_context.get("account_id", ""))
    platform = str(report_context.get("platform", "meta_ads"))
    start_date = str(report_context.get("start_date", ""))
    end_date = str(report_context.get("end_date", ""))
    connections = report_context.get("connections")
    if not connections:
        connections = [{
            "account_id": account_id or "default",
            "account_name": account_name,
            "platform": platform,
        }] if account_name else []
    platforms = report_context.get("platforms") or ([platform] if platform else [])
    query_context = {
        "connections": connections,
        "account_id": account_id,
        "account_name": account_name,
        "platform": platform,
        "start_date": start_date,
        "end_date": end_date,
        "period": {
            "start": start_date,
            "end": end_date,
        },
        "platforms": platforms,
    }
    payload = build_report_payload(
        template_key,
        current=frame,
        previous=previous_frame,
        export_table=export_table if export_table is not None else frame,
        query_context=query_context,
        optional=optional,
    )
    return render_report(template_key, payload)


def segmented_pdf_download_html(export_name, background_color):
    return f"""
    <div data-pdf-export-control="true" data-pdf-export-name="{export_name}">
        <button type="button">Descargar PDF</button>
        <p role="status" aria-live="polite"></p>
    </div>
    <style>
    [data-pdf-export-name="{export_name}"] button {{
        width: 100%;
        padding: 0.55rem 0.75rem;
        border: 1px solid #02569e;
        border-radius: 0.5rem;
        background: #02569e;
        color: #FFFFFF;
        font-weight: 700;
        cursor: pointer;
    }}
    [data-pdf-export-name="{export_name}"] button:disabled {{
        cursor: wait;
        opacity: 0.65;
    }}
    [data-pdf-export-name="{export_name}"] p {{
        min-height: 1rem;
        margin: 0.3rem 0 0;
        color: #02569e;
        font-size: 0.75rem;
    }}
    </style>
    <script>
    (() => {{
        const controls = document.querySelectorAll(
            '[data-pdf-export-name="{export_name}"]'
        );
        const root = controls[controls.length - 1];
        if (!root || root.dataset.ready === "true") return;
        root.dataset.ready = "true";

        const button = root.querySelector("button");
        const status = root.querySelector('[role="status"]');
        const trigger = document.querySelector('[data-testid="stPopoverButton"]');
        trigger?.closest('[data-testid="stPopover"]')
            ?.setAttribute("data-pdf-export-control", "true");

        const loadScript = (src, isReady) => {{
            if (isReady()) return Promise.resolve();
            return new Promise((resolve, reject) => {{
                const existing = document.querySelector(`script[src="${{src}}"]`);
                const script = existing || document.createElement("script");
                script.addEventListener("load", resolve, {{ once: true }});
                script.addEventListener(
                    "error",
                    () => reject(new Error(`Failed to load ${{src}}`)),
                    {{ once: true }},
                );
                if (!existing) {{
                    script.src = src;
                    document.head.appendChild(script);
                }}
            }});
        }};

        button.addEventListener("click", async () => {{
            button.disabled = true;
            status.style.color = "#02569e";
            status.textContent = "Preparando PDF…";

            try {{
                await loadScript(
                    "https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js",
                    () => Boolean(window.html2canvas),
                );
                await loadScript(
                    "https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js",
                    () => Boolean(window.jspdf?.jsPDF),
                );

                const target = document.querySelector(
                    '[data-testid="stMainBlockContainer"]'
                );
                if (!target) throw new Error("Dashboard report container not found");

                const pageWidthMm = 281;
                const pageHeightMm = 194;
                const captureWidth = Math.ceil(target.scrollWidth);
                const reportHeight = Math.ceil(target.scrollHeight);
                const pageHeightPx = Math.max(
                    1,
                    Math.floor(captureWidth * pageHeightMm / pageWidthMm),
                );
                const pageCount = Math.ceil(reportHeight / pageHeightPx);
                if (!captureWidth || !reportHeight || !pageCount) {{
                    throw new Error("Dashboard report is empty");
                }}

                const pdf = new window.jspdf.jsPDF({{
                    orientation: "landscape",
                    unit: "mm",
                    format: "a4",
                    compress: true,
                }});
                let renderedPageCount = 0;

                const canvasHasContent = (canvas) => {{
                    const sample = document.createElement("canvas");
                    sample.width = 64;
                    sample.height = Math.max(
                        1,
                        Math.round(64 * canvas.height / canvas.width),
                    );
                    const context = sample.getContext("2d", {{ willReadFrequently: true }});
                    context.drawImage(canvas, 0, 0, sample.width, sample.height);
                    const pixels = context.getImageData(
                        0,
                        0,
                        sample.width,
                        sample.height,
                    ).data;
                    const background = pixels.slice(0, 4);
                    for (let index = 4; index < pixels.length; index += 4) {{
                        if (
                            Math.abs(pixels[index] - background[0]) > 8 ||
                            Math.abs(pixels[index + 1] - background[1]) > 8 ||
                            Math.abs(pixels[index + 2] - background[2]) > 8 ||
                            Math.abs(pixels[index + 3] - background[3]) > 8
                        ) return true;
                    }}
                    return false;
                }};

                // ponytail: one page-sized canvas avoids browser limits from one giant report canvas.
                for (let pageIndex = 0; pageIndex < pageCount; pageIndex += 1) {{
                    const pageTop = pageIndex * pageHeightPx;
                    const sliceHeight = Math.min(
                        pageHeightPx,
                        reportHeight - pageTop,
                    );
                    status.textContent = `Generando página ${{pageIndex + 1}} de ${{pageCount}}…`;

                    const canvas = await window.html2canvas(target, {{
                        scale: 1.5,
                        useCORS: true,
                        allowTaint: false,
                        backgroundColor: "{background_color}",
                        width: captureWidth,
                        height: sliceHeight,
                        x: 0,
                        y: pageTop,
                        scrollX: 0,
                        scrollY: 0,
                        windowWidth: captureWidth,
                        windowHeight: reportHeight,
                        logging: false,
                        onclone: (clonedDoc) => {{
                            clonedDoc.querySelectorAll(
                                '[data-testid="stHeader"], [data-testid="stSidebar"], ' +
                                '[data-testid="stPopoverBody"], [data-pdf-export-control="true"], ' +
                                '[data-testid^="stElementToolbar"], ' +
                                '[data-testid="stTooltipHoverTarget"], ' +
                                '[data-testid="stBaseButton-elementToolbar"], ' +
                                '[data-testid="stVegaLiteChart"] details'
                            ).forEach((element) => element.remove());
                        }},
                        ignoreElements: (element) => Boolean(
                            element.closest?.('[data-pdf-export-control="true"]')
                        ),
                    }});
                    if (!canvas.width || !canvas.height) {{
                        throw new Error(`PDF page ${{pageIndex + 1}} is empty`);
                    }}
                    if (!canvasHasContent(canvas)) continue;

                    if (renderedPageCount > 0) pdf.addPage();
                    const imageHeightMm = Math.min(
                        pageHeightMm,
                        pageWidthMm * canvas.height / canvas.width,
                    );
                    pdf.addImage(
                        canvas,
                        "JPEG",
                        8,
                        8,
                        pageWidthMm,
                        imageHeightMm,
                        undefined,
                        "FAST",
                    );
                    renderedPageCount += 1;
                }}
                if (!renderedPageCount) throw new Error("Dashboard capture is empty");

                await pdf.save("{export_name}.pdf", {{ returnPromise: true }});
                status.style.color = "#10B981";
                status.textContent = `PDF generado correctamente (${{renderedPageCount}} páginas).`;
                setTimeout(() => {{ status.textContent = ""; }}, 3000);
            }} catch (error) {{
                console.error("PDF export failed", error);
                status.style.color = "#FF4B4B";
                status.textContent = "No se pudo generar el PDF.";
            }} finally {{
                button.disabled = false;
            }}
        }});
    }})();
    </script>
    """


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
header.stAppHeader,
[data-testid="stHeader"],
.stAppToolbar,
[data-testid="stToolbar"] {
    background-color: transparent !important;
    box-shadow: none !important;
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    padding: 0px !important;
    margin: 0px !important;
    border: none !important;
    overflow: visible !important;
    position: absolute !important;
    top: 14px !important;
    left: 16px !important;
    z-index: 9999 !important;
}

.stAppToolbar > div,
[data-testid="stToolbar"] > div,
.st-emotion-cache-1j22a0y {
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    padding: 0px !important;
    margin: 0px !important;
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

/* Remove default Streamlit top padding, container margins and style tags gap */
.block-container,
[data-testid="stMainBlockContainer"],
.stMainBlockContainer {
    padding-top: 0rem !important;
    padding-bottom: 2rem !important;
    margin-top: 0rem !important;
    position: relative !important;
}

[data-testid="stAppViewContainer"] > .main {
    padding-top: 0rem !important;
}

/* Hide empty style/script/bridge containers from flexbox layout so they do NOT take gap space */
div[data-testid="stElementContainer"]:empty,
div[data-testid="stElementContainer"]:has(style),
div[data-testid="stElementContainer"]:has(script),
div[data-testid="stElementContainer"]:has([data-testid="stHtml"]),
div[data-testid="stElementContainer"]:has(iframe[style*="display: none"]),
div[data-testid="stElementContainer"]:has(iframe[height="0"]),
div[data-testid="stElementContainer"].element-container:has(style),
div.element-container:has(style) {
    display: none !important;
    position: absolute !important;
    height: 0px !important;
    max-height: 0px !important;
    width: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
}

/* Header layout styling */
.custom-header {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding: 0px;
    margin: 0px;
    position: relative;
}
.header-live-badge {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    white-space: nowrap !important;
    padding: 0px;
    margin: 0px;
}

/* Header actions row: group download button and API Directa tightly together */
[data-testid="stHorizontalBlock"]:has(button[aria-label="Descargar reporte"]) {
    justify-content: flex-end !important;
    align-items: center !important;
    gap: 8px !important;
}

[data-testid="stColumn"]:has(button[aria-label="Descargar reporte"]) {
    display: flex !important;
    justify-content: flex-end !important;
    align-items: center !important;
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: auto !important;
}

[data-testid="stColumn"]:has(.header-live-badge) {
    display: flex !important;
    justify-content: flex-start !important;
    align-items: center !important;
    flex: 0 0 auto !important;
    width: auto !important;
    min-width: auto !important;
}

button[aria-label="Descargar reporte"],
[data-testid="stBaseButton-secondary"][aria-label="Descargar reporte"] {
    background-color: #02569e !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 8px !important;
    padding: 0 !important;
    font-size: 18px !important;
    font-weight: 700 !important;
    height: 34px !important;
    min-height: 34px !important;
    max-height: 34px !important;
    width: 34px !important;
    min-width: 34px !important;
    max-width: 34px !important;
    line-height: 1 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0 !important;
    box-shadow: 0 2px 8px rgba(2, 86, 158, 0.4) !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}
button[aria-label="Descargar reporte"]:hover,
[data-testid="stBaseButton-secondary"][aria-label="Descargar reporte"]:hover {
    background-color: #0369a1 !important;
    border-color: rgba(255, 255, 255, 0.4) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(2, 86, 158, 0.5) !important;
}
button[aria-label="Descargar reporte"] [data-testid="stIconMaterial"],
button[aria-label="Descargar reporte"] span {
    font-size: 18px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
button[aria-label="Descargar reporte"] *,
[data-testid="stBaseButton-secondary"][aria-label="Descargar reporte"] * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}

/* Download buttons inside modal dialog */
[data-testid="stDownloadButton"] {
    width: 100% !important;
}
[data-testid="stDownloadButton"] button {
    background-color: #02569e !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    font-size: 14px !important;
    font-weight: 700 !important;
    height: 40px !important;
    min-height: 40px !important;
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 8px !important;
    box-shadow: 0 2px 6px rgba(2, 86, 158, 0.3) !important;
    white-space: nowrap !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] button:hover {
    background-color: #0369a1 !important;
    border-color: rgba(255, 255, 255, 0.3) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 10px rgba(2, 86, 158, 0.4) !important;
}
[data-testid="stDownloadButton"] button * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}

[data-testid="stPopoverButton"] * {
    color: #FFFFFF !important;
    fill: #FFFFFF !important;
    stroke: #FFFFFF !important;
}

[data-testid="stDialog"] [data-testid="stModal"] {
    background-color: var(--secondary-background-color, #1e293b) !important;
    color: var(--text-color, #ffffff) !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 14px !important;
    padding: 24px !important;
}
[data-testid="stPopoverBody"] {
    background-color: var(--secondary-background-color, #1e293b) !important;
    color: var(--text-color, #ffffff) !important;
    border: 1px solid rgba(128, 128, 128, 0.2) !important;
    border-radius: 12px !important;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25) !important;
}
[data-testid="stPopoverBody"] > div {
    background-color: transparent !important;
}
[data-testid="stPopoverBody"] label,
[data-testid="stPopoverBody"] label p,
[data-testid="stPopoverBody"] label span,
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] span {
    color: var(--text-color, inherit) !important;
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
    [data-baseweb="popover"],
    [data-testid="stPopoverBody"] {
        background-color: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid rgba(15,23,42,0.12) !important;
    }
    [data-testid="stPopoverBody"] label,
    [data-testid="stPopoverBody"] label p,
    [data-testid="stPopoverBody"] label span,
    [data-testid="stPopoverBody"] p,
    [data-testid="stPopoverBody"] span {
        color: #0F172A !important;
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

    // Sync onboarding state from localStorage to cookie
    try {
        const ls = parentWin.localStorage || window.localStorage;
        const lsSeen = ls && ls.getItem("inhaus_onboarding_seen");
        if (lsSeen === "true" && !parentDoc.cookie.includes("inhaus_onboarding_seen=true")) {
            parentDoc.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
        }
    } catch (_) {}

    const version = "polygon-gradient-v8";
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
        const portal = event.target.closest('[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="select"], [role="listbox"], [role="dialog"], [data-testid="stModal"]');
        if (!sidebar && !sidebarControl && !portal) collapseSidebar();
    });
})();
</script>
""", unsafe_allow_javascript=True)

inject_gtag_script()
theme_icon = "☾" if theme_mode == "Oscuro" else "☀"
dashboard_user = require_dashboard_login(theme_icon, toggle_theme)
current_username = dashboard_user.get("username") if dashboard_user else None

def has_seen_onboarding_persisted(user=None):
    if st.session_state.get("has_seen_onboarding", False):
        return True
    try:
        if st.context.cookies.get("inhaus_onboarding_seen") in ("true", "1"):
            st.session_state["has_seen_onboarding"] = True
            return True
    except Exception:
        pass
    if user and user.get("has_seen_onboarding", False):
        st.session_state["has_seen_onboarding"] = True
        return True
    return False


def persist_onboarding_seen_to_client(username=None):
    st.session_state["has_seen_onboarding"] = True
    components.html("""
    <script>
    (() => {
        const setSeen = () => {
            try { localStorage.setItem("inhaus_onboarding_seen", "true"); } catch(e) {}
            try {
                if (window.parent) {
                    window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                }
            } catch(e) {}
            try {
                if (window.top) {
                    window.top.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.top.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                }
            } catch(e) {}
            try { document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax"; } catch(e) {}
        };
        setSeen();
        setTimeout(setSeen, 200);
    })();
    </script>
    """, height=0, width=0)
    st.html("""
    <script>
    (() => {
        try {
            window.localStorage.setItem("inhaus_onboarding_seen", "true");
            document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
        } catch (_) {}
        try {
            if (window.parent && window.parent !== window) {
                window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
            }
        } catch (_) {}
    })();
    </script>
    """, unsafe_allow_javascript=True)
    if username:
        try:
            get_firestore_client().collection(DASHBOARD_USERS_COLLECTION).document(username).update({"has_seen_onboarding": True})
        except Exception:
            pass


@st.dialog("🚀 Guía de Inicio: Dashboard de Pauta", width="medium")
def show_onboarding_dialog():
    components.html("""
    <script>
    (() => {
        const setSeen = () => {
            try { localStorage.setItem("inhaus_onboarding_seen", "true"); } catch(e) {}
            try {
                if (window.parent) {
                    window.parent.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.parent.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                }
            } catch(e) {}
            try {
                if (window.top) {
                    window.top.localStorage.setItem("inhaus_onboarding_seen", "true");
                    window.top.document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax";
                }
            } catch(e) {}
            try { document.cookie = "inhaus_onboarding_seen=true; path=/; max-age=31536000; SameSite=Lax"; } catch(e) {}
        };
        setSeen();
        setTimeout(setSeen, 200);
    })();
    </script>
    """, height=0, width=0)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.25rem;">
        <img src="https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg"
             alt="Inhaus" class="inhaus-login-logo" style="display:block; width:160px; margin:0 auto 0.6rem;">
        <div style="font-size: 0.88rem; opacity: 0.85; font-weight: 500;">
            Desarrollado por <b>Inhaus</b> para el beneficio y gestión estratégica de sus clientes.
        </div>
    </div>

    ### ¡Bienvenido al Dashboard de Marketing! 👋
    
    Esta herramienta te permite consultar y auditar en tiempo real el rendimiento de tus campañas publicitarias y canales orgánicos.
    
    ---
    #### 1️⃣ Selección de Cuentas y Accesos
    * **Selección de Plataforma:** En el menú lateral izquierdo, elige una o más plataformas (**Meta Ads, TikTok Ads, Google Ads**, etc.).
    * **Cuentas Conectadas:** Despliega el menú para elegir la cuenta publicitaria que deseas consultar.
    * 💡 **¿Necesitas acceso a más cuentas?**
      * Los usuarios no pueden agregar cuentas directamente; únicamente pueden seleccionar las cuentas a las que el administrador les ha otorgado acceso previo.
      * Si necesitas acceso a cuentas adicionales, solicítalo a la persona que te dio acceso o envía un correo solicitando la habilitación a **dpineda@inhauscorp.com**.

    ---
    #### 2️⃣ Configurar Métricas y Fechas
    * **Métricas Inteligentes:** El sistema ya selecciona por defecto las métricas oficiales recomendadas (incluyendo reproducciones de video, seguidores ganados y visitas al perfil en TikTok). Puedes añadir más escribiendo en el buscador.
    * **Comparativa Automática:** Al elegir tu rango de fechas, el dashboard calculará automáticamente la variación porcentual frente al mes anterior completo equivalente.
    """, unsafe_allow_html=True)
    if st.button("¡Entendido, comenzar a explorar!", type="primary", width="stretch"):
        persist_onboarding_seen_to_client(current_username)
        st.rerun()

if not has_seen_onboarding_persisted(dashboard_user):
    persist_onboarding_seen_to_client(current_username)
    show_onboarding_dialog()

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
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_date, end_date = date_range[0], date_range[1]
elif isinstance(date_range, (list, tuple)) and len(date_range) == 1:
    start_date = end_date = date_range[0]
else:
    start_date, end_date = default_start, today

# Benchmarking / Competitors Section
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
    log_query_execution(
        current_username,
        platform_key,
        account_id,
        start_date.isoformat(),
        end_date.isoformat(),
        write_to_bq,
    )
    fetch_campaign_data_from_api.clear()
    st.session_state["dashboard_query_cache"] = {}
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
    for m in ["reach", "video_play_actions", "follows", "profile_visits"]:
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

        # Avoid creating duplicate column names when renaming
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
            st.html(
                segmented_pdf_download_html(export_name, chart_bg),
                unsafe_allow_javascript=True,
                width="stretch",
            )
            st.download_button(
                "Descargar CSV",
                data=lambda: csv_export_frame["frame"].to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{export_name}.csv",
                mime="text/csv;charset=utf-8",
                on_click="ignore",
                icon=":material/download:",
                width="stretch",
            )
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
                if ig_comps or fb_comps:
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
        else:
            st.button(
                "",
                icon=":material/download:",
                key="btn_download_modal",
                help="Descargas deshabilitadas: tu usuario no tiene permisos de descarga asignados en Firestore. Contacta a dpineda@inhauscorp.com si requieres este acceso.",
                disabled=True,
            )


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

