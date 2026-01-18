"""
Ralph Deep Research - Error Classes

Error hierarchy for the Ralph research system based on specs/ARCHITECTURE.md.

Error Categories:
1. TransientError: Retryable errors (timeouts, rate limits, network issues)
2. PermanentError: Non-retryable errors (invalid input, auth failures)
3. SystemError: Errors requiring intervention (database, storage, config)

Why this hierarchy matters:
- Retry logic can check isinstance(error, TransientError) to decide retry
- API layer converts errors to appropriate HTTP status codes
- Logging can categorize errors by severity
"""

from typing import Any


# =============================================================================
# BASE ERROR
# =============================================================================

class RalphError(Exception):
    """
    Base error class for all Ralph errors.

    Provides common structure:
    - message: Human-readable error description
    - code: Machine-readable error code
    - details: Additional context for debugging
    - recoverable: Whether the error can be recovered from

    Why: Unified error handling across all components.
    """

    def __init__(
        self,
        message: str,
        code: str = "RALPH_ERROR",
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.recoverable = recoverable

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary for API responses."""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details,
            "recoverable": self.recoverable,
        }

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# =============================================================================
# TRANSIENT ERRORS (Retryable)
# =============================================================================

class TransientError(RalphError):
    """
    Base class for retryable errors.

    These errors may succeed on retry:
    - Network glitches
    - Temporary service unavailability
    - Rate limits (with appropriate backoff)

    Why separate class: Retry logic can check isinstance(e, TransientError)
    to decide whether to retry or propagate the error.
    """

    def __init__(
        self,
        message: str,
        code: str = "TRANSIENT_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details, recoverable=True)


class APITimeoutError(TransientError):
    """
    API call timed out.

    Why retryable: Server may have been temporarily overloaded.
    Retry strategy: Exponential backoff.
    """

    def __init__(
        self,
        message: str = "API request timed out",
        timeout_seconds: float | None = None,
        endpoint: str | None = None,
    ) -> None:
        details = {}
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        if endpoint is not None:
            details["endpoint"] = endpoint
        super().__init__(message, "API_TIMEOUT", details)


class RateLimitError(TransientError):
    """
    Rate limit exceeded.

    Why retryable: Will succeed after waiting for rate limit reset.
    Retry strategy: Fixed delay from retry_after, not exponential backoff.
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float = 60.0,
        limit_type: str | None = None,
    ) -> None:
        details = {"retry_after": retry_after}
        if limit_type is not None:
            details["limit_type"] = limit_type
        super().__init__(message, "RATE_LIMIT", details)
        self.retry_after = retry_after


class NetworkError(TransientError):
    """
    Network connectivity issue.

    Why retryable: Network may recover.
    Retry strategy: Exponential backoff with jitter.
    """

    def __init__(
        self,
        message: str = "Network error occurred",
        original_error: str | None = None,
    ) -> None:
        details = {}
        if original_error is not None:
            details["original_error"] = original_error
        super().__init__(message, "NETWORK_ERROR", details)


class ServiceUnavailableError(TransientError):
    """
    External service temporarily unavailable.

    Why retryable: Service may come back online.
    Retry strategy: Exponential backoff, consider circuit breaker.
    """

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        service_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        details = {}
        if service_name is not None:
            details["service_name"] = service_name
        if status_code is not None:
            details["status_code"] = status_code
        super().__init__(message, "SERVICE_UNAVAILABLE", details)


# =============================================================================
# PERMANENT ERRORS (Not Retryable)
# =============================================================================

class PermanentError(RalphError):
    """
    Base class for non-retryable errors.

    These errors will not succeed on retry:
    - Invalid input data
    - Authentication failures
    - Resource not found

    Why separate class: Retry logic should NOT retry these errors.
    They require user intervention or code fixes.
    """

    def __init__(
        self,
        message: str,
        code: str = "PERMANENT_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details, recoverable=False)


class InvalidInputError(PermanentError):
    """
    Input data is invalid.

    Why not retryable: Same input will always fail validation.
    Resolution: Fix the input data.
    """

    def __init__(
        self,
        message: str = "Invalid input data",
        field: str | None = None,
        value: Any = None,
        expected: str | None = None,
    ) -> None:
        details = {}
        if field is not None:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)[:100]  # Truncate for safety
        if expected is not None:
            details["expected"] = expected
        super().__init__(message, "INVALID_INPUT", details)


