"""
OAuth Router — Handles OAuth flows for Meta and Google platforms.
Supports: Meta Ads, Meta Organic, Google Ads, GA4, YouTube.
"""

import base64
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
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

# ─── Google OAuth Scopes ───────────────────────────────────────────
GOOGLE_SCOPES = {
    "google_ads": "https://www.googleapis.com/auth/adwords",
    "ga4": "https://www.googleapis.com/auth/analytics.readonly",
    "youtube": " ".join([
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/yt-analytics.readonly",
    ]),
}

# All Google scopes combined for a single consent prompt
ALL_GOOGLE_SCOPES = " ".join(GOOGLE_SCOPES.values())

SUPPORTED_PLATFORMS = {"meta_ads", "meta_organic", "google_ads", "ga4", "youtube", "threads", "tiktok_ads", "tiktok_organic"}


def _build_meta_redirect_uri(request: Request) -> str:
    """Determine the Meta OAuth backend redirect URI."""
    if settings.meta_oauth_redirect_uri:
        return settings.meta_oauth_redirect_uri
    host = request.headers.get("host", "127.0.0.1:8000")
    scheme = "https" if request.headers.get("x-forwarded-proto") == "https" or "run.app" in host else "http"
    return f"{scheme}://{host}/api/v1/oauth/callback"


def _build_threads_redirect_uri(request: Request) -> str:
    """Determine the Threads OAuth backend redirect URI."""
    return _build_meta_redirect_uri(request)


def _build_google_redirect_uri(request: Request) -> str:
    """Determine the Google OAuth backend redirect URI."""
    if settings.google_oauth_redirect_uri:
        return settings.google_oauth_redirect_uri
    host = request.headers.get("host", "127.0.0.1:8000")
    scheme = "https" if request.headers.get("x-forwarded-proto") == "https" or "run.app" in host else "http"
    return f"{scheme}://{host}/api/v1/oauth/google-callback"


