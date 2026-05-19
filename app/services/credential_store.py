"""
Firestore Credential Store — Manages platform credentials for multiple clients.
"""

import logging
from typing import Any, Dict, Optional
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
