"""
Ralph Deep Research - Reporter Agent

Generates professional reports (PDF, Excel, PowerPoint, CSV) from
aggregated research results.

Based on specs/PROMPTS.md Section 7.

Why this agent:
- Transforms aggregated research into formatted documents
- Generates content specifications for each output format
- Supports multiple output formats (PDF, Excel, PPTX, CSV)
- Uses Opus model for content structuring and formatting decisions
- Integrates with FileGenerator for actual file creation

Timeout: 120 seconds (target: 60 seconds)

Usage:
    agent = ReporterAgent(llm_client, session_manager, file_generator)
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "aggregated_research": {...},  # AggregatedResearch
        "output_formats": ["pdf", "excel"],
        "report_config": {...},         # Optional ReportConfig
        "user_preferences": {...}       # Optional preferences
    })
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    CSVConfig,
    Delimiter,
    Encoding,
    ExcelConfig,
    GeneratedReport,
    Language,
    OutputFormat,
    PDFConfig,
    PPTXConfig,
    ReportConfig,
    ReportStyle,
    DetailLevel,
)
from src.storage.session import DataType
from src.tools.errors import InvalidInputError
from src.tools.file_generator import FileGenerator


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE
# =============================================================================


class LLMPDFSection(BaseModel):
    """PDF section specification."""
    title: str = Field(description="Section title")
    content_type: str = Field(description="text|table|chart|mixed")
    word_count: int = Field(default=250, description="Approximate word count")
    visuals: list[str] = Field(default_factory=list, description="Chart/visual names")


class LLMPDFSpec(BaseModel):
    """PDF content specification."""
    title: str = Field(description="Report title")
    subtitle: str = Field(default="", description="Report subtitle")
    date: str = Field(description="Report date")
    total_pages: int = Field(default=10, description="Estimated pages")
    sections: list[LLMPDFSection] = Field(default_factory=list)
    charts_count: int = Field(default=0)
    tables_count: int = Field(default=0)


class LLMExcelSheet(BaseModel):
    """Excel sheet specification."""
    name: str = Field(description="Sheet name")
    data_source: str = Field(description="Where data comes from")
    columns: list[str] = Field(default_factory=list)
    row_count: int = Field(default=10)


class LLMExcelSpec(BaseModel):
    """Excel content specification."""
    sheets: list[LLMExcelSheet] = Field(default_factory=list)
    charts_count: int = Field(default=0)


class LLMPPTXSlide(BaseModel):
    """PowerPoint slide specification."""
    number: int = Field(description="Slide number")
    title: str = Field(description="Slide title")
    layout: str = Field(description="title|content|two_column|chart")
    elements: list[str] = Field(default_factory=list)
    speaker_notes: str = Field(default="")


class LLMPPTXSpec(BaseModel):
    """PowerPoint content specification."""
    total_slides: int = Field(default=10)
    slides: list[LLMPPTXSlide] = Field(default_factory=list)


class LLMReporterOutput(BaseModel):
    """Full output from Reporter Agent LLM."""
    pdf_spec: LLMPDFSpec | None = Field(default=None)
    excel_spec: LLMExcelSpec | None = Field(default=None)
    pptx_spec: LLMPPTXSpec | None = Field(default=None)


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class ReporterAgent(BaseAgent):
    """
    Reporter Agent - Generates professional reports.

    Process:
    1. Analyze aggregated content
    2. Generate PDF content spec (sections, charts, tables)
    3. Generate Excel content spec (sheets, columns)
    4. Generate PPTX content spec (slides, layouts)
    5. Generate CSV if requested
    6. Create actual files using FileGenerator

    Rules:
    - Language matches Brief language
    - Unified visual style
    - Graphics preferred over text where possible
    - Key figures highlighted
    - Sources cited
    """

    def __init__(
        self,
        llm: Any,  # LLMClient
        session_manager: Any,  # SessionManager
        file_generator: FileGenerator | None = None,
    ) -> None:
        """
        Initialize Reporter Agent.

        Args:
            llm: LLM client for API calls
            session_manager: Session manager for state persistence
            file_generator: Optional file generator for report creation
        """
        super().__init__(llm, session_manager)
        self._file_generator = file_generator

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "reporter"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "reporting"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context

        Raises:
            InvalidInputError: If required fields missing
        """
        super().validate_input(context)

        if "aggregated_research" not in context:
            raise InvalidInputError(
                message="aggregated_research is required",
                field="aggregated_research",
            )

        aggregated = context["aggregated_research"]
        if not isinstance(aggregated, dict):
            raise InvalidInputError(
                message="aggregated_research must be a dictionary",
                field="aggregated_research",
            )

        if "output_formats" not in context:
            raise InvalidInputError(
                message="output_formats is required",
                field="output_formats",
            )

        formats = context["output_formats"]
        if not isinstance(formats, list) or len(formats) == 0:
            raise InvalidInputError(
                message="output_formats must be a non-empty list",
                field="output_formats",
            )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute report generation task.

        Args:
            context: Input with aggregated_research, output_formats, config

        Returns:
            ReportConfig with generated reports as dictionary
        """
        session_id = context["session_id"]
        aggregated = context["aggregated_research"]
        output_formats = context["output_formats"]
        report_config = context.get("report_config", {})
        user_preferences = context.get("user_preferences", {})

        # Normalize output formats
        normalized_formats = self._normalize_formats(output_formats)

        self._logger.info(
            "Reporter starting generation",
            session_id=session_id,
            formats=normalized_formats,
        )

        # Step 1: Generate content specifications with LLM
        content_specs = await self._generate_content_specs(
            aggregated=aggregated,
            formats=normalized_formats,
            user_preferences=user_preferences,
        )

        # Step 2: Build report configuration
        result_config = self._build_report_config(
            session_id=session_id,
            formats=normalized_formats,
            content_specs=content_specs,
            report_config=report_config,
        )

        # Step 3: Generate actual files if file generator available
        generated_reports = []
        if self._file_generator:
            generated_reports = await self._generate_files(
                session_id=session_id,
                aggregated=aggregated,
                config=result_config,
                content_specs=content_specs,
            )

        # Step 4: Build final result
        result = self._build_result(
            session_id=session_id,
            config=result_config,
            generated_reports=generated_reports,
            content_specs=content_specs,
        )

        # Step 5: Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.REPORT_CONFIG,
            result=result,
        )

        self._logger.info(
            "Reporter completed",
            formats_generated=len(generated_reports),
        )

        return result

    def _normalize_formats(self, formats: list[Any]) -> list[OutputFormat]:
        """Normalize output format strings to OutputFormat enum."""
        normalized = []
        for fmt in formats:
            if isinstance(fmt, OutputFormat):
                normalized.append(fmt)
            elif isinstance(fmt, str):
                try:
                    normalized.append(OutputFormat(fmt.lower()))
                except ValueError:
                    self._logger.warning(f"Unknown format: {fmt}, skipping")
            else:
                self._logger.warning(f"Invalid format type: {type(fmt)}, skipping")

        if not normalized:
            normalized = [OutputFormat.PDF]  # Default to PDF

        return normalized

    async def _generate_content_specs(
        self,
        aggregated: dict[str, Any],
        formats: list[OutputFormat],
        user_preferences: dict[str, Any],
    ) -> LLMReporterOutput:
        """
        Generate content specifications for each format using LLM.

        Args:
            aggregated: Aggregated research data
            formats: Output formats requested
            user_preferences: User preferences

        Returns:
            Content specifications for each format
        """
        # Extract key information from aggregated research
        exec_summary = aggregated.get("executive_summary", "")
        key_insights = aggregated.get("key_insights", [])
        sections = aggregated.get("sections", [])
        recommendation = aggregated.get("recommendation", {})

        # Build prompt
        sections_text = ""
        for i, section in enumerate(sections, 1):
            title = section.get("title", f"Section {i}")
            summary = section.get("summary", "")
            key_points = section.get("key_points", [])
            sections_text += f"\n{i}. **{title}**\n"
            sections_text += f"   Summary: {summary[:200]}\n"
            if key_points:
                sections_text += f"   Key points: {len(key_points)} items\n"

        formats_needed = ", ".join([f.value for f in formats])

        prompt = f"""## Report Generation Task

