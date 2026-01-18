# RALPH Deep Research Agent
## Product Requirements Document

**Version:** 1.0  
**Date:** January 18, 2025  
**Status:** Draft

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Agent Specifications](#3-agent-specifications)
4. [Data Structures](#4-data-structures)
5. [User Flows](#5-user-flows)
6. [Technical Requirements](#6-technical-requirements)
7. [Project Structure](#7-project-structure)
8. [API Specification](#8-api-specification)
9. [Risks and Mitigations](#9-risks-and-mitigations)
10. [Success Metrics](#10-success-metrics)
11. [Roadmap](#11-roadmap)

---

## 1. Executive Summary

### 1.1 Product Vision

Ralph is an autonomous deep research agent that conducts comprehensive research on any given topic, synthesizes findings from multiple sources, and generates professional reports. Inspired by Geoffrey Huntley's Ralph pattern, the system uses a cyclic approach: plan → execute task → save result → repeat until complete.

### 1.2 Problem Statement

Current research workflows require significant manual effort:
- Searching multiple sources for information
- Extracting relevant data points
- Cross-referencing and validating information
- Synthesizing findings into coherent insights
- Formatting results into professional reports

This process is time-consuming (hours to days), prone to oversight, and difficult to scale.

### 1.3 Solution

Ralph automates the entire research pipeline through specialized AI agents working in parallel:

| Agent | Role |
|-------|------|
| **Brief Builder** | Clarifies user intent, creates approved research specification |
| **Planner** | Decomposes task, manages research cycles, filters questions |
| **Data** | Collects structured metrics and numerical data via APIs |
| **Research** | Analyzes unstructured information, generates insights |
| **Aggregator** | Synthesizes all findings into cohesive document |
| **Reporter** | Generates final outputs (PDF, Excel, PPTX, CSV) |

### 1.4 Target Users

- Individual investors conducting due diligence
- Business analysts performing market research
- Researchers gathering comprehensive information
- Anyone needing thorough, well-documented research

### 1.5 Key Differentiators

1. **Brief-driven approach** — User approves research specification before execution
2. **Data/Research separation** — Structured data vs. qualitative analysis handled by specialized agents
3. **Adaptive planning** — Planner cycles based on findings and emerging questions
4. **Parallel execution** — Data and Research agents work simultaneously

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RALPH DEEP RESEARCH                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐                                                            │
│  │ USER INPUT  │  "Расскажи про Realty Income, хочу инвестировать"         │
│  └──────┬──────┘                                                            │
│         │                                                                   │
│         ▼                                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    BRIEF BUILDER (Opus)                             │   │
│  │                                                                     │   │
│  │  • Уточняет задачу через диалог                                    │   │
│  │  • Формирует ТЗ                                                     │   │
│  │  • Цикл: ТЗ → User → Правки → ТЗ v2 → User → Approve               │   │
│  │                                                                     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                                 ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       PLANNER (Opus)                                │   │
│  │                                                                     │   │
│  │  • Читает Brief                                                     │   │
│  │  • Генерирует data_tasks + research_tasks                          │   │
│  │  • Фильтрует questions по релевантности к Brief                    │   │
│  │  • Проверяет coverage                                               │   │
│  │                                                                     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                    ┌────────────┴────────────┐                             │
│                    │                         │                             │
│                    ▼                         ▼                             │
│  ┌────────────────────────────┐ ┌────────────────────────────────────┐    │
│  │      DATA (Sonnet)         │ │        RESEARCH (Opus)             │    │
│  │                            │ │                                    │    │
│  │  • Метрики, цифры          │ │  • Новости, мнения                 │    │
│  │  • API calls               │ │  • Бизнес-модель                   │    │
│  │  • Структурированные       │ │  • Философия компании              │    │
│  │    данные                  │ │  • Качественный анализ             │    │
│  │                            │ │                                    │    │
│  │  Output:                   │ │  Output:                           │    │
│  │  • data_results[]          │ │  • research_results[]              │    │
│  │  • questions[]             │ │  • questions[]                     │    │
│  │                            │ │                                    │    │
│  └────────────┬───────────────┘ └──────────────────┬─────────────────┘    │
│               │      PARALLEL                      │                       │
│               └──────────────┬─────────────────────┘                       │
│                              │                                             │
│                              ▼                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       PLANNER (Opus)                                │   │
│  │                                                                     │   │
│  │  • Получает results + questions                                    │   │
│  │  • Проверяет coverage: "Brief покрыт?"                             │   │
│  │  • Если нет → новые tasks → ещё раунд                              │   │
│  │  • Если да → "done"                                                │   │
│  │                                                                     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                    ┌────────────┴────────────┐                             │
│                    │ status == "continue"    │                             │
│                    │         ↓               │                             │
│                    │    ┌────┴────┐          │                             │
│                    │    │  LOOP   │──────────┘                             │
│                    │    └─────────┘                                        │
│                    │                                                       │
│                    │ status == "done"                                      │
│                    ▼                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    AGGREGATOR (Opus)                                │   │
│  │                                                                     │   │
│  │  • Собирает все data_results + research_results                    │   │
│  │  • Создаёт таблицы, графики из Data                                │   │
│  │  • Интегрирует выводы из Research                                  │   │
│  │  • Проверяет consistency                                           │   │
│  │  • Пишет финальные выводы                                          │   │
│  │                                                                     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                                 ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     REPORTER (Opus)                                 │   │
│  │                                                                     │   │
│  │  • Получает aggregated_research + шаблоны                          │   │
│  │  • Генерирует: PDF, Excel, CSV, PPTX, DB records                   │   │
│  │                                                                     │   │
│  └──────────────────────────────┬──────────────────────────────────────┘   │
│                                 │                                          │
│                                 ▼                                          │
│  ┌─────────────┐                                                           │
│  │ USER OUTPUT │  Готовые отчёты                                          │
│  └─────────────┘                                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Model Configuration

| Agent | Model | Rationale |
|-------|-------|-----------|
| Brief Builder | Claude Opus | Requires strong reasoning for task clarification |
| Planner | Claude Opus | Critical decision-making and plan management |
| Data | Claude Sonnet | Simple API calls and data extraction (cost-efficient) |
| Research | Claude Opus | Complex analysis and synthesis of information |
| Aggregator | Claude Opus | Synthesizing all findings coherently |
| Reporter | Claude Opus | Quality formatting and document structure |

### 2.3 Technology Stack

**Backend:**
- Python 3.11+
- FastAPI (API server)
- Anthropic SDK (Claude API)
- asyncio (parallel execution)
- SQLite (session storage)

**Frontend:**
- React 18+
- TypeScript
- TailwindCSS
- React Query

**Report Generation:**
- WeasyPrint / ReportLab (PDF)
- openpyxl (Excel)
- python-pptx (PowerPoint)
- Jinja2 (templates)

### 2.4 Key Design Principles

1. **Ralph Pattern** — "Включил → сделал задачу → сохранил → выключил → следующая задача"
2. **Brief-Driven** — All work guided by user-approved specification
3. **Separation of Concerns** — Data (structured) vs Research (unstructured)
4. **Parallel Execution** — Data and Research agents run concurrently
5. **Adaptive Cycles** — Planner adds tasks based on emerging questions
6. **Clean Context** — Each task execution starts with fresh context

---

## 3. Agent Specifications

### 3.1 Brief Builder

**Purpose:** Transform vague user request into clear, approved research specification.

**Model:** Claude Opus

**Input:**
- User's initial query
- User's responses to clarifying questions

**Output:**
```json
{
  "brief_id": "abc123",
  "version": 2,
  "status": "approved",
  
  "goal": "Оценить Realty Income как долгосрочную инвестицию",
  
  "user_context": {
    "intent": "investment",
    "horizon": "5+ years",
    "portfolio_context": "увеличить долю real estate"
  },
  
  "scope": [
    {"id": 1, "topic": "Финансовое здоровье", "type": "data"},
    {"id": 2, "topic": "Бизнес-модель", "type": "research"},
    {"id": 3, "topic": "Менеджмент и философия", "type": "research"},
    {"id": 4, "topic": "Риски", "type": "both"},
    {"id": 5, "topic": "Сравнение с конкурентами", "type": "both"}
  ],
  
  "output_formats": ["pdf", "excel"]
}
```

**Behavior:**
1. Analyze user's initial query
2. Identify missing context (intent, scope, constraints)
3. Ask clarifying questions (one at a time)
4. Generate structured Brief
5. Present to user for approval
6. If user requests changes → update Brief → re-present
7. Loop until user approves

**Example Dialog:**
```
User: Расскажи про Realty Income, что о ней думаешь?

Brief Builder: Понял, вас интересует Realty Income. Подскажите, 
какая у вас цель? Инвестировать, устроиться на работу, 
изучить конкурента?

User: Хочу инвестировать, интересует сектор real estate, 
нужно увеличить его долю в портфеле

Brief Builder: Понял. Составил ТЗ на исследование:

───────────────────────────────────
ТЕХНИЧЕСКОЕ ЗАДАНИЕ v1

Цель: Оценить Realty Income (O) как инвестицию

Контекст:
• Цель: увеличить долю real estate в портфеле
• Горизонт: не указан
• Риск-профиль: не указан

Что исследуем:
1. Финансовое здоровье (дивиденды, долги, мультипликаторы)
2. Бизнес-модель и стратегия
3. Менеджмент и философия компании
4. Риски
5. Сравнение с альтернативами в секторе

Формат результата: PDF отчёт, Excel с данными
───────────────────────────────────

Всё верно? Что добавить/убрать?

User: Добавь анализ влияния процентных ставок. Горизонт 5+ лет.

Brief Builder: Обновил ТЗ. Подтверждаете?

User: Да, погнали

Brief Builder: ТЗ утверждено. Запускаю исследование.
```

---

### 3.2 Planner

**Purpose:** Decompose Brief into tasks, manage research cycles, ensure coverage.

**Model:** Claude Opus

**Input:**
- Approved Brief
- Results from previous rounds (if any)
- New questions from Data/Research agents

**Output (Initial Plan):**
```json
{
  "round": 1,
  "brief_id": "abc123",
  
  "data_tasks": [
    {"id": "d1", "description": "Дивиденды Realty Income", "source": "financial_api"},
    {"id": "d2", "description": "Долговая нагрузка", "source": "financial_api"},
    {"id": "d3", "description": "Мультипликаторы P/FFO, P/AFFO", "source": "financial_api"},
    {"id": "d4", "description": "Сравнение с NNN, WPC, STOR", "source": "financial_api"}
  ],
  
  "research_tasks": [
    {"id": "r1", "description": "Бизнес-модель и стратегия компании"},
    {"id": "r2", "description": "Новости за последний год"},
    {"id": "r3", "description": "Философия менеджмента, CEO"},
    {"id": "r4", "description": "Влияние процентных ставок на REIT"}
  ]
}
```

**Output (Review Decision):**
```json
{
  "round": 2,
  "status": "continue",
  
  "coverage": {
    "Финансовое здоровье": "90%",
    "Бизнес-модель": "70%",
    "Менеджмент и философия": "40%",
    "Риски": "30%",
    "Сравнение с конкурентами": "60%",
    "Влияние процентных ставок": "50%"
  },
  
  "reason": "Риски и менеджмент недостаточно покрыты. Появились новые вопросы про дата-центры.",
  
  "new_data_tasks": [
    {"id": "d5", "description": "Прогноз выручки от дата-центров"}
  ],
  
  "new_research_tasks": [
    {"id": "r5", "description": "Риски retail exposure в эпоху e-commerce"},
    {"id": "r6", "description": "Стратегия конвертации ТЦ в дата-центры"}
  ],
  
  "filtered_questions": [
    {"question": "История основателя", "relevance": "low", "action": "skip"}
  ]
}
```

**Behavior:**
1. **Initial Planning:**
   - Read Brief scope items
   - For each scope item, generate appropriate tasks
   - Classify as data_task or research_task based on type
   
2. **Review (after each round):**
   - Receive results from Data and Research
   - Collect questions generated by agents
   - Filter questions by relevance to Brief goal
   - Calculate coverage for each scope item
   - Decision: "continue" (add tasks) or "done"

3. **Coverage Calculation:**
   - Map results to Brief scope items
   - Estimate % coverage based on depth/breadth
   - Consider: "Does this answer the user's goal?"

---

### 3.3 Data Agent

**Purpose:** Collect structured, numerical data from APIs and databases.

**Model:** Claude Sonnet

**Input:**
- List of data_tasks from Planner
- API configurations
- Context (company name, tickers, etc.)

**Output:**
```json
{
  "task_id": "d1",
  "status": "done",
  "output": {
    "ticker": "O",
    "dividend_yield": 5.8,
    "dividend_growth_5y": 3.2,
    "payout_ratio": 75.2,
    "consecutive_increases": 107,
    "ex_dividend_date": "2025-01-31",
    "source": "financial_api",
    "timestamp": "2025-01-18T12:00:00Z"
  },
  "questions": []
}
```

**With Follow-up Questions:**
```json
{
  "task_id": "d2",
  "status": "done",
  "output": {
    "total_debt": 24500000000,
    "debt_to_equity": 0.85,
    "interest_coverage": 4.2,
    "debt_maturity_schedule": {
      "2025": 1200000000,
      "2026": 2300000000,
      "2027": 1800000000
    },
    "note": "Компания планирует рефинансирование в 2025"
  },
  "questions": [
    {"type": "research", "question": "Условия планируемого рефинансирования в 2025"}
  ]
}
```

**Behavior:**
1. Receive task from Planner
2. Determine appropriate API/source
3. Execute API call
4. Extract and structure relevant data
5. If discovers something requiring deeper analysis → add to questions
6. Save result
7. Move to next task

**Data Sources:**
- Custom user APIs (configured via settings)
- Financial data APIs (Yahoo Finance, Alpha Vantage, etc.)
- Web search for specific data points

---

### 3.4 Research Agent

**Purpose:** Analyze unstructured information, extract insights, form opinions.

**Model:** Claude Opus

**Input:**
- List of research_tasks from Planner
- Context (Brief, previous findings)

**Output:**
```json
{
  "task_id": "r1",
  "status": "done",
  "output": {
    "summary": "Realty Income — крупнейший triple-net lease REIT с фокусом на retail и industrial properties",
    "key_points": [
      "Бизнес-модель: долгосрочные контракты (10-20 лет) с арендаторами",
      "Арендаторы платят налоги, страховку, обслуживание (triple-net)",
      "Диверсификация: 15,450+ объектов в 50 штатах и Европе",
      "Основные арендаторы: Walgreens, Dollar General, 7-Eleven, FedEx"
    ],
    "analysis": "Модель triple-net обеспечивает предсказуемый cash flow с минимальными операционными расходами для владельца. Однако высокая концентрация в retail создаёт риски в эпоху e-commerce.",
    "sources": [
      {"type": "company_website", "url": "https://realtyincome.com/about"},
      {"type": "annual_report", "document": "10-K 2024"}
    ]
  },
  "questions": [
    {"type": "data", "question": "Breakdown выручки по типам арендаторов"},
    {"type": "research", "question": "Стратегия компании по снижению retail exposure"}
  ]
}
```

**Behavior:**
1. Receive task from Planner
2. Search web for relevant information
3. Read and analyze multiple sources
4. Extract key facts and insights
5. Form analytical conclusions
6. Identify gaps → generate questions
7. Save result with sources
8. Move to next task

**Research Capabilities:**
- Web search and content extraction
- Document analysis (annual reports, SEC filings)
- News analysis and sentiment
- Competitive analysis
- Trend identification

---

### 3.5 Aggregator

**Purpose:** Synthesize all findings into coherent, structured document.

**Model:** Claude Opus

**Input:**
- Approved Brief
- All data_results from Data agent
- All research_results from Research agent

**Output:**
```json
{
  "session_id": "abc123",
  "brief_id": "abc123",
  "created_at": "2025-01-18T15:30:00Z",
  
  "executive_summary": "Realty Income (O) представляет собой качественный REIT для долгосрочных инвесторов, ориентированных на стабильный дивидендный доход. Компания демонстрирует устойчивую финансовую позицию с умеренной долговой нагрузкой и впечатляющей историей 107 последовательных повышений дивидендов.",
  
  "sections": [
    {
      "title": "Финансовое здоровье",
      "brief_scope_id": 1,
      "data": {
        "dividend_yield": 5.8,
        "payout_ratio": 75.2,
        "debt_to_equity": 0.85,
        "interest_coverage": 4.2
      },
      "analysis": "Финансовые показатели указывают на здоровую компанию с консервативным подходом к леверджу. Payout ratio 75% оставляет запас для продолжения роста дивидендов.",
      "charts": ["dividend_history", "debt_comparison"]
    },
    {
      "title": "Бизнес-модель",
      "brief_scope_id": 2,
      "key_points": [
        "Triple-net lease модель",
        "Диверсифицированный портфель 15,000+ объектов",
        "Фокус на recession-resistant арендаторов"
      ],
      "analysis": "Бизнес-модель обеспечивает предсказуемый cash flow, однако высокая доля retail (73%) создаёт долгосрочные риски."
    },
    {
      "title": "Риски",
      "brief_scope_id": 4,
      "risks": [
        {
          "risk": "Retail exposure",
          "severity": "medium",
          "mitigation": "Компания активно диверсифицируется в industrial и data centers"
        },
        {
          "risk": "Interest rate sensitivity",
          "severity": "high",
          "mitigation": "87% долга с фиксированной ставкой, средний срок 6.3 года"
        }
      ]
    }
  ],
  
  "recommendation": {
    "verdict": "Подходит для цели",
    "confidence": "high",
    "reasoning": "Для долгосрочного инвестора (5+ лет) с целью увеличения доли real estate Realty Income представляет качественный выбор благодаря стабильности дивидендов, диверсификации и консервативному управлению.",
    "action_items": [
      "Рассмотреть стратегию DCA для снижения timing risk",
      "Мониторить динамику retail vs industrial в портфеле",
      "Следить за процентными ставками ФРС"
    ]
  }
}
```

**Behavior:**
1. Receive all results from Data and Research
2. Map results to Brief scope items
3. For each scope item:
   - Combine relevant data and research
   - Identify key metrics for tables/charts
   - Write analytical summary
4. Check for contradictions between sources
5. Generate executive summary
6. Formulate recommendation based on user's goal
7. Create actionable items

---

### 3.6 Reporter

**Purpose:** Generate final outputs in requested formats.

**Model:** Claude Opus

**Input:**
- Aggregated research document
- Requested output formats (from Brief)
- Templates (if provided)

**Output:**
- PDF report
- Excel workbook with data
- PowerPoint presentation
- CSV exports
- Database records

**Behavior:**
1. Receive aggregated document
2. For each requested format:
   - Load appropriate template
   - Map content to template structure
   - Generate file
3. Return file paths to user

**Format-Specific Logic:**

**PDF:**
- Executive summary on first page
- Table of contents
- Section per Brief scope item
- Charts and tables inline
- Sources/citations at end

**Excel:**
- Summary sheet with key metrics
- Sheet per data category
- Raw data for user's own analysis
- Charts where applicable

**PPTX:**
- Title slide
- Executive summary slide
- 1-2 slides per major finding
- Recommendation slide
- Appendix with detailed data

---

## 4. Data Structures

### 4.1 Session

```python
@dataclass
class Session:
    id: str
    user_id: str
    status: Literal["brief", "planning", "executing", "aggregating", "reporting", "done", "failed"]
    brief: Optional[Brief]
    current_round: int
    created_at: datetime
    updated_at: datetime
```

### 4.2 Brief

```python
@dataclass
class Brief:
    brief_id: str
    version: int
    status: Literal["draft", "approved"]
    goal: str
    user_context: dict
    scope: List[ScopeItem]
    output_formats: List[str]
    constraints: Optional[dict]
```

### 4.3 ScopeItem

```python
@dataclass
class ScopeItem:
    id: int
    topic: str
    type: Literal["data", "research", "both"]
    details: Optional[str]
```

### 4.4 Task

```python
@dataclass
class Task:
    id: str
    session_id: str
    round: int
    type: Literal["data", "research"]
    description: str
    source: Optional[str]
    status: Literal["pending", "running", "done", "failed"]
    result: Optional[dict]
    questions: List[Question]
    created_at: datetime
    completed_at: Optional[datetime]
```

### 4.5 Question

```python
@dataclass
class Question:
    type: Literal["data", "research"]
    question: str
    source_task_id: str
    relevance: Optional[str]
    action: Optional[Literal["add", "skip"]]
```

### 4.6 Plan

```python
@dataclass
class Plan:
    round: int
    status: Literal["continue", "done"]
    coverage: Dict[str, str]
    reason: Optional[str]
    data_tasks: List[Task]
    research_tasks: List[Task]
    filtered_questions: List[Question]
```

### 4.7 AggregatedResearch

```python
@dataclass
class AggregatedResearch:
    session_id: str
    brief_id: str
    created_at: datetime
    executive_summary: str
    sections: List[Section]
    recommendation: Recommendation
```

---

## 5. User Flows

### 5.1 Happy Path

```
1. User enters query: "Исследуй Realty Income для инвестиций"
2. Brief Builder asks clarifying questions
3. User provides context (horizon, goals)
4. Brief Builder presents ТЗ
5. User approves ТЗ
6. System shows: "Исследование запущено..."
7. [Background: Planner → Data || Research → Planner cycles]
8. System shows progress updates
9. Research completes
10. User receives PDF + Excel reports
11. User can ask follow-up questions or start new research
```

### 5.2 Brief Revision Flow

```
1. Brief Builder presents ТЗ v1
2. User: "Добавь анализ конкурентов, убери историю компании"
3. Brief Builder updates ТЗ → presents v2
4. User: "Окей, но ещё добавь влияние ставок"
5. Brief Builder updates → presents v3
6. User: "Подтверждаю"
7. Research starts with v3
```

### 5.3 Multi-Round Research Flow

```
Round 1:
  - Planner creates initial tasks
  - Data: fetches financial metrics
  - Research: analyzes business model
  - Research finds: "Company entering data center market"
  - Question generated: "Data center revenue projections?"

Round 2:
  - Planner reviews Round 1
  - Coverage: 65%
  - Planner adds tasks based on new question
  - Data: fetches data center projections
  - Research: analyzes data center strategy

Round 3:
  - Planner reviews Round 2
  - Coverage: 95%
  - Planner: "done"
  - → Aggregator
```

---

## 6. Technical Requirements

### 6.1 Performance

| Metric | Target |
|--------|--------|
| Brief Builder response | < 5 seconds |
| Planner decision | < 10 seconds |
| Single Data task | < 30 seconds |
| Single Research task | < 60 seconds |
| Full research (3 rounds) | < 15 minutes |
| Report generation | < 60 seconds |

### 6.2 Reliability

| Metric | Target |
|--------|--------|
| Task success rate | > 95% |
| Retry limit per task | 3 |
| Session recovery | Full state persistence |
| API timeout handling | Graceful fallback |

### 6.3 Scalability

| Metric | Target (MVP) |
|--------|--------------|
| Concurrent sessions | 10 |
| Tasks per session | 100 |
| Max rounds | 10 |
| Storage per session | 50 MB |

### 6.4 Security

- API keys stored in environment variables
- No PII in logs
- Session data encrypted at rest
- Rate limiting on API endpoints

---

## 7. Project Structure

```
ralph/
├── api/
│   ├── __init__.py
│   ├── routes.py              # FastAPI endpoints
│   ├── schemas.py             # Pydantic request/response models
│   └── dependencies.py        # Auth, rate limiting
│
├── agents/
│   ├── __init__.py
│   ├── base.py                # BaseAgent class
│   ├── brief_builder.py       # Brief Builder agent
│   ├── planner.py             # Planner agent
│   ├── data.py                # Data agent
│   ├── research.py            # Research agent
│   ├── aggregator.py          # Aggregator agent
│   └── reporter.py            # Reporter agent
│
├── orchestrator/
│   ├── __init__.py
│   ├── pipeline.py            # Main research pipeline
│   └── parallel.py            # Parallel execution utilities
│
├── tools/
│   ├── __init__.py
│   ├── llm.py                 # Claude API wrapper
│   ├── web_search.py          # Web search integration
│   ├── api_client.py          # Custom API client
│   └── file_generator.py      # PDF, Excel, PPTX generation
│
├── storage/
│   ├── __init__.py
│   ├── database.py            # SQLite operations
│   ├── session.py             # Session management
│   └── files.py               # File storage
│
├── prompts/
│   ├── brief_builder.md       # Brief Builder system prompt
│   ├── planner.md             # Planner system prompt
│   ├── data.md                # Data agent system prompt
│   ├── research.md            # Research agent system prompt
│   ├── aggregator.md          # Aggregator system prompt
│   └── reporter.md            # Reporter system prompt
│
├── templates/
│   ├── pdf/
│   │   └── report.html        # PDF template (WeasyPrint)
│   ├── excel/
│   │   └── report.xlsx        # Excel template
│   └── pptx/
│       └── report.pptx        # PowerPoint template
│
├── config/
│   ├── __init__.py
│   ├── settings.py            # App configuration
│   └── models.py              # Model selection config
│
├── tests/
│   ├── __init__.py
│   ├── test_agents/
│   ├── test_orchestrator/
│   └── test_api/
│
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/
│   │   │   ├── Chat.tsx
│   │   │   ├── BriefDisplay.tsx
│   │   │   ├── ProgressTracker.tsx
│   │   │   └── ReportViewer.tsx
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   └── Research.tsx
│   │   ├── hooks/
│   │   │   └── useResearch.ts
│   │   ├── api/
│   │   │   └── client.ts
│   │   └── App.tsx
│   ├── package.json
│   └── tailwind.config.js
│
├── main.py                     # Application entry point
├── requirements.txt
├── docker-compose.yml
└── README.md
```

---

## 8. API Specification

### 8.1 Endpoints

#### Start Research Session

```
POST /api/sessions
```

**Request:**
```json
{
  "user_id": "user_123",
  "initial_query": "Исследуй Realty Income для инвестиций"
}
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "status": "brief",
  "message": "Какая у вас цель? Инвестировать, изучить конкурента, устроиться на работу?"
}
```

#### Send Message (Brief Building)

```
POST /api/sessions/{session_id}/messages
```

**Request:**
```json
{
  "content": "Хочу инвестировать на 5+ лет"
}
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "status": "brief",
  "brief": {
    "version": 1,
    "goal": "...",
    "scope": [...]
  },
  "message": "Вот ТЗ на исследование. Подтверждаете?"
}
```

#### Approve Brief

```
POST /api/sessions/{session_id}/approve
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "status": "executing",
  "message": "Исследование запущено. Ожидаемое время: 10-15 минут."
}
```

#### Get Session Status

```
GET /api/sessions/{session_id}
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "status": "executing",
  "current_round": 2,
  "progress": {
    "data_tasks_completed": 5,
    "data_tasks_total": 6,
    "research_tasks_completed": 3,
    "research_tasks_total": 4
  },
  "coverage": {
    "Финансовое здоровье": "90%",
    "Бизнес-модель": "70%"
  }
}
```

#### Get Results

```
GET /api/sessions/{session_id}/results
```

**Response:**
```json
{
  "session_id": "sess_abc123",
  "status": "done",
  "aggregated": { ... },
  "reports": [
    {"format": "pdf", "url": "/files/sess_abc123/report.pdf"},
    {"format": "excel", "url": "/files/sess_abc123/data.xlsx"}
  ]
}
```

---

## 9. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **LLM hallucinations** | Medium | High | Cross-reference multiple sources, require citations |
| **API rate limits** | Medium | Medium | Implement backoff, queue tasks |
| **Infinite planning loops** | Low | High | Max rounds limit, coverage thresholds |
| **Poor Brief understanding** | Medium | High | Iterative clarification, user approval |
| **Inconsistent data** | Medium | Medium | Aggregator validation step |
| **Report quality issues** | Low | Medium | Templates, Opus for Reporter |
| **Long execution times** | Medium | Medium | Parallel execution, progress updates |
| **Cost overruns** | Medium | Low | Sonnet for Data, token budgets |

---

## 10. Success Metrics

### 10.1 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Brief accuracy | 90% | User approves Brief without changes |
| Research completeness | 85% | Coverage > 80% for all scope items |
| Factual accuracy | 95% | Spot-check sample of claims |
| User satisfaction | 4.5/5 | Post-research survey |

### 10.2 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Average research time | < 15 min | From Brief approval to reports |
| Task success rate | > 95% | Completed / Total tasks |
| Retry rate | < 10% | Tasks requiring retry |

### 10.3 Business Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Researches per week | 20+ | After launch stabilization |
| Completion rate | > 90% | Completed / Started sessions |
| Return usage | > 50% | Users who run 2+ researches |

---

## 11. Roadmap

### Phase 1: MVP (Weeks 1-4)

**Week 1-2: Foundation**
- [ ] Project setup, dependencies
- [ ] Base agent class
- [ ] LLM wrapper with model selection
- [ ] Session storage (SQLite)

**Week 3: Core Agents**
- [ ] Brief Builder agent
- [ ] Planner agent
- [ ] Data agent (basic)
- [ ] Research agent (basic)

**Week 4: Pipeline & Integration**
- [ ] Orchestrator pipeline
- [ ] Parallel execution
- [ ] Aggregator agent
- [ ] Reporter agent (PDF only)
- [ ] Basic API endpoints

### Phase 2: Full Features (Weeks 5-8)

**Week 5-6: Enhanced Agents**
- [ ] Custom API integration for Data agent
- [ ] Web search for Research agent
- [ ] Improved prompts based on testing

**Week 7: Report Generation**
- [ ] Excel report generation
- [ ] PPTX report generation
- [ ] Template system

**Week 8: Frontend**
- [ ] React app setup
- [ ] Chat interface
- [ ] Progress tracking
- [ ] Report viewer

### Phase 3: Polish (Weeks 9-10)

**Week 9:**
- [ ] Error handling improvements
- [ ] Retry logic
- [ ] Logging and monitoring

**Week 10:**
- [ ] Testing and bug fixes
- [ ] Documentation
- [ ] Deployment setup

### Future Enhancements (Backlog)

- [ ] Memory/Knowledge base across sessions
- [ ] DAG-based task planning
- [ ] Real-time progress streaming (WebSocket)
- [ ] Custom report templates
- [ ] Multi-language support
- [ ] Voice input/output
- [ ] Mobile app

---

## Appendix A: Example Prompts

### Brief Builder System Prompt

```markdown
You are a research brief builder. Your job is to understand what the user wants to research and create a clear, structured brief.

## Your Process:
1. Analyze the user's initial query
2. Identify missing context:
   - What is the user's goal? (invest, learn, compare, etc.)
   - What specific aspects interest them?
   - What is their time horizon or constraints?
   - What output format do they need?
3. Ask ONE clarifying question at a time
4. When you have enough information, create a Brief

## Brief Format:
- Goal: Clear statement of research objective
- Context: User's situation and constraints
- Scope: List of topics to cover (mark as data/research/both)
- Output: Requested formats

## Rules:
- Be concise and professional
- Ask only necessary questions
- Present Brief for user approval
- Accept user modifications gracefully
```

### Planner System Prompt

```markdown
You are a research planner. Your job is to decompose a research brief into concrete tasks and manage research cycles.

## Input:
- Approved Brief with goal, scope, and constraints
- Results from previous rounds (if any)
- New questions from agents

## Your Process:

### Initial Planning:
1. Read Brief scope items
2. For each scope item, create appropriate tasks:
   - "data" type → data_task (metrics, numbers, API calls)
   - "research" type → research_task (analysis, opinions, news)
   - "both" type → both task types
3. Output task list with clear descriptions

### Review (after each round):
1. Map results to Brief scope items
2. Calculate coverage % for each scope item
3. Review questions from agents:
   - Filter by relevance to Brief goal
   - Add relevant questions as new tasks
   - Skip low-relevance questions
4. Decide: "continue" or "done"
   - Continue if coverage < 80% on any scope item
   - Continue if critical questions remain
   - Done if Brief is sufficiently covered

## Rules:
- Always reference Brief goal in decisions
- Keep tasks focused and specific
- Limit to 10 tasks per round
- Maximum 10 rounds total
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **Brief** | User-approved specification for research |
| **Coverage** | Percentage of Brief scope addressed by results |
| **Data task** | Task for collecting structured/numerical information |
| **Research task** | Task for analyzing unstructured information |
| **Round** | One cycle of Planner → Data/Research → Planner review |
| **Ralph pattern** | Execute task → save → clear context → next task |
| **Scope item** | Individual topic within Brief to be researched |
| **Session** | Complete research process from input to output |

---

*End of Document*
