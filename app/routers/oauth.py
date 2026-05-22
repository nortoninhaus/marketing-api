"""
Meta and general OAuth Router — Handles OAuth flows, token exchange, and account resolution.
"""

import base64
import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from fastapi import APIRouter, HTTPException, Query, Depends, status, Request
from fastapi.responses import RedirectResponse
from app.config import settings
from app.services.credential_store import credential_store
from app.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/oauth",
    tags=["OAuth Connections"]
)

@router.get("/authorize")
async def get_authorize_url(
    platform: str,
    client_id: str = "client_1",
    redirect_url: str = "http://127.0.0.1:5000",
    request: Request = None
):
    """
    Generates the authorization URL for the requested platform.
    Returns: {"url": auth_url, "authorization_url": auth_url}
    """
    if platform not in ["meta_ads", "meta_organic", "google_ads"]:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' is not supported for OAuth connections."
        )

    # Encode state containing client_id, platform and final redirect_url
    state_data = {
        "client_id": client_id,
        "platform": platform,
        "redirect_url": redirect_url
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    # Determine backend redirect URI
    if settings.meta_oauth_redirect_uri:
        backend_redirect_uri = settings.meta_oauth_redirect_uri
    else:
        # Generate dynamically from host
        host = request.headers.get("host", "127.0.0.1:8000")
        scheme = "https" if request.headers.get("x-forwarded-proto") == "https" or "run.app" in host else "http"
        backend_redirect_uri = f"{scheme}://{host}/api/v1/oauth/callback"

    if platform in ["meta_ads", "meta_organic"]:
        if not settings.meta_app_id:
            raise HTTPException(
                status_code=400,
                detail="Meta App ID is not configured on the backend. Please set META_APP_ID."
            )
        # Required scopes for both ads insights and organic page engagement
        scopes = "ads_read,pages_show_list,pages_read_engagement"
        auth_url = (
            f"https://www.facebook.com/v25.0/dialog/oauth"
            f"?client_id={settings.meta_app_id}"
            f"&redirect_uri={backend_redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )
        return {
            "url": auth_url,
            "authorization_url": auth_url
        }

    # Google Ads OAuth logic placeholder (extensible)
    elif platform == "google_ads":
        raise HTTPException(
            status_code=501,
            detail="Google Ads OAuth flow is under development. Please use manual developer tokens."
        )

@router.get("/callback")
async def oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    error_description: str = None,
    request: Request = None
):
    """
    Callback endpoint handles redirect from Meta, exchanges token, and registers connections.
    """
    if error:
        logger.error(f"OAuth Callback error: {error} - {error_description}")
        # Redirect back with error
        return RedirectResponse(url="http://127.0.0.1:5000/?oauth=error&message=AccessDenied")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required parameters code or state.")

    try:
        # Decode state
        state_bytes = base64.urlsafe_b64decode(state.encode())
        state_data = json.loads(state_bytes.decode())
        client_id = state_data.get("client_id", "client_1")
        platform = state_data.get("platform")
        redirect_url = state_data.get("redirect_url", "http://127.0.0.1:5000")
    except Exception as e:
        logger.error(f"Failed to decode OAuth state parameter: {e}")
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    # Determine callback redirect URI used in authorize request
    if settings.meta_oauth_redirect_uri:
        backend_redirect_uri = settings.meta_oauth_redirect_uri
    else:
        host = request.headers.get("host", "127.0.0.1:8000")
        scheme = "https" if request.headers.get("x-forwarded-proto") == "https" or "run.app" in host else "http"
        backend_redirect_uri = f"{scheme}://{host}/api/v1/oauth/callback"

    if platform in ["meta_ads", "meta_organic"]:
        if not settings.meta_app_id or not settings.meta_app_secret:
            raise HTTPException(status_code=500, detail="Meta App configuration missing on server.")

        async with httpx.AsyncClient() as client:
            # 1. Exchange authorization code for short-lived user access token
            token_url = "https://graph.facebook.com/v25.0/oauth/access_token"
            token_params = {
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "redirect_uri": backend_redirect_uri,
                "code": code
            }
            token_res = await client.get(token_url, params=token_params)
            if token_res.status_code != 200:
                logger.error(f"Short-lived token exchange failed: {token_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token exchange failed.")
            
            token_data = token_res.json()
            short_lived_token = token_data.get("access_token")

            # 2. Upgrade short-lived token to long-lived (60 days) user access token
            upgrade_params = {
                "grant_type": "fb_exchange_token",
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "fb_exchange_token": short_lived_token
            }
            upgrade_res = await client.get(token_url, params=upgrade_params)
            if upgrade_res.status_code != 200:
                logger.error(f"Long-lived token upgrade failed: {upgrade_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token upgrade failed.")
            
            upgrade_data = upgrade_res.json()
            long_lived_token = upgrade_data.get("access_token")

            # 3. Dynamic Discovery of Ad Accounts and Managed Pages
            # Fetch Ad Accounts (for meta_ads)
            adaccounts_url = "https://graph.facebook.com/v25.0/me/adaccounts"
            adaccounts_res = await client.get(
                adaccounts_url, 
                params={"fields": "id,name,account_id", "access_token": long_lived_token, "limit": 100}
            )
            if adaccounts_res.status_code == 200:
                adaccounts_data = adaccounts_res.json().get("data", [])
                for account in adaccounts_data:
                    account_id = account.get("id") # format act_123456
                    account_name = account.get("name", "Unnamed Ad Account")
                    # Save OAuth connection
                    await credential_store.save_oauth_connection(
                        client_id=client_id,
                        platform="meta_ads",
                        account_id=account_id,
                        account_name=account_name,
                        access_token=long_lived_token
                    )

            # Fetch Managed Pages (for meta_organic)
            pages_url = "https://graph.facebook.com/v25.0/me/accounts"
            pages_res = await client.get(
                pages_url,
                params={"fields": "id,name,access_token", "access_token": long_lived_token, "limit": 100}
            )
            if pages_res.status_code == 200:
                pages_data = pages_res.json().get("data", [])
                for page in pages_data:
                    page_id = page.get("id")
                    page_name = page.get("name", "Unnamed Page")
                    page_token = page.get("access_token") # Page Access Tokens do not expire!
                    await credential_store.save_oauth_connection(
                        client_id=client_id,
                        platform="meta_organic",
                        account_id=page_id,
                        account_name=page_name,
                        access_token=page_token
                    )

        # Successfully registered connections! Redirect back to Settings UI
        return RedirectResponse(url=f"{redirect_url}?oauth=success&platform={platform}")

    raise HTTPException(status_code=400, detail="Unsupported platform.")

@router.get("/connections")
async def list_connections(
    platform: str,
    client_id: str = "client_1",
    api_key: str = Depends(verify_api_key)
):
    """
    List connected accounts for the requested platform and client.
    """
    connections = await credential_store.list_oauth_connections(client_id, platform)
    # Map connections to clean list format for frontend settings screen
    return [
        {
            "account_id": conn.get("account_id"),
            "account_name": conn.get("account_name"),
            "platform": conn.get("platform"),
            "connected_at": conn.get("connected_at")
        }
        for conn in connections
    ]

@router.delete("/connections/{platform}/{account_id}")
async def disconnect_account(
    platform: str,
    account_id: str,
    client_id: str = "client_1",
    api_key: str = Depends(verify_api_key)
):
    """
    Disconnects (deletes) the specified OAuth account connection.
    """
    await credential_store.delete_oauth_connection(client_id, platform, account_id)
    return {"status": "success", "message": f"Successfully disconnected account {account_id}"}
