# LLM Context for Marketing Data API v5.0

This document provides essential technical context for LLMs and AI Agents interacting with or developing for this codebase.

## System Overview

The Marketing Data API is a **unified abstraction layer** over 14+ marketing, analytics, and social platforms. It handles the complexity of individual SDKs, authentication flows, and API rate limits, providing a standardized JSON interface for data retrieval.

## Multi-Tenancy Architecture

The system is designed for **multi-tenancy** and **per-request identity resolution**.

### Request Flow
1. **Request**: The client sends a `DataRequest` containing `client_id`, `user_id`, and `account_id`.
2. **Identity Resolution**: `main.py` fetches the appropriate platform credentials from the `credential_store` (Firestore) using the IDs.
3. **Connector Dispatch**: The `Dispatcher` routes the request to the specific platform connector.
4. **Credential Injection**: The connector's `get_credentials()` method resolves the final credential set in this order:
   - `request.credentials` (provided inline in the request)
   - `credential_store` (fetched from secure storage)
   - `settings` (global fallbacks in `.env`)

### Key Connector Pattern
Every connector inherits from `BaseConnector` and implements `fetch_data`.
```python
def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
    # 1. Start with storage-resolved credentials
    creds = request.credentials if request and request.credentials else {}
    
    # 2. Extract dynamic identifier (account_id, property_id, etc.)
    # 3. Apply platform-specific credential logic
    return creds
```

## Tool Calling & Agentic Design

- **Structured Responses**: Every endpoint returns a standardized envelope with `request_id`, `timestamp`, and `platform`.
- **Enum-Driven**: All platforms are defined in the `Platform` Enum.
- **Batched Requests**: Agents should prefer the `/batch` endpoint to retrieve data across multiple silos in a single tool call.

## Critical Files for LLMs

- [app/models/requests.py](file:///Users/nicolasnorton/Marketing%20Api/app/models/requests.py): Defines the request schema and available platforms.
- [app/connectors/base.py](file:///Users/nicolasnorton/Marketing%20Api/app/connectors/base.py): The interface for all data retrieval.
- [app/main.py](file:///Users/nicolasnorton/Marketing%20Api/app/main.py): Identity resolution and routing logic.

## Developing New Connectors

1. Create `app/connectors/new_platform.py`.
2. Inherit from `BaseConnector`.
3. Implement `get_credentials`, `get_schema`, and `fetch_data`.
4. Register in `app/services/dispatcher.py`.
5. Add to `Platform` enum in `app/models/requests.py`.
