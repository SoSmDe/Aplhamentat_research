"""
Ralph Deep Research - Research Agent

Analyst and researcher agent that finds, analyzes, and synthesizes
qualitative information from various sources.

Based on specs/PROMPTS.md Section 5.

Why this agent:
- Finds and analyzes qualitative information from news, reports, websites
- Separates facts from opinions
- Identifies themes and contradictions
- Evaluates source credibility
- Uses Opus model for complex analysis

Timeout: 90 seconds (target: 60 seconds)

Usage:
    agent = ResearchAgent(llm_client, session_manager, search_client)
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "task": {...},           # ResearchTask
        "entity_context": {...}, # Entity information
        "brief_context": {...},  # Brief goal and constraints
        "previous_findings": [...], # Findings from previous rounds
        "round": 1
    })
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    Confidence,
    Contradiction,
    ContradictionView,
    Finding,
    FindingType,
    Priority,
    Question,
    QuestionType,
    ResearchResult,
    Sentiment,
    Source,
    SourceType,
    SourceTypeResult,
    TaskStatus,
    Theme,
)
from src.storage.session import DataType
from src.tools.errors import InvalidInputError
from src.tools.web_search import WebSearchClient, get_search_client


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE
# =============================================================================


class LLMFinding(BaseModel):
    """Research finding from LLM response."""
    finding: str = Field(description="The finding text")
    type: str = Field(description="fact|opinion|analysis")
    confidence: str = Field(description="high|medium|low")
    source: str = Field(description="Source of finding")


class LLMTheme(BaseModel):
    """Theme identified in research."""
    theme: str = Field(description="Theme name")
    points: list[str] = Field(default_factory=list)
    sentiment: str = Field(description="positive|negative|neutral|mixed")


class LLMContradictionView(BaseModel):
    """One side of a contradiction."""
    position: str = Field(description="The position")
    source: str = Field(description="Source")


class LLMContradiction(BaseModel):
    """Contradiction found between sources."""
    topic: str = Field(description="Topic")
    view_1: LLMContradictionView
    view_2: LLMContradictionView


class LLMSource(BaseModel):
    """Source used in research."""
    type: str = Field(description="news|report|website|filing|academic|other")
    title: str = Field(description="Source title")
    url: str | None = Field(default=None)
    date: str | None = Field(default=None)
    credibility: str = Field(default="medium", description="high|medium|low")


class LLMQuestion(BaseModel):
    """Follow-up question from Research Agent."""
    type: str = Field(default="research", description="data|research")
    question: str = Field(description="The question")
    priority: str = Field(default="medium", description="high|medium|low")
    context: str | None = Field(default=None)


class LLMResearchOutput(BaseModel):
    """Full output from Research Agent LLM."""
    task_id: str = Field(description="Task ID")
    round: int = Field(description="Round number")
    status: str = Field(description="done|failed|partial")
    summary: str = Field(default="", description="Brief summary")
    key_findings: list[LLMFinding] = Field(default_factory=list)
    detailed_analysis: str = Field(default="", description="Detailed analysis")
    themes: list[LLMTheme] = Field(default_factory=list)
    contradictions: list[LLMContradiction] = Field(default_factory=list)
    sources: list[LLMSource] = Field(default_factory=list)
    questions: list[LLMQuestion] = Field(default_factory=list)


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class ResearchAgent(BaseAgent):
    """
    Research Agent - Qualitative analysis specialist.

    Finds, analyzes, and synthesizes information from various sources.

    Process:
    1. Generate 3-5 search queries based on task
    2. Execute web search
    3. Read and analyze sources
    4. Extract findings (fact/opinion/analysis)
    5. Identify themes
    6. Detect contradictions
    7. Evaluate source credibility
    8. Generate follow-up questions

    Rules:
    - Always cite sources
    - Explicitly separate facts from opinions
    - Critically evaluate information
    - Stay within Brief scope
    - Maximum 60 seconds per task
    """

    def __init__(
        self,
        llm: Any,  # LLMClient
        session_manager: Any,  # SessionManager
        search_client: WebSearchClient | None = None,
    ) -> None:
        """
        Initialize Research Agent.

        Args:
            llm: LLM client for API calls
            session_manager: Session manager for state persistence
            search_client: Optional web search client
        """
        super().__init__(llm, session_manager)
        self._search_client = search_client or get_search_client()

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "research"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "research_task"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context

        Raises:
            InvalidInputError: If required fields missing
        """
        super().validate_input(context)

        if "task" not in context:
            raise InvalidInputError(
                message="task is required",
                field="task",
            )

        task = context["task"]
        if not isinstance(task, dict):
            raise InvalidInputError(
                message="task must be a dictionary",
                field="task",
            )

        if "id" not in task or "description" not in task:
            raise InvalidInputError(
                message="task must have id and description",
                field="task",
            )

        if "round" not in context:
            raise InvalidInputError(
                message="round is required",
                field="round",
            )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute research task.

        Args:
            context: Input with task, entity_context, brief_context, round

        Returns:
            ResearchResult as dictionary
        """
        session_id = context["session_id"]
        task = context["task"]
        round_num = context["round"]
        entity_context = context.get("entity_context", {})
        brief_context = context.get("brief_context", {})
        previous_findings = context.get("previous_findings", [])

        task_id = task.get("id", "r0")
        description = task.get("description", "")

        self._logger.info(
            "Research agent executing task",
            task_id=task_id,
            description_length=len(description),
        )

        # Step 1: Generate search queries
        search_queries = self._generate_search_queries(task, entity_context)

        # Step 2: Execute web searches
        search_results = await self._execute_searches(search_queries)

        # Step 3: Process with LLM
        llm_output = await self._process_with_llm(
            task_id=task_id,
            round_num=round_num,
            task=task,
            entity_context=entity_context,
            brief_context=brief_context,
            search_results=search_results,
            previous_findings=previous_findings,
        )

        # Step 4: Convert to ResearchResult
        result = self._convert_to_result(llm_output, task_id, round_num)

        # Step 5: Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.RESEARCH_RESULT,
            result=result,
            round=round_num,
            task_id=task_id,
        )

        self._logger.info(
            "Research task completed",
            task_id=task_id,
            status=result["status"],
            findings_count=len(result.get("key_findings", [])),
            sources_count=len(result.get("sources", [])),
        )

        return result

    def _generate_search_queries(
        self,
        task: dict[str, Any],
        entity_context: dict[str, Any],
    ) -> list[str]:
        """
        Generate search queries for the task.

        Args:
            task: Research task
            entity_context: Entity information

        Returns:
            List of search queries
        """
        # Use predefined search queries if available
        predefined = task.get("search_queries", [])
        if predefined:
            return predefined[:5]

        # Generate queries from task description
        description = task.get("description", "")
        focus = task.get("focus", "")
        entity_name = entity_context.get("name", "")

        queries = []

        # Primary query
        if entity_name:
            queries.append(f"{entity_name} {description[:50]}")
        else:
            queries.append(description[:100])

        # Focus-based query
        if focus:
            if entity_name:
                queries.append(f"{entity_name} {focus}")
            else:
                queries.append(focus)

        # Add context-specific queries based on source types
        source_types = task.get("source_types", [])
        if "news" in source_types or "NEWS" in source_types:
            if entity_name:
                queries.append(f"{entity_name} latest news")
            else:
                queries.append(f"{description[:30]} news")

        if "reports" in source_types or "REPORTS" in source_types:
            if entity_name:
                queries.append(f"{entity_name} analysis report")
            else:
                queries.append(f"{description[:30]} report")

        if "analyst_reports" in source_types or "ANALYST_REPORTS" in source_types:
            if entity_name:
                queries.append(f"{entity_name} analyst opinion")

        # Ensure at least 3 queries, max 5
        if len(queries) < 3:
            queries.append(f"{description[:50]} overview")
            queries.append(f"{description[:50]} analysis")

        return queries[:5]

    async def _execute_searches(
        self,
        queries: list[str],
    ) -> list[dict[str, Any]]:
        """
        Execute web searches for all queries.

        Args:
            queries: List of search queries

        Returns:
            List of search results with query info
        """
        all_results = []

        for query in queries:
            try:
                results = await self._search_client.search(
                    query=query,
                    num_results=5,
                )

                for result in results:
                    all_results.append({
                        "query": query,
                        "title": result.title,
                        "url": result.url,
                        "snippet": result.snippet,
                        "date": result.date,
                    })

            except Exception as e:
                self._logger.warning(
                    "Search failed for query",
                    query=query,
                    error=str(e),
                )

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            url = result.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(result)

        self._logger.debug(
            "Search completed",
            total_results=len(unique_results),
            queries_executed=len(queries),
        )

        return unique_results[:20]  # Limit to 20 results

    async def _process_with_llm(
        self,
        task_id: str,
        round_num: int,
        task: dict[str, Any],
        entity_context: dict[str, Any],
        brief_context: dict[str, Any],
        search_results: list[dict[str, Any]],
        previous_findings: list[str],
    ) -> LLMResearchOutput:
        """
        Process research with LLM.

        Args:
            task_id: Task ID
            round_num: Round number
            task: Task definition
            entity_context: Entity information
            brief_context: Brief goal and constraints
            search_results: Web search results
            previous_findings: Previous research findings

        Returns:
            Structured LLM output
        """
        description = task.get("description", "")
        focus = task.get("focus", "")

        entity_name = entity_context.get("name", "Unknown")
        brief_goal = brief_context.get("goal", "General research")

        # Format search results for prompt
        search_text = ""
        for i, result in enumerate(search_results[:15], 1):
            search_text += f"""
{i}. **{result.get('title', 'No title')}**
   URL: {result.get('url', 'N/A')}
   Date: {result.get('date', 'Unknown')}
   {result.get('snippet', '')}
