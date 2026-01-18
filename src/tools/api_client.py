"""
Ralph Deep Research - API Client

HTTP client for external API calls with retry logic and error handling.
Based on specs/ARCHITECTURE.md and IMPLEMENTATION_PLAN.md Phase 4.3.

Why this module:
- Data agent needs to fetch structured data from external APIs
- Provides consistent interface for different data sources
- Integrates with retry and circuit breaker infrastructure
- Handles common API patterns (auth, rate limiting, pagination)

Usage:
    from src.tools.api_client import APIClient, FinancialAPIClient

    # Generic API client
    client = APIClient(base_url="https://api.example.com", api_key="...")
    data = await client.get("/endpoint", params={"key": "value"})

    # Financial API client
    financial = FinancialAPIClient(api_key="...")
    metrics = await financial.get_company_metrics("AAPL")
"""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import httpx

from src.config.settings import get_settings
from src.tools.errors import (
    APITimeoutError,
    AuthenticationError,
    DataNotFoundError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)
from src.tools.logging import get_logger
from src.tools.retry import RETRY_CONFIGS, CircuitBreaker, RetryHandler

logger = get_logger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class APIResponse:
    """
    Standardized API response wrapper.

    Attributes:
        data: Response data (parsed JSON)
        status_code: HTTP status code
        headers: Response headers
        request_time: Time taken for request in seconds
    """
    data: Any
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    request_time: float = 0.0

    @property
    def is_success(self) -> bool:
        """Check if response indicates success."""
        return 200 <= self.status_code < 300


# =============================================================================
# BASE API CLIENT
# =============================================================================


