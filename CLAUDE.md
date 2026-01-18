# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Ralph is a multi-agent AI research automation system that accepts user queries, conducts comprehensive research through specialized agents, and generates professional reports (PDF, Excel, PowerPoint). The project is currently in the design phase with complete PRD documentation but no implementation yet.

## Technology Stack

**Backend:** Python 3.11+, FastAPI, Anthropic Claude API, asyncio, SQLite
**Frontend:** React 18+, TypeScript, TailwindCSS, React Query
**Report Generation:** WeasyPrint/ReportLab (PDF), openpyxl (Excel), python-pptx (PowerPoint), Jinja2

## Development Commands

```bash
# Backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend && npm install
npm run dev
```

## Architecture

### Agent Pipeline
```
User Input → Brief Builder (Opus) → Planner (Opus) → [Data (Sonnet) || Research (Opus)] → Planner Loop → Aggregator (Opus) → Reporter (Opus) → Output
```

### Core Design Pattern: "Ralph Pattern"
Each agent follows: **Execute task → Save result → Clear context → Next task**. This prevents context bloat and token waste by starting each task with fresh context.

### Agent Responsibilities

| Agent | Model | Purpose |
|-------|-------|---------|
| Brief Builder | Opus | Interactive dialog to clarify user intent, generate research specification |
| Planner | Opus | Decompose Brief into tasks, manage research cycles, check coverage |
| Data | Sonnet | Collect structured metrics via APIs (cost-efficient for simple tasks) |
| Research | Opus | Analyze unstructured info, web search, generate insights |
| Aggregator | Opus | Synthesize findings, create recommendations, validate consistency |
| Reporter | Opus | Generate final outputs in requested formats |

### Key Architectural Decisions

1. **Brief-Driven Workflow** - All work guided by user-approved specification before execution
2. **Data/Research Separation** - Structured data (APIs, metrics) handled separately from qualitative analysis
3. **Parallel Execution** - Data and Research agents run concurrently via asyncio
4. **Adaptive Looping** - Planner checks coverage after each round, adds tasks if <80% complete (max 10 rounds)

## Project Structure (Planned)

```
ralph/
├── api/              # FastAPI endpoints (routes.py, schemas.py)
├── agents/           # AI agents (base.py, brief_builder.py, planner.py, data.py, research.py, aggregator.py, reporter.py)
├── orchestrator/     # Pipeline coordination (pipeline.py, parallel.py)
├── tools/            # Agent tools (llm.py, web_search.py, api_client.py, file_generator.py)
├── storage/          # Data persistence (database.py, session.py, files.py)
├── prompts/          # Agent system prompts in Markdown
├── templates/        # Report templates (pdf/, excel/, pptx/)
├── config/           # Settings and model configuration
├── frontend/         # React application
├── tests/            # Test suites
└── main.py           # Application entry point
```

## API Endpoints

```
POST   /api/sessions                         # Start new research session
POST   /api/sessions/{session_id}/messages   # Send message during brief building
POST   /api/sessions/{session_id}/approve    # Approve Brief to start research
GET    /api/sessions/{session_id}            # Check status
GET    /api/sessions/{session_id}/results    # Get results and reports
```

## Environment Variables

```
ANTHROPIC_API_KEY=sk-ant-...    # Required
DATABASE_URL=...                 # Optional (SQLite default)
REDIS_URL=...                    # Optional
FINANCIAL_API_KEY=...            # Optional external data
NEWS_API_KEY=...                 # Optional external data
```

## Model Configuration

```python
# config/models.py
AGENT_MODELS = {
    "brief_builder": "claude-opus-4-20250514",
    "planner": "claude-opus-4-20250514",
    "data": "claude-sonnet-4-20250514",
    "research": "claude-opus-4-20250514",
    "aggregator": "claude-opus-4-20250514",
    "reporter": "claude-opus-4-20250514",
}
```

## Key Data Structures

- **Session** - Research workflow state (id, status, brief, current_round)
- **Brief** - User-approved research specification (goal, scope items, output formats)
- **ScopeItem** - Individual research topic (topic, type: data/research/both)
- **Task** - Research work unit (description, source, status, result, questions)
- **Plan** - Research decomposition (round, coverage map, data_tasks, research_tasks)

## Documentation

All detailed documentation is in the `docs/` folder:

- `docs/README.md` - Project overview and quick start (Russian)
- `docs/ralph_prd.md` - Complete Product Requirements Document (Russian)
- `docs/ARCHITECTURE.md` - Technical architecture, sequence diagrams, state management, error handling
- `docs/DATA_SCHEMAS.md` - JSON Schema and TypeScript types for all data structures
- `docs/PROMPTS.md` - System prompts for all 7 agents

Project management:
- `IMPLEMENTATION_PLAN.md` - Development checklist by phases
- `PROMPT.md` - Task prompt for autonomous development