"""

        # Format previous findings
        prev_findings_text = ""
        if previous_findings:
            prev_findings_text = "\n".join(f"- {f}" for f in previous_findings[:10])

        prompt = f"""## Research Task

**Task ID**: {task_id}
**Round**: {round_num}
**Description**: {description}
**Focus**: {focus or 'General analysis'}

**Entity**: {entity_name}
**Brief Goal**: {brief_goal}

## Search Results:
{search_text if search_text else "No search results available"}

## Previous Findings (avoid duplication):
{prev_findings_text if prev_findings_text else "No previous findings"}

## Instructions

Analyze the search results and provide:

1. **Summary**: 2-3 sentence overview of findings

2. **Key Findings**: Extract important information
   - Classify each as fact, opinion, or analysis
   - Rate confidence (high/medium/low)
   - Cite the source

3. **Themes**: Identify recurring themes
   - List supporting points
   - Assess sentiment (positive/negative/neutral/mixed)

4. **Contradictions**: Note any conflicting information
   - Document both viewpoints
   - Cite sources for each

5. **Sources**: Evaluate credibility of sources used

6. **Questions**: What needs further research?
   - Flag data needs vs research needs
   - Prioritize (high/medium/low)

Be critical - separate facts from opinions clearly.
Stay within the scope of the Brief goal.

