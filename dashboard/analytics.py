import logging
import requests
from typing import Any, Dict, Optional
from google.cloud import firestore

from dashboard.auth import get_firestore_client
from dashboard.config import GA_MEASUREMENT_ID, GA_API_SECRET

logger = logging.getLogger(__name__)

ANALYTICS_EVENTS_COLLECTION = "dashboard_analytics_events"
GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"


def log_analytics_event(
    event_name: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Logs an analytics event to both Firestore (instant document store) and GA4 Measurement Protocol.
    Fail-safe: errors logged as warnings.
    """
    success = False

    # 1. Store event in Firestore (visible instantly in Firebase Firestore console)
    try:
        db = get_firestore_client()
        event_doc = {
            "event_name": event_name,
            "user_id": user_id or "anonymous",
            "timestamp": firestore.SERVER_TIMESTAMP,
            "details": details or {},
        }
        db.collection(ANALYTICS_EVENTS_COLLECTION).add(event_doc)
        success = True
    except Exception as exc:
        logger.warning(f"Failed to log Firestore analytics event '{event_name}': {exc}")

    # 2. Dispatch to GA4 / Firebase Analytics Measurement Protocol
    if GA_MEASUREMENT_ID:
        try:
            client_id = user_id or "anonymous_dashboard_user"
            params = dict(details or {})
            if user_id:
                params["user_id"] = user_id

            formatted_event_name = event_name.replace(" ", "_").lower()
            payload = {
                "client_id": client_id,
                "events": [
                    {
                        "name": formatted_event_name,
                        "params": params
                    }
                ]
            }

            url = f"{GA4_ENDPOINT}?measurement_id={GA_MEASUREMENT_ID}"
            if GA_API_SECRET:
                url += f"&api_secret={GA_API_SECRET}"

            requests.post(url, json=payload, timeout=5)
        except Exception as exc:
            logger.warning(f"Failed to log GA4 analytics event '{event_name}': {exc}")

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
