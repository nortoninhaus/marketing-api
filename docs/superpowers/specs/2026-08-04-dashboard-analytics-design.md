# Design Specification: Dashboard Firebase Analytics (GA4 Measurement Protocol) Event Tracking

**Date:** 2026-08-04  
**Status:** Approved  
**Author:** Gentle AI / Antigravity  

## Summary
Add event tracking to the Streamlit Dashboard (`dashboard.py` and `dashboard/auth.py`), sending analytics events directly to **Firebase Analytics / Google Analytics 4 (GA4)** via GA4 Measurement Protocol using Measurement ID `G-KEYBRJQSWF`.

The solution captures 4 key user interactions:
1. `login`
2. `ejecutar_consulta`
3. `aplicar_filtros`
4. `pulsar_demograficos`

---

## Architecture & Design

### 1. Configuration: `dashboard/config.py`
```python
GA_MEASUREMENT_ID = os.getenv("GA_MEASUREMENT_ID", "G-KEYBRJQSWF")
GA_API_SECRET = os.getenv("GA_API_SECRET", "")
```

### 2. Module Implementation: `dashboard/analytics.py`
A lightweight, dedicated analytics helper module that sends HTTP POST payloads to the GA4 Measurement Protocol endpoint.

```python
import logging
import requests
from typing import Dict, Any, Optional
from dashboard.config import GA_MEASUREMENT_ID, GA_API_SECRET

logger = logging.getLogger(__name__)

GA4_ENDPOINT = "https://www.google-analytics.com/mp/collect"

def log_analytics_event(
    event_name: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Logs an analytics event to Firebase Analytics / GA4 via Measurement Protocol.
    Fail-safe: non-blocking, errors logged as warnings.
    """
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
        logger.warning(f"GA4 Measurement Protocol status {response.status_code}: {response.text}")
        return False
    except Exception as exc:
        logger.warning(f"Failed to log GA4 analytics event '{event_name}': {exc}")
        return False
```

### 3. Event Triggers and Details Payload

#### Event 1: `login`
- **Location:** `dashboard/auth.py`
- **Payload Details:** `{"auth_method": "form"}`

#### Event 2: `ejecutar_consulta`
- **Location:** `dashboard.py`
- **Payload Details:** `{"platform_key": platform_key, "account_id": account_id, "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "write_to_bq": write_to_bq}`

#### Event 3: `aplicar_filtros`
- **Location:** `dashboard.py`
- **Payload Details:** `{"campaign_filter": campaign_filter, "adset_filter": adset_filter, "ad_filter": ad_filter}`

#### Event 4: `pulsar_demograficos`
- **Location:** `dashboard.py`
- **Payload Details:** `{"enabled": true, "platform_key": platform_key, "account_id": account_id}`

---

## Verification Plan
1. **Unit Testing:**
   - Update `tests/test_dashboard_analytics.py` to mock `requests.post`.
   - Verify HTTP payload structure, parameters, measurement_id `G-KEYBRJQSWF`, and error handling when HTTP requests timeout or fail.
2. **Suite Verification:**
   - Run full pytest suite (`.venv/bin/python -m pytest`).
