# Ralph Deep Research - Agents package (Claude Code Native)
"""
AI agents for the Ralph research system.

Claude Code Native Workflow:
- Agents are prompt-driven (prompts in src/prompts/*.md)
- State is saved to JSON files in state/ directory
- Claude Code executes agents directly using built-in tools
- No LLM wrapper needed - Claude Code IS Claude

Agents (all follow Ralph Pattern: Execute → Save → Clear → Next):
- BaseAgent: Abstract base class with state management
- InitialResearchAgent: Quick context gathering (<60s)
- BriefBuilderAgent: Interactive dialog for research specification
- PlannerAgent: Task decomposition and coverage management
- DataAgent: Structured data collection (Sonnet model)
- ResearchAgent: Qualitative analysis (Opus model)
- AggregatorAgent: Synthesize findings and create recommendations (Opus model)
- ReporterAgent: Generate PDF, Excel, PowerPoint reports (Opus model)

State Management:
- StateManager: JSON-based state persistence
- StateFiles: Constants for state file names
"""

from src.agents.base import (
    BaseAgent,
    StateManager,
    StateFiles,
    get_state_manager,
    load_agent_prompt,
)
from src.agents.initial_research import InitialResearchAgent
from src.agents.brief_builder import BriefBuilderAgent
from src.agents.planner import PlannerAgent
from src.agents.data import DataAgent
from src.agents.research import ResearchAgent
from src.agents.aggregator import AggregatorAgent
from src.agents.reporter import ReporterAgent

__all__ = [
    # Base
    "BaseAgent",
    "StateManager",
    "StateFiles",
    "get_state_manager",
    "load_agent_prompt",
    # Agents
    "InitialResearchAgent",
    "BriefBuilderAgent",
    "PlannerAgent",
    "DataAgent",
    "ResearchAgent",
    "AggregatorAgent",
    "ReporterAgent",
]
