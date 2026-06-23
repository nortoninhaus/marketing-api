from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import logging
import contextvars

from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

from app.models.requests import DataRequest
from app.models.responses import CampaignData, ErrorDetail

logger = logging.getLogger(__name__)

# Thread-safe context variable to track rate limits for successful requests
import threading

# Thread-safe ContextVar for local thread tracking
rate_limit_ctx = contextvars.ContextVar("rate_limit_remaining", default=None)

# Thread-local storage to track the active request object in worker threads
thread_local_storage = threading.local()

# Global registry to pass rate limits back from worker threads to main threads
request_rate_limits = {}
request_rate_limits_lock = threading.Lock()

class BaseConnector(ABC):
    """Abstract base class for all marketing platforms."""

    platform_name: str = "base"

    def _record_rate_limit(self, response_headers: Dict[str, str]):
        """Helper to parse and record rate limit remaining from headers."""
        headers = response_headers or {}
        # Lowercase headers to ensure case-insensitive matching
        headers_lower = {k.lower(): v for k, v in headers.items()}
        for k in ("x-rate-limit-remaining", "rate-limit-remaining", "x-ratelimit-remaining"):
            if k in headers_lower:
                try:
                    val = int(headers_lower[k])
                    rate_limit_ctx.set(val)
                    # Also register in global map if current_request is tracked
                    req = getattr(thread_local_storage, "current_request", None)
                    if req is not None:
                        with request_rate_limits_lock:
                            request_rate_limits[id(req)] = val
                    logger.info(f"Recorded rate limit remaining for {self.platform_name}: {val}")
                    break
                except (ValueError, TypeError):
                    pass


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
        thread_local_storage.current_request = request
        try:
            return self.fetch_data(request)
        except Exception as e:
            logger.error(f"Error fetching data for {self.platform_name}: {e}")
            raise
        finally:
            if hasattr(thread_local_storage, "current_request"):
                del thread_local_storage.current_request

    def handle_error(self, e: Exception) -> ErrorDetail:
        """Map raw exceptions to structured ErrorDetail for agents."""
        import requests as _requests

        # Unwrap tenacity.RetryError if it wraps the exception
        if isinstance(e, RetryError):
            e = e.last_attempt.exception() or e

        code = "API_ERROR"
        retryable = True
        message = str(e)
        rate_limit_remaining = None

        # Try to handle FacebookRequestError specifically
        try:
            from facebook_business.exceptions import FacebookRequestError
            if isinstance(e, FacebookRequestError):
                status = e.http_status()
                api_code = e.api_error_code()
                api_subcode = e.api_error_subcode()
                api_msg = e.api_error_message() or str(e)

                # Check for token issues or administrative permission errors
                if status in (401, 403) or api_code in (102, 190) or (200 <= (api_code or 0) <= 299) or api_code == 10:
                    code = "AUTH_ERROR"
                    retryable = False
                elif status == 429 or api_code in (4, 17, 32, 613):
                    code = "RATE_LIMIT"
                    retryable = True
                elif status >= 500:
                    code = "API_ERROR"
                    retryable = True
                else:
                    code = "INVALID_REQUEST"
                    retryable = False

                message = f"Meta API Error ({api_code}:{api_subcode}) [HTTP {status}]: {api_msg}"
                
                # Get rate limit from headers if available
                headers = e.http_headers() or {}
                headers_lower = {k.lower(): v for k, v in headers.items()}
                for k in ("x-rate-limit-remaining", "rate-limit-remaining", "x-ratelimit-remaining"):
                    if k in headers_lower:
                        try:
                            rate_limit_remaining = int(headers_lower[k])
                            break
                        except (ValueError, TypeError):
                            pass
                
                return ErrorDetail(
                    code=code,
                    message=message,
                    platform=self.platform_name,
                    retryable=retryable,
                    rate_limit_remaining=rate_limit_remaining
                )
        except ImportError:
            pass

        # Classify by HTTP status code
        if isinstance(e, _requests.exceptions.HTTPError) and e.response is not None:
            status = e.response.status_code
            
            # Inspect headers for rate limits
            headers = e.response.headers or {}
            for k in ("x-rate-limit-remaining", "rate-limit-remaining", "x-ratelimit-remaining"):
                if k in headers:
                    try:
                        rate_limit_remaining = int(headers[k])
                        break
                    except (ValueError, TypeError):
                        pass

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
            retryable=retryable,
            rate_limit_remaining=rate_limit_remaining
        )
