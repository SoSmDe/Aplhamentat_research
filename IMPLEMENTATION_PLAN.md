# Ralph Deep Research - Implementation Plan

## Project Goal
Build a multi-agent AI research automation system that accepts user queries, conducts comprehensive research through specialized agents (Initial Research, Brief Builder, Planner, Data, Research, Aggregator, Reporter), and generates professional reports (PDF, Excel, PowerPoint).

## Key Technical Decisions
1. **Ralph Pattern**: Each agent executes task → saves result → clears context → next task
2. **Model Selection**: Opus for reasoning (Brief Builder, Planner, Research, Aggregator, Reporter), Sonnet for data extraction (Data agent)
3. **Parallel Execution**: Data and Research agents run concurrently via asyncio.gather()
4. **State Persistence**: All state saved to SQLite after each operation for crash recovery
5. **Coverage-Based Looping**: Planner continues rounds until all scope items reach 80%+ coverage (max 10 rounds)
6. **Error Hierarchy**: TransientError (retryable), PermanentError, SystemError
7. **Retry Logic**: Exponential backoff with jitter (±25%), circuit breaker pattern

---

## Current Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| **Specifications** | ✅ Complete | 5 files in specs/ |
| **Source Code** | 🔄 Phase 9 Complete | Config + Schemas + Errors/Logging/Retry + Storage + Tools + All Agents + Orchestrator (ParallelExecutor, ResearchPipeline) |
| **Tests** | 🔄 In Progress | 648 tests passing |
| **Frontend** | ❌ Not Started | Placeholder only |
| **Last Updated** | 2026-01-19 | |

### Spec Documents (Complete)
- `specs/README.md` - Project overview, architecture diagram
- `specs/ralph_prd.md` - Full PRD with requirements
- `specs/ARCHITECTURE.md` - Technical architecture, state machine, error handling
- `specs/DATA_SCHEMAS.md` - 24+ data types with JSON Schema + TypeScript
- `specs/PROMPTS.md` - 7 agent system prompts with I/O formats

### Critical Spec Details for Implementation

**Performance Targets (from ARCHITECTURE.md)**:
| Operation | Target | Timeout |
|-----------|--------|---------|
| Initial Research | <60s | 90s |
| Brief Builder response | <5s | 10s |
| Planner decision | <10s | 20s |
| Single Data task | <30s | 45s |
| Single Research task | <60s | 90s |
| Parallel round | <120s | 300s |
| Aggregation | <60s | 120s |
| Report generation | <60s | 120s |

**Scalability Limits (MVP)**:
| Resource | Limit |
|----------|-------|
| Concurrent sessions | 10 |
| Tasks per round | 10 |
| Rounds per session | 10 |
| Total tasks per session | 100 |
| Storage per session | 50 MB |
| Max report size | 20 MB |

**ID Patterns (from DATA_SCHEMAS.md)**:
- Session: `sess_[a-zA-Z0-9]{8,}`
- Brief: `brief_[a-zA-Z0-9]{8,}`
- DataTask: `d[0-9]+` (d1, d2, d3...)
- ResearchTask: `r[0-9]+` (r1, r2, r3...)

---

## Dependency Graph

```
Phase 0 (Bootstrap) ─────────────────────────────────────────────────────┐
    │                                                                     │
    ▼                                                                     │
Phase 1 (Configuration & Types) ──────────────────────────────────────┐  │
    │                                                                  │  │
    ▼                                                                  │  │
Phase 2 (Errors & Logging) ───────────────────────────────────────┐   │  │
    │                                                              │   │  │
    ▼                                                              │   │  │
Phase 3 (Storage Layer) ──────────────────────────────────────┐   │   │  │
    │                                                          │   │   │  │
    ▼                                                          │   │   │  │
Phase 4 (LLM & Tools) ────────────────────────────────────┐   │   │   │  │
    │                                                      │   │   │   │  │
    ▼                                                      ▼   ▼   ▼   ▼  ▼
Phase 5 (Base Agent) ────────────────────────────────────────────────────┤
    │                                                                     │
    ├────────┬────────┬────────┬────────┬────────┬────────┐              │
    ▼        ▼        ▼        ▼        ▼        ▼        ▼              │
  6.1      6.2      6.3      6.4      6.5      6.6      6.7              │
Initial  Brief   Planner   Data   Research  Aggreg  Reporter             │
Research Builder                            ator                         │
    │        │        │        │        │        │        │              │
    └────────┴────────┴────────┴────────┴────────┴────────┘              │
                              │                                           │
                              ▼                                           │
                      Phase 7 (Orchestrator) ────────────────────────────┤
                              │                                           │
                              ▼                                           │
                      Phase 8 (Report Templates) ────────────────────────┤
                              │                                           │
                              ▼                                           │
                      Phase 9 (API Layer) ───────────────────────────────┤
                              │                                           │
                              ├──────────────────┐                       │
                              ▼                  ▼                       │
                      Phase 10 (Tests)   Phase 11 (Frontend)            │
                                                 │                       │
                                                 ▼                       │
                                         Phase 12 (Production)          │
```

---

## Phase 0: Project Bootstrap (CRITICAL - Blocking)

**Purpose**: Create the foundational structure that all other code depends on.
**Dependencies**: None
**Completion Criteria**: All directories exist, `python -c "import src"` works, dependencies install.

### 0.1 Directory Structure & Package Initialization
- [x] Create root `src/` directory
- [x] Create all subdirectories with `__init__.py` files:
  - [x] `src/__init__.py`
  - [x] `src/api/__init__.py`
  - [x] `src/agents/__init__.py`
  - [x] `src/orchestrator/__init__.py`
  - [x] `src/tools/__init__.py`
  - [x] `src/storage/__init__.py`
  - [x] `src/config/__init__.py`
- [x] Create `src/prompts/` directory (no __init__.py - markdown files only)
- [x] Create `src/templates/` directory structure:
  - [x] `src/templates/pdf/`
  - [x] `src/templates/excel/`
  - [x] `src/templates/pptx/`
- [x] Create `tests/` directory structure:
  - [x] `tests/__init__.py`
  - [x] `tests/conftest.py` (empty placeholder)
  - [x] `tests/test_agents/__init__.py`
  - [x] `tests/test_tools/__init__.py`
  - [x] `tests/test_orchestrator/__init__.py`
  - [x] `tests/test_api/__init__.py`
  - [x] `tests/test_storage/__init__.py`
- [x] Create `frontend/` placeholder directory with `.gitkeep`

### 0.2 Dependencies & Environment
- [x] Create `requirements.txt`:
  ```
  # Core
  fastapi>=0.109.0
  uvicorn[standard]>=0.27.0
  anthropic>=0.40.0
  pydantic>=2.5.0
  pydantic-settings>=2.1.0
  python-dotenv>=1.0.0

  # Async
  aiosqlite>=0.19.0
  httpx>=0.26.0

  # Report Generation
  weasyprint>=60.0
  reportlab>=4.0.0
  openpyxl>=3.1.0
  python-pptx>=0.6.21
  jinja2>=3.1.0

  # Utilities
  structlog>=24.1.0

  # Testing
  pytest>=8.0.0
  pytest-asyncio>=0.23.0
  pytest-cov>=4.1.0
  ```

