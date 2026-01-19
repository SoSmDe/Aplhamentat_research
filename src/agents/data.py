"""
Ralph Deep Research - Data Agent (Claude Code Native)

Collects structured data from APIs and web sources.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class DataTableOutput(BaseModel):
    name: str
    description: str
    columns: list[str]
    rows: list[list[Any]]
    source: str
    retrieved_at: str


class DataPointOutput(BaseModel):
    metric: str
    value: Any
    unit: str = ""
    source: str


class DataTaskResultOutput(BaseModel):
    task_id: str
    status: str = Field(description="completed|partial|failed")
    tables: list[DataTableOutput] = Field(default_factory=list)
    data_points: list[DataPointOutput] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)
    notes: str = ""


class DataResultsOutput(BaseModel):
    round_number: int
    task_results: list[DataTaskResultOutput] = Field(default_factory=list)
    summary: str


class DataAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "data"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "tasks" not in context or not context["tasks"]:
            raise InvalidInputError(message="tasks are required", field="tasks")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        tasks = context.get("tasks", [])
        round_number = context.get("round_number", 1)

        tasks_str = "\n".join([f"- {t.get('task_id')}: {t.get('description')}" for t in tasks])

        return f"""## Round {round_number} - Data Tasks
{tasks_str}

## Instructions
Use web_search to find data. Save to state/round_{round_number}/data_results.json"""

    @property
    def output_filename(self) -> str:
        return StateFiles.DATA_RESULTS
