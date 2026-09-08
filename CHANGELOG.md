# Changelog

All notable changes to the **Inhaus Marketing Data API** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [5.3.0] - 2026-09-07

### Changed
- **Streamlit Dashboard Modularization**: Refactored `dashboard.py` from 3,945 lines down to 745 lines (~81% reduction), turning it into a pure high-level orchestrator for session state, authentication, sidebar controls, query caching, and view routing.
- **Dedicated Presentation Views (`dashboard/views/`)**:
  - `dashboard/views/meta_ads.py`: Isolated Meta Ads (Facebook/Instagram) analytics, demographic/geographic breakdown charts, creative rankings, and detailed export workflows.
  - `dashboard/views/generic_ads.py`: Isolated multi-platform rendering for Google Ads, TikTok Ads, LinkedIn, etc., including automatic campaign type classification.
- **Isolated Styles & Client Scripts (`dashboard/styles.py`)**: Extracted over 1,100 lines of inline CSS, light/dark themes, and View Transition JavaScript into `inject_dashboard_styles()`.
- **Decoupled User Onboarding (`dashboard/onboarding.py`)**: Extracted first-run guide dialogs and client-side cookie/localStorage synchronization.
- **Consolidated Export & Reporting Engine (`dashboard/reporting.py`)**: Centralized HTML template generation (`template_report_html`) and segmented PDF canvas capture (`segmented_pdf_download_html`).
- **Test Suite Alignment**: Updated `tests/test_dashboard_exports.py` and `tests/test_dashboard_ui.py` to inspect modular view and style sources, maintaining 100% green test pass rates.

## [5.2.0] - 2026-09-02

### Added
- **TikTok Ads Multi-Level Reporting & Metadata Mapping**: Automated campaign metadata fetching via `/v1.3/campaign/get/`, adgroup resolution via `/v1.3/adgroup/get/`, and ad name mapping via `/v1.3/ad/get/`. Dynamically selects reporting data level (`AUCTION_AD`, `AUCTION_ADGROUP`, or `AUCTION_CAMPAIGN`) according to requested dimensions.
- **TikTok Ads Metrics & Alias Normalization**: Added support and schema definitions for engagement metrics (`follows`, `profile_visits`, `likes`, `comments`, `shares`, `average_video_play`, `average_video_play_per_user`) with metric aliasing for video views and conversions.
- **Google Ads Extended Metrics & Dimensions**: Added support for interaction rates, video view quartiles, conversion values, and active view metrics. Extracted campaign channel type, status, and bidding strategy dimensions into `CampaignData.dimensions`.

## [5.1.0] - 2026-07-21

### Added
- **Google Ads MCC Manager Hierarchy Discovery**: Automated GAQL discovery of all child ad accounts and sub-managers under top-level MCC accounts via `customer_client`.
- **Descriptive Name Resolution**: Automatically resolves human-readable names for all discovered Google Ads accounts (e.g., "Banco del Austro", "Bajaj Ecuador").

### Fixed
- **Google OAuth `redirect_uri_mismatch` (Error 400)**: Configured `GOOGLE_OAUTH_REDIRECT_URI` and dynamic URI building to match Google Cloud Console authorized redirect URIs.
- **MCC Child Account Credential Resolution**: Automatically attaches `login_customer_id` metadata to child accounts inside Firestore `oauth_connections` for seamless query execution.

## [5.0.0] - 2026-07-13

### Added
- **Model Context Protocol (MCP)**: Native stdio-based MCP server in `app/mcp.py` to allow agentic tool calling with 9 core tools (`get_marketing_data`, `get_batch_marketing_data`, `compare_platforms`, etc.).
- **New Platform Connectors**: Exposes connection wrappers for Threads, Pinterest, Spotify, Shopify, and GoHighLevel (GHL).
- **Proactive Token Refresh**: Automatically exchanges short-lived Meta and Threads tokens for long-lived ones if they are within 15 days of expiration.
- **Async Firestore Support**: Integrates `AsyncClient` for credential management in `CredentialStore` to maximize concurrent request throughput.
- **BigQuery Archiver Sink**: Automated logging of normalized request-response payloads to a centralized Google BigQuery data warehouse.
- **Client & OAuth Routers**: Integrated FastAPI routes for client registration and OAuth callbacks (`routers/clients.py` and `routers/oauth.py`).

### Changed
- **Credential Hierarchy**: Standardized all connector classes to implement a unified signature (`get_credentials(request)`) prioritizing Request-level parameters -> Firestore Vault -> `.env` Fallbacks.
- **Date Handling**: Migrated deprecated UTC time helpers to timezone-aware datetime objects (`datetime.now(timezone.utc)`) to satisfy Python 3.12+ warnings.
- **API Lifecycle**: Refactored startup/shutdown routines to use FastAPI `lifespan` context managers.
- **Streamlit Dashboard**: Expanded to dynamically read from the new multi-tenant API.

### Fixed
- **State Invalidation (Dart App)**: Corrected caching issues in the frontend dashboard settings screens. OAuth redirect callbacks now trigger automated resets of connections for all platforms.
- **Active Account Auto-selection**: Resolved query page initialization failure by dynamically populating dropdown selectors with the user's first active connected client ID instead of static mocks.
- **Organic Facebook Page Token Bypass**: Excluded indefinite/permanent Facebook Page organic tokens from the auto-refresh loop.