- [x] Create `.env.example`:
  ```
  # Required
  ANTHROPIC_API_KEY=sk-ant-...

  # Database (optional, defaults to SQLite file)
  DATABASE_URL=sqlite+aiosqlite:///./ralph.db

  # Server
  HOST=0.0.0.0
  PORT=8000
  DEBUG=false
  LOG_LEVEL=INFO

  # Limits
  MAX_CONCURRENT_SESSIONS=10
  MAX_ROUNDS_PER_SESSION=10
  MAX_TASKS_PER_ROUND=10
  ROUND_TIMEOUT_SECONDS=300

  # Optional external APIs
  FINANCIAL_API_KEY=
  NEWS_API_KEY=
  SERPER_API_KEY=
  ```

- [x] Create `.gitignore` with Python/Node patterns, .env, __pycache__, *.db, reports/
- [x] Verify: `pip install -r requirements.txt` succeeds

### 0.3 Entry Point Placeholder
- [x] Create `main.py` with minimal FastAPI app:
  ```python
  from fastapi import FastAPI
  app = FastAPI(title="Ralph Deep Research", version="0.1.0")

  @app.get("/health")
  async def health():
      return {"status": "ok"}
  ```
- [x] Verify: `uvicorn main:app --port 8000` starts successfully

---

## Phase 1: Configuration & Core Types (CRITICAL - Blocking)

**Purpose**: Define settings and all data types that agents and tools use.
**Dependencies**: Phase 0
**Completion Criteria**: All Pydantic models validate correctly with example data from specs.

### 1.1 Configuration System
Reference: specs/ARCHITECTURE.md

- [x] Create `src/config/settings.py`:
  - [x] `Settings` class using pydantic-settings BaseSettings
  - [x] Environment variable loading with validation
  - [x] Required: ANTHROPIC_API_KEY
  - [x] Defaults for all optional settings
  - [x] `get_settings()` cached function

- [x] Create `src/config/models.py`:
  - [x] `AGENT_MODELS` dict:
    ```python
    AGENT_MODELS = {
        "initial_research": "claude-opus-4-20250514",
        "brief_builder": "claude-opus-4-20250514",
        "planner": "claude-opus-4-20250514",
        "data": "claude-sonnet-4-20250514",
        "research": "claude-opus-4-20250514",
        "aggregator": "claude-opus-4-20250514",
        "reporter": "claude-opus-4-20250514",
    }
    ```
  - [x] `get_model_for_agent(agent_name: str) -> str` function

### 1.2 Core Data Models (Pydantic)
Reference: specs/DATA_SCHEMAS.md

- [x] Create `src/api/schemas.py` with all models:

  **Enums** (define first, used by models):
  - [x] `SessionStatus` - CREATED, INITIAL_RESEARCH, BRIEF, PLANNING, EXECUTING, AGGREGATING, REPORTING, DONE, FAILED
  - [x] `BriefStatus` - DRAFT, APPROVED
  - [x] `TaskStatus` - PENDING, RUNNING, DONE, FAILED, PARTIAL
  - [x] `Priority` - HIGH, MEDIUM, LOW
  - [x] `ScopeType` - DATA, RESEARCH, BOTH
  - [x] `DataSource` - FINANCIAL_API, WEB_SEARCH, CUSTOM_API, DATABASE
  - [x] `SourceType` - NEWS, REPORTS, COMPANY_WEBSITE, ANALYST_REPORTS, SEC_FILINGS
  - [x] `FindingType` - FACT, OPINION, ANALYSIS
  - [x] `Confidence` - HIGH, MEDIUM, LOW
  - [x] `Sentiment` - POSITIVE, NEGATIVE, NEUTRAL, MIXED
  - [x] `OutputFormat` - PDF, EXCEL, PPTX, CSV
  - [x] `UserIntent` - INVESTMENT, MARKET_RESEARCH, COMPETITIVE, LEARNING, OTHER
  - [x] `EntityType` - COMPANY, MARKET, CONCEPT, PRODUCT, PERSON, SECTOR
  - [x] `DataFreshness` - REAL_TIME, DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL
  - [x] `RiskProfile` - CONSERVATIVE, MODERATE, AGGRESSIVE
  - [x] `SourceTypeResult` - NEWS, REPORT, WEBSITE, FILING, ACADEMIC, OTHER
  - [x] `PlannerDecisionStatus` - CONTINUE, DONE

  **Session Models**:
  - [x] `Session` - id, user_id, status, current_round, error, created_at, updated_at
  - [x] `SessionError` - code, message, details, recoverable

  **Initial Context Models**:
  - [x] `QueryAnalysis` - original_query, detected_language, detected_intent, confidence
  - [x] `EntityIdentifiers` - ticker, website, country, exchange
  - [x] `Entity` - name, type, identifiers, brief_description, category, sector
  - [x] `InitialContext` - session_id, query_analysis, entities, context_summary, suggested_topics, sources_used

  **Brief Models**:
  - [x] `ScopeItem` - id, topic, type, details
  - [x] `UserContext` - intent, horizon, risk_profile, additional
  - [x] `BriefConstraints` - focus_areas, exclude, time_period, geographic_focus, max_sources
  - [x] `Brief` - brief_id, version, status, goal, user_context, scope, output_formats, constraints

  **Plan & Task Models**:
  - [x] `DataTask` - id, scope_item_id, description, source, priority, expected_output, status
  - [x] `ResearchTask` - id, scope_item_id, description, focus, source_types, priority, status, search_queries
  - [x] `Plan` - round, brief_id, data_tasks, research_tasks, total_tasks, estimated_duration

  **Result Models**:
  - [x] `MetricValue` - value, unit, period, as_of_date
  - [x] `DataTable` - name, headers, rows
  - [x] `DataError` - field, error, fallback
  - [x] `DataMetadata` - source, api_used, timestamp, data_freshness
  - [x] `DataResult` - task_id, status, metrics, tables, raw_data, metadata, questions, errors

  - [x] `Finding` - finding, type, confidence, source
  - [x] `Theme` - theme, points, sentiment
  - [x] `ContradictionView` - position, source
  - [x] `Contradiction` - topic, view_1, view_2
  - [x] `Source` - type, title, url, date, credibility
  - [x] `ResearchResult` - task_id, status, summary, key_findings, detailed_analysis, themes, contradictions, sources, questions

  **Question Models**:
  - [x] `Question` - type, question, context, priority, source_task_id
  - [x] `FilteredQuestion` - question, source_task_id, relevance, action, reasoning

  **Planner Decision Models**:
  - [x] `CoverageItem` - topic, coverage_percent, covered_aspects, missing_aspects
  - [x] `PlannerDecision` - round, status, coverage, overall_coverage, reason, new_data_tasks, new_research_tasks, filtered_questions

  **Aggregation Models**:
  - [x] `KeyInsight` - insight, supporting_data, importance
  - [x] `DataHighlights` - dict of metric_name to value_with_context
  - [x] `Section` - title, brief_scope_id, summary, data_highlights, analysis, key_points, sentiment, charts_suggested, data_tables
  - [x] `ContradictionFound` - topic, sources, resolution
  - [x] `ActionItem` - action, priority, rationale
  - [x] `Recommendation` - verdict, confidence, confidence_reasoning, reasoning, pros, cons, action_items, risks_to_monitor
  - [x] `CoverageSummary` - topic, coverage_percent, gaps (per scope item)
  - [x] `AggregationMetadata` - total_rounds, total_data_tasks, total_research_tasks, sources_count, processing_time_seconds
  - [x] `AggregatedResearch` - session_id, brief_id, created_at, executive_summary, key_insights, sections, contradictions_found, recommendation, coverage_summary, metadata

  **Report Models**:
  - [x] `PDFConfig` - template, include_toc, include_charts, branding
  - [x] `ExcelConfig` - sheets, include_raw_data, include_charts
  - [x] `PPTXConfig` - template, slides_per_section, include_speaker_notes, aspect_ratio
  - [x] `CSVConfig` - delimiter, encoding, include_headers
  - [x] `ReportConfig` - formats, language, style, detail_level, pdf, excel, pptx, csv
  - [x] `GeneratedReport` - format, filename, file_path, structure, size_bytes

