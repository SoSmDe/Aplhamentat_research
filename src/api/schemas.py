"""
Ralph Deep Research - API Schemas

Pydantic models for all data structures defined in specs/DATA_SCHEMAS.md.
These models are used for API request/response validation, database serialization,
and inter-agent communication.

Organization:
1. Enums - All enum types used across models
2. Session Models - Session state management
3. Initial Context Models - Initial Research phase
4. Brief Models - Research specification
5. Plan & Task Models - Research planning
6. Result Models - Agent execution results
7. Question Models - Follow-up questions
8. Planner Decision Models - Coverage assessment
9. Aggregation Models - Final synthesis
10. Report Models - Report generation config
11. API Request/Response Models - FastAPI endpoints
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


# =============================================================================
# 1. ENUMS
# =============================================================================

class SessionStatus(str, Enum):
    """Session state machine status values."""
    CREATED = "created"
    INITIAL_RESEARCH = "initial_research"
    BRIEF = "brief"
    APPROVED = "approved"
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEW = "review"
    AGGREGATING = "aggregating"
    REPORTING = "reporting"
    DONE = "done"
    FAILED = "failed"


class BriefStatus(str, Enum):
    """Brief approval status."""
    DRAFT = "draft"
    APPROVED = "approved"


class TaskStatus(str, Enum):
    """Execution status for tasks."""
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    PARTIAL = "partial"


class Priority(str, Enum):
    """Priority levels for tasks and questions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ScopeType(str, Enum):
    """Type of research scope item."""
    DATA = "data"           # Quantitative data collection
    RESEARCH = "research"   # Qualitative analysis
    BOTH = "both"           # Mixed approach


class DataSource(str, Enum):
    """Data source types for Data Agent."""
    FINANCIAL_API = "financial_api"
    WEB_SEARCH = "web_search"
    CUSTOM_API = "custom_api"
    DATABASE = "database"


class SourceType(str, Enum):
    """Source types for Research Agent tasks."""
    NEWS = "news"
    REPORTS = "reports"
    COMPANY_WEBSITE = "company_website"
    ANALYST_REPORTS = "analyst_reports"
    SEC_FILINGS = "sec_filings"
    ACADEMIC = "academic"
    SOCIAL_MEDIA = "social_media"


class SourceTypeResult(str, Enum):
    """Source types for Research results (different from task source types)."""
    NEWS = "news"
    REPORT = "report"
    WEBSITE = "website"
    FILING = "filing"
    ACADEMIC = "academic"
    OTHER = "other"


class FindingType(str, Enum):
    """Type of research finding."""
    FACT = "fact"
    OPINION = "opinion"
    ANALYSIS = "analysis"


class Confidence(str, Enum):
    """Confidence levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Sentiment(str, Enum):
    """Sentiment analysis values."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class OutputFormat(str, Enum):
    """Report output formats."""
    PDF = "pdf"
    EXCEL = "excel"
    PPTX = "pptx"
    CSV = "csv"


class UserIntent(str, Enum):
    """Detected user intent from query."""
    INVESTMENT = "investment"
    MARKET_RESEARCH = "market_research"
    COMPETITIVE = "competitive"
    LEARNING = "learning"
    DUE_DILIGENCE = "due_diligence"
    OTHER = "other"


class EntityType(str, Enum):
    """Entity types for Initial Research."""
    COMPANY = "company"
    MARKET = "market"
    CONCEPT = "concept"
    PRODUCT = "product"
    PERSON = "person"
    SECTOR = "sector"


