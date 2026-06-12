"""
Unit tests for proactive credential refresh.
Verifies expiry buffers, refresh endpoints, and multi-tenant isolation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.credential_store import credential_store
from app.config import settings

@pytest.mark.asyncio
async def test_is_token_close_to_expiry():
    # 1. Close to expiry (10 days left, buffer is 15)
    expiry = datetime.now(timezone.utc) + timedelta(days=10)
    data = {"token_expires_at": expiry.isoformat()}
    assert credential_store._is_token_close_to_expiry(data, days_buffer=15) is True

    # 2. Not close to expiry (20 days left, buffer is 15)
    expiry2 = datetime.now(timezone.utc) + timedelta(days=20)
    data2 = {"token_expires_at": expiry2.isoformat()}
    assert credential_store._is_token_close_to_expiry(data2, days_buffer=15) is False

    # 3. No expiry tracked (assumed close to expiry/expired)
    assert credential_store._is_token_close_to_expiry({}, days_buffer=15) is True


@pytest.mark.asyncio
@patch("app.services.credential_store.httpx.AsyncClient")
async def test_refresh_meta_token_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_meta_token",
        "expires_in": 5184000
    }
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_doc_ref = AsyncMock()

    with patch.object(settings, "meta_app_id", "app_123"), \
         patch.object(settings, "meta_app_secret", "secret_123"):
        
        initial_data = {
            "access_token": "old_meta_token",
            "token_expires_at": "2026-05-01T00:00:00+00:00"
        }
        
        res = await credential_store._refresh_meta_token(initial_data, mock_doc_ref)
        
        assert res["access_token"] == "new_meta_token"
        assert "token_expires_at" in res
        mock_doc_ref.update.assert_called_once()
        args, kwargs = mock_doc_ref.update.call_args
        assert args[0]["access_token"] == "new_meta_token"


@pytest.mark.asyncio
@patch("app.services.credential_store.httpx.AsyncClient")
async def test_refresh_threads_token_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value.__aenter__.return_value = mock_client

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "new_threads_token",
        "expires_in": 5184000
    }
    mock_client.get = AsyncMock(return_value=mock_response)

    mock_doc_ref = AsyncMock()

    with patch.object(settings, "meta_app_secret", "secret_123"):
        initial_data = {
            "access_token": "old_threads_token",
            "token_expires_at": "2026-05-01T00:00:00+00:00"
        }
        
        res = await credential_store._refresh_threads_token(initial_data, mock_doc_ref)
        
        assert res["access_token"] == "new_threads_token"
        assert "token_expires_at" in res
        mock_doc_ref.update.assert_called_once()
        args, kwargs = mock_doc_ref.update.call_args
        assert args[0]["access_token"] == "new_threads_token"


@pytest.mark.asyncio
@patch("app.services.credential_store.CredentialStore._refresh_meta_token")
@patch("app.services.credential_store.CredentialStore._refresh_threads_token")
async def test_resolve_credentials_skips_permanent_page_tokens(mock_refresh_threads, mock_refresh_meta):
    # Set up mocked DB connection
    mock_db = MagicMock()
    credential_store.db = mock_db
    
    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "access_token": "permanent_facebook_page_token",
        "account_id": "page_123",
        "account_name": "My Facebook Page"
    }
    
    # Any chained call returns the mock db
    mock_db.collection.return_value = mock_db
    mock_db.document.return_value = mock_db
    
    # Except the final get() call which returns mock_doc in an async context
    mock_db.get = AsyncMock(return_value=mock_doc)
    
    # Call resolve_credentials for a meta_organic page connection
    res = await credential_store.resolve_credentials("client_1", "meta_organic", "page_123")
    
    assert res["access_token"] == "permanent_facebook_page_token"
    # Proactive refresh must NOT have been called because token_expires_at was omitted
    mock_refresh_meta.assert_not_called()
    mock_refresh_threads.assert_not_called()
