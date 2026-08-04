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


def test_log_login_event():
    from dashboard.auth import log_login_event
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        log_login_event("testuser")
        mock_log.assert_called_once_with("login", user_id="testuser", details={"auth_method": "form"})


def test_require_dashboard_login_logs_login_event():
    from dashboard.auth import require_dashboard_login
    mock_user = {"username": "testuser", "client_id": "client_1", "user_id": "user_1", "accounts": {}}
    mock_session_state = {}
    mock_query_params = {}

    with patch("dashboard.auth.st") as mock_st, \
         patch("dashboard.auth.authenticate_dashboard_user", return_value=mock_user), \
         patch("dashboard.auth.log_login_event") as mock_log_login, \
         patch("dashboard.auth.create_dashboard_token", return_value="mock_token"), \
         patch("dashboard.auth.dashboard_auth_cookie_bridge"):

        mock_st.session_state = mock_session_state
        mock_st.query_params = mock_query_params
        mock_st.text_input.side_effect = ["testuser", "password"]
        mock_st.form_submit_button.return_value = True
        mock_st.container.return_value.__enter__.return_value = mock_st
        mock_st.form.return_value.__enter__.return_value = mock_st

        require_dashboard_login("☀", MagicMock())

        mock_log_login.assert_called_once_with("testuser")

