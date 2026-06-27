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
        if "oauth2/advertiser/get" in url or "advertiser/info" in url:
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

    from app.routers.oauth import _sign_state
    state_data = {
        "client_id": "test_client",
        "platform": "tiktok_ads",
        "redirect_url": "http://localhost:3000"
    }
    state = _sign_state(state_data)

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

    from app.routers.oauth import _sign_state
    state_data = {
        "client_id": "test_client",
        "platform": "tiktok_organic",
        "redirect_url": "http://localhost:3000"
    }
    state = _sign_state(state_data)

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

def test_tiktok_organic_connector_fetch_data():
    from app.connectors.tiktok import TikTokOrganicConnector
    from app.models.requests import DataRequest
    from datetime import datetime

    connector = TikTokOrganicConnector()

    # Test Personal Organic Profile Stats
    req_profile = DataRequest(
        platform="tiktok_organic",
        client_id="client_1",
        user_id="user_1",
        account_id="mock_open_id",
        start_date=datetime(2026, 6, 1),
        end_date=datetime(2026, 6, 7),
        metrics=["follower_count", "profile_views"]
    )
    
    # Mock credentials store for personal account
    with patch.object(connector, "get_credentials", return_value={
        "access_token": "mock_token",
        "open_id": "mock_open_id",
        "is_bc_asset": False
    }):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": {
                    "user": {
                        "display_name": "Personal User",
                        "follower_count": 999
                    }
                }
            }
            mock_get.return_value = mock_resp
            
            res = connector.fetch_data(req_profile)
            assert len(res) == 1
            assert res[0].metrics["follower_count"] == 999
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "v2/user/info/" in args[0]
            assert "follower_count" in kwargs["params"]["fields"]

    # Test Business Center Brand Profile Stats (Mocked Fallback)
    with patch.object(connector, "get_credentials", return_value={
        "access_token": "mock_token",
        "open_id": "brand_asset_id",
        "is_bc_asset": True,
        "account_name": "My Brand Profile"
    }):
        with patch("requests.get") as mock_get_bc:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.headers = {"x-rate-limit-remaining": "100"}
            mock_resp.json.return_value = {
                "code": 0,
                "data": {
                    "follower_count": 10500,
                    "profile_views": 4200
                }
            }
            mock_get_bc.return_value = mock_resp

            res = connector.fetch_data(req_profile)
            assert len(res) == 1
            assert res[0].metrics["follower_count"] == 10500
            assert res[0].campaign_name == "My Brand Profile"
            mock_get_bc.assert_called_once()


    # Test Business Center Organic Video Stats with dynamic mapping
    req_videos = DataRequest(
        platform="tiktok_organic",
        client_id="client_1",
        user_id="user_1",
        account_id="brand_asset_id",
        start_date=datetime(2026, 6, 1),
        end_date=datetime(2026, 6, 7),
        metrics=["view_count", "like_count"]
    )
    with patch.object(connector, "get_credentials", return_value={
        "access_token": "mock_token",
        "open_id": "brand_asset_id",
        "is_bc_asset": True
    }):
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "data": {
                    "list": [
                        {
                            "item_id": "vid_1",
                            "title": "Video 1 Title",
                            "create_time": 1780332800,
                            "video_views": 100,
                            "likes": 50
                        }
                    ]
                }
            }
            mock_get.return_value = mock_resp
            
            res = connector.fetch_data(req_videos)
            assert len(res) == 1
            assert res[0].metrics["view_count"] == 100
            assert res[0].metrics["like_count"] == 50
            mock_get.assert_called_once()
            args, kwargs = mock_get.call_args
            assert "business/video/list/" in args[0]
            import json
            fields_param = json.loads(kwargs["params"]["fields"])
            assert "video_views" in fields_param
            assert "likes" in fields_param
            assert "comments" not in fields_param

def test_tiktok_ads_connector_fetch_data():
    from app.connectors.tiktok import TikTokAdsConnector
    from app.models.requests import DataRequest
    from datetime import datetime

    connector = TikTokAdsConnector()
    req = DataRequest(
        platform="tiktok_ads",
        client_id="client_1",
        user_id="user_1",
        account_id="123456789",
        start_date=datetime(2026, 6, 1),
        end_date=datetime(2026, 6, 7),
        metrics=["spend", "impressions"]
    )

    # Scenario 1: AUCTION_CAMPAIGN succeeds, RESERVATION_CAMPAIGN returns 40002 Unsupported data_level
    with patch.object(connector, "get_credentials", return_value={
        "access_token": "mock_token",
        "advertiser_id": "123456789"
    }):
        with patch("requests.get") as mock_get:
            def get_side_effect(url, params, headers, timeout):
                resp = MagicMock()
                resp.status_code = 200
                if params["data_level"] == "AUCTION_CAMPAIGN":
                    resp.json.return_value = {
                        "code": 0,
                        "data": {
                            "list": [
                                {
                                    "dimensions": {"campaign_id": "camp_1", "stat_time_day": "2026-06-02"},
                                    "metrics": {"campaign_name": "Camp 1", "spend": 10.5, "impressions": 100}
                                }
                            ]
                        }
                    }
                else:
                    resp.json.return_value = {
                        "code": 40002,
                        "message": "Unsupported data_level for auction report: RESERVATION_CAMPAIGN."
                    }
                return resp
            
            mock_get.side_effect = get_side_effect
            res = connector.fetch_data(req)
            assert len(res) == 1
            assert res[0].campaign_name == "Camp 1"
            assert res[0].metrics["spend"] == 10.5
            assert mock_get.call_count == 2

    # Scenario 2: Both levels fail, raises ValueError
    with patch.object(connector, "get_credentials", return_value={
        "access_token": "mock_token",
        "advertiser_id": "123456789"
    }):
        with patch("requests.get") as mock_get:
            def get_side_effect(url, params, headers, timeout):
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = {
                    "code": 40002,
                    "message": "Invalid metric fields"
                }
                return resp
            
            mock_get.side_effect = get_side_effect
            with pytest.raises(ValueError) as exc:
                connector.fetch_data(req)
            assert "Invalid metric fields" in str(exc.value)


