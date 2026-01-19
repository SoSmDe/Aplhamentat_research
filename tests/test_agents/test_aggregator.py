"""
Ralph Deep Research - Aggregator Agent Tests

Unit tests for the AggregatorAgent.

Why these tests:
- Verify aggregation of data and research results
- Test section generation per scope item
- Test key insight extraction
- Test recommendation generation with confidence
- Test contradiction detection
- Test coverage summary calculation
- Test fallback behavior when LLM fails
- Verify state persistence
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.aggregator import (
    AggregatorAgent,
    LLMAggregatorOutput,
    LLMKeyInsight,
    LLMSection,
    LLMDataHighlight,
    LLMContradiction,
    LLMRecommendation,
    LLMActionItem,
    LLMCoverageSummary,
)
from src.api.schemas import (
    Confidence,
    Priority,
    Sentiment,
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
    """Create AggregatorAgent for testing."""
    return AggregatorAgent(mock_llm, mock_session_manager)


@pytest.fixture
def sample_brief():
    """Create sample brief for testing."""
    return {
        "brief_id": "brief_12345678",
        "version": 1,
        "status": "approved",
        "goal": "Evaluate Realty Income (O) as a long-term dividend investment",
        "user_context": {
            "intent": "investment",
            "horizon": "5+ years",
            "risk_profile": "moderate",
        },
        "scope": [
            {
                "id": 1,
                "topic": "Financial Health",
                "type": "data",
                "details": "Dividends, debt levels, valuation multiples",
            },
            {
                "id": 2,
                "topic": "Business Model",
                "type": "research",
                "details": "Triple-net lease strategy",
            },
            {
                "id": 3,
                "topic": "Risks",
                "type": "both",
                "details": "Interest rate sensitivity, tenant concentration",
            },
        ],
        "output_formats": ["pdf", "excel"],
        "constraints": {
            "focus_areas": ["dividend sustainability", "growth prospects"],
            "exclude": ["short-term trading"],
        },
    }


@pytest.fixture
def sample_data_results():
    """Create sample data results."""
    return [
        {
            "task_id": "d1",
            "round": 1,
            "status": "done",
            "metrics": {
                "dividend_yield": {"value": 5.2, "unit": "%", "period": "TTM"},
                "payout_ratio": {"value": 76, "unit": "%", "period": "TTM"},
                "debt_to_equity": {"value": 0.85, "unit": "", "period": "Q3 2024"},
            },
            "tables": [
                {
                    "name": "Dividend History",
                    "headers": ["Year", "Dividend", "Growth"],
                    "rows": [
                        ["2024", "$3.10", "3.0%"],
                        ["2023", "$3.01", "3.5%"],
                        ["2022", "$2.91", "4.2%"],
                    ],
                },
            ],
        },
        {
            "task_id": "d2",
            "round": 1,
            "status": "done",
            "metrics": {
                "pe_ratio": {"value": 38.5, "unit": "", "period": "TTM"},
                "ffo_per_share": {"value": 3.85, "unit": "$", "period": "2024E"},
            },
            "tables": [],
        },
    ]


@pytest.fixture
def sample_research_results():
    """Create sample research results."""
    return [
        {
            "task_id": "r1",
            "round": 1,
            "status": "done",
            "summary": "Triple-net lease model provides stable, predictable income streams.",
            "key_findings": [
                {
                    "finding": "Realty Income has maintained 107 consecutive quarterly dividend increases",
                    "type": "fact",
                    "confidence": "high",
                    "source": "Company IR",
                },
                {
                    "finding": "Management expects 4-5% annual dividend growth going forward",
                    "type": "opinion",
                    "confidence": "medium",
                    "source": "Q3 2024 Earnings Call",
                },
            ],
            "themes": [
                {
                    "theme": "Dividend Reliability",
                    "points": ["Long track record", "Conservative payout"],
                    "sentiment": "positive",
                },
            ],
            "contradictions": [],
            "sources": [
                {"type": "website", "title": "Realty Income IR", "url": "https://ir.realtyincome.com"},
            ],
        },
        {
            "task_id": "r2",
            "round": 1,
            "status": "done",
            "summary": "Interest rate environment poses both risks and opportunities for REITs.",
            "key_findings": [
                {
                    "finding": "Rising rates historically pressure REIT valuations short-term",
                    "type": "analysis",
                    "confidence": "high",
                    "source": "NAREIT Research",
                },
            ],
            "themes": [
                {
                    "theme": "Interest Rate Sensitivity",
                    "points": ["Higher borrowing costs", "Valuation compression"],
                    "sentiment": "negative",
                },
            ],
            "contradictions": [
                {
                    "topic": "Rate Impact",
                    "view_1": {"position": "Higher rates hurt REITs", "source": "Bear analyst"},
                    "view_2": {"position": "O can pass through rent increases", "source": "Bull analyst"},
                },
            ],
            "sources": [],
        },
    ]


@pytest.fixture
def sample_llm_output():
    """Create sample LLM aggregator output."""
    return LLMAggregatorOutput(
        executive_summary="Realty Income (O) represents a solid long-term dividend investment with strong fundamentals. The company's 107 consecutive quarterly dividend increases demonstrate exceptional reliability. While interest rate sensitivity exists, the triple-net lease model provides stability. Overall verdict is positive for income-focused investors with 5+ year horizons.",
        key_insights=[
            LLMKeyInsight(
                insight="Dividend track record is exceptional with 107 consecutive quarterly increases",
                supporting_data=["d1: dividend history", "r1: management commentary"],
                importance="high",
            ),
            LLMKeyInsight(
                insight="5.2% dividend yield with 76% payout ratio suggests sustainable dividends",
                supporting_data=["d1: dividend_yield", "d1: payout_ratio"],
                importance="high",
            ),
            LLMKeyInsight(
                insight="Interest rate sensitivity is manageable due to triple-net lease structure",
                supporting_data=["r2: rate analysis"],
                importance="medium",
            ),
        ],
        sections=[
            LLMSection(
                title="Financial Health",
                brief_scope_id=1,
                summary="Strong financial position with sustainable dividend and manageable debt.",
                data_highlights=[
                    LLMDataHighlight(metric="Dividend Yield", value="5.2% TTM"),
                    LLMDataHighlight(metric="Payout Ratio", value="76% - conservative level"),
                    LLMDataHighlight(metric="Debt/Equity", value="0.85x - moderate leverage"),
                ],
                analysis="The company maintains a healthy balance sheet with investment-grade credit ratings. Debt levels are manageable and the dividend is well-covered by FFO.",
                key_points=["Investment-grade credit", "Conservative payout", "Stable cash flows"],
                sentiment="positive",
                charts_suggested=["dividend growth chart", "debt history"],
            ),
            LLMSection(
                title="Business Model",
                brief_scope_id=2,
                summary="Triple-net lease model provides stable, predictable income with inflation protection.",
                data_highlights=[],
                analysis="Realty Income's triple-net lease structure means tenants pay for property taxes, insurance, and maintenance. This creates predictable cash flows and natural inflation protection through rent escalators.",
                key_points=["Triple-net leases", "Inflation protection", "Diversified tenant base"],
                sentiment="positive",
                charts_suggested=["tenant diversification pie chart"],
            ),
            LLMSection(
                title="Risks",
                brief_scope_id=3,
                summary="Interest rate sensitivity and retail tenant exposure are primary risks.",
                data_highlights=[],
                analysis="Rising interest rates can compress REIT valuations and increase borrowing costs. Additionally, some retail tenants face secular headwinds from e-commerce.",
                key_points=["Interest rate risk", "Retail exposure", "Economic sensitivity"],
                sentiment="mixed",
                charts_suggested=["interest rate correlation chart"],
            ),
        ],
        contradictions_found=[
            LLMContradiction(
                topic="Interest Rate Impact",
                sources=["Bear analyst", "Bull analyst"],
                resolution="While rates do pressure valuations short-term, O's triple-net structure and tenant quality mitigate operational impact",
            ),
        ],
        recommendation=LLMRecommendation(
            verdict="Suitable for long-term dividend investors seeking stable income",
            confidence="high",
            confidence_reasoning="Strong fundamentals, exceptional dividend track record, and proven business model",
            reasoning="Realty Income meets the criteria for a long-term dividend investment: reliable income, growth potential, and manageable risks. The 5.2% yield with 4-5% expected growth aligns well with income-focused objectives.",
            pros=["107 consecutive dividend increases", "5.2% yield", "Conservative payout ratio", "Investment-grade credit"],
            cons=["Interest rate sensitivity", "Premium valuation (38x P/E)", "Retail tenant exposure"],
            action_items=[
                LLMActionItem(action="Consider initiating position at current levels", priority="high", rationale="Attractive yield with strong fundamentals"),
                LLMActionItem(action="Monitor interest rate trajectory", priority="medium", rationale="Key risk factor for valuation"),
                LLMActionItem(action="Review tenant concentration quarterly", priority="low", rationale="Long-term consideration"),
            ],
            risks_to_monitor=["Federal Reserve rate decisions", "Retail tenant defaults", "Debt refinancing costs"],
        ),
        coverage_summary=[
            LLMCoverageSummary(topic="Financial Health", coverage_percent=95.0, gaps=["Long-term debt maturity schedule"]),
            LLMCoverageSummary(topic="Business Model", coverage_percent=90.0, gaps=["International expansion details"]),
            LLMCoverageSummary(topic="Risks", coverage_percent=85.0, gaps=["Detailed stress test scenarios"]),
        ],
    )


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestAgentProperties:
    """Test agent property methods."""

    def test_agent_name(self, agent):
        """Agent name should be 'aggregator'."""
        assert agent.agent_name == "aggregator"

    def test_timeout_key(self, agent):
        """Timeout key should be 'aggregation'."""
        assert agent.get_timeout_key() == "aggregation"


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent):
        """Should fail without session_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({})
        assert "session_id" in str(exc_info.value)

    def test_validate_missing_brief(self, agent):
        """Should fail without brief."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({"session_id": "sess_123"})
        assert "brief" in str(exc_info.value)

    def test_validate_brief_not_dict(self, agent):
        """Should fail if brief is not a dict."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({"session_id": "sess_123", "brief": "not a dict"})
        assert "dictionary" in str(exc_info.value)

    def test_validate_missing_scope(self, agent):
        """Should fail if brief has no scope."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "brief": {"goal": "test"},
            })
        assert "scope" in str(exc_info.value)

    def test_validate_missing_rounds(self, agent):
        """Should fail without rounds_completed."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "brief": {"scope": [{"id": 1, "topic": "test"}]},
            })
        assert "rounds_completed" in str(exc_info.value)

    def test_validate_success(self, agent, sample_brief):
        """Should pass with valid input."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "brief": sample_brief,
            "rounds_completed": 3,
        })


class TestContextFormatting:
    """Test context formatting methods."""

    def test_format_brief_context(self, agent, sample_brief):
        """Should format brief context correctly."""
        result = agent._format_brief_context(sample_brief)

        assert "Goal" in result
        assert "Evaluate Realty Income" in result
        assert "Scope Items" in result
        assert "Financial Health" in result
        assert "Business Model" in result

    def test_format_data_results(self, agent, sample_data_results):
        """Should format data results correctly."""
        result = agent._format_data_results(sample_data_results)

        assert "d1" in result
        assert "dividend_yield" in result
        assert "5.2" in result

    def test_format_data_results_empty(self, agent):
        """Should handle empty data results."""
        result = agent._format_data_results([])
        assert "No data results available" in result

    def test_format_research_results(self, agent, sample_research_results):
        """Should format research results correctly."""
        result = agent._format_research_results(sample_research_results)

        assert "r1" in result
        assert "Triple-net" in result
        assert "Key Findings" in result

    def test_format_research_results_empty(self, agent):
        """Should handle empty research results."""
        result = agent._format_research_results([])
        assert "No research results available" in result


class TestLLMProcessing:
    """Test LLM processing and synthesis."""

    @pytest.mark.asyncio
    async def test_synthesize_with_llm_success(
        self, agent, mock_llm, sample_brief, sample_llm_output
    ):
        """Should synthesize successfully with LLM."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent._synthesize_with_llm(
            brief_context="Brief context",
            data_context="Data context",
            research_context="Research context",
            goal="Evaluate investment",
            scope=[{"id": 1, "topic": "Test"}],
        )

        assert result.executive_summary is not None
        assert len(result.key_insights) > 0
        assert len(result.sections) > 0
        assert result.recommendation is not None

    @pytest.mark.asyncio
    async def test_synthesize_with_llm_fallback(self, agent, mock_llm, sample_brief):
        """Should use fallback when LLM fails."""
        mock_llm.create_structured = AsyncMock(side_effect=Exception("LLM error"))

        scope = sample_brief["scope"]
        result = await agent._synthesize_with_llm(
            brief_context="Brief context",
            data_context="Data context",
            research_context="Research context",
            goal="Evaluate investment",
            scope=scope,
        )

        assert "failed" in result.executive_summary.lower() or "manual" in result.executive_summary.lower()
        assert len(result.sections) == len(scope)


