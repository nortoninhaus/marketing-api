import logging
import requests
from typing import Any, Dict, Optional

from dashboard.config import GA_MEASUREMENT_ID, GA_API_SECRET

logger = logging.getLogger(__name__)

GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"


def log_analytics_event(
    event_name: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """Logs an analytics event to GA4 / Firebase Analytics via Measurement Protocol."""
    if not GA_MEASUREMENT_ID:
        return False

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

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code in (200, 204):
            return True
        logger.warning(f"GA4 Measurement Protocol returned status {response.status_code}: {response.text}")
        return False
    except Exception as exc:
        logger.warning(f"Failed to log GA4 analytics event '{event_name}': {exc}")
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