### 1.3 API Request/Response Models
- [x] Add to `src/api/schemas.py`:

  **Requests**:
  - [x] `CreateSessionRequest` - user_id (optional), initial_query
  - [x] `SendMessageRequest` - content
  - [x] `ApproveBriefRequest` - modifications (optional dict)

  **Responses**:
  - [x] `BriefBuilderAction` enum - ASK_QUESTION, PRESENT_BRIEF, BRIEF_APPROVED
  - [x] `SessionResponse` - session_id, status, action, message, brief (optional)
  - [x] `ProgressInfo` - data_tasks_completed, data_tasks_total, research_tasks_completed, research_tasks_total
  - [x] `StatusResponse` - session_id, status, current_round, progress, coverage
  - [x] `ReportInfo` - format, url, filename
  - [x] `ResultsResponse` - session_id, status, aggregated, reports
  - [x] `ErrorResponse` - error, message, details, session_id (optional)
  - [x] `HealthResponse` - status, version, timestamp

---

## Phase 2: Error Handling & Logging (CRITICAL - Blocking)

**Purpose**: Error hierarchy and logging must exist before any tool or agent code.
**Dependencies**: Phase 1
**Completion Criteria**: All error types raise/catch correctly, logs output valid JSON.

### 2.1 Error Classes
Reference: specs/ARCHITECTURE.md (Section 6: Error Handling)

- [x] Create `src/tools/errors.py`:

  **Base Error**:
  - [x] `RalphError(Exception)` - base with message, code, details, recoverable flag

  **Transient Errors** (retryable):
  - [x] `TransientError(RalphError)` - base for retryable
  - [x] `APITimeoutError(TransientError)` - API timeout
  - [x] `RateLimitError(TransientError)` - rate limit hit, retry_after field
  - [x] `NetworkError(TransientError)` - network issues
  - [x] `ServiceUnavailableError(TransientError)` - service down

  **Permanent Errors** (not retryable):
  - [x] `PermanentError(RalphError)` - base for non-retryable
  - [x] `InvalidInputError(PermanentError)` - bad input data
  - [x] `AuthenticationError(PermanentError)` - auth failure
  - [x] `QuotaExceededError(PermanentError)` - quota exceeded
  - [x] `DataNotFoundError(PermanentError)` - data not available

  **System Errors** (requires intervention):
  - [x] `SystemError(RalphError)` - base for system errors
  - [x] `DatabaseError(SystemError)` - database failure
  - [x] `StorageFullError(SystemError)` - storage full
  - [x] `ConfigurationError(SystemError)` - bad configuration

  **Session Errors**:
  - [x] `SessionNotFoundError(PermanentError)` - session not found
  - [x] `SessionFailedError(PermanentError)` - session in failed state
  - [x] `BriefNotApprovedError(PermanentError)` - brief not approved yet

  **Retry Errors**:
  - [x] `RetryExhaustedError(PermanentError)` - max retries reached
  - [x] `CircuitOpenError(TransientError)` - circuit breaker open

  **Agent Errors** (additional):
  - [x] `AgentError(RalphError)` - base for agent errors
  - [x] `AgentTimeoutError(AgentError, TransientError)` - agent timed out
  - [x] `AgentExecutionError(AgentError)` - agent execution failed

### 2.2 Logging Setup
- [x] Create `src/tools/logging.py`:
  - [x] Configure structlog with JSON output
  - [x] `get_logger(name: str)` factory function
  - [x] Context processors: timestamp, level, logger name
  - [x] `bind_context()` for session_id, agent, task_id, round
  - [x] `LogContext` context manager for temporary context binding
  - [x] `filter_sensitive_data` processor - API keys never logged
  - [x] `truncate_large_values` processor - prevent log bloat
  - [x] Log level configurable via `configure_logging()`

### 2.3 Retry Logic
Reference: specs/ARCHITECTURE.md (Section 7: Retry Logic)

- [x] Create `src/tools/retry.py`:

  **Configuration**:
  - [x] `RetryConfig` dataclass:
    - max_attempts: int = 3
    - base_delay: float = 1.0
    - max_delay: float = 60.0
    - exponential_base: float = 2.0
    - jitter: float = 0.25
    - retryable_exceptions: tuple of exception types
    - rate_limit_delay: float = 60.0

  - [x] `RETRY_CONFIGS` dict for operation types:
    - llm_call: RetryConfig(max_attempts=3, base_delay=2.0)
    - api_call: RetryConfig(max_attempts=3, base_delay=1.0)
    - web_search: RetryConfig(max_attempts=2, base_delay=5.0)
    - file_generation: RetryConfig(max_attempts=2, base_delay=1.0)
    - database: RetryConfig(max_attempts=3, base_delay=0.5)

  **Retry Handler**:
  - [x] `RetryHandler` class:
    - `__init__(config: RetryConfig)`
    - `async execute(func, *args, **kwargs)` - execute with retry
    - `_calculate_delay(attempt, error)` - exponential backoff with jitter
    - RateLimitError uses retry_after from error

  - [x] `@with_retry(config_name: str)` decorator

  **Circuit Breaker**:
  - [x] `CircuitState` enum: CLOSED, OPEN, HALF_OPEN
  - [x] `CircuitBreaker` class:
    - `__init__(name, failure_threshold=5, recovery_timeout=60, half_open_max_calls=3)`
    - `async execute(func, *args, **kwargs)`
    - `_on_success()` / `_on_failure()` - state recording
    - `_can_execute()` - state-based permission check
    - `_transition_to_open/half_open/closed()` - state transitions
    - `reset()` - manual reset
    - `get_stats()` - circuit statistics

  **Combined Executor**:
  - [x] `ResilientExecutor` class - combines retry + circuit breaker

---

## Phase 3: Storage Layer (CRITICAL - Blocking) ✅ COMPLETE

**Purpose**: Agents need to save state after each task (Ralph Pattern).
**Dependencies**: Phase 2
**Completion Criteria**: Sessions can be created, saved, restored; state persists across restarts.
**Completed**: 2026-01-19 | Tag: 0.0.4

### 3.1 Database Setup
Reference: specs/ARCHITECTURE.md (Section 4: State Management)

- [x] Create `src/storage/database.py`:
  - [x] `Database` class:
    - `__init__(database_url: str)`
    - `async connect()` / `async disconnect()`
    - `async init_db()` - create tables
    - `async execute(query, params)` - run query
    - `async fetch_one(query, params)` - single row
    - `async fetch_all(query, params)` - multiple rows
    - Context manager support

  - [x] SQL schemas:
    ```sql
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'created',
        current_round INTEGER DEFAULT 0,
        error_code TEXT,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS session_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        data_type TEXT NOT NULL,
        round INTEGER,
        task_id TEXT,
        data JSON NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );

    CREATE TABLE IF NOT EXISTS session_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        file_type TEXT NOT NULL,
        filename TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES sessions(id)
    );

    CREATE INDEX IF NOT EXISTS idx_session_data_lookup
        ON session_data(session_id, data_type, round);
    CREATE INDEX IF NOT EXISTS idx_session_files_session
        ON session_files(session_id);
    ```

