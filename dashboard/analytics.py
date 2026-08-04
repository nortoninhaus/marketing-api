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
