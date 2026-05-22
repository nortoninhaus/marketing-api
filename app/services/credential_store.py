"""
Firestore Credential Store — Manages platform credentials for multiple clients.
"""

import logging
from typing import Any, Dict, List, Optional
from google.cloud import firestore
from app.config import settings

logger = logging.getLogger(__name__)

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

    async def resolve_credentials(self, client_id: str, platform: str, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Resolves credentials for a specific request.
        1. First checks in clients/{client_id}/oauth_connections/{platform}_{account_id}
        2. Falls back to the general/manual credentials document clients/{client_id}/credentials/{platform}
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
                return {"access_token": data.get("access_token")}
        except Exception as e:
            logger.error(f"Error checking OAuth connections in Firestore: {e}")

        # Fallback to general/manual credentials
        return await self.get_credentials(client_id, platform)

    async def save_oauth_connection(self, client_id: str, platform: str, account_id: str, account_name: str, access_token: str):
        """Saves a dynamic OAuth connection to Firestore."""
        if not self.db:
            return

        try:
            conn_id = f"{platform}_{account_id}"
            doc_ref = self.db.collection("clients").document(client_id).collection("oauth_connections").document(conn_id)
            from datetime import datetime, timezone
            await doc_ref.set({
                "account_id": account_id,
                "account_name": account_name,
                "platform": platform,
                "access_token": access_token,
                "connected_at": datetime.now(timezone.utc).isoformat()
            })
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
