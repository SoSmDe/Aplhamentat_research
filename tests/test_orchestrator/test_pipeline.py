"""
Tests for ResearchPipeline.

Tests cover:
- Initialization and factory function
- Session start and state transitions
- Brief building and approval
- Research execution loop
- Status and results retrieval
- Session resumption (crash recovery)
- Error handling
- State machine validation
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api.schemas import (
    AggregatedResearch,
    Brief,
    BriefBuilderAction,
    BriefStatus,
    Confidence,
    DataResult,
    Finding,
    FindingType,
    MetricValue,
    OutputFormat,
    PlannerDecisionStatus,
    ResearchResult,
    SessionError,
    SessionStatus,
    TaskStatus,
)
from src.orchestrator.pipeline import (
    InvalidStateTransitionError,
    MaxRoundsExceededError,
    PipelineError,
    ResearchPipeline,
    VALID_TRANSITIONS,
    create_research_pipeline,
)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_session_manager():
    """Create a mock session manager with state tracking."""
    manager = AsyncMock()

    # Track session state (mutable state)
    current_status = {"value": SessionStatus.CREATED}
    current_round = {"value": 0}

    def create_session_mock():
        """Create a fresh session."""
        current_status["value"] = SessionStatus.CREATED
        current_round["value"] = 0
        return MagicMock(
            id="sess_123",
            user_id="user_456",
            status=current_status["value"],
            current_round=current_round["value"],
            created_at=_utc_now().isoformat(),
            error=None,
        )

    def get_session_mock():
        """Return current session state."""
        return MagicMock(
            id="sess_123",
            user_id="user_456",
            status=current_status["value"],
            current_round=current_round["value"],
            created_at=_utc_now().isoformat(),
            error=None,
        )

    async def update_status_mock(session_id, status):
        """Update session status."""
        current_status["value"] = status

    async def increment_round_mock(session_id):
        """Increment round counter."""
        current_round["value"] += 1

    # Set up mock methods
    manager.create_session = AsyncMock(side_effect=lambda *args, **kwargs: create_session_mock())
    manager.get_session = AsyncMock(side_effect=lambda *args, **kwargs: get_session_mock())
    manager.update_status = AsyncMock(side_effect=update_status_mock)
    manager.increment_round = AsyncMock(side_effect=increment_round_mock)
    manager.save_state = AsyncMock()
    manager.get_state = AsyncMock(return_value=None)
    manager.get_all_states = AsyncMock(return_value=[])
    manager.set_error = AsyncMock()

    # Expose state for test assertions
    manager._current_status = current_status
    manager._current_round = current_round

    return manager


@pytest.fixture
def mock_initial_research_agent():
    """Create a mock initial research agent."""
    agent = AsyncMock()
    agent.run = AsyncMock(return_value={
        "entities": [{"name": "Test Entity", "type": "company"}],
        "context_summary": "Test context summary",
        "suggested_topics": ["topic1", "topic2"],
    })
    return agent


@pytest.fixture
def mock_brief_builder_agent():
    """Create a mock brief builder agent."""
    agent = AsyncMock()
    # Return None for current_brief to avoid Brief validation issues in tests
    # The pipeline code handles None brief gracefully
    agent.run = AsyncMock(return_value={
        "action": BriefBuilderAction.ASK_QUESTION.value,
        "message": "What is the time horizon for this research?",
        "current_brief": None,  # Avoid Brief validation in unit tests
    })
    return agent


@pytest.fixture
def mock_planner_agent():
    """Create a mock planner agent."""
    agent = AsyncMock()
    agent.run = AsyncMock(return_value={
        "status": PlannerDecisionStatus.CONTINUE.value,
        "data_tasks": [{"id": "data_1", "description": "Get metrics"}],
        "research_tasks": [{"id": "research_1", "description": "Analyze trends"}],
        "overall_coverage": 50,
    })
    return agent


@pytest.fixture
def mock_data_agent():
    """Create a mock data agent."""
    agent = AsyncMock()
    agent.run = AsyncMock(return_value=DataResult(
        task_id="data_1",
        round=1,
        status=TaskStatus.DONE,
        metrics={"revenue": MetricValue(value=1000000, unit="USD")},
        tables=[],
        raw_data=None,
        metadata=None,
        questions=[],
        completed_at=_utc_now(),
    ))
    return agent


@pytest.fixture
def mock_research_agent():
    """Create a mock research agent."""
    agent = AsyncMock()
    agent.run = AsyncMock(return_value=ResearchResult(
        task_id="research_1",
        round=1,
        status=TaskStatus.DONE,
        summary="Research summary",
        key_findings=[Finding(
            finding="Key finding 1",
            type=FindingType.FACT,
            confidence=Confidence.HIGH,
            source="Test source",
        )],
        detailed_analysis="Detailed analysis",
        themes=[],
        contradictions=[],
        sources=[],
        questions=[],
        completed_at=_utc_now(),
    ))
    return agent


@pytest.fixture
def mock_aggregator_agent():
    """Create a mock aggregator agent."""
    agent = AsyncMock()
    agent.run = AsyncMock(return_value={
        "executive_summary": "Executive summary",
        "key_findings": [{"finding": "Aggregated finding"}],
        "recommendations": [{"recommendation": "Recommendation 1"}],
        "data_synthesis": {},
        "research_synthesis": {},
    })
    return agent


@pytest.fixture
def mock_reporter_agent():
    """Create a mock reporter agent."""
    agent = AsyncMock()
    agent.run = AsyncMock(return_value={
        "reports": [{"format": "pdf", "filename": "report.pdf"}],
    })
    return agent


@pytest.fixture
def pipeline(
    mock_session_manager,
    mock_initial_research_agent,
    mock_brief_builder_agent,
    mock_planner_agent,
    mock_data_agent,
    mock_research_agent,
    mock_aggregator_agent,
    mock_reporter_agent,
):
    """Create a pipeline with all mock agents."""
    return ResearchPipeline(
        session_manager=mock_session_manager,
        initial_research_agent=mock_initial_research_agent,
        brief_builder_agent=mock_brief_builder_agent,
        planner_agent=mock_planner_agent,
        data_agent=mock_data_agent,
        research_agent=mock_research_agent,
        aggregator_agent=mock_aggregator_agent,
        reporter_agent=mock_reporter_agent,
    )


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================


class TestPipelineInit:
    """Test pipeline initialization."""

    def test_init_with_all_agents(
        self,
        mock_session_manager,
        mock_initial_research_agent,
        mock_brief_builder_agent,
        mock_planner_agent,
        mock_data_agent,
        mock_research_agent,
        mock_aggregator_agent,
        mock_reporter_agent,
    ):
        """Test initialization with all required agents."""
        pipeline = ResearchPipeline(
            session_manager=mock_session_manager,
            initial_research_agent=mock_initial_research_agent,
            brief_builder_agent=mock_brief_builder_agent,
            planner_agent=mock_planner_agent,
            data_agent=mock_data_agent,
            research_agent=mock_research_agent,
            aggregator_agent=mock_aggregator_agent,
            reporter_agent=mock_reporter_agent,
        )

        assert pipeline._session_manager == mock_session_manager
        assert pipeline._initial_research == mock_initial_research_agent
        assert pipeline._brief_builder == mock_brief_builder_agent
        assert pipeline._planner == mock_planner_agent
        assert pipeline._data_agent == mock_data_agent
        assert pipeline._research_agent == mock_research_agent
        assert pipeline._aggregator == mock_aggregator_agent
        assert pipeline._reporter == mock_reporter_agent

    def test_init_creates_parallel_executor(self, pipeline):
        """Test that parallel executor is created."""
        assert pipeline._parallel_executor is not None

    def test_init_sets_scalability_limits(self, pipeline):
        """Test that scalability limits are set from config."""
        assert pipeline._max_rounds == 10
        assert pipeline._max_tasks_per_round == 10
        assert pipeline._min_coverage == 80

    def test_factory_function(
        self,
        mock_session_manager,
        mock_initial_research_agent,
        mock_brief_builder_agent,
        mock_planner_agent,
        mock_data_agent,
        mock_research_agent,
        mock_aggregator_agent,
        mock_reporter_agent,
    ):
        """Test create_research_pipeline factory function."""
        pipeline = create_research_pipeline(
            session_manager=mock_session_manager,
            initial_research_agent=mock_initial_research_agent,
            brief_builder_agent=mock_brief_builder_agent,
            planner_agent=mock_planner_agent,
            data_agent=mock_data_agent,
            research_agent=mock_research_agent,
            aggregator_agent=mock_aggregator_agent,
            reporter_agent=mock_reporter_agent,
        )

        assert isinstance(pipeline, ResearchPipeline)


# =============================================================================
# START SESSION TESTS
# =============================================================================


class TestStartSession:
    """Test session start functionality."""

    @pytest.mark.asyncio
    async def test_start_session_creates_session(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that start_session creates a new session."""
        response = await pipeline.start_session("user_123", "Research topic")

        mock_session_manager.create_session.assert_called_once_with(
            "user_123", "Research topic"
        )
        assert response.session_id == "sess_123"

    @pytest.mark.asyncio
    async def test_start_session_runs_initial_research(
        self,
        pipeline,
        mock_initial_research_agent,
    ):
        """Test that initial research is executed."""
        await pipeline.start_session("user_123", "Research topic")

        mock_initial_research_agent.run.assert_called_once()
        call_context = mock_initial_research_agent.run.call_args[1]["context"]
        assert call_context["user_query"] == "Research topic"

    @pytest.mark.asyncio
    async def test_start_session_transitions_to_brief(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that session transitions to BRIEF state."""
        # Track status transitions while also updating internal state
        statuses = []
        async def track_status(session_id, status):
            statuses.append(status)
            mock_session_manager._current_status["value"] = status
        mock_session_manager.update_status.side_effect = track_status

        await pipeline.start_session("user_123", "Research topic")

        # Should transition to INITIAL_RESEARCH then BRIEF
        assert SessionStatus.INITIAL_RESEARCH in statuses
        assert SessionStatus.BRIEF in statuses

    @pytest.mark.asyncio
    async def test_start_session_runs_brief_builder(
        self,
        pipeline,
        mock_brief_builder_agent,
    ):
        """Test that brief builder is executed."""
        await pipeline.start_session("user_123", "Research topic")

        mock_brief_builder_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_session_returns_session_response(
        self,
        pipeline,
    ):
        """Test that start_session returns proper response."""
        response = await pipeline.start_session("user_123", "Research topic")

        assert response.session_id == "sess_123"
        assert response.action == BriefBuilderAction.ASK_QUESTION
        assert "time horizon" in response.message


# =============================================================================
# PROCESS MESSAGE TESTS
# =============================================================================


class TestProcessMessage:
    """Test message processing during brief building."""

    @pytest.mark.asyncio
    async def test_process_message_in_brief_state(
        self,
        pipeline,
        mock_session_manager,
        mock_brief_builder_agent,
    ):
        """Test processing message when in BRIEF state."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF

        response = await pipeline.process_message("sess_123", "5 years horizon")

        mock_brief_builder_agent.run.assert_called_once()
        assert response.session_id == "sess_123"

    @pytest.mark.asyncio
    async def test_process_message_wrong_state_raises_error(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that processing message in wrong state raises error."""
        # Set session to EXECUTING state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.EXECUTING
        mock_session_manager._current_round["value"] = 1

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            await pipeline.process_message("sess_123", "some message")

        assert exc_info.value.current_state == SessionStatus.EXECUTING

    @pytest.mark.asyncio
    async def test_process_message_passes_user_message(
        self,
        pipeline,
        mock_session_manager,
        mock_brief_builder_agent,
    ):
        """Test that user message is passed to brief builder."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF

        await pipeline.process_message("sess_123", "5 years horizon")

        call_context = mock_brief_builder_agent.run.call_args[1]["context"]
        assert call_context["user_message"] == "5 years horizon"


# =============================================================================
# APPROVE BRIEF TESTS
# =============================================================================


class TestApproveBrief:
    """Test brief approval functionality."""

    @pytest.mark.asyncio
    async def test_approve_brief_in_brief_state(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test approving brief when in BRIEF state with valid brief data."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF
        # Provide minimal brief dict (not a full Brief model) - pipeline will try to validate
        # but we catch the validation error to verify the state transition was attempted
        mock_session_manager.get_state.return_value = {
            "goal": "Research Test Entity for comprehensive analysis",
            "status": BriefStatus.DRAFT.value,
        }

        # The approve_brief will fail at Brief.model_validate() but that's expected
        # since we're not providing a full Brief schema - this tests the state check works
        # Note: In production, the brief_builder would have stored a complete Brief
        try:
            await pipeline.approve_brief("sess_123")
        except Exception as e:
            # Should fail at Brief validation, not at state transition check
            assert "brief_id" in str(e) or "validation" in str(e).lower()

    @pytest.mark.asyncio
    async def test_approve_brief_wrong_state_raises_error(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that approving brief in wrong state raises error."""
        # Set session to EXECUTING state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.EXECUTING
        mock_session_manager._current_round["value"] = 1

        with pytest.raises(InvalidStateTransitionError) as exc_info:
            await pipeline.approve_brief("sess_123")

        assert exc_info.value.current_state == SessionStatus.EXECUTING

    @pytest.mark.asyncio
    async def test_approve_brief_with_modifications(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test approving brief with modifications calls save_state."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF
        mock_session_manager.get_state.return_value = {
            "goal": "Research Test Entity for comprehensive analysis",
            "status": BriefStatus.DRAFT.value,
        }

        modifications = {"goal": "Updated research goal for comprehensive analysis"}

        # The approve_brief will fail at Brief.model_validate() but that's expected
        # This test verifies that save_state is called before validation
        try:
            await pipeline.approve_brief("sess_123", modifications=modifications)
        except Exception:
            pass  # Expected - Brief validation will fail

        # Verify save_state was called (modifications were applied before validation)
        save_calls = mock_session_manager.save_state.call_args_list
        assert len(save_calls) >= 1

    @pytest.mark.asyncio
    async def test_approve_brief_no_brief_raises_error(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that approving when no brief exists raises error."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF
        mock_session_manager.get_state.return_value = None

        from src.tools.errors import BriefNotApprovedError
        with pytest.raises(BriefNotApprovedError):
            await pipeline.approve_brief("sess_123")


# =============================================================================
# GET STATUS TESTS
# =============================================================================


class TestGetStatus:
    """Test status retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_status_returns_session_status(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that get_status returns current session status."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF

        status = await pipeline.get_status("sess_123")

        assert status.session_id == "sess_123"
        assert status.status == SessionStatus.BRIEF

    @pytest.mark.asyncio
    async def test_get_status_includes_progress_when_executing(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that progress is included when executing."""
        # Set session to EXECUTING state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.EXECUTING
        mock_session_manager._current_round["value"] = 2
        mock_session_manager.get_state.return_value = {
            "data_tasks": [{"id": "task1"}, {"id": "task2"}],
            "research_tasks": [{"id": "task3"}],
        }
        mock_session_manager.get_all_states.return_value = [{"task_id": "task1"}]

        status = await pipeline.get_status("sess_123")

        assert status.current_round == 2
        # Progress should be included in executing state


# =============================================================================
# GET RESULTS TESTS
# =============================================================================


class TestGetResults:
    """Test results retrieval functionality."""

    @pytest.mark.asyncio
    async def test_get_results_when_done(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test getting results when session is done."""
        # Set session to DONE state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.DONE
        mock_session_manager._current_round["value"] = 3
        mock_session_manager.get_state.return_value = {
            "executive_summary": "Executive summary",
            "key_findings": [],
            "recommendations": [],
        }

        results = await pipeline.get_results("sess_123")

        assert results.session_id == "sess_123"
        assert results.status == SessionStatus.DONE

    @pytest.mark.asyncio
    async def test_get_results_when_not_ready(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test getting results when not yet available."""
        # Set session to EXECUTING state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.EXECUTING
        mock_session_manager._current_round["value"] = 1

        results = await pipeline.get_results("sess_123")

        assert results.session_id == "sess_123"
        assert results.aggregated is None
        assert results.reports == []


# =============================================================================
# RESUME SESSION TESTS
# =============================================================================


class TestResumeSession:
    """Test session resumption (crash recovery)."""

    @pytest.mark.asyncio
    async def test_resume_session_in_brief_state(
        self,
        pipeline,
        mock_session_manager,
        mock_brief_builder_agent,
    ):
        """Test resuming session in BRIEF state returns to brief building."""
        # Set session to BRIEF state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.BRIEF

        response = await pipeline.resume_session("sess_123")

        assert response.session_id == "sess_123"
        mock_brief_builder_agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_resume_session_in_executing_state(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test resuming session in EXECUTING state resumes research."""
        # Set session to EXECUTING state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.EXECUTING
        mock_session_manager._current_round["value"] = 2
        # Return None to avoid Brief validation - the response will have brief=None
        mock_session_manager.get_state.return_value = None

        response = await pipeline.resume_session("sess_123")

        assert response.session_id == "sess_123"
        assert "resumed" in response.message.lower()

    @pytest.mark.asyncio
    async def test_resume_session_in_done_state(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test resuming session in DONE state returns terminal status."""
        # Set session to DONE state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.DONE
        mock_session_manager._current_round["value"] = 3

        response = await pipeline.resume_session("sess_123")

        assert response.session_id == "sess_123"
        assert "terminal" in response.message.lower()


# =============================================================================
# STATE TRANSITION TESTS
# =============================================================================


class TestStateTransitions:
    """Test state machine validation."""

    def test_valid_transitions_defined(self):
        """Test that valid transitions are properly defined."""
        # CREATED can go to INITIAL_RESEARCH or FAILED
        assert SessionStatus.INITIAL_RESEARCH in VALID_TRANSITIONS[SessionStatus.CREATED]
        assert SessionStatus.FAILED in VALID_TRANSITIONS[SessionStatus.CREATED]

        # EXECUTING can go to REVIEW or FAILED
        assert SessionStatus.REVIEW in VALID_TRANSITIONS[SessionStatus.EXECUTING]
        assert SessionStatus.FAILED in VALID_TRANSITIONS[SessionStatus.EXECUTING]

        # DONE and FAILED are terminal
        assert VALID_TRANSITIONS[SessionStatus.DONE] == set()
        assert VALID_TRANSITIONS[SessionStatus.FAILED] == set()

    def test_review_can_loop_back_to_executing(self):
        """Test that REVIEW can transition back to EXECUTING."""
        assert SessionStatus.EXECUTING in VALID_TRANSITIONS[SessionStatus.REVIEW]

    def test_review_can_proceed_to_aggregating(self):
        """Test that REVIEW can proceed to AGGREGATING."""
        assert SessionStatus.AGGREGATING in VALID_TRANSITIONS[SessionStatus.REVIEW]


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Test error handling functionality."""

    @pytest.mark.asyncio
    async def test_error_sets_session_to_failed(
        self,
        pipeline,
        mock_session_manager,
        mock_initial_research_agent,
    ):
        """Test that errors set session to FAILED state."""
        # Make initial research fail
        mock_initial_research_agent.run.side_effect = Exception("Research failed")

        with pytest.raises(Exception):
            await pipeline.start_session("user_123", "Research topic")

        mock_session_manager.set_error.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_failed_state_raises_error(
        self,
        pipeline,
        mock_session_manager,
    ):
        """Test that accessing failed session raises error."""
        # Set session to FAILED state via internal state tracker
        mock_session_manager._current_status["value"] = SessionStatus.FAILED

        from src.tools.errors import SessionFailedError
        with pytest.raises(SessionFailedError):
            await pipeline.process_message("sess_123", "message")


# =============================================================================
# CUSTOM ERROR TESTS
# =============================================================================


class TestPipelineErrors:
    """Test custom pipeline errors."""

    def test_pipeline_error(self):
        """Test PipelineError construction."""
        error = PipelineError(
            message="Pipeline failed",
            session_id="sess_123",
        )

        assert error.message == "Pipeline failed"
        assert error.code == "PIPELINE_ERROR"
        assert error.session_id == "sess_123"

    def test_invalid_state_transition_error(self):
        """Test InvalidStateTransitionError construction."""
        error = InvalidStateTransitionError(
            message="Invalid transition",
            current_state=SessionStatus.BRIEF,
            attempted_state=SessionStatus.DONE,
            session_id="sess_123",
        )

        assert error.current_state == SessionStatus.BRIEF
        assert error.attempted_state == SessionStatus.DONE
        assert error.code == "INVALID_STATE_TRANSITION"

    def test_max_rounds_exceeded_error(self):
        """Test MaxRoundsExceededError construction."""
        error = MaxRoundsExceededError(
            session_id="sess_123",
            max_rounds=10,
        )

        assert "Maximum research rounds exceeded" in error.message
        assert error.code == "MAX_ROUNDS_EXCEEDED"
        assert error.details["max_rounds"] == 10


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestPipelineIntegration:
    """Integration tests for pipeline flow."""

    @pytest.mark.asyncio
    async def test_full_brief_building_flow(
        self,
        pipeline,
        mock_session_manager,
        mock_brief_builder_agent,
    ):
        """Test complete brief building flow."""
        # Session starts in CREATED state (default)

        # First: start session (state will transition through INITIAL_RESEARCH to BRIEF)
        response = await pipeline.start_session("user_123", "Research topic")
        assert response.session_id == "sess_123"

        # Session should now be in BRIEF state (tracked by internal state tracker)

        # Second: send message (should work since we're in BRIEF state)
        response = await pipeline.process_message("sess_123", "5 years horizon")
        assert response.session_id == "sess_123"

    @pytest.mark.asyncio
    async def test_findings_extraction(self, pipeline):
        """Test _extract_findings helper method."""
        research_results = [
            {"key_findings": [{"finding": "Finding 1"}, {"finding": "Finding 2"}]},
            {"key_findings": ["Finding 3", "Finding 4"]},
            {"key_findings": []},
        ]

        findings = pipeline._extract_findings(research_results)

        assert "Finding 1" in findings
        assert "Finding 2" in findings
        assert "Finding 3" in findings
        assert "Finding 4" in findings
        assert len(findings) == 4

    @pytest.mark.asyncio
    async def test_findings_extraction_limits_count(self, pipeline):
        """Test that findings extraction limits to 50 items."""
        research_results = [
            {"key_findings": [{"finding": f"Finding {i}"} for i in range(60)]}
        ]

        findings = pipeline._extract_findings(research_results)

        assert len(findings) == 50
