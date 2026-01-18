"""
Tests for retry logic and circuit breaker (Phase 2.3).

Verifies:
- RetryConfig validation
- RetryHandler exponential backoff
- with_retry decorator
- CircuitBreaker state transitions
- ResilientExecutor combined behavior
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from src.tools.errors import (
    APITimeoutError,
    CircuitOpenError,
    NetworkError,
    RateLimitError,
    RetryExhaustedError,
    InvalidInputError,
)
from src.tools.retry import (
    RetryConfig,
    RETRY_CONFIGS,
    RetryHandler,
    with_retry,
    CircuitBreaker,
    CircuitState,
    ResilientExecutor,
)


class TestRetryConfig:
    """Tests for RetryConfig dataclass."""

    def test_default_values(self) -> None:
        """RetryConfig should have sensible defaults."""
        config = RetryConfig()
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter == 0.25
        assert config.rate_limit_delay == 60.0

    def test_custom_values(self) -> None:
        """RetryConfig should accept custom values."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=0.1,
            rate_limit_delay=30.0,
        )
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter == 0.1
        assert config.rate_limit_delay == 30.0

    def test_validation_max_attempts(self) -> None:
        """max_attempts must be at least 1."""
        with pytest.raises(ValueError, match="max_attempts"):
            RetryConfig(max_attempts=0)

    def test_validation_base_delay(self) -> None:
        """base_delay must be non-negative."""
        with pytest.raises(ValueError, match="base_delay"):
            RetryConfig(base_delay=-1.0)

    def test_validation_max_delay(self) -> None:
        """max_delay must be >= base_delay."""
        with pytest.raises(ValueError, match="max_delay"):
            RetryConfig(base_delay=10.0, max_delay=5.0)

    def test_validation_exponential_base(self) -> None:
        """exponential_base must be >= 1."""
        with pytest.raises(ValueError, match="exponential_base"):
            RetryConfig(exponential_base=0.5)

    def test_validation_jitter(self) -> None:
        """jitter must be between 0 and 1."""
        with pytest.raises(ValueError, match="jitter"):
            RetryConfig(jitter=1.5)
        with pytest.raises(ValueError, match="jitter"):
            RetryConfig(jitter=-0.1)


class TestRetryConfigs:
    """Tests for predefined retry configurations."""

    def test_llm_call_config(self) -> None:
        """llm_call config should have correct values."""
        config = RETRY_CONFIGS["llm_call"]
        assert config.max_attempts == 3
        assert config.base_delay == 2.0
        assert config.rate_limit_delay == 60.0

    def test_api_call_config(self) -> None:
        """api_call config should have correct values."""
        config = RETRY_CONFIGS["api_call"]
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0

    def test_web_search_config(self) -> None:
        """web_search config should have correct values."""
        config = RETRY_CONFIGS["web_search"]
        assert config.max_attempts == 2
        assert config.base_delay == 5.0

    def test_file_generation_config(self) -> None:
        """file_generation config should have correct values."""
        config = RETRY_CONFIGS["file_generation"]
        assert config.max_attempts == 2
        assert config.base_delay == 1.0
        assert config.max_delay == 10.0

    def test_database_config(self) -> None:
        """database config should have correct values."""
        config = RETRY_CONFIGS["database"]
        assert config.max_attempts == 3
        assert config.base_delay == 0.5


