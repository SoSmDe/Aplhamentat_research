"""
Ralph Deep Research - Planner Agent (Claude Code Native)

Decomposes Brief into executable tasks and manages research rounds.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class DataTaskOutput(BaseModel):
    task_id: str
    description: str
    data_source: str = Field(description="api|web|database")
    specific_metrics: list[str] = Field(default_factory=list)
    priority: str = "medium"


class ResearchTaskOutput(BaseModel):
    task_id: str
    description: str
    search_queries: list[str]
    analysis_focus: str
    priority: str = "medium"


class PlanOutput(BaseModel):
    round_number: int
    data_tasks: list[DataTaskOutput] = Field(default_factory=list)
    research_tasks: list[ResearchTaskOutput] = Field(default_factory=list)
    estimated_coverage: float = Field(ge=0, le=1)
    rationale: str


class CoverageItemOutput(BaseModel):
    scope_item: str
    current_coverage: float = Field(ge=0, le=1)
    missing_aspects: list[str] = Field(default_factory=list)


class CoverageCheckOutput(BaseModel):
    total_coverage: float = Field(ge=0, le=1)
    items: list[CoverageItemOutput] = Field(default_factory=list)
    is_complete: bool
    next_round_needed: bool


class PlannerAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "planner"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "brief" not in context:
            raise InvalidInputError(message="brief is required", field="brief")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        brief = context.get("brief", {})
        round_number = context.get("round_number", 1)
        mode = context.get("mode", "plan")

        return f"""## Brief
{brief}

## Round: {round_number}
## Mode: {mode}

## Instructions
Decompose brief into data tasks (d1, d2...) and research tasks (r1, r2...).
Save plan to state/plan.json. Target coverage >= 80%."""

    @property
    def output_filename(self) -> str:
        return StateFiles.PLAN
