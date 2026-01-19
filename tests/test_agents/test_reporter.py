"""
Ralph Deep Research - Reporter Agent Tests

Unit tests for the ReporterAgent.

Why these tests:
- Verify content specification generation for each format
- Test format normalization
- Test report configuration building
- Test file generation (with mock file generator)
- Test fallback behavior when LLM fails
- Verify state persistence
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.agents.reporter import (
    ReporterAgent,
    LLMReporterOutput,
    LLMPDFSpec,
    LLMPDFSection,
    LLMExcelSpec,
    LLMExcelSheet,
    LLMPPTXSpec,
    LLMPPTXSlide,
)
from src.api.schemas import (
    OutputFormat,
    Language,
    ReportStyle,
    DetailLevel,
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
def mock_file_generator():
    """Create mock file generator."""
    generator = MagicMock()
    generator.generate_pdf = AsyncMock(return_value="/tmp/report.pdf")
    generator.generate_excel = AsyncMock(return_value="/tmp/report.xlsx")
    generator.generate_pptx = AsyncMock(return_value="/tmp/report.pptx")
    generator.generate_csv = AsyncMock(return_value="/tmp/report.csv")
    return generator


@pytest.fixture
def agent(mock_llm, mock_session_manager):
    """Create ReporterAgent for testing (without file generator)."""
    return ReporterAgent(mock_llm, mock_session_manager)


@pytest.fixture
def agent_with_generator(mock_llm, mock_session_manager, mock_file_generator):
    """Create ReporterAgent with file generator for testing."""
    return ReporterAgent(mock_llm, mock_session_manager, mock_file_generator)


@pytest.fixture
def sample_aggregated():
    """Create sample aggregated research."""
    return {
        "session_id": "sess_12345678",
        "brief_id": "brief_12345678",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "executive_summary": "Realty Income (O) represents a solid long-term dividend investment with strong fundamentals. The company's exceptional dividend track record and stable business model make it attractive for income-focused investors.",
        "key_insights": [
            {
                "insight": "107 consecutive quarterly dividend increases",
                "supporting_data": ["Dividend history", "Company IR"],
                "importance": "high",
            },
            {
                "insight": "5.2% dividend yield with conservative 76% payout ratio",
                "supporting_data": ["Financial data"],
                "importance": "high",
            },
        ],
        "sections": [
            {
                "title": "Financial Health",
                "brief_scope_id": 1,
                "summary": "Strong financial position with sustainable dividend.",
                "data_highlights": {
                    "Dividend Yield": "5.2%",
                    "Payout Ratio": "76%",
                },
                "analysis": "The company maintains a healthy balance sheet.",
                "key_points": ["Investment-grade credit", "Conservative payout"],
                "sentiment": "positive",
                "charts_suggested": ["dividend chart"],
                "data_tables": [],
            },
            {
                "title": "Business Model",
                "brief_scope_id": 2,
                "summary": "Triple-net lease provides stable income.",
                "data_highlights": {},
                "analysis": "Predictable cash flows from long-term leases.",
                "key_points": ["Triple-net structure", "Inflation protection"],
                "sentiment": "positive",
                "charts_suggested": [],
                "data_tables": [],
            },
        ],
        "contradictions_found": [],
        "recommendation": {
            "verdict": "Suitable for long-term dividend investors",
            "confidence": "high",
            "confidence_reasoning": "Strong fundamentals",
            "reasoning": "Meets criteria for stable dividend income.",
            "pros": ["Reliable dividends", "Strong track record"],
            "cons": ["Interest rate sensitivity", "Premium valuation"],
            "action_items": [
                {"action": "Consider initiating position", "priority": "high", "rationale": "Attractive yield"},
            ],
            "risks_to_monitor": ["Interest rates", "Tenant defaults"],
        },
        "coverage_summary": {
            "Financial Health": {"topic": "Financial Health", "coverage_percent": 95, "gaps": []},
            "Business Model": {"topic": "Business Model", "coverage_percent": 90, "gaps": []},
        },
        "metadata": {
            "total_rounds": 3,
            "total_data_tasks": 5,
            "total_research_tasks": 4,
            "sources_count": 12,
            "processing_time_seconds": 45.2,
        },
    }


@pytest.fixture
def sample_llm_output():
    """Create sample LLM reporter output."""
    return LLMReporterOutput(
        pdf_spec=LLMPDFSpec(
            title="Realty Income Investment Analysis",
            subtitle="Deep Research Report",
            date="2025-01-19",
            total_pages=12,
            sections=[
                LLMPDFSection(
                    title="Executive Summary",
                    content_type="text",
                    word_count=300,
                    visuals=[],
                ),
                LLMPDFSection(
                    title="Financial Health",
                    content_type="mixed",
                    word_count=500,
                    visuals=["dividend_chart", "payout_table"],
                ),
                LLMPDFSection(
                    title="Business Model",
                    content_type="text",
                    word_count=400,
                    visuals=["tenant_pie_chart"],
                ),
                LLMPDFSection(
                    title="Recommendations",
                    content_type="text",
                    word_count=350,
                    visuals=[],
                ),
            ],
            charts_count=3,
            tables_count=2,
        ),
        excel_spec=LLMExcelSpec(
            sheets=[
                LLMExcelSheet(
                    name="Summary",
                    data_source="Key insights and metrics",
                    columns=["Metric", "Value", "Source"],
                    row_count=15,
                ),
                LLMExcelSheet(
                    name="Financials",
                    data_source="Data results",
                    columns=["Category", "Metric", "Value", "Period"],
                    row_count=50,
                ),
                LLMExcelSheet(
                    name="Raw Data",
                    data_source="All collected data",
                    columns=["Source", "Type", "Data"],
                    row_count=100,
                ),
            ],
            charts_count=2,
        ),
        pptx_spec=LLMPPTXSpec(
            total_slides=10,
            slides=[
                LLMPPTXSlide(
                    number=1,
                    title="Realty Income Analysis",
                    layout="title",
                    elements=["title", "subtitle", "date"],
                    speaker_notes="",
                ),
                LLMPPTXSlide(
                    number=2,
                    title="Executive Summary",
                    layout="content",
                    elements=["title", "bullet_points"],
                    speaker_notes="Key findings overview",
                ),
                LLMPPTXSlide(
                    number=3,
                    title="Financial Health",
                    layout="two_column",
                    elements=["title", "chart", "bullet_points"],
                    speaker_notes="",
                ),
                LLMPPTXSlide(
                    number=4,
                    title="Business Model",
                    layout="content",
                    elements=["title", "bullet_points"],
                    speaker_notes="",
                ),
                LLMPPTXSlide(
                    number=5,
                    title="Recommendation",
                    layout="content",
                    elements=["title", "verdict", "action_items"],
                    speaker_notes="",
                ),
            ],
        ),
    )


# =============================================================================
# TEST CLASSES
# =============================================================================


class TestAgentProperties:
    """Test agent property methods."""

    def test_agent_name(self, agent):
        """Agent name should be 'reporter'."""
        assert agent.agent_name == "reporter"

    def test_timeout_key(self, agent):
        """Timeout key should be 'reporting'."""
        assert agent.get_timeout_key() == "reporting"


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent):
        """Should fail without session_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({})
        assert "session_id" in str(exc_info.value)

    def test_validate_missing_aggregated(self, agent):
        """Should fail without aggregated_research."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({"session_id": "sess_123"})
        assert "aggregated_research" in str(exc_info.value)

    def test_validate_aggregated_not_dict(self, agent):
        """Should fail if aggregated_research is not a dict."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "aggregated_research": "not a dict",
            })
        assert "dictionary" in str(exc_info.value)

    def test_validate_missing_formats(self, agent, sample_aggregated):
        """Should fail without output_formats."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "aggregated_research": sample_aggregated,
            })
        assert "output_formats" in str(exc_info.value)

    def test_validate_empty_formats(self, agent, sample_aggregated):
        """Should fail with empty output_formats."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({
                "session_id": "sess_123",
                "aggregated_research": sample_aggregated,
                "output_formats": [],
            })
        assert "non-empty" in str(exc_info.value)

    def test_validate_success(self, agent, sample_aggregated):
        """Should pass with valid input."""
        # Should not raise
        agent.validate_input({
            "session_id": "sess_123",
            "aggregated_research": sample_aggregated,
            "output_formats": ["pdf"],
        })


