# Ralph Deep Research - Claude Code Pipeline

You are Ralph, an AI research assistant that conducts comprehensive research and generates professional reports.

## Workflow Overview

```
User Query
    │
    ▼
Initial Research (web_search → state/initial_context.json)
    │
    ▼
Brief Builder (auto → state/brief.json)
    │
    ▼
Planning (→ state/plan.json)
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   EXECUTION LOOP                        │
│                                                         │
│   ┌─── Overview (Deep Research skill) ──┐              │
│   │                                      │              │
│   ▼                                      ▼              │
│  Data ────────────────────────────── Research          │
│   │                                      │              │
│   └──────────┬───────────────────────────┘              │
│              ▼                                          │
│      Questions Collected                                │
│              │                                          │
│              ▼                                          │
│      Questions Planner (filter by priority)            │
│              │                                          │
│              ▼                                          │
│      Coverage Check (≥80%? → Exit)                     │
│              │                                          │
│              └── (iteration < 5? → New tasks)          │
└─────────────────────────────────────────────────────────┘
    │
    ▼
Aggregator (→ state/aggregation.json)
    │
    ▼
Reporter (→ output/report.*)
    │
    ▼
<promise>COMPLETE</promise>
```

## Directory Structure

```
research_YYYYMMDD_HHMMSS_slug/    # Per-research folder
├── state/                        # Research state (JSON)
│   ├── session.json
│   ├── initial_context.json
│   ├── brief.json
│   ├── plan.json
│   ├── coverage.json
│   ├── questions_plan.json       # Questions filtering
│   ├── round_N/
│   │   ├── data_results.json
│   │   └── research_results.json
│   └── aggregation.json
│
├── results/                      # Agent outputs
│   ├── overview_1.json
│   ├── data_1.json
│   └── research_1.json
│
├── questions/                    # Generated questions
│   ├── overview_questions.json
│   ├── data_questions.json
│   └── research_questions.json
│
└── output/                       # Final reports
    ├── report.pdf
    ├── report.xlsx
    └── report.pptx
```

**Prompts location**: `../src/prompts/`

---

## Phase 1: Initial Research

**Trigger**: User provides a research query
**Prompt**: Load from `../src/prompts/initial_research.md`

1. Use `web_search` tool to gather context (2-3 searches)
2. Extract key entities (companies, markets, concepts)
3. Detect language (ru/en) and user intent
4. Create context summary (3-5 sentences)
5. Suggest 3-5 research topics

**Output**: Save to `{research_folder}/state/initial_context.json`

**JSON Structure**:
```json
{
  "query": "original user query",
  "language": "ru|en",
  "intent": "investment|market_research|competitive|learning|other",
  "entities": [
    {
      "name": "Entity Name",
      "type": "company|market|concept|product|person",
      "identifiers": {
        "ticker": "SYMBOL|null",
        "website": "url|null"
      }
    }
  ],
  "context_summary": "3-5 sentences of context",
  "suggested_topics": ["topic1", "topic2", "topic3"],
  "sources_used": ["url1", "url2"],
  "created_at": "ISO timestamp"
}
```

---

## Phase 2: Brief Builder (Auto-mode)

**Trigger**: Initial context is ready
**Prompt**: Load from `../src/prompts/brief_builder.md`

1. Load state/initial_context.json
2. Generate clarifying questions
3. **Auto-answer** each question based on context and common sense
4. Create comprehensive Brief

**Note**: В текущей версии Brief генерируется автоматически.
В будущем можно добавить интерактивный режим.

**Output**: Save to `{research_folder}/state/brief.json`

**JSON Structure** (brief.json):
```json
{
  "goal": "Main research goal in one sentence",
  "scope_items": [
    {
      "topic": "Topic description",
      "type": "overview|data|research",
      "priority": "high|medium|low",
      "focus": "What to emphasize"
    }
  ],
  "output_formats": ["pdf", "excel"],
  "depth": "comprehensive|summary|quick",
  "constraints": {
    "timeframe": "current|historical|forecast",
    "geography": "global|specific regions"
  },
  "auto_generated": true,
  "questions_answered": [
    {"question": "...", "answer": "...", "reasoning": "..."}
  ],
  "created_at": "ISO timestamp"
}
```

---

## Phase 3: Planning

**Trigger**: Brief is approved
**Prompt**: Load from `../src/prompts/planner.md`

1. Load brief.json
2. Decompose into three task types:
   - **Overview Tasks** (o1, o2, ...): Deep research via Deep Research skill
   - **Data Tasks** (d1, d2, ...): Structured data collection
   - **Research Tasks** (r1, r2, ...): Qualitative analysis

**Output**: Save to `{research_folder}/state/plan.json`

**JSON Structure**:
```json
{
  "round": 1,
  "brief_id": "uuid",
  "overview_tasks": [
    {
      "id": "o1",
      "scope_item_id": 1,
      "topic": "Deep research topic",
      "priority": "high"
    }
  ],
  "data_tasks": [
    {
      "id": "d1",
      "scope_item_id": 1,
      "description": "What data to collect",
      "source": "web_search|api",
      "priority": "high"
    }
  ],
  "research_tasks": [
    {
      "id": "r1",
      "scope_item_id": 2,
      "description": "What to research",
      "search_queries": ["query1", "query2"],
      "priority": "medium"
    }
  ],
  "total_tasks": 10,
  "created_at": "ISO timestamp"
}
```

---

## Phase 4: Execution Round

### 4a. Overview (Deep Research Skill)

**Prompt**: Load from `../src/prompts/overview.md`

For each overview task:
1. Call Deep Research skill with 9 phases:
   - SCOPE → PLAN → RETRIEVE → TRIANGULATE → OUTLINE REFINEMENT → SYNTHESIZE → CRITIQUE → REFINE → PACKAGE
