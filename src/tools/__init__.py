# Ralph Deep Research - Tools package
"""
Shared tools and utilities for agents.

Components (Claude Code native workflow):
- errors: Error classes for the error hierarchy (TransientError, PermanentError, SystemError)
- logging: Structured logging with sensitive data filtering
- db_client: Read-only database query execution

Removed (Claude Code handles natively):
- llm.py: Claude Code IS Claude - no API wrapper needed
- web_search.py: Claude Code has built-in web_search tool
- api_client.py: Claude Code makes HTTP requests directly
- retry.py: Claude handles retries internally
- file_generator.py: Claude Code generates files directly
"""

from src.tools.errors import (
    # Base
    RalphError,
    # Transient (retryable)
    TransientError,
    APITimeoutError,
    RateLimitError,
    NetworkError,
    ServiceUnavailableError,
    # Permanent (not retryable)
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

from src.tools.logging import (
    get_logger,
    configure_logging,
    bind_context,
    LogContext,
)

from src.tools.db_client import (
    ColumnInfo,
    TableSchema,
    QueryResult,
    DatabaseQueryClient,
    MockDatabaseClient,
    get_db_client,
    create_mock_db_client,
)


__all__ = [
    # Errors
    "RalphError",
    "TransientError",
    "APITimeoutError",
    "RateLimitError",
    "NetworkError",
    "ServiceUnavailableError",
    "PermanentError",
    "InvalidInputError",
    "AuthenticationError",
    "QuotaExceededError",
    "DataNotFoundError",
    "SystemError",
    "DatabaseError",
    "StorageFullError",
    "ConfigurationError",
    "SessionNotFoundError",
    "SessionFailedError",
    "BriefNotApprovedError",
    "RetryExhaustedError",
    "CircuitOpenError",
    "AgentError",
    "AgentTimeoutError",
    "AgentExecutionError",
    # Logging
    "get_logger",
    "configure_logging",
    "bind_context",
    "LogContext",
    # Database Client
    "ColumnInfo",
    "TableSchema",
    "QueryResult",
    "DatabaseQueryClient",
    "MockDatabaseClient",
    "get_db_client",
    "create_mock_db_client",
]
