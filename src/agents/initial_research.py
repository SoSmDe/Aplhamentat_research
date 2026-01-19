"""
Ralph Deep Research - Initial Research Agent (Claude Code Native)

Fast preliminary research agent that gathers basic context from user query.
"""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field
from src.agents.base import BaseAgent, StateFiles
from src.tools.errors import InvalidInputError


class LLMEntityIdentifiers(BaseModel):
    ticker: str | None = None
    website: str | None = None
    country: str | None = None
    exchange: str | None = None


class LLMEntity(BaseModel):
    name: str
    type: str = Field(description="company|market|concept|product|person|sector")
    identifiers: LLMEntityIdentifiers = Field(default_factory=LLMEntityIdentifiers)
    brief_description: str = ""


class LLMQueryAnalysis(BaseModel):
    original_query: str
    detected_language: str = Field(description="ru|en")
    detected_intent: str = Field(description="investment|market_research|competitive|learning|other")
    confidence: float = Field(ge=0, le=1)


class InitialResearchOutput(BaseModel):
    query_analysis: LLMQueryAnalysis
    entities: list[LLMEntity] = Field(default_factory=list)
    context_summary: str
    suggested_topics: list[str] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)


class InitialResearchAgent(BaseAgent):
    @property
    def agent_name(self) -> str:
        return "initial_research"

    def validate_input(self, context: dict[str, Any]) -> None:
        if "user_query" not in context:
            raise InvalidInputError(message="user_query is required", field="user_query")

    def get_prompt_context(self, context: dict[str, Any]) -> str:
        user_query = context.get("user_query", "")
        return f"""## User Query
{user_query}

## Instructions
1. Use web_search to gather context (2-3 searches)
2. Extract key entities
3. Detect language and intent
4. Create context summary
5. Save to state/initial_context.json"""

    @property
    def output_filename(self) -> str:
        return StateFiles.INITIAL_CONTEXT
