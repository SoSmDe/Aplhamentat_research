"""
Ralph Deep Research - Research Agent Tests

Unit tests for the ResearchAgent.

Why these tests:
- Verify web search query generation
- Test finding extraction and classification
- Test theme and contradiction identification
- Test source credibility evaluation
- Test fallback behavior when LLM fails
- Verify state persistence
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.research import (
    ResearchAgent,
    LLMResearchOutput,
    LLMFinding,
    LLMTheme,
    LLMContradiction,
    LLMContradictionView,
    LLMSource,
    LLMQuestion,
)
from src.api.schemas import (
    Confidence,
    FindingType,
    Priority,
    QuestionType,
    Sentiment,
    SourceTypeResult,
    TaskStatus,
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
            title="Apple Reports Record Q4 Results",
            url="https://news.example.com/apple-q4",
            snippet="Apple Inc. reported record revenue for Q4 2024...",
            date="2025-01-15",
        ),
        SearchResult(
            title="iPhone Sales Analysis",
            url="https://analysis.example.com/iphone",
            snippet="Analyst opinions diverge on iPhone sales trajectory...",
            date="2025-01-14",
        ),
        SearchResult(
            title="Tech Sector Outlook 2025",
            url="https://report.example.com/tech-outlook",
            snippet="Technology sector expected to grow despite headwinds...",
            date="2025-01-10",
        ),
    ])
    return client


@pytest.fixture
def agent(mock_llm, mock_session_manager, mock_search_client):
    """Create ResearchAgent for testing."""
    return ResearchAgent(
        mock_llm,
        mock_session_manager,
        search_client=mock_search_client,
    )


@pytest.fixture
def sample_task():
    """Create sample ResearchTask for testing."""
    return {
        "id": "r1",
        "scope_item_id": 1,
        "description": "Research market position and competitive landscape for Apple",
        "focus": "Competitive advantages and market share",
        "source_types": ["news", "reports", "analyst_reports"],
        "priority": "high",
        "status": "pending",
        "search_queries": [
            "Apple market position 2025",
            "Apple vs competitors analysis",
        ],
    }


@pytest.fixture
def sample_entity_context():
    """Create sample entity context."""
    return {
        "name": "Apple Inc",
        "type": "company",
        "identifiers": {
            "ticker": "AAPL",
        },
        "sector": "Technology",
    }


@pytest.fixture
def sample_brief_context():
    """Create sample brief context."""
    return {
        "goal": "Evaluate Apple as potential investment",
        "constraints": {
            "focus_areas": ["competitive position", "growth prospects"],
        },
    }


@pytest.fixture
def sample_llm_output():
    """Create sample LLM output."""
    return LLMResearchOutput(
        task_id="r1",
        round=1,
        status="done",
        summary="Apple maintains strong market position with significant competitive advantages in ecosystem integration and brand loyalty.",
        key_findings=[
            LLMFinding(
                finding="Apple holds 52% of US smartphone market share",
                type="fact",
                confidence="high",
                source="IDC Market Report",
            ),
            LLMFinding(
                finding="Services revenue growing faster than hardware",
                type="fact",
                confidence="high",
                source="Apple Q4 2024 Earnings",
            ),
            LLMFinding(
                finding="Analysts expect continued growth in India market",
                type="opinion",
                confidence="medium",
                source="Morgan Stanley Research",
            ),
        ],
        detailed_analysis="Apple's ecosystem strategy creates high switching costs...",
        themes=[
            LLMTheme(
                theme="Ecosystem Strength",
                points=["High switching costs", "Service integration", "Hardware-software synergy"],
                sentiment="positive",
            ),
            LLMTheme(
                theme="China Market Risks",
                points=["Local competition", "Regulatory challenges"],
                sentiment="negative",
            ),
        ],
        contradictions=[
            LLMContradiction(
                topic="iPhone Sales Outlook",
                view_1=LLMContradictionView(
                    position="iPhone sales will grow in 2025",
                    source="Wedbush Securities",
                ),
                view_2=LLMContradictionView(
                    position="iPhone sales will decline due to saturation",
                    source="Counterpoint Research",
                ),
            ),
        ],
        sources=[
            LLMSource(
                type="report",
                title="IDC Smartphone Market Share Report",
                url="https://idc.com/report",
                date="2025-01-10",
                credibility="high",
            ),
            LLMSource(
                type="news",
                title="Apple Q4 Earnings Coverage",
                url="https://news.example.com/apple",
                date="2025-01-15",
                credibility="high",
            ),
        ],
        questions=[
            LLMQuestion(
                type="data",
                question="What are the exact revenue figures for Services segment?",
                priority="high",
                context="Mentioned services growth but need specific numbers",
            ),
            LLMQuestion(
                type="research",
                question="How do competitors compare in ecosystem integration?",
                priority="medium",
                context="Need deeper competitive analysis",
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
        assert agent.agent_name == "research"

    def test_timeout_key(self, agent):
        """Test timeout key."""
        assert agent.get_timeout_key() == "research_task"


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent, sample_task):
        """Test validation fails without session_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "task": sample_task,
                "round": 1,
            })
        assert "session_id" in str(exc_info.value.message)

    def test_validate_missing_task(self, agent):
        """Test validation fails without task."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "round": 1,
            })
        assert "task" in str(exc_info.value.message)

    def test_validate_task_not_dict(self, agent):
        """Test validation fails if task is not a dict."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "task": "not a dict",
                "round": 1,
            })
        assert "dictionary" in str(exc_info.value.message)

    def test_validate_task_missing_id(self, agent):
        """Test validation fails if task missing id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "task": {"description": "test"},
                "round": 1,
            })
        assert "id" in str(exc_info.value.message)

    def test_validate_missing_round(self, agent, sample_task):
        """Test validation fails without round."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "task": sample_task,
            })
        assert "round" in str(exc_info.value.message)

    def test_validate_success(self, agent, sample_task):
        """Test successful validation."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "task": sample_task,
            "round": 1,
        })


# =============================================================================
# SEARCH QUERY GENERATION TESTS
# =============================================================================


class TestSearchQueryGeneration:
    """Test search query generation."""

    def test_generate_queries_from_predefined(self, agent, sample_task, sample_entity_context):
        """Test using predefined search queries."""
        queries = agent._generate_search_queries(sample_task, sample_entity_context)

        # Should use predefined queries
        assert "Apple market position 2025" in queries
        assert len(queries) <= 5

    def test_generate_queries_without_predefined(self, agent, sample_entity_context):
        """Test generating queries when none predefined."""
        task = {
            "id": "r1",
            "description": "Research competitive position",
            "focus": "Market advantages",
        }

        queries = agent._generate_search_queries(task, sample_entity_context)

        assert len(queries) >= 3
        # Should include entity name
        assert any("Apple" in q for q in queries)

    def test_generate_queries_with_source_types(self, agent, sample_entity_context):
        """Test queries include source type hints."""
        task = {
            "id": "r1",
            "description": "Research market trends",
            "source_types": ["news", "reports"],
        }

        queries = agent._generate_search_queries(task, sample_entity_context)

        # Should have news and report related queries
        assert any("news" in q.lower() for q in queries) or any("report" in q.lower() for q in queries)


# =============================================================================
# WEB SEARCH TESTS
# =============================================================================


class TestWebSearch:
    """Test web search execution."""

    @pytest.mark.asyncio
    async def test_execute_searches(self, agent, mock_search_client):
        """Test search execution."""
        queries = ["Apple market position", "Apple competitive analysis"]

        results = await agent._execute_searches(queries)

        assert len(results) > 0
        assert mock_search_client.search.call_count >= len(queries)

    @pytest.mark.asyncio
    async def test_search_deduplication(self, agent, mock_search_client):
        """Test duplicate URLs are removed."""
        # Return same results for different queries
        mock_search_client.search = AsyncMock(return_value=[
            SearchResult(
                title="Same Article",
                url="https://same-url.com",
                snippet="Test",
            ),
        ])

        queries = ["query 1", "query 2"]
        results = await agent._execute_searches(queries)

        # Should deduplicate by URL
        urls = [r["url"] for r in results]
        assert len(urls) == len(set(urls))

    @pytest.mark.asyncio
    async def test_search_failure_handled(self, agent, mock_search_client):
        """Test search failure is handled."""
        mock_search_client.search = AsyncMock(side_effect=Exception("Search error"))

        results = await agent._execute_searches(["test query"])

        # Should return empty list, not raise
        assert results == []


# =============================================================================
# LLM PROCESSING TESTS
# =============================================================================


class TestLLMProcessing:
    """Test LLM processing."""

    @pytest.mark.asyncio
    async def test_process_with_llm_success(
        self, agent, mock_llm, sample_task, sample_entity_context, sample_brief_context, sample_llm_output
    ):
        """Test successful LLM processing."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent._process_with_llm(
            task_id="r1",
            round_num=1,
            task=sample_task,
            entity_context=sample_entity_context,
            brief_context=sample_brief_context,
            search_results=[
                {"title": "Test", "url": "https://test.com", "snippet": "Test content"},
            ],
            previous_findings=[],
        )

        assert result.task_id == "r1"
        assert result.round == 1
        assert len(result.key_findings) > 0

    @pytest.mark.asyncio
    async def test_process_with_llm_fallback(
        self, agent, mock_llm, sample_task, sample_entity_context, sample_brief_context
    ):
        """Test fallback when LLM fails."""
        mock_llm.create_structured = AsyncMock(side_effect=Exception("LLM Error"))

        result = await agent._process_with_llm(
            task_id="r1",
            round_num=1,
            task=sample_task,
            entity_context=sample_entity_context,
            brief_context=sample_brief_context,
            search_results=[
                {"title": "Test Article", "url": "https://test.com", "snippet": "Test content"},
            ],
            previous_findings=[],
        )

        assert result.task_id == "r1"
        assert result.status in ("partial", "failed")
        # Should extract basic findings from search results
        assert len(result.sources) > 0


