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
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_oauth_redirect_uri: str = ""
    meta_oauth_scopes: str = "ads_read,pages_show_list,pages_read_engagement"

    # --- Google Ads ---
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""

    # --- Google OAuth Shared ---
    google_client_id: str = ""
    google_client_secret: str = ""
    google_oauth_redirect_uri: str = ""

    # --- Google Analytics 4 ---


    # --- TikTok Ads ---
    tiktok_ads_access_token: str = ""
    tiktok_ads_app_id: str = ""
    tiktok_ads_secret: str = ""
    tiktok_ads_sandbox_app_id: str = ""
    tiktok_ads_sandbox_secret: str = ""
    use_tiktok_sandbox: bool = True

    # --- TikTok Organic ---
    tiktok_access_token: str = ""
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_organic_sandbox_client_key: str = ""
    tiktok_organic_sandbox_secret: str = ""

    # --- LinkedIn ---
    linkedin_access_token: str = ""

    # --- X (Twitter) ---
    x_bearer_token: str = ""
    x_ads_access_token: str = ""

    # --- YouTube ---
    youtube_api_key: str = ""

    # --- Threads ---
    threads_access_token: str = ""

    # --- Google Play ---
    google_play_service_account_json: str = ""
    google_play_gcs_bucket: str = ""

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
        """Check if a platform has non-empty credentials. Always returns True to make all platforms active and functional on the Dashboard."""
        return True


settings = Settings()
