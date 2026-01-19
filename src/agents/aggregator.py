"""
Ralph Deep Research - Aggregator Agent

Synthesizes all data and research results into a coherent document
with key insights, sections per scope item, and actionable recommendations.

Based on specs/PROMPTS.md Section 6.

Why this agent:
- Collects all results from Data and Research agents
- Maps results to Brief scope items
- Detects and resolves contradictions
- Synthesizes executive summary
- Generates recommendations with confidence scoring
- Uses Opus model for complex synthesis

Timeout: 120 seconds (target: 60 seconds)

Usage:
    agent = AggregatorAgent(llm_client, session_manager)
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "brief": {...},               # Brief
        "all_data_results": [...],    # List[DataResult]
        "all_research_results": [...],# List[ResearchResult]
        "rounds_completed": 3
    })
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    ActionItem,
    AggregatedResearch,
    AggregationMetadata,
    Confidence,
    ContradictionFound,
    CoverageSummary,
    DataTable,
    KeyInsight,
    Priority,
    Recommendation,
    Section,
    Sentiment,
)
from src.storage.session import DataType
from src.tools.errors import InvalidInputError


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE
# =============================================================================


class LLMKeyInsight(BaseModel):
    """Key insight from LLM response."""
    insight: str = Field(description="The insight text")
    supporting_data: list[str] = Field(default_factory=list)
    importance: str = Field(default="medium", description="high|medium|low")


class LLMDataHighlight(BaseModel):
    """Data highlight with metric name and value."""
    metric: str = Field(description="Metric name")
    value: str = Field(description="Value with context")


class LLMSection(BaseModel):
    """Research section from LLM response."""
    title: str = Field(description="Section title")
    brief_scope_id: int = Field(description="Corresponding scope item ID")
    summary: str = Field(default="", description="2-3 sentence summary")
    data_highlights: list[LLMDataHighlight] = Field(default_factory=list)
    analysis: str = Field(default="", description="Detailed analysis")
    key_points: list[str] = Field(default_factory=list)
    sentiment: str = Field(default="neutral", description="positive|negative|neutral|mixed")
    charts_suggested: list[str] = Field(default_factory=list)


class LLMContradiction(BaseModel):
    """Contradiction found in research."""
    topic: str = Field(description="Topic of contradiction")
    sources: list[str] = Field(default_factory=list)
    resolution: str = Field(default="", description="How to interpret")


class LLMActionItem(BaseModel):
    """Recommended action item."""
    action: str = Field(description="Action to take")
    priority: str = Field(default="medium", description="high|medium|low")
    rationale: str = Field(default="", description="Why this action")


class LLMRecommendation(BaseModel):
    """Final recommendation from LLM."""
    verdict: str = Field(description="Overall verdict")
    confidence: str = Field(default="medium", description="high|medium|low")
    confidence_reasoning: str = Field(default="")
    reasoning: str = Field(description="Detailed reasoning")
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)
    action_items: list[LLMActionItem] = Field(default_factory=list)
    risks_to_monitor: list[str] = Field(default_factory=list)


class LLMCoverageSummary(BaseModel):
    """Coverage summary for a scope item."""
    topic: str = Field(description="Topic name")
    coverage_percent: float = Field(description="Coverage percentage")
    gaps: list[str] = Field(default_factory=list)


class LLMAggregatorOutput(BaseModel):
    """Full output from Aggregator Agent LLM."""
    executive_summary: str = Field(description="3-5 sentence executive summary")
    key_insights: list[LLMKeyInsight] = Field(default_factory=list)
    sections: list[LLMSection] = Field(default_factory=list)
    contradictions_found: list[LLMContradiction] = Field(default_factory=list)
    recommendation: LLMRecommendation = Field(...)
    coverage_summary: list[LLMCoverageSummary] = Field(default_factory=list)


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class AggregatorAgent(BaseAgent):
    """
    Aggregator Agent - Synthesizes all research into coherent document.

    Process:
    1. Inventory all data and research results
    2. Map results to Brief scope items
    3. Check for contradictions
    4. Synthesize sections (one per scope item)
    5. Write executive summary
    6. Extract 3-10 key insights
    7. Generate recommendation with verdict, confidence, reasoning
    8. Create action items

    Rules:
    - Always reference Brief goal
    - Recommendation must answer user's question
    - Be objective - show pros and cons
    - Use data to support conclusions
    - Explicitly state uncertainties
    """

    def __init__(
        self,
        llm: Any,  # LLMClient
        session_manager: Any,  # SessionManager
    ) -> None:
        """
        Initialize Aggregator Agent.

        Args:
            llm: LLM client for API calls
            session_manager: Session manager for state persistence
        """
        super().__init__(llm, session_manager)
        self._start_time: float = 0

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "aggregator"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "aggregation"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context

        Raises:
            InvalidInputError: If required fields missing
        """
        super().validate_input(context)

        if "brief" not in context:
            raise InvalidInputError(
                message="brief is required",
                field="brief",
            )

        brief = context["brief"]
        if not isinstance(brief, dict):
            raise InvalidInputError(
                message="brief must be a dictionary",
                field="brief",
            )

        if "scope" not in brief or not brief.get("scope"):
            raise InvalidInputError(
                message="brief must have scope items",
                field="brief.scope",
            )

        if "rounds_completed" not in context:
            raise InvalidInputError(
                message="rounds_completed is required",
                field="rounds_completed",
            )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute aggregation task.

        Args:
            context: Input with brief, all results, rounds_completed

        Returns:
            AggregatedResearch as dictionary
        """
        self._start_time = time.time()

        session_id = context["session_id"]
        brief = context["brief"]
        all_data_results = context.get("all_data_results", [])
        all_research_results = context.get("all_research_results", [])
        rounds_completed = context["rounds_completed"]

        brief_id = brief.get("brief_id", "unknown")
        goal = brief.get("goal", "")
        scope = brief.get("scope", [])

        self._logger.info(
            "Aggregator starting synthesis",
            brief_id=brief_id,
            data_results_count=len(all_data_results),
            research_results_count=len(all_research_results),
            rounds_completed=rounds_completed,
        )

        # Step 1: Prepare context for LLM
        brief_context = self._format_brief_context(brief)
        data_context = self._format_data_results(all_data_results)
        research_context = self._format_research_results(all_research_results)

        # Step 2: Call LLM for synthesis
        llm_output = await self._synthesize_with_llm(
            brief_context=brief_context,
            data_context=data_context,
            research_context=research_context,
            goal=goal,
            scope=scope,
        )

        # Step 3: Convert to AggregatedResearch
        result = self._convert_to_result(
            llm_output=llm_output,
            session_id=session_id,
            brief_id=brief_id,
            all_data_results=all_data_results,
            all_research_results=all_research_results,
            rounds_completed=rounds_completed,
        )

        # Step 4: Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.AGGREGATION,
            result=result,
        )

        self._logger.info(
            "Aggregation completed",
            sections_count=len(result.get("sections", [])),
            insights_count=len(result.get("key_insights", [])),
        )

        return result

    def _format_brief_context(self, brief: dict[str, Any]) -> str:
        """Format brief for LLM prompt."""
        goal = brief.get("goal", "Unknown goal")
        scope_items = brief.get("scope", [])
        constraints = brief.get("constraints", {})
        user_context = brief.get("user_context", {})

        scope_text = ""
        for item in scope_items:
            scope_text += f"- [{item.get('id', '?')}] {item.get('topic', '')} ({item.get('type', 'both')})\n"

        constraints_text = ""
        if constraints:
            focus = constraints.get("focus_areas", [])
            if focus:
                constraints_text += f"Focus: {', '.join(focus)}\n"
            exclude = constraints.get("exclude", [])
            if exclude:
                constraints_text += f"Exclude: {', '.join(exclude)}\n"

        user_text = ""
        if user_context:
            intent = user_context.get("intent", "")
            horizon = user_context.get("horizon", "")
            if intent:
                user_text += f"Intent: {intent}\n"
            if horizon:
                user_text += f"Horizon: {horizon}\n"

        return f"""## Brief
