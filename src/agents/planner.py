"""
Ralph Deep Research - Planner Agent

Strategic research coordinator that decomposes Briefs into executable tasks
and manages research cycles by tracking coverage.

Based on specs/PROMPTS.md Section 3.

Why this agent:
- Transforms user-approved Brief into concrete Data and Research tasks
- Manages research cycles (max 10 rounds)
- Tracks coverage per scope item (80% threshold)
- Filters follow-up questions by relevance
- Ensures comprehensive research before completion

Two Modes:
1. Initial Planning: Brief -> Plan with DataTasks and ResearchTasks
2. Review: Results -> Coverage assessment -> Continue/Done decision

Timeout: 20 seconds (target: 10 seconds)

Usage:
    agent = PlannerAgent(llm_client, session_manager)

    # Initial planning
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "mode": "initial",
        "brief": {...}
    })

    # Review mode
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "mode": "review",
        "brief": {...},
        "round": 1,
        "data_results": [...],
        "research_results": [...],
        "all_questions": [...]
    })
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    Brief,
    CoverageItem,
    DataSource,
    DataTask,
    FilteredQuestion,
    FilteredQuestionAction,
    Plan,
    PlannerDecision,
    PlannerDecisionStatus,
    Priority,
    Confidence,
    ResearchTask,
    ScopeItem,
    ScopeType,
    SourceType,
    TaskStatus,
)
from src.config.settings import get_settings
from src.storage.session import DataType
from src.tools.errors import InvalidInputError


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE - INITIAL PLANNING
# =============================================================================


class LLMDataTask(BaseModel):
    """Data task from LLM response."""
    id: str = Field(description="Task ID in format d1, d2, etc")
    scope_item_id: int = Field(description="Reference to Brief scope item")
    description: str = Field(description="What data to collect")
    source: str = Field(description="financial_api|web_search|custom_api|database")
    priority: str = Field(default="medium", description="high|medium|low")
    expected_output: str | None = Field(default=None, description="Expected data description")


class LLMResearchTask(BaseModel):
    """Research task from LLM response."""
    id: str = Field(description="Task ID in format r1, r2, etc")
    scope_item_id: int = Field(description="Reference to Brief scope item")
    description: str = Field(description="Research task description")
    focus: str | None = Field(default=None, description="What to focus on")
    source_types: list[str] = Field(default_factory=list, description="news|reports|company_website|analyst_reports|sec_filings")
    priority: str = Field(default="medium", description="high|medium|low")
    search_queries: list[str] = Field(default_factory=list, description="Suggested search queries")


class LLMPlanOutput(BaseModel):
    """Initial plan output from LLM."""
    round: int = Field(default=1, description="Round number")
    brief_id: str = Field(description="Brief ID")
    data_tasks: list[LLMDataTask] = Field(default_factory=list)
    research_tasks: list[LLMResearchTask] = Field(default_factory=list)
    total_tasks: int = Field(default=0)
    estimated_duration_seconds: int | None = Field(default=None)


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE - REVIEW MODE
# =============================================================================


class LLMCoverageItem(BaseModel):
    """Coverage assessment for a scope item."""
    topic: str = Field(description="Scope item topic")
    coverage_percent: float = Field(ge=0, le=100, description="Coverage percentage")
    covered_aspects: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


class LLMFilteredQuestion(BaseModel):
    """Filtered question from LLM."""
    question: str = Field(description="The question text")
    source_task_id: str = Field(description="Task that generated this question")
    relevance: str = Field(description="high|medium|low")
    action: str = Field(description="add|skip")
    reasoning: str = Field(description="Why this decision")


class LLMPlannerDecisionOutput(BaseModel):
    """Planner decision output from LLM."""
    round: int = Field(description="Round number reviewed")
    status: str = Field(description="continue|done")
    coverage: dict[str, LLMCoverageItem] = Field(default_factory=dict)
    overall_coverage: float = Field(ge=0, le=100, description="Overall coverage percentage")
    reason: str = Field(description="Explanation for decision")
    new_data_tasks: list[LLMDataTask] = Field(default_factory=list)
    new_research_tasks: list[LLMResearchTask] = Field(default_factory=list)
    filtered_questions: list[LLMFilteredQuestion] = Field(default_factory=list)


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class PlannerAgent(BaseAgent):
    """
    Planner Agent - Strategic research coordinator.

    Decomposes Brief into executable tasks and manages research cycles.

    Modes:
    - initial: Create first plan from Brief
    - review: Assess coverage and decide continue/done

    Rules:
    - Maximum 10 tasks per round
    - Maximum 10 rounds total
    - 80% coverage threshold per scope item for completion
    - Always reference Brief goal when making decisions
    - Avoid duplicate tasks between rounds
    """

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "planner"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "planner"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context

        Raises:
            InvalidInputError: If required fields missing
        """
        super().validate_input(context)

        mode = context.get("mode")
        if mode not in ("initial", "review"):
            raise InvalidInputError(
                message="mode must be 'initial' or 'review'",
                field="mode",
                value=mode,
            )

        if "brief" not in context:
            raise InvalidInputError(
                message="brief is required",
                field="brief",
            )

        if mode == "review":
            if "round" not in context:
                raise InvalidInputError(
                    message="round is required for review mode",
                    field="round",
                )
            if "data_results" not in context:
                raise InvalidInputError(
                    message="data_results is required for review mode",
                    field="data_results",
                )
            if "research_results" not in context:
                raise InvalidInputError(
                    message="research_results is required for review mode",
                    field="research_results",
                )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute planner task based on mode.

        Args:
            context: Input with mode, brief, and mode-specific data

        Returns:
            Plan (initial mode) or PlannerDecision (review mode)
        """
        session_id = context["session_id"]
        mode = context["mode"]
        brief = context["brief"]

        self._logger.info(
            "Planner executing",
            mode=mode,
            brief_id=brief.get("brief_id", "unknown"),
        )

        if mode == "initial":
            return await self._execute_initial_planning(session_id, brief)
        else:
            return await self._execute_review(
                session_id=session_id,
                brief=brief,
                round_num=context["round"],
                data_results=context.get("data_results", []),
                research_results=context.get("research_results", []),
                all_questions=context.get("all_questions", []),
                previous_tasks=context.get("previous_tasks", []),
            )

    async def _execute_initial_planning(
        self,
        session_id: str,
        brief: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Create initial plan from Brief.

        Args:
            session_id: Session ID
            brief: Approved Brief

        Returns:
            Plan as dictionary
        """
        # Build prompt for LLM
        prompt = self._build_initial_planning_prompt(brief)

        # Call LLM for structured output
        try:
            llm_output = await self._call_llm_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMPlanOutput,
                max_tokens=4096,
                temperature=0.3,
            )
            # Ensure brief_id matches
            llm_output.brief_id = brief.get("brief_id", "")

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback",
                error=str(e),
            )
            llm_output = self._create_fallback_plan(brief)

        # Convert to Plan
        plan = self._convert_to_plan(llm_output, round_num=1)

        # Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.PLAN,
            result=plan,
            round=1,
        )

        self._logger.info(
            "Initial plan created",
            data_tasks=len(plan.get("data_tasks", [])),
            research_tasks=len(plan.get("research_tasks", [])),
        )

        return plan

    async def _execute_review(
        self,
        session_id: str,
        brief: dict[str, Any],
        round_num: int,
        data_results: list[dict[str, Any]],
        research_results: list[dict[str, Any]],
        all_questions: list[dict[str, Any]],
        previous_tasks: list[str],
    ) -> dict[str, Any]:
        """
        Review results and decide whether to continue.

        Args:
            session_id: Session ID
            brief: Approved Brief
            round_num: Current round number
            data_results: Results from Data Agent
            research_results: Results from Research Agent
            all_questions: All questions generated by agents
            previous_tasks: List of previous task IDs to avoid duplicates

        Returns:
            PlannerDecision as dictionary
        """
        settings = get_settings()
        max_rounds = settings.max_rounds_per_session

        # Check if we've hit the round limit
        if round_num >= max_rounds:
            self._logger.info(
                "Maximum rounds reached, forcing completion",
                round=round_num,
                max_rounds=max_rounds,
            )
            return self._create_forced_completion_decision(
                round_num=round_num,
                brief=brief,
                reason=f"Maximum rounds ({max_rounds}) reached",
            )

        # Build prompt for LLM
        prompt = self._build_review_prompt(
            brief=brief,
            round_num=round_num,
            data_results=data_results,
            research_results=research_results,
            all_questions=all_questions,
            previous_tasks=previous_tasks,
        )

        # Call LLM for structured output
        try:
            llm_output = await self._call_llm_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMPlannerDecisionOutput,
                max_tokens=4096,
                temperature=0.3,
            )
            llm_output.round = round_num

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback decision",
                error=str(e),
            )
            llm_output = self._create_fallback_decision(
                brief=brief,
                round_num=round_num,
                data_results=data_results,
                research_results=research_results,
            )

        # Convert to PlannerDecision
        decision = self._convert_to_decision(llm_output, round_num, previous_tasks)

        # Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.PLANNER_DECISION,
            result=decision,
            round=round_num,
        )

        self._logger.info(
            "Review completed",
            status=decision["status"],
            overall_coverage=decision["overall_coverage"],
            new_tasks=len(decision.get("new_data_tasks", [])) + len(decision.get("new_research_tasks", [])),
        )

        return decision

    def _build_initial_planning_prompt(self, brief: dict[str, Any]) -> str:
        """Build prompt for initial planning."""
        goal = brief.get("goal", "")
        scope = brief.get("scope", [])
        constraints = brief.get("constraints", {}) or {}

        scope_text = ""
        for item in scope:
            scope_text += f"""
- ID: {item.get('id')}
  Topic: {item.get('topic')}
  Type: {item.get('type')} (data/research/both)
  Priority: {item.get('priority', 'medium')}
  Details: {item.get('details', 'N/A')}
"""

        constraints_text = ""
        if constraints:
            focus = constraints.get("focus_areas", [])
            exclude = constraints.get("exclude", [])
            time_period = constraints.get("time_period", "")
            geo_focus = constraints.get("geographic_focus", "")

            if focus:
                constraints_text += f"Focus areas: {', '.join(focus)}\n"
            if exclude:
                constraints_text += f"Exclude: {', '.join(exclude)}\n"
            if time_period:
                constraints_text += f"Time period: {time_period}\n"
            if geo_focus:
                constraints_text += f"Geographic focus: {geo_focus}\n"

        return f"""## Brief для исследования

**Goal**: {goal}

**Scope Items**:
{scope_text}

**Constraints**:
{constraints_text if constraints_text else "None"}

**Brief ID**: {brief.get('brief_id', '')}

## Инструкции

Создай план исследования для первого раунда:

1. Для каждого scope item создай соответствующие задачи:
   - Если type = "data" → создай DataTask
   - Если type = "research" → создай ResearchTask
   - Если type = "both" → создай и DataTask, и ResearchTask

2. Для DataTask укажи:
   - id в формате d1, d2, d3...
   - source: financial_api, web_search, custom_api, или database
   - description: что именно собрать
   - expected_output: какие данные ожидаем

3. Для ResearchTask укажи:
   - id в формате r1, r2, r3...
   - source_types: news, reports, company_website, analyst_reports, sec_filings
   - focus: на чём сфокусироваться
   - search_queries: 2-3 поисковых запроса

4. Правила:
   - Максимум 10 задач на раунд
   - Приоритет high для критичных задач
   - Задачи должны быть конкретными и выполнимыми

Верни результат в JSON формате."""

    def _build_review_prompt(
        self,
        brief: dict[str, Any],
        round_num: int,
        data_results: list[dict[str, Any]],
        research_results: list[dict[str, Any]],
        all_questions: list[dict[str, Any]],
        previous_tasks: list[str],
    ) -> str:
        """Build prompt for review mode."""
        goal = brief.get("goal", "")
        scope = brief.get("scope", [])

        # Build scope summary
        scope_text = ""
        for item in scope:
            scope_text += f"- [{item.get('id')}] {item.get('topic')} ({item.get('type')})\n"

        # Build data results summary
        data_summary = ""
        for result in data_results:
            task_id = result.get("task_id", "")
            status = result.get("status", "")
            metrics_count = len(result.get("metrics", {}))
            errors_count = len(result.get("errors", []))
            data_summary += f"- {task_id}: status={status}, metrics={metrics_count}, errors={errors_count}\n"

        # Build research results summary
        research_summary = ""
        for result in research_results:
            task_id = result.get("task_id", "")
            status = result.get("status", "")
            findings_count = len(result.get("key_findings", []))
            sources_count = len(result.get("sources", []))
            research_summary += f"- {task_id}: status={status}, findings={findings_count}, sources={sources_count}\n"

        # Build questions list
        questions_text = ""
        for q in all_questions[:20]:  # Limit to 20 questions
            q_type = q.get("type", "research")
            q_text = q.get("question", "")
            source = q.get("source_task_id", "unknown")
            questions_text += f"- [{q_type}] {q_text} (from {source})\n"

        # Build previous tasks list
        prev_tasks_text = ", ".join(previous_tasks) if previous_tasks else "None"

        return f"""## Review раунда {round_num}

**Goal**: {goal}

**Scope Items**:
{scope_text}

**Data Results**:
{data_summary if data_summary else "No data tasks completed"}

**Research Results**:
{research_summary if research_summary else "No research tasks completed"}

**Generated Questions**:
{questions_text if questions_text else "No questions generated"}

**Previous Task IDs** (не дублировать):
{prev_tasks_text}

## Инструкции

1. **Оцени coverage** для каждого scope item:
   - Какие аспекты покрыты?
   - Какие аспекты отсутствуют?
   - Процент покрытия (0-100)

2. **Оцени вопросы**:
   - Релевантность к цели Brief (high/medium/low)
   - Действие: add (создать задачу) или skip (игнорировать)
   - Обоснование решения

3. **Прими решение**:
   - status: "continue" если любой scope item < 80%
   - status: "done" если все scope items >= 80%

4. **Если continue**, создай новые задачи:
   - Задачи должны закрывать missing_aspects
   - Избегай дублирования с previous_tasks
   - Максимум 10 задач на раунд

Верни результат в JSON формате."""

    def _create_fallback_plan(self, brief: dict[str, Any]) -> LLMPlanOutput:
        """Create fallback plan if LLM fails."""
        scope = brief.get("scope", [])
        brief_id = brief.get("brief_id", "")

        data_tasks = []
        research_tasks = []
        data_idx = 1
        research_idx = 1

        for item in scope[:10]:  # Limit to 10 scope items
            scope_id = item.get("id", 1)
            topic = item.get("topic", "")
            scope_type = item.get("type", "both")
            priority = item.get("priority", "medium")

            if scope_type in ("data", "both"):
                data_tasks.append(LLMDataTask(
                    id=f"d{data_idx}",
                    scope_item_id=scope_id,
                    description=f"Collect quantitative data for: {topic}",
                    source="web_search",
                    priority=priority,
                    expected_output=f"Key metrics and data points for {topic}",
                ))
                data_idx += 1

            if scope_type in ("research", "both"):
                research_tasks.append(LLMResearchTask(
                    id=f"r{research_idx}",
                    scope_item_id=scope_id,
                    description=f"Research and analyze: {topic}",
                    focus=f"Key aspects and insights about {topic}",
                    source_types=["news", "reports", "company_website"],
                    priority=priority,
                    search_queries=[topic, f"{topic} analysis"],
                ))
                research_idx += 1

        return LLMPlanOutput(
            round=1,
            brief_id=brief_id,
            data_tasks=data_tasks[:10],
            research_tasks=research_tasks[:10],
            total_tasks=min(len(data_tasks), 10) + min(len(research_tasks), 10),
            estimated_duration_seconds=120,
        )

    def _create_fallback_decision(
        self,
        brief: dict[str, Any],
        round_num: int,
        data_results: list[dict[str, Any]],
        research_results: list[dict[str, Any]],
    ) -> LLMPlannerDecisionOutput:
        """Create fallback decision if LLM fails."""
        scope = brief.get("scope", [])

        # Calculate basic coverage based on completed tasks
        completed_data = sum(1 for r in data_results if r.get("status") == "done")
        completed_research = sum(1 for r in research_results if r.get("status") == "done")
        total_completed = completed_data + completed_research
        total_scope = len(scope)

        # Estimate coverage
        base_coverage = min(100, (total_completed / max(total_scope, 1)) * 50 + 30)

        coverage = {}
        for item in scope:
            scope_id = str(item.get("id", 1))
            topic = item.get("topic", "")
            coverage[scope_id] = LLMCoverageItem(
                topic=topic,
                coverage_percent=base_coverage,
                covered_aspects=["Initial data gathered"] if total_completed > 0 else [],
                missing_aspects=["Detailed analysis needed"] if base_coverage < 80 else [],
            )

        status = "done" if base_coverage >= 80 else "continue"

        return LLMPlannerDecisionOutput(
            round=round_num,
            status=status,
            coverage=coverage,
            overall_coverage=base_coverage,
            reason=f"Coverage at {base_coverage}%, {'completed' if status == 'done' else 'additional research needed'}",
            new_data_tasks=[],
            new_research_tasks=[],
            filtered_questions=[],
        )

    def _create_forced_completion_decision(
        self,
        round_num: int,
        brief: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        """Create forced completion decision when max rounds reached."""
        scope = brief.get("scope", [])

        coverage = {}
        for item in scope:
            scope_id = str(item.get("id", 1))
            topic = item.get("topic", "")
            coverage[scope_id] = CoverageItem(
                topic=topic,
                coverage_percent=100.0,  # Forced to 100%
                covered_aspects=["Research completed within round limit"],
                missing_aspects=[],
            ).model_dump()

        decision = PlannerDecision(
            round=round_num,
            status=PlannerDecisionStatus.DONE,
            coverage={k: CoverageItem(**v) for k, v in coverage.items()},
            overall_coverage=100.0,
            reason=reason,
            new_data_tasks=[],
            new_research_tasks=[],
            filtered_questions=[],
        )

        return decision.model_dump(mode="json")

    def _convert_to_plan(
        self,
        llm_output: LLMPlanOutput,
        round_num: int,
    ) -> dict[str, Any]:
        """Convert LLM output to Plan dictionary."""
        # Convert data tasks
        data_tasks = []
        for task in llm_output.data_tasks[:10]:
            try:
                source = DataSource(task.source)
            except ValueError:
                source = DataSource.WEB_SEARCH

            try:
                priority = Priority(task.priority)
            except ValueError:
                priority = Priority.MEDIUM

            data_task = DataTask(
                id=task.id,
                scope_item_id=task.scope_item_id,
                description=task.description[:500],
                source=source,
                priority=priority,
                expected_output=task.expected_output[:500] if task.expected_output else None,
                status=TaskStatus.PENDING,
            )
            data_tasks.append(data_task)

        # Convert research tasks
        research_tasks = []
        for task in llm_output.research_tasks[:10]:
            try:
                priority = Priority(task.priority)
            except ValueError:
                priority = Priority.MEDIUM

            source_types = []
            for st in task.source_types:
                try:
                    source_types.append(SourceType(st))
                except ValueError:
                    pass
            if not source_types:
                source_types = [SourceType.NEWS, SourceType.REPORTS]

            research_task = ResearchTask(
                id=task.id,
                scope_item_id=task.scope_item_id,
                description=task.description[:500],
                focus=task.focus[:200] if task.focus else None,
                source_types=source_types,
                priority=priority,
                status=TaskStatus.PENDING,
                search_queries=task.search_queries[:5],
            )
            research_tasks.append(research_task)

        # Enforce max 10 total tasks
        total = len(data_tasks) + len(research_tasks)
        if total > 10:
            # Prioritize by priority, then keep balanced
            high_data = [t for t in data_tasks if t.priority == Priority.HIGH]
            high_research = [t for t in research_tasks if t.priority == Priority.HIGH]
            other_data = [t for t in data_tasks if t.priority != Priority.HIGH]
            other_research = [t for t in research_tasks if t.priority != Priority.HIGH]

            # Keep all high priority, then balance the rest
            remaining = 10 - len(high_data) - len(high_research)
            if remaining > 0:
                split = remaining // 2
                data_tasks = high_data + other_data[:split]
                research_tasks = high_research + other_research[:remaining - split]
            else:
                data_tasks = high_data[:5]
                research_tasks = high_research[:5]

        plan = Plan(
            round=round_num,
            brief_id=llm_output.brief_id,
            data_tasks=data_tasks,
            research_tasks=research_tasks,
            total_tasks=len(data_tasks) + len(research_tasks),
            estimated_duration_seconds=llm_output.estimated_duration_seconds,
        )

        return plan.model_dump(mode="json")

    def _convert_to_decision(
        self,
        llm_output: LLMPlannerDecisionOutput,
        round_num: int,
        previous_tasks: list[str],
    ) -> dict[str, Any]:
        """Convert LLM output to PlannerDecision dictionary."""
        # Convert status
        try:
            status = PlannerDecisionStatus(llm_output.status)
        except ValueError:
            status = PlannerDecisionStatus.CONTINUE

        # Convert coverage
        coverage = {}
        for scope_id, item in llm_output.coverage.items():
            coverage[scope_id] = CoverageItem(
                topic=item.topic,
                coverage_percent=item.coverage_percent,
                covered_aspects=item.covered_aspects,
                missing_aspects=item.missing_aspects,
            )

        # Convert filtered questions
        filtered_questions = []
        for q in llm_output.filtered_questions:
            try:
                relevance = Confidence(q.relevance)
            except ValueError:
                relevance = Confidence.MEDIUM

            try:
                action = FilteredQuestionAction(q.action)
            except ValueError:
                action = FilteredQuestionAction.SKIP

            filtered_questions.append(FilteredQuestion(
                question=q.question[:300],
                source_task_id=q.source_task_id,
                relevance=relevance,
                action=action,
                reasoning=q.reasoning[:500],
            ))

        # Generate new task IDs avoiding duplicates
        existing_data_ids = [t for t in previous_tasks if t.startswith("d")]
        existing_research_ids = [t for t in previous_tasks if t.startswith("r")]
        next_data_idx = max([int(t[1:]) for t in existing_data_ids] + [0]) + 1
        next_research_idx = max([int(t[1:]) for t in existing_research_ids] + [0]) + 1

        # Convert new data tasks
        new_data_tasks = []
        for task in llm_output.new_data_tasks[:10]:
            # Check if this task ID already exists
            task_id = task.id
            if task_id in previous_tasks:
                task_id = f"d{next_data_idx}"
                next_data_idx += 1

            try:
                source = DataSource(task.source)
            except ValueError:
                source = DataSource.WEB_SEARCH

            try:
                priority = Priority(task.priority)
            except ValueError:
                priority = Priority.MEDIUM

            new_data_tasks.append(DataTask(
                id=task_id,
                scope_item_id=task.scope_item_id,
                description=task.description[:500],
                source=source,
                priority=priority,
                expected_output=task.expected_output[:500] if task.expected_output else None,
                status=TaskStatus.PENDING,
            ))

        # Convert new research tasks
        new_research_tasks = []
        for task in llm_output.new_research_tasks[:10]:
            task_id = task.id
            if task_id in previous_tasks:
                task_id = f"r{next_research_idx}"
                next_research_idx += 1

            try:
                priority = Priority(task.priority)
            except ValueError:
                priority = Priority.MEDIUM

            source_types = []
            for st in task.source_types:
                try:
                    source_types.append(SourceType(st))
                except ValueError:
                    pass
            if not source_types:
                source_types = [SourceType.NEWS, SourceType.REPORTS]

            new_research_tasks.append(ResearchTask(
                id=task_id,
                scope_item_id=task.scope_item_id,
                description=task.description[:500],
                focus=task.focus[:200] if task.focus else None,
                source_types=source_types,
                priority=priority,
                status=TaskStatus.PENDING,
                search_queries=task.search_queries[:5],
            ))

        # Enforce max 10 new tasks
        total_new = len(new_data_tasks) + len(new_research_tasks)
        if total_new > 10:
            new_data_tasks = new_data_tasks[:5]
            new_research_tasks = new_research_tasks[:5]

        decision = PlannerDecision(
            round=round_num,
            status=status,
            coverage=coverage,
            overall_coverage=llm_output.overall_coverage,
            reason=llm_output.reason[:1000],
            new_data_tasks=new_data_tasks,
            new_research_tasks=new_research_tasks,
            filtered_questions=filtered_questions,
        )

        return decision.model_dump(mode="json")
