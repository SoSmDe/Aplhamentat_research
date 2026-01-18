"""
Tests for the Web Search Client module.

Tests cover:
- SearchResult data model
- MockSearchClient functionality
- SerperClient (with mocked HTTP)
- Factory functions
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.tools.web_search import (
    SearchResult,
    WebSearchClient,
    MockSearchClient,
    SerperClient,
    get_search_client,
    create_search_client,
)
from src.tools.errors import (
    APITimeoutError,
    DataNotFoundError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)


# =============================================================================
# SEARCH RESULT TESTS
# =============================================================================


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        result = SearchResult(
            title="Test Title",
            url="https://example.com",
            snippet="Test snippet",
            date=datetime(2024, 1, 15),
            position=1,
        )

        assert result.title == "Test Title"
        assert result.url == "https://example.com"
        assert result.snippet == "Test snippet"
        assert result.date == datetime(2024, 1, 15)
        assert result.position == 1

    def test_search_result_without_date(self):
        """Test search result without date."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
        )

        assert result.date is None
        assert result.position == 0

    def test_search_result_to_dict(self):
        """Test converting to dictionary."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            date=datetime(2024, 1, 15),
            position=1,
        )

        data = result.to_dict()

        assert data["title"] == "Test"
        assert data["url"] == "https://example.com"
        assert data["snippet"] == "Snippet"
        assert data["date"] == "2024-01-15T00:00:00"
        assert data["position"] == 1

    def test_search_result_to_dict_no_date(self):
        """Test converting to dictionary without date."""
        result = SearchResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
        )

        data = result.to_dict()

        assert data["date"] is None


# =============================================================================
# MOCK SEARCH CLIENT TESTS
# =============================================================================


class TestMockSearchClient:
    """Tests for MockSearchClient."""

    @pytest.fixture
    def client(self):
        """Create mock search client."""
        return MockSearchClient()

    @pytest.mark.asyncio
    async def test_search_returns_results(self, client):
        """Test search returns mock results."""
        results = await client.search("test query")

        assert len(results) > 0
        assert isinstance(results[0], SearchResult)

    @pytest.mark.asyncio
    async def test_search_respects_num_results(self, client):
        """Test search respects num_results parameter."""
        results = await client.search("test query", num_results=2)

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_search_financial_query(self, client):
        """Test search with financial keywords."""
        results = await client.search("Apple earnings report")

        assert len(results) > 0
        # Should return financial mock results
        assert any("earnings" in r.title.lower() or "earnings" in r.snippet.lower()
                   for r in results)

    @pytest.mark.asyncio
    async def test_search_news_query(self, client):
        """Test search with news keywords."""
        results = await client.search("breaking news update")

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_fetch_content(self, client):
        """Test fetching page content."""
        content = await client.fetch_content("https://example.com")

        assert len(content) > 0
        assert isinstance(content, str)

    @pytest.mark.asyncio
    async def test_fetch_content_financial_url(self, client):
        """Test fetching content from financial URL."""
        content = await client.fetch_content("https://example.com/financial")

        assert len(content) > 0
        # Should return financial mock content
        assert "Revenue" in content or "Financial" in content


# =============================================================================
# SERPER CLIENT TESTS
# =============================================================================


class TestSerperClient:
    """Tests for SerperClient with mocked HTTP."""

    @pytest.fixture
    def mock_http_client(self):
        """Create mocked HTTP client."""
        mock = MagicMock()
        return mock

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful search."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "organic": [
                    {
                        "title": "Test Result",
                        "link": "https://example.com",
                        "snippet": "Test snippet",
                    }
                ]
            }
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=None)

            # Create SerperClient with mocked HTTP
            client = SerperClient(api_key="test-key")
            client.http_client = mock_client_instance

            # Mock retry handler to just execute
            async def mock_execute(func, *args, **kwargs):
                return await func(*args, **kwargs)
            client.retry_handler.execute = mock_execute

            results = await client.search("test query")

            assert len(results) == 1
            assert results[0].title == "Test Result"
            assert results[0].url == "https://example.com"

    @pytest.mark.asyncio
    async def test_search_rate_limit(self):
        """Test rate limit handling."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 429

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)

            client = SerperClient(api_key="test-key")
            client.http_client = mock_client_instance

            # Mock retry to propagate error
            async def mock_execute(func, *args, **kwargs):
                return await func(*args, **kwargs)
            client.retry_handler.execute = mock_execute

            with pytest.raises(RateLimitError):
                await client.search("test query")

    @pytest.mark.asyncio
    async def test_search_server_error(self):
        """Test server error handling."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 500

            mock_client_instance = MagicMock()
            mock_client_instance.post = AsyncMock(return_value=mock_response)

            client = SerperClient(api_key="test-key")
            client.http_client = mock_client_instance

            async def mock_execute(func, *args, **kwargs):
                return await func(*args, **kwargs)
            client.retry_handler.execute = mock_execute

            with pytest.raises(ServiceUnavailableError):
                await client.search("test query")

    def test_extract_text_removes_scripts(self):
        """Test HTML text extraction removes scripts."""
        client = SerperClient(api_key="test-key")

        html = "<html><script>alert('bad');</script><p>Good content</p></html>"
        text = client._extract_text(html)

        assert "alert" not in text
        assert "Good content" in text

    def test_extract_text_removes_styles(self):
        """Test HTML text extraction removes styles."""
        client = SerperClient(api_key="test-key")

        html = "<html><style>body { color: red; }</style><p>Content</p></html>"
        text = client._extract_text(html)

        assert "color" not in text
        assert "Content" in text

    def test_extract_text_decodes_entities(self):
        """Test HTML entity decoding."""
        client = SerperClient(api_key="test-key")

        html = "<p>AT&amp;T is &gt; than &lt;other&gt;</p>"
        text = client._extract_text(html)

        assert "AT&T" in text
        assert ">" in text
        assert "<" in text


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_search_client_mock(self):
        """Test creating mock client explicitly."""
        client = create_search_client(use_mock=True)
        assert isinstance(client, MockSearchClient)

    def test_create_search_client_with_key(self):
        """Test creating Serper client with API key."""
        client = create_search_client(api_key="test-key")
        assert isinstance(client, SerperClient)

    def test_create_search_client_no_key(self):
        """Test creating client without key returns mock."""
        with patch("src.tools.web_search.get_settings") as mock_settings:
            mock_settings.return_value.serper_api_key = None
            client = create_search_client()
            assert isinstance(client, MockSearchClient)

    def test_get_search_client_with_key(self):
        """Test factory function with key configured."""
        with patch("src.tools.web_search.get_settings") as mock_settings:
            mock_settings.return_value.serper_api_key = "test-key"
            client = get_search_client()
            assert isinstance(client, SerperClient)

    def test_get_search_client_without_key(self):
        """Test factory function without key returns mock."""
        with patch("src.tools.web_search.get_settings") as mock_settings:
            mock_settings.return_value.serper_api_key = None
            client = get_search_client()
            assert isinstance(client, MockSearchClient)


# =============================================================================
# INTERFACE TESTS
# =============================================================================


class TestWebSearchClientInterface:
    """Tests for WebSearchClient interface compliance."""

    def test_mock_client_is_web_search_client(self):
        """Test MockSearchClient is a WebSearchClient."""
        client = MockSearchClient()
        assert isinstance(client, WebSearchClient)

    def test_serper_client_is_web_search_client(self):
        """Test SerperClient is a WebSearchClient."""
        client = SerperClient(api_key="test")
        assert isinstance(client, WebSearchClient)

    def test_abstract_methods_exist(self):
        """Test abstract methods are defined."""
        # Check that abstract methods are defined in base class
        assert hasattr(WebSearchClient, "search")
        assert hasattr(WebSearchClient, "fetch_content")