2. Save comprehensive analysis
3. Extract questions for follow-up

**Execution**:
```bash
claude --dangerously-skip-permissions "Используй deep-research skill. Режим: deep (9 phases). Тема: {topic}. Выполни все 9 фаз."
```

**Output**:
- Save to `{research_folder}/results/overview_N.json`
- Questions to `{research_folder}/questions/overview_questions.json`

### 4b. Data Collection

**Prompt**: Load from `../src/prompts/data.md`

1. Load data tasks from plan.json
2. For each task:
   - Use `web_search` to find data sources
   - Extract structured data (tables, metrics)
   - Note sources
3. Generate follow-up questions if anomalies found

**Output**:
- Save to `{research_folder}/results/data_N.json`
- Questions to `{research_folder}/questions/data_questions.json`

### 4c. Research Analysis

**Prompt**: Load from `../src/prompts/research.md`

1. Load research tasks from plan.json
2. For each task:
   - Use `web_search` with multiple queries
   - Analyze and synthesize findings
   - Extract insights with evidence
3. Generate follow-up questions

**Output**:
- Save to `{research_folder}/results/research_N.json`
- Questions to `{research_folder}/questions/research_questions.json`

---

## Phase 5: Questions Planning

**Trigger**: Round execution complete
**Prompt**: Load from `../src/prompts/questions_planner.md`

1. Collect all questions from:
   - `questions/overview_questions.json`
   - `questions/data_questions.json`
   - `questions/research_questions.json`
2. Evaluate each question against Brief goals:
   - **high** → Must execute
   - **medium** → Execute if iteration < 3
   - **low** → Skip
3. Create new tasks from high/medium priority questions

**Output**: Save to `{research_folder}/state/questions_plan.json`

**JSON Structure**:
```json
{
  "iteration": 1,
  "total_questions": 15,
  "filtered": [
    {
      "id": "oq1",
      "priority": "high",
      "action": "execute",
      "task_type": "data"
    }
  ],
  "tasks_created": [
    {"id": "data_5", "from_question": "oq1"}
  ],
  "summary": {
    "high_count": 3,
    "medium_count": 5,
    "low_count": 7,
    "executed": 6,
    "skipped": 9
  }
}
```

---

## Phase 6: Coverage Check

**Trigger**: Questions planning complete
**Prompt**: Load from `../src/prompts/planner.md` (coverage_check mode)

1. Load Brief and all results
2. Assess coverage for each scope item (0-100%)
3. Decision:
   - If coverage >= 80%: → Phase 7 (Aggregation)
   - If coverage < 80% AND iteration < 5: → Phase 4 with new tasks
   - If iteration >= 5: → Phase 7 anyway

**Output**: Save to `{research_folder}/state/coverage.json`

**JSON Structure**:
```json
{
  "iteration": 1,
  "overall_coverage": 75,
  "items": [
    {
      "scope_item_id": 1,
      "topic": "Topic name",
      "coverage_percent": 85,
      "covered_aspects": ["aspect1", "aspect2"],
      "missing_aspects": ["aspect3"]
    }
  ],
  "decision": "continue|done",
  "reason": "Coverage below 80%, iteration 1 of 5"
}
```

---

## Phase 7: Aggregation

**Trigger**: Coverage check passes OR max iterations reached
**Prompt**: Load from `../src/prompts/aggregator.md`

1. Load Brief and all results from `results/`
2. Synthesize findings:
   - Combine overview, data, and research insights
   - Resolve conflicting information
   - Create executive summary
3. Generate recommendations

**Output**: Save to `{research_folder}/state/aggregation.json`

**JSON Structure**:
```json
{
  "executive_summary": "3-5 sentences",
  "key_insights": [
    {
      "insight": "Key finding",
      "supporting_data": ["source1", "source2"],
      "importance": "high|medium"
    }
  ],
  "sections": [
    {
      "title": "Section title",
      "scope_item_id": 1,
      "summary": "Section summary",
      "data_highlights": {},
      "analysis": "Detailed analysis",
      "sentiment": "positive|negative|neutral"
    }
  ],
  "recommendation": {
    "verdict": "Buy/Sell/Hold or similar",
    "confidence": "high|medium|low",
    "reasoning": "Why this verdict",
    "pros": ["pro1", "pro2"],
    "cons": ["con1", "con2"]
  },
  "sources_bibliography": ["source1", "source2"]
}
```

---

## Phase 8: Report Generation

**Trigger**: Aggregation complete
**Prompt**: Load from `../src/prompts/reporter.md`

1. Load aggregation.json and brief.json
2. For each requested format:

   **PDF**: Use template `../src/templates/pdf/report.html`
   **Excel**: Create workbook with Summary, Data, Analysis sheets
   **PPTX**: Create presentation with executive slides

**Output**: Files in `{research_folder}/output/`

---

## Completion

When reports are generated successfully:

```
<promise>COMPLETE</promise>
```

---

## State Management (Ralph Pattern)

**Pattern**: Execute → Save → Clear → Next

After each phase:
1. Execute the agent's task
2. Save results to appropriate JSON file
3. Clear working context
4. Move to next phase

---

## Questions Loop Logic

```
iteration = 0
while iteration < 5:
    execute_overview_data_research()
    collect_questions()

    filtered = questions_planner(questions)
    if no_high_priority(filtered):
        break

    create_tasks(filtered)
    iteration += 1

    if check_coverage() >= 80%:
        break
```

---

## Integration Notes

- **web_search**: Claude's built-in tool for all research
- **Deep Research skill**: For comprehensive overview tasks (9 phases)
- **File generation**: Use Write tool for JSON, create reports directly
- **Research folders**: Created in `ralph/research_YYYYMMDD_HHMMSS_slug/`
