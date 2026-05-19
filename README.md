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