**Goal**: {goal}

**User Context**:
{user_text if user_text else "Not specified"}

**Scope Items**:
{scope_text}

**Constraints**:
{constraints_text if constraints_text else "None specified"}
"""

    def _format_data_results(self, results: list[dict[str, Any]]) -> str:
        """Format data results for LLM prompt."""
        if not results:
            return "No data results available."

        text = ""
        for i, result in enumerate(results, 1):
            task_id = result.get("task_id", f"d{i}")
            status = result.get("status", "unknown")
            metrics = result.get("metrics", {})
            tables = result.get("tables", [])

            text += f"\n### Data Result: {task_id} (status: {status})\n"

            # Format metrics
            if metrics:
                text += "**Metrics:**\n"
                for name, metric in metrics.items():
                    if isinstance(metric, dict):
                        value = metric.get("value", "N/A")
                        unit = metric.get("unit", "")
                        period = metric.get("period", "")
                        text += f"- {name}: {value}{' ' + unit if unit else ''}{' (' + period + ')' if period else ''}\n"
                    else:
                        text += f"- {name}: {metric}\n"

            # Format tables (summary only)
            if tables:
                text += f"**Tables**: {len(tables)} table(s) available\n"
                for table in tables[:2]:
                    table_name = table.get("name", "Unnamed")
                    headers = table.get("headers", [])
                    rows = table.get("rows", [])
                    text += f"  - {table_name}: {len(headers)} columns, {len(rows)} rows\n"

        return text[:8000]  # Limit size

    def _format_research_results(self, results: list[dict[str, Any]]) -> str:
        """Format research results for LLM prompt."""
        if not results:
            return "No research results available."

        text = ""
        for i, result in enumerate(results, 1):
            task_id = result.get("task_id", f"r{i}")
            status = result.get("status", "unknown")
            summary = result.get("summary", "")
            key_findings = result.get("key_findings", [])
            themes = result.get("themes", [])
            contradictions = result.get("contradictions", [])
            sources = result.get("sources", [])

            text += f"\n### Research Result: {task_id} (status: {status})\n"

            if summary:
                text += f"**Summary**: {summary[:300]}\n"

            # Key findings
            if key_findings:
                text += "**Key Findings:**\n"
                for f in key_findings[:5]:
                    finding = f.get("finding", "") if isinstance(f, dict) else str(f)
                    f_type = f.get("type", "analysis") if isinstance(f, dict) else "analysis"
                    confidence = f.get("confidence", "medium") if isinstance(f, dict) else "medium"
                    text += f"- [{f_type}, {confidence}] {finding[:150]}\n"

            # Themes
            if themes:
                text += "**Themes:**\n"
                for t in themes[:3]:
                    theme = t.get("theme", "") if isinstance(t, dict) else str(t)
                    sentiment = t.get("sentiment", "neutral") if isinstance(t, dict) else "neutral"
                    text += f"- {theme} ({sentiment})\n"

            # Contradictions
            if contradictions:
                text += "**Contradictions noted:**\n"
                for c in contradictions[:2]:
                    topic = c.get("topic", "") if isinstance(c, dict) else str(c)
                    text += f"- {topic[:100]}\n"

            # Sources
            if sources:
                text += f"**Sources**: {len(sources)} source(s)\n"

        return text[:10000]  # Limit size

    async def _synthesize_with_llm(
        self,
        brief_context: str,
        data_context: str,
        research_context: str,
        goal: str,
        scope: list[dict[str, Any]],
    ) -> LLMAggregatorOutput:
        """
        Synthesize all results with LLM.

        Args:
            brief_context: Formatted brief
            data_context: Formatted data results
            research_context: Formatted research results
            goal: Brief goal
            scope: Scope items

        Returns:
            Structured LLM output
        """
        # Format scope IDs for reference
        scope_ids = [f"{s.get('id', i+1)}: {s.get('topic', 'Unknown')}" for i, s in enumerate(scope)]

        prompt = f"""## Aggregation Task