### 3.2 Session Manager
- [x] Create `src/storage/session.py`:
  - [x] `SessionManager` class:
    - `__init__(database: Database)`
    - `async create_session(user_id: str, initial_query: str) -> Session`
    - `async get_session(session_id: str) -> Session`
    - `async update_status(session_id: str, status: SessionStatus)`
    - `async increment_round(session_id: str) -> int`
    - `async set_error(session_id: str, error: SessionError)`

    **State Management (Ralph Pattern)**:
    - `async save_state(session_id, data_type, data, round=None, task_id=None)`
    - `async get_state(session_id, data_type, round=None) -> dict | None`
    - `async get_all_states(session_id, data_type) -> List[dict]`
    - `async get_task_result(session_id, task_id) -> dict | None`

    **Recovery**:
    - `async restore_session(session_id) -> dict` (full state reconstruction)
    - `async get_resume_point(session_id) -> tuple[SessionStatus, int]`

    **Scalability Limit Enforcement** (from specs/ARCHITECTURE.md):
    - `async validate_session_limit()` - check concurrent sessions < 10
    - `async validate_storage_limit(session_id)` - check session storage < 50MB
    - `_count_active_sessions() -> int` - count non-terminal sessions

  - [x] Session ID generation: `sess_{uuid4().hex[:12]}`
  - [x] Data type constants (DataType enum):
    - `INITIAL_CONTEXT`
    - `BRIEF`
    - `CONVERSATION`
    - `PLAN`
    - `DATA_RESULT`
    - `RESEARCH_RESULT`
    - `PLANNER_DECISION`
    - `AGGREGATION`
    - `REPORT_CONFIG`

### 3.3 File Storage
- [x] Create `src/storage/files.py`:
  - [x] `FileStorage` class:
    - `__init__(base_path: str = "./reports")`
    - `get_session_dir(session_id: str) -> Path`
    - `async save_file(session_id, file_type, content: bytes, filename) -> str`
    - `async get_file(session_id, filename) -> bytes`
    - `async list_files(session_id) -> List[dict]`
    - `async delete_session_files(session_id)`
    - `get_file_url(session_id, filename) -> str`
  - [x] Directory structure: `{base_path}/{session_id}/{filename}`
  - [x] Ensure directories created automatically
  - [x] Path traversal protection
  - [x] File size validation against limits

---

## Phase 4: LLM Client & Tools (CRITICAL - Blocking) ✅ COMPLETE

**Purpose**: All agents depend on LLM client; web search needed for Research agent.
**Dependencies**: Phase 3
**Completion Criteria**: Can call Claude API with retries, token tracking works.
**Completed**: 2026-01-19 | Tag: 0.0.5

### 4.1 LLM Client
- [x] Create `src/tools/llm.py`:
  - [x] `LLMClient` class:
    - `__init__(api_key: str)`
    - `async create_message(model, system, messages, max_tokens=4096, temperature=0.7) -> str`
    - `async create_structured(model, system, messages, response_model: Type[T]) -> T`
    - Token tracking: input_tokens, output_tokens per call
    - Cost estimation helper
    - Integration with RetryHandler for transient errors
    - Rate limit handling (RateLimitError with retry_after)

  - [x] Helper functions:
    - `get_model_for_agent(agent_name: str) -> str`

### 4.2 Web Search Client
- [x] Create `src/tools/web_search.py`:
  - [x] `SearchResult` model: title, url, snippet, date
  - [x] `WebSearchClient` abstract base class:
    - `async search(query: str, num_results: int = 10) -> List[SearchResult]`
    - `async fetch_content(url: str) -> str`

  - [x] `MockSearchClient(WebSearchClient)` - for development/testing
  - [x] `SerperClient(WebSearchClient)` - real implementation (if SERPER_API_KEY set)
  - [x] Factory: `get_search_client() -> WebSearchClient`

### 4.3 API Client (External Data Sources)
- [x] Create `src/tools/api_client.py`:
  - [x] `APIClient` base class:
    - `__init__(base_url: str, api_key: str = None)`
    - `async get(endpoint, params) -> dict`
    - `async post(endpoint, data) -> dict`
    - Retry integration
    - Rate limiting

  - [x] `FinancialAPIClient(APIClient)` - placeholder for Yahoo Finance, etc.
  - [x] `CustomAPIClient(APIClient)` - user-configured endpoints

### 4.4 File Generator
- [x] Create `src/tools/file_generator.py`:
  - [x] `FileGenerator` class:
    - `__init__(template_dir: str = "src/templates")`

  - [x] `generate_pdf(report_config, aggregated, output_path) -> str`:
    - Load HTML template from templates/pdf/
    - Render with Jinja2
    - Convert to PDF with WeasyPrint
    - Return file path

  - [x] `generate_excel(report_config, aggregated, output_path) -> str`:
    - Create workbook with openpyxl
    - Add summary sheet
    - Add data sheets
    - Return file path

  - [x] `generate_pptx(report_config, aggregated, output_path) -> str`:
    - Create presentation with python-pptx
    - Add slides based on config
    - Support 16:9 and 4:3 aspect ratios
    - Return file path

  - [x] `generate_csv(report_config, aggregated, output_path) -> str`:
    - Export data tables as CSV
    - Configure delimiter, encoding per CSVConfig
    - Include headers based on config
    - Return file path

### 4.5 Database Client (for Data Agent)
- [x] Create `src/tools/db_client.py`:
  - [x] `DatabaseQueryClient` class:
    - `__init__(connection_string: str = None)`
    - `async execute_query(query: str, params: dict = None) -> List[dict]`
    - `async get_schema_info(table_name: str) -> dict`
    - Query building helpers for common patterns
    - Result formatting for Data Agent consumption
  - [x] Safety: Read-only queries only, parameterized queries to prevent injection
  - [x] Integration with RetryHandler for transient errors

### 4.6 Performance Configuration (Included in Phase 1)
- [x] Create `src/config/timeouts.py` (implemented in settings.py):
  ```python
  # Agent timeout configuration (from specs/ARCHITECTURE.md)
  AGENT_TIMEOUTS = {
      "initial_research": 90,    # Target: 60s, Max: 90s
      "brief_builder": 10,       # Target: 5s, Max: 10s
      "planner": 20,             # Target: 10s, Max: 20s
      "data_task": 45,           # Target: 30s, Max: 45s
      "research_task": 90,       # Target: 60s, Max: 90s
      "round_timeout": 300,      # Target: 120s, Max: 300s
      "aggregation": 120,        # Target: 60s, Max: 120s
      "reporting": 120,          # Target: 60s, Max: 120s
  }

  # Scalability limits (from specs/ARCHITECTURE.md)
  SCALABILITY_LIMITS = {
      "max_concurrent_sessions": 10,
      "max_tasks_per_round": 10,
      "max_rounds_per_session": 10,
      "max_tasks_per_session": 100,
      "max_storage_per_session_mb": 50,
      "max_report_size_mb": 20,
  }
  ```
- [x] Integrate timeouts into agent execution (in settings.py get_timeout() function)
- [x] Add limit validation in SessionManager (implemented in Phase 3)

---

## Phase 5: Base Agent & Initial Agents (HIGH) 🔄 PARTIAL

**Purpose**: Establish agent pattern and implement Initial Research + Brief Builder.
**Dependencies**: Phase 4
**Completion Criteria**: Initial Research produces InitialContext, Brief Builder conducts dialog.
**Status**: 5.1-5.4 Complete (2026-01-19), 5.5 (remaining agents) pending

### 5.1 Base Agent Class ✅ COMPLETE
Reference: specs/ARCHITECTURE.md, specs/PROMPTS.md

