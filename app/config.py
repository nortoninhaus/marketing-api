"""
Inhaus Marketing Data API — Validated Configuration.

All environment variables are validated at startup via Pydantic Settings.
Missing required values cause an immediate, clear failure rather than
a runtime NameError deep inside a connector.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — loaded from .env and validated at startup."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore env vars not defined here
    )

    # --- API Authentication ---
    api_key: str = "dev-key-change-me"

    # --- Meta (Facebook / Instagram) ---
    meta_access_token: str = ""

    # --- Google Ads ---
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""

    # --- Google Analytics 4 ---


    # --- TikTok Ads ---
    tiktok_ads_access_token: str = ""
    tiktok_ads_app_id: str = ""
    tiktok_ads_secret: str = ""

    # --- TikTok Organic ---
    tiktok_access_token: str = ""

    # --- LinkedIn ---
    linkedin_access_token: str = ""

    # --- X (Twitter) ---
    x_bearer_token: str = ""
    x_ads_access_token: str = ""

    # --- YouTube ---
    youtube_api_key: str = ""

    # --- Google Play ---
    google_play_service_account_json: str = ""

    # --- Apple App Store Connect ---
    apple_key_id: str = ""
    apple_issuer_id: str = ""
    apple_private_key_path: str = ""  # Path to .p8 file (not inline PEM)

    # --- Apple Search Ads ---
    apple_ads_access_token: str = ""

    # --- BigQuery Sink ---
    bigquery_project_id: str = ""
    bigquery_dataset_id: str = "marketing_data"
    bigquery_table_id: str = "raw_campaign_data"
    enable_bigquery_sink: bool = False

    def is_platform_configured(self, platform: str) -> bool:
        """Check if a platform has non-empty credentials."""
        platform_fields = {
            "meta_ads": ["meta_access_token"],
            "meta_organic": ["meta_access_token"],
            "google_ads": ["google_ads_developer_token"],
            "ga4": [], # GA4 only needs property ID which is now dynamic
            "tiktok_ads": ["tiktok_ads_access_token", "tiktok_ads_app_id", "tiktok_ads_secret"],
            "tiktok_organic": ["tiktok_access_token"],
            "linkedin_ads": ["linkedin_access_token"],
            "linkedin_organic": ["linkedin_access_token"],
            "x_ads": ["x_ads_access_token"],
            "x_organic": ["x_bearer_token"],
            "youtube": ["youtube_api_key"],
            "google_play": ["google_play_service_account_json"],
            "apple_app_store": ["apple_key_id", "apple_issuer_id"],
            "apple_ads": ["apple_ads_access_token"],
        }
        fields = platform_fields.get(platform, [])
        return all(getattr(self, f, "") for f in fields)


settings = Settings()
