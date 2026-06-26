"""
Router for Client Management — List clients, view connected accounts,
and retrieve per-platform performance summaries.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Query
from app.middleware.auth import verify_api_key
from app.services.credential_store import credential_store
from app.models.requests import Platform

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clients", tags=["Client Management"])

# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class PlatformSummary(BaseModel):
    """Summary of a single platform connection for a client."""
    platform: str
    connected_accounts: int = 0
    has_manual_credentials: bool = False
    credential_type: Literal["oauth", "api_key", "service_account", "none"] = "none"


class ClientListItem(BaseModel):
    """Lightweight client object for the listing endpoint."""
    client_id: str
    display_name: Optional[str] = None
    created_at: Optional[str] = None
    connected_platforms: int = 0
    platforms: List[PlatformSummary] = Field(default_factory=list)


class ClientListResponse(BaseModel):
    """Response for the list-clients endpoint."""
    status: str = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_clients: int = 0
    clients: List[ClientListItem] = Field(default_factory=list)


class ConnectedAccount(BaseModel):
    """A single OAuth connection or manual credential entry."""
    platform: str
    account_id: Optional[str] = None
    account_name: Optional[str] = None
    connection_type: Literal["oauth", "manual"] = "oauth"
    connected_at: Optional[str] = None
    token_expires_at: Optional[str] = None


class PlatformCredentialStatus(BaseModel):
    """Credential status for one platform on a client."""
    platform: str
    has_credentials: bool = False
    credential_type: Literal["oauth", "api_key", "service_account", "none"] = "none"
    oauth_accounts: int = 0
    details: str = ""


class ClientDetailResponse(BaseModel):
    """Full client profile with all connected accounts and credential statuses."""
    status: str = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_id: str
    display_name: Optional[str] = None
    created_at: Optional[str] = None
    total_connected_platforms: int = 0
    total_connected_accounts: int = 0
    platforms: List[PlatformCredentialStatus] = Field(default_factory=list)
    accounts: List[ConnectedAccount] = Field(default_factory=list)


class AccountsListResponse(BaseModel):
    """Response for listing connected accounts."""
    status: str = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_id: str
    total_accounts: int = 0
    accounts: List[ConnectedAccount] = Field(default_factory=list)


class PlatformReportResponse(BaseModel):
    """Quick performance report for a specific client + platform."""
    status: str = "success"
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    client_id: str
    platform: str
    account_id: Optional[str] = None
    date_range: Dict[str, str] = Field(default_factory=dict)
    total_campaigns: int = 0
    aggregated_metrics: Dict[str, Any] = Field(default_factory=dict)
    unsupported_metrics: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helper: all platform enum values
# ---------------------------------------------------------------------------
ALL_PLATFORMS = [p.value for p in Platform]


# ---------------------------------------------------------------------------
# GET /api/v1/clients — List all clients
# ---------------------------------------------------------------------------
@router.get("", response_model=ClientListResponse)
async def list_clients(api_key: str = Depends(verify_api_key)):
    """
    List all agency clients with a summary of their connected platforms.

    Queries the Firestore `clients` collection directly and inspects
    each client's `oauth_connections` and `credentials` sub-collections.
    """
    db = credential_store.db
    if not db:
        raise HTTPException(status_code=503, detail="Firestore is not available")

    try:
        # List all documents in the top-level `clients` collection
        clients_ref = db.collection("clients")
        client_docs = clients_ref.list_documents()

        async def process_client(doc_ref):
            client_id = doc_ref.id
            
            # Fetch client doc, oauth connections, and credentials in parallel
            doc_snapshot_task = doc_ref.get()
            oauth_ref = db.collection("clients").document(client_id).collection("oauth_connections")
            oauth_task = oauth_ref.get()
            creds_ref = db.collection("clients").document(client_id).collection("credentials")
            creds_task = creds_ref.get()

            doc_snapshot, oauth_docs, credentials_docs = await asyncio.gather(
                doc_snapshot_task, oauth_task, creds_task
            )

            doc_data = doc_snapshot.to_dict() if doc_snapshot.exists else {}
            display_name = doc_data.get("display_name") or doc_data.get("name") or client_id
            created_at = doc_data.get("created_at")

            # Group oauth connections by platform
            oauth_by_platform = {}
            for doc in oauth_docs:
                data = doc.to_dict() or {}
                platform = data.get("platform")
                if not platform and "_" in doc.id:
                    platform = doc.id.split("_")[0]
                if platform:
                    if platform not in oauth_by_platform:
                        oauth_by_platform[platform] = []
                    oauth_by_platform[platform].append(data)

            # Map credentials by platform (document ID is the platform)
            creds_by_platform = {}
            for doc in credentials_docs:
                creds_by_platform[doc.id] = doc.to_dict() or {}

            # Check every platform for connections / credentials
            platform_summaries: List[PlatformSummary] = []
            connected_platform_count = 0

            for pval in ALL_PLATFORMS:
                oauth_conns = oauth_by_platform.get(pval, [])
                manual_creds = creds_by_platform.get(pval)
                has_manual = manual_creds is not None
                oauth_count = len(oauth_conns)

                if oauth_count > 0 or has_manual:
                    connected_platform_count += 1
                    cred_type: Literal["oauth", "api_key", "service_account", "none"] = "none"
                    if oauth_count > 0:
                        cred_type = "oauth"
                    elif has_manual:
                        if any(k in (manual_creds or {}) for k in ("service_account", "private_key_path", "service_account_json")):
                            cred_type = "service_account"
                        else:
                            cred_type = "api_key"

                    platform_summaries.append(PlatformSummary(
                        platform=pval,
                        connected_accounts=oauth_count,
                        has_manual_credentials=has_manual,
                        credential_type=cred_type,
                    ))

            return ClientListItem(
                client_id=client_id,
                display_name=display_name,
                created_at=created_at,
                connected_platforms=connected_platform_count,
                platforms=platform_summaries,
            )

        # Collect all client doc refs from the async generator
        doc_refs = []
        async for doc_ref in client_docs:
            doc_refs.append(doc_ref)

        # Process all clients in parallel!
        items = await asyncio.gather(*[process_client(doc_ref) for doc_ref in doc_refs])

        return ClientListResponse(total_clients=len(items), clients=items)

    except Exception as e:
        logger.error(f"Error listing clients from Firestore: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list clients: {e}")


# ---------------------------------------------------------------------------
# GET /api/v1/clients/{client_id} — Get client detail
# ---------------------------------------------------------------------------
@router.get("/{client_id}", response_model=ClientDetailResponse)
async def get_client_detail(client_id: str, api_key: str = Depends(verify_api_key)):
    """
    Get a full client profile with all connected accounts and
    per-platform credential status.
    """
    db = credential_store.db
    if not db:
        raise HTTPException(status_code=503, detail="Firestore is not available")

    try:
        # Read the client profile document, oauth connections, and credentials in parallel
        client_ref = db.collection("clients").document(client_id)
        doc_snapshot_task = client_ref.get()
        oauth_ref = db.collection("clients").document(client_id).collection("oauth_connections")
        oauth_task = oauth_ref.get()
        creds_ref = db.collection("clients").document(client_id).collection("credentials")
        creds_task = creds_ref.get()

        client_doc, oauth_docs, credentials_docs = await asyncio.gather(
            doc_snapshot_task, oauth_task, creds_task
        )

        if not client_doc.exists:
            raise HTTPException(status_code=404, detail=f"Client '{client_id}' not found")

        doc_data = client_doc.to_dict() or {}
        display_name = doc_data.get("display_name") or doc_data.get("name") or client_id
        created_at = doc_data.get("created_at")

        # Group oauth connections by platform
        oauth_by_platform = {}
        for doc in oauth_docs:
            data = doc.to_dict() or {}
            platform = data.get("platform")
            if not platform and "_" in doc.id:
                platform = doc.id.split("_")[0]
            if platform:
                if platform not in oauth_by_platform:
                    oauth_by_platform[platform] = []
                oauth_by_platform[platform].append(data)

        # Map credentials by platform
        creds_by_platform = {}
        for doc in credentials_docs:
            creds_by_platform[doc.id] = doc.to_dict() or {}

        all_accounts: List[ConnectedAccount] = []
        platform_statuses: List[PlatformCredentialStatus] = []
        total_connected = 0

        for pval in ALL_PLATFORMS:
            oauth_conns = oauth_by_platform.get(pval, [])
            manual_creds = creds_by_platform.get(pval)

            has_creds = len(oauth_conns) > 0 or manual_creds is not None
            cred_type: Literal["oauth", "api_key", "service_account", "none"] = "none"
            details = "No credentials configured"

            if oauth_conns:
                cred_type = "oauth"
                details = f"{len(oauth_conns)} OAuth connection(s)"
                for conn in oauth_conns:
                    all_accounts.append(ConnectedAccount(
                        platform=pval,
                        account_id=conn.get("account_id"),
                        account_name=conn.get("account_name"),
                        connection_type="oauth",
                        connected_at=conn.get("connected_at"),
                        token_expires_at=conn.get("token_expires_at"),
                    ))
            elif manual_creds:
                if any(k in manual_creds for k in ("service_account", "private_key_path", "service_account_json")):
                    cred_type = "service_account"
                else:
                    cred_type = "api_key"
                details = "Manual credentials configured"
                all_accounts.append(ConnectedAccount(
                    platform=pval,
                    account_id=manual_creds.get("account_id"),
                    account_name=manual_creds.get("account_name"),
                    connection_type="manual",
                ))

            if has_creds:
                total_connected += 1

            platform_statuses.append(PlatformCredentialStatus(
                platform=pval,
                has_credentials=has_creds,
                credential_type=cred_type,
                oauth_accounts=len(oauth_conns),
                details=details,
            ))

        return ClientDetailResponse(
            client_id=client_id,
            display_name=display_name,
            created_at=created_at,
            total_connected_platforms=total_connected,
            total_connected_accounts=len(all_accounts),
            platforms=platform_statuses,
            accounts=all_accounts,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client detail: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch client detail: {e}")


# ---------------------------------------------------------------------------
# GET /api/v1/clients/{client_id}/accounts — List connected accounts
# ---------------------------------------------------------------------------
@router.get("/{client_id}/accounts", response_model=AccountsListResponse)
async def list_connected_accounts(
    client_id: str,
    platform: Optional[str] = Query(None, description="Filter by platform (e.g. meta_ads)"),
    api_key: str = Depends(verify_api_key),
):
    """
    List all OAuth connections and manual credentials for a client.
    Optionally filter by platform.
    """
    db = credential_store.db
    if not db:
        raise HTTPException(status_code=503, detail="Firestore is not available")

    try:
        # Fetch both oauth connections and credentials subcollections in parallel
        oauth_ref = db.collection("clients").document(client_id).collection("oauth_connections")
        if platform:
            oauth_task = oauth_ref.where(filter=firestore.FieldFilter("platform", "==", platform)).get()
        else:
            oauth_task = oauth_ref.get()

        creds_ref = db.collection("clients").document(client_id).collection("credentials")
        if platform:
            creds_task = creds_ref.document(platform).get()
        else:
            creds_task = creds_ref.get()

        oauth_docs, creds_res = await asyncio.gather(oauth_task, creds_task)

        # Normalize credentials docs
        if platform:
            # creds_res is a DocumentSnapshot
            credentials_docs = [creds_res] if creds_res.exists else []
        else:
            # creds_res is a list of DocumentSnapshots
            credentials_docs = creds_res

        accounts: List[ConnectedAccount] = []

        # Process oauth connections
        for doc in oauth_docs:
            conn = doc.to_dict() or {}
            pval = conn.get("platform") or doc.id.split("_")[0]
            accounts.append(ConnectedAccount(
                platform=pval,
                account_id=conn.get("account_id"),
                account_name=conn.get("account_name"),
                connection_type="oauth",
                connected_at=conn.get("connected_at"),
                token_expires_at=conn.get("token_expires_at"),
            ))

        # Process manual credentials
        for doc in credentials_docs:
            manual_creds = doc.to_dict() or {}
            pval = doc.id
            accounts.append(ConnectedAccount(
                platform=pval,
                account_id=manual_creds.get("account_id"),
                account_name=manual_creds.get("account_name"),
                connection_type="manual",
            ))

        return AccountsListResponse(
            client_id=client_id,
            total_accounts=len(accounts),
            accounts=accounts,
        )

    except Exception as e:
        logger.error(f"Error listing connected accounts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list accounts: {e}")


# ---------------------------------------------------------------------------
# GET /api/v1/clients/{client_id}/reports/{platform} — Per-platform report
# ---------------------------------------------------------------------------
@router.get("/{client_id}/reports/{platform}", response_model=PlatformReportResponse)
async def get_platform_report(
    client_id: str,
    platform: str,
    start_date: str = Query(..., description="Start date YYYY-MM-DD"),
    end_date: str = Query(..., description="End date YYYY-MM-DD"),
    account_id: Optional[str] = Query(None, description="Specific account ID (uses first available if omitted)"),
    user_id: str = Query("system", description="User ID for audit trail"),
    api_key: str = Depends(verify_api_key),
):
    """
    Get a quick performance summary for a specific client + platform.

    Uses the same summarize_performance logic as the MCP tool —
    automatically selects default metrics for the platform type,
    translates to native names, and returns aggregated totals.
    """
    if platform not in ALL_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Invalid platform '{platform}'. Must be one of: {ALL_PLATFORMS}")

    # If no account_id provided, try to find the first connected account
    if not account_id:
        oauth_conns = await credential_store.list_oauth_connections(client_id, platform)
        if oauth_conns:
            account_id = oauth_conns[0].get("account_id", "")
        else:
            manual_creds = await credential_store.get_credentials(client_id, platform)
            if manual_creds:
                account_id = manual_creds.get("account_id", "")
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"No connected accounts found for client '{client_id}' on platform '{platform}'"
                )

    # Use the metric helpers to get defaults and translate
    from app.metrics import get_default_metrics, get_platform_type, validate_metrics, translate_to_generic

    generic_metrics = get_default_metrics(platform)
    ptype = get_platform_type(platform)
    native_metrics, metric_errors = validate_metrics(platform, generic_metrics)
    unsupported = [e["metric"] for e in metric_errors]

    if not native_metrics:
        return PlatformReportResponse(
            status="error",
            client_id=client_id,
            platform=platform,
            account_id=account_id,
            date_range={"start": start_date, "end": end_date},
            unsupported_metrics=unsupported,
        )

    # Fetch data through the dispatcher
    import asyncio
    from app.models.requests import DataRequest
    from app.services.dispatcher import dispatcher

    try:
        request_obj = DataRequest(
            platform=Platform(platform),
            start_date=start_date,
            end_date=end_date,
            metrics=native_metrics,
            client_id=client_id,
            user_id=user_id,
            account_id=account_id,
        )

        # Resolve credentials
        request_obj.credentials = await credential_store.resolve_credentials(
            client_id, platform, account_id or ""
        )

        connector = dispatcher.get_connector(Platform(platform))
        data = await asyncio.to_thread(connector.fetch_with_retry, request_obj)

        # Aggregate with generic names
        totals: Dict[str, float] = {}
        for row in data:
            row_metrics = row.get("metrics", {})
            translated = translate_to_generic(platform, row_metrics)
            for generic_name, value in translated.items():
                if value is not None and generic_name in generic_metrics:
                    try:
                        totals[generic_name] = totals.get(generic_name, 0.0) + float(value)
                    except (ValueError, TypeError):
                        pass

        return PlatformReportResponse(
            client_id=client_id,
            platform=platform,
            account_id=account_id,
            date_range={"start": start_date, "end": end_date},
            total_campaigns=len(data),
            aggregated_metrics=totals,
            unsupported_metrics=unsupported,
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating platform report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")
