from unittest.mock import MagicMock, patch
from google.cloud import firestore

from dashboard.analytics import log_analytics_event, ANALYTICS_EVENTS_COLLECTION


def test_log_analytics_event_success_with_user_and_details():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collection.return_value = mock_collection

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_client):
        result = log_analytics_event(
            event_name="login_success",
            user_id="user_123",
            details={"method": "password"}
        )

    assert result is True
    mock_client.collection.assert_called_once_with(ANALYTICS_EVENTS_COLLECTION)
    mock_collection.add.assert_called_once_with({
        "event_name": "login_success",
        "user_id": "user_123",
        "timestamp": firestore.SERVER_TIMESTAMP,
        "details": {"method": "password"}
    })


def test_log_analytics_event_success_default_user_and_details():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collection.return_value = mock_collection

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_client):
        result = log_analytics_event(event_name="page_view")

    assert result is True
    mock_client.collection.assert_called_once_with(ANALYTICS_EVENTS_COLLECTION)
    mock_collection.add.assert_called_once_with({
        "event_name": "page_view",
        "user_id": "anonymous",
        "timestamp": firestore.SERVER_TIMESTAMP,
        "details": {}
    })


def test_log_analytics_event_failure_returns_false():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_collection.add.side_effect = Exception("Firestore write error")
    mock_client.collection.return_value = mock_collection

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_client), \
         patch("dashboard.analytics.logger") as mock_logger:
        result = log_analytics_event(event_name="login_failed", user_id="user_123")

    assert result is False
    mock_logger.warning.assert_called()
