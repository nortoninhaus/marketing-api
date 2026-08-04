import os
import hashlib
from dotenv import load_dotenv

# Load env variables for local defaults
load_dotenv()

DEFAULT_API_KEY = os.getenv("API_KEY", "dev-key-change-me")
DEFAULT_API_URL = os.getenv("API_URL", "https://inhaus-marketing-api-btdf7nijqa-uc.a.run.app")
CAMPAIGN_DATA_TIMEOUT = int(os.getenv("CAMPAIGN_DATA_TIMEOUT", "120"))
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "inhaus-marketing-api")
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")
FIREBASE_APP_ID = os.getenv("FIREBASE_APP_ID")
FIREBASE_AUTH_DOMAIN = os.getenv("FIREBASE_AUTH_DOMAIN")
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "G-KEYBRJQSWF")
GA_API_SECRET = os.getenv("GA_API_SECRET")
DASHBOARD_USERS_COLLECTION = os.getenv("DASHBOARD_USERS_COLLECTION", "dashboard_users")
DASHBOARD_JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET") or hashlib.sha256(DEFAULT_API_KEY.encode("utf-8")).hexdigest()
DASHBOARD_JWT_HOURS = int(os.getenv("DASHBOARD_JWT_HOURS", "12"))
DASHBOARD_AUTH_COOKIE = "dashboard_auth_token"
DASHBOARD_AUTH_QUERY_PARAM = "dashboard_auth_token"
PASSWORD_ALGORITHM = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 260000

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

META_PUBLISHER_LABELS = {
    "facebook": "Facebook Ads",
    "instagram": "Instagram Ads",
    "audience_network": "Audience Network",
    "messenger": "Messenger Ads",
}

META_RESULT_LABELS = {
    "reach": "Alcance",
    "actions:lead": "Clientes potenciales",
    "actions:onsite_conversion.lead_grouped": "Clientes potenciales",
    "actions:offsite_conversion.fb_pixel_lead": "Clientes potenciales",
    "actions:post_engagement": "Interacciones con la publicación",
    "actions:landing_page_view": "Visitas a la página de destino",
    "actions:link_click": "Clics en el enlace",
    "actions:purchase": "Compras",
    "actions:offsite_conversion.fb_pixel_purchase": "Compras",
    "actions:app_install": "Instalaciones de la app",
    "actions:video_view": "Reproducciones de video de 3 segundos",
    "actions:onsite_conversion.messaging_conversation_started_7d": "Conversaciones con mensajes iniciadas",
    "actions:messaging_conversation_started_7d": "Conversaciones con mensajes iniciadas",
}

DIMENSION_VALUE_LABELS = {
    "gender": {
        "male": "Masculino",
        "female": "Femenino",
        "unknown": "Desconocido",
        "unmapped": "Desconocido",
        "not_specified": "No especificado",
    }
}