class TestResultConversion:
    """Test conversion of LLM output to AggregatedResearch."""

    def test_convert_to_result(
        self, agent, sample_llm_output, sample_data_results, sample_research_results
    ):
        """Should convert LLM output to proper result format."""
        result = agent._convert_to_result(
            llm_output=sample_llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=sample_data_results,
            all_research_results=sample_research_results,
            rounds_completed=3,
        )

        assert result["session_id"] == "sess_123"
        assert result["brief_id"] == "brief_123"
        assert "executive_summary" in result
        assert "key_insights" in result
        assert "sections" in result
        assert "recommendation" in result

    def test_convert_key_insights(
        self, agent, sample_llm_output, sample_data_results, sample_research_results
    ):
        """Should convert key insights correctly."""
        result = agent._convert_to_result(
            llm_output=sample_llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=sample_data_results,
            all_research_results=sample_research_results,
            rounds_completed=3,
        )

        insights = result["key_insights"]
        assert len(insights) > 0
        assert "insight" in insights[0]
        assert "importance" in insights[0]

    def test_convert_sections(
        self, agent, sample_llm_output, sample_data_results, sample_research_results
    ):
        """Should convert sections correctly."""
        result = agent._convert_to_result(
            llm_output=sample_llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=sample_data_results,
            all_research_results=sample_research_results,
            rounds_completed=3,
        )

        sections = result["sections"]
        assert len(sections) == 3
        assert sections[0]["title"] == "Financial Health"
        assert sections[0]["brief_scope_id"] == 1

    def test_convert_recommendation(
        self, agent, sample_llm_output, sample_data_results, sample_research_results
    ):
        """Should convert recommendation correctly."""
        result = agent._convert_to_result(
            llm_output=sample_llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=sample_data_results,
            all_research_results=sample_research_results,
            rounds_completed=3,
        )

        rec = result["recommendation"]
        assert "verdict" in rec
        assert "confidence" in rec
        assert "pros" in rec
        assert "cons" in rec
        assert "action_items" in rec

    def test_convert_metadata(
        self, agent, sample_llm_output, sample_data_results, sample_research_results
    ):
        """Should calculate metadata correctly."""
        result = agent._convert_to_result(
            llm_output=sample_llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=sample_data_results,
            all_research_results=sample_research_results,
            rounds_completed=3,
        )

        metadata = result["metadata"]
        assert metadata["total_rounds"] == 3
        assert metadata["total_data_tasks"] == 2
        assert metadata["total_research_tasks"] == 2
        assert metadata["sources_count"] == 1  # One source in sample


