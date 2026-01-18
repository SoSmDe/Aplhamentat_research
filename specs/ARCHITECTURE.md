# ARCHITECTURE.md

Техническое описание архитектуры Ralph Deep Research.

---

## Содержание

1. [Component Diagram](#1-component-diagram)
2. [Sequence Diagram](#2-sequence-diagram)
3. [Data Flow](#3-data-flow)
4. [State Management](#4-state-management)
5. [Parallel Execution](#5-parallel-execution)
6. [Error Handling](#6-error-handling)
7. [Retry Logic](#7-retry-logic)

---

## 1. Component Diagram

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   RALPH SYSTEM                                       │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                            API LAYER (FastAPI)                               │   │
│  │                                                                               │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐    │   │
│  │  │   routes    │ │   schemas   │ │dependencies │ │    middleware       │    │   │
│  │  │  .py        │ │   .py       │ │    .py      │ │  (auth, rate limit) │    │   │
│  │  └──────┬──────┘ └─────────────┘ └─────────────┘ └─────────────────────┘    │   │
│  │         │                                                                     │   │
│  └─────────┼─────────────────────────────────────────────────────────────────────┘   │
│            │                                                                          │
│            ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐    │
│  │                        ORCHESTRATOR LAYER                                    │    │
│  │                                                                               │    │
│  │  ┌─────────────────────────────┐  ┌─────────────────────────────────────┐   │    │
│  │  │       pipeline.py           │  │          parallel.py                │   │    │
│  │  │                             │  │                                     │   │    │
│  │  │  • Main research pipeline   │  │  • asyncio.gather() wrapper        │   │    │
│  │  │  • Agent coordination       │  │  • Concurrent task execution       │   │    │
│  │  │  • State transitions        │  │  • Result aggregation              │   │    │
│  │  │  • Loop control             │  │  • Timeout handling                │   │    │
│  │  │                             │  │                                     │   │    │
│  │  └─────────────┬───────────────┘  └──────────────────────────────────────┘   │    │
│  │                │                                                              │    │
│  └────────────────┼──────────────────────────────────────────────────────────────┘    │
│                   │                                                                    │
│                   ▼                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────┐     │
│  │                           AGENT LAYER                                        │     │
│  │                                                                               │     │
│  │  ┌───────────────┐  ┌───────────────────────────────────────────────────┐   │     │
│  │  │   base.py     │  │              Specialized Agents                   │   │     │
│  │  │               │  │                                                   │   │     │
│  │  │  BaseAgent    │  │  ┌─────────────┐ ┌─────────────┐ ┌───────────┐   │   │     │
│  │  │  • execute()  │◄─┼──│   Initial   │ │    Brief    │ │  Planner  │   │   │     │
│  │  │  • validate() │  │  │  Research   │ │   Builder   │ │           │   │   │     │
│  │  │  • save()     │  │  └─────────────┘ └─────────────┘ └───────────┘   │   │     │
│  │  │               │  │                                                   │   │     │
│  │  └───────────────┘  │  ┌─────────────┐ ┌─────────────┐                 │   │     │
│  │                     │  │    Data     │ │  Research   │   ← Parallel    │   │     │
│  │                     │  │   Agent     │ │   Agent     │                 │   │     │
│  │                     │  └─────────────┘ └─────────────┘                 │   │     │
│  │                     │                                                   │   │     │
│  │                     │  ┌─────────────┐ ┌─────────────┐                 │   │     │
│  │                     │  │ Aggregator  │ │  Reporter   │                 │   │     │
│  │                     │  │             │ │             │                 │   │     │
│  │                     │  └─────────────┘ └─────────────┘                 │   │     │
│  │                     └───────────────────────────────────────────────────┘   │     │
│  │                                                                               │     │
│  └───────────────────────────────────────────────────────────────────────────────┘     │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐      │
│  │                            TOOLS LAYER                                       │      │
│  │                                                                               │      │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐    │      │
│  │  │   llm.py    │ │ web_search  │ │ api_client  │ │  file_generator     │    │      │
│  │  │             │ │    .py      │ │    .py      │ │       .py           │    │      │
│  │  │ Claude API  │ │ Web search  │ │ Custom APIs │ │ PDF/Excel/PPTX      │    │      │
│  │  │ wrapper     │ │ integration │ │ client      │ │ generation          │    │      │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────────┘    │      │
│  │                                                                               │      │
│  └───────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐      │
│  │                          STORAGE LAYER                                       │      │
│  │                                                                               │      │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────────────────┐    │      │
│  │  │ database.py │ │ session.py  │ │            files.py                 │    │      │
│  │  │             │ │             │ │                                     │    │      │
│  │  │ SQLite ops  │ │ Session     │ │ File storage for reports,          │    │      │
│  │  │             │ │ state mgmt  │ │ intermediate results               │    │      │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────────────────┘    │      │
│  │                                                                               │      │
│  └───────────────────────────────────────────────────────────────────────────────┘      │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘

                                    EXTERNAL SERVICES
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────┐   │
│  │   Anthropic     │  │   Financial     │  │   Web Search    │  │    Custom        │   │
│  │   Claude API    │  │   Data APIs     │  │   APIs          │  │    User APIs     │   │
│  │                 │  │                 │  │                 │  │                  │   │
│  │  • Opus         │  │  • Yahoo        │  │  • Serper       │  │  • Configured    │   │
│  │  • Sonnet       │  │  • Alpha        │  │  • Bing         │  │    per user      │   │
│  │                 │  │    Vantage      │  │  • Google       │  │                  │   │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  └──────────────────┘   │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

### Module Dependencies

```
                                    main.py
                                       │
                                       ▼
                              ┌────────────────┐
                              │   api/routes   │
                              └────────┬───────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │  api/schemas  │  │ orchestrator/ │  │   storage/    │
           │               │  │  pipeline     │  │   session     │
           └───────────────┘  └───────┬───────┘  └───────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
           ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
           │   agents/*    │  │ orchestrator/ │  │   storage/    │
           │               │  │   parallel    │  │   database    │
           └───────┬───────┘  └───────────────┘  └───────────────┘
                   │
          ┌────────┼────────┐
          │        │        │
          ▼        ▼        ▼
   ┌──────────┐ ┌──────┐ ┌──────────┐
   │tools/llm │ │tools/│ │ tools/   │
   │          │ │web_  │ │api_client│
   └──────────┘ │search│ └──────────┘
                └──────┘
```

---

## 2. Sequence Diagram

### Full Research Flow

```
┌──────┐     ┌───────┐    ┌────────┐   ┌───────┐   ┌───────┐   ┌────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐
│Client│     │  API  │    │Pipeline│   │Initial│   │Brief  │   │Planner │  │Data Agent│  │Research  │  │Storage │
└──┬───┘     └───┬───┘    └───┬────┘   │Research│  │Builder│   └───┬────┘  └────┬─────┘  │  Agent   │  └───┬────┘
   │             │            │        └───┬────┘  └───┬───┘       │           │        └────┬─────┘      │
   │  POST /sessions          │            │           │           │           │             │            │
   │ {query: "..."}           │            │           │           │           │             │            │
   │────────────────────────►│            │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │  start_session()       │           │           │           │             │            │
   │             │───────────────────────►│           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ execute(query)        │           │           │             │            │
   │             │            │──────────►│           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ initial_context       │           │           │             │            │
   │             │            │◄──────────│           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ save(initial_context) │           │           │             │            │
   │             │            │─────────────────────────────────────────────────────────────────────────►│
   │             │            │           │           │           │           │             │            │
   │             │            │ execute(context)      │           │           │             │            │
   │             │            │──────────────────────►│           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │ {status: "brief",        │           │           │           │           │             │            │
   │  message: "..."}         │           │  question │           │           │             │            │
   │◄────────────────────────────────────────────────│           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │  POST /sessions/{id}/messages        │           │           │           │             │            │
   │  {content: "..."}        │           │           │           │           │             │            │
   │─────────────────────────►│           │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │  process_message()     │           │           │           │             │            │
   │             │───────────────────────────────────►│           │           │             │            │
   │             │            │           │  ◄───────►│           │           │             │            │
   │             │            │           │   dialog  │           │           │             │            │
   │             │            │           │   loop    │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ brief     │           │           │           │             │            │
   │ {brief: {...}}           │ (draft)   │           │           │           │             │            │
   │◄────────────────────────────────────────────────│           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │  POST /sessions/{id}/approve         │           │           │           │             │            │
   │─────────────────────────►│           │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │  approve_brief()       │           │           │           │             │            │
   │             │───────────────────────►│           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ save(brief_approved)  │           │           │             │            │
   │             │            │─────────────────────────────────────────────────────────────────────────►│
   │             │            │           │           │           │           │             │            │
   │             │            │ plan(brief)           │           │           │             │            │
   │             │            │──────────────────────────────────►│           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ plan {data_tasks, research_tasks} │           │             │            │
   │             │            │◄──────────────────────────────────│           │             │            │
   │             │            │           │           │           │           │             │            │
   │ {status: "executing"}    │           │           │           │           │             │            │
   │◄─────────────────────────│           │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │═══════════════════════════════════════════════╗             │            │
   │             │            │           PARALLEL EXECUTION                  ║             │            │
   │             │            │═══════════════════════════════════════════════╣             │            │
   │             │            │           │           │           │           ║             │            │
   │             │            │ execute(data_tasks)   │           │           ▼             │            │
   │             │            │───────────────────────────────────────────────┼────────────►│            │
   │             │            │           │           │           │           │             │            │
   │             │            │ execute(research_tasks)           │           │             │            │
   │             │            │────────────────────────────────────────────────────────────►│            │
   │             │            │           │           │           │           │             │            │
   │             │            │ data_results          │           │           │             │            │
   │             │            │◄──────────────────────────────────────────────┼─────────────│            │
   │             │            │           │           │           │           │             │            │
   │             │            │ research_results      │           │           │             │            │
   │             │            │◄───────────────────────────────────────────────────────────│            │
   │             │            │           │           │           │           │             │            │
   │             │            │═══════════════════════════════════════════════╝             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ save(results)         │           │           │             │            │
   │             │            │─────────────────────────────────────────────────────────────────────────►│
   │             │            │           │           │           │           │             │            │
   │             │            │ review(results)       │           │           │             │            │
   │             │            │──────────────────────────────────►│           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ decision {status: "continue"|"done"}          │             │            │
   │             │            │◄──────────────────────────────────│           │             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ ┌─────────────────────────────────────────────┐             │            │
   │             │            │ │ if status == "continue":                    │             │            │
   │             │            │ │   → новый раунд с new_tasks                 │             │            │
   │             │            │ │ if status == "done":                        │             │            │
   │             │            │ │   → переход к aggregation                   │             │            │
   │             │            │ └─────────────────────────────────────────────┘             │            │
   │             │            │           │           │           │           │             │            │
   │             │            │═══════════════════════════════════════════════════════════════════════════
   │             │            │           AGGREGATION PHASE                                 │            │
   │             │            │═══════════════════════════════════════════════════════════════════════════
   │             │            │           │           │           │           │             │            │
   │             │            │                    ┌──────────┐                             │            │
   │             │            │ aggregate(all)     │Aggregator│                             │            │
   │             │            │───────────────────►│          │                             │            │
   │             │            │                    └────┬─────┘                             │            │
   │             │            │                         │                                   │            │
   │             │            │ aggregated_research     │                                   │            │
   │             │            │◄────────────────────────│                                   │            │
   │             │            │           │           │           │           │             │            │
   │             │            │═══════════════════════════════════════════════════════════════════════════
   │             │            │           REPORTING PHASE                                   │            │
   │             │            │═══════════════════════════════════════════════════════════════════════════
   │             │            │           │           │           │           │             │            │
   │             │            │                              ┌────────┐                     │            │
   │             │            │ generate(aggregated)         │Reporter│                     │            │
   │             │            │─────────────────────────────►│        │                     │            │
   │             │            │                              └───┬────┘                     │            │
   │             │            │                                  │                          │            │
   │             │            │ reports[pdf, excel, pptx]        │                          │            │
   │             │            │◄─────────────────────────────────│                          │            │
   │             │            │           │           │           │           │             │            │
   │             │            │ save(reports)         │           │           │             │            │
   │             │            │─────────────────────────────────────────────────────────────────────────►│
   │             │            │           │           │           │           │             │            │
   │             │            │ update_session(done)  │           │           │             │            │
   │             │            │─────────────────────────────────────────────────────────────────────────►│
   │             │            │           │           │           │           │             │            │
   │  GET /sessions/{id}/results          │           │           │           │             │            │
   │─────────────────────────►│           │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
   │ {status: "done",         │           │           │           │           │             │            │
   │  reports: [...]}         │           │           │           │           │             │            │
   │◄─────────────────────────│           │           │           │           │             │            │
   │             │            │           │           │           │           │             │            │
```

### Brief Building Sub-Flow

```
┌──────┐                    ┌──────────────┐                    ┌────────┐
│Client│                    │Brief Builder │                    │Storage │
└──┬───┘                    └──────┬───────┘                    └───┬────┘
   │                               │                                │
   │  initial_query                │                                │
   │──────────────────────────────►│                                │
   │                               │                                │
   │                               │  load(initial_context)         │
   │                               │───────────────────────────────►│
   │                               │◄───────────────────────────────│
   │                               │                                │
   │  question_1                   │                                │
   │◄──────────────────────────────│                                │
   │                               │                                │
   │  answer_1                     │                                │
   │──────────────────────────────►│                                │
   │                               │                                │
   │  question_2 (if needed)       │                                │
   │◄──────────────────────────────│                                │
   │                               │                                │
   │  answer_2                     │                                │
   │──────────────────────────────►│                                │
   │                               │                                │
   │  brief_v1 (draft)             │                                │
   │◄──────────────────────────────│                                │
   │                               │                                │
   │  "добавь X, убери Y"          │                                │
   │──────────────────────────────►│                                │
   │                               │                                │
   │  brief_v2 (draft)             │                                │
   │◄──────────────────────────────│                                │
   │                               │                                │
   │  "подтверждаю"                │                                │
   │──────────────────────────────►│                                │
   │                               │                                │
   │                               │  save(brief_v2, approved)      │
   │                               │───────────────────────────────►│
   │                               │                                │
   │  brief_v2 (approved)          │                                │
   │◄──────────────────────────────│                                │
   │                               │                                │
```

---

## 3. Data Flow

### Agent Data Flow Diagram

```
                                    USER INPUT
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │   Initial Research    │
                            │                       │
                            │  Input:               │
                            │  • raw user query     │
                            │                       │
                            │  Output:              │
                            │  • initial_context    │
                            │  • entities[]         │
                            │  • suggested_topics   │
                            └───────────┬───────────┘
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │    Brief Builder      │
                            │                       │
                            │  Input:               │
                            │  • initial_context    │
                            │  • user messages      │
                            │                       │
                            │  Output:              │
                            │  • approved_brief     │
                            │    - goal             │
                            │    - scope[]          │
                            │    - output_formats   │
                            └───────────┬───────────┘
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │       Planner         │
                            │    (Initial Plan)     │
                            │                       │
                            │  Input:               │
                            │  • approved_brief     │
                            │                       │
                            │  Output:              │
                            │  • plan               │
                            │    - data_tasks[]     │
                            │    - research_tasks[] │
                            └───────────┬───────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │                                       │
                    ▼                                       ▼
        ┌───────────────────────┐           ┌───────────────────────┐
        │      Data Agent       │           │    Research Agent     │
        │                       │           │                       │
        │  Input:               │           │  Input:               │
        │  • data_tasks[]       │           │  • research_tasks[]   │
        │  • entity_context     │           │  • brief_context      │
        │                       │           │                       │
        │  Output:              │           │  Output:              │
        │  • data_results[]     │           │  • research_results[] │
        │    - metrics          │           │    - findings         │
        │    - tables           │           │    - analysis         │
        │  • questions[]        │           │  • questions[]        │
        └───────────┬───────────┘           └───────────┬───────────┘
                    │                                   │
                    │       ┌─────── PARALLEL ─────────┐│
                    │       │                          ││
                    └───────┼──────────────────────────┘│
                            │                           │
                            ▼                           │
                ┌───────────────────────┐               │
                │       Planner         │◄──────────────┘
                │      (Review)         │
                │                       │
                │  Input:               │
                │  • brief              │
                │  • data_results[]     │
                │  • research_results[] │
                │  • questions[]        │
                │                       │
                │  Output:              │
                │  • decision           │
                │    - status           │
                │    - coverage{}       │
                │    - new_tasks[]      │
                └───────────┬───────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
        status == "continue"    status == "done"
                │                       │
                ▼                       ▼
        ┌───────────────┐   ┌───────────────────────┐
        │  Next Round   │   │      Aggregator       │
        │  (loop back)  │   │                       │
        └───────────────┘   │  Input:               │
                            │  • brief              │
                            │  • all data_results   │
                            │  • all research_results│
                            │                       │
                            │  Output:              │
                            │  • aggregated_research│
                            │    - exec_summary     │
                            │    - sections[]       │
                            │    - recommendation   │
                            └───────────┬───────────┘
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │       Reporter        │
                            │                       │
                            │  Input:               │
                            │  • aggregated_research│
                            │  • output_formats     │
                            │  • templates          │
                            │                       │
                            │  Output:              │
                            │  • report_files[]     │
                            │    - pdf              │
                            │    - excel            │
                            │    - pptx             │
                            └───────────┬───────────┘
                                        │
                                        ▼
                                  USER OUTPUT
```

### Data Transformation Table

| From Agent | Output | To Agent | Input Mapping |
|------------|--------|----------|---------------|
| Initial Research | `initial_context` | Brief Builder | `initial_context` |
| Brief Builder | `approved_brief` | Planner | `brief` |
| Planner (Initial) | `plan` | Data Agent | `data_tasks[]` |
| Planner (Initial) | `plan` | Research Agent | `research_tasks[]` |
| Data Agent | `data_results[]` | Planner (Review) | `data_results[]` |
| Data Agent | `questions[]` | Planner (Review) | `new_questions[]` |
| Research Agent | `research_results[]` | Planner (Review) | `research_results[]` |
| Research Agent | `questions[]` | Planner (Review) | `new_questions[]` |
| Planner (Review) | `new_data_tasks[]` | Data Agent (next round) | `data_tasks[]` |
| Planner (Review) | `new_research_tasks[]` | Research Agent (next round) | `research_tasks[]` |
| All Agents | All results | Aggregator | `data_results[]`, `research_results[]` |
| Aggregator | `aggregated_research` | Reporter | `aggregated_research` |

---

## 4. State Management

### Session State Machine

```
                              ┌─────────────┐
                              │   CREATED   │
                              └──────┬──────┘
                                     │
                            create_session()
                                     │
                                     ▼
                         ┌───────────────────────┐
                         │   INITIAL_RESEARCH    │
                         └───────────┬───────────┘
                                     │
                        initial_research_complete()
                                     │
                                     ▼
                            ┌───────────────┐
                            │     BRIEF     │◄──────────┐
                            └───────┬───────┘           │
                                    │                   │
                              ┌─────┴─────┐             │
                              │           │             │
                    message_received()  revision_requested()
                              │           │             │
                              ▼           └─────────────┘
                         ┌─────────┐
                         │APPROVED │
                         └────┬────┘
                              │
                       approve_brief()
                              │
                              ▼
                       ┌────────────┐
                       │  PLANNING  │
                       └─────┬──────┘
                             │
                      plan_created()
                             │
                             ▼
                      ┌────────────┐
            ┌────────►│ EXECUTING  │◄────────┐
            │         └─────┬──────┘         │
            │               │                │
     round_continue()  round_complete()      │
            │               │                │
            │               ▼                │
            │        ┌────────────┐          │
            │        │  REVIEW    │──────────┘
            │        └─────┬──────┘
            │              │
            └──────────────┤
                           │
                   coverage_complete()
                           │
                           ▼
                    ┌─────────────┐
                    │ AGGREGATING │
                    └──────┬──────┘
                           │
                   aggregation_complete()
                           │
                           ▼
                    ┌─────────────┐
                    │  REPORTING  │
                    └──────┬──────┘
                           │
                    reports_generated()
                           │
                           ▼
                       ┌────────┐
                       │  DONE  │
                       └────────┘


        ─────── ERROR TRANSITIONS ───────

        Any state ──error()──► FAILED

                       ┌────────┐
                       │ FAILED │
                       └────────┘
```

### Session Storage Schema

```python
# SQLite Tables

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL,
    current_round INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_code TEXT,
    error_message TEXT
);

CREATE TABLE session_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    data_type TEXT NOT NULL,  -- 'initial_context', 'brief', 'plan', 'data_result', etc.
    round INTEGER,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE session_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    file_type TEXT NOT NULL,  -- 'pdf', 'excel', 'pptx'
    file_path TEXT NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX idx_session_data_session ON session_data(session_id);
CREATE INDEX idx_session_data_type ON session_data(session_id, data_type);
CREATE INDEX idx_session_files_session ON session_files(session_id);
```

### State Persistence Strategy

```python
class SessionManager:
    """
    Ralph Pattern: каждое изменение состояния немедленно сохраняется.
    При перезапуске система восстанавливает состояние из БД.
    """

    async def save_state(self, session_id: str, state_type: str, data: dict):
        """Сохранить промежуточное состояние."""
        await self.db.execute(
            "INSERT INTO session_data (session_id, data_type, round, data) VALUES (?, ?, ?, ?)",
            (session_id, state_type, self.current_round, json.dumps(data))
        )

    async def restore_session(self, session_id: str) -> Session:
        """Восстановить сессию из БД."""
        session = await self.db.fetch_one(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        )
        if not session:
            raise SessionNotFound(session_id)

        # Восстанавливаем все данные
        data = await self.db.fetch_all(
            "SELECT * FROM session_data WHERE session_id = ? ORDER BY created_at",
            (session_id,)
        )

        return Session.from_db(session, data)

    async def get_resume_point(self, session_id: str) -> str:
        """Определить точку для возобновления."""
        session = await self.restore_session(session_id)

        if session.status == "failed":
            return self._get_last_successful_state(session)

        return session.status
```

---

## 5. Parallel Execution

### Data || Research Parallel Architecture

```
                            ┌─────────────────────┐
                            │     Orchestrator    │
                            │                     │
                            │  asyncio.gather()   │
                            └──────────┬──────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  │                  ▼
        ┌───────────────────┐          │      ┌───────────────────┐
        │   Data Executor   │          │      │ Research Executor │
        │                   │          │      │                   │
        │  ┌─────────────┐  │          │      │  ┌─────────────┐  │
        │  │  Task d1    │  │          │      │  │  Task r1    │  │
        │  └─────────────┘  │          │      │  └─────────────┘  │
        │  ┌─────────────┐  │          │      │  ┌─────────────┐  │
        │  │  Task d2    │  │          │      │  │  Task r2    │  │
        │  └─────────────┘  │          │      │  └─────────────┘  │
        │  ┌─────────────┐  │          │      │  ┌─────────────┐  │
        │  │  Task d3    │  │          │      │  │  Task r3    │  │
        │  └─────────────┘  │          │      │  └─────────────┘  │
        │                   │          │      │                   │
        │  Sequential       │          │      │  Sequential       │
        │  within executor  │          │      │  within executor  │
        │                   │          │      │                   │
        └─────────┬─────────┘          │      └─────────┬─────────┘
                  │                    │                │
                  │    data_results[]  │                │ research_results[]
                  │                    │                │
                  └────────────────────┼────────────────┘
                                       │
                                       ▼
                            ┌─────────────────────┐
                            │   Results Merger    │
                            │                     │
                            │  Combine results    │
                            │  for Planner review │
                            └─────────────────────┘
```

### Implementation

```python
# orchestrator/parallel.py

import asyncio
from typing import List, Tuple
from agents.data import DataAgent
from agents.research import ResearchAgent

class ParallelExecutor:
    """Параллельное выполнение Data и Research агентов."""

    def __init__(self, data_agent: DataAgent, research_agent: ResearchAgent):
        self.data_agent = data_agent
        self.research_agent = research_agent

    async def execute_round(
        self,
        data_tasks: List[DataTask],
        research_tasks: List[ResearchTask],
        timeout: float = 300.0  # 5 minutes max
    ) -> Tuple[List[DataResult], List[ResearchResult]]:
        """
        Выполняет Data и Research задачи параллельно.

        Returns:
            Tuple[data_results, research_results]
        """
        try:
            data_results, research_results = await asyncio.wait_for(
                asyncio.gather(
                    self._execute_data_tasks(data_tasks),
                    self._execute_research_tasks(research_tasks),
                    return_exceptions=True
                ),
                timeout=timeout
            )

            # Обработка исключений
            if isinstance(data_results, Exception):
                data_results = self._handle_executor_error("data", data_results, data_tasks)
            if isinstance(research_results, Exception):
                research_results = self._handle_executor_error("research", research_results, research_tasks)

            return data_results, research_results

        except asyncio.TimeoutError:
            raise RoundTimeoutError(f"Round execution exceeded {timeout}s timeout")

    async def _execute_data_tasks(self, tasks: List[DataTask]) -> List[DataResult]:
        """Последовательное выполнение Data задач."""
        results = []
        for task in tasks:
            try:
                result = await self.data_agent.execute(task)
                results.append(result)
            except Exception as e:
                results.append(DataResult(
                    task_id=task.id,
                    status="failed",
                    error=str(e)
                ))
        return results

    async def _execute_research_tasks(self, tasks: List[ResearchTask]) -> List[ResearchResult]:
        """Последовательное выполнение Research задач."""
        results = []
        for task in tasks:
            try:
                result = await self.research_agent.execute(task)
                results.append(result)
            except Exception as e:
                results.append(ResearchResult(
                    task_id=task.id,
                    status="failed",
                    error=str(e)
                ))
        return results

    def _handle_executor_error(self, executor_type: str, error: Exception, tasks: List) -> List:
        """Создаёт failed результаты для всех задач при ошибке executor'а."""
        ResultClass = DataResult if executor_type == "data" else ResearchResult
        return [
            ResultClass(task_id=task.id, status="failed", error=str(error))
            for task in tasks
        ]
```

### Timing Diagram

```
Time ──────────────────────────────────────────────────────────────►

Data Executor:
│░░░░░░░░░░│                    │░░░░░░░░░░│
│  Task d1 │                    │  Task d2 │
│  30s     │                    │  25s     │
└──────────┴────────────────────┴──────────┘

Research Executor (parallel):
│░░░░░░░░░░░░░░░░░░░░│          │░░░░░░░░░░░░░░│
│      Task r1       │          │   Task r2    │
│      45s           │          │   35s        │
└────────────────────┴──────────┴──────────────┘

                                               │
Total time: max(55s, 80s) = 80s               │
(vs sequential: 55s + 80s = 135s)             ▼
                                        Round Complete
```

---

## 6. Error Handling

### Error Classification

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ERROR HIERARCHY                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  RalphError (base)                                                  │
│  │                                                                   │
│  ├── TransientError (retryable)                                     │
│  │   ├── APITimeoutError                                            │
│  │   ├── RateLimitError                                             │
│  │   ├── NetworkError                                               │
│  │   └── ServiceUnavailableError                                    │
│  │                                                                   │
│  ├── PermanentError (not retryable)                                 │
│  │   ├── InvalidInputError                                          │
│  │   ├── AuthenticationError                                        │
│  │   ├── QuotaExceededError                                         │
│  │   └── DataNotFoundError                                          │
│  │                                                                   │
│  └── SystemError (requires intervention)                            │
│      ├── DatabaseError                                              │
│      ├── StorageFullError                                           │
│      └── ConfigurationError                                         │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Error Handling by Layer

```python
# API Layer
class APIErrorHandler:
    """Обработка ошибок на уровне API."""

    async def handle_request(self, request: Request, handler):
        try:
            return await handler(request)
        except InvalidInputError as e:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_input", "message": str(e)}
            )
        except AuthenticationError as e:
            return JSONResponse(
                status_code=401,
                content={"error": "unauthorized", "message": str(e)}
            )
        except SessionNotFound as e:
            return JSONResponse(
                status_code=404,
                content={"error": "not_found", "message": str(e)}
            )
        except RalphError as e:
            return JSONResponse(
                status_code=500,
                content={"error": "internal_error", "message": "Research failed", "details": str(e)}
            )


# Agent Layer
class AgentErrorHandler:
    """Обработка ошибок на уровне агентов."""

    async def execute_with_handling(self, agent: BaseAgent, task: Task) -> Result:
        try:
            return await agent.execute(task)
        except TransientError as e:
            # Retryable - будет обработано Retry Logic
            raise
        except PermanentError as e:
            # Не retryable - возвращаем failed result
            return Result(
                task_id=task.id,
                status="failed",
                error=ErrorInfo(
                    code=e.code,
                    message=str(e),
                    recoverable=False
                )
            )
        except Exception as e:
            # Неизвестная ошибка
            logger.exception(f"Unexpected error in agent {agent.name}")
            return Result(
                task_id=task.id,
                status="failed",
                error=ErrorInfo(
                    code="unknown_error",
                    message=str(e),
                    recoverable=False
                )
            )


# Pipeline Layer
class PipelineErrorHandler:
    """Обработка ошибок на уровне pipeline."""

    async def execute_round_with_handling(self, round: int, tasks: List[Task]) -> RoundResult:
        try:
            return await self.executor.execute_round(tasks)
        except RoundTimeoutError:
            # Таймаут раунда - сохраняем частичные результаты
            return await self._handle_timeout(round, tasks)
        except Exception as e:
            # Критическая ошибка - переводим сессию в failed
            await self.session_manager.set_failed(
                self.session_id,
                error_code="round_failed",
                error_message=str(e)
            )
            raise SessionFailedError(self.session_id, str(e))

    async def _handle_timeout(self, round: int, tasks: List[Task]) -> RoundResult:
        """Обработка таймаута раунда."""
        # Собираем завершённые результаты
        completed = await self.get_completed_results(round)

        # Помечаем незавершённые как failed
        for task in tasks:
            if task.id not in [r.task_id for r in completed]:
                completed.append(Result(
                    task_id=task.id,
                    status="failed",
                    error=ErrorInfo(code="timeout", message="Task timed out")
                ))

        return RoundResult(round=round, results=completed, had_timeout=True)
```

### Error Recovery Strategies

```
┌────────────────────────────────────────────────────────────────────────────┐
│                      ERROR RECOVERY STRATEGIES                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. TASK-LEVEL RECOVERY                                                    │
│     ┌─────────────┐                                                         │
│     │ Task Failed │                                                         │
│     └──────┬──────┘                                                         │
│            │                                                                │
│            ▼                                                                │
│     ┌─────────────────┐     Yes     ┌─────────────────┐                    │
│     │ Is Retryable?   │────────────►│  Retry (3x max) │                    │
│     └────────┬────────┘             └─────────────────┘                    │
│              │ No                                                           │
│              ▼                                                              │
│     ┌─────────────────┐     Yes     ┌─────────────────┐                    │
│     │ Has Fallback?   │────────────►│  Use Fallback   │                    │
│     └────────┬────────┘             │  (alt API, etc) │                    │
│              │ No                   └─────────────────┘                    │
│              ▼                                                              │
│     ┌─────────────────┐                                                     │
│     │ Mark as Failed  │                                                     │
│     │ Continue Round  │                                                     │
│     └─────────────────┘                                                     │
│                                                                             │
│  2. ROUND-LEVEL RECOVERY                                                   │
│     ┌─────────────────┐                                                     │
│     │ Round Timeout   │                                                     │
│     └────────┬────────┘                                                     │
│              ▼                                                              │
│     ┌─────────────────────────┐                                             │
│     │ Save partial results    │                                             │
│     │ Mark incomplete as fail │                                             │
│     │ Continue to review      │                                             │
│     └─────────────────────────┘                                             │
│                                                                             │
│  3. SESSION-LEVEL RECOVERY                                                 │
│     ┌─────────────────┐                                                     │
│     │ Critical Error  │                                                     │
│     └────────┬────────┘                                                     │
│              ▼                                                              │
│     ┌─────────────────────────┐                                             │
│     │ Save all state to DB    │                                             │
│     │ Set status = "failed"   │                                             │
│     │ Notify user             │                                             │
│     │ (Manual retry possible) │                                             │
│     └─────────────────────────┘                                             │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Retry Logic

### Retry Configuration

```python
from dataclasses import dataclass
from typing import Tuple, Type

@dataclass
class RetryConfig:
    """Конфигурация retry логики."""

    # Общие настройки
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0

    # Per-error настройки
    retryable_errors: Tuple[Type[Exception], ...] = (
        APITimeoutError,
        RateLimitError,
        NetworkError,
        ServiceUnavailableError,
    )

    # Rate limit специфика
    rate_limit_delay: float = 60.0  # Wait longer for rate limits

    # Timeouts
    request_timeout: float = 30.0
    round_timeout: float = 300.0


# Конфигурация по типам операций
RETRY_CONFIGS = {
    "llm_call": RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        rate_limit_delay=60.0
    ),
    "api_call": RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0
    ),
    "web_search": RetryConfig(
        max_attempts=2,
        base_delay=5.0,
        max_delay=30.0
    ),
    "file_generation": RetryConfig(
        max_attempts=2,
        base_delay=1.0,
        max_delay=10.0
    )
}
```

### Retry Implementation

```python
import asyncio
import random
from functools import wraps

class RetryHandler:
    """Обработчик retry логики с exponential backoff."""

    def __init__(self, config: RetryConfig):
        self.config = config

    async def execute_with_retry(self, func, *args, **kwargs):
        """Выполняет функцию с retry логикой."""
        last_exception = None

        for attempt in range(1, self.config.max_attempts + 1):
            try:
                return await func(*args, **kwargs)

            except self.config.retryable_errors as e:
                last_exception = e
                delay = self._calculate_delay(attempt, e)

                logger.warning(
                    f"Attempt {attempt}/{self.config.max_attempts} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )

                if attempt < self.config.max_attempts:
                    await asyncio.sleep(delay)

            except Exception as e:
                # Non-retryable error
                logger.error(f"Non-retryable error: {e}")
                raise

        # All retries exhausted
        raise RetryExhaustedError(
            f"Failed after {self.config.max_attempts} attempts",
            last_exception=last_exception
        )

    def _calculate_delay(self, attempt: int, error: Exception) -> float:
        """Вычисляет задержку с exponential backoff и jitter."""
        if isinstance(error, RateLimitError):
            # Для rate limit используем фиксированную задержку
            base_delay = self.config.rate_limit_delay
        else:
            # Exponential backoff: base * (2 ^ attempt)
            base_delay = self.config.base_delay * (
                self.config.exponential_base ** (attempt - 1)
            )

        # Добавляем jitter (±25%)
        jitter = base_delay * 0.25 * (2 * random.random() - 1)
        delay = base_delay + jitter

        # Ограничиваем максимальной задержкой
        return min(delay, self.config.max_delay)


# Decorator для retry
def with_retry(config_name: str = "llm_call"):
    """Декоратор для автоматического retry."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            config = RETRY_CONFIGS.get(config_name, RetryConfig())
            handler = RetryHandler(config)
            return await handler.execute_with_retry(func, *args, **kwargs)
        return wrapper
    return decorator


# Использование
class LLMClient:
    @with_retry("llm_call")
    async def complete(self, prompt: str, model: str) -> str:
        """Вызов Claude API с автоматическим retry."""
        response = await self.client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
```

### Retry Flow Diagram

```
                    ┌─────────────┐
                    │   Request   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
           ┌───────│  Attempt 1  │───────┐
           │       └─────────────┘       │
           │                             │
       Success                       Failure
           │                             │
           ▼                             ▼
      ┌─────────┐              ┌─────────────────┐
      │ Return  │              │ Is Retryable?   │
      │ Result  │              └────────┬────────┘
      └─────────┘                       │
                            ┌───────────┴───────────┐
                            │ Yes                   │ No
                            ▼                       ▼
                    ┌───────────────┐       ┌─────────────┐
                    │ Calculate     │       │ Raise Error │
                    │ Backoff Delay │       └─────────────┘
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Sleep(delay)  │
                    │ + jitter      │
                    └───────┬───────┘
                            │
                            ▼
                    ┌─────────────┐
           ┌───────│  Attempt 2  │───────┐
           │       └─────────────┘       │
           │                             │
       Success                       Failure
           │                             │
           ▼                             ▼
      ┌─────────┐              ┌─────────────────┐
      │ Return  │              │ Attempts < Max? │
      │ Result  │              └────────┬────────┘
      └─────────┘                       │
                            ┌───────────┴───────────┐
                            │ Yes                   │ No
                            ▼                       ▼
                    ┌───────────────┐       ┌─────────────────┐
                    │ Continue to   │       │ Raise           │
                    │ Attempt 3...  │       │ RetryExhausted  │
                    └───────────────┘       └─────────────────┘


    Backoff Schedule (base=2s, max=60s):
    ┌─────────┬─────────┬──────────────────────┐
    │ Attempt │ Base    │ With Jitter (±25%)   │
    ├─────────┼─────────┼──────────────────────┤
    │    1    │   2s    │    1.5s - 2.5s       │
    │    2    │   4s    │    3.0s - 5.0s       │
    │    3    │   8s    │    6.0s - 10.0s      │
    │    4    │  16s    │   12.0s - 20.0s      │
    │    5    │  32s    │   24.0s - 40.0s      │
    │   6+    │  60s    │   45.0s - 60.0s (max)│
    └─────────┴─────────┴──────────────────────┘
```

### Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """
    Circuit Breaker для защиты от каскадных сбоев.

    CLOSED → (failures > threshold) → OPEN
    OPEN → (timeout expires) → HALF_OPEN
    HALF_OPEN → (success) → CLOSED
    HALF_OPEN → (failure) → OPEN
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_calls = 0

    async def execute(self, func, *args, **kwargs):
        """Выполняет функцию через circuit breaker."""
        if not self._can_execute():
            raise CircuitOpenError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        """Проверяет, можно ли выполнить запрос."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            if self._recovery_timeout_expired():
                self._transition_to_half_open()
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return self.half_open_calls < self.half_open_max_calls

        return False

    def _on_success(self):
        """Обработка успешного запроса."""
        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_closed()
        self.failure_count = 0

    def _on_failure(self):
        """Обработка неудачного запроса."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            self._transition_to_open()
        elif self.failure_count >= self.failure_threshold:
            self._transition_to_open()

    def _transition_to_open(self):
        self.state = CircuitState.OPEN
        logger.warning("Circuit breaker OPENED")

    def _transition_to_half_open(self):
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        logger.info("Circuit breaker HALF-OPEN")

    def _transition_to_closed(self):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        logger.info("Circuit breaker CLOSED")

    def _recovery_timeout_expired(self) -> bool:
        if self.last_failure_time is None:
            return True
        return datetime.now() > self.last_failure_time + timedelta(seconds=self.recovery_timeout)
```

---

## Appendix: Performance Targets

| Operation | Target | Timeout |
|-----------|--------|---------|
| Initial Research | < 60s | 90s |
| Brief Builder response | < 5s | 10s |
| Planner decision | < 10s | 20s |
| Single Data task | < 30s | 45s |
| Single Research task | < 60s | 90s |
| Parallel round (Data + Research) | < 120s | 300s |
| Full research (3 rounds) | < 15min | 20min |
| Aggregation | < 60s | 120s |
| Report generation (all formats) | < 60s | 120s |

---

## Appendix: Scalability Limits (MVP)

| Resource | Limit |
|----------|-------|
| Concurrent sessions | 10 |
| Tasks per round | 10 |
| Rounds per session | 10 |
| Total tasks per session | 100 |
| Storage per session | 50 MB |
| Max report size | 20 MB |
