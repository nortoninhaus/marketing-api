# Inhaus Marketing Data API v5.0

Unified, multi-tenant API connector for 14 marketing and analytics platforms. Designed for AI agents, performance agencies, and automated reporting.

## Architecture

This project follows a modular, **multi-tenant** architecture designed for **reliability**, **observability**, and **agentic tool calling**.

- **`app/main.py`**: FastAPI entry point, identity resolution, and routing.
- **`app/connectors/`**: Individual platform connectors implementing a `BaseConnector` interface.
- **`app/models/`**: Pydantic models for request/response validation and normalization.
- **`app/services/`**: Internal services like `CredentialStore` and `Dispatcher`.

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

3. **Run locally**:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

- `GET /health`: Deep health check and platform readiness.
- `GET /api/v1/platforms`: List available platforms.
- `POST /api/v1/campaign-data`: Fetch data for a single platform (requires `client_id`, `user_id`, `account_id`).
- `POST /api/v1/batch`: Fetch data for multiple platforms concurrently.
- `POST /api/v1/comments`: Fetch comments for a specific post (Meta Ads, Meta Organic, or Threads).

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