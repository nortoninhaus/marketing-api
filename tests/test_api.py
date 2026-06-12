"""
Tests for API endpoints.
"""

from app.models.requests import Platform

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "platforms_configured" in data

def test_list_platforms_unauthorized(client):
    response = client.get("/api/v1/platforms")
    assert response.status_code in (401, 403)  # Missing key returns 401 or 403 depending on FastAPI version

def test_list_platforms_authorized(client, auth_headers):
    response = client.get("/api/v1/platforms", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Ensure schema-driven fields are present
    assert "available_metrics" in data[0]
    assert "display_name" in data[0]

def test_get_platform_schema(client, auth_headers):
    response = client.get("/api/v1/schema/meta_ads", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["platform"] == "meta_ads"
    assert "metrics" in data
    assert "dimensions" in data

def test_campaign_data_unauthorized(client):
    payload = {
        "platform": "google_ads",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "metrics": ["clicks"],
        "client_id": "test_client",
        "user_id": "test_user",
        "account_id": "test_account"
    }
    response = client.post("/api/v1/campaign-data", json=payload)
    assert response.status_code in (401, 403)

def test_batch_data_authorized(client, auth_headers):
    payload = {
        "requests": [
            {
                "platform": "google_ads",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "metrics": ["clicks"],
                "client_id": "test_client",
                "user_id": "test_user",
                "account_id": "test_account"
            },
            {
                "platform": "ga4",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "metrics": ["sessions"],
                "client_id": "test_client",
                "user_id": "test_user",
                "account_id": "test_property"
            }
        ]
    }
    response = client.post("/api/v1/batch", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_platforms"] == 2
    assert "results" in data
    # Results should be DataResponse objects
    assert data["results"][0]["platform"] == "google_ads"


from unittest.mock import patch, MagicMock
from app.models.responses import CommentData

@patch("app.connectors.threads.ThreadsConnector.fetch_comments")
def test_comments_endpoint(mock_fetch, client, auth_headers):
    # Mock comment data
    mock_fetch.return_value = [
        CommentData(comment_id="c_1", text="Nice post!", author="user_a", timestamp="2026-05-22T12:00:00Z")
    ]
    
    payload = {
        "platform": "threads",
        "post_id": "thread_post_123",
        "client_id": "client_test",
        "user_id": "user_test",
        "account_id": "acc_test"
    }
    
    response = client.post("/api/v1/comments", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["platform"] == "threads"
    assert data["post_id"] == "thread_post_123"
    assert len(data["comments"]) == 1
    assert data["comments"][0]["comment_id"] == "c_1"
    assert data["comments"][0]["text"] == "Nice post!"
    assert data["comments"][0]["author"] == "user_a"
    assert mock_fetch.call_args[0][0] == "thread_post_123"

