"""
Unit tests for TikTok Ads and TikTok Organic OAuth authorization and callbacks.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)

def test_tiktok_ads_authorize():
    # Alphanumeric sandbox App ID should return 400 Bad Request
    settings.use_tiktok_sandbox = True
    settings.tiktok_ads_sandbox_app_id = "sbawioy0q8vqdzm3sl"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_ads")
    assert response.status_code == 400
    assert "strictly requires a numeric App ID" in response.json()["detail"]

    # Numeric sandbox App ID should succeed
    settings.tiktok_ads_sandbox_app_id = "123456789"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_ads")
    assert response.status_code == 200
    data = response.json()
    assert "url" in data
    assert "123456789" in data["url"]
    assert "business-api.tiktok.com/portal/auth" in data["url"]

    # Production mode (numeric App ID)
    settings.use_tiktok_sandbox = False
    # Set a dummy production App ID if none configured to avoid empty string matching everything
    old_app_id = settings.tiktok_ads_app_id
    settings.tiktok_ads_app_id = "7650392266468507649"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_ads")
    assert response.status_code == 200
    data = response.json()
    assert "7650392266468507649" in data["url"]
    settings.tiktok_ads_app_id = old_app_id

def test_tiktok_organic_authorize():
    # Sandbox mode
    settings.use_tiktok_sandbox = True
    settings.tiktok_organic_sandbox_client_key = "123456789"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_organic")
    assert response.status_code == 200
    data = response.json()
    assert "open-sandbox.tiktokapis.com/v2/auth/authorize" in data["url"]
    assert "client_key=123456789" in data["url"]

    # Production mode
    settings.use_tiktok_sandbox = False
    settings.tiktok_client_key = "7650392266468507649"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_organic")
    assert response.status_code == 200
    data = response.json()
    assert "www.tiktok.com/v2/auth/authorize" in data["url"]
    assert "client_key=7650392266468507649" in data["url"]

@pytest.mark.asyncio
@patch("app.routers.oauth.credential_store.save_oauth_connection", new_callable=AsyncMock)
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
async def test_tiktok_ads_callback(mock_get, mock_post, mock_save):
    # Mock Token exchange
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "code": 0,
        "message": "OK",
        "data": {
            "access_token": "mock_ads_token",
            "advertiser_ids": ["123456789"]
        }
    }
    mock_post.return_value = mock_post_resp

    # Mock Advertiser Info / Business Center endpoints
    def get_side_effect(url, *args, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "advertiser/info" in url:
            resp.json.return_value = {
                "code": 0,
                "message": "OK",
                "data": {
                    "list": [
                        {
                            "advertiser_id": "123456789",
                            "advertiser_name": "Test Advertiser"
                        }
                    ]
                }
            }
        elif "bc/get" in url:
            resp.json.return_value = {
                "code": 0,
                "message": "OK",
                "data": {
                    "list": [
                        {
                            "bc_id": "bc_123",
                            "bc_name": "Test BC"
                        }
                    ]
                }
            }
        elif "bc/asset/get" in url:
            resp.json.return_value = {
                "code": 0,
                "message": "OK",
                "data": {
                    "list": [
                        {
                            "asset_id": "organic_user_id",
                            "asset_name": "Organic Account Name",
                            "permission": "ADMIN"
                        }
                    ]
                }
            }
        else:
            resp.json.return_value = {"code": 0, "data": {}}
        return resp

    mock_get.side_effect = get_side_effect

    import base64
    import json
    state_data = {
        "client_id": "test_client",
        "platform": "tiktok_ads",
        "redirect_url": "http://localhost:3000"
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    response = client.get(f"/api/v1/oauth/callback?code=mock_code&state={state}", follow_redirects=False)
    assert response.status_code == 307
    assert "oauth=success" in response.headers["location"]
    
    assert mock_save.call_count == 2
    
    # Verify Ad connection saved
    mock_save.assert_any_call(
        client_id="test_client",
        platform="tiktok_ads",
        account_id="123456789",
        account_name="Test Advertiser",
        access_token="mock_ads_token"
    )
    
    # Verify Brand Profile connection saved
    mock_save.assert_any_call(
        client_id="test_client",
        platform="tiktok_organic",
        account_id="organic_user_id",
        account_name="Organic Account Name",
        access_token="mock_ads_token",
        extra_data={
            "bc_id": "bc_123",
            "is_bc_asset": True,
            "permission": "ADMIN"
        }
    )

@pytest.mark.asyncio
@patch("app.routers.oauth.credential_store.save_oauth_connection", new_callable=AsyncMock)
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
async def test_tiktok_organic_callback(mock_get, mock_post, mock_save):
    # Mock Token exchange for Consumer API authentication
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "access_token": "mock_organic_token",
        "open_id": "mock_open_id",
        "refresh_token": "mock_refresh_token",
        "expires_in": 86400
    }
    mock_post.return_value = mock_post_resp

    # Mock User Info endpoint
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "data": {
            "user": {
                "display_name": "TikTok User Name",
                "username": "tiktokusername"
            }
        }
    }
    mock_get.return_value = mock_get_resp

    import base64
    import json
    state_data = {
        "client_id": "test_client",
        "platform": "tiktok_organic",
        "redirect_url": "http://localhost:3000"
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    response = client.get(f"/api/v1/oauth/callback?code=mock_code&state={state}", follow_redirects=False)
    assert response.status_code == 307
    assert "oauth=success" in response.headers["location"]
    
    mock_save.assert_called_once()
    call_kwargs = mock_save.call_args[1]
    assert call_kwargs["client_id"] == "test_client"
    assert call_kwargs["platform"] == "tiktok_organic"
    assert call_kwargs["account_id"] == "mock_open_id"
    assert call_kwargs["account_name"] == "TikTok User Name"
    assert call_kwargs["access_token"] == "mock_organic_token"
    assert call_kwargs["refresh_token"] == "mock_refresh_token"
    assert "token_expires_at" in call_kwargs
