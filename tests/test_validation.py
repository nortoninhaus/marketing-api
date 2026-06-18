"""
Tests for platform parameter and metric validation logic and endpoints.
"""

from datetime import date
import pytest
from unittest.mock import patch, MagicMock
from app.metrics import validate_platform_params
from app.models.requests import DataRequest

def test_validate_platform_params_direct():
    # 1. Test valid configurations
    errors = validate_platform_params("meta_ads", "act_12345", post_id="post_999")
    assert not errors

    errors = validate_platform_params("google_ads", "123-456-7890")
    assert not errors

    errors = validate_platform_params("ga4", "properties/999888")
    assert not errors

    errors = validate_platform_params("google_play", "com.inhaus.marketing")
    assert not errors

    # 2. Test invalid optional parameters (silent error prevention)
    errors = validate_platform_params("meta_ads", "act_12345", video_id="vid_111")
    assert len(errors) == 1
    assert "video_id" in errors[0]

    errors = validate_platform_params("google_ads", "1234567890", post_id="post_123")
    assert len(errors) == 1
    assert "post_id" in errors[0]

    # 3. Test invalid account_id formats
    errors = validate_platform_params("meta_ads", "invalid_format")
    assert len(errors) == 1
    assert "format" in errors[0] or "meta_ads" in errors[0]

    errors = validate_platform_params("google_ads", "12345")
    assert len(errors) == 1
    assert "10" in errors[0] or "google_ads" in errors[0]


def test_data_request_pydantic_validation():
    # Valid model
    req = DataRequest(
        platform="meta_ads",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 5),
        metrics=["impressions"],
        client_id="c_1",
        user_id="u_1",
        account_id="act_12345",
        post_id="post_123"
    )
    assert req.account_id == "act_12345"

    # Invalid model due to invalid parameter (video_id in meta_ads)
    with pytest.raises(ValueError) as exc:
        DataRequest(
            platform="meta_ads",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
            metrics=["impressions"],
            client_id="c_1",
            user_id="u_1",
            account_id="act_12345",
            video_id="vid_123"
        )
    assert "video_id" in str(exc.value)


def test_validate_endpoint_unauthorized(client):
    payload = {
        "platform": "meta_ads",
        "metrics": ["impressions"],
        "account_id": "act_123"
    }
    resp = client.post("/api/v1/validate", json=payload)
    assert resp.status_code in (401, 403)


def test_validate_endpoint_authorized(client, auth_headers):
    # Valid
    payload = {
        "platform": "meta_ads",
        "metrics": ["impressions"],
        "use_generic_names": True,
        "account_id": "act_12345"
    }
    resp = client.post("/api/v1/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is True
    assert "impressions" in data["valid_metrics"]
    assert data["translations"]["impressions"] == "impressions"

    # Invalid metric & parameter
    payload = {
        "platform": "meta_ads",
        "metrics": ["followers"],
        "use_generic_names": True,
        "account_id": "invalid_acc",
        "video_id": "vid_abc"
    }
    resp = client.post("/api/v1/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert len(data["parameter_errors"]) > 0
    assert len(data["invalid_metrics"]) > 0


@patch("app.services.credential_store.credential_store.list_oauth_connections")
@patch("app.services.credential_store.credential_store.get_credentials")
def test_credentials_status_endpoint(mock_get, mock_list, client, auth_headers):
    # Setup mock returns
    mock_list.return_value = [{"account_name": "Test Account"}]
    mock_get.return_value = None

    resp = client.get("/api/v1/credentials/status?client_id=client_test", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["client_id"] == "client_test"
    assert "platforms" in data
    # Check meta_ads status
    assert data["platforms"]["meta_ads"]["has_credentials"] is True
    assert data["platforms"]["meta_ads"]["credential_type"] == "oauth"


def test_campaign_data_dry_run(client, auth_headers):
    payload = {
        "platform": "meta_ads",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "metrics": ["impressions"],
        "client_id": "test_client",
        "user_id": "test_user",
        "account_id": "act_12345",
        "dry_run": True
    }
    resp = client.post("/api/v1/campaign-data", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"] == []
    assert data["metadata"]["dry_run"] is True


@patch("app.services.credential_store.credential_store.list_oauth_connections")
@patch("app.services.credential_store.credential_store.get_credentials")
def test_validate_endpoint_semantic_failure(mock_get, mock_list, client, auth_headers):
    mock_list.return_value = []
    mock_get.return_value = None

    payload = {
        "platform": "meta_ads",
        "metrics": ["impressions"],
        "client_id": "client_without_creds",
        "account_id": "act_12345"
    }
    resp = client.post("/api/v1/validate", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valid"] is False
    assert any("semántica" in err for err in data["parameter_errors"])


def test_base_connector_rate_limit_parsing():
    import requests as _requests
    from app.connectors.base import BaseConnector
    
    class TestConnector(BaseConnector):
        platform_name = "test"
        def fetch_data(self, request): return []
        def get_schema(self): return {}

    response = _requests.Response()
    response.status_code = 429
    response.headers = {"x-rate-limit-remaining": "0"}
    
    error = _requests.exceptions.HTTPError(response=response)
    
    connector = TestConnector()
    detail = connector.handle_error(error)
    
    assert detail.code == "RATE_LIMIT"
    assert detail.rate_limit_remaining == 0

