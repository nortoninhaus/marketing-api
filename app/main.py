"""
Main FastAPI application.
"""
import time as _time

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import List
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle for the application."""
    # Startup
    from app.config import settings as _settings
    from app.services.bigquery_sink import bq_sink as _bq
    if _settings.enable_bigquery_sink:
        logging.getLogger(__name__).info("Initializing BigQuery sink...")
        await _bq.ensure_dataset_and_table()
    yield
    # Shutdown (cleanup if needed)

from app.config import settings
from app.models.requests import DataRequest, Platform, BatchDataRequest, CommentsRequest, TikTokProxyRequest, TikTokOrganicProxyRequest
from app.models.responses import DataResponse, BatchDataResponse, HealthResponse, ErrorDetail, PlatformInfo, SchemaResponse
from app.middleware.auth import verify_api_key
from app.services.dispatcher import dispatcher
from app.services.bigquery_sink import bq_sink

# Import and register connectors
from app.connectors.meta import MetaAdsConnector, MetaOrganicConnector
from app.connectors.google_ads import GoogleAdsConnector
from app.connectors.ga4 import GA4Connector
from app.connectors.tiktok import TikTokAdsConnector, TikTokOrganicConnector
from app.connectors.linkedin import LinkedInAdsConnector, LinkedInOrganicConnector
from app.connectors.x_twitter import XAdsConnector, XOrganicConnector
from app.connectors.youtube import YouTubeConnector
from app.connectors.google_play import GooglePlayConnector
from app.connectors.apple import AppleAppStoreConnector, AppleAdsConnector
from app.connectors.threads import ThreadsConnector
from app.connectors.spotify import SpotifyAdsConnector
from app.connectors.pinterest import PinterestAdsConnector, PinterestOrganicConnector
from app.connectors.shopify import ShopifyConnector

# Configure root logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Register available connectors
dispatcher.register(Platform.META_ADS, MetaAdsConnector())
dispatcher.register(Platform.META_ORGANIC, MetaOrganicConnector())
dispatcher.register(Platform.GOOGLE_ADS, GoogleAdsConnector())
dispatcher.register(Platform.GA4, GA4Connector())
dispatcher.register(Platform.TIKTOK_ADS, TikTokAdsConnector())
dispatcher.register(Platform.TIKTOK_ORGANIC, TikTokOrganicConnector())
dispatcher.register(Platform.LINKEDIN_ADS, LinkedInAdsConnector())
dispatcher.register(Platform.LINKEDIN_ORGANIC, LinkedInOrganicConnector())
dispatcher.register(Platform.X_ADS, XAdsConnector())
dispatcher.register(Platform.X_ORGANIC, XOrganicConnector())
dispatcher.register(Platform.YOUTUBE, YouTubeConnector())
dispatcher.register(Platform.GOOGLE_PLAY, GooglePlayConnector())
dispatcher.register(Platform.APPLE_APP_STORE, AppleAppStoreConnector())
dispatcher.register(Platform.APPLE_ADS, AppleAdsConnector())
dispatcher.register(Platform.THREADS, ThreadsConnector())
dispatcher.register(Platform.SPOTIFY_ADS, SpotifyAdsConnector())
dispatcher.register(Platform.PINTEREST_ADS, PinterestAdsConnector())
dispatcher.register(Platform.PINTEREST_ORGANIC, PinterestOrganicConnector())
dispatcher.register(Platform.SHOPIFY, ShopifyConnector())

app = FastAPI(
    title="Inhaus Marketing Data API",
    description="Agent-ready API for multi-platform marketing data.",
    version="5.0.0",
    lifespan=lifespan
)

# Allowed CORS origins — add your dashboard / frontend domains here
_cors_origins = [
    "https://inhaus-marketing-api-btdf7nijqa-uc.a.run.app",
    "https://inhaus-marketing-api.web.app",
    "https://inhaus-marketing-api.firebaseapp.com",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://inhaus-marketing-api--[a-z0-9-]+\.web\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register OAuth router
from app.routers.oauth import router as oauth_router
app.include_router(oauth_router)

# Register SOTA router
from app.routers.sota import router as sota_router
app.include_router(sota_router)

# Register Clients router
from app.routers.clients import router as clients_router
app.include_router(clients_router)

# Mount FastMCP server and protect it with middleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.mcp import mcp

class InhausASGIMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        # 1. MCP Authentication (matches /mcp or /mcp_http)
        if path.startswith("/mcp") or path.startswith("/mcp_http"):
            # Exclude /messages subpath from API key check since standard MCP SSE clients
            # might not copy query parameters or custom headers on POST tool calls.
            # The session_id itself serves as the secure authorization token for messages.
            if "/messages" not in path:
                headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
                api_key = headers.get("x-api-key")
                if not api_key:
                    auth_header = headers.get("authorization")
                    if auth_header and auth_header.lower().startswith("bearer "):
                        api_key = auth_header.split(" ", 1)[1]
                if not api_key:
                    from urllib.parse import parse_qs
                    query_string = scope.get("query_string", b"").decode("latin1")
                    query_params = parse_qs(query_string)
                    api_key = query_params.get("api_key", [None])[0]

                if api_key != settings.api_key:
                    await send({
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [
                            (b"content-type", b"application/json"),
                        ]
                    })
                    import json
                    await send({
                        "type": "http.response.body",
                        "body": json.dumps({"detail": "Invalid API Key"}).encode("utf-8"),
                        "more_body": False
                    })
                    return

        # 2. Latency logging (matches /api/, /mcp, /mcp_http)
        if path.startswith("/api/") or path.startswith("/mcp") or path.startswith("/mcp_http"):
            import time as _time
            start = _time.monotonic()
            
            async def wrapped_send(message):
                if message["type"] == "http.response.start":
                    elapsed_ms = (_time.monotonic() - start) * 1000
                    status_code = message.get("status", 200)
                    logger.info(f"[HTTP] {method} {path} → {status_code} ({elapsed_ms:.0f}ms)")
                await send(message)
                
            await self.app(scope, receive, wrapped_send)
        else:
            await self.app(scope, receive, send)

app.add_middleware(InhausASGIMiddleware)

# Mount SSE transport under /mcp (exposing /mcp/sse and /mcp/messages)
app.mount("/mcp", mcp.sse_app())
logger.info("MCP mounted with SSE transport at /mcp/sse")

# Also mount Streamable HTTP transport under /mcp_http
try:
    app.mount("/mcp_http", mcp.streamable_http_app())
    logger.info("MCP mounted with Streamable HTTP transport at /mcp_http")
except AttributeError:
    pass

# Import comment models
from app.models.responses import CommentsResponse, CommentData

@app.get("/health", response_model=HealthResponse)
async def health_check(deep: bool = False):
    """Exposes platform readiness and optional deep connectivity tests."""
    configured = 0
    details = {}
    
    for p in Platform:
        is_ready = settings.is_platform_configured(p.value)
        
        status = "configured" if is_ready else "not_configured"
        
        if is_ready and deep:
            try:
                connector = dispatcher.get_connector(p)
                # Run ping in thread
                connected = await asyncio.to_thread(connector.ping)
                status = "healthy" if connected else "connectivity_issue"
            except Exception as e:
                logger.error(f"Ping failed for {p.value}: {e}")
                status = "unhealthy"
                
        details[p.value] = status
        if is_ready:
            configured += 1

    return HealthResponse(
        status="healthy" if configured > 0 else "unconfigured",
        version="5.0.0",
        platforms_configured=configured,
        details=details
    )

PLATFORM_API_VERSIONS = {
    "meta_ads": "v19.0",
    "meta_organic": "v19.0",
    "google_ads": "v16",
    "ga4": "v1beta",
    "tiktok_ads": "v1.3",
    "tiktok_organic": "v1.3",
    "linkedin_ads": "202405",
    "linkedin_organic": "202405",
    "x_ads": "v12",
    "x_organic": "v2",
    "youtube": "v3",
    "google_play": "v3",
    "apple_app_store": "v1.6",
    "apple_ads": "v5",
    "threads": "v1.0",
    "spotify_ads": "v3",
    "pinterest_ads": "v5",
    "pinterest_organic": "v5",
    "shopify": "2024-04"
}

@app.get("/api/v1/platforms", response_model=List[PlatformInfo])
async def list_platforms(api_key: str = Depends(verify_api_key)):
    """Discovery endpoint for agents to list available platforms."""
    from app.metrics import get_supported_generic_metrics, COMMENT_SUPPORTED_PLATFORMS, get_platform_type
    platforms = []
    for p in Platform:
        pval = p.value
        try:
            connector = dispatcher.get_connector(p)
            schema = connector.get_schema()
            raw_metrics = schema.get("metrics", [])
            available = [m["name"] if isinstance(m, dict) else m for m in raw_metrics]
            api_ver = schema.get("metadata", {}).get("api_version") or PLATFORM_API_VERSIONS.get(pval)
            
            platforms.append(PlatformInfo(
                platform=p,
                display_name=pval.replace("_", " ").title(),
                type=get_platform_type(pval),
                configured=settings.is_platform_configured(pval),
                available_metrics=available,
                generic_metrics=get_supported_generic_metrics(pval),
                supports_comments=pval in COMMENT_SUPPORTED_PLATFORMS,
                supports_batch=True,
                description=f"Connector for {pval.replace('_', ' ').title()}",
                api_version=api_ver
            ))
        except Exception as e:
            logger.warning(f"Could not get schema for {pval}: {e}")
            platforms.append(PlatformInfo(
                platform=p,
                display_name=pval.replace("_", " ").title(),
                type=get_platform_type(pval),
                configured=settings.is_platform_configured(pval),
                available_metrics=[],
                generic_metrics=get_supported_generic_metrics(pval),
                supports_comments=pval in COMMENT_SUPPORTED_PLATFORMS,
                supports_batch=True,
                description=f"Connector for {pval.replace('_', ' ').title()} (failed to load schema)",
                api_version=PLATFORM_API_VERSIONS.get(pval)
            ))
    return platforms

@app.get("/api/v1/schema/{platform}", response_model=SchemaResponse)
async def get_platform_schema(platform: Platform, api_key: str = Depends(verify_api_key)):
    """Get the full metric/dimension schema for a specific platform."""
    try:
        connector = dispatcher.get_connector(platform)
        schema = connector.get_schema()
        return SchemaResponse(
            platform=platform,
            metrics=schema.get("metrics", []),
            dimensions=schema.get("dimensions", []),
            metadata=schema.get("metadata", {})
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching schema for {platform}: {e}")
        raise HTTPException(status_code=500, detail="Internal error fetching schema")

from app.services.credential_store import credential_store
from app.models.requests import ValidationRequest
from app.models.responses import ValidationResponse, CredentialStatusResponse, CredentialStatusDetails

@app.post("/api/v1/validate", response_model=ValidationResponse)
async def validate_request_endpoint(
    request: ValidationRequest,
    api_key: str = Depends(verify_api_key)
):
    """Validate parameters and metrics for a platform without making any upstream calls."""
    from app.metrics import validate_platform_params, validate_metrics, METRIC_TRANSLATION_MAP
    
    # 1. Parameter validation (syntactic)
    param_errors = validate_platform_params(
        request.platform.value,
        request.account_id,
        request.post_id,
        request.video_id,
        request.app_id
    )
    
    # 1.5 Semantic validation (check Firestore connection/credentials)
    if request.client_id and request.account_id:
        oauth_conns = await credential_store.list_oauth_connections(request.client_id, request.platform.value)
        has_oauth = any(c.get("account_id") == request.account_id for c in oauth_conns)
        manual_creds = await credential_store.get_credentials(request.client_id, request.platform.value)
        
        if not (has_oauth or manual_creds is not None):
            param_errors.append(
                f"Validación semántica fallida: No se encontraron credenciales o conexiones activas para la cuenta '{request.account_id}' en el cliente '{request.client_id}'."
            )
    
    # 2. Metric validation
    if request.use_generic_names:
        native_metrics, metric_errors = validate_metrics(request.platform.value, request.metrics)
        translations = {}
        for m in request.metrics:
            native = METRIC_TRANSLATION_MAP.get(request.platform.value, {}).get(m)
            translations[m] = native
            
        invalid_metrics = [e["metric"] for e in metric_errors]
        valid_metrics = [m for m in request.metrics if translations.get(m) is not None]
        
        return ValidationResponse(
            valid=len(param_errors) == 0 and len(metric_errors) == 0,
            platform=request.platform,
            valid_metrics=valid_metrics,
            invalid_metrics=invalid_metrics,
            translations=translations,
            native_metrics_to_request=native_metrics,
            parameter_errors=param_errors
        )
    else:
        try:
            connector = dispatcher.get_connector(request.platform)
            schema = connector.get_schema()
            raw_metrics = schema.get("metrics", [])
            schema_names = {m["name"] if isinstance(m, dict) else m for m in raw_metrics}
        except Exception:
            schema_names = set()
            
        valid_metrics = [m for m in request.metrics if m in schema_names]
        invalid_metrics = [m for m in request.metrics if m not in schema_names]
        
        return ValidationResponse(
            valid=len(param_errors) == 0 and len(invalid_metrics) == 0,
            platform=request.platform,
            valid_metrics=valid_metrics,
            invalid_metrics=invalid_metrics,
            parameter_errors=param_errors
        )

@app.get("/api/v1/credentials/status", response_model=CredentialStatusResponse)
async def get_credentials_status(
    client_id: str,
    api_key: str = Depends(verify_api_key)
):
    """Check configuration and credential status for all platforms for a client."""
    platforms_status = {}
    for p in Platform:
        pval = p.value
        # Check Firestore for OAuth connections
        oauth_conns = await credential_store.list_oauth_connections(client_id, pval)
        # Check Firestore for manual credentials
        manual_creds = await credential_store.get_credentials(client_id, pval)
        
        has_creds = len(oauth_conns) > 0 or manual_creds is not None
        cred_type = "none"
        last_refreshed = None
        
        if oauth_conns:
            cred_type = "oauth"
            dates = [c.get("connected_at") for c in oauth_conns if c.get("connected_at")]
            if dates:
                last_refreshed = max(dates)
        elif manual_creds:
            if pval in ("google_play", "apple_app_store") or "service_account" in manual_creds or "private_key_path" in manual_creds or "service_account_json" in manual_creds:
                cred_type = "service_account"
            else:
                cred_type = "api_key"
            
        details = (
            f"{len(oauth_conns)} OAuth connection(s)"
            if oauth_conns
            else ("Manual credentials configured" if manual_creds else "No credentials configured")
        )
        
        platforms_status[pval] = CredentialStatusDetails(
            has_credentials=has_creds,
            credential_type=cred_type,
            details=details,
            last_refreshed=last_refreshed
        )
        
    return CredentialStatusResponse(
        client_id=client_id,
        platforms=platforms_status
    )

@app.post("/api/v1/campaign-data", response_model=DataResponse)
async def get_campaign_data(
    request: DataRequest, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Fetch data for a single platform with multi-tenant support."""
    logger.info(f"AUDIT LOG: client_id='{request.client_id}' user_id='{request.user_id}' platform='{request.platform.value}'")
    logger.info(f"Request for platform: {request.platform.value}, client: {request.client_id}")
    
    # Reset rate limit tracker for this thread
    from app.connectors.base import rate_limit_ctx
    rate_limit_ctx.set(None)

    if request.dry_run:
        return DataResponse(
            status="success",
            platform=request.platform,
            date_range={"start": str(request.start_date), "end": str(request.end_date)},
            data=[],
            metadata={"dry_run": True, "message": "Dry-run validation successful."}
        )
    
    # Resolve credentials: first check OAuth connections, then fall back to manual
    if not request.credentials:
        logger.info(f"Resolving credentials for {request.platform.value} from Firestore...")
        request.credentials = await credential_store.resolve_credentials(
            request.client_id, request.platform.value, request.account_id or ""
        )
    
    try:
        connector = dispatcher.get_connector(request.platform)
    except ValueError as e:
        # Not yet implemented
        return DataResponse(
            platform=request.platform,
            status="error",
            errors=[ErrorDetail(code="NOT_IMPLEMENTED", message=str(e), retryable=False)]
        )

    try:
        # Thread offloading is critical here to avoid blocking FastAPI
        data = await asyncio.to_thread(connector.fetch_with_retry, request)
        
        # Dual-write to BigQuery in background
        if settings.enable_bigquery_sink:
            background_tasks.add_task(
                bq_sink.write_data, 
                request.platform, 
                data,
                request.client_id,
                request.user_id,
                {"request_id": str(datetime.now(timezone.utc).timestamp())}
            )

        # Unified pagination
        total_count = len(data)
        limit = request.limit
        offset = 0
        if request.next_page_token:
            try:
                offset = int(request.next_page_token)
            except ValueError:
                pass
                
        if limit is not None:
            sliced_data = data[offset : offset + limit]
            has_next = (offset + limit) < total_count
            next_token = str(offset + limit) if has_next else None
            page_size = limit
        else:
            sliced_data = data
            has_next = False
            next_token = None
            page_size = total_count

        from app.models.responses import PaginationInfo
        pagination = PaginationInfo(
            page=(offset // limit) + 1 if (limit and limit > 0) else 1,
            page_size=page_size,
            total_count=total_count,
            has_next=has_next,
            next_page_token=next_token
        )

        from app.connectors.base import request_rate_limits, request_rate_limits_lock
        with request_rate_limits_lock:
            rl_remaining = request_rate_limits.pop(id(request), None)
        if rl_remaining is None:
            rl_remaining = rate_limit_ctx.get()

        return DataResponse(
            status="success",
            platform=request.platform,
            date_range={"start": str(request.start_date), "end": str(request.end_date)},
            data=sliced_data,
            pagination=pagination,
            rate_limit_remaining=rl_remaining
        )
    except Exception as e:
        logger.error(f"Connector error: {e}")
        err_detail = connector.handle_error(e)
        from app.connectors.base import request_rate_limits, request_rate_limits_lock
        with request_rate_limits_lock:
            rl_remaining = request_rate_limits.pop(id(request), None)
        if rl_remaining is None:
            rl_remaining = rate_limit_ctx.get() or err_detail.rate_limit_remaining
        return DataResponse(
            status="error",
            platform=request.platform,
            date_range={"start": str(request.start_date), "end": str(request.end_date)},
            errors=[err_detail],
            rate_limit_remaining=rl_remaining
        )


@app.post("/api/v1/comments", response_model=CommentsResponse)
async def get_comments(
    request: CommentsRequest,
    api_key: str = Depends(verify_api_key)
):
    """Fetch comments on a specific post.
    
    Supported platforms: meta_ads, meta_organic (FB Pages + Instagram),
    threads, youtube, x_organic.
    """
    logger.info(f"AUDIT LOG: client_id='{request.client_id}' user_id='{request.user_id}' platform='{request.platform.value}'")
    logger.info(f"Comment request for platform: {request.platform.value}, post: {request.post_id}")

    from app.connectors.base import rate_limit_ctx
    rate_limit_ctx.set(None)

    # Resolve credentials
    creds = await credential_store.resolve_credentials(request.client_id, request.platform.value, request.account_id)
    if not creds:
        creds = {}

    def fetch_comments_in_thread():
        from app.connectors.base import thread_local_storage
        thread_local_storage.current_request = request
        try:
            if request.platform == Platform.THREADS:
                access_token = creds.get("access_token") or settings.threads_access_token
                from app.connectors.threads import ThreadsConnector
                connector = ThreadsConnector()
                return connector.fetch_comments(request.post_id, access_token)
            elif request.platform == Platform.META_ADS:
                access_token = creds.get("access_token") or settings.meta_access_token
                from app.connectors.meta import MetaAdsConnector
                connector = MetaAdsConnector()
                return connector.fetch_comments(request.post_id, access_token)
            elif request.platform == Platform.META_ORGANIC:
                access_token = creds.get("access_token") or settings.meta_access_token
                is_instagram = creds.get("is_instagram", False)
                from app.connectors.meta import MetaOrganicConnector
                connector = MetaOrganicConnector()
                return connector.fetch_comments(request.post_id, access_token, is_instagram)
            elif request.platform == Platform.YOUTUBE:
                api_key_or_token = creds.get("access_token") or settings.youtube_api_key
                is_oauth = bool(creds.get("access_token"))
                from app.connectors.youtube import YouTubeConnector
                connector = YouTubeConnector()
                return connector.fetch_comments(request.post_id, api_key_or_token, is_oauth)
            elif request.platform == Platform.X_ORGANIC:
                bearer_token = creds.get("bearer_token") or settings.x_bearer_token
                from app.connectors.x_twitter import XOrganicConnector
                connector = XOrganicConnector()
                return connector.fetch_comments(request.post_id, bearer_token)
            elif request.platform == Platform.PINTEREST_ORGANIC:
                access_token = creds.get("access_token") or settings.pinterest_access_token
                from app.connectors.pinterest import PinterestOrganicConnector
                connector = PinterestOrganicConnector()
                return connector.fetch_comments(request.post_id, access_token)
            else:
                raise ValueError(f"Unsupported platform {request.platform.value}")
        finally:
            if hasattr(thread_local_storage, "current_request"):
                del thread_local_storage.current_request

    try:
        if request.platform not in (Platform.THREADS, Platform.META_ADS, Platform.META_ORGANIC, Platform.YOUTUBE, Platform.X_ORGANIC, Platform.PINTEREST_ORGANIC):
            return CommentsResponse(
                status="error",
                platform=request.platform,
                post_id=request.post_id,
                errors=[ErrorDetail(
                    code="UNSUPPORTED",
                    message=f"Comments not supported for platform {request.platform.value}. "
                            f"Supported: meta_ads, meta_organic, threads, youtube, x_organic, pinterest_organic",
                    retryable=False
                )]
            )

        comments = await asyncio.to_thread(fetch_comments_in_thread)

        # Slicing pagination for comments
        total_comments = len(comments)
        limit = request.limit
        offset = 0
        if request.next_page_token:
            try:
                offset = int(request.next_page_token)
            except ValueError:
                pass
                
        if limit is not None:
            sliced_comments = comments[offset : offset + limit]
            has_next = (offset + limit) < total_comments
            next_token = str(offset + limit) if has_next else None
        else:
            sliced_comments = comments
            has_next = False
            next_token = None

        from app.connectors.base import request_rate_limits, request_rate_limits_lock
        with request_rate_limits_lock:
            rl_remaining = request_rate_limits.pop(id(request), None)
        if rl_remaining is None:
            rl_remaining = rate_limit_ctx.get()

        return CommentsResponse(
            status="success",
            platform=request.platform,
            post_id=request.post_id,
            total_comments=total_comments,
            comments=sliced_comments,
            next_page_token=next_token,
            rate_limit_remaining=rl_remaining
        )
    except Exception as e:
        logger.error(f"Error fetching comments: {e}")
        from app.connectors.base import request_rate_limits, request_rate_limits_lock
        with request_rate_limits_lock:
            rl_remaining = request_rate_limits.pop(id(request), None)
        if rl_remaining is None:
            rl_remaining = rate_limit_ctx.get()
        return CommentsResponse(
            status="error",
            platform=request.platform,
            post_id=request.post_id,
            errors=[ErrorDetail(
                code="COMMENT_FETCH_ERROR",
                message=str(e),
                retryable=True
            )],
            rate_limit_remaining=rl_remaining
        )


@app.post("/api/v1/batch", response_model=BatchDataResponse)
async def get_batch_data(
    request: BatchDataRequest, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Fetch data from multiple platforms concurrently with robust error handling."""
    client_id = request.requests[0].client_id if request.requests else "unknown"
    user_id = request.requests[0].user_id if request.requests else "unknown"
    logger.info(f"AUDIT LOG: client_id='{client_id}' user_id='{user_id}' platform='batch'")

    # Reset rate limit tracker
    from app.connectors.base import rate_limit_ctx
    rate_limit_ctx.set(None)

    async def fetch_wrapper(req: DataRequest):
        try:
            return await get_campaign_data(req, background_tasks, api_key)
        except Exception as e:
            logger.error(f"Batch sub-request failed: {e}")
            return DataResponse(
                status="error",
                platform=req.platform,
                errors=[ErrorDetail(code="BATCH_SUBREQUEST_FAILED", message=str(e), retryable=False)]
            )

    # Run all requests concurrently
    results = await asyncio.gather(*[fetch_wrapper(req) for req in request.requests])
    
    successful = sum(1 for res in results if res.status == "success")
    failed = sum(1 for res in results if res.status == "error")
    
    status = "success"
    if failed > 0:
        status = "partial" if successful > 0 else "error"

    rl_remaining = rate_limit_ctx.get()

    return BatchDataResponse(
        status=status,
        results=results,
        total_platforms=len(request.requests),
        successful_platforms=successful,
        failed_platforms=failed,
        rate_limit_remaining=rl_remaining
    )


import requests as _requests

@app.post("/api/v1/tiktok-proxy")
async def tiktok_proxy(
    request: TikTokProxyRequest,
    api_key: str = Depends(verify_api_key)
):
    """Generic authenticated proxy for executing any TikTok Marketing API endpoint."""
    logger.info(f"TikTok API Proxy Request: path='{request.path}' client_id='{request.client_id}' account_id='{request.account_id}' method='{request.method}'")
    
    # 1. Resolve credentials
    creds = await credential_store.resolve_credentials(
        request.client_id, "tiktok_ads", request.account_id
    )
    if not creds or not creds.get("access_token"):
        raise HTTPException(
            status_code=401,
            detail=f"Credentials not found for client '{request.client_id}' and advertiser '{request.account_id}' on platform 'tiktok_ads'."
        )
        
    access_token = creds["access_token"]
    
    # 2. Normalize path (must start with /open_api/v1.3/)
    path = request.path.lstrip("/")
    if not path.startswith("open_api/"):
        path = f"open_api/v1.3/{path}"
        
    url = f"https://business-api.tiktok.com/{path}"
    headers = {
        "Access-Token": access_token,
        "Content-Type": "application/json"
    }
    
    # 3. Execute HTTP request
    try:
        method = request.method.upper()
        if method == "GET":
            response = await asyncio.to_thread(
                _requests.get, url, params=request.params, headers=headers, timeout=30
            )
        elif method == "POST":
            response = await asyncio.to_thread(
                _requests.post, url, json=request.json_body, params=request.params, headers=headers, timeout=30
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported method '{method}' for TikTok API Proxy.")
            
        response.raise_for_status()
        return response.json()
    except _requests.RequestException as e:
        logger.error(f"TikTok API Proxy Call failed: {e}")
        if e.response is not None:
            try:
                return JSONResponse(status_code=e.response.status_code, content=e.response.json())
            except Exception:
                raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        raise HTTPException(status_code=502, detail=f"Failed to communicate with TikTok API: {e}")


@app.post("/api/v1/tiktok-organic-proxy")
async def tiktok_organic_proxy(
    request: TikTokOrganicProxyRequest,
    api_key: str = Depends(verify_api_key)
):
    """Generic authenticated proxy for executing any TikTok Organic/Display API endpoint."""
    logger.info(f"TikTok Organic API Proxy Request: path='{request.path}' client_id='{request.client_id}' account_id='{request.account_id}' method='{request.method}'")
    
    # 1. Resolve credentials
    creds = await credential_store.resolve_credentials(
        request.client_id, "tiktok_organic", request.account_id
    )
    if not creds or not creds.get("access_token"):
        raise HTTPException(
            status_code=401,
            detail=f"Credentials not found for client '{request.client_id}' and account '{request.account_id}' on platform 'tiktok_organic'."
        )
        
    access_token = creds["access_token"]
    is_bc_asset = creds.get("is_bc_asset") == True
    
    # 2. Determine base URL and headers based on account type (BC brand asset vs personal Display API)
    path = request.path.lstrip("/")
    if is_bc_asset:
        if not path.startswith("open_api/"):
            path = f"open_api/v1.3/{path}"
        url = f"https://business-api.tiktok.com/{path}"
        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json"
        }
    else:
        if not path.startswith("v2/"):
            path = f"v2/{path}"
        base_url = "https://open-sandbox.tiktokapis.com" if settings.use_tiktok_sandbox else "https://open.tiktokapis.com"
        url = f"{base_url}/{path}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
    # 3. Execute HTTP request
    try:
        method = request.method.upper()
        if method == "GET":
            response = await asyncio.to_thread(
                _requests.get, url, params=request.params, headers=headers, timeout=30
            )
        elif method == "POST":
            response = await asyncio.to_thread(
                _requests.post, url, json=request.json_body, params=request.params, headers=headers, timeout=30
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported method '{method}' for TikTok Organic API Proxy.")
            
        response.raise_for_status()
        return response.json()
    except _requests.RequestException as e:
        logger.error(f"TikTok Organic API Proxy Call failed: {e}")
        if e.response is not None:
            try:
                return JSONResponse(status_code=e.response.status_code, content=e.response.json())
            except Exception:
                raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        raise HTTPException(status_code=502, detail=f"Failed to communicate with TikTok Organic API: {e}")


# ===================================================================
# Unified Platform Proxy Handler
# ===================================================================
from fastapi.responses import JSONResponse
from app.models.requests import PlatformProxyRequest

async def _execute_generic_proxy(
    platform_name: str, 
    request: PlatformProxyRequest, 
    default_base_url: str, 
    auth_type: str = "bearer", 
    default_token: str = ""
):
    creds = await credential_store.resolve_credentials(
        request.client_id, platform_name, request.account_id
    )
    if not creds:
        creds = {}

    access_token = creds.get("access_token") or default_token
    
    headers = {"Content-Type": "application/json"}
    if request.headers:
        headers.update(request.headers)

    if auth_type == "bearer" and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    elif auth_type == "shopify" and access_token:
        headers["X-Shopify-Access-Token"] = access_token
    elif auth_type == "x-ap-context" and access_token:
        headers["Authorization"] = f"Bearer {access_token}"
        headers["X-AP-Context"] = request.account_id
    elif auth_type == "google_ads":
        dev_token = creds.get("developer_token") or settings.google_ads_developer_token
        if dev_token:
            headers["developer-token"] = dev_token
        login_cust_id = creds.get("login_customer_id")
        if login_cust_id:
            headers["login-customer-id"] = str(login_cust_id).replace("-", "")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
    elif auth_type == "apple_app_store":
        try:
            key_id = creds.get("key_id") or settings.apple_key_id
            issuer_id = creds.get("issuer_id") or settings.apple_issuer_id
            private_key_path = creds.get("private_key_path") or settings.apple_private_key_path
            if key_id and issuer_id and private_key_path:
                with open(private_key_path, 'r') as f:
                    private_key = f.read()
                import jwt
                import time
                token = jwt.encode(
                    {"iss": issuer_id, "iat": int(time.time()), "exp": int(time.time()) + 1200, "aud": "appstoreconnect-v1"},
                    private_key, algorithm="ES256", headers={"kid": key_id}
                )
                headers["Authorization"] = f"Bearer {token}"
            elif access_token:
                headers["Authorization"] = f"Bearer {access_token}"
        except Exception as jwt_err:
            logger.error(f"Failed to generate JWT for Apple App Store proxy: {jwt_err}")
            if access_token:
                headers["Authorization"] = f"Bearer {access_token}"

    base_url = default_base_url
    if platform_name == "shopify":
        shop_domain = request.account_id or creds.get("shop_name") or settings.shopify_shop_name
        if shop_domain:
            if "." not in shop_domain:
                shop_domain = f"{shop_domain}.myshopify.com"
            base_url = f"https://{shop_domain}/admin/api/2024-04"

    path = request.path.lstrip("/")
    url = f"{base_url}/{path}"
    
    try:
        method = request.method.upper()
        if method == "GET":
            response = await asyncio.to_thread(
                _requests.get, url, params=request.params, headers=headers, timeout=30
            )
        elif method == "POST":
            response = await asyncio.to_thread(
                _requests.post, url, json=request.json_body, params=request.params, headers=headers, timeout=30
            )
        elif method == "PUT":
            response = await asyncio.to_thread(
                _requests.put, url, json=request.json_body, params=request.params, headers=headers, timeout=30
            )
        elif method == "DELETE":
            response = await asyncio.to_thread(
                _requests.delete, url, params=request.params, headers=headers, timeout=30
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported method '{method}' for proxy.")
            
        response.raise_for_status()
        return response.json()
    except _requests.RequestException as e:
        logger.error(f"Proxy Call failed for {platform_name}: {e}")
        if e.response is not None:
            try:
                return JSONResponse(status_code=e.response.status_code, content=e.response.json())
            except Exception:
                raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        raise HTTPException(status_code=502, detail=f"Failed to communicate with {platform_name} API: {e}")


@app.post("/api/v1/meta-proxy")
async def meta_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Meta Ads / Organic (Graph API)."""
    return await _execute_generic_proxy("meta_ads", request, "https://graph.facebook.com/v19.0", "bearer", settings.meta_access_token)

@app.post("/api/v1/google-ads-proxy")
async def google_ads_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Google Ads REST API."""
    return await _execute_generic_proxy("google_ads", request, "https://googleads.googleapis.com/v16", "google_ads", settings.google_ads_refresh_token)

@app.post("/api/v1/ga4-proxy")
async def ga4_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for GA4 Analytics Data API."""
    return await _execute_generic_proxy("ga4", request, "https://analyticsdata.googleapis.com/v1beta", "bearer")

@app.post("/api/v1/linkedin-proxy")
async def linkedin_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for LinkedIn API."""
    return await _execute_generic_proxy("linkedin_ads", request, "https://api.linkedin.com", "bearer", settings.linkedin_access_token)

@app.post("/api/v1/x-twitter-proxy")
async def x_twitter_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for X/Twitter API v2."""
    return await _execute_generic_proxy("x_organic", request, "https://api.twitter.com/2", "bearer", settings.x_bearer_token)

@app.post("/api/v1/youtube-proxy")
async def youtube_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for YouTube Data API v3."""
    return await _execute_generic_proxy("youtube", request, "https://www.googleapis.com/youtube/v3", "bearer", settings.youtube_api_key)

@app.post("/api/v1/google-play-proxy")
async def google_play_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Google Play Developer API."""
    return await _execute_generic_proxy("google_play", request, "https://www.googleapis.com/androidpublisher/v3", "bearer")

@app.post("/api/v1/apple-app-store-proxy")
async def apple_app_store_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Apple App Store Connect API."""
    return await _execute_generic_proxy("apple_app_store", request, "https://api.appstoreconnect.apple.com/v1", "apple_app_store")

@app.post("/api/v1/apple-ads-proxy")
async def apple_ads_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Apple Search Ads API v5."""
    return await _execute_generic_proxy("apple_ads", request, "https://api.searchads.apple.com/api/v5", "x-ap-context", settings.apple_ads_access_token)

@app.post("/api/v1/threads-proxy")
async def threads_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Threads Graph API."""
    return await _execute_generic_proxy("threads", request, "https://graph.threads.net/v1.0", "bearer", settings.threads_access_token)

@app.post("/api/v1/spotify-proxy")
async def spotify_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Spotify Partner Ads API."""
    return await _execute_generic_proxy("spotify_ads", request, "https://api-partner.spotify.com/ads/v3", "bearer")

@app.post("/api/v1/pinterest-proxy")
async def pinterest_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Pinterest API v5."""
    return await _execute_generic_proxy("pinterest_ads", request, "https://api.pinterest.com/v5", "bearer", settings.pinterest_access_token)

@app.post("/api/v1/shopify-proxy")
async def shopify_proxy(request: PlatformProxyRequest, api_key: str = Depends(verify_api_key)):
    """Proxy for Shopify Admin API."""
    return await _execute_generic_proxy("shopify", request, "https://mock.myshopify.com/admin/api/2024-04", "shopify", settings.shopify_access_token)


