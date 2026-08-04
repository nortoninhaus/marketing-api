# Design Specification: Dashboard Firestore Analytics Event Tracking

**Date:** 2026-08-04  
**Status:** Approved  
**Author:** Gentle AI / Antigravity  

## Summary
Add event tracking to the Streamlit Dashboard (`dashboard.py` and `dashboard/auth.py`), persisting analytics events directly into Google Cloud Firestore (`inhaus-marketing-api` project) under the `dashboard_analytics_events` collection.

The solution captures 4 key user interactions:
1. `login`
2. `ejecutar_consulta`
3. `aplicar_filtros`
4. `pulsar_demograficos`

---

## Architecture & Design

### 1. New Module: `dashboard/analytics.py`
A lightweight, dedicated analytics helper module that encapsulates all event logging logic to keep auth and UI modules decoupled.

```python
from typing import Dict, Any, Optional
import logging
from google.cloud import firestore
from dashboard.auth import get_firestore_client

logger = logging.getLogger(__name__)

ANALYTICS_EVENTS_COLLECTION = "dashboard_analytics_events"

def log_analytics_event(
    event_name: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Logs an analytics event to Firestore in a fail-safe manner.
    Errors are logged as warnings and never propagate to break the UI.
    """
    try:
        db = get_firestore_client()
        event_doc = {
            "event_name": event_name,
            "user_id": user_id or "anonymous",
            "timestamp": firestore.SERVER_TIMESTAMP,
            "details": details or {},
        }
        db.collection(ANALYTICS_EVENTS_COLLECTION).add(event_doc)
        return True
    except Exception as e:
        logger.warning(f"Failed to log analytics event '{event_name}': {e}")
        return False
```

### 2. Event Triggers and Details Payload

#### Event 1: `login`
- **Location:** `dashboard/auth.py` inside `require_dashboard_login()` when password verification succeeds.
- **Payload Details:**
  ```json
  {
    "auth_method": "form"
  }
  ```
- **User ID:** Authenticated `username`.

#### Event 2: `ejecutar_consulta`
- **Location:** `dashboard.py` when `execute_query = st.sidebar.button("🚀 Consultar API", ...)` is triggered.
- **Payload Details:**
  ```json
  {
    "platform_key": platform_key,
    "account_id": account_id,
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD",
    "write_to_bq": write_to_bq
  }
  ```
- **User ID:** `dashboard_user.get("username")`.

#### Event 3: `aplicar_filtros`
- **Location:** `dashboard.py` when `if st.button("Aplicar filtros", ...)` is pressed.
- **Payload Details:**
  ```json
  {
    "campaign_filter": campaign_filter,
    "adset_filter": adset_filter,
    "ad_filter": ad_filter,
    "applied_api_filters": applied_api_filters
  }
  ```
- **User ID:** `dashboard_user.get("username")`.

#### Event 4: `pulsar_demograficos`
- **Location:** `dashboard.py` when `st.checkbox("Cargar datos demográficos", value=False)` evaluates to `True`.
- **Payload Details:**
  ```json
  {
    "enabled": true,
    "platform_key": platform_key,
    "account_id": account_id
  }
  ```
- **User ID:** `dashboard_user.get("username")`.

---

## Resiliency and Error Handling
- All `log_analytics_event` calls are fail-safe. If Firestore write operations fail due to transient network issues, quota limits, or permission issues in local environments, a non-blocking `logger.warning()` is emitted.
- Dashboard rendering and query execution flow continue unaffected.

---

## Verification Plan
1. **Unit Testing:**
   - Create `tests/test_dashboard_analytics.py`.
   - Test `log_analytics_event` with a mocked Firestore client to ensure documents are formatted and created as expected.
   - Test exception handling when Firestore client throws an error, ensuring `log_analytics_event` returns `False` without raising.
2. **Integration Verification:**
   - Run `pytest tests/test_dashboard_analytics.py` and existing test suite (`pytest tests/test_dashboard_ui.py`).
