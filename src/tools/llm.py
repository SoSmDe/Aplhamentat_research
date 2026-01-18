"""
Ralph Deep Research - LLM Client

Wrapper around Anthropic Claude API with retry logic, token tracking, and cost estimation.
Based on specs/ARCHITECTURE.md and IMPLEMENTATION_PLAN.md Phase 4.1.

Why this module:
- Centralizes all Claude API interactions
- Provides consistent error handling and retry logic
- Tracks token usage for cost monitoring
- Supports both text and structured (Pydantic) responses

Usage:
    from src.tools.llm import LLMClient, get_llm_client

    # Basic usage
    client = get_llm_client()
    response = await client.create_message(
        model="claude-opus-4-20250514",
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Hello!"}]
    )

    # Structured output
    result = await client.create_structured(
        model="claude-opus-4-20250514",
        system="Extract entities from text.",
        messages=[{"role": "user", "content": "Apple Inc is based in Cupertino."}],
        response_model=EntityExtraction
    )
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, TypeVar

import httpx
from anthropic import APIConnectionError as AnthropicConnectionError
from anthropic import APIStatusError, APITimeoutError as AnthropicTimeoutError
from anthropic import AsyncAnthropic, RateLimitError as AnthropicRateLimitError
from pydantic import BaseModel, ValidationError

from src.config.models import get_model_for_agent
from src.config.settings import get_settings
from src.tools.errors import (
    APITimeoutError,
    AuthenticationError,
    InvalidInputError,
    NetworkError,
    QuotaExceededError,
    RateLimitError,
    ServiceUnavailableError,
)
from src.tools.logging import get_logger
from src.tools.retry import RETRY_CONFIGS, CircuitBreaker, RetryHandler

logger = get_logger(__name__)

# Type variable for generic Pydantic models
T = TypeVar("T", bound=BaseModel)


# =============================================================================
# COST ESTIMATION
# =============================================================================

# Pricing per million tokens (USD) - as of Claude API pricing
# These are approximate and should be updated as pricing changes
MODEL_PRICING = {
    "claude-opus-4-20250514": {
        "input": 15.0,    # $15 per million input tokens
        "output": 75.0,   # $75 per million output tokens
    },
    "claude-sonnet-4-20250514": {
        "input": 3.0,     # $3 per million input tokens
        "output": 15.0,   # $15 per million output tokens
    },
}

# Default pricing for unknown models
DEFAULT_PRICING = {
    "input": 15.0,
    "output": 75.0,
}


@dataclass
class TokenUsage:
    """
    Tracks token usage for a single API call.

    Attributes:
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        model: Model used for the call
        cache_creation_input_tokens: Tokens used to create cache
        cache_read_input_tokens: Tokens read from cache
    """
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)."""
        return self.input_tokens + self.output_tokens

    def estimate_cost(self) -> float:
        """
        Estimate cost in USD for this usage.

        Returns:
            Estimated cost in USD
        """
        pricing = MODEL_PRICING.get(self.model, DEFAULT_PRICING)
        input_cost = (self.input_tokens / 1_000_000) * pricing["input"]
        output_cost = (self.output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost


@dataclass
class CumulativeUsage:
    """
    Tracks cumulative token usage across multiple API calls.

    Why track this:
    - Cost monitoring and budgeting
    - Usage analytics for optimization
    - Alerting on unusual usage patterns
    """
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0
    usage_by_model: dict[str, TokenUsage] = field(default_factory=dict)

    def add_usage(self, usage: TokenUsage) -> None:
        """Add token usage from a single call."""
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_calls += 1

        # Track per-model usage
        if usage.model not in self.usage_by_model:
            self.usage_by_model[usage.model] = TokenUsage(model=usage.model)

        model_usage = self.usage_by_model[usage.model]
        model_usage.input_tokens += usage.input_tokens
        model_usage.output_tokens += usage.output_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens used across all calls."""
        return self.total_input_tokens + self.total_output_tokens

    def estimate_total_cost(self) -> float:
        """Estimate total cost across all calls."""
        return sum(usage.estimate_cost() for usage in self.usage_by_model.values())

    def get_stats(self) -> dict[str, Any]:
        """Get usage statistics as dictionary."""
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_calls": self.total_calls,
            "estimated_cost_usd": round(self.estimate_total_cost(), 4),
            "usage_by_model": {
                model: {
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "estimated_cost_usd": round(usage.estimate_cost(), 4),
                }
                for model, usage in self.usage_by_model.items()
            },
        }


# =============================================================================
# LLM CLIENT
# =============================================================================


class LLMClient:
    """
    Claude API client with retry logic, circuit breaker, and token tracking.

    Why this design:
    - Centralizes API interaction logic
    - Provides robust error handling with proper error types
    - Tracks token usage for cost monitoring
    - Supports both text and structured (JSON/Pydantic) responses
    - Integrates with existing retry and circuit breaker infrastructure

    Example:
        client = LLMClient(api_key="sk-ant-...")

        # Text response
        text = await client.create_message(
            model="claude-opus-4-20250514",
            system="You are helpful.",
            messages=[{"role": "user", "content": "Hi!"}]
        )

        # Structured response
        result = await client.create_structured(
            model="claude-opus-4-20250514",
            system="Extract data.",
            messages=[{"role": "user", "content": "..."}],
            response_model=MyModel
        )
    """

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 120.0,
        max_retries: int = 0,  # We handle retries ourselves
    ) -> None:
        """
        Initialize LLM client.

        Args:
            api_key: Anthropic API key
            timeout: Request timeout in seconds
            max_retries: Anthropic client retries (0 = we handle retries)
        """
        self.api_key = api_key
        self.timeout = timeout

        # Initialize Anthropic client
        self.client = AsyncAnthropic(
            api_key=api_key,
            timeout=httpx.Timeout(timeout),
            max_retries=max_retries,
        )

        # Initialize retry handler and circuit breaker
        self.retry_handler = RetryHandler(RETRY_CONFIGS["llm_call"])
        self.circuit_breaker = CircuitBreaker(
            name="anthropic_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

        # Token tracking
        self.usage = CumulativeUsage()

        logger.debug("LLMClient initialized", timeout=timeout)

    async def create_message(
        self,
        model: str,
        system: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        stop_sequences: list[str] | None = None,
    ) -> str:
        """
        Create a message completion with Claude.

        Args:
            model: Claude model ID
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            stop_sequences: Optional stop sequences

        Returns:
            Generated text response

        Raises:
            AuthenticationError: Invalid API key
            RateLimitError: Rate limit exceeded
            APITimeoutError: Request timed out
            NetworkError: Connection failed
            ServiceUnavailableError: API unavailable
            InvalidInputError: Invalid request parameters
        """
        async def _call() -> str:
            try:
                response = await self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=messages,
                    stop_sequences=stop_sequences or [],
                )

                # Track token usage
                usage = TokenUsage(
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=model,
                    cache_creation_input_tokens=getattr(
                        response.usage, "cache_creation_input_tokens", 0
                    ),
                    cache_read_input_tokens=getattr(
                        response.usage, "cache_read_input_tokens", 0
                    ),
                )
                self.usage.add_usage(usage)

                logger.debug(
                    "LLM call completed",
                    model=model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost_usd=round(usage.estimate_cost(), 4),
                )

                # Extract text from response
                if response.content and len(response.content) > 0:
                    return response.content[0].text
                return ""

            except AnthropicRateLimitError as e:
                # Extract retry_after from headers if available
                retry_after = 60.0
                if hasattr(e, "response") and e.response:
                    retry_after_header = e.response.headers.get("retry-after")
                    if retry_after_header:
                        try:
                            retry_after = float(retry_after_header)
                        except ValueError:
                            pass

                logger.warning(
                    "Rate limit hit",
                    retry_after=retry_after,
                    model=model,
                )
                raise RateLimitError(
                    message="Anthropic rate limit exceeded",
                    retry_after=retry_after,
                    limit_type="api",
                )

            except AnthropicTimeoutError as e:
                logger.warning("API timeout", model=model, timeout=self.timeout)
                raise APITimeoutError(
                    message="Anthropic API request timed out",
                    timeout_seconds=self.timeout,
                    endpoint="messages",
                )

            except AnthropicConnectionError as e:
                logger.warning("Connection error", error=str(e))
                raise NetworkError(
                    message="Failed to connect to Anthropic API",
                    original_error=str(e),
                )

            except APIStatusError as e:
                status_code = e.status_code

                if status_code == 401:
                    raise AuthenticationError(
                        message="Invalid Anthropic API key",
                        auth_type="api_key",
                    )
                elif status_code == 400:
                    raise InvalidInputError(
                        message=f"Invalid request: {e.message}",
                        field="request",
                        expected="valid API request",
                    )
                elif status_code == 429:
                    # Quota exceeded (different from rate limit)
                    raise QuotaExceededError(
                        message="Anthropic API quota exceeded",
                        quota_type="api_calls",
                    )
                elif status_code >= 500:
                    raise ServiceUnavailableError(
                        message="Anthropic API service unavailable",
                        service_name="anthropic",
                        status_code=status_code,
                    )
                else:
                    # Re-raise as network error for other status codes
                    raise NetworkError(
                        message=f"Anthropic API error: {e.message}",
                        original_error=str(e),
                    )

        # Execute with circuit breaker and retry
        async def _call_with_circuit_breaker() -> str:
            return await self.circuit_breaker.execute(_call)

        return await self.retry_handler.execute(_call_with_circuit_breaker)

    async def create_structured(
        self,
        model: str,
        system: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,  # Lower temperature for structured output
    ) -> T:
        """
        Create a structured response using a Pydantic model.

        This method instructs Claude to output JSON matching the Pydantic schema,
        then validates and parses the response.

        Args:
            model: Claude model ID
            system: System prompt
            messages: Conversation messages
            response_model: Pydantic model class for response
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower for consistency)

        Returns:
            Parsed Pydantic model instance

        Raises:
            InvalidInputError: If response doesn't match schema
            (Plus all errors from create_message)
        """
        # Generate JSON schema from Pydantic model
        schema = response_model.model_json_schema()
        schema_str = json.dumps(schema, indent=2)

        # Augment system prompt with JSON instructions
        structured_system = f"""{system}

