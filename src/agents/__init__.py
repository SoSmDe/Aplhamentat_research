# Ralph Deep Research - Agents package
"""
AI agents for the Ralph research system.

Agents (all follow Ralph Pattern: Execute → Save → Clear → Next):
- BaseAgent: Abstract base class with common agent behavior
- InitialResearchAgent: Quick context gathering (<60s)
- BriefBuilderAgent: Interactive dialog for research specification
- PlannerAgent: Task decomposition and coverage management (TODO)
- DataAgent: Structured data collection from APIs (Sonnet model) (TODO)
- ResearchAgent: Qualitative analysis from web sources (Opus model) (TODO)
- AggregatorAgent: Synthesize findings and create recommendations (TODO)
- ReporterAgent: Generate PDF, Excel, PowerPoint reports (TODO)
"""

from src.agents.base import BaseAgent
from src.agents.initial_research import InitialResearchAgent
from src.agents.brief_builder import BriefBuilderAgent

__all__ = [
    "BaseAgent",
    "InitialResearchAgent",
    "BriefBuilderAgent",
]
