"""
LLM Token Estimation for Claude Code.

Since Claude Code doesn't expose token counts directly,
we estimate based on:
1. Character count (~4 chars per token for English)
2. Known prompt file sizes
3. Response length estimation

For accurate tracking, integrate with Anthropic API usage logs
or use Claude API directly with usage metadata.

Usage:
    from integrations.core.llm_estimator import (
        estimate_tokens,
        estimate_agent_call,
        record_agent_call
    )

    # Estimate tokens from text
    tokens = estimate_tokens("Hello world", content_type="english")

    # Estimate and record agent call
    record_agent_call(
        agent_name="data_agent",
        input_files=["prompts/data.md", "state/session.json"],
        output_file="results/data_1.json"
    )
"""

import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .tracker import tracker, LLMCallMetric
from .pricing import calculate_llm_cost


# Average characters per token by content type
CHARS_PER_TOKEN = {
    "english": 4.0,
    "russian": 3.0,      # Cyrillic is denser
    "code": 3.5,
    "json": 3.0,
    "markdown": 3.8,
    "mixed": 3.7,
}

# Base token counts for agent prompts (pre-computed estimates)
AGENT_BASE_TOKENS = {
    "initial_research": 2500,
    "brief_builder": 3000,
    "planner": 4500,
    "overview": 5000,
    "data": 4000,
    "research": 4500,
    "literature": 3500,
    "fact_check": 3000,
    "questions_planner": 3500,
    "aggregator": 5500,
    "chart_analyzer": 4000,
    "story_liner": 4500,
    "visual_designer": 4000,
    "reporter": 6000,
    "editor": 5000,
}

# Default model for estimation
DEFAULT_MODEL = "claude-3-5-sonnet"


def estimate_tokens(text: str, content_type: str = "mixed") -> int:
    """Estimate token count from text.

    Args:
        text: Text to estimate tokens for
        content_type: Type of content (english, russian, code, json, markdown, mixed)

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    chars_per = CHARS_PER_TOKEN.get(content_type, 3.7)
    return max(1, int(len(text) / chars_per))


def estimate_file_tokens(file_path: str) -> int:
    """Estimate token count from file size.

    Args:
        file_path: Path to file

    Returns:
        Estimated token count (0 if file doesn't exist)
    """
    if not os.path.exists(file_path):
        return 0

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Detect content type from extension
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".json"]:
            content_type = "json"
        elif ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
            content_type = "code"
        elif ext in [".md", ".markdown"]:
            content_type = "markdown"
        else:
            content_type = "mixed"

        return estimate_tokens(content, content_type)
    except Exception:
        # Fallback to size-based estimation
        size = os.path.getsize(file_path)
        return max(1, int(size / 4))


def get_agent_base_tokens(agent_name: str) -> int:
    """Get base token count for an agent's prompt.

    Args:
        agent_name: Agent name (e.g., data, research, aggregator)

    Returns:
        Base token count for the agent's prompt
    """
    # Normalize agent name
    name = agent_name.lower().replace("_agent", "").replace("-", "_")
    return AGENT_BASE_TOKENS.get(name, 3000)


def estimate_agent_call(
    agent_name: str,
    input_files: List[str] = None,
    output_file: str = None,
    model: str = None
) -> Dict[str, Any]:
    """Estimate tokens and cost for an agent call.

    Args:
        agent_name: Name of the agent
        input_files: List of input file paths (prompts, context)
        output_file: Output file path (agent result)
        model: Model name for pricing

    Returns:
        Dictionary with token estimates and cost
    """
    model = model or DEFAULT_MODEL
    input_files = input_files or []

    # Calculate input tokens
    input_tokens = get_agent_base_tokens(agent_name)
    for f in input_files:
        input_tokens += estimate_file_tokens(f)

    # Calculate output tokens
    output_tokens = 0
    if output_file:
        output_tokens = estimate_file_tokens(output_file)

    # Calculate cost
    cost = calculate_llm_cost(model, input_tokens, output_tokens)

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost,
        "estimation_method": "file_size",
    }


def record_agent_call(
    agent_name: str,
    input_files: List[str] = None,
    output_file: str = None,
    model: str = None,
    phase: str = None,
    task_type: str = None,
    duration_ms: float = None,
    start_time: str = None,
    end_time: str = None
) -> LLMCallMetric:
    """Estimate and record an agent call to the tracker.

    Args:
        agent_name: Name of the agent
        input_files: List of input file paths
        output_file: Output file path
        model: Model name
        phase: Pipeline phase
        task_type: Task type (e.g., d1, r2)
        duration_ms: Call duration in milliseconds
        start_time: ISO timestamp of call start
        end_time: ISO timestamp of call end

    Returns:
        LLMCallMetric that was recorded
    """
    model = model or DEFAULT_MODEL
    estimate = estimate_agent_call(agent_name, input_files, output_file, model)

    now = datetime.utcnow().isoformat() + "Z"
    metric = LLMCallMetric(
        model=model,
        input_tokens=estimate["input_tokens"],
        output_tokens=estimate["output_tokens"],
        total_tokens=estimate["total_tokens"],
        cost_usd=estimate["cost_usd"],
        start_time=start_time or now,
        end_time=end_time or now,
        duration_ms=duration_ms or 0,
        agent_name=agent_name,
        phase=phase,
        task_type=task_type,
    )

    tracker.record_llm_call(metric)
    return metric


def estimate_conversation_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimate tokens for a conversation history.

    Args:
        messages: List of message dicts with 'role' and 'content' keys

    Returns:
        Estimated total token count
    """
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        # Add overhead for message structure (~4 tokens per message)
        total += estimate_tokens(content, "mixed") + 4
    return total


def estimate_from_session(
    session_file: str,
    result_files: List[str] = None,
    model: str = None
) -> Dict[str, Any]:
    """Estimate total LLM usage for a research session.

    Args:
        session_file: Path to session.json
        result_files: List of result file paths
        model: Model name

    Returns:
        Dictionary with total token estimates and costs
    """
    model = model or DEFAULT_MODEL
    result_files = result_files or []

    # Estimate input from session and state files
    input_tokens = 0
    session_dir = os.path.dirname(session_file)

    state_files = [
        "session.json",
        "brief.json",
        "plan.json",
        "aggregation.json",
        "story.json",
    ]
    for f in state_files:
        path = os.path.join(session_dir, f)
        input_tokens += estimate_file_tokens(path)

    # Add prompt estimates (rough: 5 agents * 4000 tokens average)
    input_tokens += 5 * 4000

    # Estimate output from result files
    output_tokens = 0
    for f in result_files:
        output_tokens += estimate_file_tokens(f)

    # Calculate cost
    cost = calculate_llm_cost(model, input_tokens, output_tokens)

    return {
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_usd": cost,
        "estimation_method": "session_files",
    }