class TestFormatNormalization:
    """Test format normalization methods."""

    def test_normalize_string_formats(self, agent):
        """Should normalize string format names."""
        result = agent._normalize_formats(["pdf", "excel", "pptx"])
        assert OutputFormat.PDF in result
        assert OutputFormat.EXCEL in result
        assert OutputFormat.PPTX in result

    def test_normalize_enum_formats(self, agent):
        """Should keep enum formats as-is."""
        result = agent._normalize_formats([OutputFormat.PDF, OutputFormat.CSV])
        assert OutputFormat.PDF in result
        assert OutputFormat.CSV in result

    def test_normalize_mixed_formats(self, agent):
        """Should handle mixed string and enum formats."""
        result = agent._normalize_formats(["pdf", OutputFormat.EXCEL])
        assert OutputFormat.PDF in result
        assert OutputFormat.EXCEL in result

    def test_normalize_uppercase_formats(self, agent):
        """Should normalize uppercase format names."""
        result = agent._normalize_formats(["PDF", "EXCEL"])
        assert OutputFormat.PDF in result
        assert OutputFormat.EXCEL in result

    def test_normalize_unknown_format_skipped(self, agent):
        """Should skip unknown formats."""
        result = agent._normalize_formats(["pdf", "unknown", "docx"])
        assert OutputFormat.PDF in result
        assert len(result) == 1

    def test_normalize_empty_defaults_to_pdf(self, agent):
        """Should default to PDF if all formats invalid."""
        result = agent._normalize_formats(["invalid"])
        assert result == [OutputFormat.PDF]


