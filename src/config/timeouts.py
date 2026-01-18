"""
Ralph Deep Research - Timeout and Limit Configuration

Performance targets and scalability limits from specs/ARCHITECTURE.md.
These values are used to enforce timeouts and prevent runaway operations.
"""

# =============================================================================
# Agent Timeout Configuration (in seconds)
# =============================================================================
# Based on specs/ARCHITECTURE.md performance targets
# Format: (target, max_timeout)
#
# Target: Expected completion time under normal conditions
# Max Timeout: Hard limit before operation is cancelled

AGENT_TIMEOUTS: dict[str, int] = {
    # Agent operation timeouts (max values)
    "initial_research": 90,     # Target: 60s, Max: 90s
    "brief_builder": 10,        # Target: 5s, Max: 10s
    "planner": 20,              # Target: 10s, Max: 20s
    "data_task": 45,            # Target: 30s, Max: 45s
    "research_task": 90,        # Target: 60s, Max: 90s
    "round_timeout": 300,       # Target: 120s, Max: 300s (parallel execution)
    "aggregation": 120,         # Target: 60s, Max: 120s
    "reporting": 120,           # Target: 60s, Max: 120s
}

# Performance targets (informational, for logging/monitoring)
AGENT_TARGETS: dict[str, int] = {
    "initial_research": 60,
    "brief_builder": 5,
    "planner": 10,
    "data_task": 30,
    "research_task": 60,
    "round_timeout": 120,
    "aggregation": 60,
    "reporting": 60,
}


# =============================================================================
# Scalability Limits (MVP)
# =============================================================================
# Based on specs/ARCHITECTURE.md scalability requirements

SCALABILITY_LIMITS: dict[str, int] = {
    # Session limits
    "max_concurrent_sessions": 10,
    "max_tasks_per_round": 10,
    "max_rounds_per_session": 10,
    "max_tasks_per_session": 100,

    # Storage limits
    "max_storage_per_session_mb": 50,
    "max_report_size_mb": 20,

    # Coverage thresholds
    "min_coverage_percent": 80,  # Minimum coverage to complete research
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_timeout(operation: str) -> int:
    """
    Get timeout value for an operation.

    Args:
        operation: Name of the operation (e.g., "data_task", "research_task")

    Returns:
        int: Timeout in seconds

    Raises:
        ValueError: If operation is not recognized
    """
    if operation not in AGENT_TIMEOUTS:
        valid_ops = ", ".join(AGENT_TIMEOUTS.keys())
        raise ValueError(f"Unknown operation: {operation}. Valid: {valid_ops}")

    return AGENT_TIMEOUTS[operation]


def get_limit(limit_name: str) -> int:
    """
    Get scalability limit value.

    Args:
        limit_name: Name of the limit

    Returns:
        int: Limit value

    Raises:
        ValueError: If limit_name is not recognized
    """
    if limit_name not in SCALABILITY_LIMITS:
        valid_limits = ", ".join(SCALABILITY_LIMITS.keys())
        raise ValueError(f"Unknown limit: {limit_name}. Valid: {valid_limits}")

    return SCALABILITY_LIMITS[limit_name]
