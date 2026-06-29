# Inhaus Marketing API — MCP Tool Reference

Complete reference for all MCP tools exposed by the Inhaus Marketing Data API.

---

## Quick Reference

| Tool | Purpose | Requires Account ID |
|------|---------|:-------------------:|
| `check_api_health` | Verify API is running | ❌ |
| `list_platforms` | Discover available platforms | ❌ |
| `get_platform_schema` | Get native metric/dimension names | ❌ |
| `get_marketing_data` | Fetch data from one platform | ✅ |
| `get_batch_marketing_data` | Fetch data from multiple platforms | ✅ |
| `compare_platforms` | Side-by-side platform comparison | ✅ |
| `list_available_metrics` | Quick metric name lookup | ❌ |
| `summarize_performance` | Auto-summarize platform KPIs | ✅ |
| `get_comments` | Fetch post comments/replies | ✅* |
| `validate_request` | Dry-run metric validation | ❌ |
| `get_metric_compatibility` | Cross-platform metric support | ❌ |

\* `account_id` is optional for `get_comments`.

---

## Understanding Metric Types

### Native Metrics
Platform-specific metric names as defined by each platform's API.
- Use with: `get_marketing_data`, `get_batch_marketing_data`
- Discover via: `get_platform_schema`, `list_available_metrics`
- Example: `cost_micros` (Google Ads), `activeUsers` (GA4), `view_count` (TikTok)

### Generic Metrics
Standardized metric names that work across all platforms.
- Use with: `summarize_performance`, `compare_platforms`
- Discover via: `get_metric_compatibility`
- Automatically translated to native names per platform

| Generic Name | Description |
|-------------|-------------|
| `impressions` | Content views/displays |
| `clicks` | Link/ad clicks |
| `spend` | Ad spend in currency |
| `conversions` | Goal completions |
| `reach` | Unique users reached |
| `engagement` | Interactions (likes, comments, etc.) |
| `followers` | New followers/subscribers |
| `sessions` | Website/app sessions |
| `users` | Active users |
| `pageviews` | Page/screen views |
| `bounce_rate` | Session bounce rate |
| `downloads` | App installs/downloads |
| `ratings` | App ratings |

---

## Platform-Specific Parameters

### Parameter Validation Rules & Silent Error Prevention
Every call to `get_marketing_data` undergoes platform-specific parameter validation to prevent silent failures and return immediate, actionable feedback:
1. **Allowed Parameters Enforcement**: Only parameters explicitly supported by the connector's upstream API (`post_id`, `video_id`, `app_id`) can be passed. If an unsupported parameter is passed (e.g., passing `video_id` to `meta_ads`), the call is rejected immediately with a clear error: `El parámetro 'video_id' no es válido para la plataforma meta_ads`.
2. **Account ID Format Enforcement**: The `account_id` is validated against platform conventions (e.g., `google_ads` checks for 10-digit formats; `meta_ads` checks for `act_` prefixes; `ga4` checks for property ID formats).

### `get_marketing_data` — Required Parameters by Platform

| Platform | `account_id` Format & Details | Examples | Allowed Optional Params |
|----------|-------------------------------|----------|-------------------------|
| `meta_ads` | Ad Account ID (starts with `act_` or is numeric) | `act_1234567890123` or `1234567890123` | `post_id` |
| `meta_organic` | Facebook Page ID or IG Business ID (numeric) | `123456789012` | `post_id` (Post/Media ID) |
| `google_ads` | Customer ID (10 digits, optional dashes) | `123-456-7890` or `1234567890` | — |
| `ga4` | Property ID (numeric, optional `properties/` prefix) | `properties/123456789` or `123456789` | — |
| `tiktok_ads` | Advertiser ID (numeric string) | `7123456789012345678` | — |
| `tiktok_organic` | Creator Open ID / Business ID | `open_id_xxxxxxxxxx` | `video_id` |
| `linkedin_ads` | Sponsored Ad Account ID (numeric or URN) | `500000000` | — |
| `linkedin_organic` | Organization Page ID (numeric or URN) | `urn:li:organization:12345` or `12345` | `post_id` |
| `x_ads` | Twitter Ads Account ID (numeric) | `18266800` | — |
| `x_organic` | Twitter Username or numeric ID | `inhaus_mktg` | `post_id` (Tweet ID) |
| `youtube` | Channel ID (starts with `UC`) | `UCxxxxxxxxxxxxxxxxxxxxxx` | `video_id` (Video ID) |
| `google_play` | Package name of the app (reverse domain notation) | `com.example.my_app` | `app_id` (Package name) |
| `apple_app_store` | App Store App ID (numeric string) | `123456789` | `app_id` (App ID) |
| `apple_ads` | Search Ads Organization ID (numeric) | `12345678` | — |
| `threads` | Threads User ID or `me` | `me` or `12345678` | `post_id` (Media ID) |

### Optional/Platform-Specific Query Parameters Support

Below is a quick reference table showing which platforms support or require specific optional parameters (`post_id`, `video_id`, `app_id`) in `get_marketing_data`:

| Platform | Supports `post_id` | Supports `video_id` | Supports `app_id` |
|----------|:-----------------:|:------------------:|:----------------:|
| `meta_ads` | Optional (ad creative level) | No | No |
| `meta_organic` | Optional (IG media/Page post) | No | No |
| `linkedin_organic` | Optional (Share ID) | No | No |
| `x_organic` | Optional (Tweet ID) | No | No |
| `youtube` | No | Optional (Video ID) | No |
| `tiktok_organic` | No | Optional (Video ID) | No |
| `threads` | Optional (Threads Media ID) | No | No |
| `google_play` | No | No | Optional (Package name) |
| `apple_app_store` | No | No | Optional (App ID) |
| All others | No | No | No |

---


## Metric Compatibility Table

Which generic metrics work on which platforms:

| Generic | meta_ads | google_ads | tiktok_ads | linkedin_ads | apple_ads | x_ads | ga4 | youtube | tiktok_org | linkedin_org | x_org | threads | meta_org | play | apple_store |
|---------|:--------:|:----------:|:----------:|:------------:|:---------:|:-----:|:---:|:-------:|:----------:|:------------:|:-----:|:-------:|:--------:|:----:|:-----------:|
| impressions | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| clicks | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| spend | ✅ | ✅* | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| conversions | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| reach | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| engagement | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| followers | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| sessions | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| users | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| pageviews | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| bounce_rate | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| downloads | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| ratings | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

\* Google Ads `spend` is stored as `cost_micros` (divide by 1,000,000). The API handles this conversion automatically in `summarize_performance` and `compare_platforms`.

---

## Comment Support by Platform

| Platform | Supported | Comment Source | `post_id` format |
|----------|:---------:|---------------|-----------------|
| `meta_ads` | ✅ | Ad creative's effective post | `effective_object_story_id` |
| `meta_organic` | ✅ | FB Page posts or IG media | FB post ID or IG media ID |
| `threads` | ✅ | Thread post replies | Threads media ID |
| `youtube` | ✅ | Video comment threads | YouTube video ID |
| `x_organic` | ✅ | Tweet replies (conversation) | Tweet ID |
| All others | ❌ | — | — |

---

## Usage Examples

### 1. Quick health check
```json
{"tool": "check_api_health", "args": {"deep": true}}
```

### 2. Discover platforms and their metrics
```json
{"tool": "list_platforms", "args": {}}
```

### 3. Fetch Meta Ads campaign data
```json
{
  "tool": "get_marketing_data",
  "args": {
    "platform": "meta_ads",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "metrics": ["impressions", "clicks", "spend", "conversions"],
    "client_id": "client_123",
    "user_id": "user_456",
    "account_id": "act_789"
  }
}
```

### 4. Quick performance summary (uses generic metrics automatically)
```json
{
  "tool": "summarize_performance",
  "args": {
    "platform": "google_ads",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "client_id": "client_123",
    "user_id": "user_456",
    "account_id": "1234567890"
  }
}
```
Response will use generic names: `{"impressions": 50000, "clicks": 2500, "spend": 1250.50, "conversions": 150}`

### 5. Compare ads platforms side-by-side
```json
{
  "tool": "compare_platforms",
  "args": {
    "platforms": ["meta_ads", "google_ads", "tiktok_ads"],
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "metrics": ["impressions", "clicks", "spend"],
    "client_id": "client_123",
    "user_id": "user_456",
    "account_ids": {
      "meta_ads": "act_111",
      "google_ads": "2222222222",
      "tiktok_ads": "3333333333"
    }
  }
}
```

### 6. Validate metrics before fetching
```json
{
  "tool": "validate_request",
  "args": {
    "platform": "ga4",
    "metrics": ["impressions", "sessions", "users"],
    "use_generic_names": true
  }
}
```
Response: `{"valid": false, "invalid_metrics": ["impressions"], "translations": {"impressions": null, "sessions": "sessions", "users": "activeUsers"}}`

### 7. Fetch YouTube video comments
```json
{
  "tool": "get_comments",
  "args": {
    "platform": "youtube",
    "post_id": "dQw4w9WgXcQ",
    "client_id": "client_123",
    "user_id": "user_456"
  }
}
```

---

## Error Codes

| Code | Meaning | Retryable |
|------|---------|:---------:|
| `AUTH_ERROR` | Invalid or expired credentials | ❌ |
| `RATE_LIMIT` | API rate limit exceeded | ✅ |
| `INVALID_REQUEST` | Bad parameters or metrics | ❌ |
| `INVALID_METRIC` | Metric name not recognized | ❌ |
| `CONNECTIVITY` | Network connection failed | ✅ |
| `TIMEOUT` | Request timed out | ✅ |
| `API_ERROR` | Generic upstream API error | ✅ |
| `NOT_IMPLEMENTED` | Connector not available | ❌ |
| `UNSUPPORTED` | Feature not available for platform | ❌ |
