"""
Ralph Deep Research - Model Configuration

Defines which Claude model to use for each agent type.
Opus is used for complex reasoning tasks, Sonnet for data extraction.
"""

from typing import Literal

# Model identifiers for Claude models
OPUS_MODEL = "claude-opus-4-20250514"
SONNET_MODEL = "claude-sonnet-4-20250514"

# Agent names as literal type for type safety
AgentName = Literal[
    "initial_research",
    "brief_builder",
    "planner",
    "data",
    "research",
    "aggregator",
    "reporter",
]

# Model selection per agent
# - Opus: Complex reasoning, synthesis, decision-making
# - Sonnet: Data extraction, structured output (more cost-efficient)
AGENT_MODELS: dict[AgentName, str] = {
    "initial_research": OPUS_MODEL,  # Needs quick reasoning for entity extraction
    "brief_builder": OPUS_MODEL,      # Needs conversational reasoning
    "planner": OPUS_MODEL,            # Needs strategic planning and coverage assessment
    "data": SONNET_MODEL,             # Data extraction - simpler, more cost-efficient
    "research": OPUS_MODEL,           # Analysis and synthesis - complex reasoning
    "aggregator": OPUS_MODEL,         # Synthesis across all results - complex reasoning
    "reporter": OPUS_MODEL,           # Report generation - needs good writing
}


def get_model_for_agent(agent_name: str) -> str:
    """
    Get the Claude model ID for a specific agent.

    Args:
        agent_name: Name of the agent (e.g., "data", "research")

    Returns:
        str: Claude model ID

    Raises:
        ValueError: If agent_name is not recognized
    """
    if agent_name not in AGENT_MODELS:
        valid_agents = ", ".join(AGENT_MODELS.keys())
        raise ValueError(f"Unknown agent: {agent_name}. Valid agents: {valid_agents}")

    return AGENT_MODELS[agent_name]
