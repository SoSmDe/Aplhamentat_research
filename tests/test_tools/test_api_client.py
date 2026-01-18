"""
Tests for the API Client module.

Tests cover:
- APIResponse data model
- APIClient base functionality
- FinancialAPIClient
- MockAPIClient
- Error handling
- Factory functions
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.tools.api_client import (
    APIResponse,
    APIClient,
    FinancialAPIClient,
    CustomAPIClient,
    MockAPIClient,
    get_financial_client,
    create_api_client,
)
from src.tools.errors import (
    APITimeoutError,
    AuthenticationError,
    DataNotFoundError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)


# =============================================================================
# API RESPONSE TESTS
# =============================================================================


class TestAPIResponse:
    """Tests for APIResponse dataclass."""

    def test_response_creation(self):
        """Test creating an API response."""
        response = APIResponse(
            data={"key": "value"},
            status_code=200,
            headers={"content-type": "application/json"},
            request_time=0.5,
        )

        assert response.data == {"key": "value"}
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert response.request_time == 0.5

    def test_is_success_true(self):
        """Test is_success for success status codes."""
        for status in [200, 201, 204, 299]:
            response = APIResponse(data={}, status_code=status)
            assert response.is_success is True

    def test_is_success_false(self):
        """Test is_success for error status codes."""
        for status in [400, 401, 404, 500]:
            response = APIResponse(data={}, status_code=status)
            assert response.is_success is False

    def test_default_values(self):
        """Test default values."""
        response = APIResponse(data={}, status_code=200)
        assert response.headers == {}
        assert response.request_time == 0.0


# =============================================================================
# API CLIENT TESTS
# =============================================================================


class TestAPIClient:
    """Tests for APIClient base class."""

    def test_client_initialization(self):
        """Test client initializes correctly."""
        client = APIClient(
            base_url="https://api.example.com",
            api_key="test-key",
        )

        assert client.base_url == "https://api.example.com"
        assert client.api_key == "test-key"
        assert client.timeout == 30.0

    def test_client_custom_timeout(self):
        """Test client with custom timeout."""
        client = APIClient(
            base_url="https://api.example.com",
            timeout=60.0,
        )
        assert client.timeout == 60.0

    def test_client_custom_auth_header(self):
        """Test client with custom auth header."""
        client = APIClient(
            base_url="https://api.example.com",
            api_key="test-key",
            auth_header="X-API-Key",
            auth_prefix="",
        )
        assert client.auth_header == "X-API-Key"
        assert client.auth_prefix == ""

    def test_build_url_relative(self):
        """Test URL building for relative endpoint."""
        client = APIClient(base_url="https://api.example.com")
        url = client._build_url("/users")
        assert url == "https://api.example.com/users"

    def test_build_url_relative_no_slash(self):
        """Test URL building for relative endpoint without leading slash."""
        client = APIClient(base_url="https://api.example.com")
        url = client._build_url("users")
        assert url == "https://api.example.com/users"

    def test_build_url_absolute(self):
        """Test URL building for absolute endpoint."""
        client = APIClient(base_url="https://api.example.com")
        url = client._build_url("https://other.com/endpoint")
        assert url == "https://other.com/endpoint"

    def test_build_url_strips_trailing_slash(self):
        """Test URL building strips trailing slash from base."""
        client = APIClient(base_url="https://api.example.com/")
        url = client._build_url("users")
        assert url == "https://api.example.com/users"


class TestAPIClientErrors:
    """Tests for API client error handling."""

    @pytest.fixture
    def client(self):
        """Create API client for testing."""
        return APIClient(base_url="https://api.example.com", api_key="test")

    def test_handle_401(self, client):
        """Test 401 raises AuthenticationError."""
        response = MagicMock()
        response.status_code = 401
        response.headers = {}

        with pytest.raises(AuthenticationError):
            client._handle_status_code(response, "https://api.example.com/test")

    def test_handle_403(self, client):
        """Test 403 raises AuthenticationError."""
        response = MagicMock()
        response.status_code = 403
        response.headers = {}

        with pytest.raises(AuthenticationError):
            client._handle_status_code(response, "https://api.example.com/test")

    def test_handle_404(self, client):
        """Test 404 raises DataNotFoundError."""
        response = MagicMock()
        response.status_code = 404
        response.headers = {}

        with pytest.raises(DataNotFoundError):
            client._handle_status_code(response, "https://api.example.com/test")

    def test_handle_429(self, client):
        """Test 429 raises RateLimitError."""
        response = MagicMock()
        response.status_code = 429
        response.headers = {}

        with pytest.raises(RateLimitError):
            client._handle_status_code(response, "https://api.example.com/test")

    def test_handle_429_with_retry_after(self, client):
        """Test 429 with retry-after header."""
        response = MagicMock()
        response.status_code = 429
        response.headers = {"retry-after": "120"}

        try:
            client._handle_status_code(response, "https://api.example.com/test")
        except RateLimitError as e:
            assert e.retry_after == 120.0

    def test_handle_500(self, client):
        """Test 500 raises ServiceUnavailableError."""
        response = MagicMock()
        response.status_code = 500
        response.headers = {}

        with pytest.raises(ServiceUnavailableError):
            client._handle_status_code(response, "https://api.example.com/test")

    def test_handle_503(self, client):
        """Test 503 raises ServiceUnavailableError."""
        response = MagicMock()
        response.status_code = 503
        response.headers = {}

        with pytest.raises(ServiceUnavailableError):
            client._handle_status_code(response, "https://api.example.com/test")


# =============================================================================
# MOCK API CLIENT TESTS
# =============================================================================


class TestMockAPIClient:
    """Tests for MockAPIClient."""

    @pytest.fixture
    def client(self):
        """Create mock API client."""
        return MockAPIClient(responses={
            "/users": {"users": [{"id": 1, "name": "Test"}]},
        })

    @pytest.mark.asyncio
    async def test_get_with_mock_response(self, client):
        """Test GET with predefined mock response."""
        response = await client.get("/users")

        assert response.status_code == 200
        assert response.data["users"][0]["name"] == "Test"

    @pytest.mark.asyncio
    async def test_get_without_mock_response(self, client):
        """Test GET without predefined mock returns default."""
        response = await client.get("/other")

        assert response.status_code == 200
        assert response.data["mock"] is True
        assert response.data["endpoint"] == "/other"

    @pytest.mark.asyncio
    async def test_post_records_call(self, client):
        """Test POST records the call."""
        await client.post("/users", data={"name": "New"})

        calls = client.get_calls()
        assert len(calls) == 1
        assert calls[0]["method"] == "POST"
        assert calls[0]["data"]["name"] == "New"

    def test_set_response(self, client):
        """Test setting mock response."""
        client.set_response("/new", {"result": "success"})

        assert "/new" in client.responses
        assert client.responses["/new"]["result"] == "success"

    def test_clear_history(self, client):
        """Test clearing call history."""
        client.call_history = [{"method": "GET"}]
        client.clear_history()

        assert len(client.call_history) == 0

    @pytest.mark.asyncio
    async def test_close_no_error(self, client):
        """Test close doesn't raise error."""
        await client.close()  # Should not raise


