"""
Ralph Deep Research - Reporter Agent (Claude Code Native)

Generates final reports in requested formats.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class ReportFileOutput(BaseModel):
    format: str = Field(description="pdf|excel|pptx")
    filename: str
    path: str


class PDFContentOutput(BaseModel):
    title: str
    subtitle: str | None = None
    executive_summary: str
    sections: list[dict[str, Any]]


class ReporterOutput(BaseModel):
    generated_files: list[ReportFileOutput] = Field(default_factory=list)
    pdf_content: PDFContentOutput | None = None
    generation_notes: str = ""


class ReporterAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "reporter"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "aggregation" not in context:
            raise InvalidInputError(message="aggregation is required", field="aggregation")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        aggregation = context.get("aggregation", {})
        brief = context.get("brief", {})
        output_formats = brief.get("output_formats", ["pdf"])

        return f"""## Brief
{brief}

## Aggregation
{aggregation}

## Formats: {output_formats}

## Instructions
Generate reports using templates/pdf/report.html. Save to output/.
Signal completion with <promise>COMPLETE</promise>"""

    @property
    def output_filename(self) -> str:
        return StateFiles.REPORT_CONFIG
