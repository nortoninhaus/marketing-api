from unittest.mock import MagicMock, patch
from google.cloud import firestore

from dashboard.analytics import log_analytics_event, ANALYTICS_EVENTS_COLLECTION, GA4_ENDPOINT


def test_log_analytics_event_success_both_firestore_and_ga4():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    mock_client.collection.return_value = mock_collection

    mock_response = MagicMock()
    mock_response.status_code = 204

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_client), \
         patch("dashboard.analytics.requests.post", return_value=mock_response) as mock_post, \
         patch("dashboard.analytics.GA_MEASUREMENT_ID", "G-KEYBRJQSWF"):

        result = log_analytics_event(
            event_name="login_success",
            user_id="user_123",
            details={"method": "password"}
        )

    assert result is True
    # Verify Firestore write
    mock_client.collection.assert_called_once_with(ANALYTICS_EVENTS_COLLECTION)
    mock_collection.add.assert_called_once()
    # Verify GA4 post
    mock_post.assert_called_once()
    url, kwargs = mock_post.call_args
    assert "measurement_id=G-KEYBRJQSWF" in url[0]
    payload = kwargs["json"]
    assert payload["client_id"] == "user_123"
    assert payload["events"][0]["name"] == "login_success"


def test_log_analytics_event_firestore_resiliency():
    mock_client = MagicMock()
    mock_client.collection.side_effect = Exception("Firestore write error")

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


def test_log_query_execution():
    from dashboard.analytics import log_query_execution
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        log_query_execution("user123", "meta_ads", "act_123", "2026-08-01", "2026-08-04", False)
        mock_log.assert_called_once_with(
            "ejecutar_consulta",
            user_id="user123",
            details={
                "platform_key": "meta_ads",
                "account_id": "act_123",
                "start_date": "2026-08-01",
                "end_date": "2026-08-04",
                "write_to_bq": False,
            }
        )


def test_log_filter_application():
    from dashboard.analytics import log_filter_application
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        log_filter_application("user123", ["Camp1"], ["Adset1"], "Ad1", {"campaign.id": ["c1"]})
        mock_log.assert_called_once_with(
            "aplicar_filtros",
            user_id="user123",
            details={
                "campaign_filter": ["Camp1"],
                "adset_filter": ["Adset1"],
                "ad_filter": "Ad1",
                "applied_api_filters": {"campaign.id": ["c1"]},
            }
        )


def test_log_demographics_check():
    from dashboard.analytics import log_demographics_check
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        log_demographics_check("user123", "meta_ads", "act_123")
        mock_log.assert_called_once_with(
            "pulsar_demograficos",
            user_id="user123",
            details={
                "enabled": True,
                "platform_key": "meta_ads",
                "account_id": "act_123",
            }
        )