- [x] Create `src/agents/base.py`:
  - [x] `BaseAgent` abstract class:
    - Abstract `agent_name` property for model selection and logging
    - `model` property using `get_model_for_agent()`
    - `system_prompt` property with markdown file loading
    - `timeout_seconds` property from config
    - `_load_prompt()` from `src/prompts/{agent_name}.md`
    - `validate_input()` for context validation
    - `_call_llm()` for LLM calls with agent's model
    - `_call_llm_structured()` for structured output
    - `_save_result()` for Ralph Pattern state persistence
    - `_get_state()` for state retrieval
    - `run()` with timeout enforcement and error handling
    - Utility methods: `format_messages()`, `format_conversation()`

### 5.2 Agent Prompts ✅ COMPLETE
- [x] Create `src/prompts/initial_research.md` - Fast preliminary research
- [x] Create `src/prompts/brief_builder.md` - Interactive dialog for Brief building
- [x] Create `src/prompts/planner.md` - Task decomposition and coverage planning
- [x] Create `src/prompts/data.md` - Structured data collection
- [x] Create `src/prompts/research.md` - Qualitative analysis and web research
- [x] Create `src/prompts/aggregator.md` - Result synthesis and recommendations
- [x] Create `src/prompts/reporter.md` - Report structure specification

### 5.3 Initial Research Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 1

- [x] Create `src/agents/initial_research.py`:
  - [x] `InitialResearchAgent(BaseAgent)`:
    - `agent_name = "initial_research"`
    - Input: `{"user_query": str, "session_id": str}`
    - Output: `InitialContext` dict

  - [x] Process:
    1. Parse user query
    2. Extract entities (companies, tickers, markets, concepts)
    3. Detect language (en/ru) and intent
    4. Quick web search for entity verification
    5. Generate context summary
    6. Suggest research topics

  - [x] Features:
    - Pydantic models for LLM structured output
    - Web search integration
    - Fallback output on LLM failure
    - State persistence via SessionManager

  - [x] Constraints: 90 second timeout (target 60s)

### 5.4 Brief Builder Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 2

- [x] Create `src/agents/brief_builder.py`:
  - [x] `BriefBuilderAgent(BaseAgent)`:
    - `agent_name = "brief_builder"`
    - Input: `{"session_id": str, "initial_context": dict, "conversation_history": List, "current_brief": dict | None, "user_message": str}`
    - Output: `{"action": BriefBuilderAction, "message": str, "current_brief": dict | None}`

  - [x] Actions:
    - `ASK_QUESTION` - return clarifying question
    - `PRESENT_BRIEF` - return draft Brief for approval
    - `BRIEF_APPROVED` - return approved Brief

  - [x] Features:
    - Pydantic models for LLM structured output
    - Brief conversion with validation
    - Conversation history management
    - Fallback output on LLM failure
    - State persistence (conversation + approved brief)

  - [x] Constraints: 10 second timeout (target 5s)

### 5.5 Tests ✅ COMPLETE
- [x] `tests/test_agents/test_base.py` - 26 tests
- [x] `tests/test_agents/test_initial_research.py` - 22 tests
- [x] `tests/test_agents/test_brief_builder.py` - 24 tests

---

## Phase 6: Core Execution Agents (HIGH) ✅ COMPLETE

**Purpose**: Implement Planner, Data, and Research agents.
**Dependencies**: Phase 5
**Completion Criteria**: Planner creates tasks, Data/Research produce results with follow-up questions.
**Status**: Complete (2026-01-19) - All 3 agents implemented with 82 tests

### 6.1 Planner Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 3

- [x] Create `src/agents/planner.py`:
  - [x] `PlannerAgent(BaseAgent)`:
    - `agent_name = "planner"`

  - [x] **Initial Planning Mode**:
    - Input: `{"mode": "initial", "session_id": str, "brief": Brief}`
    - Output: `Plan` with data_tasks and research_tasks
    - Task ID format: d1, d2... (data), r1, r2... (research)
    - Max 10 tasks per round

  - [x] **Review Mode**:
    - Input: `{"mode": "review", "session_id": str, "brief": Brief, "round": int, "data_results": List, "research_results": List, "new_questions": List}`
    - Output: `PlannerDecision`
    - Coverage calculation per scope item
    - Question filtering with relevance scoring
    - Decision: "continue" if any scope < 80%, else "done"
    - Max 10 rounds total

  - [x] Features implemented:
    - Pydantic models for structured LLM output (LLMPlanOutput, LLMPlannerDecisionOutput)
    - Task ID generation and deduplication
    - Coverage tracking with threshold enforcement (80%)
    - Fallback plan/decision creation on LLM failure
    - State persistence via SessionManager

### 6.2 Data Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 4

- [x] Create `src/agents/data.py`:
  - [x] `DataAgent(BaseAgent)`:
    - `agent_name = "data"`
    - Input: `{"task": DataTask, "entity_context": dict, "available_apis": List[str]}`
    - Output: `DataResult`

  - [x] Process:
    1. Parse task for specific metrics
    2. Select appropriate API source
    3. Execute API call
    4. Extract and validate data
    5. Structure with metadata (source, timestamp, freshness)
    6. Generate follow-up questions if anomalies found

  - [x] Constraints: 45 second timeout per task (data_task timeout key)

  - [x] Features implemented:
    - Pydantic models for structured LLM output (LLMDataOutput)
    - API data fetching with FinancialAPIClient integration
    - Ticker extraction from task identifiers
    - Fallback result generation on LLM/API failure
    - State persistence via SessionManager

### 6.3 Research Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 5

- [x] Create `src/agents/research.py`:
  - [x] `ResearchAgent(BaseAgent)`:
    - `agent_name = "research"`
    - Input: `{"task": ResearchTask, "entity_context": dict, "brief_context": dict, "previous_findings": List[str]}`
    - Output: `ResearchResult`

  - [x] Process:
    1. Generate 3-5 search queries
    2. Execute web search
    3. Read and analyze sources
    4. Extract findings (fact/opinion/analysis)
    5. Identify themes
    6. Detect contradictions
    7. Evaluate source credibility
    8. Generate follow-up questions

  - [x] Constraints: 90 second timeout per task (research_task timeout key)

  - [x] Features implemented:
    - Pydantic models for structured LLM output (LLMResearchOutput)
    - Search query generation with source type awareness
    - Web search integration with result deduplication
    - Finding, theme, contradiction extraction
    - Source credibility evaluation
    - Fallback result generation on LLM failure
    - State persistence via SessionManager

### 6.4 Tests ✅ COMPLETE
- [x] `tests/test_agents/test_planner.py` - 27 tests
- [x] `tests/test_agents/test_data.py` - 26 tests
- [x] `tests/test_agents/test_research.py` - 29 tests

---

## Phase 7: Aggregation & Reporting Agents (HIGH) ✅ COMPLETE

**Purpose**: Synthesize all results and generate output specifications.
**Dependencies**: Phase 6
**Completion Criteria**: Aggregator produces coherent summary, Reporter generates file specs.
**Status**: Complete (2026-01-19) - 2 agents implemented with 65 tests

### 7.1 Aggregator Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 6