@pytest.mark.asyncio
@patch("app.main.credential_store.resolve_credentials", new_callable=AsyncMock)
@patch("requests.get")
@patch("requests.post")
async def test_tiktok_proxy_endpoint(mock_post, mock_get, mock_resolve_creds):
    headers = {"X-API-Key": settings.api_key}

    # Scenario 1: Credentials not found (401)
    mock_resolve_creds.return_value = None
    response = client.post(
        "/api/v1/tiktok-proxy",
        json={
            "client_id": "client_1",
            "account_id": "123",
            "path": "campaign/get/",
            "method": "GET"
        },
        headers=headers
    )
    assert response.status_code == 401
    assert "Credentials not found" in response.json()["detail"]

    # Scenario 2: Successful GET request
    mock_resolve_creds.return_value = {"access_token": "mock_token"}
    
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"code": 0, "message": "OK", "data": {"list": []}}
    mock_get.return_value = mock_get_resp

    response = client.post(
        "/api/v1/tiktok-proxy",
        json={
            "client_id": "client_1",
            "account_id": "123",
            "path": "campaign/get/",
            "method": "GET",
            "params": {"page_size": 10}
        },
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["code"] == 0
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://business-api.tiktok.com/open_api/v1.3/campaign/get/" in args[0]
    assert kwargs["params"] == {"page_size": 10}
    assert kwargs["headers"]["Access-Token"] == "mock_token"

    # Scenario 3: Successful POST request
    mock_post_resp = MagicMock()
    mock_post_resp.status_code = 200
    mock_post_resp.json.return_value = {"code": 0, "message": "Created"}
    mock_post.return_value = mock_post_resp

    response = client.post(
        "/api/v1/tiktok-proxy",
        json={
            "client_id": "client_1",
            "account_id": "123",
            "path": "campaign/create/",
            "method": "POST",
            "json_body": {"campaign_name": "New Camp"}
        },
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Created"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert "https://business-api.tiktok.com/open_api/v1.3/campaign/create/" in args[0]
    assert kwargs["json"] == {"campaign_name": "New Camp"}
    assert kwargs["headers"]["Access-Token"] == "mock_token"


@pytest.mark.asyncio
@patch("app.main.credential_store.resolve_credentials", new_callable=AsyncMock)
@patch("requests.get")
@patch("requests.post")
async def test_tiktok_organic_proxy_endpoint(mock_post, mock_get, mock_resolve_creds):
    headers = {"X-API-Key": settings.api_key}

    # Scenario 1: Credentials not found (401)
    mock_resolve_creds.return_value = None
    response = client.post(
        "/api/v1/tiktok-organic-proxy",
        json={
            "client_id": "client_1",
            "account_id": "org_123",
            "path": "business/video/list/",
            "method": "GET"
        },
        headers=headers
    )
    assert response.status_code == 401
    assert "Credentials not found" in response.json()["detail"]

    # Scenario 2: BC Asset (is_bc_asset = True) -> routes to business-api.tiktok.com with Access-Token
    mock_resolve_creds.return_value = {"access_token": "bc_token", "is_bc_asset": True}
    
    mock_get_resp = MagicMock()
    mock_get_resp.status_code = 200
    mock_get_resp.json.return_value = {"code": 0, "message": "OK", "data": {"list": []}}
    mock_get.return_value = mock_get_resp

    response = client.post(
        "/api/v1/tiktok-organic-proxy",
        json={
            "client_id": "client_1",
            "account_id": "org_123",
            "path": "business/video/list/",
            "method": "GET",
            "params": {"max_count": 10}
        },
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["code"] == 0
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "https://business-api.tiktok.com/open_api/v1.3/business/video/list/" in args[0]
    assert kwargs["params"] == {"max_count": 10}
    assert kwargs["headers"]["Access-Token"] == "bc_token"
    assert "Authorization" not in kwargs["headers"]

    # Reset mocks
    mock_get.reset_mock()

    # Scenario 3: Personal Profile (is_bc_asset = False) -> routes to open.tiktokapis.com with Bearer token
    mock_resolve_creds.return_value = {"access_token": "personal_token", "is_bc_asset": False}
    
    response = client.post(
        "/api/v1/tiktok-organic-proxy",
        json={
            "client_id": "client_1",
            "account_id": "org_123",
            "path": "video/list/",
            "method": "GET"
        },
        headers=headers
    )
    assert response.status_code == 200
    assert response.json()["code"] == 0
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "v2/video/list/" in args[0]
    assert "open.tiktokapis.com" in args[0]
    assert kwargs["headers"]["Authorization"] == "Bearer personal_token"
    assert "Access-Token" not in kwargs["headers"]




