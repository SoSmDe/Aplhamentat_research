"""
Ralph Deep Research - Data Agent

Specialist agent for collecting structured quantitative data from APIs
and databases.

Based on specs/PROMPTS.md Section 4.

Why this agent:
- Collects numerical metrics and facts from APIs
- Structures data with proper metadata (source, timestamp, freshness)
- Uses Sonnet model for cost efficiency (simple extraction)
- Generates follow-up questions when anomalies are found

Timeout: 45 seconds (target: 30 seconds)

Usage:
    agent = DataAgent(llm_client, session_manager, api_client)
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "task": {...},           # DataTask
        "entity_context": {...}, # Entity information
        "available_apis": ["financial_api", "web_search"]
    })
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    DataError,
    DataFreshness,
    DataMetadata,
    DataResult,
    DataSource,
    DataTable,
    DataTask,
    MetricValue,
    Priority,
    Question,
    QuestionType,
    TaskStatus,
)
from src.storage.session import DataType
from src.tools.api_client import APIClient, FinancialAPIClient, get_financial_client
from src.tools.errors import InvalidInputError


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE
# =============================================================================


class LLMMetricValue(BaseModel):
    """Metric value from LLM response."""
    value: float | str | int | None = Field(description="Metric value")
    unit: str | None = Field(default=None, description="Unit of measurement")
    period: str | None = Field(default=None, description="Time period")
    as_of_date: str | None = Field(default=None, description="Data as-of date")


class LLMDataTable(BaseModel):
    """Data table from LLM response."""
    name: str = Field(description="Table name")
    headers: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)


class LLMDataError(BaseModel):
    """Error from data collection."""
    field: str = Field(description="Field that caused error")
    error: str = Field(description="Error message")
    fallback: str | None = Field(default=None)


class LLMQuestion(BaseModel):
    """Follow-up question from Data Agent."""
    type: str = Field(default="research", description="data|research")
    question: str = Field(description="The question")
    context: str | None = Field(default=None, description="Why this question arose")
    priority: str = Field(default="medium", description="high|medium|low")


class LLMDataOutput(BaseModel):
    """Full output from Data Agent LLM."""
    task_id: str = Field(description="Task ID")
    round: int = Field(description="Round number")
    status: str = Field(description="done|failed|partial")
    metrics: dict[str, LLMMetricValue] = Field(default_factory=dict)
    tables: list[LLMDataTable] = Field(default_factory=list)
    raw_data: dict[str, Any] | None = Field(default=None)
    metadata: dict[str, Any] | None = Field(default=None)
    questions: list[LLMQuestion] = Field(default_factory=list)
    errors: list[LLMDataError] = Field(default_factory=list)


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class DataAgent(BaseAgent):
    """
    Data Agent - Structured data collection specialist.

    Collects quantitative data from APIs and databases.
    Uses Sonnet model for cost efficiency.

    Process:
    1. Parse task for specific metrics
    2. Select appropriate API source
    3. Execute API call
    4. Extract and validate data
    5. Structure with metadata
    6. Generate follow-up questions if anomalies found

    Rules:
    - Facts only, no interpretations
    - All numbers with source and date
    - Explicit null with reason if data unavailable
    - Maximum 30 seconds per task
    - Try alternative source on API error
    """

    def __init__(
        self,
        llm: Any,  # LLMClient
        session_manager: Any,  # SessionManager
        api_client: APIClient | None = None,
    ) -> None:
        """
        Initialize Data Agent.

        Args:
            llm: LLM client for API calls
            session_manager: Session manager for state persistence
            api_client: Optional API client for data sources
        """
        super().__init__(llm, session_manager)
        self._api_client = api_client or get_financial_client()

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "data"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "data_task"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context

        Raises:
            InvalidInputError: If required fields missing
        """
        super().validate_input(context)

        if "task" not in context:
            raise InvalidInputError(
                message="task is required",
                field="task",
            )

        task = context["task"]
        if not isinstance(task, dict):
            raise InvalidInputError(
                message="task must be a dictionary",
                field="task",
            )

        if "id" not in task or "description" not in task:
            raise InvalidInputError(
                message="task must have id and description",
                field="task",
            )

        if "round" not in context:
            raise InvalidInputError(
                message="round is required",
                field="round",
            )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute data collection task.

        Args:
            context: Input with task, entity_context, available_apis

        Returns:
            DataResult as dictionary
        """
        session_id = context["session_id"]
        task = context["task"]
        round_num = context["round"]
        entity_context = context.get("entity_context", {})
        available_apis = context.get("available_apis", ["web_search"])

        task_id = task.get("id", "d0")
        description = task.get("description", "")
        source = task.get("source", "web_search")

        self._logger.info(
            "Data agent executing task",
            task_id=task_id,
            source=source,
        )

        # Step 1: Try to get data from API
        api_data = await self._fetch_api_data(
            source=source,
            description=description,
            entity_context=entity_context,
            available_apis=available_apis,
        )

        # Step 2: Process data with LLM
        llm_output = await self._process_with_llm(
            task_id=task_id,
            round_num=round_num,
            task=task,
            entity_context=entity_context,
            api_data=api_data,
        )

        # Step 3: Convert to DataResult
        result = self._convert_to_result(llm_output, task_id, round_num)

        # Step 4: Save result (Ralph Pattern)
        await self._save_result(
            session_id=session_id,
            data_type=DataType.DATA_RESULT,
            result=result,
            round=round_num,
            task_id=task_id,
        )

        self._logger.info(
            "Data task completed",
            task_id=task_id,
            status=result["status"],
            metrics_count=len(result.get("metrics", {})),
        )

        return result

    async def _fetch_api_data(
        self,
        source: str,
        description: str,
        entity_context: dict[str, Any],
        available_apis: list[str],
    ) -> dict[str, Any]:
        """
        Fetch data from API based on source type.

        Args:
            source: Data source type
            description: Task description for context
            entity_context: Entity information
            available_apis: List of available API types

        Returns:
            Raw API response or empty dict if failed
        """
        api_data: dict[str, Any] = {"source": source, "raw": {}}

        try:
            if source == "financial_api" and "financial_api" in available_apis:
                # Try to extract ticker from entity context
                ticker = self._extract_ticker(entity_context)
                if ticker:
                    data = await self._api_client.get_stock_data(ticker)
                    api_data["raw"] = data
                    api_data["ticker"] = ticker

            elif source == "database":
                # For database queries, we'd need specific query parameters
                # This is a placeholder for future implementation
                api_data["raw"] = {}
                api_data["note"] = "Database queries require specific configuration"

            elif source == "custom_api":
                # Custom API would need endpoint configuration
                api_data["raw"] = {}
                api_data["note"] = "Custom API requires endpoint configuration"

            else:
                # Default to web_search or fallback
                api_data["raw"] = {}
                api_data["fallback"] = "web_search"

        except Exception as e:
            self._logger.warning(
                "API call failed",
                source=source,
                error=str(e),
            )
            api_data["error"] = str(e)
            api_data["raw"] = {}

        return api_data

    def _extract_ticker(self, entity_context: dict[str, Any]) -> str | None:
        """Extract stock ticker from entity context."""
        # Check identifiers first
        identifiers = entity_context.get("identifiers", {})
        if isinstance(identifiers, dict) and identifiers.get("ticker"):
            return identifiers["ticker"]

        # Check for ticker in entity name (common pattern)
        name = entity_context.get("name", "")
        if name and len(name) <= 5 and name.isupper():
            return name

        return None

    async def _process_with_llm(
        self,
        task_id: str,
        round_num: int,
        task: dict[str, Any],
        entity_context: dict[str, Any],
        api_data: dict[str, Any],
    ) -> LLMDataOutput:
        """
        Process data collection with LLM.

        Args:
            task_id: Task ID
            round_num: Round number
            task: Task definition
            entity_context: Entity information
            api_data: Data from API call

        Returns:
            Structured LLM output
        """
        # Build prompt
        description = task.get("description", "")
        expected_output = task.get("expected_output", "")
        source = task.get("source", "web_search")

        entity_name = entity_context.get("name", "Unknown")
        entity_type = entity_context.get("type", "unknown")

        api_result_text = ""
        if api_data.get("raw"):
            # Format API data for LLM
            raw = api_data["raw"]
            if isinstance(raw, dict):
                api_result_text = "\n".join(f"  {k}: {v}" for k, v in list(raw.items())[:20])
            else:
                api_result_text = str(raw)[:1000]
        elif api_data.get("error"):
            api_result_text = f"API Error: {api_data['error']}"
        else:
            api_result_text = "No API data available"

        prompt = f"""## Data Collection Task