- [x] Create `src/agents/aggregator.py`:
  - [x] `AggregatorAgent(BaseAgent)`:
    - `agent_name = "aggregator"`
    - Input: `{"session_id": str, "brief": Brief, "data_results": List[DataResult], "research_results": List[ResearchResult], "rounds_completed": int}`
    - Output: `AggregatedResearch`

  - [x] Process:
    1. Inventory all results
    2. Map results to Brief scope items
    3. Check for contradictions
    4. Synthesize sections (one per scope item)
    5. Write executive summary
    6. Extract 3-10 key insights
    7. Generate recommendation with verdict, confidence, reasoning
    8. Create action items

  - [x] Features implemented:
    - Pydantic models for structured LLM output (LLMAggregatorOutput, LLMKeyInsight, LLMSection, LLMRecommendation)
    - Context formatting for brief, data results, and research results
    - Fallback result generation on LLM failure
    - Enum conversion with fallback for invalid values
    - State persistence via SessionManager (DataType.AGGREGATION)

### 7.2 Reporter Agent ✅ COMPLETE
Reference: specs/PROMPTS.md Section 7

- [x] Create `src/agents/reporter.py`:
  - [x] `ReporterAgent(BaseAgent)`:
    - `agent_name = "reporter"`
    - Input: `{"session_id": str, "aggregated": AggregatedResearch, "formats": List[OutputFormat], "brief": Brief (optional)}`
    - Output: `ReportConfig`

  - [x] Process:
    1. Analyze aggregated content
    2. Normalize output formats (string/enum handling)
    3. Generate content specs for each format via LLM
    4. Build ReportConfig with format-specific configurations
    5. Optionally generate actual files via FileGenerator

  - [x] Features implemented:
    - Pydantic models for structured LLM output (LLMContentSpec, LLMPDFSpec, LLMExcelSpec, LLMPPTXSpec)
    - Format normalization (strings/enums → OutputFormat)
    - Fallback content spec generation on LLM failure
    - FileGenerator integration for actual file creation
    - State persistence via SessionManager (DataType.REPORT_CONFIG)

### 7.3 Tests ✅ COMPLETE
- [x] `tests/test_agents/test_aggregator.py` - 28 tests
- [x] `tests/test_agents/test_reporter.py` - 37 tests

---

## Phase 8: Report Templates (HIGH)

**Purpose**: Create templates for PDF, Excel, PowerPoint generation.
**Dependencies**: Phase 4.4
**Completion Criteria**: All three formats generate valid, readable files.

### 8.1 PDF Template
- [ ] Create `src/templates/pdf/report.html`:
  - [ ] Jinja2 template structure
  - [ ] Title page with branding
  - [ ] Table of contents
  - [ ] Executive summary section
  - [ ] Key insights section
  - [ ] Sections per scope item (data highlights, analysis, charts)
  - [ ] Recommendation section (highlighted)
  - [ ] Sources/citations section
  - [ ] CSS styling for professional appearance
  - [ ] Branding support (from specs/DATA_SCHEMAS.md):
    - [ ] Logo placement in header (logo_url variable)
    - [ ] Primary color CSS variables (primary_color)
    - [ ] Company name in footer (company_name)

### 8.2 Excel Template
- [ ] Create `src/templates/excel/` with README.md describing structure:
  - [ ] Summary sheet layout (key metrics)
  - [ ] Data sheet layouts (tables, charts)
  - [ ] Raw data sheet layout

### 8.3 PowerPoint Template
- [ ] Create `src/templates/pptx/report.pptx`:
  - [ ] Title slide layout
  - [ ] Content slide layout (bullet points)
  - [ ] Two-column slide layout
  - [ ] Chart slide layout
  - [ ] 10-12 slides typical
  - [ ] Aspect ratio support:
    - [ ] 16:9 template (default)
    - [ ] 4:3 template (alternative)

---

## Phase 9: Orchestrator & Pipeline (HIGH) ✅ COMPLETE

**Purpose**: Coordinate all agents and manage the research workflow.
**Dependencies**: Phase 7
**Completion Criteria**: Full research pipeline runs from query to reports.
**Status**: Complete (2026-01-19) - ParallelExecutor + ResearchPipeline with 56 tests

### 9.1 Parallel Executor ✅ COMPLETE
Reference: specs/ARCHITECTURE.md Section 5

- [x] Create `src/orchestrator/parallel.py`:
  - [x] `ParallelExecutor` class:
    - `__init__(data_agent: DataAgent, research_agent: ResearchAgent)`
    - `async execute_round(data_tasks: List[DataTask], research_tasks: List[ResearchTask], context: dict, timeout: int = 300) -> Tuple[List[DataResult], List[ResearchResult]]`

  - [x] Implementation:
    - Use `asyncio.gather()` with `return_exceptions=True`
    - Execute all data tasks concurrently
    - Execute all research tasks concurrently
    - Handle individual task failures gracefully
    - Collect all questions from results
    - Timeout handling (raise RoundTimeoutError)

  - [x] Custom errors:
    - `RoundTimeoutError(TransientError)` - Round execution timed out
    - `TaskExecutionError(RalphError)` - Individual task execution error

  - [x] Features implemented:
    - Statistics tracking (rounds, tasks, success/failure counts, timeouts)
    - Failed result creation for error tracking
    - Question collection from all results
    - Configurable timeout via config or parameter

### 9.2 Research Pipeline ✅ COMPLETE
Reference: specs/ARCHITECTURE.md Section 2

- [x] Create `src/orchestrator/pipeline.py`:
  - [x] `ResearchPipeline` class:
    - Inject all agents and services
    - State machine implementation

  - [x] State transitions:
    ```
    CREATED → INITIAL_RESEARCH → BRIEF ↔ (revisions) → PLANNING →
    EXECUTING ↔ REVIEW (loop) → AGGREGATING → REPORTING → DONE
    (Any state → FAILED on error)
    ```

  - [x] Public methods:
    - `async start_session(user_id: str, initial_query: str) -> Session`
    - `async process_message(session_id: str, content: str) -> SessionResponse`
    - `async approve_brief(session_id: str, modifications: dict = None) -> SessionResponse`
    - `async get_status(session_id: str) -> StatusResponse`
    - `async get_results(session_id: str) -> ResultsResponse`
    - `async resume_session(session_id: str) -> SessionResponse`

  - [x] Internal methods:
    - `async _run_initial_research(session_id: str)`
    - `async _run_brief_building(session_id: str, message: str) -> SessionResponse`
    - `async _run_planning(session_id: str)`
    - `async _run_execution_loop(session_id: str)` - Planner → Execute → Review loop
    - `async _run_aggregation(session_id: str)`
    - `async _run_reporting(session_id: str)`
    - `async _transition_state(session_id: str, new_status: SessionStatus)`
    - `async _handle_error(session_id: str, error: Exception)`

  - [x] Features:
    - Save state after each operation (Ralph Pattern)
    - Max 10 rounds enforcement (MaxRoundsExceededError)
    - Max 10 tasks per round enforcement (via Planner)
    - Max 100 tasks per session enforcement
    - Error handling and status transitions
    - Session recovery from any state
    - Timeout enforcement per agent (from AGENT_TIMEOUTS config)
    - VALID_TRANSITIONS constant for state machine validation
    - InvalidStateTransitionError for invalid transitions

  - [x] Custom errors:
    - `PipelineError(RalphError)` - Base pipeline error
    - `InvalidStateTransitionError(PipelineError)` - Invalid state transition
    - `MaxRoundsExceededError(PipelineError)` - Max rounds exceeded

### 9.3 Tests ✅ COMPLETE
- [x] `tests/test_orchestrator/test_parallel.py` - 22 tests
- [x] `tests/test_orchestrator/test_pipeline.py` - 34 tests

---

## Phase 10: API Layer (HIGH)

**Purpose**: Expose pipeline via REST API.
**Dependencies**: Phase 9
**Completion Criteria**: All endpoints work, can complete full research flow via API.

