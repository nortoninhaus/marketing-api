import streamlit as st

BASE_CSS = """<style>
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
"""

LIGHT_THEME_CSS = """    <style>
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
"""

VIEW_TRANSITIONS_JS = """<script>
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

    const version = "polygon-gradient-v9";
    if (parentDoc.__inhausSidebarEnhancer === version) return;
    parentDoc.__inhausSidebarEnhancer = version;

    // Reset Streamlit's internal collapsed state so it defaults to open
    try {
        const ls = parentWin.localStorage || window.localStorage;
        if (ls) {
            for (let i = 0; i < ls.length; i++) {
                const k = ls.key(i);
                if (k && k.startsWith("stSidebarCollapsed")) {
                    ls.setItem(k, "false");
                }
            }
        }
    } catch (_) {}

    if (!parentWin.__inhausNavListener) {
        parentWin.__inhausNavListener = (event) => {
            if (event.source !== parentWin && event.data && event.data.type === "inhaus-navigate" && event.data.url) {
                parentWin.location.href = event.data.url;
            }
        };
        parentWin.addEventListener("message", parentWin.__inhausNavListener);
    }

    const expandSidebar = () => {
        try {
            const openBtn = parentDoc.querySelector(
                'button[data-testid="stSidebarCollapseButton"], button[aria-label="Open sidebar"], button[title="Open sidebar"], [data-testid="stSidebarCollapsedControl"] button, [data-testid="collapsedControl"] button'
            );
            if (openBtn) {
                const label = (openBtn.getAttribute("aria-label") || openBtn.getAttribute("title") || "").toLowerCase();
                if (!label.includes("close") && !label.includes("cerrar")) {
                    openBtn.click();
                }
            }
            const ls = parentWin.localStorage || window.localStorage;
            if (ls) {
                for (let i = 0; i < ls.length; i++) {
                    const k = ls.key(i);
                    if (k && k.startsWith("stSidebarCollapsed")) {
                        ls.setItem(k, "false");
                    }
                }
            }
        } catch (_) {}
    };
    parentWin.__inhausExpandSidebar = expandSidebar;

    // Automatically ensure sidebar is open on startup and after dialogs
    setTimeout(expandSidebar, 150);
    setTimeout(expandSidebar, 600);
    setTimeout(expandSidebar, 1200);

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
        if (parentWin.innerWidth > 768) return; // Keep sidebar open on desktop screens
        const sidebar = event.target.closest('[data-testid="stSidebar"]');
        const sidebarControl = event.target.closest('[data-testid="stSidebarCollapseButton"], button[aria-label="Open sidebar"], button[aria-label="Close sidebar"]');
        const portal = event.target.closest('[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="select"], [role="listbox"], [role="dialog"], [data-testid="stModal"]');
        if (!sidebar && !sidebarControl && !portal) collapseSidebar();
    });
})();
</script>
"""

def inject_dashboard_styles(theme_mode: str) -> None:
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    if theme_mode == "Claro":
        st.markdown(LIGHT_THEME_CSS, unsafe_allow_html=True)
    st.html(VIEW_TRANSITIONS_JS)