class APIClient:
    """
    Base HTTP client for external API calls.

    Features:
    - Automatic retry with exponential backoff
    - Circuit breaker for cascading failure protection
    - Consistent error handling
    - Request/response logging
    - Authentication header management

    Example:
        client = APIClient(
            base_url="https://api.example.com/v1",
            api_key="your-api-key"
        )

        # GET request
        response = await client.get("/users", params={"page": 1})

        # POST request
        response = await client.post("/users", data={"name": "John"})
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        timeout: float = 30.0,
        auth_header: str = "Authorization",
        auth_prefix: str = "Bearer",
        retry_config_name: str = "api_call",
    ) -> None:
        """
        Initialize API client.

        Args:
            base_url: Base URL for all requests
            api_key: API key for authentication
            timeout: Request timeout in seconds
            auth_header: Header name for authentication
            auth_prefix: Prefix for auth token (e.g., "Bearer", "Token")
            retry_config_name: Key in RETRY_CONFIGS for retry settings
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.auth_header = auth_header
        self.auth_prefix = auth_prefix

        # Build default headers
        headers = {
            "User-Agent": "RalphResearch/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            headers[auth_header] = f"{auth_prefix} {api_key}".strip()

        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers=headers,
            follow_redirects=True,
        )

        # Initialize retry handler and circuit breaker
        self.retry_handler = RetryHandler(RETRY_CONFIGS.get(retry_config_name, RETRY_CONFIGS["api_call"]))
        self.circuit_breaker = CircuitBreaker(
            name=f"api_{base_url[:30]}",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

        logger.debug("APIClient initialized", base_url=base_url)

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """
        Execute GET request.

        Args:
            endpoint: API endpoint (relative to base_url)
            params: Query parameters
            headers: Additional headers

        Returns:
            APIResponse with parsed data
        """
        return await self._request("GET", endpoint, params=params, headers=headers)

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """
        Execute POST request.

        Args:
            endpoint: API endpoint (relative to base_url)
            data: Request body (will be JSON-encoded)
            params: Query parameters
            headers: Additional headers

        Returns:
            APIResponse with parsed data
        """
        return await self._request("POST", endpoint, data=data, params=params, headers=headers)

    async def put(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Execute PUT request."""
        return await self._request("PUT", endpoint, data=data, params=params, headers=headers)

    async def delete(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Execute DELETE request."""
        return await self._request("DELETE", endpoint, params=params, headers=headers)

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """
        Execute HTTP request with retry and circuit breaker.

        Args:
            method: HTTP method
            endpoint: API endpoint
            data: Request body
            params: Query parameters
            headers: Additional headers

        Returns:
            APIResponse

        Raises:
            AuthenticationError: 401 response
            RateLimitError: 429 response
            DataNotFoundError: 404 response
            ServiceUnavailableError: 5xx response
            APITimeoutError: Request timeout
            NetworkError: Connection failure
        """
        url = self._build_url(endpoint)

        async def _execute() -> APIResponse:
            start_time = datetime.now()

            try:
                response = await self.http_client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=data,
                    headers=headers,
                )

                elapsed = (datetime.now() - start_time).total_seconds()

                # Handle error responses
                self._handle_status_code(response, url)

                # Parse response
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text

                logger.debug(
                    "API request completed",
                    method=method,
                    url=url[:100],
                    status=response.status_code,
                    elapsed=round(elapsed, 3),
                )

                return APIResponse(
                    data=response_data,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    request_time=elapsed,
                )

            except httpx.TimeoutException:
                raise APITimeoutError(
                    message=f"API request timed out: {method} {url}",
                    timeout_seconds=self.timeout,
                    endpoint=endpoint,
                )

            except httpx.ConnectError as e:
                raise NetworkError(
                    message=f"Failed to connect to API: {url}",
                    original_error=str(e),
                )

        # Execute with circuit breaker and retry
        async def _execute_with_circuit_breaker() -> APIResponse:
            return await self.circuit_breaker.execute(_execute)

        return await self.retry_handler.execute(_execute_with_circuit_breaker)

    def _build_url(self, endpoint: str) -> str:
        """Build full URL from base and endpoint."""
        if endpoint.startswith("http"):
            return endpoint
        endpoint = endpoint.lstrip("/")
        return f"{self.base_url}/{endpoint}"

    def _handle_status_code(self, response: httpx.Response, url: str) -> None:
        """Handle HTTP error status codes."""
        status = response.status_code

        if status == 401:
            raise AuthenticationError(
                message="API authentication failed",
                auth_type=self.auth_header,
            )

        if status == 403:
            raise AuthenticationError(
                message="API access forbidden",
                auth_type="permission",
            )

        if status == 404:
            raise DataNotFoundError(
                message=f"API resource not found: {url}",
                resource_type="api_endpoint",
                resource_id=url,
            )

        if status == 429:
            # Try to get retry-after from headers
            retry_after = 60.0
            if "retry-after" in response.headers:
                try:
                    retry_after = float(response.headers["retry-after"])
                except ValueError:
                    pass

            raise RateLimitError(
                message="API rate limit exceeded",
                retry_after=retry_after,
                limit_type="api",
            )

        if status >= 500:
            raise ServiceUnavailableError(
                message=f"API server error: {status}",
                service_name=self.base_url,
                status_code=status,
            )

    def get_circuit_breaker_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return self.circuit_breaker.get_stats()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.aclose()
        logger.debug("APIClient closed")


# =============================================================================
# SPECIALIZED API CLIENTS
# =============================================================================


class FinancialAPIClient(APIClient):
    """
    Client for financial data APIs.

    Provides methods for common financial data queries.
    Currently a placeholder - implement with specific API when needed.

    Example:
        client = FinancialAPIClient(api_key="...")
        metrics = await client.get_company_metrics("AAPL")
        price = await client.get_stock_price("AAPL")
    """

    # Placeholder base URL - would be replaced with actual API
    DEFAULT_BASE_URL = "https://api.example.com/v1/financial"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize financial API client."""
        settings = get_settings()
        super().__init__(
            base_url=base_url or self.DEFAULT_BASE_URL,
            api_key=api_key or settings.financial_api_key,
            **kwargs,
        )

    async def get_company_metrics(
        self,
        ticker: str,
        metrics: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get company financial metrics.

        Args:
            ticker: Stock ticker symbol
            metrics: List of specific metrics to fetch (None = all)

        Returns:
            Dictionary of metric name -> value
        """
        params = {"ticker": ticker}
        if metrics:
            params["metrics"] = ",".join(metrics)

        response = await self.get("/metrics", params=params)
        return response.data

    async def get_stock_price(
        self,
        ticker: str,
        period: str = "1d",
    ) -> dict[str, Any]:
        """
        Get stock price data.

        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 5y)

        Returns:
            Price data with open, high, low, close, volume
        """
        response = await self.get(
            "/prices",
            params={"ticker": ticker, "period": period}
        )
        return response.data

    async def get_dividends(
        self,
        ticker: str,
        years: int = 5,
    ) -> dict[str, Any]:
        """
        Get dividend history.

        Args:
            ticker: Stock ticker symbol
            years: Number of years of history

        Returns:
            Dividend history data
        """
        response = await self.get(
            "/dividends",
            params={"ticker": ticker, "years": years}
        )
        return response.data

    async def get_financial_statements(
        self,
        ticker: str,
        statement_type: str = "income",
        period: str = "annual",
    ) -> dict[str, Any]:
        """
        Get financial statements.

        Args:
            ticker: Stock ticker symbol
            statement_type: income, balance, cashflow
            period: annual or quarterly

        Returns:
            Financial statement data
        """
        response = await self.get(
            f"/statements/{statement_type}",
            params={"ticker": ticker, "period": period}
        )
        return response.data


class CustomAPIClient(APIClient):
    """
    Client for user-configured custom APIs.

    Allows users to add their own data sources with custom authentication.

    Example:
        client = CustomAPIClient(
            base_url="https://my-internal-api.com/v1",
            api_key="my-key",
            auth_header="X-API-Key",
            auth_prefix=""
        )
        data = await client.get("/custom-endpoint")
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        auth_header: str = "X-API-Key",
        auth_prefix: str = "",
        **kwargs: Any,
    ) -> None:
        """
        Initialize custom API client.

        Args:
            base_url: Base URL for the custom API
            api_key: API key (if required)
            auth_header: Header name for API key
            auth_prefix: Prefix for API key value
            **kwargs: Additional arguments for APIClient
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            auth_header=auth_header,
            auth_prefix=auth_prefix,
            **kwargs,
        )