### 10.1 FastAPI Application Setup
- [ ] Update `main.py`:
  - [ ] FastAPI app with lifespan (startup/shutdown)
  - [ ] Database initialization on startup
  - [ ] CORS middleware configuration
  - [ ] Exception handlers (RalphError → HTTP responses)
  - [ ] Request ID middleware for tracing
  - [ ] Include API router

### 10.2 API Routes
Reference: specs/ralph_prd.md Section 8

- [ ] Create `src/api/routes.py`:
  - [ ] `POST /api/sessions` - Start new research session
    - Input: CreateSessionRequest
    - Runs Initial Research
    - Returns SessionResponse with first Brief Builder message

  - [ ] `POST /api/sessions/{session_id}/messages` - Send message during brief building
    - Input: SendMessageRequest
    - Returns SessionResponse with Brief Builder response

  - [ ] `POST /api/sessions/{session_id}/approve` - Approve Brief
    - Input: ApproveBriefRequest (optional modifications)
    - Triggers background research execution
    - Returns SessionResponse with status "executing"

  - [ ] `GET /api/sessions/{session_id}` - Get session status
    - Returns StatusResponse with progress and coverage

  - [ ] `GET /api/sessions/{session_id}/results` - Get results
    - Returns ResultsResponse with aggregated research and report URLs

  - [ ] `GET /api/health` - Health check
    - Returns HealthResponse

### 10.3 Dependencies
- [ ] Create `src/api/dependencies.py`:
  - [ ] `get_database() -> Database` - database dependency
  - [ ] `get_session_manager() -> SessionManager`
  - [ ] `get_pipeline() -> ResearchPipeline`
  - [ ] `verify_session(session_id) -> Session` - validate session exists

### 10.4 Background Tasks
- [ ] Implement background execution for research:
  - [ ] Use FastAPI BackgroundTasks or asyncio.create_task
  - [ ] Pipeline runs after Brief approval
  - [ ] Status polling via GET /sessions/{id}

---

## Phase 11: Testing (MEDIUM)

**Purpose**: Ensure reliability and catch regressions.
**Dependencies**: Phase 10
**Completion Criteria**: >80% code coverage, all critical paths tested.

### 11.1 Test Infrastructure
- [ ] Update `tests/conftest.py`:
  - [ ] pytest fixtures:
    - Test database (in-memory SQLite)
    - Mock LLM client with canned responses
    - Mock web search client
    - Sample data: Brief, Plan, DataResult, ResearchResult
    - Session manager instance
  - [ ] pytest-asyncio configuration
  - [ ] Test settings override

### 11.2 Unit Tests - Tools
- [ ] `tests/test_tools/test_errors.py` - Error class behavior
- [ ] `tests/test_tools/test_retry.py` - Retry logic, circuit breaker
- [ ] `tests/test_tools/test_llm.py` - LLM client (mocked)
- [ ] `tests/test_tools/test_web_search.py` - Search client (mocked)
- [ ] `tests/test_tools/test_logging.py` - Logger configuration

### 11.3 Unit Tests - Storage
- [ ] `tests/test_storage/test_database.py` - CRUD operations
- [ ] `tests/test_storage/test_session.py` - Session manager
- [ ] `tests/test_storage/test_files.py` - File storage

### 11.4 Unit Tests - Agents
- [ ] `tests/test_agents/test_base.py` - Base class behavior
- [ ] `tests/test_agents/test_initial_research.py` - Query parsing, entity extraction
- [ ] `tests/test_agents/test_brief_builder.py` - Conversation flow
- [ ] `tests/test_agents/test_planner.py` - Task generation, coverage calculation
- [ ] `tests/test_agents/test_data.py` - Data extraction
- [ ] `tests/test_agents/test_research.py` - Analysis synthesis
- [ ] `tests/test_agents/test_aggregator.py` - Result aggregation
- [ ] `tests/test_agents/test_reporter.py` - Report configuration

### 11.5 Integration Tests
- [ ] `tests/test_orchestrator/test_parallel.py` - Parallel execution
- [ ] `tests/test_orchestrator/test_pipeline.py` - Full pipeline flow
- [ ] `tests/test_api/test_routes.py` - All API endpoints

---

## Phase 12: Frontend (LOWER PRIORITY)

**Purpose**: User interface for research system.
**Dependencies**: Phase 10
**Completion Criteria**: Users can conduct research through web UI.

### 12.1 React Application Setup
- [ ] Create `frontend/` with Vite + React 18 + TypeScript
- [ ] Configure TailwindCSS
- [ ] Set up React Query for API calls
- [ ] Create API client (`frontend/src/api/client.ts`)

### 12.2 Components
- [ ] `Chat.tsx` - Chat interface for Brief Builder
- [ ] `BriefDisplay.tsx` - Display Brief with edit/approve buttons
- [ ] `ProgressTracker.tsx` - Research progress visualization (rounds, tasks, coverage)
- [ ] `ReportViewer.tsx` - Download and preview reports

### 12.3 Pages
- [ ] `Home.tsx` - Landing page, start new research
- [ ] `Research.tsx` - Active research session (chat + progress + results)

### 12.4 Hooks
- [ ] `useResearch.ts` - Research session state management
- [ ] `usePolling.ts` - Status polling during execution
- [ ] `useWebSocket.ts` - Real-time updates subscription (optional enhancement)

### 12.5 Real-Time Updates (Optional Enhancement)
Reference: specs/README.md mentions WebSocket for real-time updates
- [ ] Add WebSocket endpoint `/ws/sessions/{session_id}`
- [ ] Emit events: task_started, task_completed, round_finished, status_changed
- [ ] Frontend WebSocket subscription in `useWebSocket.ts` hook
- [ ] Graceful fallback to polling if WebSocket unavailable

---

## Phase 13: Production Readiness (LOWER PRIORITY)

**Purpose**: Prepare for deployment.
**Dependencies**: Phase 12
**Completion Criteria**: System runs reliably in production environment.

### 13.1 Logging & Monitoring
- [ ] Structured logging to stdout (JSON format for parsing)
- [ ] Request/response logging
- [ ] Performance metrics (timing, token usage, costs)
- [ ] Error tracking (Sentry integration optional)

### 13.2 Documentation
- [ ] API documentation (auto-generated OpenAPI/Swagger)
- [ ] README with setup instructions
- [ ] Environment variable documentation
- [ ] Architecture overview

### 13.3 Deployment
- [ ] Create `Dockerfile` for backend
- [ ] Create `docker-compose.yml` for local development
- [ ] Production configuration guide
- [ ] Database backup strategy

---

## Implementation Order Summary

### Critical Path (Blocking - Must Complete First):
1. **Phase 0**: Project Bootstrap (1-2 hours)
2. **Phase 1**: Configuration & Core Types (4-6 hours)
3. **Phase 2**: Error Handling & Logging (2-3 hours)
4. **Phase 3**: Storage Layer (3-4 hours)
5. **Phase 4**: LLM Client & Tools (4-6 hours)

### Core Functionality:
6. **Phase 5**: Base Agent & Initial Agents (6-8 hours)
7. **Phase 6**: Core Execution Agents (8-10 hours)
8. **Phase 7**: Aggregation & Reporting Agents (4-6 hours)
9. **Phase 8**: Report Templates (4-6 hours)
10. **Phase 9**: Orchestrator & Pipeline (6-8 hours)
11. **Phase 10**: API Layer (4-6 hours)

### Quality & Polish:
12. **Phase 11**: Testing (8-12 hours)
13. **Phase 12**: Frontend (16-20 hours)
14. **Phase 13**: Production Readiness (8-12 hours)