Create content specifications for the following report formats: {formats_needed}

## Source Content

**Executive Summary:**
{exec_summary[:500]}

**Key Insights:** {len(key_insights)} insights

**Sections:**
{sections_text}

**Recommendation:**
- Verdict: {recommendation.get('verdict', 'N/A')[:100]}
- Confidence: {recommendation.get('confidence', 'N/A')}

## User Preferences
{user_preferences if user_preferences else "Default preferences"}

## Instructions

Generate specifications for each requested format:

**For PDF:**
- Title and subtitle
- Section breakdown with content types
- Estimated page count
- Chart and table counts

**For Excel:**
- Sheet names and purposes
- Column headers for each sheet
- Data sources

**For PowerPoint:**
- Slide count and titles
- Layout types (title, content, two_column, chart)
- Key elements per slide

Create professional, well-structured specifications.
Optimize for readability and visual impact.

Current timestamp: {datetime.now(timezone.utc).isoformat()}"""

        try:
            result = await self._call_llm_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMReporterOutput,
                max_tokens=4096,
                temperature=0.3,
            )
            return result

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback specs",
                error=str(e),
            )
            return self._create_fallback_specs(formats, aggregated)

    def _create_fallback_specs(
        self,
        formats: list[OutputFormat],
        aggregated: dict[str, Any],
    ) -> LLMReporterOutput:
        """Create fallback specifications if LLM fails."""
        exec_summary = aggregated.get("executive_summary", "Research Report")
        sections = aggregated.get("sections", [])

        result = LLMReporterOutput()

        if OutputFormat.PDF in formats:
            pdf_sections = [
                LLMPDFSection(
                    title="Executive Summary",
                    content_type="text",
                    word_count=300,
                    visuals=[],
                )
            ]
            for section in sections:
                pdf_sections.append(LLMPDFSection(
                    title=section.get("title", "Section"),
                    content_type="mixed",
                    word_count=500,
                    visuals=[],
                ))
            pdf_sections.append(LLMPDFSection(
                title="Recommendations",
                content_type="text",
                word_count=400,
                visuals=[],
            ))

            result.pdf_spec = LLMPDFSpec(
                title=exec_summary[:100] if exec_summary else "Research Report",
                subtitle="Deep Research Analysis",
                date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                total_pages=max(5, len(sections) * 2 + 3),
                sections=pdf_sections,
                charts_count=len(sections),
                tables_count=len(sections),
            )

        if OutputFormat.EXCEL in formats:
            sheets = [
                LLMExcelSheet(
                    name="Summary",
                    data_source="Key insights and metrics",
                    columns=["Metric", "Value", "Source"],
                    row_count=10,
                ),
                LLMExcelSheet(
                    name="Data",
                    data_source="Data results",
                    columns=["Category", "Metric", "Value", "Period"],
                    row_count=50,
                ),
            ]
            result.excel_spec = LLMExcelSpec(
                sheets=sheets,
                charts_count=2,
            )

        if OutputFormat.PPTX in formats:
            slides = [
                LLMPPTXSlide(
                    number=1,
                    title="Research Report",
                    layout="title",
                    elements=["title", "subtitle", "date"],
                ),
                LLMPPTXSlide(
                    number=2,
                    title="Executive Summary",
                    layout="content",
                    elements=["title", "bullet_points"],
                ),
            ]
            for i, section in enumerate(sections[:5], 3):
                slides.append(LLMPPTXSlide(
                    number=i,
                    title=section.get("title", f"Section {i-2}"),
                    layout="content",
                    elements=["title", "bullet_points"],
                ))
            slides.append(LLMPPTXSlide(
                number=len(slides) + 1,
                title="Recommendations",
                layout="content",
                elements=["title", "bullet_points"],
            ))

            result.pptx_spec = LLMPPTXSpec(
                total_slides=len(slides),
                slides=slides,
            )

        return result

    def _build_report_config(
        self,
        session_id: str,
        formats: list[OutputFormat],
        content_specs: LLMReporterOutput,
        report_config: dict[str, Any],
    ) -> ReportConfig:
        """Build ReportConfig from specifications."""
        # Extract settings from report_config or use defaults
        language = Language(report_config.get("language", "ru"))
        style = ReportStyle(report_config.get("style", "formal"))
        detail_level = DetailLevel(report_config.get("detail_level", "detailed"))

        # Build format-specific configs
        pdf_config = None
        if OutputFormat.PDF in formats:
            pdf_opts = report_config.get("pdf", {})
            pdf_config = PDFConfig(
                template=pdf_opts.get("template"),
                include_toc=pdf_opts.get("include_toc", True),
                include_charts=pdf_opts.get("include_charts", True),
                include_sources=pdf_opts.get("include_sources", True),
            )

        excel_config = None
        if OutputFormat.EXCEL in formats:
            excel_opts = report_config.get("excel", {})
            excel_config = ExcelConfig(
                template=excel_opts.get("template"),
                include_summary_sheet=excel_opts.get("include_summary_sheet", True),
                include_raw_data=excel_opts.get("include_raw_data", True),
                include_charts=excel_opts.get("include_charts", True),
            )

        pptx_config = None
        if OutputFormat.PPTX in formats:
            pptx_opts = report_config.get("pptx", {})
            pptx_config = PPTXConfig(
                template=pptx_opts.get("template"),
                slides_per_section=pptx_opts.get("slides_per_section", 2),
                include_speaker_notes=pptx_opts.get("include_speaker_notes", False),
                include_appendix=pptx_opts.get("include_appendix", True),
            )

        csv_config = None
        if OutputFormat.CSV in formats:
            csv_opts = report_config.get("csv", {})
            csv_config = CSVConfig(
                delimiter=Delimiter(csv_opts.get("delimiter", ",")),
                encoding=Encoding(csv_opts.get("encoding", "utf-8")),
                include_headers=csv_opts.get("include_headers", True),
            )

        return ReportConfig(
            session_id=session_id,
            formats=formats,
            language=language,
            style=style,
            detail_level=detail_level,
            pdf=pdf_config,
            excel=excel_config,
            pptx=pptx_config,
            csv=csv_config,
        )

    async def _generate_files(
        self,
        session_id: str,
        aggregated: dict[str, Any],
        config: ReportConfig,
        content_specs: LLMReporterOutput,
    ) -> list[GeneratedReport]:
        """
        Generate actual report files.

        Args:
            session_id: Session ID
            aggregated: Aggregated research
            config: Report configuration
            content_specs: Content specifications

        Returns:
            List of generated report information
        """
        if not self._file_generator:
            return []

        generated = []
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        for fmt in config.formats:
            try:
                if fmt == OutputFormat.PDF and config.pdf:
                    filename = f"report_{session_id}_{timestamp}.pdf"
                    file_path = await self._file_generator.generate_pdf(
                        report_config=config.pdf.model_dump(),
                        aggregated=aggregated,
                        output_path=filename,
                    )
                    size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                    structure = None
                    if content_specs.pdf_spec:
                        structure = {
                            "total_pages": content_specs.pdf_spec.total_pages,
                            "sections": [s.title for s in content_specs.pdf_spec.sections],
                            "charts_count": content_specs.pdf_spec.charts_count,
                            "tables_count": content_specs.pdf_spec.tables_count,
                        }
                    generated.append(GeneratedReport(
                        format=OutputFormat.PDF,
                        filename=filename,
                        file_path=file_path,
                        structure=structure,
                        size_bytes=size,
                    ))

                elif fmt == OutputFormat.EXCEL and config.excel:
                    filename = f"report_{session_id}_{timestamp}.xlsx"
                    file_path = await self._file_generator.generate_excel(
                        report_config=config.excel.model_dump(),
                        aggregated=aggregated,
                        output_path=filename,
                    )
                    size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                    structure = None
                    if content_specs.excel_spec:
                        structure = {
                            "sheets": [s.name for s in content_specs.excel_spec.sheets],
                            "charts_count": content_specs.excel_spec.charts_count,
                        }
                    generated.append(GeneratedReport(
                        format=OutputFormat.EXCEL,
                        filename=filename,
                        file_path=file_path,
                        structure=structure,
                        size_bytes=size,
                    ))

                elif fmt == OutputFormat.PPTX and config.pptx:
                    filename = f"report_{session_id}_{timestamp}.pptx"
                    file_path = await self._file_generator.generate_pptx(
                        report_config=config.pptx.model_dump(),
                        aggregated=aggregated,
                        output_path=filename,
                    )
                    size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                    structure = None
                    if content_specs.pptx_spec:
                        structure = {
                            "total_slides": content_specs.pptx_spec.total_slides,
                            "slides": [
                                {"number": s.number, "title": s.title, "type": s.layout}
                                for s in content_specs.pptx_spec.slides
                            ],
                        }
                    generated.append(GeneratedReport(
                        format=OutputFormat.PPTX,
                        filename=filename,
                        file_path=file_path,
                        structure=structure,
                        size_bytes=size,
                    ))

                elif fmt == OutputFormat.CSV and config.csv:
                    filename = f"report_{session_id}_{timestamp}.csv"
                    file_path = await self._file_generator.generate_csv(
                        report_config=config.csv.model_dump(),
                        aggregated=aggregated,
                        output_path=filename,
                    )
                    size = Path(file_path).stat().st_size if Path(file_path).exists() else 0
                    generated.append(GeneratedReport(
                        format=OutputFormat.CSV,
                        filename=filename,
                        file_path=file_path,
                        structure={"row_count": 0, "column_count": 0},
                        size_bytes=size,
                    ))

            except Exception as e:
                self._logger.error(
                    f"Failed to generate {fmt.value} report",
                    error=str(e),
                )

        return generated

    def _build_result(
        self,
        session_id: str,
        config: ReportConfig,
        generated_reports: list[GeneratedReport],
        content_specs: LLMReporterOutput,
    ) -> dict[str, Any]:
        """Build final result dictionary."""
        # Build content specs dict
        content_specs_dict = {}

        if content_specs.pdf_spec:
            content_specs_dict["pdf"] = {
                "title": content_specs.pdf_spec.title,
                "subtitle": content_specs.pdf_spec.subtitle,
                "date": content_specs.pdf_spec.date,
                "sections": [
                    {
                        "title": s.title,
                        "content_type": s.content_type,
                        "word_count": s.word_count,
                        "visuals": s.visuals,
                    }
                    for s in content_specs.pdf_spec.sections
                ],
            }

        if content_specs.excel_spec:
            content_specs_dict["excel"] = {
                "sheets": [
                    {
                        "name": s.name,
                        "data_source": s.data_source,
                        "columns": s.columns,
                        "row_count": s.row_count,
                    }
                    for s in content_specs.excel_spec.sheets
                ],
            }

        if content_specs.pptx_spec:
            content_specs_dict["pptx"] = {
                "slides": [
                    {
                        "number": s.number,
                        "layout": s.layout,
                        "elements": s.elements,
                    }
                    for s in content_specs.pptx_spec.slides
                ],
            }

        result = {
            "session_id": session_id,
            "config": config.model_dump(mode="json"),
            "generated_reports": [r.model_dump(mode="json") for r in generated_reports],
            "content_specs": content_specs_dict,
        }

        return result