# =============================================================================
# MOCK API CLIENT (Testing)
# =============================================================================


class MockAPIClient(APIClient):
    """
    Mock API client for testing.

    Returns predefined responses without making actual HTTP requests.
    """

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        """
        Initialize mock client.

        Args:
            responses: Dictionary mapping endpoints to mock responses
        """
        # Don't call super().__init__ as we don't need real HTTP client
        self.responses = responses or {}
        self.call_history: list[dict[str, Any]] = []

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """Return mock response."""
        self.call_history.append({
            "method": method,
            "endpoint": endpoint,
            "data": data,
            "params": params,
            "headers": headers,
        })

        # Look for mock response
        if endpoint in self.responses:
            response_data = self.responses[endpoint]
        else:
            response_data = {"mock": True, "endpoint": endpoint}

        return APIResponse(
            data=response_data,
            status_code=200,
            request_time=0.01,
        )

    def set_response(self, endpoint: str, data: Any) -> None:
        """Set mock response for an endpoint."""
        self.responses[endpoint] = data

    def get_calls(self) -> list[dict[str, Any]]:
        """Get history of API calls made."""
        return self.call_history

    def clear_history(self) -> None:
        """Clear call history."""
        self.call_history = []

    async def close(self) -> None:
        """No-op for mock client."""
        pass


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def get_financial_client() -> FinancialAPIClient:
    """
    Get financial API client.

    Returns configured FinancialAPIClient.
    """
    return FinancialAPIClient()


def create_api_client(
    base_url: str,
    api_key: str | None = None,
    **kwargs: Any,
) -> APIClient:
    """
    Create a new API client instance.

    Args:
        base_url: Base URL for the API
        api_key: API key for authentication
        **kwargs: Additional arguments for APIClient

    Returns:
        Configured APIClient instance
    """
    return APIClient(base_url=base_url, api_key=api_key, **kwargs)