class TestFallbackBehavior:
    """Test fallback when LLM fails."""

    def test_fallback_output_structure(self, agent, sample_brief):
        """Fallback output should have correct structure."""
        scope = sample_brief["scope"]
        goal = sample_brief["goal"]

        result = agent._create_fallback_output(goal, scope)

        assert result.executive_summary is not None
        assert len(result.sections) == len(scope)
        assert result.recommendation is not None
        assert result.recommendation.confidence == "low"

    def test_fallback_sections_match_scope(self, agent, sample_brief):
        """Fallback sections should match scope items."""
        scope = sample_brief["scope"]
        goal = sample_brief["goal"]

        result = agent._create_fallback_output(goal, scope)

        for i, section in enumerate(result.sections):
            assert section.brief_scope_id == scope[i]["id"]
            assert section.title == scope[i]["topic"]


class TestFullExecution:
    """Test full agent execution flow."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, mock_llm, mock_session_manager,
        sample_brief, sample_data_results, sample_research_results,
        sample_llm_output
    ):
        """Should execute complete aggregation successfully."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        context = {
            "session_id": "sess_123",
            "brief": sample_brief,
            "all_data_results": sample_data_results,
            "all_research_results": sample_research_results,
            "rounds_completed": 3,
        }

        result = await agent.execute(context)

        assert result["session_id"] == "sess_123"
        assert "executive_summary" in result
        assert len(result["sections"]) > 0

    @pytest.mark.asyncio
    async def test_execute_saves_result(
        self, agent, mock_llm, mock_session_manager,
        sample_brief, sample_data_results, sample_research_results,
        sample_llm_output
    ):
        """Should save result to session manager."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        context = {
            "session_id": "sess_123",
            "brief": sample_brief,
            "all_data_results": sample_data_results,
            "all_research_results": sample_research_results,
            "rounds_completed": 3,
        }

        await agent.execute(context)

        mock_session_manager.save_state.assert_called_once()
        call_args = mock_session_manager.save_state.call_args
        assert call_args.kwargs["session_id"] == "sess_123"

    @pytest.mark.asyncio
    async def test_run_with_validation(
        self, agent, mock_llm, sample_brief, sample_llm_output
    ):
        """Should validate input before execution."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        with pytest.raises(InvalidInputError):
            await agent.run("sess_123", {})  # Missing required fields


