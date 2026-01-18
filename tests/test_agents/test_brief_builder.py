"""
Ralph Deep Research - Brief Builder Agent Tests

Unit tests for the BriefBuilderAgent.

Why these tests:
- Verify conversation flow handling
- Test brief generation and validation
- Test action types (ask_question, present_brief, brief_approved)
- Test state persistence for conversations
- Test fallback behavior when LLM fails
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from src.agents.brief_builder import (
    BriefBuilderAgent,
    LLMBriefBuilderOutput,
    LLMBrief,
    LLMScopeItem,
    LLMUserContext,
    LLMBriefConstraints,
)
from src.api.schemas import (
    BriefBuilderAction,
    BriefStatus,
    ScopeType,
    Priority,
    UserIntent,
    OutputFormat,
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
    """Create BriefBuilderAgent for testing."""
    return BriefBuilderAgent(mock_llm, mock_session_manager)


@pytest.fixture
def sample_initial_context():
    """Create sample initial context."""
    return {
        "session_id": "sess_test123456",
        "query_analysis": {
            "original_query": "Tell me about Realty Income",
            "detected_language": "en",
            "detected_intent": "learning",
            "confidence": 0.8,
        },
        "entities": [
            {
                "name": "Realty Income",
                "type": "company",
                "identifiers": {"ticker": "O"},
                "brief_description": "A REIT company",
            }
        ],
        "context_summary": "Realty Income is a REIT company...",
        "suggested_topics": ["Financial analysis", "Dividend history"],
    }


@pytest.fixture
def sample_ask_question_output():
    """Create sample ask_question output."""
    return LLMBriefBuilderOutput(
        action="ask_question",
        message="What is your investment goal?",
        current_brief=None,
    )


@pytest.fixture
def sample_present_brief_output():
    """Create sample present_brief output."""
    return LLMBriefBuilderOutput(
        action="present_brief",
        message="Here is your research specification.",
        current_brief=LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="draft",
            goal="Evaluate Realty Income as a long-term investment",
            user_context=LLMUserContext(
                intent="investment",
                horizon="5+ years",
                risk_profile="moderate",
            ),
            scope=[
                LLMScopeItem(
                    id=1,
                    topic="Financial health",
                    type="data",
                    details="Dividends, debt, ratios",
                    priority="high",
                ),
                LLMScopeItem(
                    id=2,
                    topic="Business model",
                    type="research",
                    details=None,
                    priority="medium",
                ),
            ],
            output_formats=["pdf", "excel"],
            constraints=LLMBriefConstraints(
                focus_areas=["dividend growth"],
                exclude=["short-term trading"],
            ),
        ),
    )


@pytest.fixture
def sample_approved_output():
    """Create sample brief_approved output."""
    return LLMBriefBuilderOutput(
        action="brief_approved",
        message="Great! Starting research now.",
        current_brief=LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="approved",
            goal="Evaluate Realty Income as investment",
            scope=[
                LLMScopeItem(
                    id=1,
                    topic="Financial analysis",
                    type="both",
                    priority="high",
                ),
            ],
            output_formats=["pdf"],
        ),
    )


# =============================================================================
# BASIC PROPERTIES TESTS
# =============================================================================


class TestAgentProperties:
    """Test agent properties."""

    def test_agent_name(self, agent):
        """Test agent_name property."""
        assert agent.agent_name == "brief_builder"

    def test_timeout_key(self, agent):
        """Test timeout key."""
        assert agent.get_timeout_key() == "brief_builder"


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent):
        """Test validation fails without session_id."""
        with pytest.raises(InvalidInputError):
            agent.validate_input({"user_message": "test"})

    def test_validate_with_initial_context(self, agent, sample_initial_context):
        """Test validation passes with initial_context."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "initial_context": sample_initial_context,
        })

    def test_validate_with_user_message(self, agent):
        """Test validation passes with user_message."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "user_message": "I want to invest",
        })

    def test_validate_missing_both(self, agent):
        """Test validation fails without initial_context or user_message."""
        with pytest.raises(InvalidInputError):
            agent.validate_input({"session_id": "sess_123"})


# =============================================================================
# ACTION HANDLING TESTS
# =============================================================================


class TestActionHandling:
    """Test different action types."""

    @pytest.mark.asyncio
    async def test_ask_question_action(self, agent, mock_llm, sample_ask_question_output):
        """Test ask_question action."""
        mock_llm.create_structured = AsyncMock(return_value=sample_ask_question_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {"context_summary": "Test context"},
            "user_message": "I'm interested in REITs",
        })

        assert result["action"] == BriefBuilderAction.ASK_QUESTION.value
        assert "goal" in result["message"].lower() or len(result["message"]) > 0
        assert result["current_brief"] is None

    @pytest.mark.asyncio
    async def test_present_brief_action(self, agent, mock_llm, sample_present_brief_output):
        """Test present_brief action."""
        mock_llm.create_structured = AsyncMock(return_value=sample_present_brief_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {},
            "user_message": "For long-term investment",
        })

        assert result["action"] == BriefBuilderAction.PRESENT_BRIEF.value
        assert result["current_brief"] is not None
        assert result["current_brief"]["status"] == BriefStatus.DRAFT.value

    @pytest.mark.asyncio
    async def test_brief_approved_action(self, agent, mock_llm, mock_session_manager, sample_approved_output):
        """Test brief_approved action."""
        mock_llm.create_structured = AsyncMock(return_value=sample_approved_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {},
            "current_brief": {"brief_id": "brief_test12345"},
            "user_message": "Looks good, approve it",
        })

        assert result["action"] == BriefBuilderAction.BRIEF_APPROVED.value
        assert result["current_brief"] is not None
        # Check that brief was saved
        assert mock_session_manager.save_state.call_count >= 2  # Conversation + Brief


# =============================================================================
# BRIEF CONVERSION TESTS
# =============================================================================


class TestBriefConversion:
    """Test LLM brief to Brief conversion."""

    def test_convert_brief_basic(self, agent):
        """Test basic brief conversion."""
        llm_brief = LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="draft",
            goal="Test research goal",
            scope=[
                LLMScopeItem(id=1, topic="Test topic", type="data"),
            ],
            output_formats=["pdf"],
        )

        result = agent._convert_brief(llm_brief)

        assert result["brief_id"] == "brief_test12345"
        assert result["version"] == 1
        assert result["status"] == BriefStatus.DRAFT.value
        assert result["goal"] == "Test research goal"
        assert len(result["scope"]) == 1
        assert OutputFormat.PDF.value in result["output_formats"]

    def test_convert_brief_with_user_context(self, agent):
        """Test brief conversion with user context."""
        llm_brief = LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="draft",
            goal="Investment analysis",
            user_context=LLMUserContext(
                intent="investment",
                horizon="5 years",
                risk_profile="moderate",
            ),
            scope=[LLMScopeItem(id=1, topic="Analysis", type="both")],
            output_formats=["pdf"],
        )

        result = agent._convert_brief(llm_brief)

        assert result["user_context"]["intent"] == UserIntent.INVESTMENT.value
        assert result["user_context"]["horizon"] == "5 years"

    def test_convert_brief_invalid_scope_type(self, agent):
        """Test brief conversion with invalid scope type."""
        llm_brief = LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="draft",
            goal="Test goal for research analysis",  # At least 10 chars
            scope=[
                LLMScopeItem(id=1, topic="Test", type="invalid_type"),
            ],
            output_formats=["pdf"],
        )

        result = agent._convert_brief(llm_brief)

        # Should default to BOTH
        assert result["scope"][0]["type"] == ScopeType.BOTH.value

    def test_convert_brief_invalid_priority(self, agent):
        """Test brief conversion with invalid priority."""
        llm_brief = LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="draft",
            goal="Test goal for research analysis",  # At least 10 chars
            scope=[
                LLMScopeItem(id=1, topic="Test", type="data", priority="invalid"),
            ],
            output_formats=["pdf"],
        )

        result = agent._convert_brief(llm_brief)

        # Should default to MEDIUM
        assert result["scope"][0]["priority"] == Priority.MEDIUM.value

    def test_convert_brief_empty_formats(self, agent):
        """Test brief conversion with empty output formats."""
        llm_brief = LLMBrief(
            brief_id="brief_test12345",
            version=1,
            status="draft",
            goal="Test goal for research analysis",  # At least 10 chars
            scope=[LLMScopeItem(id=1, topic="Test", type="data")],
            output_formats=[],
        )

        result = agent._convert_brief(llm_brief)

        # Should default to PDF
        assert OutputFormat.PDF.value in result["output_formats"]


# =============================================================================
# FALLBACK TESTS
# =============================================================================


class TestFallbackBehavior:
    """Test fallback output creation."""

    def test_fallback_with_initial_context(self, agent):
        """Test fallback with initial context."""
        initial_context = {
            "query_analysis": {
                "original_query": "Tell me about Apple",
            },
        }

        result = agent._create_fallback_output(
            brief_id="brief_123",
            initial_context=initial_context,
        )

        assert result.action == "ask_question"
        assert "Apple" in result.message

    def test_fallback_without_context(self, agent):
        """Test fallback without initial context."""
        result = agent._create_fallback_output(
            brief_id="brief_123",
            initial_context={},
        )

        assert result.action == "ask_question"
        assert "цель" in result.message.lower() or "goal" in result.message.lower()


# =============================================================================
# STATE PERSISTENCE TESTS
# =============================================================================


class TestStatePersistence:
    """Test state persistence."""

    @pytest.mark.asyncio
    async def test_saves_conversation(self, agent, mock_llm, mock_session_manager, sample_ask_question_output):
        """Test that conversation is saved."""
        mock_llm.create_structured = AsyncMock(return_value=sample_ask_question_output)

        await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {},
            "user_message": "I want to invest",
        })

        # Should save conversation
        mock_session_manager.save_state.assert_called()

    @pytest.mark.asyncio
    async def test_saves_approved_brief(self, agent, mock_llm, mock_session_manager, sample_approved_output):
        """Test that approved brief is saved."""
        mock_llm.create_structured = AsyncMock(return_value=sample_approved_output)

        await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {},
            "current_brief": {"brief_id": "brief_test12345"},
            "user_message": "Approve",
        })

        # Should have saved both conversation and brief
        assert mock_session_manager.save_state.call_count >= 2


# =============================================================================
# FULL EXECUTION TESTS
# =============================================================================


class TestFullExecution:
    """Test full agent execution."""

    @pytest.mark.asyncio
    async def test_execute_first_interaction(self, agent, mock_llm, sample_ask_question_output):
        """Test first interaction without conversation history."""
        mock_llm.create_structured = AsyncMock(return_value=sample_ask_question_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {"context_summary": "User interested in REITs"},
            "conversation_history": [],
            "user_message": "",
        })

        assert result["action"] in [a.value for a in BriefBuilderAction]

    @pytest.mark.asyncio
    async def test_execute_with_conversation_history(self, agent, mock_llm, sample_present_brief_output):
        """Test execution with existing conversation."""
        mock_llm.create_structured = AsyncMock(return_value=sample_present_brief_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "initial_context": {},
            "conversation_history": [
                {"role": "assistant", "content": "What is your goal?"},
                {"role": "user", "content": "Investment"},
            ],
            "user_message": "Long-term, 5 years",
        })

        assert result["action"] == BriefBuilderAction.PRESENT_BRIEF.value

    @pytest.mark.asyncio
    async def test_run_validates_input(self, agent, mock_llm, sample_ask_question_output):
        """Test run() with validation."""
        mock_llm.create_structured = AsyncMock(return_value=sample_ask_question_output)

        result = await agent.run(
            session_id="sess_test123456",
            context={
                "session_id": "sess_test123456",
                "initial_context": {"context_summary": "Test"},
                "user_message": "Hello",
            },
        )

        assert "action" in result
        assert "message" in result


# =============================================================================
# RESPONSE BUILDING TESTS
# =============================================================================


class TestResponseBuilding:
    """Test response building."""

    def test_build_response_ask_question(self, agent, sample_ask_question_output):
        """Test building ask_question response."""
        result = agent._build_response("sess_123", sample_ask_question_output)

        assert result["action"] == BriefBuilderAction.ASK_QUESTION.value
        assert result["message"] == sample_ask_question_output.message
        assert result["current_brief"] is None

    def test_build_response_present_brief(self, agent, sample_present_brief_output):
        """Test building present_brief response."""
        result = agent._build_response("sess_123", sample_present_brief_output)

        assert result["action"] == BriefBuilderAction.PRESENT_BRIEF.value
        assert result["current_brief"] is not None
        assert "goal" in result["current_brief"]

    def test_build_response_invalid_action(self, agent):
        """Test building response with invalid action."""
        output = LLMBriefBuilderOutput(
            action="invalid_action",
            message="Test",
            current_brief=None,
        )

        result = agent._build_response("sess_123", output)

        # Should default to ask_question
        assert result["action"] == BriefBuilderAction.ASK_QUESTION.value
