# Dashboard Firestore Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement analytics event tracking for Streamlit Dashboard (`login`, `ejecutar_consulta`, `aplicar_filtros`, `pulsar_demograficos`) into Google Cloud Firestore (`dashboard_analytics_events` collection).

**Architecture:** A fail-safe helper function `log_analytics_event` is introduced in `dashboard/analytics.py`. It uses the existing `get_firestore_client()` from `dashboard/auth.py` and is invoked from `dashboard/auth.py` and `dashboard.py`. All Firestore write errors are caught and logged with `logger.warning()` to ensure zero UI interruption.

**Tech Stack:** Python 3.11+, Streamlit, Google Cloud Firestore, Pytest, unittest.mock.

## Global Constraints

- Collection name in Firestore: `dashboard_analytics_events`
- Event names: `login`, `ejecutar_consulta`, `aplicar_filtros`, `pulsar_demograficos`
- Must be fail-safe: wrapped in `try/except` to prevent breaking UI if Firestore is unreachable
- Must conform to Rioplatense/English code rules (English for code/identifiers/comments)

---

### Task 1: Create `dashboard/analytics.py` and unit tests

**Files:**
- Create: `dashboard/analytics.py`
- Test: `tests/test_dashboard_analytics.py`

**Interfaces:**
- Produces: `log_analytics_event(event_name: str, user_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> bool`

- [ ] **Step 1: Write the failing unit tests**

Create `tests/test_dashboard_analytics.py`:
```python
from unittest.mock import MagicMock, patch
from dashboard.analytics import log_analytics_event, ANALYTICS_EVENTS_COLLECTION

def test_log_analytics_event_success():
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_db):
        res = log_analytics_event("test_event", user_id="user123", details={"key": "val"})

    assert res is True
    mock_db.collection.assert_called_once_with(ANALYTICS_EVENTS_COLLECTION)
    mock_collection.add.assert_called_once()
    added_doc = mock_collection.add.call_args[0][0]
    assert added_doc["event_name"] == "test_event"
    assert added_doc["user_id"] == "user123"
    assert added_doc["details"] == {"key": "val"}

def test_log_analytics_event_failure_resiliency():
    mock_db = MagicMock()
    mock_db.collection.side_effect = Exception("Firestore network error")

    with patch("dashboard.analytics.get_firestore_client", return_value=mock_db):
        res = log_analytics_event("test_event", user_id="user123")

    assert res is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard_analytics.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'dashboard.analytics')

- [ ] **Step 3: Write minimal implementation**

Create `dashboard/analytics.py`:
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

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dashboard_analytics.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/analytics.py tests/test_dashboard_analytics.py
git commit -m "feat: add dashboard analytics helper module with unit tests"
```

---

### Task 2: Integrate `login` event tracking in `dashboard/auth.py`

**Files:**
- Modify: `dashboard/auth.py`
- Modify: `tests/test_dashboard_analytics.py`

**Interfaces:**
- Consumes: `log_analytics_event` from `dashboard.analytics`

- [ ] **Step 1: Write test for login analytics logging**

Add to `tests/test_dashboard_analytics.py`:
```python
def test_login_event_logging():
    with patch("dashboard.auth.log_analytics_event") as mock_log:
        from dashboard.auth import log_login_event
        log_login_event("test_admin")
        mock_log.assert_called_once_with("login", user_id="test_admin", details={"auth_method": "form"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard_analytics.py::test_login_event_logging -v`
Expected: FAIL (ImportError: cannot import name 'log_login_event')

- [ ] **Step 3: Update `dashboard/auth.py`**

In `dashboard/auth.py`:
Add helper function and call it inside `require_dashboard_login` when password verification passes:
```python
def log_login_event(username: str):
    from dashboard.analytics import log_analytics_event
    log_analytics_event("login", user_id=username, details={"auth_method": "form"})
```

Call `log_login_event(username)` inside `require_dashboard_login` right after successful user login logic (before `st.rerun()` or returning user).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_dashboard_analytics.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard/auth.py tests/test_dashboard_analytics.py
git commit -m "feat: log login events to firestore analytics"
```

---

### Task 3: Integrate `ejecutar_consulta`, `aplicar_filtros`, and `pulsar_demograficos` event tracking in `dashboard.py`

**Files:**
- Modify: `dashboard.py`
- Modify: `tests/test_dashboard_analytics.py`

**Interfaces:**
- Consumes: `log_analytics_event` from `dashboard.analytics`

- [ ] **Step 1: Add unit tests for dashboard event triggers**

Add to `tests/test_dashboard_analytics.py`:
```python
def test_ejecutar_consulta_event_logging():
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        from dashboard.analytics import log_query_execution
        log_query_execution("user_a", "meta_ads", "act_123", "2026-08-01", "2026-08-04", False)
        mock_log.assert_called_once_with(
            "ejecutar_consulta",
            user_id="user_a",
            details={
                "platform_key": "meta_ads",
                "account_id": "act_123",
                "start_date": "2026-08-01",
                "end_date": "2026-08-04",
                "write_to_bq": False,
            }
        )

def test_aplicar_filtros_event_logging():
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        from dashboard.analytics import log_filter_application
        log_filter_application("user_a", ["Camp A"], ["Adset B"], "Todos", {})
        mock_log.assert_called_once_with(
            "aplicar_filtros",
            user_id="user_a",
            details={
                "campaign_filter": ["Camp A"],
                "adset_filter": ["Adset B"],
                "ad_filter": "Todos",
                "applied_api_filters": {},
            }
        )

def test_pulsar_demograficos_event_logging():
    with patch("dashboard.analytics.log_analytics_event") as mock_log:
        from dashboard.analytics import log_demographics_check
        log_demographics_check("user_a", "meta_ads", "act_123")
        mock_log.assert_called_once_with(
            "pulsar_demograficos",
            user_id="user_a",
            details={
                "enabled": True,
                "platform_key": "meta_ads",
                "account_id": "act_123",
            }
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_dashboard_analytics.py -v`
Expected: FAIL (ImportError for `log_query_execution`, `log_filter_application`, `log_demographics_check`)

- [ ] **Step 3: Implement helper functions in `dashboard/analytics.py` and call them in `dashboard.py`**

In `dashboard/analytics.py`:
```python
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
```

In `dashboard.py`:
1. When `execute_query` is clicked:
```python
if execute_query:
    log_query_execution(
        current_username,
        platform_key,
        account_id,
        start_date.isoformat(),
        end_date.isoformat(),
        write_to_bq
    )
    st.session_state.query_run = True
    ...
```
2. When `Aplicar filtros` button is clicked:
```python
if st.button("Aplicar filtros", type="primary", use_container_width=True):
    ...
    log_filter_application(
        current_username,
        campaign_filter,
        adset_filter,
        ad_filter,
        applied_api_filters
    )
    st.session_state.force_query_fetch = True
    st.rerun()
```
3. When `st.checkbox("Cargar datos demográficos", value=False)` is checked:
```python
if platform_key == "meta_ads" and st.checkbox("Cargar datos demográficos", value=False):
    log_demographics_check(current_username, platform_key, account_id)
    ...
```

- [ ] **Step 4: Run all tests to verify passing**

Run: `pytest tests/test_dashboard_analytics.py tests/test_dashboard_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dashboard.py dashboard/analytics.py tests/test_dashboard_analytics.py
git commit -m "feat: log query execution, filter application, and demographics check events"
```
