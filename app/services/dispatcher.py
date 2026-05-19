"""
Dispatcher service to route requests to the correct platform connector.
"""

from typing import Dict, Type
from app.models.requests import Platform
from app.connectors.base import BaseConnector

class Dispatcher:
    """Registry-based dispatch for platform connectors."""

    def __init__(self):
        self._connectors: Dict[Platform, BaseConnector] = {}

    def register(self, platform: Platform, connector: BaseConnector):
        """Register a connector instance for a platform."""
        self._connectors[platform] = connector

    def get_connector(self, platform: Platform) -> BaseConnector:
        """Get the registered connector for a platform."""
        connector = self._connectors.get(platform)
        if not connector:
            raise ValueError(f"Connector not registered for platform: {platform.value}")
        return connector

dispatcher = Dispatcher()
