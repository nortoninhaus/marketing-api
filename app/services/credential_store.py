"""
Firestore Credential Store — Manages platform credentials for multiple clients.
Supports token refresh for Google OAuth credentials.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import httpx
from google.cloud import firestore
from app.config import settings

logger = logging.getLogger(__name__)

# Google platforms that use OAuth and need token refresh
GOOGLE_OAUTH_PLATFORMS = {"google_ads", "ga4", "youtube"}


class CredentialStore:
    def __init__(self):
        self.db: Optional[firestore.AsyncClient] = None
        try:
            # Assumes GOOGLE_APPLICATION_CREDENTIALS or default auth is set
            self.db = firestore.AsyncClient()
            logger.info("Firestore async client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Firestore async client: {e}")

    async def get_credentials(self, client_id: str, platform: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves credentials for a specific client and platform from Firestore.
        Path: clients/{client_id}/credentials/{platform}
        """
        if not self.db:
            return None

        try:
            doc_ref = self.db.collection("clients").document(client_id).collection("credentials").document(platform)
            doc = await doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            else:
                logger.warning(f"No credentials found for client {client_id} and platform {platform}")
                return None
        except Exception as e:
            logger.error(f"Error fetching credentials from Firestore: {e}")
            return None

    async def _refresh_google_token(self, data: Dict[str, Any], doc_ref) -> Dict[str, Any]:
        """
        Refreshes a Google OAuth access token using the stored refresh_token.
        Updates the Firestore document with the new access_token and expiry.
        Returns the updated credential dict.
        """
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            logger.warning("No refresh_token available for Google token refresh")
            return data

        client_id = settings.google_client_id or settings.google_ads_client_id
        client_secret = settings.google_client_secret or settings.google_ads_client_secret

        if not client_id or not client_secret:
            logger.warning("Google client_id/client_secret not configured for token refresh")
            return data

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    new_access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 3600)
                    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    # Update Firestore document
                    await doc_ref.update({
                        "access_token": new_access_token,
                        "token_expires_at": new_expiry.isoformat(),
                    })
                    data["access_token"] = new_access_token
                    data["token_expires_at"] = new_expiry.isoformat()
                    logger.info("Successfully refreshed Google access token")
                else:
                    logger.error(f"Google token refresh failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error refreshing Google token: {e}")

        return data

    def _is_token_expired(self, data: Dict[str, Any]) -> bool:
        """Check if the stored access_token is expired or about to expire (5 min buffer)."""
        expires_at_str = data.get("token_expires_at")
        if not expires_at_str:
            # No expiry tracked — assume expired to be safe
            return True
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= (expires_at - timedelta(minutes=5))
        except (ValueError, TypeError):
            return True

    def _is_token_close_to_expiry(self, data: Dict[str, Any], days_buffer: int = 15) -> bool:
        """Check if the stored access_token is close to expiring (within buffer days)."""
        expires_at_str = data.get("token_expires_at")
        if not expires_at_str:
            # No expiry tracked — assume close to expiry to be safe
            return True
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc) >= (expires_at - timedelta(days=days_buffer))
        except (ValueError, TypeError):
            return True

    async def _refresh_meta_token(self, data: Dict[str, Any], doc_ref) -> Dict[str, Any]:
        """
        Refreshes a Meta long-lived access token using the active token.
        Updates the Firestore document with the new access_token and expiry.
        """
        access_token = data.get("access_token")
        if not access_token:
            logger.warning("No access_token available for Meta token refresh")
            return data

        if not settings.meta_app_id or not settings.meta_app_secret:
            logger.warning("Meta App ID/Secret not configured for token refresh")
            return data

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://graph.facebook.com/v25.0/oauth/access_token",
                    params={
                        "grant_type": "fb_exchange_token",
                        "client_id": settings.meta_app_id,
                        "client_secret": settings.meta_app_secret,
                        "fb_exchange_token": access_token,
                    },
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    new_access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 5184000)  # Default 60 days
                    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    # Update Firestore document
                    await doc_ref.update({
                        "access_token": new_access_token,
                        "token_expires_at": new_expiry.isoformat(),
                    })
                    data["access_token"] = new_access_token
                    data["token_expires_at"] = new_expiry.isoformat()
                    logger.info("Successfully refreshed Meta access token")
                else:
                    logger.error(f"Meta token refresh failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error refreshing Meta token: {e}")

        return data

    async def _refresh_threads_token(self, data: Dict[str, Any], doc_ref) -> Dict[str, Any]:
        """
        Refreshes a Threads long-lived access token using the active token.
        Updates the Firestore document with the new access_token and expiry.
        """
        access_token = data.get("access_token")
        if not access_token:
            logger.warning("No access_token available for Threads token refresh")
            return data

        if not settings.meta_app_secret:
            logger.warning("Meta App Secret not configured for Threads token refresh")
            return data

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://graph.threads.net/access_token",
                    params={
                        "grant_type": "th_exchange_token",
                        "client_secret": settings.meta_app_secret,
                        "access_token": access_token,
                    },
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    new_access_token = token_data["access_token"]
                    expires_in = token_data.get("expires_in", 5184000)  # Default 60 days
                    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    # Update Firestore document
                    await doc_ref.update({
                        "access_token": new_access_token,
                        "token_expires_at": new_expiry.isoformat(),
                    })
                    data["access_token"] = new_access_token
                    data["token_expires_at"] = new_expiry.isoformat()
                    logger.info("Successfully refreshed Threads access token")
                else:
                    logger.error(f"Threads token refresh failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error refreshing Threads token: {e}")

        return data

    async def _refresh_ghl_token(self, data: Dict[str, Any], doc_ref) -> Dict[str, Any]:
        """
        Refreshes a GoHighLevel OAuth access token using the stored refresh_token.
        Updates the Firestore document with the new access_token, refresh_token, and expiry.
        Returns the updated credential dict.
        """
        refresh_token = data.get("refresh_token")
        if not refresh_token:
            logger.warning("No refresh_token available for GHL token refresh")
            return data

        client_id = settings.ghl_client_id
        client_secret = settings.ghl_client_secret

        if not client_id or not client_secret:
            logger.warning("GHL client_id/client_secret not configured for token refresh")
            return data

        user_type = data.get("user_type") or data.get("userType") or "Location"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://services.leadconnectorhq.com/oauth/token",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                        "user_type": user_type,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if resp.status_code == 200:
                    token_data = resp.json()
                    new_access_token = token_data["access_token"]
                    new_refresh_token = token_data.get("refresh_token", refresh_token)
                    expires_in = token_data.get("expires_in", 86399)
                    new_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

                    # Update Firestore document
                    update_payload = {
                        "access_token": new_access_token,
                        "refresh_token": new_refresh_token,
                        "token_expires_at": new_expiry.isoformat(),
                    }
                    if "userType" in token_data:
                        update_payload["user_type"] = token_data["userType"]
                    await doc_ref.update(update_payload)

                    data["access_token"] = new_access_token
                    data["refresh_token"] = new_refresh_token
                    data["token_expires_at"] = new_expiry.isoformat()
                    if "userType" in token_data:
                        data["user_type"] = token_data["userType"]
                    logger.info("Successfully refreshed GHL access token")
                else:
                    logger.error(f"GHL token refresh failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            logger.error(f"Error refreshing GHL token: {e}")

        return data

    async def resolve_credentials(self, client_id: str, platform: str, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolves credentials for a specific request.
        1. First checks in clients/{client_id}/oauth_connections/{platform}_{account_id}
        2. Falls back to the general/manual credentials document clients/{client_id}/credentials/{platform}
        3. For Google platforms, refreshes access_token if expired.
        4. For Meta and Threads platforms, refreshes access_token if close to expiry.
        5. For GHL, refreshes access_token if expired.
        """
        if not self.db:
            return None

        try:
            conn_id = f"{platform}_{account_id}"
            doc_ref = self.db.collection("clients").document(client_id).collection("oauth_connections").document(conn_id)
            doc = await doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                logger.info(f"Resolved OAuth credentials for {platform} and account {account_id}")

                # Refresh Google tokens if expired
                if platform in GOOGLE_OAUTH_PLATFORMS and self._is_token_expired(data):
                    logger.info(f"Access token expired for {platform}/{account_id}, refreshing...")
                    data = await self._refresh_google_token(data, doc_ref)

                # Refresh Meta tokens if close to expiring (only if token_expires_at is set, to skip permanent page tokens)
                elif platform in {"meta_ads", "meta_organic"} and data.get("token_expires_at") and self._is_token_close_to_expiry(data):
                    logger.info(f"Access token close to expiry for {platform}/{account_id}, refreshing...")
                    data = await self._refresh_meta_token(data, doc_ref)

                # Refresh Threads tokens if close to expiring
                elif platform == "threads" and self._is_token_close_to_expiry(data):
                    logger.info(f"Access token close to expiry for Threads {account_id}, refreshing...")
                    data = await self._refresh_threads_token(data, doc_ref)

                # Refresh GHL tokens if expired
                elif platform == "ghl" and self._is_token_expired(data):
                    logger.info(f"Access token expired for GHL {account_id}, refreshing...")
                    data = await self._refresh_ghl_token(data, doc_ref)

                return data  # Returns full dict including access_token, refresh_token, etc.
        except Exception as e:
            logger.error(f"Error checking OAuth connections in Firestore: {e}")

        # Fallback to general/manual credentials
        return await self.get_credentials(client_id, platform)

    async def save_oauth_connection(
        self,
        client_id: str,
        platform: str,
        account_id: str,
        account_name: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        token_expires_at: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ):
        """Saves a dynamic OAuth connection to Firestore."""
        if not self.db:
            return

        try:
            conn_id = f"{platform}_{account_id}"
            doc_ref = self.db.collection("clients").document(client_id).collection("oauth_connections").document(conn_id)
            doc_data = {
                "account_id": account_id,
                "account_name": account_name,
                "platform": platform,
                "access_token": access_token,
                "connected_at": datetime.now(timezone.utc).isoformat()
            }
            if refresh_token:
                doc_data["refresh_token"] = refresh_token
            if token_expires_at:
                doc_data["token_expires_at"] = token_expires_at
            if extra_data:
                doc_data.update(extra_data)
            await doc_ref.set(doc_data)
            logger.info(f"Saved OAuth connection {conn_id} for client {client_id}")
        except Exception as e:
            logger.error(f"Error saving OAuth connection to Firestore: {e}")

    async def list_oauth_connections(self, client_id: str, platform: str) -> List[Dict[str, Any]]:
        """Lists connected OAuth accounts for a given client and platform."""
        if not self.db:
            return []

        try:
            connections_ref = self.db.collection("clients").document(client_id).collection("oauth_connections")
            query = connections_ref.where(filter=firestore.FieldFilter("platform", "==", platform))
            docs = await query.get()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error listing OAuth connections from Firestore: {e}")
            return []

    async def delete_oauth_connection(self, client_id: str, platform: str, account_id: str):
        """Deletes a connected OAuth account from Firestore."""
        if not self.db:
            return

        try:
            conn_id = f"{platform}_{account_id}"
            doc_ref = self.db.collection("clients").document(client_id).collection("oauth_connections").document(conn_id)
            await doc_ref.delete()
            logger.info(f"Deleted OAuth connection {conn_id} for client {client_id}")
        except Exception as e:
            logger.error(f"Error deleting OAuth connection from Firestore: {e}")

    async def save_credentials(self, client_id: str, platform: str, credentials: Dict[str, Any]):
        """Saves or updates credentials for a client."""
        if not self.db:
            return

        try:
            doc_ref = self.db.collection("clients").document(client_id).collection("credentials").document(platform)
            await doc_ref.set(credentials)
            logger.info(f"Saved credentials for client {client_id} and platform {platform}")
        except Exception as e:
            logger.error(f"Error saving credentials to Firestore: {e}")

# Global instance
credential_store = CredentialStore()