class DataFreshness(str, Enum):
    """Data freshness levels."""
    REAL_TIME = "real-time"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class RiskProfile(str, Enum):
    """User risk profile for investment research."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class PlannerDecisionStatus(str, Enum):
    """Planner decision on whether to continue or finish research."""
    CONTINUE = "continue"
    DONE = "done"


class Language(str, Enum):
    """Supported languages."""
    RU = "ru"
    EN = "en"


class ReportStyle(str, Enum):
    """Report writing style."""
    FORMAL = "formal"
    CASUAL = "casual"


class DetailLevel(str, Enum):
    """Report detail level."""
    DETAILED = "detailed"
    SUMMARY = "summary"


class PageSize(str, Enum):
    """PDF page sizes."""
    A4 = "A4"
    LETTER = "Letter"


class AspectRatio(str, Enum):
    """PowerPoint aspect ratios."""
    WIDE = "16:9"
    STANDARD = "4:3"


class Delimiter(str, Enum):
    """CSV delimiters."""
    COMMA = ","
    SEMICOLON = ";"
    TAB = "\t"


class Encoding(str, Enum):
    """CSV encodings."""
    UTF8 = "utf-8"
    UTF8_BOM = "utf-8-bom"
    CP1251 = "cp1251"


class BriefBuilderAction(str, Enum):
    """Actions returned by Brief Builder agent."""
    ASK_QUESTION = "ask_question"
    PRESENT_BRIEF = "present_brief"
    BRIEF_APPROVED = "brief_approved"


class QuestionType(str, Enum):
    """Type of follow-up question."""
    DATA = "data"
    RESEARCH = "research"


class FilteredQuestionAction(str, Enum):
    """Action to take on a filtered question."""
    ADD = "add"
    SKIP = "skip"


# =============================================================================
# 2. SESSION MODELS
# =============================================================================

class SessionError(BaseModel):
    """Error information for failed sessions."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    recoverable: bool = Field(default=False, description="Whether error is recoverable")


class Session(BaseModel):
    """Research session state container."""
    id: str = Field(..., pattern=r"^sess_[a-zA-Z0-9]{8,}$", description="Session ID")
    user_id: str = Field(..., description="User who owns this session")
    status: SessionStatus = Field(default=SessionStatus.CREATED, description="Current status")
    current_round: int = Field(default=0, ge=0, le=10, description="Current research round")
    error: SessionError | None = Field(default=None, description="Error if failed")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# 3. INITIAL CONTEXT MODELS
# =============================================================================

class QueryAnalysis(BaseModel):
    """Analysis of user's initial query."""
    original_query: str = Field(..., description="User's raw input")
    detected_language: Language = Field(..., description="Detected query language")
    detected_intent: UserIntent = Field(..., description="Detected user intent")
    confidence: float = Field(ge=0, le=1, description="Intent detection confidence")


class EntityIdentifiers(BaseModel):
    """Identifiers for an entity (company, etc.)."""
    ticker: str | None = Field(default=None, description="Stock ticker symbol")
    website: str | None = Field(default=None, description="Company website URL")
    country: str | None = Field(default=None, description="Country of origin")
    exchange: str | None = Field(default=None, description="Stock exchange")


class Entity(BaseModel):
    """Entity extracted from user query."""
    name: str = Field(..., description="Entity name")
    type: EntityType = Field(..., description="Entity type")
    identifiers: EntityIdentifiers = Field(default_factory=EntityIdentifiers)
    brief_description: str = Field(default="", max_length=500, description="Short description")
    category: str = Field(default="", description="Category classification")
    sector: str | None = Field(default=None, description="Industry sector")


class InitialContext(BaseModel):
    """Result of Initial Research phase."""
    session_id: str = Field(..., description="Session this context belongs to")
    query_analysis: QueryAnalysis = Field(..., description="Analysis of user query")
    entities: list[Entity] = Field(default_factory=list, description="Extracted entities")
    context_summary: str = Field(..., max_length=1000, description="3-5 sentence overview")
    suggested_topics: list[str] = Field(default_factory=list, description="Suggested research topics")
    sources_used: list[str] = Field(default_factory=list, description="Sources used in initial research")
    created_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# 4. BRIEF MODELS
# =============================================================================

