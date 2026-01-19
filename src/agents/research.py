"""
Ralph Deep Research - Research Agent (Claude Code Native)

Conducts qualitative research and analysis.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class InsightOutput(BaseModel):
    finding: str
    evidence: str
    confidence: str = Field(description="high|medium|low")
    sources: list[str] = Field(default_factory=list)


class SourceOutput(BaseModel):
    url: str
    title: str
    relevance: str


class ResearchTaskResultOutput(BaseModel):
    task_id: str
    status: str = Field(description="completed|partial|failed")
    summary: str
    insights: list[InsightOutput] = Field(default_factory=list)
    sources: list[SourceOutput] = Field(default_factory=list)
    unanswered_questions: list[str] = Field(default_factory=list)


class ResearchResultsOutput(BaseModel):
    round_number: int
    task_results: list[ResearchTaskResultOutput] = Field(default_factory=list)
    cross_task_insights: list[str] = Field(default_factory=list)
    overall_summary: str


class ResearchAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "research"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "tasks" not in context or not context["tasks"]:
            raise InvalidInputError(message="tasks are required", field="tasks")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        tasks = context.get("tasks", [])
        round_number = context.get("round_number", 1)

        tasks_str = "\n".join([f"- {t.get('task_id')}: {t.get('description')}" for t in tasks])

        return f"""## Round {round_number} - Research Tasks
{tasks_str}

## Instructions
Use web_search for research. Save to state/round_{round_number}/research_results.json"""

    @property
    def output_filename(self) -> str:
        return StateFiles.RESEARCH_RESULTS
