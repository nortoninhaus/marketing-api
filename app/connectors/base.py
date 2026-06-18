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
        import requests as _requests

        code = "API_ERROR"
        retryable = True
        message = str(e)

        # Classify by HTTP status code
        if isinstance(e, _requests.exceptions.HTTPError) and e.response is not None:
            status = e.response.status_code
            if status in (401, 403):
                code = "AUTH_ERROR"
                retryable = False
                message = f"Authentication/authorization failed (HTTP {status}): {e}"
            elif status == 429:
                code = "RATE_LIMIT"
                retryable = True
                message = f"Rate limit exceeded (HTTP 429). Please wait before retrying."
            elif 400 <= status < 500:
                code = "INVALID_REQUEST"
                retryable = False
                message = f"Client error (HTTP {status}): {e}"
            else:
                code = "API_ERROR"
                retryable = True

        # Classify by exception type
        elif isinstance(e, _requests.exceptions.ConnectionError):
            code = "CONNECTIVITY"
            retryable = True
            message = f"Connection failed to {self.platform_name} API: {e}"
        elif isinstance(e, _requests.exceptions.Timeout):
            code = "TIMEOUT"
            retryable = True
            message = f"Request to {self.platform_name} API timed out: {e}"
        elif isinstance(e, ValueError):
            code = "INVALID_METRIC"
            retryable = False
            message = f"Invalid parameter or metric: {e}"

        return ErrorDetail(
            code=code,
            message=message,
            platform=self.platform_name,
            retryable=retryable
        )
