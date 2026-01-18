"""
Tests for error classes (Phase 2.1).

Verifies:
- Error hierarchy and inheritance
- Error attributes and serialization
- Specific error types and their properties
"""

import pytest

from src.tools.errors import (
    # Base
    RalphError,
    # Transient
    TransientError,
    APITimeoutError,
    RateLimitError,
    NetworkError,
    ServiceUnavailableError,
    # Permanent
    PermanentError,
    InvalidInputError,
    AuthenticationError,
    QuotaExceededError,
    DataNotFoundError,
    # System
    SystemError,
    DatabaseError,
    StorageFullError,
    ConfigurationError,
    # Session
    SessionNotFoundError,
    SessionFailedError,
    BriefNotApprovedError,
    # Retry
    RetryExhaustedError,
    CircuitOpenError,
    # Agent
    AgentError,
    AgentTimeoutError,
    AgentExecutionError,
)


class TestRalphError:
    """Tests for base RalphError class."""

    def test_basic_error(self) -> None:
        """RalphError should store message and defaults."""
        error = RalphError("Something went wrong")
        assert str(error) == "[RALPH_ERROR] Something went wrong"
        assert error.message == "Something went wrong"
        assert error.code == "RALPH_ERROR"
        assert error.details == {}
        assert error.recoverable is False

    def test_error_with_all_fields(self) -> None:
        """RalphError should accept all optional fields."""
        error = RalphError(
            message="Custom error",
            code="CUSTOM_CODE",
            details={"key": "value"},
            recoverable=True,
        )
        assert error.code == "CUSTOM_CODE"
        assert error.details == {"key": "value"}
        assert error.recoverable is True

    def test_to_dict(self) -> None:
        """to_dict should return serializable dictionary."""
        error = RalphError(
            message="Test error",
            code="TEST",
            details={"foo": "bar"},
            recoverable=True,
        )
        result = error.to_dict()
        assert result == {
            "code": "TEST",
            "message": "Test error",
            "details": {"foo": "bar"},
            "recoverable": True,
        }


class TestTransientErrors:
    """Tests for transient (retryable) errors."""

    def test_transient_error_is_recoverable(self) -> None:
        """TransientError should always be recoverable."""
        error = TransientError("Temporary issue")
        assert error.recoverable is True
        assert isinstance(error, RalphError)

    def test_api_timeout_error(self) -> None:
        """APITimeoutError should have timeout details."""
        error = APITimeoutError(
            message="Request timed out",
            timeout_seconds=30.0,
            endpoint="/api/chat",
        )
        assert error.code == "API_TIMEOUT"
        assert error.details["timeout_seconds"] == 30.0
        assert error.details["endpoint"] == "/api/chat"
        assert error.recoverable is True

    def test_rate_limit_error(self) -> None:
        """RateLimitError should have retry_after attribute."""
        error = RateLimitError(
            message="Too many requests",
            retry_after=60.0,
            limit_type="requests_per_minute",
        )
        assert error.code == "RATE_LIMIT"
        assert error.retry_after == 60.0
        assert error.details["retry_after"] == 60.0
        assert error.details["limit_type"] == "requests_per_minute"

    def test_network_error(self) -> None:
        """NetworkError should have original error details."""
        error = NetworkError(
            message="Connection refused",
            original_error="ConnectionRefusedError",
        )
        assert error.code == "NETWORK_ERROR"
        assert error.details["original_error"] == "ConnectionRefusedError"

    def test_service_unavailable_error(self) -> None:
        """ServiceUnavailableError should have service details."""
        error = ServiceUnavailableError(
            message="API is down",
            service_name="anthropic",
            status_code=503,
        )
        assert error.code == "SERVICE_UNAVAILABLE"
        assert error.details["service_name"] == "anthropic"
        assert error.details["status_code"] == 503


