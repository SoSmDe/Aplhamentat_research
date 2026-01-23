"""
Metrics Aggregation and Summary Functions.

Provides tools for analyzing and summarizing resource usage
across research sessions.

Usage:
    from integrations.core.metrics_aggregator import (
        load_metrics,
        generate_summary,
        format_cost_report
    )

    # Load and analyze metrics
    metrics = load_metrics("/path/to/state")
    summary = generate_summary(metrics)
    report = format_cost_report(metrics)
    print(report)
"""

import json
import os
from typing import Dict, Any, List, Optional
from collections import defaultdict


def load_metrics(state_dir: str) -> Dict[str, Any]:
    """Load metrics from state directory.

    Args:
        state_dir: Path to state directory

    Returns:
        Metrics dictionary or empty dict if not found
    """
    metrics_path = os.path.join(state_dir, "metrics.json")
    if not os.path.exists(metrics_path):
        return {}
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def aggregate_by_module(metrics: Dict[str, Any]) -> Dict[str, Dict]:
    """Aggregate API metrics by integration module.

    Args:
        metrics: Loaded metrics dictionary

    Returns:
        Dict mapping module name to stats
    """
    by_module: Dict[str, Dict] = defaultdict(lambda: {
        "calls": 0,
        "duration_ms": 0,
        "errors": 0,
        "avg_duration_ms": 0,
    })

    for call in metrics.get("api_calls", []):
        module = call.get("module", "unknown")
        by_module[module]["calls"] += 1
        by_module[module]["duration_ms"] += call.get("duration_ms", 0)
        if call.get("error"):
            by_module[module]["errors"] += 1

    # Calculate averages
    for module, stats in by_module.items():
        if stats["calls"] > 0:
            stats["avg_duration_ms"] = round(
                stats["duration_ms"] / stats["calls"], 2
            )

    return dict(by_module)


def aggregate_by_phase(metrics: Dict[str, Any]) -> Dict[str, Dict]:
    """Aggregate LLM metrics by research phase.

    Args:
        metrics: Loaded metrics dictionary

    Returns:
        Dict mapping phase name to stats
    """
    by_phase: Dict[str, Dict] = defaultdict(lambda: {
        "llm_calls": 0,
        "tokens": 0,
        "cost_usd": 0,
        "api_calls": 0,
    })

    for call in metrics.get("llm_calls", []):
        phase = call.get("phase") or "unknown"
        by_phase[phase]["llm_calls"] += 1
        by_phase[phase]["tokens"] += call.get("total_tokens", 0)
        by_phase[phase]["cost_usd"] += call.get("cost_usd", 0)

    return dict(by_phase)


def aggregate_by_agent(metrics: Dict[str, Any]) -> Dict[str, Dict]:
    """Aggregate LLM metrics by agent.

    Args:
        metrics: Loaded metrics dictionary

    Returns:
        Dict mapping agent name to stats
    """
    by_agent: Dict[str, Dict] = defaultdict(lambda: {
        "calls": 0,
        "tokens": 0,
        "cost_usd": 0,
        "avg_tokens": 0,
    })

    for call in metrics.get("llm_calls", []):
        agent = call.get("agent_name") or "unknown"
        by_agent[agent]["calls"] += 1
        by_agent[agent]["tokens"] += call.get("total_tokens", 0)
        by_agent[agent]["cost_usd"] += call.get("cost_usd", 0)

    # Calculate averages
    for agent, stats in by_agent.items():
        if stats["calls"] > 0:
            stats["avg_tokens"] = round(stats["tokens"] / stats["calls"])

    return dict(by_agent)


def get_top_expensive_calls(
    metrics: Dict[str, Any],
    limit: int = 5
) -> List[Dict]:
    """Get top N most expensive LLM calls.

    Args:
        metrics: Loaded metrics dictionary
        limit: Maximum number of calls to return

    Returns:
        List of call dictionaries sorted by cost
    """
    llm_calls = metrics.get("llm_calls", [])
    sorted_calls = sorted(
        llm_calls,
        key=lambda x: x.get("cost_usd", 0),
        reverse=True
    )
    return sorted_calls[:limit]


def get_slowest_api_calls(
    metrics: Dict[str, Any],
    limit: int = 5
) -> List[Dict]:
    """Get top N slowest API calls.

    Args:
        metrics: Loaded metrics dictionary
        limit: Maximum number of calls to return

    Returns:
        List of call dictionaries sorted by duration
    """
    api_calls = metrics.get("api_calls", [])
    sorted_calls = sorted(
        api_calls,
        key=lambda x: x.get("duration_ms", 0),
        reverse=True
    )
    return sorted_calls[:limit]


def get_failed_api_calls(metrics: Dict[str, Any]) -> List[Dict]:
    """Get all failed API calls.

    Args:
        metrics: Loaded metrics dictionary

    Returns:
        List of failed call dictionaries
    """
    return [
        call for call in metrics.get("api_calls", [])
        if call.get("error")
    ]


