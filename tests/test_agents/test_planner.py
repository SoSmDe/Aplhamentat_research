"""
Ralph Deep Research - Planner Agent Tests

Unit tests for the PlannerAgent.

Why these tests:
- Verify initial planning creates correct tasks from Brief
- Test review mode calculates coverage correctly
- Test task ID generation and deduplication
- Test fallback behavior when LLM fails
- Test max rounds enforcement
- Verify state persistence
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.planner import (
    PlannerAgent,
    LLMPlanOutput,
    LLMDataTask,
    LLMResearchTask,
    LLMPlannerDecisionOutput,
    LLMCoverageItem,
    LLMFilteredQuestion,
)
from src.api.schemas import (
    DataSource,
    Priority,
    PlannerDecisionStatus,
    ScopeType,
    TaskStatus,
)
from src.tools.errors import InvalidInputError


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    client = MagicMock()
    client.create_message = AsyncMock(return_value="Test response")
    client.create_structured = AsyncMock()
    return client


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    manager = MagicMock()
    manager.save_state = AsyncMock(return_value=1)
    manager.get_state = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def agent(mock_llm, mock_session_manager):
    """Create PlannerAgent for testing."""
    return PlannerAgent(mock_llm, mock_session_manager)


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.max_rounds_per_session = 10
    return settings


@pytest.fixture
def sample_brief():
    """Create sample Brief for testing."""
    return {
        "brief_id": "brief_test123456",
        "version": 1,
        "status": "approved",
        "goal": "Analyze Realty Income Corporation for investment potential",
        "scope": [
            {
                "id": 1,
                "topic": "Financial performance and metrics",
                "type": "data",
                "priority": "high",
                "details": "Revenue, FFO, dividend history",
            },
            {
                "id": 2,
                "topic": "Market position and competitive landscape",
                "type": "research",
                "priority": "medium",
                "details": "Industry analysis",
            },
            {
                "id": 3,
                "topic": "Risk assessment",
                "type": "both",
                "priority": "high",
                "details": "Key risks and mitigations",
            },
        ],
        "output_formats": ["pdf", "excel"],
        "constraints": {
            "focus_areas": ["REIT sector", "dividend sustainability"],
            "time_period": "Last 5 years",
        },
    }


@pytest.fixture
def sample_plan_output():
    """Create sample LLM plan output."""
    return LLMPlanOutput(
        round=1,
        brief_id="brief_test123456",
        data_tasks=[
            LLMDataTask(
                id="d1",
                scope_item_id=1,
                description="Collect financial metrics for Realty Income",
                source="financial_api",
                priority="high",
                expected_output="Revenue, FFO, dividend yield data",
            ),
            LLMDataTask(
                id="d2",
                scope_item_id=3,
                description="Collect risk metrics",
                source="web_search",
                priority="high",
                expected_output="Debt ratios, occupancy rates",
            ),
        ],
        research_tasks=[
            LLMResearchTask(
                id="r1",
                scope_item_id=2,
                description="Research market position",
                focus="Competitive advantages",
                source_types=["news", "reports", "analyst_reports"],
                priority="medium",
                search_queries=["Realty Income market position", "net lease REIT comparison"],
            ),
            LLMResearchTask(
                id="r2",
                scope_item_id=3,
                description="Research key risks",
                focus="Risk factors and mitigations",
                source_types=["sec_filings", "analyst_reports"],
                priority="high",
                search_queries=["Realty Income risks", "REIT interest rate risk"],
            ),
        ],
        total_tasks=4,
        estimated_duration_seconds=120,
    )


@pytest.fixture
def sample_decision_output():
    """Create sample LLM decision output."""
    return LLMPlannerDecisionOutput(
        round=1,
        status="continue",
        coverage={
            "1": LLMCoverageItem(
                topic="Financial performance",
                coverage_percent=70.0,
                covered_aspects=["Basic financial metrics collected"],
                missing_aspects=["Historical comparison", "Peer benchmarking"],
            ),
            "2": LLMCoverageItem(
                topic="Market position",
                coverage_percent=85.0,
                covered_aspects=["Competitive analysis", "Market share"],
                missing_aspects=[],
            ),
            "3": LLMCoverageItem(
                topic="Risk assessment",
                coverage_percent=60.0,
                covered_aspects=["Interest rate risk identified"],
                missing_aspects=["Tenant concentration", "Geographic risk"],
            ),
        },
        overall_coverage=72.0,
        reason="Scope item 1 and 3 below 80% threshold",
        new_data_tasks=[
            LLMDataTask(
                id="d3",
                scope_item_id=1,
                description="Collect peer comparison data",
                source="financial_api",
                priority="high",
                expected_output="Peer metrics for comparison",
            ),
        ],
        new_research_tasks=[
            LLMResearchTask(
                id="r3",
                scope_item_id=3,
                description="Research tenant concentration",
                focus="Top tenants and diversification",
                source_types=["sec_filings"],
                priority="high",
                search_queries=["Realty Income top tenants"],
            ),
        ],
        filtered_questions=[
            LLMFilteredQuestion(
                question="What is the dividend growth rate trend?",
                source_task_id="d1",
                relevance="high",
                action="add",
                reasoning="Directly relevant to investment goal",
            ),
        ],
    )


# =============================================================================
# BASIC PROPERTIES TESTS
# =============================================================================


class TestAgentProperties:
    """Test agent properties."""

    def test_agent_name(self, agent):
        """Test agent_name property."""
        assert agent.agent_name == "planner"

    def test_timeout_key(self, agent):
        """Test timeout key."""
        assert agent.get_timeout_key() == "planner"


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent, sample_brief):
        """Test validation fails without session_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "mode": "initial",
                "brief": sample_brief,
            })
        assert "session_id" in str(exc_info.value.message)

    def test_validate_missing_mode(self, agent, sample_brief):
        """Test validation fails without mode."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "brief": sample_brief,
            })
        assert "mode" in str(exc_info.value.message)

    def test_validate_invalid_mode(self, agent, sample_brief):
        """Test validation fails with invalid mode."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "mode": "invalid",
                "brief": sample_brief,
            })
        assert "mode" in str(exc_info.value.message)

    def test_validate_missing_brief(self, agent):
        """Test validation fails without brief."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "mode": "initial",
            })
        assert "brief" in str(exc_info.value.message)

    def test_validate_review_missing_round(self, agent, sample_brief):
        """Test review mode validation fails without round."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "mode": "review",
                "brief": sample_brief,
                "data_results": [],
                "research_results": [],
            })
        assert "round" in str(exc_info.value.message)

    def test_validate_review_missing_results(self, agent, sample_brief):
        """Test review mode validation fails without results."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "mode": "review",
                "brief": sample_brief,
                "round": 1,
            })
        assert "data_results" in str(exc_info.value.message)

    def test_validate_initial_mode_success(self, agent, sample_brief):
        """Test successful initial mode validation."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "mode": "initial",
            "brief": sample_brief,
        })

    def test_validate_review_mode_success(self, agent, sample_brief):
        """Test successful review mode validation."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "mode": "review",
            "brief": sample_brief,
            "round": 1,
            "data_results": [],
            "research_results": [],
        })


# =============================================================================
# INITIAL PLANNING TESTS
# =============================================================================


class TestInitialPlanning:
    """Test initial planning mode."""

    @pytest.mark.asyncio
    async def test_initial_planning_success(
        self, agent, mock_llm, mock_session_manager, sample_brief, sample_plan_output
    ):
        """Test successful initial planning."""
        mock_llm.create_structured = AsyncMock(return_value=sample_plan_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "mode": "initial",
            "brief": sample_brief,
        })

        assert result["round"] == 1
        assert result["brief_id"] == sample_brief["brief_id"]
        assert len(result["data_tasks"]) > 0
        assert len(result["research_tasks"]) > 0

        # Verify state saved
        mock_session_manager.save_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_initial_planning_task_ids(
        self, agent, mock_llm, sample_brief, sample_plan_output
    ):
        """Test task IDs follow correct format."""
        mock_llm.create_structured = AsyncMock(return_value=sample_plan_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "mode": "initial",
            "brief": sample_brief,
        })

        # Check data task IDs
        for task in result["data_tasks"]:
            assert task["id"].startswith("d")
            assert task["id"][1:].isdigit()

        # Check research task IDs
        for task in result["research_tasks"]:
            assert task["id"].startswith("r")
            assert task["id"][1:].isdigit()

    @pytest.mark.asyncio
    async def test_initial_planning_max_tasks(self, agent, mock_llm, sample_brief):
        """Test max 10 tasks per round enforcement."""
        # Create output with too many tasks
        many_data = [
            LLMDataTask(
                id=f"d{i}",
                scope_item_id=1,
                description=f"Collect data task number {i} for analysis",
                source="web_search",
                priority="medium",
            )
            for i in range(1, 8)
        ]
        many_research = [
            LLMResearchTask(
                id=f"r{i}",
                scope_item_id=2,
                description=f"Research task number {i} for analysis",
                focus="Focus",
                source_types=["news"],
                priority="medium",
            )
            for i in range(1, 8)
        ]

        output = LLMPlanOutput(
            round=1,
            brief_id="brief_test123456",
            data_tasks=many_data,
            research_tasks=many_research,
            total_tasks=14,
        )
        mock_llm.create_structured = AsyncMock(return_value=output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "mode": "initial",
            "brief": sample_brief,
        })

        # Total should be limited to 10
        total = len(result["data_tasks"]) + len(result["research_tasks"])
        assert total <= 10

    def test_build_initial_planning_prompt(self, agent, sample_brief):
        """Test prompt building for initial planning."""
        prompt = agent._build_initial_planning_prompt(sample_brief)

        assert sample_brief["goal"] in prompt
        assert "Financial performance" in prompt
        assert "brief_test123456" in prompt

    def test_fallback_plan_creation(self, agent, sample_brief):
        """Test fallback plan when LLM fails."""
        result = agent._create_fallback_plan(sample_brief)

        assert result.round == 1
        assert result.brief_id == sample_brief["brief_id"]
        assert len(result.data_tasks) > 0 or len(result.research_tasks) > 0


# =============================================================================
# REVIEW MODE TESTS
# =============================================================================


class TestReviewMode:
    """Test review mode."""

    @pytest.mark.asyncio
    async def test_review_continue_decision(
        self, agent, mock_llm, mock_session_manager, mock_settings, sample_brief, sample_decision_output
    ):
        """Test review returns continue decision."""
        mock_llm.create_structured = AsyncMock(return_value=sample_decision_output)

        with patch("src.agents.planner.get_settings", return_value=mock_settings):
            result = await agent.execute({
                "session_id": "sess_test123456",
                "mode": "review",
                "brief": sample_brief,
                "round": 1,
                "data_results": [
                    {"task_id": "d1", "status": "done", "metrics": {}},
                ],
                "research_results": [
                    {"task_id": "r1", "status": "done", "key_findings": []},
                ],
                "all_questions": [],
                "previous_tasks": ["d1", "d2", "r1", "r2"],
            })

        assert result["status"] == "continue"
        assert result["overall_coverage"] < 80
        assert len(result.get("new_data_tasks", [])) > 0 or len(result.get("new_research_tasks", [])) > 0

        # Verify state saved
        mock_session_manager.save_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_review_done_decision(
        self, agent, mock_llm, mock_settings, sample_brief
    ):
        """Test review returns done decision when coverage >= 80%."""
        done_output = LLMPlannerDecisionOutput(
            round=2,
            status="done",
            coverage={
                "1": LLMCoverageItem(
                    topic="Financial",
                    coverage_percent=90.0,
                    covered_aspects=["All covered"],
                    missing_aspects=[],
                ),
                "2": LLMCoverageItem(
                    topic="Market",
                    coverage_percent=85.0,
                    covered_aspects=["All covered"],
                    missing_aspects=[],
                ),
            },
            overall_coverage=87.5,
            reason="All scope items above 80% threshold",
            new_data_tasks=[],
            new_research_tasks=[],
            filtered_questions=[],
        )
        mock_llm.create_structured = AsyncMock(return_value=done_output)

        with patch("src.agents.planner.get_settings", return_value=mock_settings):
            result = await agent.execute({
                "session_id": "sess_test123456",
                "mode": "review",
                "brief": sample_brief,
                "round": 2,
                "data_results": [],
                "research_results": [],
                "all_questions": [],
            })

        assert result["status"] == "done"
        assert result["overall_coverage"] >= 80

    @pytest.mark.asyncio
    async def test_max_rounds_forced_completion(
        self, agent, sample_brief
    ):
        """Test forced completion when max rounds reached."""
        # Patch settings to have max_rounds = 2
        with pytest.MonkeyPatch().context() as mp:
            mock_settings = MagicMock()
            mock_settings.max_rounds_per_session = 2
            mp.setattr("src.agents.planner.get_settings", lambda: mock_settings)

            result = await agent._execute_review(
                session_id="sess_test123456",
                brief=sample_brief,
                round_num=2,
                data_results=[],
                research_results=[],
                all_questions=[],
                previous_tasks=[],
            )

        assert result["status"] == "done"
        assert "Maximum rounds" in result["reason"]

    def test_build_review_prompt(self, agent, sample_brief):
        """Test prompt building for review mode."""
        prompt = agent._build_review_prompt(
            brief=sample_brief,
            round_num=1,
            data_results=[
                {"task_id": "d1", "status": "done", "metrics": {"revenue": 100}},
            ],
            research_results=[
                {"task_id": "r1", "status": "done", "key_findings": [{"finding": "test"}]},
            ],
            all_questions=[
                {"type": "research", "question": "What about growth?", "source_task_id": "r1"},
            ],
            previous_tasks=["d1", "r1"],
        )

        assert sample_brief["goal"] in prompt
        assert "d1" in prompt
        assert "r1" in prompt

    def test_task_id_deduplication(
        self, agent, sample_decision_output
    ):
        """Test new task IDs avoid duplicates."""
        previous_tasks = ["d1", "d2", "d3", "r1", "r2"]

        result = agent._convert_to_decision(
            sample_decision_output,
            round_num=1,
            previous_tasks=previous_tasks,
        )

        # Check new task IDs don't duplicate
        all_new_ids = [t["id"] for t in result["new_data_tasks"]]
        all_new_ids += [t["id"] for t in result["new_research_tasks"]]

        for new_id in all_new_ids:
            if new_id.startswith("d") and new_id in previous_tasks:
                # ID was regenerated
                assert int(new_id[1:]) > 3


# =============================================================================
# CONVERSION TESTS
# =============================================================================


class TestConversions:
    """Test LLM output conversions."""

    def test_convert_to_plan(self, agent, sample_plan_output):
        """Test Plan conversion."""
        result = agent._convert_to_plan(sample_plan_output, round_num=1)

        assert result["round"] == 1
        assert result["brief_id"] == "brief_test123456"
        assert len(result["data_tasks"]) == 2
        assert len(result["research_tasks"]) == 2

        # Check task structure
        data_task = result["data_tasks"][0]
        assert data_task["id"] == "d1"
        assert data_task["source"] == "financial_api"
        assert data_task["priority"] == "high"
        assert data_task["status"] == "pending"

    def test_convert_to_plan_invalid_values(self, agent):
        """Test Plan conversion with invalid enum values."""
        output = LLMPlanOutput(
            round=1,
            brief_id="brief_123",
            data_tasks=[
                LLMDataTask(
                    id="d1",
                    scope_item_id=1,
                    description="Test description with at least 10 chars",
                    source="invalid_source",
                    priority="invalid_priority",
                ),
            ],
            research_tasks=[],
            total_tasks=1,
        )

        result = agent._convert_to_plan(output, round_num=1)

        # Should use defaults
        task = result["data_tasks"][0]
        assert task["source"] == "web_search"  # Default
        assert task["priority"] == "medium"  # Default

    def test_convert_to_decision(self, agent, sample_decision_output):
        """Test PlannerDecision conversion."""
        result = agent._convert_to_decision(
            sample_decision_output,
            round_num=1,
            previous_tasks=["d1", "d2"],
        )

        assert result["round"] == 1
        assert result["status"] == "continue"
        assert result["overall_coverage"] == 72.0
        assert len(result["coverage"]) == 3
        assert len(result["filtered_questions"]) == 1

        # Check filtered question
        question = result["filtered_questions"][0]
        assert question["action"] == "add"
        assert question["relevance"] == "high"


# =============================================================================
# FALLBACK TESTS
# =============================================================================


class TestFallbackBehavior:
    """Test fallback behavior."""

    def test_fallback_plan(self, agent, sample_brief):
        """Test fallback plan creation."""
        result = agent._create_fallback_plan(sample_brief)

        # Should create tasks based on scope
        assert result.round == 1
        assert len(result.data_tasks) >= 1  # Scope items with type data or both
        assert len(result.research_tasks) >= 1  # Scope items with type research or both

    def test_fallback_decision(self, agent, sample_brief):
        """Test fallback decision creation."""
        result = agent._create_fallback_decision(
            brief=sample_brief,
            round_num=1,
            data_results=[
                {"task_id": "d1", "status": "done"},
            ],
            research_results=[
                {"task_id": "r1", "status": "done"},
            ],
        )

        assert result.round == 1
        assert result.status in ("continue", "done")
        assert result.overall_coverage > 0


# =============================================================================
# FULL EXECUTION TESTS
# =============================================================================


class TestFullExecution:
    """Test full agent execution."""

    @pytest.mark.asyncio
    async def test_run_initial_mode(
        self, agent, mock_llm, sample_brief, sample_plan_output
    ):
        """Test run() in initial mode."""
        mock_llm.create_structured = AsyncMock(return_value=sample_plan_output)

        result = await agent.run(
            session_id="sess_test123456",
            context={
                "session_id": "sess_test123456",
                "mode": "initial",
                "brief": sample_brief,
            },
        )

        assert result["round"] == 1
        assert "data_tasks" in result
        assert "research_tasks" in result

    @pytest.mark.asyncio
    async def test_run_review_mode(
        self, agent, mock_llm, mock_settings, sample_brief, sample_decision_output
    ):
        """Test run() in review mode."""
        mock_llm.create_structured = AsyncMock(return_value=sample_decision_output)

        with patch("src.agents.planner.get_settings", return_value=mock_settings):
            result = await agent.run(
                session_id="sess_test123456",
                context={
                    "session_id": "sess_test123456",
                    "mode": "review",
                    "brief": sample_brief,
                    "round": 1,
                    "data_results": [],
                    "research_results": [],
                    "all_questions": [],
                },
            )

        assert "status" in result
        assert "coverage" in result
        assert "overall_coverage" in result
