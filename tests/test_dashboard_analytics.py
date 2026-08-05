from unittest.mock import MagicMock, patch
from google.cloud import firestore

from dashboard.analytics import (
    ANALYTICS_EVENTS_COLLECTION,
    PENDING_GTAG_EVENTS_KEY,
    _write_firestore_event,
    inject_gtag_script,
    log_analytics_event,
)


def test_gtag_injection_flushes_pending_events():
    session_state = {
        PENDING_GTAG_EVENTS_KEY: [
            {"name": "login", "params": {"auth_method": "form"}},
        ]
    }

    with patch("dashboard.analytics.st.html") as mock_html, \
         patch("dashboard.analytics.st.session_state", session_state), \
         patch("dashboard.analytics.GA_MEASUREMENT_ID", "G-KEYBRJQSWF"):
        inject_gtag_script()

    mock_html.assert_called_once()
    assert mock_html.call_args.kwargs == {"unsafe_allow_javascript": True}
    assert '"name": "login"' in mock_html.call_args.args[0]
    assert PENDING_GTAG_EVENTS_KEY not in session_state


def test_gtag_injection_keeps_events_when_rendering_fails():
    session_state = {
        PENDING_GTAG_EVENTS_KEY: [
            {"name": "login", "params": {}},
        ]
    }

    with patch("dashboard.analytics.st.html", side_effect=RuntimeError("render failed")), \
         patch("dashboard.analytics.st.session_state", session_state), \
         patch("dashboard.analytics.GA_MEASUREMENT_ID", "G-KEYBRJQSWF"):
        inject_gtag_script()

    assert session_state[PENDING_GTAG_EVENTS_KEY][0]["name"] == "login"


def test_log_analytics_event_queues_firestore_and_gtag():
    session_state = {}
    with patch("dashboard.analytics.Thread") as mock_thread, \
         patch("dashboard.analytics.st.session_state", session_state), \
         patch("dashboard.analytics.GA_MEASUREMENT_ID", "G-KEYBRJQSWF"):

        result = log_analytics_event(
            event_name="login_success",
            user_id="user_123",
            details={"method": "password"}
        )

    assert result is True
    mock_thread.return_value.start.assert_called_once_with()
    assert mock_thread.call_args.kwargs["target"] is _write_firestore_event
    assert mock_thread.call_args.kwargs["daemon"] is True
    assert session_state[PENDING_GTAG_EVENTS_KEY] == [
        {
            "name": "login_success",
            "params": {"method": "password", "user_id": "user_123"},
        }
    ]


def test_firestore_write_is_bounded_and_resilient():
    mock_client = MagicMock()
    mock_client.collection.side_effect = Exception("Firestore write error")

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_client), \
         patch("dashboard.analytics.logger") as mock_logger:
        _write_firestore_event("login_failed", {"user_id": "user_123"})

    mock_logger.warning.assert_called()


def test_firestore_write_disables_retries_and_has_timeout():
    mock_client = MagicMock()

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_client):
        _write_firestore_event("login", {"user_id": "user_123"})

    mock_client.collection.assert_called_once_with(ANALYTICS_EVENTS_COLLECTION)
    mock_client.collection.return_value.add.assert_called_once_with(
        {"user_id": "user_123"},
        retry=None,
        timeout=5,
    )


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
