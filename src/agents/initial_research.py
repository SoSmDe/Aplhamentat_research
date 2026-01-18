"""
Ralph Deep Research - Initial Research Agent

Fast preliminary research agent that gathers basic context from user query.
Based on specs/PROMPTS.md Section 1.

Why this agent:
- Provides initial context for Brief Builder to start informed dialog
- Extracts entities (companies, tickers, markets, concepts)
- Detects language and user intent
- Generates suggested research topics

Timeout: 90 seconds (target: 60 seconds)

Usage:
    agent = InitialResearchAgent(llm_client, session_manager)
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "user_query": "Tell me about Realty Income"
    })
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    Entity,
    EntityIdentifiers,
    EntityType,
    InitialContext,
    Language,
    QueryAnalysis,
    UserIntent,
)
from src.storage.session import DataType
from src.tools.errors import InvalidInputError
from src.tools.web_search import WebSearchClient, get_search_client


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE
# =============================================================================


class LLMEntityIdentifiers(BaseModel):
    """Entity identifiers from LLM response."""
    ticker: str | None = None
    website: str | None = None
    country: str | None = None
    exchange: str | None = None


class LLMEntity(BaseModel):
    """Entity extracted by LLM."""
    name: str
    type: str = Field(description="company|market|concept|product|person|sector")
    identifiers: LLMEntityIdentifiers = Field(default_factory=LLMEntityIdentifiers)
    brief_description: str = ""
    category: str = ""
    sector: str | None = None


class LLMQueryAnalysis(BaseModel):
    """Query analysis from LLM."""
    original_query: str
    detected_language: str = Field(description="ru|en")
    detected_intent: str = Field(description="investment|market_research|competitive|learning|other")
    confidence: float = Field(ge=0, le=1)


class LLMInitialResearchOutput(BaseModel):
    """Full output from LLM for initial research."""
    session_id: str
    query_analysis: LLMQueryAnalysis
    entities: list[LLMEntity] = Field(default_factory=list)
    context_summary: str
    suggested_topics: list[str] = Field(default_factory=list)
    sources_used: list[str] = Field(default_factory=list)


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class InitialResearchAgent(BaseAgent):
    """
    Initial Research Agent - Fast preliminary context gathering.

    Analyzes user query, extracts entities, detects intent,
    and generates context for Brief Builder.

    Process:
    1. Parse query for key entities (companies, tickers, markets)
    2. Execute 2-3 web searches for basic facts
    3. Collect official sources and metadata
    4. Structure context summary

    Constraints:
    - Maximum 60 seconds execution
    - Facts only, no deep analysis
    - Verified sources only
    """

    def __init__(
        self,
        llm: Any,  # LLMClient
        session_manager: Any,  # SessionManager
        search_client: WebSearchClient | None = None,
    ) -> None:
        """
        Initialize Initial Research Agent.

        Args:
            llm: LLM client for API calls
            session_manager: Session manager for state persistence
            search_client: Optional web search client (defaults to mock)
        """
        super().__init__(llm, session_manager)
        self._search_client = search_client or get_search_client()

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "initial_research"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "initial_research"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context with session_id and user_query

        Raises:
            InvalidInputError: If required fields missing or invalid
        """
        super().validate_input(context)

        if "user_query" not in context:
            raise InvalidInputError(
                message="user_query is required",
                field="user_query",
            )

        query = context.get("user_query", "")
        if not query or len(query.strip()) < 3:
            raise InvalidInputError(
                message="user_query must be at least 3 characters",
                field="user_query",
                value=query,
            )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute initial research on user query.

        Args:
            context: Input with session_id and user_query

        Returns:
            InitialContext as dictionary
        """
        session_id = context["session_id"]
        user_query = context["user_query"].strip()

        self._logger.info(
            "Starting initial research",
            query_length=len(user_query),
        )

        # Step 1: Perform quick web searches for context
        search_results = await self._gather_search_results(user_query)
        sources_used = [r.url for r in search_results if r.url]

        # Step 2: Build context string for LLM
        search_context = self._build_search_context(search_results)

        # Step 3: Call LLM for structured analysis
        llm_output = await self._analyze_with_llm(
            session_id=session_id,
            user_query=user_query,
            search_context=search_context,
        )

        # Step 4: Convert to InitialContext
        initial_context = self._build_initial_context(
            session_id=session_id,
            llm_output=llm_output,
            sources_used=sources_used,
        )

        # Step 5: Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.INITIAL_CONTEXT,
            result=initial_context.model_dump(mode="json"),
        )

        self._logger.info(
            "Initial research completed",
            entities_count=len(initial_context.entities),
            topics_count=len(initial_context.suggested_topics),
        )

        return initial_context.model_dump(mode="json")

    async def _gather_search_results(
        self,
        query: str,
        max_results: int = 5,
    ) -> list:
        """
        Gather search results for initial context.

        Args:
            query: User query to search
            max_results: Maximum results per search

        Returns:
            List of SearchResult objects
        """
        from src.tools.web_search import SearchResult

        results: list[SearchResult] = []

        try:
            # Primary search on the query itself
            primary_results = await self._search_client.search(
                query=query,
                num_results=max_results,
            )
            results.extend(primary_results)

            # If query mentions a company, search for financial info
            financial_keywords = ["stock", "ticker", "company", "inc", "corp", "ltd"]
            if any(kw in query.lower() for kw in financial_keywords):
                financial_results = await self._search_client.search(
                    query=f"{query} stock ticker financial",
                    num_results=3,
                )
                results.extend(financial_results)

        except Exception as e:
            self._logger.warning(
                "Search failed, continuing with empty results",
                error=str(e),
            )

        self._logger.debug(
            "Search completed",
            result_count=len(results),
        )

        return results

    def _build_search_context(self, search_results: list) -> str:
        """
        Build context string from search results.

        Args:
            search_results: List of SearchResult objects

        Returns:
            Formatted context string for LLM
        """
        if not search_results:
            return "No search results available."

        context_parts = []
        for i, result in enumerate(search_results[:10], 1):
            context_parts.append(
                f"{i}. {result.title}\n"
                f"   URL: {result.url}\n"
                f"   {result.snippet}"
            )

        return "\n\n".join(context_parts)

    async def _analyze_with_llm(
        self,
        session_id: str,
        user_query: str,
        search_context: str,
    ) -> LLMInitialResearchOutput:
        """
        Analyze query and search results with LLM.

        Args:
            session_id: Session ID
            user_query: Original user query
            search_context: Formatted search results

        Returns:
            Structured LLM output
        """
        # Build user message with query and context
        user_message = f"""Проанализируй следующий запрос пользователя и контекст из поиска.