# =============================================================================
# FALLBACK TESTS
# =============================================================================


class TestFallbackBehavior:
    """Test fallback behavior."""

    def test_fallback_with_search_results(self, agent, sample_task):
        """Test fallback extracts findings from search results."""
        search_results = [
            {
                "title": "Test Article",
                "url": "https://test.com",
                "snippet": "Important finding about market trends.",
                "date": "2025-01-15",
            },
        ]

        result = agent._create_fallback_output(
            task_id="r1",
            round_num=1,
            task=sample_task,
            search_results=search_results,
        )

        assert result.task_id == "r1"
        assert result.status == "partial"
        assert len(result.key_findings) > 0
        assert len(result.sources) > 0

    def test_fallback_without_search_results(self, agent, sample_task):
        """Test fallback with no search results."""
        result = agent._create_fallback_output(
            task_id="r1",
            round_num=1,
            task=sample_task,
            search_results=[],
        )

        assert result.status == "failed"
        assert len(result.questions) > 0


# =============================================================================
# CONVERSION TESTS
# =============================================================================


class TestConversions:
    """Test LLM output conversions."""

    def test_convert_to_result(self, agent, sample_llm_output):
        """Test ResearchResult conversion."""
        result = agent._convert_to_result(sample_llm_output, "r1", 1)

        assert result["task_id"] == "r1"
        assert result["round"] == 1
        assert result["status"] == "done"
        assert len(result["key_findings"]) == 3
        assert len(result["themes"]) == 2
        assert len(result["contradictions"]) == 1
        assert len(result["sources"]) == 2
        assert len(result["questions"]) == 2

    def test_convert_findings(self, agent, sample_llm_output):
        """Test finding conversion."""
        result = agent._convert_to_result(sample_llm_output, "r1", 1)

        finding = result["key_findings"][0]
        assert finding["type"] == "fact"
        assert finding["confidence"] == "high"
        assert "market share" in finding["finding"].lower()

    def test_convert_themes(self, agent, sample_llm_output):
        """Test theme conversion."""
        result = agent._convert_to_result(sample_llm_output, "r1", 1)

        theme = result["themes"][0]
        assert theme["theme"] == "Ecosystem Strength"
        assert theme["sentiment"] == "positive"
        assert len(theme["points"]) > 0

    def test_convert_contradictions(self, agent, sample_llm_output):
        """Test contradiction conversion."""
        result = agent._convert_to_result(sample_llm_output, "r1", 1)

        contradiction = result["contradictions"][0]
        assert "iPhone" in contradiction["topic"]
        assert "view_1" in contradiction
        assert "view_2" in contradiction

    def test_convert_sources(self, agent, sample_llm_output):
        """Test source conversion."""
        result = agent._convert_to_result(sample_llm_output, "r1", 1)

        source = result["sources"][0]
        assert source["type"] == "report"
        assert source["credibility"] == "high"

    def test_convert_questions(self, agent, sample_llm_output):
        """Test question conversion."""
        result = agent._convert_to_result(sample_llm_output, "r1", 1)

        data_questions = [q for q in result["questions"] if q["type"] == "data"]
        research_questions = [q for q in result["questions"] if q["type"] == "research"]

        assert len(data_questions) >= 1
        assert len(research_questions) >= 1

    def test_convert_invalid_values(self, agent):
        """Test conversion with invalid enum values."""
        output = LLMResearchOutput(
            task_id="r1",
            round=1,
            status="invalid",
            summary="Test",
            key_findings=[
                LLMFinding(
                    finding="Test finding",
                    type="invalid_type",
                    confidence="invalid_conf",
                    source="Test",
                ),
            ],
            themes=[
                LLMTheme(
                    theme="Test",
                    points=[],
                    sentiment="invalid_sentiment",
                ),
            ],
            contradictions=[],
            sources=[
                LLMSource(
                    type="invalid_type",
                    title="Test",
                    credibility="invalid_cred",
                ),
            ],
            questions=[],
        )

        result = agent._convert_to_result(output, "r1", 1)

        # Should use defaults for invalid values
        assert result["status"] == "partial"
        assert result["key_findings"][0]["type"] == "analysis"
        assert result["themes"][0]["sentiment"] == "neutral"
        assert result["sources"][0]["type"] == "other"


