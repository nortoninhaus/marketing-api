# ponytail: simple, dynamic marketing dashboard connecting to the API directly with period comparison and custom CSS styling
import streamlit as st
import pandas as pd
import requests
import json
import os
import textwrap
import calendar
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
def fetch_campaign_data_from_api(platform_key, client_id, user_id, account_id, start_date, end_date, metrics, dimensions, opt_filters, write_to_bq, api_key):
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
        res = requests.post(url, headers=headers, json=payload, timeout=45)
        if res.status_code == 200:
            return res.json().get("data", [])
        else:
            st.error(f"Error de API ({res.status_code}): {res.text}")
            return []
    except Exception as e:
        st.error(f"Error de conexión con la API: {e}")
        return []

# Process the API result list into a pandas dataframe
def process_api_response(api_data, platform_key, client_id, user_id):
    flat_rows = []
    for item in api_data:
        metrics = item.get("metrics", {})
        
        spend = extract_metric(metrics, ["spend", "social_spend", "cost"])
        impressions = extract_metric(metrics, ["impressions", "reach"])
        clicks = extract_metric(metrics, ["clicks", "unique_clicks"])
        conversions = extract_metric(metrics, ["conversions", "actions", "purchase", "lead", "add_to_cart"])
        
        sessions = extract_metric(metrics, ["sessions"])
        users = extract_metric(metrics, ["users"])
        pageviews = extract_metric(metrics, ["pageviews"])
        bounce_rate = extract_metric(metrics, ["bounce_rate"])
        
        downloads = extract_metric(metrics, ["downloads"])
        ratings = extract_metric(metrics, ["ratings"])
        
        engagement = extract_metric(metrics, ["engagement"])
        followers = extract_metric(metrics, ["followers"])
        reach = extract_metric(metrics, ["reach", "impressions"])
        
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
            "reach": int(reach)
        }
        # Add dimensions to the row dict dynamically
        for key, val in item.items():
            if key not in ["metrics", "platform", "client_id", "user_id"]:
                row[key] = val
                
        flat_rows.append(row)
        
    df = pd.DataFrame(flat_rows)
    if df.empty:
        return pd.DataFrame(columns=[
            "platform", "client_id", "user_id", "campaign_name", "date", "spend", "impressions", "clicks", "conversions",
            "sessions", "users", "pageviews", "bounce_rate", "downloads", "ratings", "engagement", "followers", "reach"
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

# SIDEBAR FILTERS (Acts as the collapsible Hamburger Menu on the left)
st.sidebar.image("https://assets.cdn.filesafe.space/7w7j6sfnicAwqdXG0sKP/media/69691ca0d848087449f86454.svg", width=120)
st.sidebar.markdown("### Configuración de Consulta")

# API key setup
api_key = st.sidebar.text_input("X-API-Key", value=DEFAULT_API_KEY, type="password")

# Client & User setup
client_id = st.sidebar.text_input("Client ID", value="client_1")
user_id = st.sidebar.text_input("User ID", value="user_1")

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
    "meta_organic": "Meta Organic",
    "tiktok_organic": "TikTok Organic",
    "linkedin_organic": "LinkedIn Organic",
    "x_organic": "X Organic",
    "youtube": "YouTube Analytics",
    "threads": "Threads Organic",
    "pinterest_organic": "Pinterest Organic",
    "ga4": "Google Analytics 4",
    "shopify": "Shopify Store",
    "ghl": "GoHighLevel (GHL)",
    "google_play": "Google Play Store",
    "apple_app_store": "Apple App Store",
}
selected_platform_label = st.sidebar.selectbox("Plataforma", list(platform_labels.values()))
platform_key = [k for k, v in platform_labels.items() if v == selected_platform_label][0]

# Detect platform changes to reset selections
if "prev_platform" not in st.session_state:
    st.session_state.prev_platform = platform_key
    
if st.session_state.prev_platform != platform_key:
    st.session_state.selected_metrics = []
    st.session_state.selected_dimensions = []
    st.session_state.prev_platform = platform_key
    st.rerun()

# Discover accounts
connections = fetch_connections_from_api(platform_key, client_id, api_key)
if connections:
    connection_options = {f"{c['account_name']} ({c['account_id']})": c['account_id'] for c in connections}
    selected_conn_label = st.sidebar.selectbox("Cuentas Conectadas", list(connection_options.keys()))
    default_account_id = connection_options[selected_conn_label]
else:
    default_account_id = "act_1229232368796008" if platform_key == "meta_ads" else "account_1"
    
account_id = st.sidebar.text_input("Account ID / ID de Cuenta", value=default_account_id)

# Load schema (metrics & dimensions)
schema_data = fetch_schema_from_api(platform_key, api_key)
metrics_list = schema_data.get("metrics", [])
dimensions_list = schema_data.get("dimensions", [])

# Ensure session state variables
if "selected_metrics" not in st.session_state or not st.session_state.selected_metrics:
    st.session_state.selected_metrics = [m["name"] for m in metrics_list[:8]] if metrics_list else ["impressions"]
    
if "selected_dimensions" not in st.session_state:
    st.session_state.selected_dimensions = []

# METRICS MULTISELECT
selected_metrics = st.sidebar.multiselect(
    "Métricas *", 
    options=[m["name"] for m in metrics_list], 
    default=st.session_state.selected_metrics,
    key="metrics_selector"
)

# DIMENSIONS MULTISELECT
selected_dimensions = st.sidebar.multiselect(
    "Dimensiones (Opcional)",
    options=[d["name"] for d in dimensions_list],
    default=st.session_state.selected_dimensions,
    key="dimensions_selector"
)

# Dynamic Context Filters
opt_filters = {}
platform_type = PLATFORM_TYPES.get(platform_key, "ads")

if platform_type == "organic":
    post_id = st.sidebar.text_input("Post ID", value="", placeholder="ID de publicación (opcional)")
    video_id = st.sidebar.text_input("Video ID", value="", placeholder="ID de video (opcional)")
    if post_id:
        opt_filters["post_id"] = post_id
    if video_id:
        opt_filters["video_id"] = video_id
elif platform_type == "app_store":
    app_id = st.sidebar.text_input("App ID", value="", placeholder="ID de app / paquete (opcional)")
    if app_id:
        opt_filters["app_id"] = app_id
        
# Write to BQ checkbox
write_to_bq = st.sidebar.checkbox("Escribir resultados a BigQuery (write_to_bq)", value=False)

# Date Pickers
today = date.today()
default_start = today - timedelta(days=30)
date_range = st.sidebar.date_input("Rango de Fechas a Consultar", [default_start, today])

st.sidebar.markdown("---")
# Execute Button in Sidebar to prevent auto-loading until clicked
execute_query = st.sidebar.button("🚀 Consultar API de Producción", use_container_width=True)

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
    st.rerun()

if not st.session_state.get("query_run", False):
    st.info("Configura tus parámetros de consulta en el menú hamburguesa lateral izquierdo y presiona el botón 'Consultar API de Producción' para cargar la visualización en pantalla completa.")
else:
    # Render the fullscreen loading overlay first to block the screen
    loading_placeholder = st.empty()
    loading_placeholder.markdown("""
        <div class="loading-overlay">
        <div class="spinner"></div>
        <div class="loading-text">1/3: Conectando con la API de Inhaus y solicitando periodo actual...</div>
        </div>
        """, unsafe_allow_html=True)

    # Resolve dates
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range[0], date_range[1]
    else:
        start_date, end_date = default_start, today
        
    # Calculate comparison month (previous calendar month)
    prev_start_date, prev_end_date = get_prior_month_range(start_date)
    
    # Ensure that standard KPI metrics are requested in payload even if unchecked
    request_metrics = list(selected_metrics)
    if platform_type == "ads":
        for m in ["impressions", "clicks", "spend", "conversions", "reach"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
    elif platform_type == "analytics":
        for m in ["sessions", "users", "pageviews", "bounce_rate"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
    elif platform_type == "app_store":
        for m in ["downloads", "ratings"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
    else:
        for m in ["impressions", "engagement", "followers", "reach"]:
            if m not in request_metrics and m in [x["name"] for x in metrics_list]:
                request_metrics.append(m)
                
    # Call API for current data
    curr_data = fetch_campaign_data_from_api(
        platform_key, client_id, user_id, account_id, 
        start_date, end_date, request_metrics, selected_dimensions, 
        opt_filters, write_to_bq, api_key
    )
    
    # Update loader text for second request
    loading_placeholder.markdown("""
        <div class="loading-overlay">
            <div class="spinner"></div>
            <div class="loading-text">2/3: Procesando periodo actual y solicitando comparativa del mes anterior...</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Call API for previous period comparisons
    prev_data = fetch_campaign_data_from_api(
        platform_key, client_id, user_id, account_id, 
        prev_start_date, prev_end_date, request_metrics, selected_dimensions, 
        opt_filters, False, api_key
    )
    
    # Update loader text for rendering calculations
    loading_placeholder.markdown("""
        <div class="loading-overlay">
            <div class="spinner"></div>
            <div class="loading-text">3/3: Calculando métricas y estructurando tendencias PoP...</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Remove the loading overlay
    loading_placeholder.empty()
    
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
    
    if not curr_data:
        st.error("No se recibió información de la API para el periodo actual. Verifica las credenciales, plataforma o ID de cuenta en el menú lateral.")
    else:
        df_curr = process_api_response(curr_data, platform_key, client_id, user_id)
        df_prev = process_api_response(prev_data, platform_key, client_id, user_id) if prev_data else pd.DataFrame()
        
        # Resolve account label
        account_disp = account_id
        if connections:
            matched_name = [c["account_name"] for c in connections if c["account_id"] == account_id]
            if matched_name:
                account_disp = f"{matched_name[0]} ({account_id})"
                
        # HERO RENDER (Clean, full width, no Sipy logo)
        st.markdown(f"""
        <h1 style="margin-top: 10px; font-size: 2rem; line-height: 1.1; color: #EAF0F7;">{selected_platform_label} &middot; {account_disp}</h1>
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
            primary_label = "Engagement Total"
            
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
        st.markdown("### Métricas Clave (KPIs) con Comparación")
        
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
            kpis_layout += get_kpi_card_html("Interacciones (Engagement)", f"{total_engagement_curr:,}", "Likes, shares, comentarios", total_engagement_curr, total_engagement_prev) + "\n"
            kpis_layout += get_kpi_card_html("Seguidores Totales", f"{total_followers_curr:,}", "Comunidad", total_followers_curr, total_followers_prev) + "\n"
            kpis_layout += get_kpi_card_html("Alcance Orgánico", f"{total_reach_curr:,}", "Usuarios únicos alcanzados", total_reach_curr, total_reach_prev) + "\n"
            kpis_layout += '</div>'

        st.markdown(kpis_layout, unsafe_allow_html=True)
        
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
                    st.markdown("#### Inversión vs. Conversiones Diarias (Eje Dual)")
                    left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                        y=alt.Y('spend:Q', title='Inversión ($)', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
                    )
                    right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
                        y=alt.Y('conversions:Q', title='Conversiones', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
                    )
                    dual_chart = alt.layer(left_line, right_line).resolve_scale(
                        y='independent'
                    ).properties(height=350).configure_view(strokeOpacity=0).configure_axis(gridColor='rgba(255,255,255,0.05)')
                    st.altair_chart(dual_chart, use_container_width=True)
                    
                elif platform_type == "analytics":
                    st.markdown("#### Sesiones vs. Páginas Vistas (Eje Dual)")
                    left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                        y=alt.Y('sessions:Q', title='Sesiones', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
                    )
                    right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
                        y=alt.Y('pageviews:Q', title='Páginas Vistas', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
                    )
                    dual_chart = alt.layer(left_line, right_line).resolve_scale(
                        y='independent'
                    ).properties(height=350).configure_view(strokeOpacity=0).configure_axis(gridColor='rgba(255,255,255,0.05)')
                    st.altair_chart(dual_chart, use_container_width=True)
                    
                elif platform_type == "app_store":
                    st.markdown("#### Descargas Diarias")
                    line_chart = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                        y=alt.Y('downloads:Q', title='Descargas')
                    ).properties(height=350).configure_view(strokeOpacity=0).configure_axis(gridColor='rgba(255,255,255,0.05)')
                    st.altair_chart(line_chart, use_container_width=True)
                    
                else: # organic
                    st.markdown("#### Impresiones vs. Engagement (Eje Dual)")
                    left_line = base.mark_line(color='#1AE08C', strokeWidth=3).encode(
                        y=alt.Y('impressions:Q', title='Impresiones', axis=alt.Axis(titleColor='#1AE08C', labelColor='#1AE08C'))
                    )
                    right_line = base.mark_line(color='#5C9DFF', strokeWidth=3).encode(
                        y=alt.Y('engagement:Q', title='Interacciones', axis=alt.Axis(titleColor='#5C9DFF', labelColor='#5C9DFF'))
                    )
                    dual_chart = alt.layer(left_line, right_line).resolve_scale(
                        y='independent'
                    ).properties(height=350).configure_view(strokeOpacity=0).configure_axis(gridColor='rgba(255,255,255,0.05)')
                    st.altair_chart(dual_chart, use_container_width=True)
                    
        with col_chart_right:
            # Render Campaign Distribution as a Horizontal Bar Chart so long labels are readable
            if platform_type == "ads":
                st.markdown("#### Distribución de Conversiones por Campaña")
                df_camp = df_curr.groupby("campaign_name")["conversions"].sum().reset_index()
                df_camp = df_camp.sort_values("conversions", ascending=False).head(10)
                
                chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                    x=alt.X('conversions:Q', title='Conversiones'),
                    y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
                ).properties(height=350)
                st.altair_chart(chart_camp, use_container_width=True)
                
            elif platform_type == "analytics":
                st.markdown("#### Sesiones por Campaña/Fuente")
                df_camp = df_curr.groupby("campaign_name")["sessions"].sum().reset_index()
                df_camp = df_camp.sort_values("sessions", ascending=False).head(10)
                
                chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                    x=alt.X('sessions:Q', title='Sesiones'),
                    y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
                ).properties(height=350)
                st.altair_chart(chart_camp, use_container_width=True)
                
            else: # organic / app_store
                st.markdown("#### Alcance / Distribución por Publicación")
                target_metric = "reach" if platform_type != "app_store" else "downloads"
                df_camp = df_curr.groupby("campaign_name")[target_metric].sum().reset_index()
                df_camp = df_camp.sort_values(target_metric, ascending=False).head(10)
                
                chart_camp = alt.Chart(df_camp).mark_bar(color='#5C9DFF', cornerRadiusEnd=6).encode(
                    x=alt.X(f"{target_metric}:Q", title='Alcance / Volumen'),
                    y=alt.Y('campaign_name:N', sort='-x', title=None, axis=alt.Axis(labelLimit=300))
                ).properties(height=350)
                st.altair_chart(chart_camp, use_container_width=True)
                
        # CAMPAIGN BREAKDOWN TABLE
        st.markdown("### Detalle de Campañas y Resultados")
        
        search_query = st.text_input("🔍 Buscar campaña por nombre:", "")
        df_table = df_curr.copy()
        if search_query:
            df_table = df_table[df_table["campaign_name"].str.contains(search_query, case=False, na=False)]
            
        group_keys = ["campaign_name", "platform"]
        for dim in selected_dimensions:
            if dim in df_table.columns and dim not in group_keys:
                group_keys.append(dim)
                
        if platform_type == "ads":
            df_table = df_table.groupby(group_keys).agg({
                "spend": "sum", "impressions": "sum", "clicks": "sum", "conversions": "sum"
            }).reset_index()
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
            
        st.dataframe(df_table, width="stretch", hide_index=True)
