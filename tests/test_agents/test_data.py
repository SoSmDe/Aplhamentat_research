"""
Ralph Deep Research - Data Agent Tests

Unit tests for the DataAgent.

Why these tests:
- Verify data collection from various API sources
- Test metric extraction and structuring
- Test error handling when API fails
- Test fallback behavior when LLM fails
- Test question generation for anomalies
- Verify state persistence
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.data import (
    DataAgent,
    LLMDataOutput,
    LLMMetricValue,
    LLMDataTable,
    LLMDataError,
    LLMQuestion,
)
from src.api.schemas import (
    DataFreshness,
    DataSource,
    Priority,
    QuestionType,
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
def mock_api_client():
    """Create mock API client."""
    client = MagicMock()
    client.get_stock_data = AsyncMock(return_value={
        "ticker": "AAPL",
        "price": 185.50,
        "market_cap": 2900000000000,
        "pe_ratio": 28.5,
        "dividend_yield": 0.5,
    })
    return client


@pytest.fixture
def agent(mock_llm, mock_session_manager, mock_api_client):
    """Create DataAgent for testing."""
    return DataAgent(
        mock_llm,
        mock_session_manager,
        api_client=mock_api_client,
    )


@pytest.fixture
def sample_task():
    """Create sample DataTask for testing."""
    return {
        "id": "d1",
        "scope_item_id": 1,
        "description": "Collect financial metrics for Apple Inc",
        "source": "financial_api",
        "priority": "high",
        "expected_output": "Price, market cap, P/E ratio, dividend yield",
        "status": "pending",
    }


@pytest.fixture
def sample_entity_context():
    """Create sample entity context."""
    return {
        "name": "Apple Inc",
        "type": "company",
        "identifiers": {
            "ticker": "AAPL",
            "website": "https://apple.com",
            "country": "USA",
            "exchange": "NASDAQ",
        },
        "brief_description": "Technology company",
        "sector": "Technology",
    }


@pytest.fixture
def sample_llm_output():
    """Create sample LLM output."""
    return LLMDataOutput(
        task_id="d1",
        round=1,
        status="done",
        metrics={
            "price": LLMMetricValue(
                value=185.50,
                unit="USD",
                period="current",
                as_of_date="2025-01-19",
            ),
            "market_cap": LLMMetricValue(
                value=2900000000000,
                unit="USD",
                period="current",
                as_of_date="2025-01-19",
            ),
            "pe_ratio": LLMMetricValue(
                value=28.5,
                unit=None,
                period="TTM",
                as_of_date="2025-01-19",
            ),
        },
        tables=[
            LLMDataTable(
                name="Quarterly Revenue",
                headers=["Quarter", "Revenue (B)"],
                rows=[["Q1 2024", "119.5"], ["Q2 2024", "117.3"]],
            ),
        ],
        raw_data={"ticker": "AAPL", "price": 185.50},
        metadata={
            "source": "Yahoo Finance",
            "api_used": "financial_api",
            "timestamp": "2025-01-19T12:00:00Z",
            "data_freshness": "daily",
        },
        questions=[
            LLMQuestion(
                type="research",
                question="Why did dividend yield decrease compared to last year?",
                context="Noticed dividend yield dropped from 0.7% to 0.5%",
                priority="medium",
            ),
        ],
        errors=[],
    )


# =============================================================================
# BASIC PROPERTIES TESTS
# =============================================================================


class TestAgentProperties:
    """Test agent properties."""

    def test_agent_name(self, agent):
        """Test agent_name property."""
        assert agent.agent_name == "data"

    def test_timeout_key(self, agent):
        """Test timeout key."""
        assert agent.get_timeout_key() == "data_task"


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
# API DATA FETCHING TESTS
# =============================================================================


class TestAPIDataFetching:
    """Test API data fetching."""

    @pytest.mark.asyncio
    async def test_fetch_financial_api(self, agent, mock_api_client, sample_entity_context):
        """Test fetching from financial API."""
        result = await agent._fetch_api_data(
            source="financial_api",
            description="Get stock data",
            entity_context=sample_entity_context,
            available_apis=["financial_api"],
        )

        assert result["source"] == "financial_api"
        assert result["raw"]["ticker"] == "AAPL"
        mock_api_client.get_stock_data.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_fetch_api_not_available(self, agent, sample_entity_context):
        """Test fetching when API not available."""
        result = await agent._fetch_api_data(
            source="financial_api",
            description="Get stock data",
            entity_context=sample_entity_context,
            available_apis=["web_search"],  # financial_api not available
        )

        assert result["raw"] == {}

    @pytest.mark.asyncio
    async def test_fetch_api_failure(self, agent, mock_api_client, sample_entity_context):
        """Test handling API failure."""
        mock_api_client.get_stock_data = AsyncMock(side_effect=Exception("API Error"))

        result = await agent._fetch_api_data(
            source="financial_api",
            description="Get stock data",
            entity_context=sample_entity_context,
            available_apis=["financial_api"],
        )

        assert "error" in result
        assert result["raw"] == {}

    def test_extract_ticker_from_identifiers(self, agent, sample_entity_context):
        """Test ticker extraction from identifiers."""
        ticker = agent._extract_ticker(sample_entity_context)
        assert ticker == "AAPL"

    def test_extract_ticker_from_name(self, agent):
        """Test ticker extraction from uppercase name."""
        context = {"name": "MSFT"}
        ticker = agent._extract_ticker(context)
        assert ticker == "MSFT"

    def test_extract_ticker_no_ticker(self, agent):
        """Test ticker extraction when no ticker available."""
        context = {"name": "Microsoft Corporation"}
        ticker = agent._extract_ticker(context)
        assert ticker is None


# =============================================================================
# LLM PROCESSING TESTS
# =============================================================================


class TestLLMProcessing:
    """Test LLM processing."""

    @pytest.mark.asyncio
    async def test_process_with_llm_success(
        self, agent, mock_llm, sample_task, sample_entity_context, sample_llm_output
    ):
        """Test successful LLM processing."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent._process_with_llm(
            task_id="d1",
            round_num=1,
            task=sample_task,
            entity_context=sample_entity_context,
            api_data={"source": "financial_api", "raw": {"price": 185.50}},
        )

        assert result.task_id == "d1"
        assert result.round == 1
        assert len(result.metrics) > 0

    @pytest.mark.asyncio
    async def test_process_with_llm_fallback(
        self, agent, mock_llm, sample_task, sample_entity_context
    ):
        """Test fallback when LLM fails."""
        mock_llm.create_structured = AsyncMock(side_effect=Exception("LLM Error"))

        result = await agent._process_with_llm(
            task_id="d1",
            round_num=1,
            task=sample_task,
            entity_context=sample_entity_context,
            api_data={"source": "financial_api", "raw": {"price": 185.50}},
        )

        assert result.task_id == "d1"
        assert result.status in ("done", "partial")
        # Should have extracted basic data from api_data
        assert len(result.metrics) > 0


