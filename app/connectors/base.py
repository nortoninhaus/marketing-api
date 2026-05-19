"""
Base Connector with unified error handling and retry logic.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging

from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.requests import DataRequest
from app.models.responses import CampaignData, ErrorDetail

logger = logging.getLogger(__name__)

class BaseConnector(ABC):
    """Abstract base class for all marketing platforms."""

    platform_name: str = "base"

    def get_credentials(self, request: Optional[DataRequest] = None) -> Dict[str, Any]:
        """
        Resolves credentials for the request.
        Priority: 1. Dynamic credentials in request, 2. Environment settings (default).
        """
        if request and request.credentials:
            return request.credentials
        return {}

    @abstractmethod
    def fetch_data(self, request: DataRequest) -> List[CampaignData]:
        """Fetch and normalize data from the platform. Subclasses must implement this."""
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Return the available metrics and dimensions for this platform."""
        pass

    def ping(self) -> bool:
        """Default ping implementation. Should be overridden by subclasses."""
        return True

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_with_retry(self, request: DataRequest) -> List[CampaignData]:
        """Fetch data with exponential backoff for transient errors."""
        try:
            return self.fetch_data(request)
        except Exception as e:
            logger.error(f"Error fetching data for {self.platform_name}: {e}")
            raise

    def handle_error(self, e: Exception) -> ErrorDetail:
        """Map raw exceptions to structured ErrorDetail for agents."""
        return ErrorDetail(
            code="API_ERROR",
            message=str(e),
            platform=self.platform_name,
            retryable=True
        )