# =============================================================================
# FULL EXECUTION TESTS
# =============================================================================


class TestFullExecution:
    """Test full agent execution."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, mock_llm, mock_session_manager, sample_task, sample_entity_context, sample_llm_output
    ):
        """Test successful execution."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "task": sample_task,
            "round": 1,
            "entity_context": sample_entity_context,
            "brief_context": {"goal": "Research investment potential"},
        })

        assert result["task_id"] == "r1"
        assert result["status"] == "done"
        assert "key_findings" in result
        assert "themes" in result

        # Verify state saved
        mock_session_manager.save_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_saves_correct_data_type(
        self, agent, mock_llm, mock_session_manager, sample_task, sample_llm_output
    ):
        """Test execution saves with correct data type."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        await agent.execute({
            "session_id": "sess_test123456",
            "task": sample_task,
            "round": 1,
        })

        # Check save_state call
        call_kwargs = mock_session_manager.save_state.call_args
        data_type = call_kwargs[1]["data_type"]
        data_type_str = data_type.value if hasattr(data_type, "value") else str(data_type)
        assert "research_result" in data_type_str.lower()
        assert call_kwargs[1]["task_id"] == "r1"
        assert call_kwargs[1]["round"] == 1

    @pytest.mark.asyncio
    async def test_execute_with_previous_findings(
        self, agent, mock_llm, sample_task, sample_llm_output
    ):
        """Test execution incorporates previous findings."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent.execute({
            "session_id": "sess_test123456",
            "task": sample_task,
            "round": 2,
            "previous_findings": ["Previous finding 1", "Previous finding 2"],
        })

        assert result["round"] == 2

    @pytest.mark.asyncio
    async def test_run_with_validation(
        self, agent, mock_llm, sample_task, sample_llm_output
    ):
        """Test run() with input validation."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent.run(
            session_id="sess_test123456",
            context={
                "session_id": "sess_test123456",
                "task": sample_task,
                "round": 1,
            },
        )

        assert result["task_id"] == "r1"
        assert "key_findings" in result
        assert "sources" in result
