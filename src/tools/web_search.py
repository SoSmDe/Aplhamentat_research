"""
Ralph Deep Research - Web Search Client

Web search functionality for the Research agent using Serper API or mock responses.
Based on specs/ARCHITECTURE.md and IMPLEMENTATION_PLAN.md Phase 4.2.

Why this module:
- Research agent needs web search to find relevant sources
- Abstracts search provider behind common interface
- Provides mock implementation for development/testing
- Integrates with retry logic for reliability

Usage:
    from src.tools.web_search import get_search_client, SearchResult

    client = get_search_client()
    results = await client.search("Apple Q4 2024 earnings", num_results=10)

    for result in results:
        content = await client.fetch_content(result.url)
        # Analyze content...
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus, urlparse

import httpx

from src.config.settings import get_settings
from src.tools.errors import (
    APITimeoutError,
    DataNotFoundError,
    NetworkError,
    RateLimitError,
    ServiceUnavailableError,
)
from src.tools.logging import get_logger
from src.tools.retry import RETRY_CONFIGS, RetryHandler

logger = get_logger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class SearchResult:
    """
    Represents a single search result.

    Attributes:
        title: Page title
        url: Page URL
        snippet: Text snippet/description
        date: Publication date (if available)
        position: Position in search results
    """
    title: str
    url: str
    snippet: str
    date: datetime | None = None
    position: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "date": self.date.isoformat() if self.date else None,
            "position": self.position,
        }


# =============================================================================
# ABSTRACT BASE CLASS
# =============================================================================


class WebSearchClient(ABC):
    """
    Abstract base class for web search clients.

    Why abstract base:
    - Allows swapping search providers (Serper, Google, Bing, etc.)
    - Enables mock implementation for testing
    - Enforces consistent interface

    Implementations must provide:
    - search(): Execute web search
    - fetch_content(): Fetch full page content from URL
    """

    @abstractmethod
    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Execute web search.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of SearchResult objects
        """
        pass

    @abstractmethod
    async def fetch_content(
        self,
        url: str,
        *,
        timeout: float = 30.0,
    ) -> str:
        """
        Fetch full text content from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Extracted text content from the page
        """
        pass


# =============================================================================
# MOCK IMPLEMENTATION (Development/Testing)
# =============================================================================


