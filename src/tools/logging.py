"""
Ralph Deep Research - Logging Configuration

Structured logging using structlog for the Ralph research system.

Why structlog:
- JSON output for log aggregation and parsing
- Context binding for correlation (session_id, agent, task_id)
- Consistent formatting across all components
- Easy filtering and searching in log management tools

Usage:
    from src.tools.logging import get_logger

    logger = get_logger(__name__)
    logger.info("Processing task", task_id="d1", session_id="sess_123")

Security:
- Never log API keys, passwords, or sensitive data
- Truncate large payloads to prevent log bloat
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import Processor

# =============================================================================
# SENSITIVE DATA FILTERING
# =============================================================================

# Keys that should never be logged
SENSITIVE_KEYS = frozenset({
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
})


def filter_sensitive_data(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Filter sensitive data from log entries.

    Why: Prevent accidental exposure of API keys and credentials.
    Replaces sensitive values with "[REDACTED]".
    """
    for key in list(event_dict.keys()):
        key_lower = key.lower()
        # Check if key contains any sensitive term
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            event_dict[key] = "[REDACTED]"
        # Also check nested dicts
        elif isinstance(event_dict[key], dict):
            event_dict[key] = _filter_dict(event_dict[key])
    return event_dict


def _filter_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively filter sensitive data from nested dictionaries."""
    result = {}
    for key, value in d.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_KEYS):
            result[key] = "[REDACTED]"
        elif isinstance(value, dict):
            result[key] = _filter_dict(value)
        else:
            result[key] = value
    return result


# =============================================================================
# TRUNCATION
# =============================================================================

MAX_STRING_LENGTH = 1000
MAX_LIST_ITEMS = 10


def truncate_large_values(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """
    Truncate large values to prevent log bloat.

    Why: Large payloads can overwhelm log storage and slow parsing.
    """
    for key, value in event_dict.items():
        if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
            event_dict[key] = value[:MAX_STRING_LENGTH] + f"... [truncated, total: {len(value)}]"
        elif isinstance(value, list) and len(value) > MAX_LIST_ITEMS:
            event_dict[key] = value[:MAX_LIST_ITEMS] + [f"... [{len(value) - MAX_LIST_ITEMS} more items]"]
    return event_dict


# =============================================================================
# LOGGER CONFIGURATION
# =============================================================================

def configure_logging(
    log_level: str = "INFO",
    json_output: bool = True,
) -> None:
    """
    Configure structlog for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: If True, output JSON logs; if False, output pretty console logs

    Why this configuration:
    - JSON for production: Easy to parse, aggregate, and search
    - Pretty for development: Human-readable for debugging
    """
    # Standard library logging configuration
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )

    # Common processors for all environments
    shared_processors: list[Processor] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        filter_sensitive_data,
        truncate_large_values,
    ]

    if json_output:
        # JSON output for production
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty output for development
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog BoundLogger

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing started", session_id="sess_123")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> structlog.stdlib.BoundLogger:
    """
    Bind context to all subsequent log entries.

    Useful for adding correlation IDs across a request.

    Args:
        **kwargs: Context to bind (session_id, agent, task_id, round)

    Returns:
        Logger with bound context

    Usage:
        logger = bind_context(session_id="sess_123", round=1)
        logger.info("Round started")  # Includes session_id and round
    """
    return structlog.get_logger().bind(**kwargs)


# =============================================================================
# CONTEXT MANAGERS
# =============================================================================

class LogContext:
    """
    Context manager for temporarily binding log context.

    Usage:
        with LogContext(session_id="sess_123", agent="data"):
            logger.info("Processing")  # Includes session_id and agent
        # Context is cleared after the block
    """

    def __init__(self, **kwargs: Any) -> None:
        self.context = kwargs
        self._token: Any = None

    def __enter__(self) -> structlog.stdlib.BoundLogger:
        self._token = structlog.contextvars.bind_contextvars(**self.context)
        return structlog.get_logger()

    def __exit__(self, *args: Any) -> None:
        structlog.contextvars.unbind_contextvars(*self.context.keys())


# =============================================================================
# INITIALIZATION
# =============================================================================

# Default initialization for module import
# Will be reconfigured by main.py with actual settings
_configured = False


def ensure_configured(log_level: str = "INFO", json_output: bool = True) -> None:
    """Ensure logging is configured (idempotent)."""
    global _configured
    if not _configured:
        configure_logging(log_level, json_output)
        _configured = True


# Configure with defaults on import (can be reconfigured later)
ensure_configured()
