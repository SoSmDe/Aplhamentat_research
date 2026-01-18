"""
Ralph Deep Research - Retry Logic and Circuit Breaker

Implements retry logic with exponential backoff and circuit breaker pattern
based on specs/ARCHITECTURE.md (Section 7: Retry Logic).

Why these patterns:
- Exponential backoff: Prevents overwhelming recovering services
- Jitter: Prevents thundering herd problem when multiple clients retry
- Circuit breaker: Protects against cascading failures

Usage:
    from src.tools.retry import with_retry, RetryHandler, CircuitBreaker

    # Decorator usage
    @with_retry("llm_call")
    async def call_claude(prompt: str) -> str:
        ...

    # Manual usage
    handler = RetryHandler(RETRY_CONFIGS["api_call"])
    result = await handler.execute(func, *args, **kwargs)

    # Circuit breaker
    breaker = CircuitBreaker("anthropic_api")
    result = await breaker.execute(func, *args, **kwargs)
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar

from src.tools.errors import (
    APITimeoutError,
    CircuitOpenError,
    NetworkError,
    RateLimitError,
    RetryExhaustedError,
    ServiceUnavailableError,
    TransientError,
)
from src.tools.logging import get_logger

logger = get_logger(__name__)

# Type variable for generic async functions
T = TypeVar("T")


# =============================================================================
# RETRY CONFIGURATION
# =============================================================================


@dataclass
class RetryConfig:
    """
    Configuration for retry logic.

    Based on specs/ARCHITECTURE.md Section 7.

    Attributes:
        max_attempts: Maximum number of retry attempts (including first try)
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay cap in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Jitter factor (±percentage of delay)
        retryable_exceptions: Tuple of exception types that trigger retry
        rate_limit_delay: Fixed delay for rate limit errors
    """

    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: float = 0.25  # ±25% jitter
    retryable_exceptions: tuple[type[Exception], ...] = field(
        default_factory=lambda: (
            APITimeoutError,
            RateLimitError,
            NetworkError,
            ServiceUnavailableError,
            TransientError,
        )
    )
    rate_limit_delay: float = 60.0

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")
        if not 0 <= self.jitter <= 1:
            raise ValueError("jitter must be between 0 and 1")


# Per-operation retry configurations from spec
RETRY_CONFIGS: dict[str, RetryConfig] = {
    "llm_call": RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=60.0,
        rate_limit_delay=60.0,
    ),
    "api_call": RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
    ),
    "web_search": RetryConfig(
        max_attempts=2,
        base_delay=5.0,
        max_delay=30.0,
    ),
    "file_generation": RetryConfig(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0,
    ),
    "database": RetryConfig(
        max_attempts=3,
        base_delay=0.5,
        max_delay=5.0,
    ),
}


# =============================================================================
# RETRY HANDLER
# =============================================================================


class RetryHandler:
    """
    Handles retry logic with exponential backoff.

    Why this implementation:
    - Separates retry logic from business logic
    - Configurable per operation type
    - Handles rate limits specially (fixed delay from error)
    - Adds jitter to prevent thundering herd

    Example:
        handler = RetryHandler(RETRY_CONFIGS["llm_call"])
        result = await handler.execute(call_api, prompt="Hello")
    """

    def __init__(self, config: RetryConfig) -> None:
        """Initialize with retry configuration."""
        self.config = config

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            RetryExhaustedError: When all retry attempts fail
            Exception: Any non-retryable exception
        """
        last_exception: Exception | None = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)

            except self.config.retryable_exceptions as e:
                last_exception = e
                delay = self._calculate_delay(attempt, e)

                logger.warning(
                    "Retry attempt failed",
                    attempt=attempt,
                    max_attempts=self.config.max_attempts,
                    error=str(e),
                    error_type=type(e).__name__,
                    delay_seconds=round(delay, 2),
                )

                if attempt < self.config.max_attempts:
                    await asyncio.sleep(delay)

            except Exception as e:
                # Non-retryable error - propagate immediately
                logger.error(
                    "Non-retryable error occurred",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise

        # All retries exhausted
        error_msg = f"Failed after {self.config.max_attempts} attempts"
        last_error_str = str(last_exception) if last_exception else None

        logger.error(
            "Retry exhausted",
            attempts=self.config.max_attempts,
            last_error=last_error_str,
        )

        raise RetryExhaustedError(
            message=error_msg,
            attempts=self.config.max_attempts,
            last_error=last_error_str,
        )

    def _calculate_delay(self, attempt: int, error: Exception) -> float:
        """
        Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (1-based)
            error: The error that triggered the retry

        Returns:
            Delay in seconds

        Backoff schedule (base=2s, max=60s):
        | Attempt | Base  | With Jitter (±25%) |
        |---------|-------|--------------------|
        |    1    |  2s   |   1.5s - 2.5s      |
        |    2    |  4s   |   3.0s - 5.0s      |
        |    3    |  8s   |   6.0s - 10.0s     |
        |    4    | 16s   |  12.0s - 20.0s     |
        |    5    | 32s   |  24.0s - 40.0s     |
        |   6+    | 60s   |  45.0s - 60.0s     |
        """
        # Rate limit errors use fixed delay or retry_after from error
        if isinstance(error, RateLimitError):
            base_delay = getattr(error, "retry_after", self.config.rate_limit_delay)
        else:
            # Exponential backoff: base * (exponential_base ^ (attempt - 1))
            base_delay = self.config.base_delay * (
                self.config.exponential_base ** (attempt - 1)
            )

        # Add jitter: ±jitter percentage of delay
        # jitter_range = base_delay * jitter
        # actual_jitter = random value in [-jitter_range, +jitter_range]
        jitter_range = base_delay * self.config.jitter
        jitter = jitter_range * (2 * random.random() - 1)
        delay = base_delay + jitter

        # Cap at max_delay
        return min(max(delay, 0), self.config.max_delay)


# =============================================================================
# RETRY DECORATOR
# =============================================================================


def with_retry(config_name: str = "llm_call") -> Callable[..., Callable[..., Any]]:
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        config_name: Key in RETRY_CONFIGS dict, defaults to "llm_call"

    Returns:
        Decorator function

    Example:
        @with_retry("api_call")
        async def fetch_data(url: str) -> dict:
            ...

    Why decorator pattern:
    - Clean separation of retry logic from business logic
    - Reusable across multiple functions
    - Easy to configure per function
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            config = RETRY_CONFIGS.get(config_name, RetryConfig())
            handler = RetryHandler(config)
            return await handler.execute(func, *args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================


class CircuitState(Enum):
    """
    Circuit breaker states.

    CLOSED: Normal operation, requests pass through
    OPEN: Failing, requests rejected immediately
    HALF_OPEN: Testing recovery with limited requests
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    State transitions:
    - CLOSED → (failures > threshold) → OPEN
    - OPEN → (timeout expires) → HALF_OPEN
    - HALF_OPEN → (success) → CLOSED
    - HALF_OPEN → (failure) → OPEN

    Why circuit breaker:
    - Prevents overwhelming failing services
    - Allows services time to recover
    - Fails fast instead of waiting for timeout
    - Provides visibility into service health

    Example:
        breaker = CircuitBreaker("anthropic_api")

        try:
            result = await breaker.execute(call_api, prompt="Hello")
        except CircuitOpenError:
            # Service is unavailable, use fallback
            result = get_cached_response()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            name: Name for logging/identification
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            half_open_max_calls: Max calls allowed in half-open state
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        # State tracking
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0
        self._success_count = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Number of consecutive failures."""
        return self._failure_count

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self._state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)."""
        return self._state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self._state == CircuitState.HALF_OPEN

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            CircuitOpenError: When circuit is open
            Exception: Any exception from func
        """
        if not self._can_execute():
            logger.warning(
                "Circuit breaker open",
                name=self.name,
                state=self._state.value,
                failure_count=self._failure_count,
            )
            raise CircuitOpenError(
                message=f"Circuit breaker '{self.name}' is open",
                service_name=self.name,
                recovery_time=self._get_recovery_time_remaining(),
            )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        """Check if request can be executed."""
        if self._state == CircuitState.CLOSED:
            return True

        if self._state == CircuitState.OPEN:
            if self._recovery_timeout_expired():
                self._transition_to_half_open()
                return True
            return False

        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.half_open_max_calls

        return False

    def _on_success(self) -> None:
        """Handle successful request."""
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            # After successful calls in half-open, close the circuit
            if self._half_open_calls >= self.half_open_max_calls:
                self._transition_to_closed()
        else:
            # Reset failure count on success in closed state
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed request."""
        self._failure_count += 1
        self._last_failure_time = _utc_now()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open goes back to open
            self._transition_to_open()
        elif self._failure_count >= self.failure_threshold:
            self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        previous_state = self._state
        self._state = CircuitState.OPEN
        logger.warning(
            "Circuit breaker opened",
            name=self.name,
            previous_state=previous_state.value,
            failure_count=self._failure_count,
        )

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        previous_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._half_open_calls = 0
        logger.info(
            "Circuit breaker half-open",
            name=self.name,
            previous_state=previous_state.value,
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        previous_state = self._state
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
        logger.info(
            "Circuit breaker closed",
            name=self.name,
            previous_state=previous_state.value,
        )

    def _recovery_timeout_expired(self) -> bool:
        """Check if recovery timeout has expired."""
        if self._last_failure_time is None:
            return True
        elapsed = (_utc_now() - self._last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout

    def _get_recovery_time_remaining(self) -> float | None:
        """Get remaining recovery time in seconds."""
        if self._last_failure_time is None:
            return None
        elapsed = (_utc_now() - self._last_failure_time).total_seconds()
        remaining = self.recovery_timeout - elapsed
        return max(0, remaining)

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info("Circuit breaker manually reset", name=self.name)

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "half_open_calls": self._half_open_calls,
            "last_failure_time": (
                self._last_failure_time.isoformat()
                if self._last_failure_time
                else None
            ),
            "recovery_time_remaining": self._get_recovery_time_remaining(),
        }


# =============================================================================
# COMBINED RETRY + CIRCUIT BREAKER
# =============================================================================


class ResilientExecutor:
    """
    Combines retry logic with circuit breaker for robust execution.

    Why combine:
    - Circuit breaker prevents overwhelming failing services
    - Retry handles transient failures within normal operation
    - Together they provide comprehensive fault tolerance

    Example:
        executor = ResilientExecutor(
            name="anthropic_api",
            retry_config=RETRY_CONFIGS["llm_call"],
        )
        result = await executor.execute(call_api, prompt="Hello")
    """

    def __init__(
        self,
        name: str,
        retry_config: RetryConfig | None = None,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> None:
        """
        Initialize resilient executor.

        Args:
            name: Name for logging/identification
            retry_config: Retry configuration (defaults to llm_call)
            failure_threshold: Circuit breaker failure threshold
            recovery_timeout: Circuit breaker recovery timeout
        """
        self.name = name
        self.retry_handler = RetryHandler(retry_config or RETRY_CONFIGS["llm_call"])
        self.circuit_breaker = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Execute with retry and circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function call

        Raises:
            CircuitOpenError: When circuit is open
            RetryExhaustedError: When all retries fail
            Exception: Any non-retryable exception
        """

        async def wrapped_with_retry() -> Any:
            return await self.retry_handler.execute(func, *args, **kwargs)

        return await self.circuit_breaker.execute(wrapped_with_retry)

    def get_stats(self) -> dict[str, Any]:
        """Get combined statistics."""
        return {
            "name": self.name,
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "retry_config": {
                "max_attempts": self.retry_handler.config.max_attempts,
                "base_delay": self.retry_handler.config.base_delay,
                "max_delay": self.retry_handler.config.max_delay,
            },
        }
