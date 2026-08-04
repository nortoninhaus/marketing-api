import logging
from typing import Any, Dict, Optional
from google.cloud import firestore

from dashboard.auth import get_firestore_client

logger = logging.getLogger(__name__)

ANALYTICS_EVENTS_COLLECTION = "dashboard_analytics_events"


def log_analytics_event(
    event_name: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """Logs an analytics event to Firestore."""
    doc_data = {
        "event_name": event_name,
        "user_id": user_id or "anonymous",
        "timestamp": firestore.SERVER_TIMESTAMP,
        "details": details or {},
    }
    try:
        client = get_firestore_client()
        client.collection(ANALYTICS_EVENTS_COLLECTION).add(doc_data)
        return True
    except Exception as exc:
        logger.warning(f"Failed to log analytics event '{event_name}': {exc}")
        return False


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

