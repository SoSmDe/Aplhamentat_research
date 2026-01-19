"""
Ralph Deep Research - Research Pipeline

Coordinates all agents through the complete research workflow.
Based on specs/ARCHITECTURE.md Section 2.

Why this module:
- Orchestrates the full research pipeline from query to reports
- Implements state machine transitions with crash recovery
- Follows Ralph Pattern: state saved after each operation
- Enforces scalability limits (rounds, tasks, storage)

State Flow:
CREATED → INITIAL_RESEARCH → BRIEF ↔ (revisions) → PLANNING →
EXECUTING ↔ REVIEW (loop) → AGGREGATING → REPORTING → DONE
(Any state → FAILED on error)

Usage:
    pipeline = ResearchPipeline(
        session_manager=session_manager,
        initial_research_agent=initial_research_agent,
        brief_builder_agent=brief_builder_agent,
        planner_agent=planner_agent,
        data_agent=data_agent,
        research_agent=research_agent,
        aggregator_agent=aggregator_agent,
        reporter_agent=reporter_agent,
    )

    # Start new research
    response = await pipeline.start_session("user_123", "Research Realty Income")

    # Continue brief building
    response = await pipeline.process_message(session_id, "5 years horizon")

    # Approve brief to start research
    response = await pipeline.approve_brief(session_id)

    # Check status
    status = await pipeline.get_status(session_id)

    # Get results
    results = await pipeline.get_results(session_id)
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from src.api.schemas import (
    AggregatedResearch,
    Brief,
    BriefBuilderAction,
    BriefStatus,
    DataResult,
    OutputFormat,
    PlannerDecisionStatus,
    ProgressInfo,
    ReportInfo,
    ResearchResult,
    ResultsResponse,
    Session,
    SessionError,
    SessionResponse,
    SessionStatus,
    StatusResponse,
)
from src.config.timeouts import get_timeout, SCALABILITY_LIMITS
from src.orchestrator.parallel import ParallelExecutor, RoundTimeoutError
from src.storage.session import DataType, SessionManager
from src.tools.errors import (
    BriefNotApprovedError,
    InvalidInputError,
    PermanentError,
    RalphError,
    SessionFailedError,
    SessionNotFoundError,
)
from src.tools.logging import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# =============================================================================
# PIPELINE ERRORS
# =============================================================================


class PipelineError(RalphError):
    """Base error for pipeline-specific issues."""

    def __init__(
        self,
        message: str,
        code: str = "PIPELINE_ERROR",
        session_id: str | None = None,
        **kwargs,
    ) -> None:
        super().__init__(message=message, code=code, **kwargs)
        self.session_id = session_id


class InvalidStateTransitionError(PipelineError):
    """Attempted invalid state transition."""

    def __init__(
        self,
        message: str,
        current_state: SessionStatus,
        attempted_state: SessionStatus,
        session_id: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="INVALID_STATE_TRANSITION",
            session_id=session_id,
            details={
                "current_state": current_state.value,
                "attempted_state": attempted_state.value,
            },
        )
        self.current_state = current_state
        self.attempted_state = attempted_state


class MaxRoundsExceededError(PipelineError):
    """Maximum research rounds reached."""

    def __init__(
        self,
        message: str = "Maximum research rounds exceeded",
        session_id: str | None = None,
        max_rounds: int = 10,
    ) -> None:
        super().__init__(
            message=message,
            code="MAX_ROUNDS_EXCEEDED",
            session_id=session_id,
            details={"max_rounds": max_rounds},
        )


# =============================================================================
# VALID STATE TRANSITIONS
# =============================================================================

# Define which states can transition to which other states
VALID_TRANSITIONS: dict[SessionStatus, set[SessionStatus]] = {
    SessionStatus.CREATED: {SessionStatus.INITIAL_RESEARCH, SessionStatus.FAILED},
    SessionStatus.INITIAL_RESEARCH: {SessionStatus.BRIEF, SessionStatus.FAILED},
    SessionStatus.BRIEF: {SessionStatus.APPROVED, SessionStatus.FAILED},
    SessionStatus.APPROVED: {SessionStatus.PLANNING, SessionStatus.FAILED},
    SessionStatus.PLANNING: {SessionStatus.EXECUTING, SessionStatus.FAILED},
    SessionStatus.EXECUTING: {SessionStatus.REVIEW, SessionStatus.FAILED},
    SessionStatus.REVIEW: {SessionStatus.EXECUTING, SessionStatus.AGGREGATING, SessionStatus.FAILED},
    SessionStatus.AGGREGATING: {SessionStatus.REPORTING, SessionStatus.FAILED},
    SessionStatus.REPORTING: {SessionStatus.DONE, SessionStatus.FAILED},
    SessionStatus.DONE: set(),  # Terminal state
    SessionStatus.FAILED: set(),  # Terminal state
}


# =============================================================================
# RESEARCH PIPELINE
# =============================================================================


class ResearchPipeline:
    """
    Coordinates the full research workflow.

    Why this design:
    - Single entry point for all pipeline operations
    - State machine ensures valid transitions
    - Ralph Pattern: saves state after each operation
    - Supports session recovery from any point

    Features:
    - Start new research sessions
    - Interactive brief building
    - Parallel execution of data/research tasks
    - Adaptive looping based on coverage
    - Report generation in multiple formats
    """

    def __init__(
        self,
        session_manager: SessionManager,
        initial_research_agent: Any,  # InitialResearchAgent
        brief_builder_agent: Any,  # BriefBuilderAgent
        planner_agent: Any,  # PlannerAgent
        data_agent: Any,  # DataAgent
        research_agent: Any,  # ResearchAgent
        aggregator_agent: Any,  # AggregatorAgent
        reporter_agent: Any,  # ReporterAgent
        file_storage: Any = None,  # FileStorage (optional)
    ) -> None:
        """
        Initialize research pipeline.

        Args:
            session_manager: For state persistence
            initial_research_agent: Quick context gathering
            brief_builder_agent: Interactive specification
            planner_agent: Task decomposition and coverage
            data_agent: Structured data collection
            research_agent: Qualitative analysis
            aggregator_agent: Synthesis and recommendations
            reporter_agent: Report generation
            file_storage: Optional file storage for reports
        """
        self._session_manager = session_manager
        self._initial_research = initial_research_agent
        self._brief_builder = brief_builder_agent
        self._planner = planner_agent
        self._data_agent = data_agent
        self._research_agent = research_agent
        self._aggregator = aggregator_agent
        self._reporter = reporter_agent
        self._file_storage = file_storage

        # Create parallel executor
        self._parallel_executor = ParallelExecutor(
            data_agent=data_agent,
            research_agent=research_agent,
        )

        # Scalability limits from config
        self._max_rounds = SCALABILITY_LIMITS.get("max_rounds_per_session", 10)
        self._max_tasks_per_round = SCALABILITY_LIMITS.get("max_tasks_per_round", 10)
        self._min_coverage = SCALABILITY_LIMITS.get("min_coverage_percent", 80)

    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================

    async def start_session(
        self,
        user_id: str,
        initial_query: str,
    ) -> SessionResponse:
        """
        Start a new research session.

        Creates session, runs Initial Research, and returns first Brief Builder response.

        Args:
            user_id: User identifier
            initial_query: User's research query

        Returns:
            SessionResponse with session_id and first message
        """
        # Create session
        session = await self._session_manager.create_session(user_id, initial_query)
        session_id = session.id

        logger.info(
            "Starting new research session",
            session_id=session_id,
            user_id=user_id,
            query_length=len(initial_query),
        )

        try:
            # Run Initial Research
            initial_context = await self._run_initial_research(session_id, initial_query)

            # Transition to BRIEF state
            await self._transition_to(session_id, SessionStatus.BRIEF)

            # Get first Brief Builder response
            response = await self._run_brief_building(
                session_id=session_id,
                initial_context=initial_context,
                user_message=None,  # First message from Brief Builder
            )

            return response

        except Exception as e:
            await self._handle_error(session_id, e)
            raise

    async def process_message(
        self,
        session_id: str,
        content: str,
    ) -> SessionResponse:
        """
        Process a message during brief building.

        Args:
            session_id: Session identifier
            content: User message content

        Returns:
            SessionResponse with Brief Builder response
        """
        session = await self._get_session_or_fail(session_id)

        # Validate state
        if session.status not in {SessionStatus.BRIEF}:
            raise InvalidStateTransitionError(
                message=f"Cannot send message in state {session.status.value}",
                current_state=session.status,
                attempted_state=SessionStatus.BRIEF,
                session_id=session_id,
            )

        logger.info(
            "Processing user message",
            session_id=session_id,
            content_length=len(content),
        )

        try:
            # Get initial context
            initial_context = await self._session_manager.get_state(
                session_id, DataType.INITIAL_CONTEXT
            )

            # Run Brief Builder
            response = await self._run_brief_building(
                session_id=session_id,
                initial_context=initial_context,
                user_message=content,
            )

            return response

        except Exception as e:
            await self._handle_error(session_id, e)
            raise

    async def approve_brief(
        self,
        session_id: str,
        modifications: dict[str, Any] | None = None,
    ) -> SessionResponse:
        """
        Approve the Brief and start research execution.

        Args:
            session_id: Session identifier
            modifications: Optional modifications to the Brief

        Returns:
            SessionResponse with execution status
        """
        session = await self._get_session_or_fail(session_id)

        # Validate state
        if session.status != SessionStatus.BRIEF:
            raise InvalidStateTransitionError(
                message=f"Cannot approve brief in state {session.status.value}",
                current_state=session.status,
                attempted_state=SessionStatus.APPROVED,
                session_id=session_id,
            )

        logger.info(
            "Approving brief",
            session_id=session_id,
            has_modifications=modifications is not None,
        )

        try:
            # Get current brief
            brief_data = await self._session_manager.get_state(session_id, DataType.BRIEF)

            if not brief_data:
                raise BriefNotApprovedError(
                    message="No brief found to approve",
                    session_id=session_id,
                )

            # Apply modifications if provided
            if modifications:
                brief_data.update(modifications)
                await self._session_manager.save_state(
                    session_id, DataType.BRIEF, brief_data
                )

            # Mark brief as approved
            brief_data["status"] = BriefStatus.APPROVED.value
            brief_data["approved_at"] = _utc_now().isoformat()
            await self._session_manager.save_state(session_id, DataType.BRIEF, brief_data)

            # Transition to APPROVED
            await self._transition_to(session_id, SessionStatus.APPROVED)

            # Start research execution in background
            asyncio.create_task(self._run_research_execution(session_id, brief_data))

            return SessionResponse(
                session_id=session_id,
                status=SessionStatus.APPROVED,
                action=None,
                message="Brief approved. Research execution started.",
                brief=Brief.model_validate(brief_data) if brief_data else None,
            )

        except Exception as e:
            await self._handle_error(session_id, e)
            raise

    async def get_status(self, session_id: str) -> StatusResponse:
        """
        Get current session status.

        Args:
            session_id: Session identifier

        Returns:
            StatusResponse with current status and progress
        """
        session = await self._get_session_or_fail(session_id)

        # Get progress info if executing
        progress = None
        coverage = None

        if session.status in {
            SessionStatus.EXECUTING,
            SessionStatus.REVIEW,
            SessionStatus.AGGREGATING,
        }:
            progress = await self._get_progress(session_id)
            coverage = await self._get_coverage(session_id)

        return StatusResponse(
            session_id=session_id,
            status=session.status,
            current_round=session.current_round,
            progress=progress,
            coverage=coverage,
            error=session.error,
        )

    async def get_results(self, session_id: str) -> ResultsResponse:
        """
        Get research results.

        Args:
            session_id: Session identifier

        Returns:
            ResultsResponse with aggregated research and reports
        """
        session = await self._get_session_or_fail(session_id)

        # Can only get results in terminal states or after aggregation
        if session.status not in {
            SessionStatus.AGGREGATING,
            SessionStatus.REPORTING,
            SessionStatus.DONE,
        }:
            return ResultsResponse(
                session_id=session_id,
                status=session.status,
                aggregated=None,
                reports=[],
            )

        # Get aggregated research
        aggregated_data = await self._session_manager.get_state(
            session_id, DataType.AGGREGATION
        )

        aggregated = None
        if aggregated_data:
            try:
                aggregated = AggregatedResearch.model_validate(aggregated_data)
            except Exception as e:
                logger.warning(
                    "Failed to parse aggregated research",
                    session_id=session_id,
                    error=str(e),
                )

        # Get report files
        reports = await self._get_reports(session_id)

        return ResultsResponse(
            session_id=session_id,
            status=session.status,
            aggregated=aggregated,
            reports=reports,
        )

    async def resume_session(self, session_id: str) -> SessionResponse:
        """
        Resume a session from its current state.

        Useful for crash recovery - picks up from last saved state.

        Args:
            session_id: Session identifier

        Returns:
            SessionResponse with current state info
        """
        session = await self._get_session_or_fail(session_id)

        logger.info(
            "Resuming session",
            session_id=session_id,
            current_status=session.status.value,
        )

        # Handle based on current state
        if session.status == SessionStatus.BRIEF:
            # Return to brief building
            initial_context = await self._session_manager.get_state(
                session_id, DataType.INITIAL_CONTEXT
            )
            return await self._run_brief_building(
                session_id=session_id,
                initial_context=initial_context,
                user_message=None,
            )

        elif session.status in {
            SessionStatus.APPROVED,
            SessionStatus.PLANNING,
            SessionStatus.EXECUTING,
            SessionStatus.REVIEW,
        }:
            # Resume research execution
            brief_data = await self._session_manager.get_state(
                session_id, DataType.BRIEF
            )
            asyncio.create_task(self._run_research_execution(session_id, brief_data))

            return SessionResponse(
                session_id=session_id,
                status=session.status,
                action=None,
                message="Research execution resumed.",
                brief=Brief.model_validate(brief_data) if brief_data else None,
            )

        elif session.status in {SessionStatus.DONE, SessionStatus.FAILED}:
            # Terminal state - just return current status
            return SessionResponse(
                session_id=session_id,
                status=session.status,
                action=None,
                message=f"Session in terminal state: {session.status.value}",
                brief=None,
            )

        else:
            # For other states, return current status
            return SessionResponse(
                session_id=session_id,
                status=session.status,
                action=None,
                message=f"Session state: {session.status.value}",
                brief=None,
            )

    # =========================================================================
    # INTERNAL METHODS - PIPELINE STAGES
    # =========================================================================

    async def _run_initial_research(
        self,
        session_id: str,
        initial_query: str,
    ) -> dict[str, Any]:
        """Run Initial Research agent."""
        await self._transition_to(session_id, SessionStatus.INITIAL_RESEARCH)

        result = await self._initial_research.run(
            session_id=session_id,
            context={
                "session_id": session_id,
                "user_query": initial_query,
            },
        )

        logger.info(
            "Initial research completed",
            session_id=session_id,
            entities=len(result.get("entities", [])) if isinstance(result, dict) else 0,
        )

        return result if isinstance(result, dict) else result.model_dump()

    async def _run_brief_building(
        self,
        session_id: str,
        initial_context: dict[str, Any] | None,
        user_message: str | None,
    ) -> SessionResponse:
        """Run Brief Builder agent."""
        # Get conversation history
        conversation = await self._session_manager.get_all_states(
            session_id, DataType.CONVERSATION
        )

        # Get current brief (may be in progress)
        current_brief = await self._session_manager.get_state(
            session_id, DataType.BRIEF
        )

        result = await self._brief_builder.run(
            session_id=session_id,
            context={
                "session_id": session_id,
                "initial_context": initial_context,
                "conversation_history": conversation,
                "current_brief": current_brief,
                "user_message": user_message,
            },
        )

        # Parse result
        action = result.get("action", BriefBuilderAction.ASK_QUESTION)
        if isinstance(action, str):
            try:
                action = BriefBuilderAction(action)
            except ValueError:
                action = BriefBuilderAction.ASK_QUESTION

        message = result.get("message", "")
        brief_data = result.get("current_brief")

        # Handle different actions
        if action == BriefBuilderAction.BRIEF_APPROVED:
            # Auto-transition to approved state
            if brief_data:
                brief_data["status"] = BriefStatus.APPROVED.value
                brief_data["approved_at"] = _utc_now().isoformat()
                await self._session_manager.save_state(
                    session_id, DataType.BRIEF, brief_data
                )

        session = await self._session_manager.get_session(session_id)

        return SessionResponse(
            session_id=session_id,
            status=session.status,
            action=action,
            message=message,
            brief=Brief.model_validate(brief_data) if brief_data else None,
        )

    async def _run_research_execution(
        self,
        session_id: str,
        brief_data: dict[str, Any],
    ) -> None:
        """
        Run the full research execution loop.

        This is the main research loop:
        1. Planning - create initial tasks
        2. Execute tasks in parallel
        3. Review coverage
        4. Loop back if coverage < threshold
        5. Aggregate results
        6. Generate reports
        """
        try:
            # Transition to PLANNING
            await self._transition_to(session_id, SessionStatus.PLANNING)

            # Get entity context from initial research
            initial_context = await self._session_manager.get_state(
                session_id, DataType.INITIAL_CONTEXT
            ) or {}

            entity_context = {
                "entities": initial_context.get("entities", []),
                "context_summary": initial_context.get("context_summary", ""),
            }

            brief_context = {
                "goal": brief_data.get("goal", ""),
                "user_context": brief_data.get("user_context", {}),
                "constraints": brief_data.get("constraints", {}),
            }

            # Initial planning
            plan = await self._run_planning(
                session_id=session_id,
                brief_data=brief_data,
                mode="initial",
            )

            current_round = 1
            all_data_results: list[dict] = []
            all_research_results: list[dict] = []

            # Research loop
            while current_round <= self._max_rounds:
                logger.info(
                    "Starting research round",
                    session_id=session_id,
                    round=current_round,
                )

                # Update round counter
                await self._session_manager.increment_round(session_id)

                # Transition to EXECUTING
                await self._transition_to(session_id, SessionStatus.EXECUTING)

                # Execute round
                data_results, research_results = await self._parallel_executor.execute_round(
                    data_tasks=plan.get("data_tasks", []),
                    research_tasks=plan.get("research_tasks", []),
                    context={
                        "session_id": session_id,
                        "round": current_round,
                        "entity_context": entity_context,
                        "brief_context": brief_context,
                        "previous_findings": self._extract_findings(all_research_results),
                        "available_apis": ["financial_api", "web_search"],
                    },
                )

                # Collect results
                all_data_results.extend(
                    r.model_dump() if hasattr(r, "model_dump") else r
                    for r in data_results
                )
                all_research_results.extend(
                    r.model_dump() if hasattr(r, "model_dump") else r
                    for r in research_results
                )

                # Collect follow-up questions
                new_questions = self._parallel_executor.collect_questions(
                    data_results, research_results
                )

                # Transition to REVIEW
                await self._transition_to(session_id, SessionStatus.REVIEW)

                # Run Planner review
                decision = await self._run_planning(
                    session_id=session_id,
                    brief_data=brief_data,
                    mode="review",
                    round_num=current_round,
                    data_results=all_data_results,
                    research_results=all_research_results,
                    new_questions=new_questions,
                )

                # Check decision
                decision_status = decision.get("status", "continue")
                if isinstance(decision_status, str):
                    try:
                        decision_status = PlannerDecisionStatus(decision_status)
                    except ValueError:
                        decision_status = PlannerDecisionStatus.CONTINUE

                overall_coverage = decision.get("overall_coverage", 0)

                logger.info(
                    "Round review completed",
                    session_id=session_id,
                    round=current_round,
                    decision=decision_status.value,
                    coverage=overall_coverage,
                )

                if decision_status == PlannerDecisionStatus.DONE:
                    break

                # Prepare next round
                current_round += 1
                plan = {
                    "data_tasks": decision.get("new_data_tasks", []),
                    "research_tasks": decision.get("new_research_tasks", []),
                }

                # Check if any tasks for next round
                if not plan["data_tasks"] and not plan["research_tasks"]:
                    logger.info(
                        "No more tasks to execute",
                        session_id=session_id,
                    )
                    break

            # Aggregation
            await self._transition_to(session_id, SessionStatus.AGGREGATING)
            aggregated = await self._run_aggregation(
                session_id=session_id,
                brief_data=brief_data,
                data_results=all_data_results,
                research_results=all_research_results,
                rounds_completed=current_round,
            )

            # Reporting
            await self._transition_to(session_id, SessionStatus.REPORTING)
            await self._run_reporting(
                session_id=session_id,
                aggregated=aggregated,
                output_formats=brief_data.get("output_formats", [OutputFormat.PDF]),
            )

            # Done!
            await self._transition_to(session_id, SessionStatus.DONE)

            logger.info(
                "Research execution completed",
                session_id=session_id,
                total_rounds=current_round,
                data_results=len(all_data_results),
                research_results=len(all_research_results),
            )

        except Exception as e:
            logger.error(
                "Research execution failed",
                session_id=session_id,
                error=str(e),
            )
            await self._handle_error(session_id, e)

    async def _run_planning(
        self,
        session_id: str,
        brief_data: dict[str, Any],
        mode: str,
        round_num: int = 1,
        data_results: list[dict] | None = None,
        research_results: list[dict] | None = None,
        new_questions: list | None = None,
    ) -> dict[str, Any]:
        """Run Planner agent."""
        context = {
            "session_id": session_id,
            "mode": mode,
            "brief": brief_data,
        }

        if mode == "review":
            context.update({
                "round": round_num,
                "data_results": data_results or [],
                "research_results": research_results or [],
                "new_questions": [
                    q.model_dump() if hasattr(q, "model_dump") else q
                    for q in (new_questions or [])
                ],
            })

        result = await self._planner.run(
            session_id=session_id,
            context=context,
        )

        return result if isinstance(result, dict) else result.model_dump()

    async def _run_aggregation(
        self,
        session_id: str,
        brief_data: dict[str, Any],
        data_results: list[dict],
        research_results: list[dict],
        rounds_completed: int,
    ) -> dict[str, Any]:
        """Run Aggregator agent."""
        result = await self._aggregator.run(
            session_id=session_id,
            context={
                "session_id": session_id,
                "brief": brief_data,
                "data_results": data_results,
                "research_results": research_results,
                "rounds_completed": rounds_completed,
            },
        )

        return result if isinstance(result, dict) else result.model_dump()

    async def _run_reporting(
        self,
        session_id: str,
        aggregated: dict[str, Any],
        output_formats: list[OutputFormat | str],
    ) -> dict[str, Any]:
        """Run Reporter agent."""
        # Normalize output formats
        formats = []
        for fmt in output_formats:
            if isinstance(fmt, str):
                try:
                    formats.append(OutputFormat(fmt))
                except ValueError:
                    formats.append(OutputFormat.PDF)
            else:
                formats.append(fmt)

        result = await self._reporter.run(
            session_id=session_id,
            context={
                "session_id": session_id,
                "aggregated": aggregated,
                "formats": [f.value for f in formats],
            },
        )

        return result if isinstance(result, dict) else result.model_dump()

    # =========================================================================
    # INTERNAL METHODS - STATE MANAGEMENT
    # =========================================================================

    async def _transition_to(
        self,
        session_id: str,
        new_status: SessionStatus,
    ) -> None:
        """
        Transition session to new state.

        Validates transition is allowed.
        """
        session = await self._session_manager.get_session(session_id)
        current_status = session.status

        # Check if transition is valid
        valid_next = VALID_TRANSITIONS.get(current_status, set())
        if new_status not in valid_next:
            raise InvalidStateTransitionError(
                message=f"Cannot transition from {current_status.value} to {new_status.value}",
                current_state=current_status,
                attempted_state=new_status,
                session_id=session_id,
            )

        await self._session_manager.update_status(session_id, new_status)

        logger.debug(
            "State transition",
            session_id=session_id,
            from_state=current_status.value,
            to_state=new_status.value,
        )

    async def _get_session_or_fail(self, session_id: str) -> Session:
        """Get session or raise error."""
        session = await self._session_manager.get_session(session_id)

        if session.status == SessionStatus.FAILED:
            raise SessionFailedError(
                message="Session is in failed state",
                session_id=session_id,
            )

        return session

    async def _handle_error(
        self,
        session_id: str,
        error: Exception,
    ) -> None:
        """Handle pipeline error - set session to FAILED."""
        error_data = SessionError(
            code=getattr(error, "code", "PIPELINE_ERROR"),
            message=str(error),
            details=getattr(error, "details", None),
            recoverable=isinstance(error, RoundTimeoutError),
        )

        await self._session_manager.set_error(session_id, error_data)

        logger.error(
            "Pipeline error",
            session_id=session_id,
            error_code=error_data.code,
            error_message=error_data.message,
        )

    # =========================================================================
    # INTERNAL METHODS - UTILITIES
    # =========================================================================

    async def _get_progress(self, session_id: str) -> ProgressInfo | None:
        """Get progress information."""
        session = await self._session_manager.get_session(session_id)

        # Get current plan
        plan_data = await self._session_manager.get_state(
            session_id, DataType.PLAN, round=session.current_round
        )

        if not plan_data:
            return None

        # Count completed tasks
        data_results = await self._session_manager.get_all_states(
            session_id, DataType.DATA_RESULT
        )
        research_results = await self._session_manager.get_all_states(
            session_id, DataType.RESEARCH_RESULT
        )

        return ProgressInfo(
            data_tasks_completed=len(data_results),
            data_tasks_total=len(plan_data.get("data_tasks", [])),
            research_tasks_completed=len(research_results),
            research_tasks_total=len(plan_data.get("research_tasks", [])),
            current_round=session.current_round,
            max_rounds=self._max_rounds,
        )

    async def _get_coverage(self, session_id: str) -> dict[str, float] | None:
        """Get coverage information from latest planner decision."""
        decisions = await self._session_manager.get_all_states(
            session_id, DataType.PLANNER_DECISION
        )

        if not decisions:
            return None

        # Get latest decision
        latest = decisions[-1] if decisions else None
        if not latest:
            return None

        coverage = latest.get("coverage", {})
        return {
            topic: item.get("coverage_percent", 0)
            for topic, item in coverage.items()
        }

    async def _get_reports(self, session_id: str) -> list[ReportInfo]:
        """Get list of generated reports."""
        if not self._file_storage:
            return []

        try:
            files = await self._file_storage.list_files(session_id)
            reports = []

            for file_info in files:
                fmt_str = file_info.get("file_type", "pdf")
                try:
                    fmt = OutputFormat(fmt_str)
                except ValueError:
                    fmt = OutputFormat.PDF

                reports.append(ReportInfo(
                    format=fmt,
                    url=file_info.get("url", f"/files/{session_id}/{file_info.get('filename', '')}"),
                    filename=file_info.get("filename", "report"),
                    size_bytes=file_info.get("file_size", 0),
                ))

            return reports
        except Exception as e:
            logger.warning(
                "Failed to list reports",
                session_id=session_id,
                error=str(e),
            )
            return []

    def _extract_findings(self, research_results: list[dict]) -> list[str]:
        """Extract key findings from research results for context."""
        findings = []
        for result in research_results:
            for finding in result.get("key_findings", []):
                if isinstance(finding, dict):
                    findings.append(finding.get("finding", ""))
                elif isinstance(finding, str):
                    findings.append(finding)
        return findings[:50]  # Limit to prevent context bloat


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_research_pipeline(
    session_manager: SessionManager,
    initial_research_agent: Any,
    brief_builder_agent: Any,
    planner_agent: Any,
    data_agent: Any,
    research_agent: Any,
    aggregator_agent: Any,
    reporter_agent: Any,
    file_storage: Any = None,
) -> ResearchPipeline:
    """
    Create a research pipeline instance.

    Args:
        session_manager: For state persistence
        initial_research_agent: InitialResearchAgent instance
        brief_builder_agent: BriefBuilderAgent instance
        planner_agent: PlannerAgent instance
        data_agent: DataAgent instance
        research_agent: ResearchAgent instance
        aggregator_agent: AggregatorAgent instance
        reporter_agent: ReporterAgent instance
        file_storage: Optional FileStorage instance

    Returns:
        Configured ResearchPipeline
    """
    return ResearchPipeline(
        session_manager=session_manager,
        initial_research_agent=initial_research_agent,
        brief_builder_agent=brief_builder_agent,
        planner_agent=planner_agent,
        data_agent=data_agent,
        research_agent=research_agent,
        aggregator_agent=aggregator_agent,
        reporter_agent=reporter_agent,
        file_storage=file_storage,
    )
