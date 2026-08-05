import json
import logging
from threading import Thread
from typing import Any, Dict, Optional

from google.cloud import firestore
import streamlit as st

from dashboard.auth import get_firestore_client
from dashboard.config import GA_MEASUREMENT_ID

logger = logging.getLogger(__name__)

ANALYTICS_EVENTS_COLLECTION = "dashboard_analytics_events"
PENDING_GTAG_EVENTS_KEY = "_pending_gtag_events"


def _write_firestore_event(event_name: str, event_doc: Dict[str, Any]) -> None:
    try:
        db = get_firestore_client()
        db.collection(ANALYTICS_EVENTS_COLLECTION).add(
            event_doc,
            retry=None,
            timeout=5,
        )
    except Exception as exc:
        logger.warning(f"Failed to log Firestore analytics event '{event_name}': {exc}")


def inject_gtag_script():
    """Injects Google Analytics 4 (gtag.js) script into parent document for real-time active users and session tracking."""
    if not GA_MEASUREMENT_ID:
        return
    pending_events = st.session_state.get(PENDING_GTAG_EVENTS_KEY, [])
    pending_events_json = json.dumps(pending_events, default=str).replace("</", "<\\/")
    gtag_html = f"""
    <script>
    (function() {{
        try {{
            if (window.parent && window.parent.document) {{
                const parentDoc = window.parent.document;
                const parentWin = window.parent;
                parentWin.dataLayer = parentWin.dataLayer || [];
                parentWin.gtag = parentWin.gtag || function(){{ parentWin.dataLayer.push(arguments); }};
                if (!parentDoc.getElementById('ga4-gtag-script')) {{
                    const script = parentDoc.createElement('script');
                    script.id = 'ga4-gtag-script';
                    script.async = true;
                    script.src = 'https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}';
                    parentDoc.head.appendChild(script);

                    parentWin.gtag('js', new Date());
                    parentWin.gtag('config', '{GA_MEASUREMENT_ID}');
                }}
                const pendingEvents = {pending_events_json};
                pendingEvents.forEach(event => parentWin.gtag('event', event.name, event.params));
            }}
        }} catch(e) {{}}
    }})();
    </script>
    """
    try:
        st.html(gtag_html, unsafe_allow_javascript=True)
    except Exception:
        return
    if pending_events:
        del st.session_state[PENDING_GTAG_EVENTS_KEY]


def log_analytics_event(
    event_name: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Logs an analytics event to Firestore and queues it for frontend GTAG.
    Fail-safe: errors logged as warnings.
    """
    success = False

    # 1. Store event in Firestore without blocking the Streamlit rerun.
    try:
        event_doc = {
            "event_name": event_name,
            "user_id": user_id or "anonymous",
            "timestamp": firestore.SERVER_TIMESTAMP,
            "details": details or {},
        }
        # ponytail: one daemon thread per event; use a queue if event volume grows.
        Thread(
            target=_write_firestore_event,
            args=(event_name, event_doc),
            daemon=True,
        ).start()
        success = True
    except Exception as exc:
        logger.warning(f"Failed to log Firestore analytics event '{event_name}': {exc}")

    # 2. Queue frontend GTAG delivery for the next stable Streamlit run.
    if GA_MEASUREMENT_ID:
        try:
            params = dict(details or {})
            if user_id:
                params["user_id"] = user_id
            st.session_state.setdefault(PENDING_GTAG_EVENTS_KEY, []).append({
                "name": event_name.replace(" ", "_").lower(),
                "params": params,
            })
        except Exception:
            pass

    return success


def log_query_execution(user_id: str, platform_key: str, account_id: str, start_date: str, end_date: str, write_to_bq: bool):
    return log_analytics_event(
        "ejecutar_consulta",
        user_id=user_id,
        details={
            "platform_key": platform_key,
            "account_id": account_id,
            "start_date": str(start_date),
            "end_date": str(end_date),
            "write_to_bq": write_to_bq,
        }
    )


def log_filter_application(user_id: str, campaign_filter: Any, adset_filter: Any, ad_filter: Any, applied_api_filters: Any):
    return log_analytics_event(
        "aplicar_filtros",
        user_id=user_id,
        details={
            "campaign_filter": campaign_filter,
            "adset_filter": adset_filter,
            "ad_filter": ad_filter,
            "applied_api_filters": applied_api_filters,
        }
    )


def log_demographics_check(user_id: str, platform_key: str, account_id: str):
    return log_analytics_event(
        "pulsar_demograficos",
        user_id=user_id,
        details={
            "enabled": True,
            "platform_key": platform_key,
            "account_id": account_id,
        }
    )
