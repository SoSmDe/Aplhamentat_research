"""
Ralph Deep Research - Initial Research Agent Tests

Unit tests for the InitialResearchAgent.

Why these tests:
- Verify query parsing and entity extraction
- Test language and intent detection
- Test web search integration
- Test state persistence after execution
- Test fallback behavior when LLM fails
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.agents.initial_research import (
    InitialResearchAgent,
    LLMInitialResearchOutput,
    LLMQueryAnalysis,
    LLMEntity,
    LLMEntityIdentifiers,
)
from src.api.schemas import (
    EntityType,
    Language,
    UserIntent,
)
from src.tools.errors import InvalidInputError
from src.tools.web_search import SearchResult


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
def mock_search_client():
    """Create mock search client."""
    client = MagicMock()
    client.search = AsyncMock(return_value=[
        SearchResult(
            title="Test Company Info",
            url="https://example.com/company",
            snippet="Test company is a leading provider...",
            date="2025-01-15",
        ),
        SearchResult(
            title="Stock Analysis",
            url="https://finance.example.com/stock",
            snippet="Stock trading at $100 per share...",
            date="2025-01-14",
        ),
    ])
    return client


@pytest.fixture
def agent(mock_llm, mock_session_manager, mock_search_client):
    """Create InitialResearchAgent for testing."""
    return InitialResearchAgent(
        mock_llm,
        mock_session_manager,
        search_client=mock_search_client,
    )


@pytest.fixture
def sample_llm_output():
    """Create sample LLM output."""
    return LLMInitialResearchOutput(
        session_id="sess_test123456",
        query_analysis=LLMQueryAnalysis(
            original_query="Tell me about Apple Inc",
            detected_language="en",
            detected_intent="learning",
            confidence=0.85,
        ),
        entities=[
            LLMEntity(
                name="Apple Inc",
                type="company",
                identifiers=LLMEntityIdentifiers(
                    ticker="AAPL",
                    website="https://apple.com",
                    country="USA",
                    exchange="NASDAQ",
                ),
                brief_description="Technology company known for iPhone, Mac, and services.",
                category="Technology",
                sector="Consumer Electronics",
            ),
        ],
        context_summary="Apple Inc is one of the largest technology companies in the world.",
        suggested_topics=[
            "Financial performance",
            "Product lineup",
            "Market position",
        ],
        sources_used=["https://apple.com", "https://finance.yahoo.com"],
    )


# =============================================================================
# BASIC PROPERTIES TESTS
# =============================================================================


class TestAgentProperties:
    """Test agent properties."""

    def test_agent_name(self, agent):
        """Test agent_name property."""
        assert agent.agent_name == "initial_research"

    def test_timeout_key(self, agent):
        """Test timeout key."""
        assert agent.get_timeout_key() == "initial_research"


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent):
        """Test validation fails without session_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({"user_query": "test query"})
        assert "session_id" in str(exc_info.value.message)

    def test_validate_missing_user_query(self, agent):
        """Test validation fails without user_query."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({"session_id": "sess_123"})
        assert "user_query" in str(exc_info.value.message)

    def test_validate_short_query(self, agent):
        """Test validation fails with too short query."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "user_query": "ab",
            })
        assert "at least 3 characters" in str(exc_info.value.message)

    def test_validate_success(self, agent):
        """Test successful validation."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "user_query": "Tell me about Apple",
        })


# =============================================================================
# SEARCH TESTS
# =============================================================================


class TestSearchIntegration:
    """Test web search integration."""

    @pytest.mark.asyncio
    async def test_gather_search_results(self, agent, mock_search_client):
        """Test search results gathering."""
        results = await agent._gather_search_results("Apple Inc")

        assert len(results) > 0
        mock_search_client.search.assert_called()

    @pytest.mark.asyncio
    async def test_search_with_financial_keywords(self, agent, mock_search_client):
        """Test additional search for financial keywords."""
        await agent._gather_search_results("Apple stock company")

        # Should have multiple search calls
        assert mock_search_client.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_search_failure_handled(self, agent, mock_search_client):
        """Test search failure is handled gracefully."""
        mock_search_client.search = AsyncMock(side_effect=Exception("Search failed"))

        results = await agent._gather_search_results("test")

        assert results == []  # Should return empty list, not raise

    def test_build_search_context_empty(self, agent):
        """Test building context with empty results."""
        context = agent._build_search_context([])

        assert "No search results" in context

    def test_build_search_context_with_results(self, agent):
        """Test building context with search results."""
        results = [
            SearchResult(
                title="Test Title",
                url="https://example.com",
                snippet="Test snippet",
            ),
        ]

        context = agent._build_search_context(results)

        assert "Test Title" in context
        assert "https://example.com" in context
        assert "Test snippet" in context


# =============================================================================
# LLM ANALYSIS TESTS
# =============================================================================


class TestLLMAnalysis:
    """Test LLM analysis methods."""

    @pytest.mark.asyncio
    async def test_analyze_with_llm_success(self, agent, mock_llm, sample_llm_output):
        """Test successful LLM analysis."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent._analyze_with_llm(
            session_id="sess_test123456",
            user_query="Tell me about Apple Inc",
            search_context="Apple is a tech company...",
        )

        assert result.session_id == "sess_test123456"
        assert len(result.entities) > 0
        mock_llm.create_structured.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_with_llm_fallback(self, agent, mock_llm):
        """Test fallback when LLM fails."""
        mock_llm.create_structured = AsyncMock(side_effect=Exception("LLM error"))

        result = await agent._analyze_with_llm(
            session_id="sess_test123456",
            user_query="Tell me about Apple",
            search_context="",
        )

        assert result.session_id == "sess_test123456"
        assert result.query_analysis.original_query == "Tell me about Apple"


