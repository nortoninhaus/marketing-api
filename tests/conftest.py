"""
Pytest configuration and fixtures.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

@pytest.fixture
def client():
    """Sync test client."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def auth_headers():
    """Headers with valid API key."""
    return {"X-API-Key": settings.api_key}