class TestRetryHandler:
    """Tests for RetryHandler class."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self) -> None:
        """Should return result on first successful call."""
        handler = RetryHandler(RetryConfig(max_attempts=3))
        mock_func = AsyncMock(return_value="success")

        result = await handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_success_after_retries(self) -> None:
        """Should retry and eventually succeed."""
        handler = RetryHandler(RetryConfig(max_attempts=3, base_delay=0.01))
        mock_func = AsyncMock(
            side_effect=[NetworkError("Failed"), NetworkError("Failed"), "success"]
        )

        result = await handler.execute(mock_func)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self) -> None:
        """Should raise RetryExhaustedError after all attempts fail."""
        handler = RetryHandler(RetryConfig(max_attempts=2, base_delay=0.01))
        mock_func = AsyncMock(side_effect=NetworkError("Always fails"))

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.execute(mock_func)

        assert exc_info.value.details["attempts"] == 2
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_error_propagates(self) -> None:
        """Should propagate non-retryable errors immediately."""
        handler = RetryHandler(RetryConfig(max_attempts=3, base_delay=0.01))
        mock_func = AsyncMock(side_effect=InvalidInputError("Bad input"))

        with pytest.raises(InvalidInputError):
            await handler.execute(mock_func)

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_delay_calculation_exponential(self) -> None:
        """Should use exponential backoff."""
        config = RetryConfig(
            max_attempts=4,
            base_delay=1.0,
            exponential_base=2.0,
            jitter=0.0,  # Disable jitter for predictable testing
        )
        handler = RetryHandler(config)

        # Test delay calculation for each attempt
        delays = [
            handler._calculate_delay(1, NetworkError("test")),
            handler._calculate_delay(2, NetworkError("test")),
            handler._calculate_delay(3, NetworkError("test")),
        ]

        assert delays[0] == 1.0  # base_delay * 2^0
        assert delays[1] == 2.0  # base_delay * 2^1
        assert delays[2] == 4.0  # base_delay * 2^2

    @pytest.mark.asyncio
    async def test_delay_with_jitter(self) -> None:
        """Should add jitter to delays."""
        config = RetryConfig(
            max_attempts=2,
            base_delay=10.0,
            jitter=0.25,
        )
        handler = RetryHandler(config)

        # Calculate multiple delays to verify jitter adds variation
        delays = [
            handler._calculate_delay(1, NetworkError("test"))
            for _ in range(100)
        ]

        # With 25% jitter, delays should be in range [7.5, 12.5]
        assert all(7.5 <= d <= 12.5 for d in delays)
        # Should have some variation
        assert len(set(delays)) > 1

    @pytest.mark.asyncio
    async def test_rate_limit_uses_fixed_delay(self) -> None:
        """Should use retry_after from RateLimitError."""
        config = RetryConfig(
            max_attempts=2,
            base_delay=1.0,
            rate_limit_delay=30.0,
            jitter=0.0,
        )
        handler = RetryHandler(config)

        # RateLimitError with retry_after should use that value
        error = RateLimitError(retry_after=45.0)
        delay = handler._calculate_delay(1, error)
        assert delay == 45.0

    @pytest.mark.asyncio
    async def test_delay_capped_at_max(self) -> None:
        """Should cap delay at max_delay."""
        config = RetryConfig(
            max_attempts=10,
            base_delay=10.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=0.0,
        )
        handler = RetryHandler(config)

        # Attempt 5 would be 10 * 2^4 = 160, but should cap at 30
        delay = handler._calculate_delay(5, NetworkError("test"))
        assert delay == 30.0


class TestWithRetryDecorator:
    """Tests for with_retry decorator."""

    @pytest.mark.asyncio
    async def test_decorator_with_config_name(self) -> None:
        """Decorator should use named config."""

        @with_retry("api_call")
        async def test_func() -> str:
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_default_config(self) -> None:
        """Decorator should use llm_call config by default."""

        @with_retry()
        async def test_func() -> str:
            return "success"

        result = await test_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_decorator_retries_on_failure(self) -> None:
        """Decorated function should retry on transient errors."""
        call_count = 0

        @with_retry("database")  # 0.5s base delay
        async def test_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise NetworkError("Failed")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 2


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_closed(self) -> None:
        """Circuit breaker should start in CLOSED state."""
        breaker = CircuitBreaker("test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_success_keeps_closed(self) -> None:
        """Successful calls should keep circuit closed."""
        breaker = CircuitBreaker("test", failure_threshold=3)
        mock_func = AsyncMock(return_value="success")

        for _ in range(5):
            result = await breaker.execute(mock_func)
            assert result == "success"

        assert breaker.is_closed
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_failures_open_circuit(self) -> None:
        """Consecutive failures should open circuit."""
        breaker = CircuitBreaker("test", failure_threshold=3)
        mock_func = AsyncMock(side_effect=Exception("Fail"))

        # Fail threshold times
        for _ in range(3):
            with pytest.raises(Exception):
                await breaker.execute(mock_func)

        assert breaker.is_open
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_circuit_rejects_calls(self) -> None:
        """Open circuit should reject calls immediately."""
        breaker = CircuitBreaker("test", failure_threshold=2)
        mock_func = AsyncMock(side_effect=Exception("Fail"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(mock_func)

        assert breaker.is_open

        # Next call should be rejected with CircuitOpenError
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.execute(mock_func)

        assert "test" in exc_info.value.details["service_name"]

    @pytest.mark.asyncio
    async def test_recovery_timeout_transitions_to_half_open(self) -> None:
        """Circuit should transition to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.1)
        mock_func = AsyncMock(side_effect=Exception("Fail"))

        # Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(mock_func)

        assert breaker.is_open

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Mock should succeed now
        mock_func.reset_mock()
        mock_func.side_effect = None
        mock_func.return_value = "success"

        result = await breaker.execute(mock_func)
        assert result == "success"
        assert breaker.is_half_open or breaker.is_closed

    @pytest.mark.asyncio
    async def test_half_open_success_closes_circuit(self) -> None:
        """Successful calls in HALF_OPEN should close circuit."""
        breaker = CircuitBreaker(
            "test",
            failure_threshold=2,
            recovery_timeout=0.01,
            half_open_max_calls=2,
        )

        # Open the circuit
        mock_func = AsyncMock(side_effect=Exception("Fail"))
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(mock_func)

        # Wait for recovery
        await asyncio.sleep(0.02)

        # Now succeed
        mock_func.side_effect = None
        mock_func.return_value = "success"

        for _ in range(2):
            await breaker.execute(mock_func)

        assert breaker.is_closed

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens_circuit(self) -> None:
        """Failure in HALF_OPEN should reopen circuit."""
        breaker = CircuitBreaker("test", failure_threshold=2, recovery_timeout=0.01)

        # Open the circuit
        mock_func = AsyncMock(side_effect=Exception("Fail"))
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.execute(mock_func)

        # Wait for recovery
        await asyncio.sleep(0.02)

        # Fail again in half-open
        with pytest.raises(Exception):
            await breaker.execute(mock_func)

        assert breaker.is_open

    def test_reset(self) -> None:
        """Manual reset should close circuit."""
        breaker = CircuitBreaker("test", failure_threshold=2)
        breaker._state = CircuitState.OPEN
        breaker._failure_count = 5

        breaker.reset()

        assert breaker.is_closed
        assert breaker.failure_count == 0

    def test_get_stats(self) -> None:
        """get_stats should return circuit information."""
        breaker = CircuitBreaker("test_service")
        stats = breaker.get_stats()

        assert stats["name"] == "test_service"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert "success_count" in stats