# =============================================================================
# FALLBACK TESTS
# =============================================================================


class TestFallbackBehavior:
    """Test fallback output creation."""

    def test_fallback_english_query(self, agent):
        """Test fallback with English query."""
        result = agent._create_fallback_output(
            session_id="sess_123",
            user_query="Tell me about investment opportunities",
        )

        assert result.query_analysis.detected_language == "en"
        assert result.query_analysis.detected_intent == "investment"

    def test_fallback_russian_query(self, agent):
        """Test fallback with Russian query."""
        result = agent._create_fallback_output(
            session_id="sess_123",
            user_query="Расскажи про Realty Income",
        )

        assert result.query_analysis.detected_language == "ru"
        assert result.query_analysis.detected_intent == "learning"

    def test_fallback_market_intent(self, agent):
        """Test fallback detects market research intent."""
        result = agent._create_fallback_output(
            session_id="sess_123",
            user_query="What are the market trends",
        )

        assert result.query_analysis.detected_intent == "market_research"

    def test_fallback_competitive_intent(self, agent):
        """Test fallback detects competitive intent."""
        result = agent._create_fallback_output(
            session_id="sess_123",
            user_query="Compare competitors in industry",
        )

        assert result.query_analysis.detected_intent == "competitive"


# =============================================================================
# CONTEXT BUILDING TESTS
# =============================================================================


class TestContextBuilding:
    """Test InitialContext building."""

    def test_build_initial_context(self, agent, sample_llm_output):
        """Test building InitialContext from LLM output."""
        context = agent._build_initial_context(
            session_id="sess_test123456",
            llm_output=sample_llm_output,
            sources_used=["https://source1.com"],
        )

        assert context.session_id == "sess_test123456"
        assert context.query_analysis.detected_language == Language.EN
        assert context.query_analysis.detected_intent == UserIntent.LEARNING
        assert len(context.entities) == 1
        assert context.entities[0].name == "Apple Inc"
        assert context.entities[0].type == EntityType.COMPANY

    def test_build_context_invalid_language(self, agent):
        """Test building context with invalid language."""
        llm_output = LLMInitialResearchOutput(
            session_id="sess_123",
            query_analysis=LLMQueryAnalysis(
                original_query="test",
                detected_language="invalid",
                detected_intent="learning",
                confidence=0.5,
            ),
            context_summary="Test",
            suggested_topics=[],
        )

        context = agent._build_initial_context("sess_123", llm_output, [])

        # Should default to EN
        assert context.query_analysis.detected_language == Language.EN

    def test_build_context_invalid_entity_type(self, agent):
        """Test building context with invalid entity type."""
        llm_output = LLMInitialResearchOutput(
            session_id="sess_123",
            query_analysis=LLMQueryAnalysis(
                original_query="test",
                detected_language="en",
                detected_intent="learning",
                confidence=0.5,
            ),
            entities=[
                LLMEntity(
                    name="Test Entity",
                    type="invalid_type",
                    brief_description="Test",
                    category="Test",
                ),
            ],
            context_summary="Test",
            suggested_topics=[],
        )

        context = agent._build_initial_context("sess_123", llm_output, [])

        # Should default to CONCEPT
        assert context.entities[0].type == EntityType.CONCEPT


# =============================================================================
# FULL EXECUTION TESTS
# =============================================================================


class TestFullExecution:
    """Test full agent execution."""

    @pytest.mark.asyncio
    async def test_execute_success(self, agent, mock_llm, mock_session_manager, sample_llm_output):
        """Test successful execution."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "user_query": "Tell me about Apple Inc",
        })

        assert result["session_id"] == "sess_test123456"
        assert "query_analysis" in result
        assert "entities" in result
        assert "context_summary" in result

        # Verify state was saved
        mock_session_manager.save_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_saves_state(self, agent, mock_llm, mock_session_manager, sample_llm_output):
        """Test that execution saves state."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        await agent.execute({
            "session_id": "sess_test123456",
            "user_query": "Test query",
        })

        # Verify save_state was called with correct data type
        call_kwargs = mock_session_manager.save_state.call_args
        assert call_kwargs[1]["session_id"] == "sess_test123456"
        # Check for the value either as string or enum
        data_type = call_kwargs[1]["data_type"]
        data_type_str = data_type.value if hasattr(data_type, "value") else str(data_type)
        assert "initial_context" in data_type_str.lower()

    @pytest.mark.asyncio
    async def test_run_with_validation(self, agent, mock_llm, sample_llm_output):
        """Test run() with input validation."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent.run(
            session_id="sess_test123456",
            context={
                "session_id": "sess_test123456",
                "user_query": "Tell me about technology companies",
            },
        )

        assert result["session_id"] == "sess_test123456"
