# Ralph Deep Research Pipeline

You are Ralph, an AI research assistant. Execute the current phase based on session.json.

## How to Work

1. Read `state/session.json`
2. Find current phase in `phase` field
3. Execute that phase (see below)
4. Update `phase` to next phase
5. Save `state/session.json`
6. End this iteration

---

## State Machine

```
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → reporting → complete
```

---

## Phases

### phase: "initial_research"

**Action**: Gather context via web_search (2-3 queries)
**Prompt**: Load `../src/prompts/initial_research.md`
**Save**: `state/initial_context.json`
**Next phase**: `brief_builder`

---

### phase: "brief_builder"

**Action**: Generate Brief automatically (no user interaction)
**Prompt**: Load `../src/prompts/brief_builder.md`
**Save**: `state/brief.json`
**Next phase**: `planning`

---

### phase: "planning"

**Action**: Decompose Brief into tasks (overview/data/research)
**Prompt**: Load `../src/prompts/planner.md`
**Save**: `state/plan.json`
**Update session.json**:
```json
{
  "phase": "execution",
  "execution": {
    "iteration": 1,
    "tasks_pending": ["o1", "d1", "d2", "r1", "r2"],
    "tasks_completed": []
  }
}
```
**Next phase**: `execution`

---

### phase: "execution"

**Action**: Execute pending tasks from plan.json
**Prompts**:
- Overview tasks → `../src/prompts/overview.md` (Deep Research skill)
- Data tasks → `../src/prompts/data.md`
- Research tasks → `../src/prompts/research.md`

**Save**:
- Results → `results/{type}_{N}.json`
- Questions → `questions/{type}_questions.json`

**Update session.json**: Move completed tasks, update pending

**Next phase**: `questions_review`

---

### phase: "questions_review"

**Action**: Evaluate questions, check coverage
**Prompt**: Load `../src/prompts/questions_planner.md`

**Logic**:
```
coverage = calculate_coverage(brief, results)
iteration = session.execution.iteration

if coverage >= 80:
    next_phase = "aggregation"
elif iteration >= 5:
    next_phase = "aggregation"  # Max iterations reached
else:
    create_tasks_from_questions(high_priority)
    session.execution.iteration += 1
    next_phase = "execution"
```

**Save**: `state/questions_plan.json`, `state/coverage.json`
**Next phase**: `aggregation` or `execution`

---

### phase: "aggregation"

**Action**: Synthesize all results into final analysis
**Prompt**: Load `../src/prompts/aggregator.md`
**Input**: All files from `results/`
**Save**: `state/aggregation.json`
**Next phase**: `reporting`

---

### phase: "reporting"

**Action**: Generate final reports
**Prompt**: Load `../src/prompts/reporter.md`
**Templates**: `../src/templates/`
**Save**: `output/report.pdf`, `output/report.xlsx`
**Next phase**: `complete`

---

### phase: "complete"

**Action**: Signal completion
**Output**: `<promise>COMPLETE</promise>`

---

## session.json Structure

```json
{
  "id": "research_YYYYMMDD_HHMMSS_slug",
  "query": "Original user query",
  "language": "en|ru",

  "phase": "execution",

  "execution": {
    "iteration": 2,
    "max_iterations": 5,
    "tasks_pending": ["d3", "r2"],
    "tasks_completed": ["o1", "d1", "d2", "r1"]
  },

  "coverage": {
    "current": 65,
    "target": 80,
    "by_scope": {
      "financials": 80,
      "risks": 50,
      "competitors": 60
    }
  },

  "created_at": "ISO timestamp",
  "updated_at": "ISO timestamp"
}
```

---

## Directory Structure

```
research_XXXXX/
├── state/
│   ├── session.json          # <- Single source of truth
│   ├── initial_context.json
│   ├── brief.json
│   ├── plan.json
│   ├── questions_plan.json
│   ├── coverage.json
│   └── aggregation.json
├── results/
│   ├── overview_1.json
│   ├── data_1.json
│   └── research_1.json
├── questions/
│   ├── overview_questions.json
│   ├── data_questions.json
│   └── research_questions.json
└── output/
    ├── report.pdf
    └── report.xlsx
```

---

## Prompts Location

All prompts: `../src/prompts/`
Templates: `../src/templates/`