class TestResilientExecutor:
    """Tests for ResilientExecutor (combined retry + circuit breaker)."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        """Should execute successfully."""
        executor = ResilientExecutor("test")
        mock_func = AsyncMock(return_value="success")

        result = await executor.execute(mock_func)

        assert result == "success"

    @pytest.mark.asyncio
    async def test_retries_within_circuit(self) -> None:
        """Should retry transient errors within circuit breaker."""
        executor = ResilientExecutor(
            "test",
            retry_config=RetryConfig(max_attempts=3, base_delay=0.01),
        )
        call_count = 0

        async def flaky_func() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise NetworkError("Flaky")
            return "success"

        result = await executor.execute(flaky_func)

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_circuit_opens_after_exhausted_retries(self) -> None:
        """Circuit should open after retry exhaustion."""
        executor = ResilientExecutor(
            "test",
            retry_config=RetryConfig(max_attempts=2, base_delay=0.01),
            failure_threshold=2,
        )
        mock_func = AsyncMock(side_effect=NetworkError("Always fails"))

        # First call: retries exhausted
        with pytest.raises(RetryExhaustedError):
            await executor.execute(mock_func)

        # Second call: retries exhausted again
        with pytest.raises(RetryExhaustedError):
            await executor.execute(mock_func)

        # Circuit should be open now
        assert executor.circuit_breaker.is_open

    def test_get_stats(self) -> None:
        """get_stats should return combined statistics."""
        executor = ResilientExecutor("test_executor")
        stats = executor.get_stats()

        assert stats["name"] == "test_executor"
        assert "circuit_breaker" in stats
        assert "retry_config" in stats