**Task ID**: {task_id}
**Round**: {round_num}
**Description**: {description}
**Expected Output**: {expected_output or 'Relevant metrics and data'}

**Entity**: {entity_name} (Type: {entity_type})
**Source**: {source}

**API Data Retrieved**:
{api_result_text}

## Instructions

1. Extract relevant metrics from the task description
2. If API data is available, extract and structure the values
3. If data is missing, indicate with null and explain why
4. Generate questions if you notice anomalies or interesting patterns
5. Include proper metadata (source, timestamp, freshness)

Return structured JSON with:
- metrics: key metric values with units and dates
- tables: any tabular data found
- errors: any issues encountered
- questions: follow-up questions if anomalies found

Current timestamp: {datetime.now(timezone.utc).isoformat()}"""

        try:
            result = await self._call_llm_structured(
                messages=[{"role": "user", "content": prompt}],
                response_model=LLMDataOutput,
                max_tokens=2048,
                temperature=0.2,
            )
            result.task_id = task_id
            result.round = round_num
            return result

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback",
                error=str(e),
            )
            return self._create_fallback_output(
                task_id=task_id,
                round_num=round_num,
                task=task,
                api_data=api_data,
            )

    def _create_fallback_output(
        self,
        task_id: str,
        round_num: int,
        task: dict[str, Any],
        api_data: dict[str, Any],
    ) -> LLMDataOutput:
        """Create fallback output if LLM fails."""
        metrics = {}
        errors = []
        status = "partial"

        # Try to extract basic data from API response
        raw = api_data.get("raw", {})
        if raw and isinstance(raw, dict):
            for key, value in list(raw.items())[:10]:
                if isinstance(value, (int, float, str)):
                    metrics[key] = LLMMetricValue(
                        value=value,
                        unit=None,
                        period=None,
                        as_of_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    )
            if metrics:
                status = "done"
        else:
            status = "failed" if api_data.get("error") else "partial"
            errors.append(LLMDataError(
                field="api_data",
                error=api_data.get("error", "No data available"),
                fallback=None,
            ))

        return LLMDataOutput(
            task_id=task_id,
            round=round_num,
            status=status,
            metrics=metrics,
            tables=[],
            raw_data=raw if raw else None,
            metadata={
                "source": api_data.get("source", "unknown"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            questions=[],
            errors=errors,
        )

    def _convert_to_result(
        self,
        llm_output: LLMDataOutput,
        task_id: str,
        round_num: int,
    ) -> dict[str, Any]:
        """Convert LLM output to DataResult dictionary."""
        # Convert status
        try:
            status = TaskStatus(llm_output.status)
        except ValueError:
            status = TaskStatus.PARTIAL

        # Convert metrics
        metrics = {}
        for name, metric in llm_output.metrics.items():
            metrics[name] = MetricValue(
                value=metric.value,
                unit=metric.unit,
                period=metric.period,
                as_of_date=metric.as_of_date,
            )

        # Convert tables
        tables = []
        for table in llm_output.tables:
            tables.append(DataTable(
                name=table.name,
                headers=table.headers,
                rows=table.rows,
            ))

        # Convert metadata
        metadata = None
        if llm_output.metadata:
            try:
                freshness = DataFreshness(llm_output.metadata.get("data_freshness", "daily"))
            except ValueError:
                freshness = DataFreshness.DAILY

            metadata = DataMetadata(
                source=llm_output.metadata.get("source", "unknown"),
                api_used=llm_output.metadata.get("api_used"),
                data_freshness=freshness,
            )

        # Convert questions
        questions = []
        for q in llm_output.questions:
            try:
                q_type = QuestionType(q.type)
            except ValueError:
                q_type = QuestionType.RESEARCH

            try:
                priority = Priority(q.priority)
            except ValueError:
                priority = Priority.MEDIUM

            questions.append(Question(
                type=q_type,
                question=q.question[:300],
                context=q.context[:500] if q.context else None,
                priority=priority,
                source_task_id=task_id,
            ))

        # Convert errors
        errors = []
        for err in llm_output.errors:
            errors.append(DataError(
                field=err.field,
                error=err.error[:500],
                fallback=err.fallback,
            ))

        result = DataResult(
            task_id=task_id,
            round=round_num,
            status=status,
            metrics=metrics,
            tables=tables,
            raw_data=llm_output.raw_data,
            metadata=metadata,
            questions=questions,
            errors=errors,
        )

        return result.model_dump(mode="json")
