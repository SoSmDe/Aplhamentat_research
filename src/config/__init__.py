# Ralph Deep Research - Config package
"""
Configuration and settings for the Ralph research system.

Components:
- Settings: Environment variable loading and validation
- AGENT_MODELS: Model selection per agent (Opus for reasoning, Sonnet for data)
- AGENT_TIMEOUTS: Timeout configuration per operation
- SCALABILITY_LIMITS: MVP limits (sessions, tasks, storage)

Usage:
    from src.config import get_settings, get_model_for_agent, get_timeout

    settings = get_settings()
    model = get_model_for_agent("research")  # Returns Opus model ID
    timeout = get_timeout("data_task")  # Returns 45 seconds
"""

from src.config.models import (
    AGENT_MODELS,
    OPUS_MODEL,
    SONNET_MODEL,
    AgentName,
    get_model_for_agent,
)
from src.config.settings import Settings, get_settings
from src.config.timeouts import (
    AGENT_TIMEOUTS,
    AGENT_TARGETS,
    SCALABILITY_LIMITS,
    get_limit,
    get_timeout,
)

__all__ = [
    # Settings
    "Settings",
    "get_settings",
    # Models
    "AGENT_MODELS",
    "OPUS_MODEL",
    "SONNET_MODEL",
    "AgentName",
    "get_model_for_agent",
    # Timeouts
    "AGENT_TIMEOUTS",
    "AGENT_TARGETS",
    "SCALABILITY_LIMITS",
    "get_timeout",
    "get_limit",
]
