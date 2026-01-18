"""
Tests for logging configuration (Phase 2.2).

Verifies:
- Logger creation and configuration
- Sensitive data filtering
- Value truncation
- Context binding
"""

import pytest
import structlog

from src.tools.logging import (
    get_logger,
    configure_logging,
    bind_context,
    filter_sensitive_data,
    truncate_large_values,
    LogContext,
    SENSITIVE_KEYS,
    MAX_STRING_LENGTH,
    MAX_LIST_ITEMS,
)


class TestSensitiveDataFiltering:
    """Tests for sensitive data filtering."""

    def test_filters_exact_sensitive_keys(self) -> None:
        """Should filter exact matches of sensitive keys."""
        event_dict = {
            "api_key": "sk-ant-123",
            "password": "secret123",
            "token": "abc123",
            "message": "normal message",
        }
        result = filter_sensitive_data(None, "", event_dict)
        assert result["api_key"] == "[REDACTED]"
        assert result["password"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"
        assert result["message"] == "normal message"

    def test_filters_partial_key_matches(self) -> None:
        """Should filter keys containing sensitive terms."""
        event_dict = {
            "anthropic_api_key": "sk-ant-123",
            "auth_token": "abc123",
            "user_password_hash": "hash123",
            "normal_field": "value",
        }
        result = filter_sensitive_data(None, "", event_dict)
        assert result["anthropic_api_key"] == "[REDACTED]"
        assert result["auth_token"] == "[REDACTED]"
        assert result["user_password_hash"] == "[REDACTED]"
        assert result["normal_field"] == "value"

    def test_filters_nested_dicts(self) -> None:
        """Should filter sensitive data in nested dictionaries."""
        event_dict = {
            "config": {
                "api_key": "sk-ant-123",
                "endpoint": "https://api.anthropic.com",
            },
            "metadata": {
                "password": "secret",
                "user": "test_user",
            },
        }
        result = filter_sensitive_data(None, "", event_dict)
        assert result["config"]["api_key"] == "[REDACTED]"
        assert result["config"]["endpoint"] == "https://api.anthropic.com"
        assert result["metadata"]["password"] == "[REDACTED]"
        assert result["metadata"]["user"] == "test_user"

    def test_case_insensitive_filtering(self) -> None:
        """Should filter regardless of case."""
        event_dict = {
            "API_KEY": "sk-ant-123",
            "Password": "secret",
            "TOKEN": "abc",
        }
        result = filter_sensitive_data(None, "", event_dict)
        assert result["API_KEY"] == "[REDACTED]"
        assert result["Password"] == "[REDACTED]"
        assert result["TOKEN"] == "[REDACTED]"

    def test_sensitive_keys_list(self) -> None:
        """SENSITIVE_KEYS should include all expected keys."""
        expected_keys = {
            "api_key",
            "apikey",
            "anthropic_api_key",
            "password",
            "secret",
            "token",
            "authorization",
            "auth_token",
            "access_token",
            "refresh_token",
            "credentials",
            "private_key",
        }
        assert SENSITIVE_KEYS == expected_keys


class TestTruncation:
    """Tests for value truncation."""

    def test_truncates_long_strings(self) -> None:
        """Should truncate strings longer than MAX_STRING_LENGTH."""
        long_string = "x" * 2000
        event_dict = {"content": long_string}
        result = truncate_large_values(None, "", event_dict)

        assert len(result["content"]) < len(long_string)
        assert result["content"].startswith("x" * MAX_STRING_LENGTH)
        assert "truncated" in result["content"]
        assert "2000" in result["content"]

    def test_preserves_short_strings(self) -> None:
        """Should not truncate strings under MAX_STRING_LENGTH."""
        short_string = "x" * 100
        event_dict = {"content": short_string}
        result = truncate_large_values(None, "", event_dict)
        assert result["content"] == short_string

    def test_truncates_long_lists(self) -> None:
        """Should truncate lists with more than MAX_LIST_ITEMS."""
        long_list = list(range(50))
        event_dict = {"items": long_list}
        result = truncate_large_values(None, "", event_dict)

        assert len(result["items"]) == MAX_LIST_ITEMS + 1
        assert result["items"][:MAX_LIST_ITEMS] == list(range(MAX_LIST_ITEMS))
        assert "more items" in result["items"][-1]

    def test_preserves_short_lists(self) -> None:
        """Should not truncate lists under MAX_LIST_ITEMS."""
        short_list = [1, 2, 3]
        event_dict = {"items": short_list}
        result = truncate_large_values(None, "", event_dict)
        assert result["items"] == short_list


class TestLoggerConfiguration:
    """Tests for logger configuration."""

    def test_get_logger_returns_bound_logger(self) -> None:
        """get_logger should return a structlog BoundLogger."""
        logger = get_logger("test_module")
        assert logger is not None
        # Verify it has standard logging methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "debug")

    def test_configure_logging_json_output(self) -> None:
        """configure_logging should work with JSON output."""
        # Should not raise
        configure_logging(log_level="DEBUG", json_output=True)

    def test_configure_logging_console_output(self) -> None:
        """configure_logging should work with console output."""
        # Should not raise
        configure_logging(log_level="INFO", json_output=False)

    def test_configure_logging_levels(self) -> None:
        """configure_logging should accept various log levels."""
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            configure_logging(log_level=level)


class TestContextBinding:
    """Tests for context binding."""

    def test_bind_context_returns_logger(self) -> None:
        """bind_context should return a logger with bound context."""
        logger = bind_context(session_id="sess_123", round=1)
        assert logger is not None

    def test_log_context_manager(self) -> None:
        """LogContext should work as context manager."""
        with LogContext(session_id="sess_123", agent="data") as logger:
            assert logger is not None
        # Context should be cleared after exit


class TestLoggerUsage:
    """Tests for practical logger usage."""

    def test_logger_with_extra_fields(self) -> None:
        """Logger should accept extra fields."""
        logger = get_logger("test")
        # Should not raise
        logger.info("Processing task", task_id="d1", session_id="sess_123")

    def test_logger_exception_handling(self) -> None:
        """Logger should handle exception info."""
        logger = get_logger("test")
        try:
            raise ValueError("Test error")
        except ValueError:
            # Should not raise
            logger.exception("Error occurred")