class TestPermanentErrors:
    """Tests for permanent (non-retryable) errors."""

    def test_permanent_error_not_recoverable(self) -> None:
        """PermanentError should not be recoverable."""
        error = PermanentError("Fatal error")
        assert error.recoverable is False
        assert isinstance(error, RalphError)

    def test_invalid_input_error(self) -> None:
        """InvalidInputError should have field details."""
        error = InvalidInputError(
            message="Invalid email",
            field="email",
            value="not-an-email",
            expected="valid email format",
        )
        assert error.code == "INVALID_INPUT"
        assert error.details["field"] == "email"
        assert error.details["value"] == "not-an-email"
        assert error.details["expected"] == "valid email format"

    def test_invalid_input_truncates_value(self) -> None:
        """InvalidInputError should truncate long values."""
        long_value = "x" * 200
        error = InvalidInputError(value=long_value)
        assert len(error.details["value"]) == 100

    def test_authentication_error(self) -> None:
        """AuthenticationError should have auth type."""
        error = AuthenticationError(
            message="Invalid API key",
            auth_type="api_key",
        )
        assert error.code == "AUTH_ERROR"
        assert error.details["auth_type"] == "api_key"

    def test_quota_exceeded_error(self) -> None:
        """QuotaExceededError should have usage details."""
        error = QuotaExceededError(
            message="Monthly quota exceeded",
            quota_type="tokens",
            current_usage=100000,
            limit=50000,
        )
        assert error.code == "QUOTA_EXCEEDED"
        assert error.details["quota_type"] == "tokens"
        assert error.details["current_usage"] == 100000
        assert error.details["limit"] == 50000

    def test_data_not_found_error(self) -> None:
        """DataNotFoundError should have resource details."""
        error = DataNotFoundError(
            message="Session not found",
            resource_type="session",
            resource_id="sess_123",
        )
        assert error.code == "DATA_NOT_FOUND"
        assert error.details["resource_type"] == "session"
        assert error.details["resource_id"] == "sess_123"


class TestSystemErrors:
    """Tests for system-level errors."""

    def test_system_error_not_recoverable(self) -> None:
        """SystemError should not be recoverable."""
        error = SystemError("System failure")
        assert error.recoverable is False
        assert isinstance(error, RalphError)

    def test_database_error(self) -> None:
        """DatabaseError should have operation details."""
        error = DatabaseError(
            message="Failed to insert",
            operation="INSERT",
            original_error="IntegrityError",
        )
        assert error.code == "DATABASE_ERROR"
        assert error.details["operation"] == "INSERT"
        assert error.details["original_error"] == "IntegrityError"

    def test_storage_full_error(self) -> None:
        """StorageFullError should have storage details."""
        error = StorageFullError(
            message="Disk full",
            storage_type="session_files",
            current_size_mb=100.5,
            limit_mb=50.0,
        )
        assert error.code == "STORAGE_FULL"
        assert error.details["storage_type"] == "session_files"
        assert error.details["current_size_mb"] == 100.5
        assert error.details["limit_mb"] == 50.0

    def test_configuration_error(self) -> None:
        """ConfigurationError should have config details."""
        error = ConfigurationError(
            message="Missing API key",
            config_key="ANTHROPIC_API_KEY",
            expected="sk-ant-...",
        )
        assert error.code == "CONFIG_ERROR"
        assert error.details["config_key"] == "ANTHROPIC_API_KEY"
        assert error.details["expected"] == "sk-ant-..."


class TestSessionErrors:
    """Tests for session-related errors."""

    def test_session_not_found_error(self) -> None:
        """SessionNotFoundError should have session_id."""
        error = SessionNotFoundError(
            message="Session does not exist",
            session_id="sess_abc123",
        )
        assert error.code == "SESSION_NOT_FOUND"
        assert error.details["session_id"] == "sess_abc123"
        assert isinstance(error, PermanentError)

    def test_session_failed_error(self) -> None:
        """SessionFailedError should have session and error details."""
        error = SessionFailedError(
            message="Session crashed",
            session_id="sess_abc123",
            original_error="OutOfMemoryError",
        )
        assert error.code == "SESSION_FAILED"
        assert error.details["session_id"] == "sess_abc123"
        assert error.details["original_error"] == "OutOfMemoryError"

    def test_brief_not_approved_error(self) -> None:
        """BriefNotApprovedError should have brief status."""
        error = BriefNotApprovedError(
            message="Please approve the brief",
            session_id="sess_abc123",
            brief_status="draft",
        )
        assert error.code == "BRIEF_NOT_APPROVED"
        assert error.details["session_id"] == "sess_abc123"
        assert error.details["brief_status"] == "draft"