class AuthenticationError(PermanentError):
    """
    Authentication failed.

    Why not retryable: Credentials are invalid.
    Resolution: Check API key, refresh tokens.
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        auth_type: str | None = None,
    ) -> None:
        details = {}
        if auth_type is not None:
            details["auth_type"] = auth_type
        super().__init__(message, "AUTH_ERROR", details)


class QuotaExceededError(PermanentError):
    """
    Usage quota exceeded.

    Why not retryable: Need to wait for quota reset or upgrade.
    Resolution: Wait for quota reset or increase quota.
    """

    def __init__(
        self,
        message: str = "Usage quota exceeded",
        quota_type: str | None = None,
        current_usage: int | None = None,
        limit: int | None = None,
    ) -> None:
        details = {}
        if quota_type is not None:
            details["quota_type"] = quota_type
        if current_usage is not None:
            details["current_usage"] = current_usage
        if limit is not None:
            details["limit"] = limit
        super().__init__(message, "QUOTA_EXCEEDED", details)


class DataNotFoundError(PermanentError):
    """
    Requested data not found.

    Why not retryable: Data doesn't exist.
    Resolution: Check if resource exists, use different query.
    """

    def __init__(
        self,
        message: str = "Data not found",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        details = {}
        if resource_type is not None:
            details["resource_type"] = resource_type
        if resource_id is not None:
            details["resource_id"] = resource_id
        super().__init__(message, "DATA_NOT_FOUND", details)


# =============================================================================
# SYSTEM ERRORS (Requires Intervention)
# =============================================================================

class SystemError(RalphError):
    """
    Base class for system-level errors.

    These errors indicate infrastructure problems:
    - Database failures
    - Storage issues
    - Configuration problems

    Why separate class: May need operator intervention, not user action.
    Should trigger alerts and logging.
    """

    def __init__(
        self,
        message: str,
        code: str = "SYSTEM_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, code, details, recoverable=False)


class DatabaseError(SystemError):
    """
    Database operation failed.

    Why system error: May indicate DB connection issues, corruption.
    Resolution: Check database connectivity, repair if needed.
    """

    def __init__(
        self,
        message: str = "Database error occurred",
        operation: str | None = None,
        original_error: str | None = None,
    ) -> None:
        details = {}
        if operation is not None:
            details["operation"] = operation
        if original_error is not None:
            details["original_error"] = original_error
        super().__init__(message, "DATABASE_ERROR", details)


class StorageFullError(SystemError):
    """
    Storage capacity exceeded.

    Why system error: Need to increase storage or clean up.
    Resolution: Free up space, increase storage quota.
    """

    def __init__(
        self,
        message: str = "Storage capacity exceeded",
        storage_type: str | None = None,
        current_size_mb: float | None = None,
        limit_mb: float | None = None,
    ) -> None:
        details = {}
        if storage_type is not None:
            details["storage_type"] = storage_type
        if current_size_mb is not None:
            details["current_size_mb"] = current_size_mb
        if limit_mb is not None:
            details["limit_mb"] = limit_mb
        super().__init__(message, "STORAGE_FULL", details)


class ConfigurationError(SystemError):
    """
    Configuration is invalid or missing.

    Why system error: Application cannot function without proper config.
    Resolution: Fix configuration files or environment variables.
    """

    def __init__(
        self,
        message: str = "Configuration error",
        config_key: str | None = None,
        expected: str | None = None,
    ) -> None:
        details = {}
        if config_key is not None:
            details["config_key"] = config_key
        if expected is not None:
            details["expected"] = expected
        super().__init__(message, "CONFIG_ERROR", details)


# =============================================================================
# SESSION ERRORS
# =============================================================================

class SessionNotFoundError(PermanentError):
    """
    Session does not exist.

    Why not retryable: Session ID is invalid.
    Resolution: Create a new session.
    """

    def __init__(
        self,
        message: str = "Session not found",
        session_id: str | None = None,
    ) -> None:
        details = {}
        if session_id is not None:
            details["session_id"] = session_id
        super().__init__(message, "SESSION_NOT_FOUND", details)


class SessionFailedError(PermanentError):
    """
    Session is in failed state.

    Why not retryable: Session has permanently failed.
    Resolution: Check error details, create a new session.
    """

    def __init__(
        self,
        message: str = "Session has failed",
        session_id: str | None = None,
        original_error: str | None = None,
    ) -> None:
        details = {}
        if session_id is not None:
            details["session_id"] = session_id
        if original_error is not None:
            details["original_error"] = original_error
        super().__init__(message, "SESSION_FAILED", details)


class BriefNotApprovedError(PermanentError):
    """
    Brief has not been approved yet.

    Why not retryable: User must approve the brief first.
    Resolution: Approve the brief before continuing.
    """

    def __init__(
        self,
        message: str = "Brief not approved",
        session_id: str | None = None,
        brief_status: str | None = None,
    ) -> None:
        details = {}
        if session_id is not None:
            details["session_id"] = session_id
        if brief_status is not None:
            details["brief_status"] = brief_status
        super().__init__(message, "BRIEF_NOT_APPROVED", details)


# =============================================================================
# RETRY ERRORS
# =============================================================================

class RetryExhaustedError(PermanentError):
    """
    Maximum retries reached.

    Why permanent: All retry attempts have failed.
    Resolution: Investigate the underlying error, may need manual fix.
    """

    def __init__(
        self,
        message: str = "Maximum retry attempts exceeded",
        attempts: int | None = None,
        last_error: str | None = None,
    ) -> None:
        details = {}
        if attempts is not None:
            details["attempts"] = attempts
        if last_error is not None:
            details["last_error"] = last_error
        super().__init__(message, "RETRY_EXHAUSTED", details)


class CircuitOpenError(TransientError):
    """
    Circuit breaker is open.

    Why transient: Circuit may close after recovery timeout.
    Retry strategy: Wait for circuit to enter half-open state.
    """

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        service_name: str | None = None,
        recovery_time: float | None = None,
    ) -> None:
        details = {}
        if service_name is not None:
            details["service_name"] = service_name
        if recovery_time is not None:
            details["recovery_time"] = recovery_time
        super().__init__(message, "CIRCUIT_OPEN", details)


# =============================================================================
# AGENT ERRORS
# =============================================================================

class AgentError(RalphError):
    """
    Base class for agent-related errors.

    Used for errors during agent execution.
    """

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        task_id: str | None = None,
        code: str = "AGENT_ERROR",
        details: dict[str, Any] | None = None,
        recoverable: bool = False,
    ) -> None:
        details = details or {}
        if agent_name is not None:
            details["agent_name"] = agent_name
        if task_id is not None:
            details["task_id"] = task_id
        super().__init__(message, code, details, recoverable)


class AgentTimeoutError(AgentError, TransientError):
    """Agent execution timed out."""

    def __init__(
        self,
        message: str = "Agent execution timed out",
        agent_name: str | None = None,
        task_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        details = {}
        if timeout_seconds is not None:
            details["timeout_seconds"] = timeout_seconds
        # Initialize TransientError part
        TransientError.__init__(self, message, "AGENT_TIMEOUT", details)
        # Add agent context
        if agent_name is not None:
            self.details["agent_name"] = agent_name
        if task_id is not None:
            self.details["task_id"] = task_id


class AgentExecutionError(AgentError):
    """Agent execution failed with an error."""

    def __init__(
        self,
        message: str = "Agent execution failed",
        agent_name: str | None = None,
        task_id: str | None = None,
        original_error: str | None = None,
    ) -> None:
        details = {}
        if original_error is not None:
            details["original_error"] = original_error
        super().__init__(
            message,
            agent_name=agent_name,
            task_id=task_id,
            code="AGENT_EXECUTION_ERROR",
            details=details,
            recoverable=False,
        )