class TestEnumConversions:
    """Test enum value conversions."""

    def test_invalid_confidence_fallback(self, agent):
        """Should handle invalid confidence values."""
        llm_output = LLMAggregatorOutput(
            executive_summary="Test summary that is long enough to pass validation checks and should be at least 100 characters",
            key_insights=[
                LLMKeyInsight(insight="Test", supporting_data=[], importance="invalid")
            ],
            sections=[],
            contradictions_found=[],
            recommendation=LLMRecommendation(
                verdict="Test",
                confidence="invalid",
                reasoning="Test reasoning",
                pros=[],
                cons=[],
                action_items=[],
                risks_to_monitor=[],
            ),
            coverage_summary=[],
        )

        result = agent._convert_to_result(
            llm_output=llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=[],
            all_research_results=[],
            rounds_completed=1,
        )

        # Should use MEDIUM as fallback
        assert result["key_insights"][0]["importance"] == "medium"
        assert result["recommendation"]["confidence"] == "medium"

    def test_invalid_sentiment_fallback(self, agent):
        """Should handle invalid sentiment values."""
        llm_output = LLMAggregatorOutput(
            executive_summary="Test summary that is long enough to pass validation checks and should be at least 100 characters",
            key_insights=[],
            sections=[
                LLMSection(
                    title="Test",
                    brief_scope_id=1,
                    sentiment="invalid",
                )
            ],
            contradictions_found=[],
            recommendation=LLMRecommendation(
                verdict="Test",
                reasoning="Test",
                pros=[],
                cons=[],
                action_items=[],
                risks_to_monitor=[],
            ),
            coverage_summary=[],
        )

        result = agent._convert_to_result(
            llm_output=llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=[],
            all_research_results=[],
            rounds_completed=1,
        )

        # Should use NEUTRAL as fallback
        assert result["sections"][0]["sentiment"] == "neutral"

    def test_invalid_priority_fallback(self, agent):
        """Should handle invalid priority values."""
        llm_output = LLMAggregatorOutput(
            executive_summary="Test summary that is long enough to pass validation checks and should be at least 100 characters",
            key_insights=[],
            sections=[],
            contradictions_found=[],
            recommendation=LLMRecommendation(
                verdict="Test",
                reasoning="Test",
                pros=[],
                cons=[],
                action_items=[
                    LLMActionItem(action="Test", priority="invalid", rationale="Test")
                ],
                risks_to_monitor=[],
            ),
            coverage_summary=[],
        )

        result = agent._convert_to_result(
            llm_output=llm_output,
            session_id="sess_123",
            brief_id="brief_123",
            all_data_results=[],
            all_research_results=[],
            rounds_completed=1,
        )

        # Should use MEDIUM as fallback
        assert result["recommendation"]["action_items"][0]["priority"] == "medium"