# =============================================================================
# FALLBACK TESTS
# =============================================================================


class TestFallbackBehavior:
    """Test fallback behavior."""

    def test_fallback_with_api_data(self, agent, sample_task):
        """Test fallback extracts data from API response."""
        result = agent._create_fallback_output(
            task_id="d1",
            round_num=1,
            task=sample_task,
            api_data={
                "source": "financial_api",
                "raw": {
                    "price": 185.50,
                    "volume": 50000000,
                },
            },
        )

        assert result.task_id == "d1"
        assert result.status == "done"
        assert "price" in result.metrics
        assert result.metrics["price"].value == 185.50

    def test_fallback_with_empty_api_data(self, agent, sample_task):
        """Test fallback with no API data."""
        result = agent._create_fallback_output(
            task_id="d1",
            round_num=1,
            task=sample_task,
            api_data={
                "source": "financial_api",
                "raw": {},
            },
        )

        assert result.status == "partial"
        assert len(result.metrics) == 0

    def test_fallback_with_api_error(self, agent, sample_task):
        """Test fallback with API error."""
        result = agent._create_fallback_output(
            task_id="d1",
            round_num=1,
            task=sample_task,
            api_data={
                "source": "financial_api",
                "raw": {},
                "error": "Connection timeout",
            },
        )

        assert result.status == "failed"
        assert len(result.errors) > 0
        assert result.errors[0].error == "Connection timeout"


# =============================================================================
# CONVERSION TESTS
# =============================================================================


class TestConversions:
    """Test LLM output conversions."""

    def test_convert_to_result(self, agent, sample_llm_output):
        """Test DataResult conversion."""
        result = agent._convert_to_result(sample_llm_output, "d1", 1)

        assert result["task_id"] == "d1"
        assert result["round"] == 1
        assert result["status"] == "done"
        assert len(result["metrics"]) == 3
        assert len(result["tables"]) == 1
        assert len(result["questions"]) == 1

        # Check metric structure
        price_metric = result["metrics"]["price"]
        assert price_metric["value"] == 185.50
        assert price_metric["unit"] == "USD"

    def test_convert_invalid_status(self, agent):
        """Test conversion with invalid status."""
        output = LLMDataOutput(
            task_id="d1",
            round=1,
            status="invalid",
            metrics={},
            tables=[],
            raw_data=None,
            metadata=None,
            questions=[],
            errors=[],
        )

        result = agent._convert_to_result(output, "d1", 1)

        # Should default to partial
        assert result["status"] == "partial"

    def test_convert_questions(self, agent, sample_llm_output):
        """Test question conversion."""
        result = agent._convert_to_result(sample_llm_output, "d1", 1)

        question = result["questions"][0]
        assert question["type"] == "research"
        assert "dividend yield" in question["question"].lower()
        assert question["source_task_id"] == "d1"

    def test_convert_metadata(self, agent, sample_llm_output):
        """Test metadata conversion."""
        result = agent._convert_to_result(sample_llm_output, "d1", 1)

        metadata = result["metadata"]
        assert metadata["source"] == "Yahoo Finance"
        assert metadata["data_freshness"] == "daily"


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
            "available_apis": ["financial_api"],
        })

        assert result["task_id"] == "d1"
        assert result["status"] == "done"
        assert "metrics" in result

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
        assert "data_result" in data_type_str.lower()
        assert call_kwargs[1]["task_id"] == "d1"
        assert call_kwargs[1]["round"] == 1

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

        assert result["task_id"] == "d1"
        assert "metrics" in result
