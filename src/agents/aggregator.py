"""
Ralph Deep Research - Aggregator Agent (Claude Code Native)

Synthesizes all research findings into cohesive analysis.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class KeyFindingOutput(BaseModel):
    finding: str
    importance: str = Field(description="high|medium|low")
    supporting_evidence: list[str]
    confidence: str = Field(description="high|medium|low")


class RecommendationOutput(BaseModel):
    recommendation: str
    rationale: str
    supporting_findings: list[str]
    risk_factors: list[str] = Field(default_factory=list)
    priority: str = Field(description="high|medium|low")


class SectionOutput(BaseModel):
    title: str
    content: str
    findings: list[str] = Field(default_factory=list)


class AggregationOutput(BaseModel):
    executive_summary: str
    key_findings: list[KeyFindingOutput]
    recommendations: list[RecommendationOutput] = Field(default_factory=list)
    sections: list[SectionOutput]
    methodology_notes: str = ""
    sources_bibliography: list[str] = Field(default_factory=list)


class AggregatorAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "aggregator"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "round_results" not in context or not context["round_results"]:
            raise InvalidInputError(message="round_results are required", field="round_results")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        brief = context.get("brief", {})
        round_results = context.get("round_results", [])

        return f"""## Brief
{brief}

## Round Results
{round_results}

## Instructions
Synthesize all findings. Save to state/aggregation.json"""

    @property
    def output_filename(self) -> str:
        return StateFiles.AGGREGATION