class ScopeItem(BaseModel):
    """Individual research topic in the Brief."""
    id: int = Field(..., ge=1, description="Scope item ID")
    topic: str = Field(..., min_length=3, max_length=200, description="Topic to research")
    type: ScopeType = Field(..., description="Type of research needed")
    details: str | None = Field(default=None, max_length=500, description="Additional details")
    priority: Priority = Field(default=Priority.MEDIUM, description="Research priority")


class UserContext(BaseModel):
    """User context for research."""
    intent: UserIntent = Field(..., description="User's research intent")
    horizon: str | None = Field(default=None, description="Time horizon")
    risk_profile: RiskProfile | None = Field(default=None, description="Risk tolerance")
    budget: str | None = Field(default=None, description="Investment budget")
    additional: dict[str, Any] | None = Field(default=None, description="Additional context")


class BriefConstraints(BaseModel):
    """Constraints for research."""
    focus_areas: list[str] = Field(default_factory=list, description="Areas to prioritize")
    exclude: list[str] = Field(default_factory=list, description="Topics to exclude")
    time_period: str | None = Field(default=None, description="Time period for data")
    geographic_focus: str | None = Field(default=None, description="Geographic focus")
    max_sources: int | None = Field(default=None, ge=1, description="Maximum sources")


class Brief(BaseModel):
    """Approved research specification (Technical Specification)."""
    brief_id: str = Field(..., pattern=r"^brief_[a-zA-Z0-9]{8,}$", description="Brief ID")
    version: int = Field(default=1, ge=1, description="Version number")
    status: BriefStatus = Field(default=BriefStatus.DRAFT, description="Approval status")
    goal: str = Field(..., min_length=10, max_length=500, description="Research objective")
    user_context: UserContext | None = Field(default=None, description="User context")
    scope: list[ScopeItem] = Field(..., min_length=1, max_length=10, description="Research scope")
    output_formats: list[OutputFormat] = Field(..., min_length=1, description="Desired output formats")
    constraints: BriefConstraints | None = Field(default=None, description="Research constraints")
    created_at: datetime = Field(default_factory=utc_now)
    approved_at: datetime | None = Field(default=None, description="When brief was approved")


# =============================================================================
# 5. PLAN & TASK MODELS
# =============================================================================

class DataTask(BaseModel):
    """Task for Data Agent."""
    id: str = Field(..., pattern=r"^d[0-9]+$", description="Task ID (e.g., d1, d2)")
    scope_item_id: int = Field(..., description="Reference to Brief scope item")
    description: str = Field(..., min_length=10, max_length=500, description="What data to collect")
    source: DataSource = Field(..., description="Data source type")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    expected_output: str | None = Field(default=None, description="Expected data description")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    parameters: dict[str, Any] | None = Field(default=None, description="API-specific parameters")


class ResearchTask(BaseModel):
    """Task for Research Agent."""
    id: str = Field(..., pattern=r"^r[0-9]+$", description="Task ID (e.g., r1, r2)")
    scope_item_id: int = Field(..., description="Reference to Brief scope item")
    description: str = Field(..., min_length=10, max_length=500, description="Research task description")
    focus: str | None = Field(default=None, description="What to focus on")
    source_types: list[SourceType] = Field(default_factory=list, description="Preferred source types")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Task status")
    search_queries: list[str] = Field(default_factory=list, description="Suggested search queries")


class Plan(BaseModel):
    """Research plan for a single round."""
    round: int = Field(..., ge=1, le=10, description="Round number")
    brief_id: str = Field(..., description="Brief this plan is for")
    data_tasks: list[DataTask] = Field(default_factory=list, description="Data collection tasks")
    research_tasks: list[ResearchTask] = Field(default_factory=list, description="Research tasks")
    total_tasks: int = Field(default=0, description="Total task count")
    estimated_duration_seconds: int | None = Field(default=None, description="Estimated duration")
    created_at: datetime = Field(default_factory=utc_now)

    @field_validator("total_tasks", mode="before")
    @classmethod
    def compute_total_tasks(cls, v: int, info) -> int:
        """Compute total tasks from data and research tasks."""
        data = info.data
        if "data_tasks" in data and "research_tasks" in data:
            return len(data.get("data_tasks", [])) + len(data.get("research_tasks", []))
        return v