class TestRetryErrors:
    """Tests for retry-related errors."""

    def test_retry_exhausted_error(self) -> None:
        """RetryExhaustedError should have attempt details."""
        error = RetryExhaustedError(
            message="All retries failed",
            attempts=3,
            last_error="ConnectionError",
        )
        assert error.code == "RETRY_EXHAUSTED"
        assert error.details["attempts"] == 3
        assert error.details["last_error"] == "ConnectionError"
        assert isinstance(error, PermanentError)

    def test_circuit_open_error(self) -> None:
        """CircuitOpenError should have recovery details."""
        error = CircuitOpenError(
            message="Circuit is open",
            service_name="anthropic_api",
            recovery_time=30.5,
        )
        assert error.code == "CIRCUIT_OPEN"
        assert error.details["service_name"] == "anthropic_api"
        assert error.details["recovery_time"] == 30.5
        assert isinstance(error, TransientError)


class TestAgentErrors:
    """Tests for agent-related errors."""

    def test_agent_error_base(self) -> None:
        """AgentError should have agent context."""
        error = AgentError(
            message="Agent failed",
            agent_name="data",
            task_id="d1",
        )
        assert error.details["agent_name"] == "data"
        assert error.details["task_id"] == "d1"
        assert isinstance(error, RalphError)

    def test_agent_timeout_error(self) -> None:
        """AgentTimeoutError should be transient."""
        error = AgentTimeoutError(
            message="Agent timed out",
            agent_name="research",
            task_id="r1",
            timeout_seconds=90.0,
        )
        assert error.code == "AGENT_TIMEOUT"
        assert error.details["agent_name"] == "research"
        assert error.details["task_id"] == "r1"
        assert error.details["timeout_seconds"] == 90.0
        assert error.recoverable is True

    def test_agent_execution_error(self) -> None:
        """AgentExecutionError should have error details."""
        error = AgentExecutionError(
            message="Agent crashed",
            agent_name="planner",
            task_id="p1",
            original_error="KeyError: 'missing_key'",
        )
        assert error.code == "AGENT_EXECUTION_ERROR"
        assert error.details["agent_name"] == "planner"
        assert error.details["original_error"] == "KeyError: 'missing_key'"
        assert error.recoverable is False


class TestErrorInheritance:
    """Tests for error class hierarchy."""

    def test_transient_errors_inherit_correctly(self) -> None:
        """All transient errors should inherit from TransientError."""
        transient_classes = [
            APITimeoutError,
            RateLimitError,
            NetworkError,
            ServiceUnavailableError,
            CircuitOpenError,
        ]
        for cls in transient_classes:
            instance = cls()
            assert isinstance(instance, TransientError)
            assert isinstance(instance, RalphError)
            assert instance.recoverable is True

    def test_permanent_errors_inherit_correctly(self) -> None:
        """All permanent errors should inherit from PermanentError."""
        permanent_classes = [
            InvalidInputError,
            AuthenticationError,
            QuotaExceededError,
            DataNotFoundError,
            SessionNotFoundError,
            SessionFailedError,
            BriefNotApprovedError,
            RetryExhaustedError,
        ]
        for cls in permanent_classes:
            instance = cls()
            assert isinstance(instance, PermanentError)
            assert isinstance(instance, RalphError)
            assert instance.recoverable is False

    def test_system_errors_inherit_correctly(self) -> None:
        """All system errors should inherit from SystemError."""
        system_classes = [
            DatabaseError,
            StorageFullError,
            ConfigurationError,
        ]
        for cls in system_classes:
            instance = cls()
            assert isinstance(instance, SystemError)
            assert isinstance(instance, RalphError)
            assert instance.recoverable is False
