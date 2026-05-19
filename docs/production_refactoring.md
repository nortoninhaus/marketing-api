# Production Refactoring Walkthrough: Inhaus Marketing Data API v5.0

This walkthrough documents the comprehensive production-grade upgrade of the Inhaus Marketing Data API. The codebase has been modernized to support true multi-tenancy, dynamic credential resolution, async non-blocking database queries, and robust agentic tool-calling patterns.

---

## 1. Unified Connector Architecture

All platform connectors (Meta, Google, TikTok, LinkedIn, etc.) have been updated to inherit from a standardized `BaseConnector` and implement a dynamic, multi-tenant credential resolution flow.

### Standardized Signature
Connectors now implement:
```python
def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]
```

### Dynamic Credential Resolution Priority
Instead of relying solely on static `.env` settings or hardcoded credentials, every request dynamically resolves credentials using the following hierarchy:
1. **Explicit Request Credentials**: Direct inline overrides provided in `DataRequest.credentials` (ideal for on-the-fly OAuth access token rotation).
2. **Secure Multi-Tenant Store**: Retrieved asynchronously from Firestore using `client_id` and the specific platform name.
3. **Environment Variable Fallback**: System-wide defaults defined in the local `.env` file (e.g., developer tokens, master API keys).

---

## 2. Dynamic Schema Discovery & Agentic Readiness

To support seamless integration with LLMs and AI Agents, the API exposes advanced discovery and reflective capabilities:

### Endpoint: `GET /api/v1/platforms`
*   **Purpose**: Allows agents to query which platforms are currently supported and whether they are active/configured for the requesting tenant.
*   **Polymorphic Handling**: Handles both basic string metrics and descriptive dictionaries for maximum metadata richness.

### Endpoint: `GET /api/v1/schema/{platform}`
*   **Purpose**: Reflects the complete JSON schema of supported metrics, dimensions, and platform-specific capabilities (e.g., whether the platform is Ads, Organic, or Analytics).

### Updated MCP Server Tools
The Model Context Protocol (MCP) definitions in `app/mcp.py` have been upgraded to match the new schema:
*   `get_marketing_data` and `get_batch_marketing_data` now accept:
    *   `client_id` (String)
    *   `user_id` (String)
    *   `account_id` (String)
    *   `post_id` / `video_id` / `app_id` (Optional strings for organic content & app platforms)

---

## 3. High-Performance Batch Processing

The `/api/v1/batch` endpoint has been optimized for scale and aggregate stability:
*   **Concurrency**: Uses `asyncio.gather` combined with `asyncio.to_thread` to execute API fetches across multiple marketing platforms in parallel, keeping the FastAPI event loop fully non-blocking.
*   **Partial Failure Handling**: If one platform fails (e.g., invalid token or network timeout), the batch request returns a `status: "partial"` along with the successfully retrieved data and structured errors for the failed platforms.

---

## 4. Modernization & Code Health

*   **Async Firestore**: Upgraded the `CredentialStore` to use Firestore's `AsyncClient` for high-concurrency, non-blocking I/O.
*   **Python 3.12+ Readiness**: Resolved FastAPI lifecycle startup/shutdown deprecation warnings by implementing the recommended `asynccontextmanager` `lifespan` handler.
*   **Strict DateTime Handling**: Replaced deprecated `datetime.utcnow()` calls with timezone-aware `datetime.now(timezone.utc)` to prevent runtime warnings and clock-skew errors.
*   **Health and Connectivity Pings**: Robustly implemented `ping()` in all connectors to allow deep connectivity checking (e.g., `/health?deep=true`).

---

## 5. Verification & Test Suite

The system has been verified using a comprehensive test suite in strict warning mode:

```bash
============================= test session starts ==============================
platform darwin -- Python 3.13.7, pytest-9.0.3, pluggy-1.6.0
collected 6 items                                                              

tests/test_api.py::test_health_check PASSED                              [ 16%]
tests/test_api.py::test_list_platforms_unauthorized PASSED               [ 33%]
tests/test_api.py::test_list_platforms_authorized PASSED                 [ 50%]
tests/test_api.py::test_get_platform_schema PASSED                       [ 66%]
tests/test_api.py::test_campaign_data_unauthorized PASSED                [ 83%]
tests/test_api.py::test_batch_data_authorized PASSED                     [100%]

============================== 6 passed in 8.60s ===============================
```

