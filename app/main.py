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
from app.models.requests import DataRequest, Platform, BatchDataRequest, CommentsRequest
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
# Future connectors to register here...

app = FastAPI(
    title="Inhaus Marketing Data API",
    description="Agent-ready API for multi-platform marketing data.",
    version="5.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register OAuth router
from app.routers.oauth import router as oauth_router
app.include_router(oauth_router)

# Mount FastMCP server and protect it with middleware
from fastapi import Request
from fastapi.responses import JSONResponse
from app.mcp import mcp

@app.middleware("http")
async def mcp_auth_middleware(request: Request, call_next):
    # Match /mcp, /mcp/sse, etc.
    if request.url.path.startswith("/mcp"):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            api_key = request.query_params.get("api_key")
        if api_key != settings.api_key:
            return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})
    return await call_next(request)

@app.middleware("http")
async def latency_logging_middleware(request: Request, call_next):
    """Log structured request/response info with latency."""
    start = _time.monotonic()
    response = await call_next(request)
    elapsed_ms = (_time.monotonic() - start) * 1000
    # Only log API and MCP routes
    path = request.url.path
    if path.startswith("/api/") or path.startswith("/mcp"):
        logger.info(
            f"[HTTP] {request.method} {path} → {response.status_code} "
            f"({elapsed_ms:.0f}ms)"
        )
    return response

# Use Streamable HTTP transport (more robust than SSE for long-lived connections)
# Falls back to SSE for clients that don't support Streamable HTTP
try:
    app.mount("/mcp", mcp.streamable_http_app())
    logger.info("MCP mounted with Streamable HTTP transport")
except AttributeError:
    # Fallback for older mcp versions that don't have streamable_http_app
    app.mount("/mcp", mcp.sse_app())
    logger.info("MCP mounted with SSE transport (streamable_http_app not available)")

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
    "linkedin_ads": "v2",
    "linkedin_organic": "v2",
    "x_ads": "v2",
    "x_organic": "v2",
    "youtube": "v3",
    "google_play": "v3",
    "apple_app_store": "v1.6",
    "apple_ads": "v5",
    "threads": "v1.0"
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
            else:
                raise ValueError(f"Unsupported platform {request.platform.value}")
        finally:
            if hasattr(thread_local_storage, "current_request"):
                del thread_local_storage.current_request

    try:
        if request.platform not in (Platform.THREADS, Platform.META_ADS, Platform.META_ORGANIC, Platform.YOUTUBE, Platform.X_ORGANIC):
            return CommentsResponse(
                status="error",
                platform=request.platform,
                post_id=request.post_id,
                errors=[ErrorDetail(
                    code="UNSUPPORTED",
                    message=f"Comments not supported for platform {request.platform.value}. "
                            f"Supported: meta_ads, meta_organic, threads, youtube, x_organic",
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
