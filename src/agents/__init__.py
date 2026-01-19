# Ralph Deep Research - Agents package
"""
AI agents for the Ralph research system.

Agents (all follow Ralph Pattern: Execute → Save → Clear → Next):
- BaseAgent: Abstract base class with common agent behavior
- InitialResearchAgent: Quick context gathering (<60s)
- BriefBuilderAgent: Interactive dialog for research specification
- PlannerAgent: Task decomposition and coverage management
- DataAgent: Structured data collection from APIs (Sonnet model)
- ResearchAgent: Qualitative analysis from web sources (Opus model)
- AggregatorAgent: Synthesize findings and create recommendations (Opus model)
- ReporterAgent: Generate PDF, Excel, PowerPoint, CSV reports (Opus model)
"""

from src.agents.base import BaseAgent
from src.agents.initial_research import InitialResearchAgent
from src.agents.brief_builder import BriefBuilderAgent
from src.agents.planner import PlannerAgent
from src.agents.data import DataAgent
from src.agents.research import ResearchAgent
from src.agents.aggregator import AggregatorAgent
from src.agents.reporter import ReporterAgent

__all__ = [
    "BaseAgent",
    "InitialResearchAgent",
    "BriefBuilderAgent",
    "PlannerAgent",
    "DataAgent",
    "ResearchAgent",
    "AggregatorAgent",
    "ReporterAgent",
]