# ═══════════════════════════════════════════════════════════════════
# AUTHORIZE — Generate redirect URL for user consent
# ═══════════════════════════════════════════════════════════════════

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
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=400,
            detail=f"Platform '{platform}' is not supported for OAuth connections. Supported: {', '.join(SUPPORTED_PLATFORMS)}"
        )

    # Encode state containing client_id, platform and final redirect_url
    state_data = {
        "client_id": client_id,
        "platform": platform,
        "redirect_url": redirect_url
    }
    state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

    # ─── Meta Platforms ────────────────────────────────────────────
    if platform in ("meta_ads", "meta_organic"):
        if not settings.meta_app_id:
            raise HTTPException(
                status_code=400,
                detail="Meta App ID is not configured on the backend. Please set META_APP_ID."
            )
        backend_redirect_uri = _build_meta_redirect_uri(request)
        # Use configurable scopes from settings
        scopes = settings.meta_oauth_scopes
        auth_url = (
            f"https://www.facebook.com/v25.0/dialog/oauth"
            f"?client_id={settings.meta_app_id}"
            f"&redirect_uri={backend_redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )
        return {"url": auth_url, "authorization_url": auth_url}

    # ─── Threads Platform ──────────────────────────────────────────
    if platform == "threads":
        if not settings.meta_app_id:
            raise HTTPException(
                status_code=400,
                detail="Meta App ID is not configured on the backend. Please set META_APP_ID."
            )
        backend_redirect_uri = _build_threads_redirect_uri(request)
        scopes = "threads_basic,threads_manage_insights"
        auth_url = (
            f"https://threads.net/oauth/authorize"
            f"?client_id={settings.meta_app_id}"
            f"&redirect_uri={backend_redirect_uri}"
            f"&scope={scopes}"
            f"&state={state}"
            f"&response_type=code"
        )
        return {"url": auth_url, "authorization_url": auth_url}

    # ─── Google Platforms ──────────────────────────────────────────
    if platform in ("google_ads", "ga4", "youtube"):
        google_client_id = settings.google_client_id or settings.google_ads_client_id
        if not google_client_id:
            raise HTTPException(
                status_code=400,
                detail="Google Client ID is not configured on the backend. Please set GOOGLE_CLIENT_ID or GOOGLE_ADS_CLIENT_ID."
            )
        backend_redirect_uri = _build_google_redirect_uri(request)
        # Request all Google scopes in one consent for broad access
        scope = ALL_GOOGLE_SCOPES
        auth_url = (
            f"https://accounts.google.com/o/oauth2/v2/auth?"
            + urlencode({
                "client_id": google_client_id,
                "redirect_uri": backend_redirect_uri,
                "scope": scope,
                "state": state,
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
            })
        )
        return {"url": auth_url, "authorization_url": auth_url}

    # ─── TikTok Platforms ──────────────────────────────────────────
    if platform == "tiktok_ads":
        tiktok_client_id = settings.tiktok_ads_sandbox_app_id if settings.use_tiktok_sandbox else settings.tiktok_ads_app_id
        if not tiktok_client_id:
            raise HTTPException(
                status_code=400,
                detail="TikTok Client ID (App ID) is not configured on the backend. Please set TIKTOK_ADS_APP_ID or TIKTOK_ADS_SANDBOX_APP_ID."
            )
        # TikTok Ads OAuth strictly requires a numeric App ID. Alphanumeric Client Keys will fail on TikTok's side.
        if not tiktok_client_id.isdigit():
            raise HTTPException(
                status_code=400,
                detail=f"TikTok Ads strictly requires a numeric App ID (like '{settings.tiktok_ads_app_id or '7621197369555666962'}'), but received alphanumeric key '{tiktok_client_id}'. "
                       f"Please ensure TIKTOK_ADS_SANDBOX_APP_ID is configured with the numeric App ID of your sandbox app, or toggle off sandbox mode for Ads."
            )
        backend_redirect_uri = _build_meta_redirect_uri(request)
        auth_url = (
            f"https://business-api.tiktok.com/portal/auth?"
            + urlencode({
                "app_id": tiktok_client_id,
                "state": state,
                "redirect_uri": backend_redirect_uri,
            })
        )
        return {"url": auth_url, "authorization_url": auth_url}

    if platform == "tiktok_organic":
        tiktok_client_id = settings.tiktok_organic_sandbox_client_key if settings.use_tiktok_sandbox else settings.tiktok_client_key
        if not tiktok_client_id:
            raise HTTPException(
                status_code=400,
                detail="TikTok Client Key is not configured on the backend. Please set TIKTOK_CLIENT_KEY."
            )
        backend_redirect_uri = _build_meta_redirect_uri(request)
        base_url = "https://open-sandbox.tiktokapis.com/v2/auth/authorize/" if settings.use_tiktok_sandbox else "https://www.tiktok.com/v2/auth/authorize/"
        auth_url = (
            f"{base_url}?"
            + urlencode({
                "client_key": tiktok_client_id,
                "scope": "user.info.basic,video.list",
                "response_type": "code",
                "state": state,
                "redirect_uri": backend_redirect_uri,
            })
        )
        return {"url": auth_url, "authorization_url": auth_url}


# ═══════════════════════════════════════════════════════════════════
# META CALLBACK — Token exchange + dynamic discovery
# ═══════════════════════════════════════════════════════════════════

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
        return RedirectResponse(url="http://127.0.0.1:5000/?oauth=error&message=AccessDenied")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required parameters code or state.")

    try:
        state_bytes = base64.urlsafe_b64decode(state.encode())
        state_data = json.loads(state_bytes.decode())
        client_id = state_data.get("client_id", "client_1")
        platform = state_data.get("platform")
        redirect_url = state_data.get("redirect_url", "http://127.0.0.1:5000")
    except Exception as e:
        logger.error(f"Failed to decode OAuth state parameter: {e}")
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    backend_redirect_uri = _build_meta_redirect_uri(request)

    if platform in ("meta_ads", "meta_organic"):
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

            # 3. Discover Ad Accounts (for meta_ads)
            adaccounts_url = "https://graph.facebook.com/v25.0/me/adaccounts"
            adaccounts_res = await client.get(
                adaccounts_url,
                params={"fields": "id,name,account_id", "access_token": long_lived_token, "limit": 100}
            )
            if adaccounts_res.status_code == 200:
                adaccounts_data = adaccounts_res.json().get("data", [])
                for account in adaccounts_data:
                    account_id = account.get("id")  # format act_123456
                    account_name = account.get("name", "Unnamed Ad Account")
                    await credential_store.save_oauth_connection(
                        client_id=client_id,
                        platform="meta_ads",
                        account_id=account_id,
                        account_name=account_name,
                        access_token=long_lived_token
                    )

            # 4. Discover Pages AND linked Instagram Business Accounts
            pages_url = "https://graph.facebook.com/v25.0/me/accounts"
            pages_res = await client.get(
                pages_url,
                params={
                    "fields": "id,name,access_token,instagram_business_account{id,username,name}",
                    "access_token": long_lived_token,
                    "limit": 100,
                }
            )
            if pages_res.status_code == 200:
                pages_data = pages_res.json().get("data", [])
                for page in pages_data:
                    page_id = page.get("id")
                    page_name = page.get("name", "Unnamed Page")
                    page_token = page.get("access_token")  # Page Access Tokens do not expire!
                    # Save Facebook Page connection
                    await credential_store.save_oauth_connection(
                        client_id=client_id,
                        platform="meta_organic",
                        account_id=page_id,
                        account_name=page_name,
                        access_token=page_token
                    )
                    # Check for linked Instagram Business Account
                    ig_account = page.get("instagram_business_account")
                    if ig_account:
                        ig_id = ig_account.get("id")
                        ig_username = ig_account.get("username", "")
                        ig_name = ig_account.get("name", ig_username or "Instagram Account")
                        await credential_store.save_oauth_connection(
                            client_id=client_id,
                            platform="meta_organic",
                            account_id=ig_id,
                            account_name=f"IG: {ig_name}",
                            access_token=page_token,
                            extra_data={
                                "is_instagram": True,
                                "page_id": page_id,
                                "instagram_username": ig_username,
                            }
                        )

        return RedirectResponse(url=f"{redirect_url}?oauth=success&platform={platform}")

    elif platform == "threads":
        if not settings.meta_app_id or not settings.meta_app_secret:
            raise HTTPException(status_code=500, detail="Meta App configuration missing on server.")

        backend_redirect_uri = _build_threads_redirect_uri(request)
        async with httpx.AsyncClient() as client:
            # 1. Exchange authorization code for short-lived access token
            token_url = "https://graph.threads.net/oauth/access_token"
            token_data = {
                "client_id": settings.meta_app_id,
                "client_secret": settings.meta_app_secret,
                "grant_type": "authorization_code",
                "redirect_uri": backend_redirect_uri,
                "code": code
            }
            token_res = await client.post(token_url, data=token_data)
            if token_res.status_code != 200:
                logger.error(f"Threads short-lived token exchange failed: {token_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Threads token exchange failed.")

            short_lived_token = token_res.json().get("access_token")

            # 2. Upgrade short-lived token to long-lived (60 days) access token
            long_lived_url = "https://graph.threads.net/access_token"
            long_lived_params = {
                "grant_type": "th_exchange_token",
                "client_secret": settings.meta_app_secret,
                "access_token": short_lived_token
            }
            long_lived_res = await client.get(long_lived_url, params=long_lived_params)
            if long_lived_res.status_code != 200:
                logger.error(f"Threads long-lived token upgrade failed: {long_lived_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Threads token upgrade failed.")

            long_lived_data = long_lived_res.json()
            long_lived_token = long_lived_data.get("access_token")
            expires_in = long_lived_data.get("expires_in", 5184000)
            token_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

            # 3. Discover user profile
            me_res = await client.get(
                "https://graph.threads.net/v1.0/me",
                params={
                    "fields": "id,username,name,threads_profile_picture_url",
                    "access_token": long_lived_token
                }
            )
            if me_res.status_code == 200:
                me_data = me_res.json()
                threads_user_id = me_data.get("id")
                username = me_data.get("username", "threads_user")
                name = me_data.get("name", username)

                await credential_store.save_oauth_connection(
                    client_id=client_id,
                    platform="threads",
                    account_id=threads_user_id,
                    account_name=f"Threads: {name}",
                    access_token=long_lived_token,
                    token_expires_at=token_expires_at,
                    extra_data={
                        "username": username,
                        "threads_profile_picture_url": me_data.get("threads_profile_picture_url", "")
                    }
                )
            else:
                logger.error(f"Threads profile query failed: {me_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Threads profile query failed.")

        return RedirectResponse(url=f"{redirect_url}?oauth=success&platform={platform}")

    elif platform == "tiktok_ads":
        app_id = settings.tiktok_ads_sandbox_app_id if settings.use_tiktok_sandbox else settings.tiktok_ads_app_id
        secret = settings.tiktok_ads_sandbox_secret if settings.use_tiktok_sandbox else settings.tiktok_ads_secret
        if not app_id or not secret:
            raise HTTPException(status_code=500, detail="TikTok Ads configuration missing on server.")

        async with httpx.AsyncClient() as client:
            token_url = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
            token_payload = {
                "app_id": app_id,
                "secret": secret,
                "auth_code": code
            }
            token_res = await client.post(token_url, json=token_payload)
            if token_res.status_code != 200:
                logger.error(f"TikTok Ads token exchange failed: {token_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TikTok Ads token exchange failed.")

            token_data = token_res.json()
            if token_data.get("code") != 0:
                logger.error(f"TikTok Ads token response error: {token_data}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"TikTok Ads token exchange error: {token_data.get('message')}")

            access_token = token_data.get("data", {}).get("access_token")
            advertiser_ids = token_data.get("data", {}).get("advertiser_ids", [])
            
            if advertiser_ids:
                info_url = "https://business-api.tiktok.com/open_api/v1.3/advertiser/info/"
                info_res = await client.get(
                    info_url,
                    params={"advertiser_ids": json.dumps(advertiser_ids)},
                    headers={"Access-Token": access_token}
                )
                if info_res.status_code == 200:
                    info_data = info_res.json()
                    advertisers = info_data.get("data", {}).get("list", [])
                    for adv in advertisers:
                        await credential_store.save_oauth_connection(
                            client_id=client_id,
                            platform="tiktok_ads",
                            account_id=str(adv.get("advertiser_id")),
                            account_name=adv.get("advertiser_name", f"TikTok Ads {adv.get('advertiser_id')}"),
                            access_token=access_token
                        )
                else:
                    for adv_id in advertiser_ids:
                        await credential_store.save_oauth_connection(
                            client_id=client_id,
                            platform="tiktok_ads",
                            account_id=str(adv_id),
                            account_name=f"TikTok Ads {adv_id}",
                            access_token=access_token
                        )
            else:
                await credential_store.save_oauth_connection(
                    client_id=client_id,
                    platform="tiktok_ads",
                    account_id="default",
                    account_name="TikTok Ads Connected",
                    access_token=access_token
                )

        return RedirectResponse(url=f"{redirect_url}?oauth=success&platform={platform}")

    elif platform == "tiktok_organic":
        client_key = settings.tiktok_organic_sandbox_client_key if settings.use_tiktok_sandbox else settings.tiktok_client_key
        client_secret = settings.tiktok_organic_sandbox_secret if settings.use_tiktok_sandbox else settings.tiktok_client_secret
        if not client_key or not client_secret:
            raise HTTPException(status_code=500, detail="TikTok Organic configuration missing on server.")

        base_url = "https://open-sandbox.tiktokapis.com" if settings.use_tiktok_sandbox else "https://open.tiktokapis.com"
        async with httpx.AsyncClient() as client:
            token_url = f"{base_url}/v2/oauth/token/"
            token_data = {
                "client_key": client_key,
                "client_secret": client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": backend_redirect_uri
            }
            token_res = await client.post(token_url, data=token_data)
            if token_res.status_code != 200:
                logger.error(f"TikTok Organic token exchange failed: {token_res.text}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TikTok Organic token exchange failed.")

            res_json = token_res.json()
            access_token = res_json.get("access_token")
            open_id = res_json.get("open_id")
            refresh_token = res_json.get("refresh_token")
            expires_in = res_json.get("expires_in", 86400)
            token_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

            user_info_url = f"{base_url}/v2/user/info/"
            user_res = await client.get(
                user_info_url,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"fields": "username,display_name"}
            )
            account_name = "TikTok User"
            if user_res.status_code == 200:
                user_data = user_res.json().get("data", {}).get("user", {})
                account_name = user_data.get("display_name") or user_data.get("username") or "TikTok User"

            await credential_store.save_oauth_connection(
                client_id=client_id,
                platform="tiktok_organic",
                account_id=open_id or "default_organic",
                account_name=account_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at
            )

        return RedirectResponse(url=f"{redirect_url}?oauth=success&platform={platform}")

    raise HTTPException(status_code=400, detail="Unsupported platform.")


# ═══════════════════════════════════════════════════════════════════
# GOOGLE CALLBACK — Token exchange + dynamic discovery
# ═══════════════════════════════════════════════════════════════════

@router.get("/google-callback")
async def google_oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    request: Request = None
):
    """
    Callback endpoint for Google OAuth. Exchanges code for tokens and discovers
    Google Ads accounts, GA4 properties, and YouTube channels.
    """
    if error:
        logger.error(f"Google OAuth Callback error: {error}")
        return RedirectResponse(url="http://127.0.0.1:5000/?oauth=error&message=GoogleAccessDenied")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required parameters code or state.")

    try:
        state_bytes = base64.urlsafe_b64decode(state.encode())
        state_data = json.loads(state_bytes.decode())
        client_id = state_data.get("client_id", "client_1")
        platform = state_data.get("platform")
        redirect_url = state_data.get("redirect_url", "http://127.0.0.1:5000")
    except Exception as e:
        logger.error(f"Failed to decode Google OAuth state parameter: {e}")
        raise HTTPException(status_code=400, detail="Invalid state parameter.")

    backend_redirect_uri = _build_google_redirect_uri(request)

    # 1. Exchange authorization code for access + refresh tokens
    google_client_id = settings.google_client_id or settings.google_ads_client_id
    google_client_secret = settings.google_client_secret or settings.google_ads_client_secret
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": google_client_id,
                "client_secret": google_client_secret,
                "redirect_uri": backend_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code != 200:
            logger.error(f"Google token exchange failed: {token_res.text}")
            raise HTTPException(status_code=400, detail="Google token exchange failed.")

        token_data = token_res.json()
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        token_expires_at = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

        headers = {"Authorization": f"Bearer {access_token}"}

        # 2. Discover Google Ads Accounts (via Customer Service)
        try:
            ads_res = await client.get(
                "https://googleads.googleapis.com/v18/customers:listAccessibleCustomers",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "developer-token": settings.google_ads_developer_token,
                },
            )
            if ads_res.status_code == 404:
                logger.info("Google Ads v18 discovery returned 404. Falling back to v17...")
                ads_res = await client.get(
                    "https://googleads.googleapis.com/v17/customers:listAccessibleCustomers",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "developer-token": settings.google_ads_developer_token,
                    },
                )
            if ads_res.status_code == 200:
                customer_names = ads_res.json().get("resourceNames", [])
                for name in customer_names:
                    # format: "customers/1234567890"
                    cid = name.split("/")[-1]
                    await credential_store.save_oauth_connection(
                        client_id=client_id,
                        platform="google_ads",
                        account_id=cid,
                        account_name=f"Google Ads {cid}",
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expires_at=token_expires_at,
                        extra_data={"developer_token": settings.google_ads_developer_token},
                    )
                logger.info(f"Discovered {len(customer_names)} Google Ads accounts")
            else:
                logger.warning(f"Google Ads discovery returned {ads_res.status_code}: {ads_res.text}")
        except Exception as e:
            logger.warning(f"Google Ads discovery failed (non-fatal): {e}")

        # 3. Discover GA4 Properties
        try:
            ga4_res = await client.get(
                "https://analyticsadmin.googleapis.com/v1beta/accountSummaries",
                headers=headers,
            )
            if ga4_res.status_code == 200:
                summaries = ga4_res.json().get("accountSummaries", [])
                for summary in summaries:
                    for prop in summary.get("propertySummaries", []):
                        property_id = prop.get("property", "").replace("properties/", "")
                        display_name = prop.get("displayName", f"GA4 Property {property_id}")
                        await credential_store.save_oauth_connection(
                            client_id=client_id,
                            platform="ga4",
                            account_id=property_id,
                            account_name=display_name,
                            access_token=access_token,
                            refresh_token=refresh_token,
                            token_expires_at=token_expires_at,
                        )
                logger.info(f"Discovered GA4 properties from {len(summaries)} accounts")
            else:
                logger.warning(f"GA4 discovery returned {ga4_res.status_code}: {ga4_res.text}")
        except Exception as e:
            logger.warning(f"GA4 discovery failed (non-fatal): {e}")

        # 4. Discover YouTube Channels
        try:
            yt_res = await client.get(
                "https://www.googleapis.com/youtube/v3/channels",
                params={"part": "snippet,statistics", "mine": "true"},
                headers=headers,
            )
            if yt_res.status_code == 200:
                channels = yt_res.json().get("items", [])
                for ch in channels:
                    ch_id = ch.get("id")
                    ch_title = ch.get("snippet", {}).get("title", f"YouTube Channel {ch_id}")
                    await credential_store.save_oauth_connection(
                        client_id=client_id,
                        platform="youtube",
                        account_id=ch_id,
                        account_name=ch_title,
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expires_at=token_expires_at,
                    )
                logger.info(f"Discovered {len(channels)} YouTube channels")
            else:
                logger.warning(f"YouTube discovery returned {yt_res.status_code}: {yt_res.text}")
        except Exception as e:
            logger.warning(f"YouTube discovery failed (non-fatal): {e}")

    return RedirectResponse(url=f"{redirect_url}?oauth=success&platform={platform}")


# ═══════════════════════════════════════════════════════════════════
# LIST / DELETE CONNECTIONS
# ═══════════════════════════════════════════════════════════════════

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
    return [
        {
            "account_id": conn.get("account_id"),
            "account_name": conn.get("account_name"),
            "platform": conn.get("platform"),
            "connected_at": conn.get("connected_at"),
            "is_instagram": conn.get("is_instagram", False),
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
