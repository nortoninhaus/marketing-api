# Product Requirements Document (PRD): Inhaus Marketing Data API

## 1. Executive Summary
The Inhaus Marketing Data API is a unified, high-performance, multi-tenant gateway that abstracts the complexities of interfacing with over 14 major marketing, analytics, and social platforms. Designed for both traditional reporting applications (e.g., Streamlit, Flutter dashboards) and AI-driven workflows, the platform provides standardized JSON interfaces, automated token management, and built-in Model Context Protocol (MCP) server endpoints to allow autonomous AI agents to query cross-channel performance metrics seamlessly.

---

## 2. Product Objectives & Value Proposition
- **Unified Abstraction**: Eliminate the friction of integration by exposing a single standardized request format (`DataRequest`) that translates generic metrics (`impressions`, `clicks`, `spend`, `conversions`) to native API endpoints.
- **Agentic Readiness**: Native support for Model Context Protocol (MCP) enabling AI agents to discover, schema-validate, fetch, and compare marketing metrics across multiple channels in a single tool call.
- **Enterprise Multi-Tenancy**: Safely store, isolate, and dynamically retrieve client credentials on a per-request basis utilizing Google Cloud Firestore, prioritizing request-level overrides.
- **Resilient & Async-First**: Keep operations non-blocking using FastAPI, threads for synchronous SDK wrappers, and automated retry mechanisms (via `tenacity`) with exponential backoff.

---

## 3. Supported Integrations
The API implements specialized connector classes under `app/connectors/` for the following platforms:

| Platform Category | Platforms | Status |
| :--- | :--- | :--- |
| **Paid Advertising** | Meta Ads, Google Ads, TikTok Ads, LinkedIn Ads, X (Twitter) Ads, Apple Search Ads, Spotify Ads, Pinterest Ads | ✅ Active |
| **Organic & Social** | Meta Organic (Facebook/Instagram), TikTok Organic, LinkedIn Organic, X (Twitter) Organic, YouTube, Threads, Pinterest Organic | ✅ Active |
| **App Stores** | Google Play Console, Apple App Store Connect | ✅ Active |
| **Analytics & Web** | Google Analytics 4 (GA4) | ✅ Active |
| **CRM & E-commerce**| Shopify, GoHighLevel (GHL) | ✅ Active |

---

## 4. Key Functional Requirements

### 4.1. Dynamic Credential Resolution
- Resolve credentials per-request using a three-tier hierarchy:
  1. **Inline Credentials**: Passed directly in the payload for immediate access/testing.
  2. **Firestore Vault**: Asynchronously fetched from a multi-tenant collection matching the `client_id`.
  3. **Global Defaults**: System-level fallbacks defined in environment variables (`.env`).
- Automatic refresh of long-lived access tokens (Meta, Threads) if they are within 15 days of expiration.
- Skip refresh checks for permanent organic page access tokens.

### 4.2. Schema Discovery and Validation
- **GET `/api/v1/platforms`**: Exposes supported platforms, active configurations, and descriptors.
- **GET `/api/v1/schema/{platform}`**: Dynamically returns structural parameters and lists of valid metrics and dimensions.
- Native parameter sanitization rejects invalid query combinations (e.g., passing `video_id` to Google Ads) before invoking upstream endpoints, avoiding silent API errors.

### 4.3. High-Concurrency Batch Queries
- **POST `/api/v1/batch`**: Execute concurrent platform fetches using `asyncio.gather` and background worker threads.
- **Partial Failure Resiliency**: If one platform fails (e.g., due to an expired token), return successful datasets alongside structured error payloads with a `"status": "partial"` response code.

### 4.4. Model Context Protocol (MCP) Support
- Expose native stdio transport for MCP host systems (e.g., Cursor, Claude Desktop, Antigravity).
- Provide tools:
  - `check_api_health` / `list_platforms` / `get_platform_schema`
  - `get_marketing_data` / `get_batch_marketing_data`
  - `compare_platforms` / `summarize_performance`
  - `get_comments` (Meta Ads, Meta Organic, Threads, YouTube, X)

### 4.5. Data Archiving (BigQuery Sink)
- Optional automated synchronization of normalized marketing payloads to a Google BigQuery data warehouse.
- Controlled via `ENABLE_BIGQUERY_SINK` toggle.

---

## 5. Non-Functional Requirements
- **Security**: Mandatory `X-API-Key` validation on all REST endpoints. Strict credential isolation per client tenant.
- **Performance**: Thread pool offloading for synchronous blocking client SDK code to prevent main-loop starvation.
- **Scalability**: Stateless architecture containerized via `Dockerfile` and configured for serverless scaling (e.g., Google Cloud Run).