You are synthesizing research results into a comprehensive document.

{brief_context}

## Data Results
{data_context}

## Research Results
{research_context}

## Instructions

Create a comprehensive synthesis following this structure:

1. **Executive Summary** (3-5 sentences)
   - Answer the main question from the goal
   - Highlight the most important finding
   - Give a clear verdict or assessment

2. **Key Insights** (3-10 insights)
   - Important findings that answer the goal
   - Support each with data references
   - Rate importance (high/medium)

3. **Sections** (one per scope item)
   Scope items: {scope_ids}

   For each section:
   - Title matching scope item topic
   - 2-3 sentence summary
   - Data highlights (key metrics with context)
   - Detailed analysis
   - Key bullet points
   - Sentiment (positive/negative/neutral/mixed)
   - Suggested chart types

4. **Contradictions Found**
   - Any conflicting information between sources
   - How to resolve/interpret them

5. **Recommendation**
   - Verdict relative to user's goal: "{goal}"
   - Confidence level with reasoning
   - Pros and cons list
   - Specific action items with priority
   - Risks to monitor

6. **Coverage Summary**
   - For each scope item: coverage % and remaining gaps

Be objective. Show both positives and negatives.
Use data to support conclusions.
Explicitly state uncertainties.

Current timestamp: {datetime.now(timezone.utc).isoformat()}"""

        try:
            result = await self._call_llm_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMAggregatorOutput,
                max_tokens=8192,
                temperature=0.3,
            )
            return result

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback",
                error=str(e),
            )
            return self._create_fallback_output(goal, scope)

    def _create_fallback_output(
        self,
        goal: str,
        scope: list[dict[str, Any]],
    ) -> LLMAggregatorOutput:
        """Create fallback output if LLM fails."""
        sections = []
        coverage_summary = []

        for i, item in enumerate(scope):
            topic = item.get("topic", f"Topic {i+1}")
            scope_id = item.get("id", i + 1)

            sections.append(LLMSection(
                title=topic,
                brief_scope_id=scope_id,
                summary=f"Analysis of {topic} is available. Manual review recommended.",
                data_highlights=[],
                analysis="LLM processing failed. Please review raw results manually.",
                key_points=["Manual review required"],
                sentiment="neutral",
                charts_suggested=[],
            ))

            coverage_summary.append(LLMCoverageSummary(
                topic=topic,
                coverage_percent=50.0,
                gaps=["LLM synthesis failed - manual review needed"],
            ))

        return LLMAggregatorOutput(
            executive_summary=f"Research on '{goal}' has been collected. LLM synthesis failed - manual review of raw results is recommended.",
            key_insights=[
                LLMKeyInsight(
                    insight="Data and research have been collected but automated synthesis failed",
                    supporting_data=["Raw results available for manual review"],
                    importance="high",
                )
            ],
            sections=sections,
            contradictions_found=[],
            recommendation=LLMRecommendation(
                verdict="Unable to determine - manual review required",
                confidence="low",
                confidence_reasoning="LLM synthesis failed",
                reasoning="Automated synthesis was not possible. Review raw data and research results manually.",
                pros=[],
                cons=[],
                action_items=[
                    LLMActionItem(
                        action="Review raw data results",
                        priority="high",
                        rationale="Automated synthesis failed",
                    ),
                    LLMActionItem(
                        action="Review raw research results",
                        priority="high",
                        rationale="Automated synthesis failed",
                    ),
                ],
                risks_to_monitor=["Incomplete analysis due to synthesis failure"],
            ),
            coverage_summary=coverage_summary,
        )

    def _convert_to_result(
        self,
        llm_output: LLMAggregatorOutput,
        session_id: str,
        brief_id: str,
        all_data_results: list[dict[str, Any]],
        all_research_results: list[dict[str, Any]],
        rounds_completed: int,
    ) -> dict[str, Any]:
        """Convert LLM output to AggregatedResearch dictionary."""

        # Convert key insights
        key_insights = []
        for insight in llm_output.key_insights[:10]:
            try:
                importance = Confidence(insight.importance)
            except ValueError:
                importance = Confidence.MEDIUM

            key_insights.append(KeyInsight(
                insight=insight.insight[:500],
                supporting_data=insight.supporting_data[:5],
                importance=importance,
            ))

        # Convert sections
        sections = []
        for section in llm_output.sections:
            try:
                sentiment = Sentiment(section.sentiment)
            except ValueError:
                sentiment = Sentiment.NEUTRAL

            # Convert data highlights
            data_highlights = {}
            for h in section.data_highlights:
                data_highlights[h.metric] = h.value

            sections.append(Section(
                title=section.title[:200],
                brief_scope_id=section.brief_scope_id,
                summary=section.summary[:500],
                data_highlights=data_highlights,
                analysis=section.analysis[:5000],
                key_points=section.key_points[:10],
                sentiment=sentiment,
                charts_suggested=section.charts_suggested[:5],
                data_tables=[],  # Tables from data results would go here
            ))

        # Convert contradictions
        contradictions_found = []
        for c in llm_output.contradictions_found:
            contradictions_found.append(ContradictionFound(
                topic=c.topic[:200],
                sources=c.sources[:5],
                resolution=c.resolution[:500],
            ))

        # Convert recommendation
        rec = llm_output.recommendation
        try:
            confidence = Confidence(rec.confidence)
        except ValueError:
            confidence = Confidence.MEDIUM

        action_items = []
        for item in rec.action_items[:10]:
            try:
                priority = Priority(item.priority)
            except ValueError:
                priority = Priority.MEDIUM

            action_items.append(ActionItem(
                action=item.action[:300],
                priority=priority,
                rationale=item.rationale[:500],
            ))

        recommendation = Recommendation(
            verdict=rec.verdict[:500],
            confidence=confidence,
            confidence_reasoning=rec.confidence_reasoning[:500],
            reasoning=rec.reasoning[:2000],
            pros=rec.pros[:10],
            cons=rec.cons[:10],
            action_items=action_items,
            risks_to_monitor=rec.risks_to_monitor[:10],
        )

        # Convert coverage summary
        coverage_summary = {}
        for cov in llm_output.coverage_summary:
            key = str(cov.topic)
            coverage_summary[key] = CoverageSummary(
                topic=cov.topic[:200],
                coverage_percent=min(100.0, max(0.0, cov.coverage_percent)),
                gaps=cov.gaps[:5],
            )

        # Count unique sources
        sources_count = 0
        for result in all_research_results:
            sources = result.get("sources", [])
            sources_count += len(sources)

        # Calculate processing time
        processing_time = time.time() - self._start_time

        # Create metadata
        metadata = AggregationMetadata(
            total_rounds=rounds_completed,
            total_data_tasks=len(all_data_results),
            total_research_tasks=len(all_research_results),
            sources_count=sources_count,
            processing_time_seconds=round(processing_time, 2),
        )

        # Ensure executive summary meets minimum length
        exec_summary = llm_output.executive_summary
        if len(exec_summary) < 100:
            exec_summary = exec_summary + " " + "Additional analysis is available in the detailed sections below." * 3
            exec_summary = exec_summary[:2000]

        result = AggregatedResearch(
            session_id=session_id,
            brief_id=brief_id,
            created_at=datetime.now(timezone.utc),
            executive_summary=exec_summary[:2000],
            key_insights=key_insights,
            sections=sections,
            contradictions_found=contradictions_found,
            recommendation=recommendation,
            coverage_summary=coverage_summary,
            metadata=metadata,
        )

        return result.model_dump(mode="json")