# =============================================================================
# 6. RESULT MODELS
# =============================================================================

class MetricValue(BaseModel):
    """A single metric value with metadata."""
    value: float | str | int | None = Field(..., description="Metric value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    period: str | None = Field(default=None, description="Time period")
    as_of_date: str | None = Field(default=None, description="Data as-of date")


class DataTable(BaseModel):
    """Tabular data structure."""
    name: str = Field(..., description="Table name")
    headers: list[str] = Field(..., description="Column headers")
    rows: list[list[Any]] = Field(default_factory=list, description="Table rows")


class DataError(BaseModel):
    """Error from data collection."""
    field: str = Field(..., description="Field that caused error")
    error: str = Field(..., description="Error message")
    fallback: str | None = Field(default=None, description="Fallback value used")


class DataMetadata(BaseModel):
    """Metadata for data result."""
    source: str = Field(..., description="Data source name")
    api_used: str | None = Field(default=None, description="API endpoint used")
    timestamp: datetime = Field(default_factory=utc_now, description="Collection timestamp")
    data_freshness: DataFreshness = Field(default=DataFreshness.DAILY, description="Data freshness")


class DataResult(BaseModel):
    """Result from Data Agent."""
    task_id: str = Field(..., description="Task ID")
    round: int = Field(..., ge=1, description="Round number")
    status: TaskStatus = Field(..., description="Execution status")
    metrics: dict[str, MetricValue] = Field(default_factory=dict, description="Collected metrics")
    tables: list[DataTable] = Field(default_factory=list, description="Data tables")
    raw_data: dict[str, Any] | None = Field(default=None, description="Raw API response")
    metadata: DataMetadata | None = Field(default=None, description="Data metadata")
    questions: list["Question"] = Field(default_factory=list, description="Follow-up questions")
    errors: list[DataError] = Field(default_factory=list, description="Errors encountered")
    completed_at: datetime = Field(default_factory=utc_now)


class Finding(BaseModel):
    """A single research finding."""
    finding: str = Field(..., description="The finding text")
    type: FindingType = Field(..., description="Type of finding")
    confidence: Confidence = Field(..., description="Confidence level")
    source: str = Field(..., description="Source of finding")


class Theme(BaseModel):
    """A theme identified in research."""
    theme: str = Field(..., description="Theme name")
    points: list[str] = Field(default_factory=list, description="Supporting points")
    sentiment: Sentiment = Field(..., description="Overall sentiment")


class ContradictionView(BaseModel):
    """One side of a contradiction."""
    position: str = Field(..., description="The position taken")
    source: str = Field(..., description="Source of this view")


class Contradiction(BaseModel):
    """A contradiction found between sources."""
    topic: str = Field(..., description="Topic of contradiction")
    view_1: ContradictionView = Field(..., description="First viewpoint")
    view_2: ContradictionView = Field(..., description="Second viewpoint")


class Source(BaseModel):
    """A source used in research."""
    type: SourceTypeResult = Field(..., description="Source type")
    title: str = Field(..., description="Source title")
    url: str | None = Field(default=None, description="Source URL")
    date: str | None = Field(default=None, description="Publication date")
    credibility: Confidence = Field(default=Confidence.MEDIUM, description="Source credibility")


class ResearchResult(BaseModel):
    """Result from Research Agent."""
    task_id: str = Field(..., description="Task ID")
    round: int = Field(..., ge=1, description="Round number")
    status: TaskStatus = Field(..., description="Execution status")
    summary: str = Field(default="", max_length=500, description="Brief summary")
    key_findings: list[Finding] = Field(default_factory=list, description="Key findings")
    detailed_analysis: str = Field(default="", description="Detailed analysis")
    themes: list[Theme] = Field(default_factory=list, description="Identified themes")
    contradictions: list[Contradiction] = Field(default_factory=list, description="Contradictions found")
    sources: list[Source] = Field(default_factory=list, description="Sources used")
    questions: list["Question"] = Field(default_factory=list, description="Follow-up questions")
    completed_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# 7. QUESTION MODELS
# =============================================================================

class Question(BaseModel):
    """Follow-up question generated by agents."""
    type: QuestionType = Field(..., description="Which agent should handle")
    question: str = Field(..., min_length=5, max_length=300, description="The question")
    context: str | None = Field(default=None, description="Why this question arose")
    priority: Priority = Field(default=Priority.MEDIUM, description="Question priority")
    source_task_id: str | None = Field(default=None, description="Task that generated this")


class FilteredQuestion(BaseModel):
    """Question with filter decision from Planner."""
    question: str = Field(..., description="The question text")
    source_task_id: str = Field(..., description="Source task ID")
    relevance: Confidence = Field(..., description="Relevance to brief")
    action: FilteredQuestionAction = Field(..., description="Whether to add or skip")
    reasoning: str = Field(..., description="Reasoning for decision")


# =============================================================================
# 8. PLANNER DECISION MODELS
# =============================================================================

class CoverageItem(BaseModel):
    """Coverage assessment for a single scope item."""
    topic: str = Field(..., description="Scope item topic")
    coverage_percent: float = Field(..., ge=0, le=100, description="Coverage percentage")
    covered_aspects: list[str] = Field(default_factory=list, description="Aspects covered")
    missing_aspects: list[str] = Field(default_factory=list, description="Aspects still missing")


class PlannerDecision(BaseModel):
    """Planner's decision after reviewing a round."""
    round: int = Field(..., ge=1, description="Round number reviewed")
    status: PlannerDecisionStatus = Field(..., description="Continue or done")
    coverage: dict[str, CoverageItem] = Field(..., description="Coverage per scope item")
    overall_coverage: float = Field(..., ge=0, le=100, description="Overall coverage")
    reason: str = Field(..., description="Explanation for decision")
    new_data_tasks: list[DataTask] = Field(default_factory=list, description="New data tasks")
    new_research_tasks: list[ResearchTask] = Field(default_factory=list, description="New research tasks")
    filtered_questions: list[FilteredQuestion] = Field(default_factory=list, description="Filtered questions")
    created_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# 9. AGGREGATION MODELS
# =============================================================================

class KeyInsight(BaseModel):
    """A key insight from aggregated research."""
    insight: str = Field(..., description="The insight")
    supporting_data: list[str] = Field(default_factory=list, description="Supporting evidence")
    importance: Confidence = Field(default=Confidence.MEDIUM, description="Importance level")


class DataHighlights(BaseModel):
    """Data highlights for a section - stored as dict."""
    # Actually just a dict[str, str] wrapper for clarity
    highlights: dict[str, str] = Field(default_factory=dict)


class Section(BaseModel):
    """A section of the aggregated research."""
    title: str = Field(..., description="Section title")
    brief_scope_id: int = Field(..., description="Corresponding scope item ID")
    summary: str = Field(default="", description="Section summary")
    data_highlights: dict[str, str] = Field(default_factory=dict, description="Key data points")
    analysis: str = Field(default="", description="Analysis text")
    key_points: list[str] = Field(default_factory=list, description="Key points")
    sentiment: Sentiment = Field(default=Sentiment.NEUTRAL, description="Section sentiment")
    charts_suggested: list[str] = Field(default_factory=list, description="Suggested chart types")
    data_tables: list[DataTable] = Field(default_factory=list, description="Data tables")


class ContradictionFound(BaseModel):
    """A contradiction found and resolved in aggregation."""
    topic: str = Field(..., description="Topic of contradiction")
    sources: list[str] = Field(..., description="Conflicting sources")
    resolution: str = Field(..., description="How it was resolved")


class ActionItem(BaseModel):
    """An action item from recommendations."""
    action: str = Field(..., description="Action to take")
    priority: Priority = Field(..., description="Action priority")
    rationale: str = Field(..., description="Why this action")


class Recommendation(BaseModel):
    """Final recommendation from aggregated research."""
    verdict: str = Field(..., description="Overall verdict")
    confidence: Confidence = Field(..., description="Confidence in verdict")
    confidence_reasoning: str = Field(default="", description="Why this confidence")
    reasoning: str = Field(..., description="Detailed reasoning")
    pros: list[str] = Field(default_factory=list, description="Positive factors")
    cons: list[str] = Field(default_factory=list, description="Negative factors")
    action_items: list[ActionItem] = Field(default_factory=list, description="Recommended actions")
    risks_to_monitor: list[str] = Field(default_factory=list, description="Risks to watch")


class CoverageSummary(BaseModel):
    """Coverage summary for a scope item."""
    topic: str = Field(..., description="Topic name")
    coverage_percent: float = Field(..., ge=0, le=100, description="Final coverage")
    gaps: list[str] = Field(default_factory=list, description="Remaining gaps")


class AggregationMetadata(BaseModel):
    """Metadata about the aggregation process."""
    total_rounds: int = Field(..., ge=1, description="Total rounds completed")
    total_data_tasks: int = Field(..., ge=0, description="Total data tasks executed")
    total_research_tasks: int = Field(..., ge=0, description="Total research tasks executed")
    sources_count: int = Field(..., ge=0, description="Total unique sources")
    processing_time_seconds: float = Field(..., ge=0, description="Total processing time")


class AggregatedResearch(BaseModel):
    """Final synthesized research document."""
    session_id: str = Field(..., description="Session ID")
    brief_id: str = Field(..., description="Brief ID")
    created_at: datetime = Field(default_factory=utc_now)
    executive_summary: str = Field(..., min_length=100, max_length=2000, description="Executive summary")
    key_insights: list[KeyInsight] = Field(..., max_length=10, description="Key insights")
    sections: list[Section] = Field(..., description="Research sections")
    contradictions_found: list[ContradictionFound] = Field(default_factory=list)
    recommendation: Recommendation = Field(..., description="Final recommendation")
    coverage_summary: dict[str, CoverageSummary] = Field(default_factory=dict)
    metadata: AggregationMetadata | None = Field(default=None)


# =============================================================================
# 10. REPORT MODELS
# =============================================================================

class PDFBranding(BaseModel):
    """Branding settings for PDF reports."""
    logo_url: str | None = Field(default=None, description="Logo URL")
    primary_color: str = Field(default="#1a365d", pattern=r"^#[0-9A-Fa-f]{6}$")
    company_name: str | None = Field(default=None, description="Company name")


class PDFConfig(BaseModel):
    """PDF report configuration."""
    template: str | None = Field(default=None, description="Template ID")
    include_toc: bool = Field(default=True, description="Include table of contents")
    include_charts: bool = Field(default=True, description="Include charts")
    include_sources: bool = Field(default=True, description="Include sources section")
    page_size: PageSize = Field(default=PageSize.A4, description="Page size")
    branding: PDFBranding | None = Field(default=None, description="Branding settings")


class ExcelConfig(BaseModel):
    """Excel report configuration."""
    template: str | None = Field(default=None, description="Template ID")
    include_summary_sheet: bool = Field(default=True)
    include_raw_data: bool = Field(default=True)
    include_charts: bool = Field(default=True)
    sheets: list[str] = Field(default_factory=list, description="Sheets to include")


class PPTXConfig(BaseModel):
    """PowerPoint report configuration."""
    template: str | None = Field(default=None, description="Template ID")
    slides_per_section: int = Field(default=2, ge=1, le=5)
    include_speaker_notes: bool = Field(default=False)
    include_appendix: bool = Field(default=True)
    aspect_ratio: AspectRatio = Field(default=AspectRatio.WIDE)


class CSVConfig(BaseModel):
    """CSV export configuration."""
    delimiter: Delimiter = Field(default=Delimiter.COMMA)
    encoding: Encoding = Field(default=Encoding.UTF8)
    include_headers: bool = Field(default=True)


class ReportConfig(BaseModel):
    """Configuration for report generation."""
    session_id: str = Field(..., description="Session ID")
    formats: list[OutputFormat] = Field(..., min_length=1, description="Output formats")
    language: Language = Field(default=Language.RU, description="Report language")
    style: ReportStyle = Field(default=ReportStyle.FORMAL, description="Writing style")
    detail_level: DetailLevel = Field(default=DetailLevel.DETAILED, description="Detail level")
    pdf: PDFConfig | None = Field(default=None)
    excel: ExcelConfig | None = Field(default=None)
    pptx: PPTXConfig | None = Field(default=None)
    csv: CSVConfig | None = Field(default=None)


class GeneratedReport(BaseModel):
    """Information about a generated report file."""
    format: OutputFormat = Field(..., description="Report format")
    filename: str = Field(..., description="Generated filename")
    file_path: str = Field(..., description="Path to file")
    structure: dict[str, Any] | None = Field(default=None, description="Report structure")
    size_bytes: int = Field(..., ge=0, description="File size")
    created_at: datetime = Field(default_factory=utc_now)


# =============================================================================
# 11. API REQUEST/RESPONSE MODELS
# =============================================================================

class CreateSessionRequest(BaseModel):
    """Request to create a new research session."""
    user_id: str | None = Field(default=None, description="Optional user ID")
    initial_query: str = Field(..., min_length=5, max_length=5000, description="Research query")


class SendMessageRequest(BaseModel):
    """Request to send a message during brief building."""
    content: str = Field(..., min_length=1, max_length=5000, description="Message content")


class ApproveBriefRequest(BaseModel):
    """Request to approve a Brief."""
    modifications: dict[str, Any] | None = Field(default=None, description="Optional modifications")


class SessionResponse(BaseModel):
    """Response for session-related endpoints."""
    session_id: str = Field(..., description="Session ID")
    status: SessionStatus = Field(..., description="Session status")
    action: BriefBuilderAction | None = Field(default=None, description="Suggested action")
    message: str | None = Field(default=None, description="Response message")
    brief: Brief | None = Field(default=None, description="Current brief if available")


class ProgressInfo(BaseModel):
    """Progress information for ongoing research."""
    data_tasks_completed: int = Field(..., ge=0)
    data_tasks_total: int = Field(..., ge=0)
    research_tasks_completed: int = Field(..., ge=0)
    research_tasks_total: int = Field(..., ge=0)
    current_round: int = Field(..., ge=0)
    max_rounds: int = Field(default=10)


class StatusResponse(BaseModel):
    """Response for session status endpoint."""
    session_id: str = Field(..., description="Session ID")
    status: SessionStatus = Field(..., description="Session status")
    current_round: int = Field(..., ge=0, description="Current round")
    progress: ProgressInfo | None = Field(default=None, description="Progress if executing")
    coverage: dict[str, float] | None = Field(default=None, description="Coverage per scope item")
    error: SessionError | None = Field(default=None, description="Error if failed")


class ReportInfo(BaseModel):
    """Information about an available report."""
    format: OutputFormat = Field(..., description="Report format")
    url: str = Field(..., description="Download URL")
    filename: str = Field(..., description="Filename")
    size_bytes: int = Field(..., ge=0, description="File size")


class ResultsResponse(BaseModel):
    """Response for results endpoint."""
    session_id: str = Field(..., description="Session ID")
    status: SessionStatus = Field(..., description="Session status")
    aggregated: AggregatedResearch | None = Field(default=None, description="Aggregated research")
    reports: list[ReportInfo] = Field(default_factory=list, description="Available reports")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional details")
    session_id: str | None = Field(default=None, description="Session ID if applicable")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", description="Health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=utc_now)


# Update forward references for circular dependencies
DataResult.model_rebuild()
ResearchResult.model_rebuild()
