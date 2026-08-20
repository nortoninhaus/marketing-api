"""
Unit tests for Meta permissions and multi-platform OAuth scopes & standards.
"""

from unittest.mock import patch
import pytest
from app.config import settings
from app.connectors.linkedin import LinkedInAdsConnector, LinkedInOrganicConnector
from app.connectors.shopify import ShopifyConnector
from app.connectors.meta import MetaAdsConnector, MetaOrganicConnector, GRAPH_API_VERSION
from app.routers.oauth import GOOGLE_SCOPES, ALL_GOOGLE_SCOPES


def test_meta_all_21_permissions_in_config():
    """Verify that all 21 Meta permissions requested are present in default settings."""
    expected_permissions = [
        "email",
        "ads_management",
        "ads_read",
        "business_management",
        "pages_manage_ads",
        "pages_manage_engagement",
        "pages_manage_metadata",
        "pages_read_engagement",
        "pages_read_user_content",
        "pages_show_list",
        "catalog_management",
        "instagram_basic",
        "instagram_branded_content_ads_brand",
        "instagram_content_publish",
        "instagram_manage_comments",
        "instagram_manage_contents",
        "instagram_manage_engagement",
        "instagram_manage_insights",
        "leads_retrieval",
        "read_insights",
        "threads_business_basic",
    ]
    configured_scopes = [s.strip() for s in settings.meta_oauth_scopes.split(",") if s.strip()]
    assert len(configured_scopes) == 21
    for perm in expected_permissions:
        assert perm in configured_scopes, f"Missing permission: {perm}"


def test_google_scopes_include_openid_and_services():
    """Verify Google scopes include openid, email, profile, ads, ga4, and youtube."""
    assert "openid" in ALL_GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/userinfo.email" in ALL_GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/userinfo.profile" in ALL_GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/adwords" in ALL_GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/analytics.readonly" in ALL_GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/youtube.readonly" in ALL_GOOGLE_SCOPES
    assert "https://www.googleapis.com/auth/yt-analytics.readonly" in ALL_GOOGLE_SCOPES


def test_threads_oauth_authorize_url(client):
    """Verify Threads OAuth authorization URL generation and scopes."""
    with patch("app.config.settings.meta_app_id", "test_threads_app_123"):
        response = client.get("/api/v1/oauth/authorize?platform=threads&client_id=test_client")
        assert response.status_code == 200
        data = response.json()
        auth_url = data["authorization_url"]
        assert "threads_basic" in auth_url
        assert "threads_content_publish" in auth_url
        assert "threads_manage_insights" in auth_url
        assert "threads_business_basic" in auth_url


def test_tiktok_organic_oauth_authorize_url(client):
    """Verify TikTok Organic authorization URL contains modern Display/Organic scopes."""
    with patch("app.config.settings.tiktok_client_key", "test_tiktok_key"):
        with patch("app.config.settings.use_tiktok_sandbox", False):
            response = client.get("/api/v1/oauth/authorize?platform=tiktok_organic&client_id=test_client")
            assert response.status_code == 200
            data = response.json()
            auth_url = data["authorization_url"]
            assert "user.info.basic" in auth_url
            assert "user.info.profile" in auth_url
            assert "user.info.stats" in auth_url
            assert "video.list" in auth_url
            assert "video.insights" in auth_url


def test_meta_graph_api_version_is_v25():
    """Verify Graph API version standard is v25.0."""
    assert GRAPH_API_VERSION == "v25.0"
    ads_schema = MetaAdsConnector().get_schema()
    assert ads_schema["metadata"]["api_version"] == "v25.0"
    org_schema = MetaOrganicConnector().get_schema()
    assert org_schema["metadata"]["api_version"] == "v25.0"
