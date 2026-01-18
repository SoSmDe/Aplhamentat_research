"""
Tests for Pydantic schemas (Phase 1.2 and 1.3).

Verifies:
- All enum values match specification
- Model validation works correctly
- Required fields are enforced
- Default values are set
- ID patterns are validated
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from src.api.schemas import (
    # Enums
    SessionStatus,
    BriefStatus,
    TaskStatus,
    Priority,
    ScopeType,
    DataSource,
    SourceType,
    FindingType,
    Confidence,
    Sentiment,
    OutputFormat,
    UserIntent,
    EntityType,
    DataFreshness,
    RiskProfile,
    PlannerDecisionStatus,
    Language,
    BriefBuilderAction,
    # Session Models
    Session,
    SessionError,
    # Initial Context Models
    QueryAnalysis,
    EntityIdentifiers,
    Entity,
    InitialContext,
    # Brief Models
    ScopeItem,
    UserContext,
    BriefConstraints,
    Brief,
    # Task Models
    DataTask,
    ResearchTask,
    Plan,
    # Result Models
    MetricValue,
    DataTable,
    DataResult,
    Finding,
    Theme,
    Source,
    ResearchResult,
    # Question Models
    Question,
    FilteredQuestion,
    # Planner Decision
    CoverageItem,
    PlannerDecision,
    # Aggregation Models
    KeyInsight,
    Section,
    Recommendation,
    AggregatedResearch,
    AggregationMetadata,
    # Report Models
    PDFConfig,
    ExcelConfig,
    PPTXConfig,
    CSVConfig,
    ReportConfig,
    GeneratedReport,
    # API Models
    CreateSessionRequest,
    SendMessageRequest,
    ApproveBriefRequest,
    SessionResponse,
    StatusResponse,
    ResultsResponse,
    ErrorResponse,
    HealthResponse,
)


class TestEnums:
    """Tests for all enum types."""

    def test_session_status_values(self) -> None:
        """SessionStatus should have all required values."""
        expected = {
            "created", "initial_research", "brief", "approved",
            "planning", "executing", "review", "aggregating",
            "reporting", "done", "failed"
        }
        assert {s.value for s in SessionStatus} == expected

    def test_brief_status_values(self) -> None:
        """BriefStatus should have draft and approved."""
        assert {s.value for s in BriefStatus} == {"draft", "approved"}

    def test_task_status_values(self) -> None:
        """TaskStatus should have all required values."""
        assert {s.value for s in TaskStatus} == {"pending", "running", "done", "failed", "partial"}

    def test_priority_values(self) -> None:
        """Priority should have high, medium, low."""
        assert {p.value for p in Priority} == {"high", "medium", "low"}

    def test_scope_type_values(self) -> None:
        """ScopeType should have data, research, both."""
        assert {s.value for s in ScopeType} == {"data", "research", "both"}

    def test_data_source_values(self) -> None:
        """DataSource should include database."""
        values = {s.value for s in DataSource}
        assert "database" in values
        assert "financial_api" in values

    def test_entity_type_includes_sector(self) -> None:
        """EntityType should include sector."""
        values = {e.value for e in EntityType}
        assert "sector" in values
        assert "company" in values

    def test_output_format_includes_csv(self) -> None:
        """OutputFormat should include CSV."""
        values = {f.value for f in OutputFormat}
        assert "csv" in values
        assert "pdf" in values

    def test_data_freshness_values(self) -> None:
        """DataFreshness should have all required values."""
        expected = {"real-time", "daily", "weekly", "monthly", "quarterly", "annual"}
        assert {f.value for f in DataFreshness} == expected

    def test_planner_decision_status_values(self) -> None:
        """PlannerDecisionStatus should have continue and done."""
        assert {s.value for s in PlannerDecisionStatus} == {"continue", "done"}


class TestSessionModels:
    """Tests for Session-related models."""

    def test_session_id_pattern(self) -> None:
        """Session ID must match pattern sess_[a-zA-Z0-9]{8,}."""
        # Valid
        session = Session(id="sess_abc12345678", user_id="user1")
        assert session.id == "sess_abc12345678"

        # Invalid
        with pytest.raises(ValidationError):
            Session(id="invalid_id", user_id="user1")

    def test_session_default_status(self) -> None:
        """Session should default to CREATED status."""
        session = Session(id="sess_12345678", user_id="user1")
        assert session.status == SessionStatus.CREATED

    def test_session_default_round(self) -> None:
        """Session should default to round 0."""
        session = Session(id="sess_12345678", user_id="user1")
        assert session.current_round == 0

    def test_session_error_model(self) -> None:
        """SessionError should have required fields."""
        error = SessionError(code="E001", message="Something went wrong")
        assert error.code == "E001"
        assert error.recoverable is False


class TestInitialContextModels:
    """Tests for Initial Context models."""

    def test_query_analysis_required_fields(self) -> None:
        """QueryAnalysis should require all fields."""
        qa = QueryAnalysis(
            original_query="Research Realty Income",
            detected_language=Language.EN,
            detected_intent=UserIntent.INVESTMENT,
            confidence=0.95
        )
        assert qa.confidence == 0.95

    def test_entity_identifiers_optional_fields(self) -> None:
        """EntityIdentifiers should have all optional fields."""
        ids = EntityIdentifiers()
        assert ids.ticker is None
        assert ids.exchange is None

        ids_with_data = EntityIdentifiers(ticker="O", exchange="NYSE")
        assert ids_with_data.ticker == "O"
        assert ids_with_data.exchange == "NYSE"

    def test_entity_model(self) -> None:
        """Entity should validate correctly."""
        entity = Entity(
            name="Realty Income",
            type=EntityType.COMPANY,
            identifiers=EntityIdentifiers(ticker="O"),
            brief_description="Real estate investment trust"
        )
        assert entity.name == "Realty Income"


class TestBriefModels:
    """Tests for Brief models."""

    def test_brief_id_pattern(self) -> None:
        """Brief ID must match pattern brief_[a-zA-Z0-9]{8,}."""
        brief = Brief(
            brief_id="brief_abc12345678",
            goal="Research company financials",
            scope=[ScopeItem(id=1, topic="Financial metrics", type=ScopeType.DATA)],
            output_formats=[OutputFormat.PDF]
        )
        assert brief.brief_id == "brief_abc12345678"

    def test_brief_scope_min_items(self) -> None:
        """Brief must have at least one scope item."""
        with pytest.raises(ValidationError):
            Brief(
                brief_id="brief_12345678",
                goal="Research company",
                scope=[],  # Empty not allowed
                output_formats=[OutputFormat.PDF]
            )

    def test_scope_item_validation(self) -> None:
        """ScopeItem should validate topic length."""
        with pytest.raises(ValidationError):
            ScopeItem(id=1, topic="AB", type=ScopeType.DATA)  # Too short

    def test_brief_constraints_model(self) -> None:
        """BriefConstraints should accept geographic_focus."""
        constraints = BriefConstraints(
            focus_areas=["financials", "growth"],
            geographic_focus="North America",
            time_period="last 5 years"
        )
        assert constraints.geographic_focus == "North America"


class TestTaskModels:
    """Tests for Task models."""

    def test_data_task_id_pattern(self) -> None:
        """DataTask ID must match pattern d[0-9]+."""
        task = DataTask(
            id="d1",
            scope_item_id=1,
            description="Collect revenue data for Q4",
            source=DataSource.FINANCIAL_API
        )
        assert task.id == "d1"

        with pytest.raises(ValidationError):
            DataTask(
                id="data1",  # Invalid pattern
                scope_item_id=1,
                description="Collect data",
                source=DataSource.FINANCIAL_API
            )

    def test_research_task_id_pattern(self) -> None:
        """ResearchTask ID must match pattern r[0-9]+."""
        task = ResearchTask(
            id="r1",
            scope_item_id=1,
            description="Research market trends in real estate"
        )
        assert task.id == "r1"

    def test_research_task_search_queries(self) -> None:
        """ResearchTask should support search_queries field."""
        task = ResearchTask(
            id="r1",
            scope_item_id=1,
            description="Research trends",
            search_queries=["REIT market trends 2024", "real estate investing"]
        )
        assert len(task.search_queries) == 2

    def test_plan_round_limits(self) -> None:
        """Plan round must be 1-10."""
        plan = Plan(round=1, brief_id="brief_12345678")
        assert plan.round == 1

        with pytest.raises(ValidationError):
            Plan(round=0, brief_id="brief_12345678")

        with pytest.raises(ValidationError):
            Plan(round=11, brief_id="brief_12345678")


class TestResultModels:
    """Tests for Result models."""

    def test_metric_value_model(self) -> None:
        """MetricValue should accept various value types."""
        metric = MetricValue(value=1234567.89, unit="USD", period="FY2023")
        assert metric.value == 1234567.89

        metric_str = MetricValue(value="N/A", as_of_date="2024-01-01")
        assert metric_str.value == "N/A"

    def test_data_table_model(self) -> None:
        """DataTable should store tabular data."""
        table = DataTable(
            name="Revenue by Year",
            headers=["Year", "Revenue", "Growth"],
            rows=[
                [2022, 3500, 0.15],
                [2023, 4000, 0.14]
            ]
        )
        assert len(table.rows) == 2

    def test_data_result_with_questions(self) -> None:
        """DataResult should support follow-up questions."""
        result = DataResult(
            task_id="d1",
            round=1,
            status=TaskStatus.DONE,
            questions=[
                Question(type="research", question="Why did revenue growth slow in Q4?")
            ]
        )
        assert len(result.questions) == 1

    def test_finding_model(self) -> None:
        """Finding should validate all fields."""
        finding = Finding(
            finding="Revenue grew 15% YoY",
            type=FindingType.FACT,
            confidence=Confidence.HIGH,
            source="Annual Report 2023"
        )
        assert finding.type == FindingType.FACT


class TestPlannerDecisionModels:
    """Tests for Planner Decision models."""

    def test_coverage_item_model(self) -> None:
        """CoverageItem should validate coverage percentage."""
        coverage = CoverageItem(
            topic="Financial Analysis",
            coverage_percent=75.5,
            covered_aspects=["Revenue", "Expenses"],
            missing_aspects=["Cash Flow"]
        )
        assert coverage.coverage_percent == 75.5

    def test_planner_decision_model(self) -> None:
        """PlannerDecision should include all required fields."""
        decision = PlannerDecision(
            round=1,
            status=PlannerDecisionStatus.CONTINUE,
            coverage={
                "1": CoverageItem(
                    topic="Financials",
                    coverage_percent=70,
                    covered_aspects=["Revenue"],
                    missing_aspects=["Margins"]
                )
            },
            overall_coverage=70,
            reason="Coverage below 80% threshold"
        )
        assert decision.status == PlannerDecisionStatus.CONTINUE


class TestAggregationModels:
    """Tests for Aggregation models."""

    def test_key_insight_model(self) -> None:
        """KeyInsight should validate correctly."""
        insight = KeyInsight(
            insight="Strong revenue growth indicates healthy business",
            supporting_data=["Revenue up 15%", "Customer base grew 20%"],
            importance=Confidence.HIGH
        )
        assert len(insight.supporting_data) == 2

    def test_section_model(self) -> None:
        """Section should include all fields."""
        section = Section(
            title="Financial Performance",
            brief_scope_id=1,
            summary="Strong financial performance across key metrics",
            data_highlights={"Revenue": "$4B", "Growth": "15%"},
            sentiment=Sentiment.POSITIVE
        )
        assert section.sentiment == Sentiment.POSITIVE

    def test_recommendation_model(self) -> None:
        """Recommendation should have verdict and confidence."""
        rec = Recommendation(
            verdict="Buy",
            confidence=Confidence.HIGH,
            reasoning="Strong fundamentals and growth trajectory"
        )
        assert rec.verdict == "Buy"

    def test_aggregation_metadata_model(self) -> None:
        """AggregationMetadata should track processing stats."""
        metadata = AggregationMetadata(
            total_rounds=3,
            total_data_tasks=8,
            total_research_tasks=12,
            sources_count=25,
            processing_time_seconds=145.5
        )
        assert metadata.total_rounds == 3


class TestReportModels:
    """Tests for Report configuration models."""

    def test_pdf_config_defaults(self) -> None:
        """PDFConfig should have sensible defaults."""
        config = PDFConfig()
        assert config.include_toc is True
        assert config.include_charts is True

    def test_csv_config_model(self) -> None:
        """CSVConfig should support all options."""
        config = CSVConfig(
            delimiter=";",
            encoding="utf-8-bom",
            include_headers=True
        )
        assert config.delimiter == ";"

    def test_report_config_requires_format(self) -> None:
        """ReportConfig must have at least one format."""
        with pytest.raises(ValidationError):
            ReportConfig(session_id="sess_12345678", formats=[])

    def test_generated_report_model(self) -> None:
        """GeneratedReport should track file info."""
        report = GeneratedReport(
            format=OutputFormat.PDF,
            filename="research_report.pdf",
            file_path="/reports/sess_123/research_report.pdf",
            size_bytes=1024000
        )
        assert report.size_bytes == 1024000


class TestAPIModels:
    """Tests for API request/response models."""

    def test_create_session_request(self) -> None:
        """CreateSessionRequest should validate query length."""
        request = CreateSessionRequest(initial_query="Research Realty Income for investment")
        assert request.initial_query is not None

        with pytest.raises(ValidationError):
            CreateSessionRequest(initial_query="Hi")  # Too short

    def test_session_response_model(self) -> None:
        """SessionResponse should include all fields."""
        response = SessionResponse(
            session_id="sess_12345678",
            status=SessionStatus.BRIEF,
            action=BriefBuilderAction.ASK_QUESTION,
            message="What is your investment horizon?"
        )
        assert response.action == BriefBuilderAction.ASK_QUESTION

    def test_error_response_model(self) -> None:
        """ErrorResponse should include error details."""
        error = ErrorResponse(
            error="session_not_found",
            message="Session sess_invalid does not exist",
            session_id="sess_invalid"
        )
        assert error.error == "session_not_found"

    def test_health_response_model(self) -> None:
        """HealthResponse should include status and version."""
        response = HealthResponse(status="ok", version="0.1.0")
        assert response.status == "ok"
        assert isinstance(response.timestamp, datetime)