def generate_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comprehensive metrics summary.

    Args:
        metrics: Loaded metrics dictionary

    Returns:
        Summary dictionary with all aggregations
    """
    if not metrics:
        return {}

    return {
        "overview": {
            "session_id": metrics.get("session_id"),
            "start_time": metrics.get("start_time"),
            "end_time": metrics.get("end_time"),
            "total_duration_ms": metrics.get("total_duration_ms", 0),
            "total_api_calls": metrics.get("api_calls_count", 0),
            "total_api_errors": metrics.get("api_errors_count", 0),
            "total_api_duration_ms": metrics.get("api_total_duration_ms", 0),
            "total_llm_calls": metrics.get("llm_calls_count", 0),
            "total_llm_tokens": metrics.get("llm_total_tokens", 0),
            "llm_cost_usd": metrics.get("llm_total_cost_usd", 0),
            "api_cost_usd": metrics.get("api_cost_usd", 0),
            "total_cost_usd": metrics.get("total_cost_usd", 0),
        },
        "by_module": aggregate_by_module(metrics),
        "by_phase": aggregate_by_phase(metrics),
        "by_agent": aggregate_by_agent(metrics),
        "top_expensive_calls": get_top_expensive_calls(metrics),
        "slowest_api_calls": get_slowest_api_calls(metrics),
        "failed_api_calls": get_failed_api_calls(metrics),
    }


def format_cost_report(metrics: Dict[str, Any]) -> str:
    """Generate human-readable cost report.

    Args:
        metrics: Loaded metrics dictionary

    Returns:
        Formatted report string
    """
    if not metrics:
        return "No metrics available."

    summary = generate_summary(metrics)
    overview = summary.get("overview", {})

    lines = [
        "=" * 60,
        "RALPH RESOURCE USAGE REPORT",
        "=" * 60,
        "",
        f"Session: {overview.get('session_id', 'unknown')}",
        f"Start:   {overview.get('start_time', 'N/A')}",
        f"End:     {overview.get('end_time', 'N/A')}",
        f"Duration: {overview.get('total_duration_ms', 0) / 1000:.1f}s",
        "",
        "-" * 40,
        "API CALLS",
        "-" * 40,
        f"  Total Calls:    {overview.get('total_api_calls', 0)}",
        f"  Errors:         {overview.get('total_api_errors', 0)}",
        f"  Total Time:     {overview.get('total_api_duration_ms', 0) / 1000:.1f}s",
        f"  API Cost:       ${overview.get('api_cost_usd', 0):.4f}",
        "",
    ]

    # By module breakdown
    by_module = summary.get("by_module", {})
    if by_module:
        lines.append("  By Module:")
        for module, stats in sorted(by_module.items(), key=lambda x: -x[1]["calls"]):
            error_str = f" ({stats['errors']} errors)" if stats['errors'] > 0 else ""
            lines.append(
                f"    {module}: {stats['calls']} calls, "
                f"{stats['duration_ms']:.0f}ms{error_str}"
            )
        lines.append("")

    lines.extend([
        "-" * 40,
        "LLM USAGE",
        "-" * 40,
        f"  Total Calls:    {overview.get('total_llm_calls', 0)}",
        f"  Total Tokens:   {overview.get('total_llm_tokens', 0):,}",
        f"  LLM Cost:       ${overview.get('llm_cost_usd', 0):.4f}",
        "",
    ])

    # By agent breakdown
    by_agent = summary.get("by_agent", {})
    if by_agent:
        lines.append("  By Agent:")
        for agent, stats in sorted(by_agent.items(), key=lambda x: -x[1]["tokens"]):
            lines.append(
                f"    {agent}: {stats['tokens']:,} tokens, "
                f"${stats['cost_usd']:.4f}"
            )
        lines.append("")

    # By phase breakdown
    by_phase = summary.get("by_phase", {})
    if by_phase:
        lines.append("  By Phase:")
        for phase, stats in sorted(by_phase.items(), key=lambda x: -x[1]["tokens"]):
            lines.append(
                f"    {phase}: {stats['tokens']:,} tokens, "
                f"${stats['cost_usd']:.4f}"
            )
        lines.append("")

    lines.extend([
        "-" * 40,
        "TOTAL COST",
        "-" * 40,
        f"  ${overview.get('total_cost_usd', 0):.4f}",
        "",
        "=" * 60,
    ])

    # Failed calls warning
    failed = summary.get("failed_api_calls", [])
    if failed:
        lines.extend([
            "",
            "WARNING: Failed API Calls",
            "-" * 40,
        ])
        for call in failed[:5]:  # Show first 5
            lines.append(f"  {call.get('module')}: {call.get('error', 'Unknown error')}")

    return "\n".join(lines)


def compare_sessions(
    metrics_list: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Compare metrics across multiple sessions.

    Args:
        metrics_list: List of metrics dictionaries

    Returns:
        Comparison summary
    """
    if not metrics_list:
        return {}

    totals = {
        "sessions": len(metrics_list),
        "total_api_calls": 0,
        "total_llm_tokens": 0,
        "total_cost_usd": 0,
        "avg_cost_per_session": 0,
    }

    for metrics in metrics_list:
        totals["total_api_calls"] += metrics.get("api_calls_count", 0)
        totals["total_llm_tokens"] += metrics.get("llm_total_tokens", 0)
        totals["total_cost_usd"] += metrics.get("total_cost_usd", 0)

    totals["avg_cost_per_session"] = round(
        totals["total_cost_usd"] / len(metrics_list), 4
    )

    return totals