# =============================================================================
# FINANCIAL API CLIENT TESTS
# =============================================================================


class TestFinancialAPIClient:
    """Tests for FinancialAPIClient."""

    def test_initialization(self):
        """Test client initializes with default base URL."""
        with patch("src.tools.api_client.get_settings") as mock_settings:
            mock_settings.return_value.financial_api_key = "test-key"
            client = FinancialAPIClient()

            assert client.DEFAULT_BASE_URL in client.base_url or client.base_url == client.DEFAULT_BASE_URL

    def test_initialization_custom_url(self):
        """Test client with custom base URL."""
        with patch("src.tools.api_client.get_settings") as mock_settings:
            mock_settings.return_value.financial_api_key = None
            client = FinancialAPIClient(
                api_key="test-key",
                base_url="https://custom-api.com",
            )
            assert client.base_url == "https://custom-api.com"


# =============================================================================
# CUSTOM API CLIENT TESTS
# =============================================================================


class TestCustomAPIClient:
    """Tests for CustomAPIClient."""

    def test_initialization(self):
        """Test custom client initialization."""
        client = CustomAPIClient(
            base_url="https://internal.api.com",
            api_key="internal-key",
            auth_header="X-Internal-Key",
        )

        assert client.base_url == "https://internal.api.com"
        assert client.api_key == "internal-key"
        assert client.auth_header == "X-Internal-Key"

    def test_no_auth_prefix(self):
        """Test custom client with no auth prefix."""
        client = CustomAPIClient(
            base_url="https://api.com",
            api_key="key",
            auth_prefix="",
        )
        assert client.auth_prefix == ""


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_api_client(self):
        """Test creating basic API client."""
        client = create_api_client(
            base_url="https://api.example.com",
            api_key="test-key",
        )

        assert isinstance(client, APIClient)
        assert client.base_url == "https://api.example.com"

    def test_create_api_client_with_options(self):
        """Test creating API client with options."""
        client = create_api_client(
            base_url="https://api.example.com",
            api_key="test-key",
            timeout=60.0,
        )

        assert client.timeout == 60.0

    def test_get_financial_client(self):
        """Test getting financial API client."""
        with patch("src.tools.api_client.get_settings") as mock_settings:
            mock_settings.return_value.financial_api_key = "fin-key"
            client = get_financial_client()

            assert isinstance(client, FinancialAPIClient)


# =============================================================================
# CIRCUIT BREAKER INTEGRATION TESTS
# =============================================================================


class TestCircuitBreakerIntegration:
    """Tests for circuit breaker integration."""

    def test_circuit_breaker_stats(self):
        """Test getting circuit breaker stats."""
        client = APIClient(base_url="https://api.example.com")
        stats = client.get_circuit_breaker_stats()

        assert "name" in stats
        assert "state" in stats
        assert "failure_count" in stats