class MockSearchClient(WebSearchClient):
    """
    Mock search client for development and testing.

    Returns canned responses that simulate real search results.
    Does not make actual API calls.

    Why mock implementation:
    - Enables development without API key
    - Provides deterministic results for testing
    - Avoids API costs during development
    """

    # Sample mock results for different query types
    MOCK_RESULTS = {
        "default": [
            SearchResult(
                title="Sample Search Result 1",
                url="https://example.com/result1",
                snippet="This is a sample search result for testing purposes.",
                date=datetime(2024, 1, 15),
                position=1,
            ),
            SearchResult(
                title="Sample Search Result 2",
                url="https://example.com/result2",
                snippet="Another sample result with relevant information.",
                date=datetime(2024, 1, 14),
                position=2,
            ),
            SearchResult(
                title="Sample Search Result 3",
                url="https://example.com/result3",
                snippet="More sample content for comprehensive testing.",
                date=datetime(2024, 1, 13),
                position=3,
            ),
        ],
        "financial": [
            SearchResult(
                title="Company Q4 2024 Earnings Report",
                url="https://example.com/earnings",
                snippet="The company reported Q4 2024 earnings of $2.5B, "
                       "exceeding analyst expectations by 15%.",
                date=datetime(2024, 1, 25),
                position=1,
            ),
            SearchResult(
                title="Stock Analysis and Market Trends",
                url="https://example.com/analysis",
                snippet="Market analysts predict continued growth in 2025 "
                       "based on strong fundamentals.",
                date=datetime(2024, 1, 24),
                position=2,
            ),
        ],
        "news": [
            SearchResult(
                title="Breaking News: Industry Update",
                url="https://example.com/news",
                snippet="Latest developments in the industry show positive trends "
                       "for market participants.",
                date=datetime(2024, 1, 26),
                position=1,
            ),
        ],
    }

    MOCK_CONTENT = {
        "default": """
        This is sample content from a web page.

        Key Points:
        - Point 1: Important information about the topic
        - Point 2: Additional context and details
        - Point 3: Supporting data and evidence

        The content demonstrates the typical structure of a web article
        that would be returned by the fetch_content method.
        """,
        "financial": """
        Financial Report Summary

        Quarterly Results:
        - Revenue: $2.5 billion (up 15% YoY)
        - Net Income: $500 million
        - EPS: $1.25 (beat estimates by $0.10)

        Key Metrics:
        - Gross Margin: 42%
        - Operating Margin: 25%
        - Cash Flow: $750 million

        Management Commentary:
        "We are pleased with our Q4 performance and remain optimistic
        about growth opportunities in 2025."
        """,
    }

    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[SearchResult]:
        """Return mock search results."""
        logger.debug("Mock search executed", query=query, num_results=num_results)

        # Simulate some latency
        await asyncio.sleep(0.1)

        # Determine which mock results to use based on query
        query_lower = query.lower()
        if any(term in query_lower for term in ["earnings", "revenue", "stock", "financial"]):
            results = self.MOCK_RESULTS["financial"]
        elif any(term in query_lower for term in ["news", "breaking", "latest"]):
            results = self.MOCK_RESULTS["news"]
        else:
            results = self.MOCK_RESULTS["default"]

        # Return up to num_results
        return results[:num_results]

    async def fetch_content(
        self,
        url: str,
        *,
        timeout: float = 30.0,
    ) -> str:
        """Return mock page content."""
        logger.debug("Mock fetch executed", url=url)

        # Simulate some latency
        await asyncio.sleep(0.1)

        # Return appropriate mock content
        if "financial" in url or "earnings" in url:
            return self.MOCK_CONTENT["financial"]
        return self.MOCK_CONTENT["default"]


# =============================================================================
# SERPER IMPLEMENTATION (Production)
# =============================================================================


