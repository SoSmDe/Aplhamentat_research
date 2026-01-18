# Ralph Deep Research - Tools package
"""
Shared tools and utilities for agents.

Components:
- errors: Error classes for the error hierarchy (TransientError, PermanentError, SystemError)
- logging: Structured logging with sensitive data filtering
- retry: Retry logic with exponential backoff and circuit breaker
- llm: Claude API wrapper with retry logic and token tracking
- web_search: Web search integration (Serper API or mock)
- api_client: External data source clients (financial APIs)
- file_generator: PDF, Excel, PowerPoint, CSV generation
- db_client: Read-only database query execution
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

from src.tools.retry import (
    RetryConfig,
    RETRY_CONFIGS,
    RetryHandler,
    with_retry,
    CircuitState,
    CircuitBreaker,
    ResilientExecutor,
)

from src.tools.llm import (
    LLMClient,
    TokenUsage,
    CumulativeUsage,
    get_llm_client,
    create_llm_client,
)

from src.tools.web_search import (
    SearchResult,
    WebSearchClient,
    MockSearchClient,
    SerperClient,
    get_search_client,
    create_search_client,
)

from src.tools.api_client import (
    APIResponse,
    APIClient,
    FinancialAPIClient,
    CustomAPIClient,
    MockAPIClient,
    get_financial_client,
    create_api_client,
)

from src.tools.file_generator import (
    FileGenerator,
    get_file_generator,
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
    # Retry
    "RetryConfig",
    "RETRY_CONFIGS",
    "RetryHandler",
    "with_retry",
    "CircuitState",
    "CircuitBreaker",
    "ResilientExecutor",
    # LLM
    "LLMClient",
    "TokenUsage",
    "CumulativeUsage",
    "get_llm_client",
    "create_llm_client",
    # Web Search
    "SearchResult",
    "WebSearchClient",
    "MockSearchClient",
    "SerperClient",
    "get_search_client",
    "create_search_client",
    # API Client
    "APIResponse",
    "APIClient",
    "FinancialAPIClient",
    "CustomAPIClient",
    "MockAPIClient",
    "get_financial_client",
    "create_api_client",
    # File Generator
    "FileGenerator",
    "get_file_generator",
    # Database Client
    "ColumnInfo",
    "TableSchema",
    "QueryResult",
    "DatabaseQueryClient",
    "MockDatabaseClient",
    "get_db_client",
    "create_mock_db_client",
]