---

## 6. Detailed Configuration Reference

The following environment variables are supported in the `.env` file for full system configuration and platform authentication fallbacks.

### Core API & Database Sink
- `API_KEY`: Secret token for `X-API-Key` header authentication.
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to the service account JSON file for Firestore multi-tenancy.
- `ENABLE_BIGQUERY_SINK`: Boolean (`True`/`False`) to enable automated BigQuery archiving.
- `BIGQUERY_PROJECT_ID`: Target GCP project ID for BigQuery.
- `BIGQUERY_DATASET_ID`: Target BigQuery dataset ID (defaults to `marketing_data`).
- `BIGQUERY_TABLE_ID`: Target BigQuery table ID (defaults to `raw_campaign_data`).

### Platform Credentials (Global Fallbacks)
While per-tenant credentials should be dynamically resolved via Firestore, the following environment variables can be used as system-wide fallback credentials:
- **Meta (Ads & Organic)**: `META_ACCESS_TOKEN`
- **Google Ads**: `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, `GOOGLE_ADS_CLIENT_SECRET`, `GOOGLE_ADS_REFRESH_TOKEN`
- **TikTok Ads**: `TIKTOK_ADS_ACCESS_TOKEN`, `TIKTOK_ADS_APP_ID`, `TIKTOK_ADS_SECRET`
- **TikTok Organic**: `TIKTOK_ACCESS_TOKEN`
- **LinkedIn (Ads & Organic)**: `LINKEDIN_ACCESS_TOKEN`
- **X (Twitter) Ads**: `X_ADS_ACCESS_TOKEN`
- **X (Twitter) Organic**: `X_BEARER_TOKEN`
- **YouTube**: `YOUTUBE_API_KEY`
- **Google Play**: `GOOGLE_PLAY_SERVICE_ACCOUNT_JSON`
- **Apple App Store Connect**: `APPLE_KEY_ID`, `APPLE_ISSUER_ID`, `APPLE_PRIVATE_KEY_PATH`
- **Apple Search Ads**: `APPLE_ADS_ACCESS_TOKEN`

---

## 7. Multi-Tenant Request Schema

All data retrieval requests submitted to the single-platform endpoint (`/api/v1/campaign-data`) or within a batch request (`/api/v1/batch`) must conform to the following schema.

### `DataRequest` Fields

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `platform` | Enum | **Yes** | Target marketing platform. Must be one of the supported enum values (e.g., `meta_ads`, `ga4`, `google_play`). |
| `start_date` | Date | **Yes** | Start date for data retrieval range in `YYYY-MM-DD` format. |
| `end_date` | Date | **Yes** | End date for data retrieval range in `YYYY-MM-DD` format. |
| `metrics` | List[str] | **Yes** | List of platform-specific metrics to retrieve (must contain at least one metric). |
| `client_id` | String | **Yes** | Unique identifier of the agency's client/tenant. Used for secure credential lookup. |
| `user_id` | String | **Yes** | Unique identifier of the operator or API user initiating the request. |
| `account_id` | String | **Yes** | Primary platform identifier (e.g., Facebook Ad Account ID, GA4 Property ID, LinkedIn Organization ID). |
| `credentials` | Dict | No | Optional dictionary of on-the-fly credentials to bypass Firestore and environment variables. |
| `post_id` | String | No | Specific content ID to query (only applicable for organic/social platforms). |
| `video_id` | String | No | Specific video identifier (only applicable for YouTube or TikTok). |
| `app_id` | String | No | App package name or ID (only applicable for Google Play or Apple App Store). |

### Pydantic Validation Constraints
1. **Date Validation**: The Pydantic model automatically enforces that `start_date <= end_date`. If `start_date > end_date`, it raises a validation error.
2. **Metrics Validation**: The list of metrics must be non-empty (`min_length=1`).
3. **Strict Enums**: The `platform` field must match one of the predefined values in the `Platform` enum.