class SerperClient(WebSearchClient):
    """
    Web search client using Serper API (serper.dev).

    Serper provides Google Search API access with:
    - 2,500 free searches/month
    - Fast response times
    - Rich result metadata

    Why Serper:
    - Cost-effective for MVP
    - Simple API
    - Good result quality
    """

    BASE_URL = "https://google.serper.dev/search"

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 20.0,
    ) -> None:
        """
        Initialize Serper client.

        Args:
            api_key: Serper API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.retry_handler = RetryHandler(RETRY_CONFIGS["web_search"])

        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "X-API-KEY": api_key,
                "Content-Type": "application/json",
            },
        )

        logger.debug("SerperClient initialized")

    async def search(
        self,
        query: str,
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Execute web search via Serper API.

        Args:
            query: Search query string
            num_results: Maximum results (Serper returns up to 100)

        Returns:
            List of SearchResult objects

        Raises:
            RateLimitError: If rate limit exceeded
            APITimeoutError: If request times out
            NetworkError: If connection fails
            ServiceUnavailableError: If Serper is down
        """
        async def _search() -> list[SearchResult]:
            try:
                response = await self.http_client.post(
                    self.BASE_URL,
                    json={
                        "q": query,
                        "num": min(num_results, 100),  # Serper max is 100
                    },
                )

                if response.status_code == 429:
                    raise RateLimitError(
                        message="Serper rate limit exceeded",
                        retry_after=60.0,
                        limit_type="search_api",
                    )

                if response.status_code >= 500:
                    raise ServiceUnavailableError(
                        message="Serper API unavailable",
                        service_name="serper",
                        status_code=response.status_code,
                    )

                response.raise_for_status()
                data = response.json()

                results = []
                organic = data.get("organic", [])

                for i, item in enumerate(organic[:num_results]):
                    # Parse date if available
                    date = None
                    if "date" in item:
                        try:
                            date = datetime.fromisoformat(
                                item["date"].replace("Z", "+00:00")
                            )
                        except (ValueError, TypeError):
                            pass

                    results.append(SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        date=date,
                        position=i + 1,
                    ))

                logger.info(
                    "Search completed",
                    query=query[:50],
                    num_results=len(results),
                )

                return results

            except httpx.TimeoutException:
                raise APITimeoutError(
                    message="Serper search request timed out",
                    timeout_seconds=self.timeout,
                    endpoint="search",
                )

            except httpx.ConnectError as e:
                raise NetworkError(
                    message="Failed to connect to Serper API",
                    original_error=str(e),
                )

        return await self.retry_handler.execute(_search)

    async def fetch_content(
        self,
        url: str,
        *,
        timeout: float = 30.0,
    ) -> str:
        """
        Fetch and extract text content from a URL.

        Args:
            url: URL to fetch
            timeout: Request timeout

        Returns:
            Extracted text content

        Note:
            This is a basic implementation. In production, consider:
            - Using a proper HTML-to-text library (trafilatura, newspaper3k)
            - Handling JavaScript-rendered content
            - Respecting robots.txt
        """
        async def _fetch() -> str:
            try:
                # Create a new client with custom timeout for this request
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(timeout),
                    follow_redirects=True,
                    headers={
                        "User-Agent": "Mozilla/5.0 (compatible; RalphResearch/1.0)",
                    },
                ) as client:
                    response = await client.get(url)

                    if response.status_code == 404:
                        raise DataNotFoundError(
                            message=f"Page not found: {url}",
                            resource_type="webpage",
                            resource_id=url,
                        )

                    if response.status_code >= 500:
                        raise ServiceUnavailableError(
                            message=f"Website unavailable: {url}",
                            service_name=urlparse(url).netloc,
                            status_code=response.status_code,
                        )

                    response.raise_for_status()

                    # Basic text extraction (strip HTML tags)
                    # In production, use trafilatura or similar
                    content = response.text
                    content = self._extract_text(content)

                    logger.debug(
                        "Content fetched",
                        url=url[:100],
                        content_length=len(content),
                    )

                    return content

            except httpx.TimeoutException:
                raise APITimeoutError(
                    message=f"Timeout fetching URL: {url}",
                    timeout_seconds=timeout,
                    endpoint=url,
                )

            except httpx.ConnectError as e:
                raise NetworkError(
                    message=f"Failed to connect to {url}",
                    original_error=str(e),
                )

        return await self.retry_handler.execute(_fetch)

    def _extract_text(self, html: str) -> str:
        """
        Basic text extraction from HTML.

        This is a simple implementation. For production, consider
        using trafilatura, newspaper3k, or BeautifulSoup.
        """
        import re

        # Remove script and style elements
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Decode HTML entities
        text = text.replace("&nbsp;", " ")
        text = text.replace("&amp;", "&")
        text = text.replace("&lt;", "<")
        text = text.replace("&gt;", ">")
        text = text.replace("&quot;", '"')

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.http_client.aclose()
        logger.debug("SerperClient closed")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def get_search_client() -> WebSearchClient:
    """
    Get appropriate search client based on configuration.

    Returns SerperClient if SERPER_API_KEY is set, otherwise MockSearchClient.

    Returns:
        WebSearchClient: Configured search client
    """
    settings = get_settings()

    if settings.serper_api_key:
        logger.info("Using SerperClient for web search")
        return SerperClient(api_key=settings.serper_api_key)
    else:
        logger.info("Using MockSearchClient (SERPER_API_KEY not set)")
        return MockSearchClient()


def create_search_client(
    api_key: str | None = None,
    use_mock: bool = False,
) -> WebSearchClient:
    """
    Create a new search client instance.

    Args:
        api_key: Serper API key (None = use settings or mock)
        use_mock: Force mock client even if API key available

    Returns:
        WebSearchClient: New search client instance
    """
    if use_mock:
        return MockSearchClient()

    if api_key is None:
        settings = get_settings()
        api_key = settings.serper_api_key

    if api_key:
        return SerperClient(api_key=api_key)
    else:
        return MockSearchClient()