IMPORTANT: You MUST respond with valid JSON that matches this schema exactly:
{schema_str}

Respond ONLY with the JSON object, no additional text or markdown formatting."""

        # Make the API call
        response_text = await self.create_message(
            model=model,
            system=structured_system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Parse JSON from response
        try:
            # Try to extract JSON from response (handle markdown code blocks)
            json_str = response_text.strip()
            if json_str.startswith("```"):
                # Remove markdown code block
                lines = json_str.split("\n")
                # Find the JSON content between ``` markers
                start_idx = 1 if lines[0].startswith("```") else 0
                end_idx = len(lines)
                for i, line in enumerate(lines[1:], 1):
                    if line.strip() == "```":
                        end_idx = i
                        break
                json_str = "\n".join(lines[start_idx:end_idx])

            data = json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse JSON from LLM response",
                error=str(e),
                response_preview=response_text[:500],
            )
            raise InvalidInputError(
                message=f"LLM response is not valid JSON: {e}",
                field="response",
                value=response_text[:200],
                expected="valid JSON",
            )

        # Validate against Pydantic model
        try:
            return response_model.model_validate(data)

        except ValidationError as e:
            logger.error(
                "LLM response failed schema validation",
                errors=e.errors(),
                response_preview=str(data)[:500],
            )
            raise InvalidInputError(
                message=f"LLM response doesn't match expected schema: {e}",
                field="response",
                expected=response_model.__name__,
            )

    async def create_message_for_agent(
        self,
        agent_name: str,
        system: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """
        Convenience method to call LLM with agent's configured model.

        Args:
            agent_name: Name of the agent (e.g., "data", "research")
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Generated text response
        """
        model = get_model_for_agent(agent_name)
        return await self.create_message(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def create_structured_for_agent(
        self,
        agent_name: str,
        system: str,
        messages: list[dict[str, str]],
        response_model: type[T],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> T:
        """
        Convenience method to get structured output with agent's configured model.

        Args:
            agent_name: Name of the agent (e.g., "data", "research")
            system: System prompt
            messages: Conversation messages
            response_model: Pydantic model class for response
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Parsed Pydantic model instance
        """
        model = get_model_for_agent(agent_name)
        return await self.create_structured(
            model=model,
            system=system,
            messages=messages,
            response_model=response_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    def get_usage_stats(self) -> dict[str, Any]:
        """Get cumulative usage statistics."""
        return self.usage.get_stats()

    def reset_usage_stats(self) -> None:
        """Reset cumulative usage statistics."""
        self.usage = CumulativeUsage()
        logger.debug("Usage stats reset")

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self.client.close()
        logger.debug("LLMClient closed")


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


@lru_cache
def get_llm_client() -> LLMClient:
    """
    Get cached LLM client instance.

    Returns:
        LLMClient: Configured LLM client

    Why cached:
    - Reuses HTTP connection pool
    - Maintains circuit breaker state
    - Tracks cumulative token usage
    """
    settings = get_settings()
    return LLMClient(api_key=settings.anthropic_api_key)


def create_llm_client(api_key: str | None = None, **kwargs: Any) -> LLMClient:
    """
    Create a new LLM client instance (not cached).

    Use this when you need a separate client with different settings.

    Args:
        api_key: Anthropic API key (defaults to settings)
        **kwargs: Additional arguments for LLMClient

    Returns:
        LLMClient: New LLM client instance
    """
    if api_key is None:
        settings = get_settings()
        api_key = settings.anthropic_api_key

    return LLMClient(api_key=api_key, **kwargs)