class TestContentSpecGeneration:
    """Test content specification generation."""

    @pytest.mark.asyncio
    async def test_generate_specs_success(
        self, agent, mock_llm, sample_aggregated, sample_llm_output
    ):
        """Should generate content specs successfully."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        result = await agent._generate_content_specs(
            aggregated=sample_aggregated,
            formats=[OutputFormat.PDF, OutputFormat.EXCEL],
            user_preferences={},
        )

        assert result.pdf_spec is not None
        assert result.excel_spec is not None

    @pytest.mark.asyncio
    async def test_generate_specs_fallback(self, agent, mock_llm, sample_aggregated):
        """Should use fallback when LLM fails."""
        mock_llm.create_structured = AsyncMock(side_effect=Exception("LLM error"))

        result = await agent._generate_content_specs(
            aggregated=sample_aggregated,
            formats=[OutputFormat.PDF, OutputFormat.EXCEL, OutputFormat.PPTX],
            user_preferences={},
        )

        assert result.pdf_spec is not None
        assert result.excel_spec is not None
        assert result.pptx_spec is not None


class TestFallbackSpecs:
    """Test fallback specification generation."""

    def test_fallback_pdf_spec(self, agent, sample_aggregated):
        """Should create fallback PDF spec."""
        result = agent._create_fallback_specs(
            [OutputFormat.PDF],
            sample_aggregated,
        )

        assert result.pdf_spec is not None
        assert result.pdf_spec.title is not None
        assert len(result.pdf_spec.sections) > 0

    def test_fallback_excel_spec(self, agent, sample_aggregated):
        """Should create fallback Excel spec."""
        result = agent._create_fallback_specs(
            [OutputFormat.EXCEL],
            sample_aggregated,
        )

        assert result.excel_spec is not None
        assert len(result.excel_spec.sheets) >= 2

    def test_fallback_pptx_spec(self, agent, sample_aggregated):
        """Should create fallback PPTX spec."""
        result = agent._create_fallback_specs(
            [OutputFormat.PPTX],
            sample_aggregated,
        )

        assert result.pptx_spec is not None
        assert len(result.pptx_spec.slides) > 0

    def test_fallback_sections_from_aggregated(self, agent, sample_aggregated):
        """Fallback should include sections from aggregated research."""
        result = agent._create_fallback_specs(
            [OutputFormat.PDF],
            sample_aggregated,
        )

        # Should have executive summary + sections + recommendations
        section_count = len(sample_aggregated["sections"])
        # +2 for executive summary and recommendations
        assert len(result.pdf_spec.sections) >= section_count


class TestReportConfigBuilding:
    """Test report configuration building."""

    def test_build_config_basic(self, agent, sample_llm_output):
        """Should build basic report config."""
        result = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF],
            content_specs=sample_llm_output,
            report_config={},
        )

        assert result.session_id == "sess_123"
        assert OutputFormat.PDF in result.formats
        assert result.pdf is not None

    def test_build_config_with_language(self, agent, sample_llm_output):
        """Should apply language from config."""
        result = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF],
            content_specs=sample_llm_output,
            report_config={"language": "en"},
        )

        assert result.language == Language.EN

    def test_build_config_with_style(self, agent, sample_llm_output):
        """Should apply style from config."""
        result = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF],
            content_specs=sample_llm_output,
            report_config={"style": "casual"},
        )

        assert result.style == ReportStyle.CASUAL

    def test_build_config_all_formats(self, agent, sample_llm_output):
        """Should build configs for all formats."""
        result = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF, OutputFormat.EXCEL, OutputFormat.PPTX, OutputFormat.CSV],
            content_specs=sample_llm_output,
            report_config={},
        )

        assert result.pdf is not None
        assert result.excel is not None
        assert result.pptx is not None
        assert result.csv is not None


class TestFileGeneration:
    """Test file generation with mock generator."""

    @pytest.mark.asyncio
    async def test_generate_files_no_generator(self, agent, sample_aggregated, sample_llm_output):
        """Should return empty list without file generator."""
        config = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF],
            content_specs=sample_llm_output,
            report_config={},
        )

        result = await agent._generate_files(
            session_id="sess_123",
            aggregated=sample_aggregated,
            config=config,
            content_specs=sample_llm_output,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_generate_files_with_generator(
        self, agent_with_generator, mock_file_generator,
        sample_aggregated, sample_llm_output
    ):
        """Should generate files with file generator."""
        config = agent_with_generator._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF, OutputFormat.EXCEL],
            content_specs=sample_llm_output,
            report_config={},
        )

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.stat") as mock_stat:
                mock_stat.return_value = MagicMock(st_size=1024)

                result = await agent_with_generator._generate_files(
                    session_id="sess_123",
                    aggregated=sample_aggregated,
                    config=config,
                    content_specs=sample_llm_output,
                )

        assert len(result) == 2
        mock_file_generator.generate_pdf.assert_called_once()
        mock_file_generator.generate_excel.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_files_handles_error(
        self, agent_with_generator, mock_file_generator,
        sample_aggregated, sample_llm_output
    ):
        """Should handle file generation errors gracefully."""
        mock_file_generator.generate_pdf = AsyncMock(side_effect=Exception("PDF error"))

        config = agent_with_generator._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF],
            content_specs=sample_llm_output,
            report_config={},
        )

        result = await agent_with_generator._generate_files(
            session_id="sess_123",
            aggregated=sample_aggregated,
            config=config,
            content_specs=sample_llm_output,
        )

        # Should return empty list due to error (logged but not raised)
        assert len(result) == 0


class TestResultBuilding:
    """Test final result building."""

    def test_build_result_structure(self, agent, sample_llm_output):
        """Should build result with correct structure."""
        config = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF],
            content_specs=sample_llm_output,
            report_config={},
        )

        result = agent._build_result(
            session_id="sess_123",
            config=config,
            generated_reports=[],
            content_specs=sample_llm_output,
        )

        assert result["session_id"] == "sess_123"
        assert "config" in result
        assert "generated_reports" in result
        assert "content_specs" in result

    def test_build_result_content_specs(self, agent, sample_llm_output):
        """Should include content specs in result."""
        config = agent._build_report_config(
            session_id="sess_123",
            formats=[OutputFormat.PDF, OutputFormat.EXCEL],
            content_specs=sample_llm_output,
            report_config={},
        )

        result = agent._build_result(
            session_id="sess_123",
            config=config,
            generated_reports=[],
            content_specs=sample_llm_output,
        )

        assert "pdf" in result["content_specs"]
        assert "excel" in result["content_specs"]
        assert "title" in result["content_specs"]["pdf"]
        assert "sheets" in result["content_specs"]["excel"]


class TestFullExecution:
    """Test full agent execution flow."""

    @pytest.mark.asyncio
    async def test_execute_success(
        self, agent, mock_llm, mock_session_manager,
        sample_aggregated, sample_llm_output
    ):
        """Should execute complete reporting successfully."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        context = {
            "session_id": "sess_123",
            "aggregated_research": sample_aggregated,
            "output_formats": ["pdf", "excel"],
            "report_config": {},
            "user_preferences": {},
        }

        result = await agent.execute(context)

        assert result["session_id"] == "sess_123"
        assert "config" in result
        assert "content_specs" in result

    @pytest.mark.asyncio
    async def test_execute_saves_result(
        self, agent, mock_llm, mock_session_manager,
        sample_aggregated, sample_llm_output
    ):
        """Should save result to session manager."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        context = {
            "session_id": "sess_123",
            "aggregated_research": sample_aggregated,
            "output_formats": ["pdf"],
            "report_config": {},
            "user_preferences": {},
        }

        await agent.execute(context)

        mock_session_manager.save_state.assert_called_once()
        call_args = mock_session_manager.save_state.call_args
        assert call_args.kwargs["session_id"] == "sess_123"

    @pytest.mark.asyncio
    async def test_run_with_validation(
        self, agent, mock_llm, sample_aggregated, sample_llm_output
    ):
        """Should validate input before execution."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        with pytest.raises(InvalidInputError):
            await agent.run("sess_123", {})  # Missing required fields


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    @pytest.mark.asyncio
    async def test_empty_sections_in_aggregated(self, agent, mock_llm, sample_llm_output):
        """Should handle empty sections gracefully."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        aggregated = {
            "session_id": "sess_123",
            "brief_id": "brief_123",
            "executive_summary": "Test summary",
            "key_insights": [],
            "sections": [],
            "recommendation": {"verdict": "Test"},
        }

        context = {
            "session_id": "sess_123",
            "aggregated_research": aggregated,
            "output_formats": ["pdf"],
        }

        result = await agent.execute(context)
        assert result is not None

    @pytest.mark.asyncio
    async def test_all_formats_requested(
        self, agent, mock_llm, sample_aggregated, sample_llm_output
    ):
        """Should handle all formats being requested."""
        mock_llm.create_structured = AsyncMock(return_value=sample_llm_output)

        context = {
            "session_id": "sess_123",
            "aggregated_research": sample_aggregated,
            "output_formats": ["pdf", "excel", "pptx", "csv"],
        }

        result = await agent.execute(context)

        config = result["config"]
        assert len(config["formats"]) == 4
