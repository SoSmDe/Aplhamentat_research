"""
Ralph Deep Research - Brief Builder Agent (Claude Code Native)

Interactive agent that builds research specification through dialog.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class ScopeItemOutput(BaseModel):
    topic: str
    type: str = Field(description="data|research|both")
    priority: str = Field(description="high|medium|low")
    specific_questions: list[str] = Field(default_factory=list)


class BriefOutput(BaseModel):
    goal: str
    scope_items: list[ScopeItemOutput]
    output_formats: list[str] = Field(default=["pdf"])
    constraints: list[str] = Field(default_factory=list)
    timeline: str | None = None
    additional_context: str = ""


class BriefBuilderResponse(BaseModel):
    is_complete: bool
    message: str
    brief: BriefOutput | None = None
    clarifying_questions: list[str] = Field(default_factory=list)


class BriefBuilderAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "brief_builder"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "initial_context" not in context:
            raise InvalidInputError(message="initial_context is required", field="initial_context")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        initial_context = context.get("initial_context", {})
        conversation = context.get("conversation", [])
        user_message = context.get("user_message", "")

        conv_str = ""
        for msg in conversation:
            conv_str += f"**{msg.get('role', 'user').title()}:** {msg.get('content', '')}\n\n"

        return f"""## Initial Context
{initial_context}

## Conversation
{conv_str or "No previous conversation."}

## User Message
{user_message or "Start by asking about research goals."}

## Instructions
Ask clarifying questions, then save brief to state/brief.json when approved."""

    @property
    def output_filename(self) -> str:
        return StateFiles.BRIEF
