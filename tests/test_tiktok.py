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
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_ads")
    assert response.status_code == 200
    data = response.json()
    assert "7621197369555666962" in data["url"]

def test_tiktok_organic_authorize():
    # Sandbox mode
    settings.use_tiktok_sandbox = True
    settings.tiktok_ads_sandbox_app_id = "sbawioy0q8vqdzm3sl"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_organic")
    assert response.status_code == 200
    data = response.json()
    assert "open-sandbox.tiktokapis.com" in data["url"]
    assert "client_key=sbawioy0q8vqdzm3sl" in data["url"]

    # Production mode
    settings.use_tiktok_sandbox = False
    settings.tiktok_client_key = "awvc6io3a6k3z9xi"
    response = client.get("/api/v1/oauth/authorize?platform=tiktok_organic")
    assert response.status_code == 200
    data = response.json()
    assert "www.tiktok.com" in data["url"]
    assert "client_key=awvc6io3a6k3z9xi" in data["url"]

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

    # Mock Advertiser Info
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
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
    mock_get.return_value = mock_get_resp

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
    
    mock_save.assert_called_once()
    args, kwargs = mock_save.call_args
    assert kwargs["client_id"] == "test_client"
    assert kwargs["platform"] == "tiktok_ads"
    assert kwargs["account_id"] == "123456789"
    assert kwargs["account_name"] == "Test Advertiser"
    assert kwargs["access_token"] == "mock_ads_token"

@pytest.mark.asyncio
@patch("app.routers.oauth.credential_store.save_oauth_connection", new_callable=AsyncMock)
@patch("httpx.AsyncClient.post")
@patch("httpx.AsyncClient.get")
async def test_tiktok_organic_callback(mock_get, mock_post, mock_save):
    # Mock Token exchange
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {
        "access_token": "mock_organic_token",
        "open_id": "mock_open_id",
        "refresh_token": "mock_refresh_token",
        "expires_in": 86400
    }
    mock_post.return_value = mock_post_resp

    # Mock User Info
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {
        "data": {
            "user": {
                "username": "tiktok_user",
                "display_name": "TikTok User Name"
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
    args, kwargs = mock_save.call_args
    assert kwargs["client_id"] == "test_client"
    assert kwargs["platform"] == "tiktok_organic"
    assert kwargs["account_id"] == "mock_open_id"
    assert kwargs["account_name"] == "TikTok User Name"
    assert kwargs["access_token"] == "mock_organic_token"