**Estimated Total**: 80-110 hours

---

## Quick Reference

### Model IDs
- **Opus**: `claude-opus-4-20250514`
- **Sonnet**: `claude-sonnet-4-20250514`

### Session Data Types
- `initial_context` - InitialContext from Initial Research
- `brief` - Brief from Brief Builder
- `conversation` - Conversation history for Brief Builder
- `plan` - Plan from Planner (per round)
- `data_result` - DataResult from Data agent (per task)
- `research_result` - ResearchResult from Research agent (per task)
- `planner_decision` - PlannerDecision from Planner review (per round)
- `aggregation` - AggregatedResearch from Aggregator
- `report_config` - ReportConfig from Reporter

### Session Status Flow
```
CREATED → INITIAL_RESEARCH → BRIEF → PLANNING → EXECUTING ↔ REVIEW → AGGREGATING → REPORTING → DONE
                                                                                              ↓
                                                                                           FAILED
```

### Coverage Targets
- **Per scope item**: 80% minimum
- **Overall**: 80% minimum
- **Max rounds**: 10

---

## Identified Gaps Between Specs and Prior Plan (Now Addressed)

The following items were found in the specification documents but were missing or incomplete in earlier versions of this plan. They have been incorporated into the phases above:

### DATA_SCHEMAS.md Gaps (Now Fixed)
| Gap | Location Fixed | Notes |
|-----|----------------|-------|
| `DATABASE` enum value for DataSource | Phase 1.2 | Added to DataSource enum |
| `source_task_id` field on Question | Phase 1.2 | Added to Question model |
| `search_queries` field on ResearchTask | Phase 1.2 | Added to ResearchTask model |
| `geographic_focus` in BriefConstraints | Phase 1.2 | Added to BriefConstraints model |
| `AggregationMetadata` model | Phase 1.2 | Added complete model |
| CSV output format support | Phase 4.4, 8.x | Added CSVConfig and generate_csv() |
| `SECTOR` type in EntityType enum | Phase 1.2 | Added to EntityType enum |
| `exchange` field in EntityIdentifiers | Phase 1.2 | Added to EntityIdentifiers model |

### ARCHITECTURE.md Gaps (Now Fixed)
| Gap | Location Fixed | Notes |
|-----|----------------|-------|
| Database client tool for Data Agent | Phase 4.5 | Added db_client.py |
| Timeout constants documentation | Phase 4.6 | Added timeouts.py with all values |
| Scalability limit enforcement | Phase 3.2, 9.2 | Added validation methods |
| Round timeout (300s) | Phase 4.6 | Documented in AGENT_TIMEOUTS |
| Circuit breaker state machine | Phase 2.3 | Full implementation specified |

### PROMPTS.md Gaps (Now Addressed)
| Gap | Location Fixed | Notes |
|-----|----------------|-------|
| Exact Russian prompts | Phase 5.2 | Direct copy from specs/PROMPTS.md |
| Input/output JSON formats | All agent phases | Match exact formats from specs |
| 60s Initial Research timeout | Phase 5.3 | Documented constraint |
| 30s Data Agent timeout | Phase 6.2 | Documented constraint |
| 60s Research Agent timeout | Phase 6.3 | Documented constraint |

### Additional Types from DATA_SCHEMAS.md (Now Added to Phase 1.2)
The following enum types have been added to Phase 1.2:
- [x] `DataFreshness` - REAL_TIME, DAILY, WEEKLY, MONTHLY, QUARTERLY, ANNUAL
- [x] `RiskProfile` - CONSERVATIVE, MODERATE, AGGRESSIVE
- [x] `SourceTypeResult` - NEWS, REPORT, WEBSITE, FILING, ACADEMIC, OTHER (different from SourceType in tasks)
- [x] `PlannerDecisionStatus` - CONTINUE, DONE
- [x] `SECTOR` added to EntityType enum
- [x] `exchange` added to EntityIdentifiers

---

## Risk Areas and Implementation Challenges

### HIGH RISK - Architectural Decisions

1. **Ralph Pattern Context Clearing**
   - **Challenge**: Ensuring each agent truly starts with "fresh context" while maintaining necessary session state
   - **Mitigation**: Clear separation between session storage (persistent) and working context (transient)
   - **Testing**: Unit tests for context isolation between agent calls

2. **Parallel Execution with asyncio.gather()**
   - **Challenge**: Handling partial failures (some tasks succeed, some fail) in `return_exceptions=True` mode
   - **Mitigation**: Result type checking, structured error collection, partial result handling
   - **Testing**: Integration tests with simulated failures

3. **Coverage Calculation Accuracy**
   - **Challenge**: Planner must accurately assess "coverage_percent" for each scope item without objective metrics
   - **Mitigation**: Clear rubric in prompt, examples of coverage assessment, consistent format
   - **Testing**: Golden-file tests with known inputs/expected coverage

### MEDIUM RISK - External Dependencies

4. **LLM Rate Limits and Costs**
   - **Challenge**: Opus model is expensive; rate limits may throttle research
   - **Mitigation**: Retry with exponential backoff, circuit breaker, token tracking, cost alerts
   - **Testing**: Mock LLM client for unit tests, rate limit simulation

5. **Web Search Quality**
   - **Challenge**: Search results vary in quality; may return irrelevant content
   - **Mitigation**: Multiple search queries per task, source credibility scoring, fallback strategies
   - **Testing**: Cached search results for deterministic testing

6. **Report Generation Libraries**
   - **Challenge**: WeasyPrint requires system dependencies; python-pptx has template limitations
   - **Mitigation**: Docker with pre-installed dependencies, template customization, fallback to simpler formats
   - **Testing**: Output validation for all three formats

### LOWER RISK - Operational

7. **Session State Recovery**
   - **Challenge**: Recovering mid-session after crash or restart
   - **Mitigation**: State saved after every operation, resume_point detection, idempotent operations
   - **Testing**: Simulate crashes at various states

8. **Scalability Limits**
   - **Challenge**: Enforcing 10 concurrent sessions, 100 tasks/session without race conditions
   - **Mitigation**: Database-level constraints, atomic counter operations
   - **Testing**: Concurrent access tests

---

## Notes

- All agent prompts defined in specs/PROMPTS.md with exact input/output formats
- Data schemas defined in specs/DATA_SCHEMAS.md with JSON Schema and TypeScript types
- Architecture diagrams and flows in specs/ARCHITECTURE.md
- This is a greenfield project - no existing source code in src/
- Specifications are in Russian but implementation supports both Russian and English
- Use lowercase enum values for JSON compatibility (e.g., "pending" not "PENDING")
- Timeout values from specs: Initial Research 60s, Brief Builder 5s, Planner 10s, Data 30s, Research 60s, Round 300s

---

## Future Enhancements (Post-MVP)

Reference: specs/README.md mentions these as future features

### RAG for User Documents
- [ ] File upload endpoint for user documents (PDF, DOCX, TXT)
- [ ] Document parsing and chunking
- [ ] Vector embedding storage (consider pgvector or Pinecone)
- [ ] RAG integration in Research agent for user-provided context

### Advanced Analytics
- [ ] Token usage tracking and cost estimation per session
- [ ] Agent performance metrics dashboard
- [ ] Research quality scoring

### Multi-User Features
- [ ] User authentication and authorization
- [ ] Session sharing and collaboration
- [ ] Template briefs for common research types

### Enterprise Features
- [ ] Custom API integrations
- [ ] White-label report branding
- [ ] Audit logging
- [ ] SSO integration