Current timestamp: {datetime.now(timezone.utc).isoformat()}"""

        try:
            result = await self._call_llm_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMResearchOutput,
                max_tokens=4096,
                temperature=0.4,
            )
            result.task_id = task_id
            result.round = round_num
            return result

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback",
                error=str(e),
            )
            return self._create_fallback_output(
                task_id=task_id,
                round_num=round_num,
                task=task,
                search_results=search_results,
            )

    def _create_fallback_output(
        self,
        task_id: str,
        round_num: int,
        task: dict[str, Any],
        search_results: list[dict[str, Any]],
    ) -> LLMResearchOutput:
        """Create fallback output if LLM fails."""
        description = task.get("description", "")

        # Extract basic findings from search results
        findings = []
        sources = []

        for result in search_results[:5]:
            title = result.get("title", "")
            url = result.get("url", "")
            snippet = result.get("snippet", "")

            if snippet:
                findings.append(LLMFinding(
                    finding=snippet[:200],
                    type="fact",
                    confidence="low",
                    source=title or url or "Unknown",
                ))

            sources.append(LLMSource(
                type="website",
                title=title or "Unknown",
                url=url,
                date=result.get("date"),
                credibility="medium",
            ))

        status = "partial" if findings else "failed"

        return LLMResearchOutput(
            task_id=task_id,
            round=round_num,
            status=status,
            summary=f"Partial research on: {description[:100]}",
            key_findings=findings,
            detailed_analysis="",
            themes=[],
            contradictions=[],
            sources=sources,
            questions=[LLMQuestion(
                type="research",
                question=f"Need more detailed analysis of: {description[:50]}",
                priority="medium",
                context="LLM processing failed, manual review needed",
            )],
        )

    def _convert_to_result(
        self,
        llm_output: LLMResearchOutput,
        task_id: str,
        round_num: int,
    ) -> dict[str, Any]:
        """Convert LLM output to ResearchResult dictionary."""
        # Convert status
        try:
            status = TaskStatus(llm_output.status)
        except ValueError:
            status = TaskStatus.PARTIAL

        # Convert key findings
        key_findings = []
        for f in llm_output.key_findings:
            try:
                f_type = FindingType(f.type)
            except ValueError:
                f_type = FindingType.ANALYSIS

            try:
                confidence = Confidence(f.confidence)
            except ValueError:
                confidence = Confidence.MEDIUM

            key_findings.append(Finding(
                finding=f.finding[:500],
                type=f_type,
                confidence=confidence,
                source=f.source[:200],
            ))

        # Convert themes
        themes = []
        for t in llm_output.themes:
            try:
                sentiment = Sentiment(t.sentiment)
            except ValueError:
                sentiment = Sentiment.NEUTRAL

            themes.append(Theme(
                theme=t.theme[:100],
                points=t.points[:10],
                sentiment=sentiment,
            ))

        # Convert contradictions
        contradictions = []
        for c in llm_output.contradictions:
            contradictions.append(Contradiction(
                topic=c.topic[:200],
                view_1=ContradictionView(
                    position=c.view_1.position[:300],
                    source=c.view_1.source[:100],
                ),
                view_2=ContradictionView(
                    position=c.view_2.position[:300],
                    source=c.view_2.source[:100],
                ),
            ))

        # Convert sources
        sources = []
        for s in llm_output.sources:
            try:
                s_type = SourceTypeResult(s.type)
            except ValueError:
                s_type = SourceTypeResult.OTHER

            try:
                credibility = Confidence(s.credibility)
            except ValueError:
                credibility = Confidence.MEDIUM

            sources.append(Source(
                type=s_type,
                title=s.title[:200],
                url=s.url,
                date=s.date,
                credibility=credibility,
            ))

        # Convert questions
        questions = []
        for q in llm_output.questions:
            try:
                q_type = QuestionType(q.type)
            except ValueError:
                q_type = QuestionType.RESEARCH

            try:
                priority = Priority(q.priority)
            except ValueError:
                priority = Priority.MEDIUM

            questions.append(Question(
                type=q_type,
                question=q.question[:300],
                context=q.context[:500] if q.context else None,
                priority=priority,
                source_task_id=task_id,
            ))

        result = ResearchResult(
            task_id=task_id,
            round=round_num,
            status=status,
            summary=llm_output.summary[:500],
            key_findings=key_findings,
            detailed_analysis=llm_output.detailed_analysis[:5000],
            themes=themes,
            contradictions=contradictions,
            sources=sources,
            questions=questions,
        )

        return result.model_dump(mode="json")
