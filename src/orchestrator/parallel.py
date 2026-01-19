"""
Ralph Deep Research - Parallel Executor

Coordinates parallel execution of Data and Research agents.
Based on specs/ARCHITECTURE.md Section 5.

Why this module:
- Data and Research agents can run concurrently for faster rounds
- Handles individual task failures gracefully without blocking other tasks
- Collects follow-up questions from all completed results
- Enforces round timeouts to prevent infinite execution

Usage:
    executor = ParallelExecutor(data_agent, research_agent)
    data_results, research_results = await executor.execute_round(
        data_tasks=data_tasks,
        research_tasks=research_tasks,
        context={"session_id": "sess_123", "round": 1, ...},
        timeout=300,
    )
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from src.api.schemas import (
    DataResult,
    DataTask,
    Question,
    ResearchResult,
    ResearchTask,
    TaskStatus,
)
from src.config.timeouts import get_timeout, SCALABILITY_LIMITS
from src.tools.errors import (
    AgentTimeoutError,
    RalphError,
    TransientError,
)
from src.tools.logging import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# =============================================================================
# CUSTOM ERRORS
# =============================================================================


class RoundTimeoutError(TransientError):
    """
    Round execution timed out.

    Why separate: Allows retry logic to distinguish between
    task-level and round-level timeouts.
    """

    def __init__(
        self,
        message: str = "Round execution timed out",
        timeout_seconds: int | None = None,
        completed_tasks: int = 0,
        total_tasks: int = 0,
    ) -> None:
        super().__init__(
            message=message,
            code="ROUND_TIMEOUT",
            details={
                "timeout_seconds": timeout_seconds,
                "completed_tasks": completed_tasks,
                "total_tasks": total_tasks,
            },
        )
        self.timeout_seconds = timeout_seconds
        self.completed_tasks = completed_tasks
        self.total_tasks = total_tasks


class TaskExecutionError(RalphError):
    """
    Error during individual task execution.

    Why: Wraps task-specific errors for aggregation.
    """

    def __init__(
        self,
        message: str,
        task_id: str,
        task_type: str,
        original_error: Exception | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="TASK_EXECUTION_ERROR",
            details={
                "task_id": task_id,
                "task_type": task_type,
                "original_error": str(original_error) if original_error else None,
            },
            recoverable=isinstance(original_error, TransientError),
        )
        self.task_id = task_id
        self.task_type = task_type
        self.original_error = original_error


# =============================================================================
# PARALLEL EXECUTOR
# =============================================================================


class ParallelExecutor:
    """
    Executes Data and Research agents in parallel.

    Why this design:
    - Uses asyncio.gather() with return_exceptions=True for concurrent execution
    - Individual task failures don't block other tasks
    - Collects partial results even if some tasks fail
    - Enforces configurable round timeout

    Pattern:
    1. Create async tasks for all data and research tasks
    2. Run all tasks concurrently via asyncio.gather()
    3. Separate successful results from failures
    4. Return partial results on timeout
    """

    def __init__(
        self,
        data_agent: Any,  # DataAgent type
        research_agent: Any,  # ResearchAgent type
    ) -> None:
        """
        Initialize parallel executor.

        Args:
            data_agent: DataAgent instance for data collection
            research_agent: ResearchAgent instance for qualitative research
        """
        self._data_agent = data_agent
        self._research_agent = research_agent

        # Statistics tracking
        self._stats = {
            "rounds_executed": 0,
            "total_data_tasks": 0,
            "total_research_tasks": 0,
            "successful_data_tasks": 0,
            "successful_research_tasks": 0,
            "failed_tasks": 0,
            "timeouts": 0,
        }

    async def execute_round(
        self,
        data_tasks: list[dict[str, Any]] | list[DataTask],
        research_tasks: list[dict[str, Any]] | list[ResearchTask],
        context: dict[str, Any],
        timeout: int | None = None,
    ) -> tuple[list[DataResult], list[ResearchResult]]:
        """
        Execute a round of data and research tasks in parallel.

        Args:
            data_tasks: List of DataTask objects or dicts
            research_tasks: List of ResearchTask objects or dicts
            context: Shared context including session_id, round, entity_context
            timeout: Round timeout in seconds (default: from config)

        Returns:
            Tuple of (data_results, research_results)

        Raises:
            RoundTimeoutError: If round times out (partial results available)
        """
        if timeout is None:
            timeout = get_timeout("round_timeout")

        session_id = context.get("session_id", "unknown")
        current_round = context.get("round", 1)

        total_tasks = len(data_tasks) + len(research_tasks)

        logger.info(
            "Starting parallel round execution",
            session_id=session_id,
            round=current_round,
            data_tasks=len(data_tasks),
            research_tasks=len(research_tasks),
            timeout=timeout,
        )

        # Validate task counts
        max_tasks_per_round = SCALABILITY_LIMITS.get("max_tasks_per_round", 10)
        if total_tasks > max_tasks_per_round:
            logger.warning(
                "Task count exceeds limit",
                total_tasks=total_tasks,
                limit=max_tasks_per_round,
            )

        # Update stats
        self._stats["rounds_executed"] += 1
        self._stats["total_data_tasks"] += len(data_tasks)
        self._stats["total_research_tasks"] += len(research_tasks)

        start_time = _utc_now()

        try:
            # Execute with timeout
            data_results, research_results = await asyncio.wait_for(
                self._execute_tasks(data_tasks, research_tasks, context),
                timeout=timeout,
            )

            # Update success stats
            self._stats["successful_data_tasks"] += len([r for r in data_results if r.status == TaskStatus.DONE])
            self._stats["successful_research_tasks"] += len([r for r in research_results if r.status == TaskStatus.DONE])

            execution_time = (_utc_now() - start_time).total_seconds()

            logger.info(
                "Round execution completed",
                session_id=session_id,
                round=current_round,
                data_results=len(data_results),
                research_results=len(research_results),
                execution_time_seconds=execution_time,
            )

            return data_results, research_results

        except asyncio.TimeoutError:
            self._stats["timeouts"] += 1
            execution_time = (_utc_now() - start_time).total_seconds()

            logger.warning(
                "Round execution timed out",
                session_id=session_id,
                round=current_round,
                timeout=timeout,
                execution_time_seconds=execution_time,
            )

            # Return empty results on timeout
            # In production, we could track partial results
            raise RoundTimeoutError(
                message=f"Round {current_round} timed out after {timeout} seconds",
                timeout_seconds=timeout,
                completed_tasks=0,  # Would need to track partial completion
                total_tasks=total_tasks,
            )

    async def _execute_tasks(
        self,
        data_tasks: list[dict[str, Any]] | list[DataTask],
        research_tasks: list[dict[str, Any]] | list[ResearchTask],
        context: dict[str, Any],
    ) -> tuple[list[DataResult], list[ResearchResult]]:
        """
        Execute all tasks concurrently.

        Uses asyncio.gather() with return_exceptions=True to capture
        all results (including exceptions) without blocking.
        """
        session_id = context.get("session_id", "unknown")
        current_round = context.get("round", 1)
        entity_context = context.get("entity_context", {})
        brief_context = context.get("brief_context", {})
        previous_findings = context.get("previous_findings", [])
        available_apis = context.get("available_apis", ["financial_api", "web_search"])

        # Create coroutines for all data tasks
        data_coros = [
            self._execute_data_task(
                task=task,
                session_id=session_id,
                round_num=current_round,
                entity_context=entity_context,
                available_apis=available_apis,
            )
            for task in data_tasks
        ]

        # Create coroutines for all research tasks
        research_coros = [
            self._execute_research_task(
                task=task,
                session_id=session_id,
                round_num=current_round,
                entity_context=entity_context,
                brief_context=brief_context,
                previous_findings=previous_findings,
            )
            for task in research_tasks
        ]

        # Execute all tasks concurrently
        all_results = await asyncio.gather(
            *data_coros,
            *research_coros,
            return_exceptions=True,
        )

        # Separate data and research results
        data_results: list[DataResult] = []
        research_results: list[ResearchResult] = []

        num_data_tasks = len(data_tasks)

        for i, result in enumerate(all_results):
            if i < num_data_tasks:
                # Data task result
                if isinstance(result, DataResult):
                    data_results.append(result)
                elif isinstance(result, Exception):
                    # Create failed result
                    task = data_tasks[i]
                    task_id = task.get("id") if isinstance(task, dict) else task.id
                    data_results.append(self._create_failed_data_result(
                        task_id=task_id,
                        round_num=current_round,
                        error=result,
                    ))
                    self._stats["failed_tasks"] += 1
            else:
                # Research task result
                research_idx = i - num_data_tasks
                if isinstance(result, ResearchResult):
                    research_results.append(result)
                elif isinstance(result, Exception):
                    # Create failed result
                    task = research_tasks[research_idx]
                    task_id = task.get("id") if isinstance(task, dict) else task.id
                    research_results.append(self._create_failed_research_result(
                        task_id=task_id,
                        round_num=current_round,
                        error=result,
                    ))
                    self._stats["failed_tasks"] += 1

        return data_results, research_results

    async def _execute_data_task(
        self,
        task: dict[str, Any] | DataTask,
        session_id: str,
        round_num: int,
        entity_context: dict[str, Any],
        available_apis: list[str],
    ) -> DataResult:
        """Execute a single data task."""
        task_dict = task if isinstance(task, dict) else task.model_dump()
        task_id = task_dict.get("id", "unknown")

        logger.debug(
            "Executing data task",
            session_id=session_id,
            task_id=task_id,
            round=round_num,
        )

        try:
            result = await self._data_agent.run(
                session_id=session_id,
                context={
                    "session_id": session_id,
                    "task": task_dict,
                    "entity_context": entity_context,
                    "available_apis": available_apis,
                    "round": round_num,
                },
            )
            return result

        except Exception as e:
            logger.error(
                "Data task failed",
                session_id=session_id,
                task_id=task_id,
                error=str(e),
            )
            raise TaskExecutionError(
                message=f"Data task {task_id} failed: {e}",
                task_id=task_id,
                task_type="data",
                original_error=e,
            )

    async def _execute_research_task(
        self,
        task: dict[str, Any] | ResearchTask,
        session_id: str,
        round_num: int,
        entity_context: dict[str, Any],
        brief_context: dict[str, Any],
        previous_findings: list[str],
    ) -> ResearchResult:
        """Execute a single research task."""
        task_dict = task if isinstance(task, dict) else task.model_dump()
        task_id = task_dict.get("id", "unknown")

        logger.debug(
            "Executing research task",
            session_id=session_id,
            task_id=task_id,
            round=round_num,
        )

        try:
            result = await self._research_agent.run(
                session_id=session_id,
                context={
                    "session_id": session_id,
                    "task": task_dict,
                    "entity_context": entity_context,
                    "brief_context": brief_context,
                    "previous_findings": previous_findings,
                    "round": round_num,
                },
            )
            return result

        except Exception as e:
            logger.error(
                "Research task failed",
                session_id=session_id,
                task_id=task_id,
                error=str(e),
            )
            raise TaskExecutionError(
                message=f"Research task {task_id} failed: {e}",
                task_id=task_id,
                task_type="research",
                original_error=e,
            )

    def _create_failed_data_result(
        self,
        task_id: str,
        round_num: int,
        error: Exception,
    ) -> DataResult:
        """Create a failed DataResult for error tracking."""
        return DataResult(
            task_id=task_id,
            round=round_num,
            status=TaskStatus.FAILED,
            metrics={},
            tables=[],
            raw_data=None,
            metadata=None,
            questions=[],
            errors=[{
                "field": "execution",
                "error": str(error),
                "fallback": None,
            }],
            completed_at=_utc_now(),
        )

    def _create_failed_research_result(
        self,
        task_id: str,
        round_num: int,
        error: Exception,
    ) -> ResearchResult:
        """Create a failed ResearchResult for error tracking."""
        return ResearchResult(
            task_id=task_id,
            round=round_num,
            status=TaskStatus.FAILED,
            summary=f"Task failed: {error}",
            key_findings=[],
            detailed_analysis="",
            themes=[],
            contradictions=[],
            sources=[],
            questions=[],
            completed_at=_utc_now(),
        )

    def collect_questions(
        self,
        data_results: list[DataResult],
        research_results: list[ResearchResult],
    ) -> list[Question]:
        """
        Collect all follow-up questions from task results.

        Args:
            data_results: Results from Data agent
            research_results: Results from Research agent

        Returns:
            List of all follow-up questions
        """
        questions: list[Question] = []

        for result in data_results:
            if hasattr(result, "questions") and result.questions:
                questions.extend(result.questions)

        for result in research_results:
            if hasattr(result, "questions") and result.questions:
                questions.extend(result.questions)

        logger.debug(
            "Collected follow-up questions",
            data_questions=sum(len(r.questions) if hasattr(r, "questions") else 0 for r in data_results),
            research_questions=sum(len(r.questions) if hasattr(r, "questions") else 0 for r in research_results),
            total=len(questions),
        )

        return questions

    def get_stats(self) -> dict[str, int]:
        """
        Get execution statistics.

        Returns:
            Dictionary with execution metrics
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset execution statistics."""
        self._stats = {
            "rounds_executed": 0,
            "total_data_tasks": 0,
            "total_research_tasks": 0,
            "successful_data_tasks": 0,
            "successful_research_tasks": 0,
            "failed_tasks": 0,
            "timeouts": 0,
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================


def create_parallel_executor(
    data_agent: Any,
    research_agent: Any,
) -> ParallelExecutor:
    """
    Create a parallel executor instance.

    Args:
        data_agent: DataAgent instance
        research_agent: ResearchAgent instance

    Returns:
        Configured ParallelExecutor
    """
    return ParallelExecutor(data_agent, research_agent)