## Запрос пользователя:
{user_query}

## Контекст из поиска:
{search_context}

## Инструкции:
1. Извлеки ключевые сущности (компании, рынки, концепции, продукты, персоны)
2. Определи язык запроса (ru или en)
3. Определи намерение пользователя (investment, market_research, competitive, learning, other)
4. Создай краткое резюме контекста (3-5 предложений)
5. Предложи 3-5 тем для исследования

Верни результат в формате JSON согласно схеме."""

        try:
            result = await self._call_llm_structured(
                messages=[{"role": "user", "content": user_message}],
                response_model=LLMInitialResearchOutput,
                max_tokens=2048,
                temperature=0.3,
            )
            # Ensure session_id is set correctly
            result.session_id = session_id
            return result

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback",
                error=str(e),
            )
            return self._create_fallback_output(session_id, user_query)

    def _create_fallback_output(
        self,
        session_id: str,
        user_query: str,
    ) -> LLMInitialResearchOutput:
        """
        Create fallback output if LLM call fails.

        Args:
            session_id: Session ID
            user_query: Original user query

        Returns:
            Basic LLM output with minimal extraction
        """
        # Detect language based on characters
        has_cyrillic = any('\u0400' <= c <= '\u04FF' for c in user_query)
        detected_language = "ru" if has_cyrillic else "en"

        # Basic intent detection
        intent_keywords = {
            "investment": ["invest", "buy", "sell", "stock", "инвест", "купить", "акци"],
            "market_research": ["market", "trend", "рынок", "тренд"],
            "competitive": ["competitor", "compare", "конкурент", "сравн"],
            "learning": ["what is", "explain", "tell me", "что такое", "расскажи", "объясни"],
        }

        detected_intent = "other"
        query_lower = user_query.lower()
        for intent, keywords in intent_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_intent = intent
                break

        return LLMInitialResearchOutput(
            session_id=session_id,
            query_analysis=LLMQueryAnalysis(
                original_query=user_query,
                detected_language=detected_language,
                detected_intent=detected_intent,
                confidence=0.5,
            ),
            entities=[],
            context_summary=f"User query: {user_query}. Additional context needed from web search.",
            suggested_topics=[
                "General overview",
                "Key characteristics",
                "Recent developments",
            ],
            sources_used=[],
        )

    def _build_initial_context(
        self,
        session_id: str,
        llm_output: LLMInitialResearchOutput,
        sources_used: list[str],
    ) -> InitialContext:
        """
        Build InitialContext from LLM output.

        Args:
            session_id: Session ID
            llm_output: Structured LLM output
            sources_used: List of source URLs

        Returns:
            InitialContext Pydantic model
        """
        # Convert language
        try:
            language = Language(llm_output.query_analysis.detected_language)
        except ValueError:
            language = Language.EN

        # Convert intent
        try:
            intent = UserIntent(llm_output.query_analysis.detected_intent)
        except ValueError:
            intent = UserIntent.OTHER

        # Build query analysis
        query_analysis = QueryAnalysis(
            original_query=llm_output.query_analysis.original_query,
            detected_language=language,
            detected_intent=intent,
            confidence=llm_output.query_analysis.confidence,
        )

        # Convert entities
        entities = []
        for llm_entity in llm_output.entities:
            try:
                entity_type = EntityType(llm_entity.type)
            except ValueError:
                entity_type = EntityType.CONCEPT

            entity = Entity(
                name=llm_entity.name,
                type=entity_type,
                identifiers=EntityIdentifiers(
                    ticker=llm_entity.identifiers.ticker,
                    website=llm_entity.identifiers.website,
                    country=llm_entity.identifiers.country,
                    exchange=llm_entity.identifiers.exchange,
                ),
                brief_description=llm_entity.brief_description[:500] if llm_entity.brief_description else "",
                category=llm_entity.category,
                sector=llm_entity.sector,
            )
            entities.append(entity)

        # Combine sources
        all_sources = list(set(sources_used + llm_output.sources_used))

        return InitialContext(
            session_id=session_id,
            query_analysis=query_analysis,
            entities=entities,
            context_summary=llm_output.context_summary[:1000],
            suggested_topics=llm_output.suggested_topics[:10],
            sources_used=all_sources[:20],
        )
