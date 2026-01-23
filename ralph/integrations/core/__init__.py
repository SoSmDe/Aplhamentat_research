"""
Core Resource Tracking Module for Ralph Integrations.

Provides unified tracking of API calls, LLM tokens, and costs
across all Ralph operations.

Usage:
    # Auto-enable tracking on import
    from integrations.core import tracker

    # Or import specific components
    from integrations.core.tracker import tracker, APICallMetric, LLMCallMetric
    from integrations.core.pricing import calculate_llm_cost, calculate_api_cost
    from integrations.core.http_wrapper import patch_requests
    from integrations.core.llm_estimator import record_agent_call
    from integrations.core.metrics_aggregator import format_cost_report

CLI:
    # With tracking enabled via environment variables:
    export RALPH_SESSION_ID="research_123"
    export RALPH_STATE_DIR="./research_123/state"
    python cli/fetch.py coingecko get_price '["bitcoin"]'

    # Check results:
    cat ./research_123/state/metrics.json

Tracked Metrics:
    - API calls: endpoint, method, module, duration_ms, status_code, error
    - LLM calls: model, input_tokens, output_tokens, cost_usd, agent_name, phase
    - Costs: llm_cost_usd, api_cost_usd, total_cost_usd
    - Context: session_id, phase, agent_name, task_type
"""

from .tracker import (
    tracker,
    ResourceTracker,
    APICallMetric,
    LLMCallMetric,
    SessionMetrics,
)

from .pricing import (
    calculate_llm_cost,
    calculate_api_cost,
    get_module_tier,
    get_llm_pricing,
    LLM_PRICING,
    API_PRICING,
)

from .http_wrapper import (
    patch_requests,
    unpatch_requests,
    is_patched,
    TrackedSession,
)

from .llm_estimator import (
    estimate_tokens,
    estimate_file_tokens,
    estimate_agent_call,
    record_agent_call,
    get_agent_base_tokens,
)

from .metrics_aggregator import (
    load_metrics,
    generate_summary,
    format_cost_report,
    aggregate_by_module,
    aggregate_by_phase,
    aggregate_by_agent,
)


__all__ = [
    # Tracker
    "tracker",
    "ResourceTracker",
    "APICallMetric",
    "LLMCallMetric",
    "SessionMetrics",

    # Pricing
    "calculate_llm_cost",
    "calculate_api_cost",
    "get_module_tier",
    "get_llm_pricing",
    "LLM_PRICING",
    "API_PRICING",

    # HTTP Wrapper
    "patch_requests",
    "unpatch_requests",
    "is_patched",
    "TrackedSession",

    # LLM Estimator
    "estimate_tokens",
    "estimate_file_tokens",
    "estimate_agent_call",
    "record_agent_call",
    "get_agent_base_tokens",

    # Aggregator
    "load_metrics",
    "generate_summary",
    "format_cost_report",
    "aggregate_by_module",
    "aggregate_by_phase",
    "aggregate_by_agent",
]
