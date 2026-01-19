"""
Tests for ParallelExecutor.

Why these tests:
- ParallelExecutor coordinates concurrent Data and Research agent execution
- Must handle individual task failures gracefully
- Must enforce round timeouts
- Must collect follow-up questions from all results

Test Categories:
1. Initialization - Agent setup
2. Successful execution - Happy path with all tasks succeeding
3. Partial failures - Some tasks fail, others succeed
4. Timeouts - Round-level timeout handling
5. Question collection - Gathering follow-up questions
6. Statistics tracking - Execution metrics
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.schemas import (
    DataResult,
    Question,
    QuestionType,
    ResearchResult,
    TaskStatus,
    Priority,
)
from src.orchestrator.parallel import (
    ParallelExecutor,
    RoundTimeoutError,
    TaskExecutionError,
    create_parallel_executor,
)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_data_agent():
    """Create a mock DataAgent."""
    agent = AsyncMock()
    agent.run = AsyncMock()
    return agent


@pytest.fixture
def mock_research_agent():
    """Create a mock ResearchAgent."""
    agent = AsyncMock()
    agent.run = AsyncMock()
    return agent


@pytest.fixture
def executor(mock_data_agent, mock_research_agent):
    """Create ParallelExecutor with mocked agents."""
    return ParallelExecutor(
        data_agent=mock_data_agent,
        research_agent=mock_research_agent,
    )


@pytest.fixture
def sample_data_tasks():
    """Sample data tasks for testing."""
    return [
        {
            "id": "d1",
            "scope_item_id": 1,
            "description": "Collect financial metrics",
            "source": "financial_api",
            "priority": "high",
        },
        {
            "id": "d2",
            "scope_item_id": 2,
            "description": "Get market data",
            "source": "web_search",
            "priority": "medium",
        },
    ]


@pytest.fixture
def sample_research_tasks():
    """Sample research tasks for testing."""
    return [
        {
            "id": "r1",
            "scope_item_id": 1,
            "description": "Analyze business model",
            "focus": "Revenue streams",
            "source_types": ["news", "reports"],
            "priority": "high",
        },
        {
            "id": "r2",
            "scope_item_id": 2,
            "description": "Research competitors",
            "focus": "Market position",
            "source_types": ["company_website"],
            "priority": "medium",
        },
    ]


@pytest.fixture
def sample_context():
    """Sample execution context."""
    return {
        "session_id": "sess_test123",
        "round": 1,
        "entity_context": {"name": "Test Company", "ticker": "TEST"},
        "brief_context": {"goal": "Analyze Test Company"},
        "previous_findings": [],
        "available_apis": ["financial_api", "web_search"],
    }


def create_data_result(task_id: str, round_num: int = 1, status: TaskStatus = TaskStatus.DONE):
    """Helper to create DataResult."""
    return DataResult(
        task_id=task_id,
        round=round_num,
        status=status,
        metrics={"test_metric": {"value": 100, "unit": "USD"}},
        tables=[],
        questions=[],
        errors=[],
    )


def create_research_result(task_id: str, round_num: int = 1, status: TaskStatus = TaskStatus.DONE):
    """Helper to create ResearchResult."""
    return ResearchResult(
        task_id=task_id,
        round=round_num,
        status=status,
        summary="Test summary",
        key_findings=[],
        detailed_analysis="",
        themes=[],
        contradictions=[],
        sources=[],
        questions=[],
    )


# =============================================================================
# TEST: INITIALIZATION
# =============================================================================


class TestParallelExecutorInit:
    """Test ParallelExecutor initialization."""

    def test_init_with_agents(self, mock_data_agent, mock_research_agent):
        """Test initialization with agents."""
        executor = ParallelExecutor(
            data_agent=mock_data_agent,
            research_agent=mock_research_agent,
        )

        assert executor._data_agent is mock_data_agent
        assert executor._research_agent is mock_research_agent

    def test_init_stats(self, executor):
        """Test initial statistics are zero."""
        stats = executor.get_stats()

        assert stats["rounds_executed"] == 0
        assert stats["total_data_tasks"] == 0
        assert stats["total_research_tasks"] == 0
        assert stats["successful_data_tasks"] == 0
        assert stats["successful_research_tasks"] == 0
        assert stats["failed_tasks"] == 0
        assert stats["timeouts"] == 0

    def test_factory_function(self, mock_data_agent, mock_research_agent):
        """Test create_parallel_executor factory."""
        executor = create_parallel_executor(
            data_agent=mock_data_agent,
            research_agent=mock_research_agent,
        )

        assert isinstance(executor, ParallelExecutor)


# =============================================================================
# TEST: SUCCESSFUL EXECUTION
# =============================================================================


class TestSuccessfulExecution:
    """Test successful round execution."""

    @pytest.mark.asyncio
    async def test_execute_round_success(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test successful execution of all tasks."""
        # Setup mocks
        mock_data_agent.run.side_effect = [
            create_data_result("d1"),
            create_data_result("d2"),
        ]
        mock_research_agent.run.side_effect = [
            create_research_result("r1"),
            create_research_result("r2"),
        ]

        # Execute
        data_results, research_results = await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        # Verify
        assert len(data_results) == 2
        assert len(research_results) == 2
        assert all(r.status == TaskStatus.DONE for r in data_results)
        assert all(r.status == TaskStatus.DONE for r in research_results)

    @pytest.mark.asyncio
    async def test_execute_round_empty_tasks(self, executor, sample_context):
        """Test execution with no tasks."""
        data_results, research_results = await executor.execute_round(
            data_tasks=[],
            research_tasks=[],
            context=sample_context,
        )

        assert len(data_results) == 0
        assert len(research_results) == 0

    @pytest.mark.asyncio
    async def test_execute_round_data_only(
        self,
        executor,
        mock_data_agent,
        sample_data_tasks,
        sample_context,
    ):
        """Test execution with only data tasks."""
        mock_data_agent.run.side_effect = [
            create_data_result("d1"),
            create_data_result("d2"),
        ]

        data_results, research_results = await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=[],
            context=sample_context,
        )

        assert len(data_results) == 2
        assert len(research_results) == 0

    @pytest.mark.asyncio
    async def test_execute_round_research_only(
        self,
        executor,
        mock_research_agent,
        sample_research_tasks,
        sample_context,
    ):
        """Test execution with only research tasks."""
        mock_research_agent.run.side_effect = [
            create_research_result("r1"),
            create_research_result("r2"),
        ]

        data_results, research_results = await executor.execute_round(
            data_tasks=[],
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        assert len(data_results) == 0
        assert len(research_results) == 2


# =============================================================================
# TEST: PARTIAL FAILURES
# =============================================================================


class TestPartialFailures:
    """Test handling of partial task failures."""

    @pytest.mark.asyncio
    async def test_data_task_failure_continues(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test that data task failure doesn't block others."""
        # First data task fails, second succeeds
        mock_data_agent.run.side_effect = [
            Exception("API Error"),
            create_data_result("d2"),
        ]
        mock_research_agent.run.side_effect = [
            create_research_result("r1"),
            create_research_result("r2"),
        ]

        data_results, research_results = await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        # Should still get all results (one failed)
        assert len(data_results) == 2
        assert len(research_results) == 2

        # Check failed task
        failed_result = next(r for r in data_results if r.task_id == "d1")
        assert failed_result.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_research_task_failure_continues(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test that research task failure doesn't block others."""
        mock_data_agent.run.side_effect = [
            create_data_result("d1"),
            create_data_result("d2"),
        ]
        # First research task fails
        mock_research_agent.run.side_effect = [
            Exception("Search Error"),
            create_research_result("r2"),
        ]

        data_results, research_results = await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        assert len(data_results) == 2
        assert len(research_results) == 2

        # Check failed task
        failed_result = next(r for r in research_results if r.task_id == "r1")
        assert failed_result.status == TaskStatus.FAILED

    @pytest.mark.asyncio
    async def test_all_tasks_fail(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test handling when all tasks fail."""
        mock_data_agent.run.side_effect = Exception("All fail")
        mock_research_agent.run.side_effect = Exception("All fail")

        data_results, research_results = await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        # Should still get failed results for all tasks
        assert len(data_results) == 2
        assert len(research_results) == 2
        assert all(r.status == TaskStatus.FAILED for r in data_results)
        assert all(r.status == TaskStatus.FAILED for r in research_results)


# =============================================================================
# TEST: TIMEOUTS
# =============================================================================


class TestTimeouts:
    """Test timeout handling."""

    @pytest.mark.asyncio
    async def test_round_timeout(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test round-level timeout."""
        # Make tasks take too long
        async def slow_task(*args, **kwargs):
            await asyncio.sleep(10)
            return create_data_result("d1")

        mock_data_agent.run.side_effect = slow_task
        mock_research_agent.run.side_effect = slow_task

        # Use very short timeout
        with pytest.raises(RoundTimeoutError) as exc_info:
            await executor.execute_round(
                data_tasks=sample_data_tasks,
                research_tasks=sample_research_tasks,
                context=sample_context,
                timeout=1,  # 1 second timeout
            )

        assert exc_info.value.timeout_seconds == 1
        assert "timed out" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_updates_stats(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test that timeout updates statistics."""
        async def slow_task(*args, **kwargs):
            await asyncio.sleep(10)
            return create_data_result("d1")

        mock_data_agent.run.side_effect = slow_task
        mock_research_agent.run.side_effect = slow_task

        try:
            await executor.execute_round(
                data_tasks=sample_data_tasks,
                research_tasks=sample_research_tasks,
                context=sample_context,
                timeout=1,
            )
        except RoundTimeoutError:
            pass

        stats = executor.get_stats()
        assert stats["timeouts"] == 1


# =============================================================================
# TEST: QUESTION COLLECTION
# =============================================================================


class TestQuestionCollection:
    """Test follow-up question collection."""

    def test_collect_questions_from_data(self, executor):
        """Test collecting questions from data results."""
        data_results = [
            DataResult(
                task_id="d1",
                round=1,
                status=TaskStatus.DONE,
                metrics={},
                tables=[],
                questions=[
                    Question(
                        type=QuestionType.RESEARCH,
                        question="What caused this metric spike?",
                        priority=Priority.HIGH,
                    ),
                ],
                errors=[],
            ),
        ]

        questions = executor.collect_questions(data_results, [])

        assert len(questions) == 1
        assert questions[0].question == "What caused this metric spike?"

    def test_collect_questions_from_research(self, executor):
        """Test collecting questions from research results."""
        research_results = [
            ResearchResult(
                task_id="r1",
                round=1,
                status=TaskStatus.DONE,
                summary="Test",
                key_findings=[],
                detailed_analysis="",
                themes=[],
                contradictions=[],
                sources=[],
                questions=[
                    Question(
                        type=QuestionType.DATA,
                        question="What are the exact revenue figures?",
                        priority=Priority.MEDIUM,
                    ),
                ],
            ),
        ]

        questions = executor.collect_questions([], research_results)

        assert len(questions) == 1
        assert questions[0].question == "What are the exact revenue figures?"

    def test_collect_questions_from_both(self, executor):
        """Test collecting questions from both agent types."""
        data_results = [
            DataResult(
                task_id="d1",
                round=1,
                status=TaskStatus.DONE,
                metrics={},
                tables=[],
                questions=[
                    Question(
                        type=QuestionType.RESEARCH,
                        question="Data question 1",
                        priority=Priority.HIGH,
                    ),
                ],
                errors=[],
            ),
        ]

        research_results = [
            ResearchResult(
                task_id="r1",
                round=1,
                status=TaskStatus.DONE,
                summary="Test",
                key_findings=[],
                detailed_analysis="",
                themes=[],
                contradictions=[],
                sources=[],
                questions=[
                    Question(
                        type=QuestionType.DATA,
                        question="Research question 1",
                        priority=Priority.MEDIUM,
                    ),
                    Question(
                        type=QuestionType.DATA,
                        question="Research question 2",
                        priority=Priority.LOW,
                    ),
                ],
            ),
        ]

        questions = executor.collect_questions(data_results, research_results)

        assert len(questions) == 3

    def test_collect_questions_empty(self, executor):
        """Test collecting with no questions."""
        data_results = [create_data_result("d1")]
        research_results = [create_research_result("r1")]

        questions = executor.collect_questions(data_results, research_results)

        assert len(questions) == 0


# =============================================================================
# TEST: STATISTICS
# =============================================================================


class TestStatistics:
    """Test statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_updated_on_success(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test statistics are updated on successful execution."""
        mock_data_agent.run.side_effect = [
            create_data_result("d1"),
            create_data_result("d2"),
        ]
        mock_research_agent.run.side_effect = [
            create_research_result("r1"),
            create_research_result("r2"),
        ]

        await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        stats = executor.get_stats()
        assert stats["rounds_executed"] == 1
        assert stats["total_data_tasks"] == 2
        assert stats["total_research_tasks"] == 2
        assert stats["successful_data_tasks"] == 2
        assert stats["successful_research_tasks"] == 2
        assert stats["failed_tasks"] == 0

    @pytest.mark.asyncio
    async def test_stats_count_failures(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_data_tasks,
        sample_research_tasks,
        sample_context,
    ):
        """Test statistics count failed tasks."""
        mock_data_agent.run.side_effect = [
            Exception("Fail"),
            create_data_result("d2"),
        ]
        mock_research_agent.run.side_effect = [
            create_research_result("r1"),
            Exception("Fail"),
        ]

        await executor.execute_round(
            data_tasks=sample_data_tasks,
            research_tasks=sample_research_tasks,
            context=sample_context,
        )

        stats = executor.get_stats()
        assert stats["failed_tasks"] == 2

    def test_reset_stats(self, executor):
        """Test statistics reset."""
        # Manually set some stats
        executor._stats["rounds_executed"] = 5
        executor._stats["failed_tasks"] = 3

        executor.reset_stats()

        stats = executor.get_stats()
        assert stats["rounds_executed"] == 0
        assert stats["failed_tasks"] == 0


# =============================================================================
# TEST: ERROR TYPES
# =============================================================================


class TestErrorTypes:
    """Test custom error types."""

    def test_round_timeout_error(self):
        """Test RoundTimeoutError attributes."""
        error = RoundTimeoutError(
            message="Test timeout",
            timeout_seconds=300,
            completed_tasks=5,
            total_tasks=10,
        )

        assert error.timeout_seconds == 300
        assert error.completed_tasks == 5
        assert error.total_tasks == 10
        assert error.code == "ROUND_TIMEOUT"

    def test_task_execution_error(self):
        """Test TaskExecutionError attributes."""
        original = ValueError("Bad value")
        error = TaskExecutionError(
            message="Task failed",
            task_id="d1",
            task_type="data",
            original_error=original,
        )

        assert error.task_id == "d1"
        assert error.task_type == "data"
        assert error.original_error is original
        assert error.code == "TASK_EXECUTION_ERROR"


# =============================================================================
# TEST: CONCURRENCY
# =============================================================================


class TestConcurrency:
    """Test concurrent execution behavior."""

    @pytest.mark.asyncio
    async def test_tasks_run_concurrently(
        self,
        executor,
        mock_data_agent,
        mock_research_agent,
        sample_context,
    ):
        """Test that tasks actually run in parallel."""
        execution_times = []

        async def track_time(task_id, delay=0.1):
            start = asyncio.get_event_loop().time()
            await asyncio.sleep(delay)
            end = asyncio.get_event_loop().time()
            execution_times.append((task_id, start, end))
            if task_id.startswith("d"):
                return create_data_result(task_id)
            return create_research_result(task_id)

        # Setup 4 tasks that each take 0.1s
        mock_data_agent.run.side_effect = [
            track_time("d1"),
            track_time("d2"),
        ]
        mock_research_agent.run.side_effect = [
            track_time("r1"),
            track_time("r2"),
        ]

        data_tasks = [{"id": "d1"}, {"id": "d2"}]
        research_tasks = [{"id": "r1"}, {"id": "r2"}]

        start_time = asyncio.get_event_loop().time()
        await executor.execute_round(
            data_tasks=data_tasks,
            research_tasks=research_tasks,
            context=sample_context,
        )
        total_time = asyncio.get_event_loop().time() - start_time

        # If sequential, would take ~0.4s. Parallel should be ~0.1s
        # Use generous margin for test stability
        assert total_time < 0.3, "Tasks should run concurrently"
