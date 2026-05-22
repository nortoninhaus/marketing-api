"""
Unit tests for Threads connector.
"""

from unittest.mock import MagicMock, patch
import pytest
from datetime import date
import httpx
from app.models.requests import DataRequest
from app.connectors.threads import ThreadsConnector


@patch("app.connectors.threads.httpx.Client")
def test_threads_fetch_media_insights(mock_client_class):
    # Set up mock responses
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock response for post listing
    mock_list_resp = MagicMock()
    mock_list_resp.status_code = 200
    mock_list_resp.json.return_value = {
        "data": [
            {"id": "thread_123", "text": "Hello Threads!", "timestamp": "2026-05-02T12:00:00+0000"}
        ]
    }

    # Mock response for post insights
    mock_ins_resp = MagicMock()
    mock_ins_resp.status_code = 200
    mock_ins_resp.json.return_value = {
        "data": [
            {"name": "views", "values": [{"value": 1500}]},
            {"name": "likes", "values": [{"value": 120}]},
            {"name": "replies", "values": [{"value": 15}]},
        ]
    }

    mock_client.get.side_effect = [mock_list_resp, mock_ins_resp]

    connector = ThreadsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_threads_token",
            "threads_user_id": "me"
        }

        req = DataRequest(
            platform="threads",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["views", "likes", "replies"],
            dimensions=["post_id"],
            client_id="test_client",
            user_id="test_user",
            account_id="me"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Thread_thread_123"
        assert results[0].metrics["views"] == 1500
        assert results[0].metrics["likes"] == 120
        assert results[0].metrics["replies"] == 15


@patch("app.connectors.threads.httpx.Client")
def test_threads_fetch_user_insights(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    # Mock response for account-level insights
    mock_ins_resp = MagicMock()
    mock_ins_resp.status_code = 200
    mock_ins_resp.json.return_value = {
        "data": [
            {"name": "views", "values": [{"value": 10000, "end_time": "2026-05-02T23:59:59+0000"}]},
            {"name": "likes", "values": [{"value": 500, "end_time": "2026-05-02T23:59:59+0000"}]},
        ]
    }
    mock_client.get.return_value = mock_ins_resp

    connector = ThreadsConnector()
    with patch.object(connector, "get_credentials") as mock_get_creds:
        mock_get_creds.return_value = {
            "access_token": "fake_threads_token",
            "threads_user_id": "me"
        }

        # Ask for user-level metrics only (e.g. followers_count, views)
        req = DataRequest(
            platform="threads",
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 7),
            metrics=["views", "likes"],  # User metrics triggers account-level path
            client_id="test_client",
            user_id="test_user",
            account_id="me"
        )

        results = connector.fetch_data(req)
        assert len(results) == 1
        assert results[0].campaign_name == "Threads_Account_Insights"
        assert results[0].date == "2026-05-02"
        assert results[0].metrics["views"] == 10000
        assert results[0].metrics["likes"] == 500


@patch("app.connectors.threads.httpx.Client")
def test_threads_fetch_comments(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__enter__.return_value = mock_client

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "data": [
            {"id": "reply_1", "text": "Awesome!", "username": "user1", "timestamp": "2026-05-02T12:00:00+0000"},
            {"id": "reply_2", "text": "Agreed.", "username": "user2", "timestamp": "2026-05-02T12:01:00+0000"},
        ],
        "paging": {}
    }
    mock_client.get.return_value = mock_resp

    connector = ThreadsConnector()
    comments = connector.fetch_comments("thread_123", "fake_token")
    assert len(comments) == 2
    assert comments[0].comment_id == "reply_1"
    assert comments[0].text == "Awesome!"
    assert comments[0].author == "user1"
    assert comments[1].comment_id == "reply_2"
    assert comments[1].text == "Agreed."
    assert comments[1].author == "user2"
