# Inhaus Marketing Data API v5.0

Unified, multi-tenant API connector for 14 marketing and analytics platforms. Designed for AI agents, performance agencies, and automated reporting.

## Architecture

This project follows a modular, **multi-tenant** architecture designed for **reliability**, **observability**, and **agentic tool calling**.

- **`app/main.py`**: FastAPI entry point, identity resolution, and routing.
- **`app/connectors/`**: Individual platform connectors implementing a `BaseConnector` interface.
- **`app/models/`**: Pydantic models for request/response validation and normalization.
- **`app/services/`**: Internal services like `CredentialStore` and `Dispatcher`.
- **`dashboard.py`**: Streamlit-based data visualization and interactive dashboard.
- **`web_ui/`**: Flutter web application for frontend interaction.

## Multi-Tenancy

The API supports dynamic, per-request identity resolution. Credentials are resolved based on `client_id`, `user_id`, and `account_id` from the request, prioritizing secure storage (Firestore) over environment variables.

See [llms.md](llms.md) for detailed technical context on the credential resolution logic and [production_refactoring.md](docs/production_refactoring.md) for a comprehensive walkthrough of the production-grade updates.

## Key Features

- **Multi-Tenant**: Native support for managing hundreds of client accounts and social profiles.
- **Agent-Ready**: Structured JSON responses with `request_id`, `timestamp`, and detailed metadata.
- **Reliable**: Automatic retries with exponential backoff via `tenacity`.
- **Async-Safe**: Synchronous SDK calls are offloaded to a thread pool.
- **Secure**: API Key authentication and per-user credential isolation.

## Supported Platforms

| Platform | Type | Status |
|---|---|---|
| Meta Ads | Ads | ✅ |
| Meta Organic | Organic | ✅ |
| Google Ads | Ads | ✅ |
| GA4 | Analytics | ✅ |
| Google Search Console | Search analytics (read-only) | ✅ |
| TikTok Ads | Ads | ✅ |
| TikTok Organic | Organic | ✅ |
| LinkedIn Ads | Ads | ✅ |
| LinkedIn Organic | Organic | ✅ |
| X (Twitter) | Ads/Organic | ✅ |
| YouTube | Organic | ✅ |
| Google Play | App Store | ✅ |
| Apple App Store | App Store | ✅ |
| Apple Search Ads | Ads | ✅ |
| Threads | Organic | ✅ |

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Set your API_KEY and BigQuery sink settings
   ```

3. **Run Backend (FastAPI)**:
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Run Dashboard (Streamlit)**:
   ```bash
   streamlit run dashboard.py
   ```

5. **Run Web UI (Flutter)**:
   ```bash
   cd web_ui
   flutter pub get
   flutter run -d chrome
   ```

## API Endpoints

- `GET /health`: Deep health check and platform readiness.
- `GET /api/v1/platforms`: List available platforms.
- `POST /api/v1/campaign-data`: Fetch data for a single platform (requires `client_id`, `user_id`, `account_id`).
- `POST /api/v1/batch`: Fetch data for multiple platforms concurrently.
- `POST /api/v1/comments`: Fetch comments for a specific post (Meta Ads, Meta Organic, or Threads).

## Connect Google Search Console

Search Console uses the existing Google OAuth client, with a separate **read-only** consent. Linking Search Console inside GA4 does not authorize this API to read search queries.

1. Enable the [Search Console API](https://developers.google.com/webmaster-tools/v1/prereqs) in the Google Cloud project that owns the OAuth client. Configure the existing `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (or Google Ads fallback) and registered `GOOGLE_OAUTH_REDIRECT_URI` ending in `/api/v1/oauth/google-callback`.
2. Request `GET /api/v1/oauth/authorize?platform=search_console&client_id=client_1&redirect_url=http%3A%2F%2Flocalhost%3A8501`, then open the returned `authorization_url`. The account owner must approve `https://www.googleapis.com/auth/webmasters.readonly`. Existing GA4, Google Ads and YouTube connections are unchanged.
3. Call `GET /api/v1/oauth/connections?platform=search_console&client_id=client_1` with `X-API-Key` and use a returned `account_id` exactly. It is a site URL such as `https://www.example.com/` or `sc-domain:example.com`, **not a GA4 property ID**.

### Top 10 search queries

```bash
curl "$API_BASE_URL/api/v1/search-console/query" \
  -H "X-API-Key: $API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "client_1",
    "account_id": "sc-domain:example.com",
    "start_date": "2026-08-01",
    "end_date": "2026-08-31",
    "dimensions": ["query"],
    "row_limit": 10
  }'
```

The response preserves Google's `rows` (`keys`, `clicks`, `impressions`, `ctr`, `position`) and aggregation metadata. Use `dimensions: ["country"]` for countries, `["page"]` for pages, or `[]` for period totals. Add `"query": "nutri"` for the **exact, case-sensitive** query `nutri`; it does not include `nutri leche` or `nutrileche`. Query other exact names separately.

- Results are ordered by clicks, not impressions; the endpoint does not claim an impressions-ranked top 10. Use `start_row` to paginate and `row_limit` up to 25,000. Google's source can omit low-volume/anonymized queries, so query rows are not a complete search census.
- Requests use web search and finalized data. Search Console dates use Pacific Time; do not equate its clicks with GA4 sessions or sum a top 10 to derive period totals.
- The platform also supports `/api/v1/campaign-data` as `search_console`, with metrics `clicks`, `impressions`, `ctr`, `position`, optional `dimensions`, `limit`, and `filters: {"query": "nutri"}`. Prefer the dedicated endpoint for native totals and metadata.

A permission error requires checking site access, API enablement and read-only consent—not reconnecting GA4. No new SDK is required. Deploy the updated backend before using these endpoints on an existing hosted service.

## MCP Server (Agent Tool Calling)

The API exposes a **Model Context Protocol (MCP)** server so AI agents can interact with all 15 marketing platforms via structured tool calls over stdio transport.

### Setup

```bash
# Create a virtual environment and install dependencies
uv venv .venv
uv pip install -r requirements.txt
```

### Running the MCP Server

```bash
# Standalone (stdio transport)
.venv/bin/python -m app.mcp
```

The server is also registered in `mcp_config.json` for automatic discovery by IDE agents.

### Available MCP Tools

| Tool | Description |
|---|---|
| `check_api_health` | Check API status and per-platform connectivity |
| `list_platforms` | Discover all 15 platforms, their types, and available metrics |
| `get_platform_schema` | Get the full metric/dimension schema for a platform |
| `get_marketing_data` | Fetch campaign data from a single platform |
| `get_batch_marketing_data` | Fetch data from multiple platforms concurrently |
| `compare_platforms` | Cross-platform metric comparison with aggregated totals |
| `list_available_metrics` | Quick list of valid metric names for a platform |
| `summarize_performance` | High-level performance summary with auto-selected metrics |
| `get_comments` | Fetch comments/replies for a specific post (Meta Ads, Meta Organic, or Threads) |