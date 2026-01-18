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

### 2.1 Initial Research Agent
- [ ] Create prompts/initial_research.md from PROMPTS.md spec
- [ ] Implement agents/initial_research.py
- [ ] Write tests for Initial Research Agent

### 2.2 Brief Builder Agent
- [ ] Create prompts/brief_builder.md from PROMPTS.md spec
- [ ] Implement agents/brief_builder.py
- [ ] Create api/routes.py POST /sessions endpoint
- [ ] Create api/routes.py POST /sessions/{id}/messages endpoint
- [ ] Create api/routes.py POST /sessions/{id}/approve endpoint
- [ ] Write tests for Brief Builder flow

### 2.3 Planner Agent
- [ ] Create prompts/planner.md from PROMPTS.md spec
- [ ] Implement agents/planner.py (initial plan generation)
- [ ] Implement planner coverage check logic
- [ ] Implement planner loop (continue/done decision)
- [ ] Write tests for Planner

### 2.4 Data Agent
- [ ] Create prompts/data.md from PROMPTS.md spec
- [ ] Implement agents/data.py
- [ ] Implement tools/api_client.py (mock financial API)
- [ ] Write tests for Data Agent

### 2.5 Research Agent
- [ ] Create prompts/research.md from PROMPTS.md spec
- [ ] Implement agents/research.py
- [ ] Implement tools/web_search.py (mock or real)
- [ ] Write tests for Research Agent

### 2.6 Aggregator Agent
- [ ] Create prompts/aggregator.md from PROMPTS.md spec
- [ ] Implement agents/aggregator.py
- [ ] Implement consistency checking logic
- [ ] Write tests for Aggregator

### 2.7 Reporter Agent
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
