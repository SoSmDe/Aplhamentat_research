Отлично! У тебя уже всё готово. Посмотрю что в файлах:Супер, все документы на месте! Теперь нужно подготовить для Ralph. Вот план:

---

## Что делать

### 1. Создай папку проекта и скопируй документы

```bash
mkdir ralph-deep-research
cd ralph-deep-research

# Скопируй все загруженные файлы в docs/
mkdir docs
cp ARCHITECTURE.md DATA_SCHEMAS.md PROMPTS.md ralph_prd.md README.md docs/

# CLAUDE.md в корень (это для Claude Code)
cp CLAUDE.md .
```

### 2. Создай PROMPT.md (главный файл для Ralph)

```markdown
# Ralph Deep Research - Build Task

## Context
You are building a multi-agent deep research system.
All specifications are in the `docs/` folder:
- `docs/ralph_prd.md` - Product Requirements Document
- `docs/ARCHITECTURE.md` - Technical architecture
- `docs/DATA_SCHEMAS.md` - JSON schemas for all data structures
- `docs/PROMPTS.md` - System prompts for each agent
- `CLAUDE.md` - Project overview and conventions

## Current Task
Read `IMPLEMENTATION_PLAN.md` and complete the highest priority unchecked item.

After completing each task:
1. Run tests: `pytest tests/ -v`
2. Commit changes: `git add -A && git commit -m "feat: <description>"`
3. Mark item as [x] in IMPLEMENTATION_PLAN.md

## Rules
- Follow CLAUDE.md conventions strictly
- Use type hints in all Python code
- Write tests for new functionality
- Keep functions small and focused
- Use async/await for I/O operations

## Completion
When ALL items in IMPLEMENTATION_PLAN.md are checked [x], output:
<promise>COMPLETE</promise>
```

### 3. Создай IMPLEMENTATION_PLAN.md

```markdown
# Implementation Plan

## Phase 1: Foundation (Week 1-2)

### 1.1 Project Setup
- [ ] Initialize Python project with pyproject.toml
- [ ] Create virtual environment and requirements.txt
- [ ] Setup FastAPI application skeleton (main.py)
- [ ] Configure environment variables (.env.example)
- [ ] Setup SQLite database with SQLAlchemy
- [ ] Create config/settings.py and config/models.py

### 1.2 Core Infrastructure
- [ ] Implement tools/llm.py (Claude API wrapper with model selection)
- [ ] Implement storage/database.py (Session, Brief, Task models)
- [ ] Implement storage/session.py (session state management)
- [ ] Create agents/base.py (BaseAgent class)
- [ ] Setup basic test infrastructure (pytest, conftest.py)

## Phase 2: Agents (Week 3-5)

### 2.1 Brief Builder Agent
- [ ] Create prompts/brief_builder.md from PROMPTS.md spec
- [ ] Implement agents/brief_builder.py
- [ ] Create api/routes.py POST /sessions endpoint
- [ ] Create api/routes.py POST /sessions/{id}/messages endpoint
- [ ] Create api/routes.py POST /sessions/{id}/approve endpoint
- [ ] Write tests for Brief Builder flow

### 2.2 Planner Agent
- [ ] Create prompts/planner.md from PROMPTS.md spec
- [ ] Implement agents/planner.py (initial plan generation)
- [ ] Implement planner coverage check logic
- [ ] Implement planner loop (continue/done decision)
- [ ] Write tests for Planner

### 2.3 Data Agent
- [ ] Create prompts/data.md from PROMPTS.md spec
- [ ] Implement agents/data.py
- [ ] Implement tools/api_client.py (mock financial API)
- [ ] Write tests for Data Agent

### 2.4 Research Agent
- [ ] Create prompts/research.md from PROMPTS.md spec
- [ ] Implement agents/research.py
- [ ] Implement tools/web_search.py (mock or real)
- [ ] Write tests for Research Agent

### 2.5 Aggregator Agent
- [ ] Create prompts/aggregator.md from PROMPTS.md spec
- [ ] Implement agents/aggregator.py
- [ ] Implement consistency checking logic
- [ ] Write tests for Aggregator

### 2.6 Reporter Agent
- [ ] Create prompts/reporter.md from PROMPTS.md spec
- [ ] Implement agents/reporter.py
- [ ] Implement tools/file_generator.py (PDF, Excel, PPTX)
- [ ] Create templates/pdf/default.html
- [ ] Create templates/excel/default.py
- [ ] Write tests for Reporter

## Phase 3: Orchestration (Week 6-7)

### 3.1 Pipeline
- [ ] Implement orchestrator/pipeline.py (main research flow)
- [ ] Implement orchestrator/parallel.py (async Data || Research)
- [ ] Connect all agents in sequence
- [ ] Implement research loop with Planner review
- [ ] Write integration tests for full pipeline

### 3.2 API Completion
- [ ] Implement GET /sessions/{id} (status endpoint)
- [ ] Implement GET /sessions/{id}/results (download reports)
- [ ] Add WebSocket support for real-time updates
- [ ] Write API integration tests

## Phase 4: Frontend (Week 8-9)

### 4.1 React Setup
- [ ] Initialize React app with Vite + TypeScript
- [ ] Setup TailwindCSS
- [ ] Setup React Query for API calls
- [ ] Create basic layout components

### 4.2 Pages
- [ ] Create HomePage (new research input)
- [ ] Create ChatPage (brief building dialog)
- [ ] Create ProgressPage (research progress tracking)
- [ ] Create ResultsPage (view and download reports)

### 4.3 Integration
- [ ] Connect frontend to backend API
- [ ] Implement WebSocket connection for live updates
- [ ] Add error handling and loading states

## Phase 5: Polish (Week 10)

- [ ] End-to-end testing
- [ ] Error handling improvements
- [ ] Documentation cleanup
- [ ] Performance optimization
- [ ] Docker setup for deployment
```

### 4. Инициализируй git и запусти Ralph

```bash
git init
git add -A
git commit -m "Initial commit: project documentation"

# Запуск Ralph
/ralph-loop "Build the project per PROMPT.md" --max-iterations 100 --completion-promise "COMPLETE"
```

---

## Структура после подготовки

```
ralph-deep-research/
├── PROMPT.md                 # Главный промпт для Ralph
├── IMPLEMENTATION_PLAN.md    # Чеклист задач
├── CLAUDE.md                 # Инструкции для Claude Code
├── docs/
│   ├── README.md
│   ├── ralph_prd.md
│   ├── ARCHITECTURE.md
│   ├── DATA_SCHEMAS.md
│   └── PROMPTS.md
└── (Ralph создаст остальное)
```

---

Хочешь чтобы я создал PROMPT.md и IMPLEMENTATION_PLAN.md файлами? Или ты сам скопируешь?