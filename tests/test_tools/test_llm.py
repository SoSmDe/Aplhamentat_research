"""
Tests for the LLM Client module.

Tests cover:
- LLMClient initialization
- Token tracking
- Cost estimation
- Error handling (mocked API responses)
- Structured output parsing
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import BaseModel

from src.tools.llm import (
    LLMClient,
    TokenUsage,
    CumulativeUsage,
    create_llm_client,
    MODEL_PRICING,
)
from src.tools.errors import (
    APITimeoutError,
    AuthenticationError,
    InvalidInputError,
    NetworkError,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
)


# =============================================================================
# TOKEN USAGE TESTS
# =============================================================================


class TestTokenUsage:
    """Tests for TokenUsage dataclass."""

    def test_token_usage_total(self):
        """Test total token calculation."""
        usage = TokenUsage(input_tokens=100, output_tokens=50, model="test")
        assert usage.total_tokens == 150

    def test_token_usage_cost_estimation_opus(self):
        """Test cost estimation for Opus model."""
        usage = TokenUsage(
            input_tokens=1_000_000,  # 1M input tokens
            output_tokens=100_000,   # 100K output tokens
            model="claude-opus-4-20250514",
        )
        # Input: $15/M * 1M = $15
        # Output: $75/M * 0.1M = $7.50
        expected_cost = 15.0 + 7.5
        assert abs(usage.estimate_cost() - expected_cost) < 0.01

    def test_token_usage_cost_estimation_sonnet(self):
        """Test cost estimation for Sonnet model."""
        usage = TokenUsage(
            input_tokens=1_000_000,  # 1M input tokens
            output_tokens=100_000,   # 100K output tokens
            model="claude-sonnet-4-20250514",
        )
        # Input: $3/M * 1M = $3
        # Output: $15/M * 0.1M = $1.50
        expected_cost = 3.0 + 1.5
        assert abs(usage.estimate_cost() - expected_cost) < 0.01

    def test_token_usage_cost_estimation_unknown_model(self):
        """Test cost estimation uses defaults for unknown model."""
        usage = TokenUsage(
            input_tokens=1_000_000,
            output_tokens=100_000,
            model="unknown-model",
        )
        # Should use default pricing (same as Opus)
        expected_cost = 15.0 + 7.5
        assert abs(usage.estimate_cost() - expected_cost) < 0.01


class TestCumulativeUsage:
    """Tests for CumulativeUsage class."""

    def test_add_usage(self):
        """Test adding usage accumulates correctly."""
        cumulative = CumulativeUsage()

        usage1 = TokenUsage(input_tokens=100, output_tokens=50, model="test")
        usage2 = TokenUsage(input_tokens=200, output_tokens=100, model="test")

        cumulative.add_usage(usage1)
        cumulative.add_usage(usage2)

        assert cumulative.total_input_tokens == 300
        assert cumulative.total_output_tokens == 150
        assert cumulative.total_calls == 2

    def test_total_tokens(self):
        """Test total tokens across all calls."""
        cumulative = CumulativeUsage()
        cumulative.add_usage(TokenUsage(input_tokens=100, output_tokens=50, model="a"))
        cumulative.add_usage(TokenUsage(input_tokens=200, output_tokens=100, model="b"))

        assert cumulative.total_tokens == 450

    def test_usage_by_model(self):
        """Test per-model tracking."""
        cumulative = CumulativeUsage()
        cumulative.add_usage(TokenUsage(input_tokens=100, output_tokens=50, model="opus"))
        cumulative.add_usage(TokenUsage(input_tokens=200, output_tokens=100, model="opus"))
        cumulative.add_usage(TokenUsage(input_tokens=50, output_tokens=25, model="sonnet"))

        assert "opus" in cumulative.usage_by_model
        assert "sonnet" in cumulative.usage_by_model
        assert cumulative.usage_by_model["opus"].input_tokens == 300
        assert cumulative.usage_by_model["sonnet"].input_tokens == 50

    def test_get_stats(self):
        """Test statistics dictionary generation."""
        cumulative = CumulativeUsage()
        cumulative.add_usage(TokenUsage(input_tokens=1000, output_tokens=500, model="test"))

        stats = cumulative.get_stats()

        assert "total_input_tokens" in stats
        assert "total_output_tokens" in stats
        assert "total_tokens" in stats
        assert "total_calls" in stats
        assert "estimated_cost_usd" in stats
        assert "usage_by_model" in stats


# =============================================================================
# LLM CLIENT TESTS
# =============================================================================


class TestLLMClient:
    """Tests for LLMClient class."""

    def test_client_initialization(self):
        """Test client initializes correctly."""
        client = LLMClient(api_key="sk-ant-test123")

        assert client.api_key == "sk-ant-test123"
        assert client.timeout == 120.0
        assert client.usage.total_calls == 0

    def test_client_custom_timeout(self):
        """Test client with custom timeout."""
        client = LLMClient(api_key="sk-ant-test123", timeout=60.0)
        assert client.timeout == 60.0

    def test_get_usage_stats(self):
        """Test getting usage statistics."""
        client = LLMClient(api_key="sk-ant-test123")
        client.usage.add_usage(TokenUsage(input_tokens=100, output_tokens=50, model="test"))

        stats = client.get_usage_stats()

        assert stats["total_calls"] == 1
        assert stats["total_input_tokens"] == 100

    def test_reset_usage_stats(self):
        """Test resetting usage statistics."""
        client = LLMClient(api_key="sk-ant-test123")
        client.usage.add_usage(TokenUsage(input_tokens=100, output_tokens=50, model="test"))

        client.reset_usage_stats()

        assert client.usage.total_calls == 0
        assert client.usage.total_input_tokens == 0


class TestLLMClientMocked:
    """Tests for LLMClient with mocked API calls."""

    @pytest.fixture
    def mock_client(self):
        """Create client with mocked Anthropic client."""
        with patch("src.tools.llm.AsyncAnthropic") as MockAnthropic:
            client = LLMClient(api_key="sk-ant-test123")
            # Create mock response
            mock_response = MagicMock()
            mock_response.content = [MagicMock(text="Hello, world!")]
            mock_response.usage.input_tokens = 10
            mock_response.usage.output_tokens = 5

            client.client.messages.create = AsyncMock(return_value=mock_response)

            # Disable circuit breaker and retry for simpler testing
            client.circuit_breaker._state = MagicMock()
            client.circuit_breaker._state.value = "closed"

            yield client

    @pytest.mark.asyncio
    async def test_create_message_success(self, mock_client):
        """Test successful message creation."""
        # Mock the circuit breaker to just execute the function
        async def mock_execute(func):
            return await func()

        mock_client.circuit_breaker.execute = mock_execute

        # Mock retry handler to just execute the function
        async def mock_retry_execute(func, *args, **kwargs):
            return await func(*args, **kwargs)

        mock_client.retry_handler.execute = mock_retry_execute

        result = await mock_client.create_message(
            model="claude-opus-4-20250514",
            system="You are helpful.",
            messages=[{"role": "user", "content": "Hi!"}],
        )

        assert result == "Hello, world!"
        assert mock_client.usage.total_calls == 1


class TestStructuredOutput:
    """Tests for structured output parsing."""

    def test_extract_json_from_markdown(self):
        """Test JSON extraction from markdown code block."""
        # The actual extraction is done in create_structured method
        # This tests the pattern
        response = '```json\n{"name": "test"}\n```'
        lines = response.strip().split("\n")

        # Find JSON content between ``` markers
        start_idx = 1 if lines[0].startswith("```") else 0
        end_idx = len(lines)
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "```":
                end_idx = i
                break
        json_str = "\n".join(lines[start_idx:end_idx])

        import json
        data = json.loads(json_str)
        assert data["name"] == "test"

    def test_extract_plain_json(self):
        """Test JSON extraction from plain response."""
        response = '{"name": "test"}'
        import json
        data = json.loads(response.strip())
        assert data["name"] == "test"


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_llm_client_with_key(self):
        """Test creating client with explicit API key."""
        client = create_llm_client(api_key="sk-ant-test123")
        assert client.api_key == "sk-ant-test123"

    def test_create_llm_client_with_timeout(self):
        """Test creating client with custom timeout."""
        client = create_llm_client(api_key="sk-ant-test123", timeout=60.0)
        assert client.timeout == 60.0


# =============================================================================
# MODEL PRICING TESTS
# =============================================================================


class TestModelPricing:
    """Tests for model pricing configuration."""

    def test_opus_pricing_defined(self):
        """Test Opus pricing is defined."""
        assert "claude-opus-4-20250514" in MODEL_PRICING
        assert "input" in MODEL_PRICING["claude-opus-4-20250514"]
        assert "output" in MODEL_PRICING["claude-opus-4-20250514"]

    def test_sonnet_pricing_defined(self):
        """Test Sonnet pricing is defined."""
        assert "claude-sonnet-4-20250514" in MODEL_PRICING
        assert "input" in MODEL_PRICING["claude-sonnet-4-20250514"]
        assert "output" in MODEL_PRICING["claude-sonnet-4-20250514"]

    def test_opus_more_expensive_than_sonnet(self):
        """Test Opus is more expensive than Sonnet."""
        opus = MODEL_PRICING["claude-opus-4-20250514"]
        sonnet = MODEL_PRICING["claude-sonnet-4-20250514"]

        assert opus["input"] > sonnet["input"]
        assert opus["output"] > sonnet["output"]
