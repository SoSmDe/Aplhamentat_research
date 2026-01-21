# State Machine Phases

## Overview

```
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  initial_   │──▶│   brief_    │──▶│  planning   │──▶│  execution  │
│  research   │   │   builder   │   │             │   │             │
└─────────────┘   └─────────────┘   └─────────────┘   └──────┬──────┘
                                                              │
                                                              ▼
┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  complete   │◀──│  reporting  │◀──│ aggregation │◀──│  questions_ │
│             │   │             │   │             │   │   review    │
└─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘
                        ▲
                        │ (deep_dive only)
              ┌─────────┴─────────┐
              │                   │
        ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
        │   editing   │◀──│story_lining │◀──│   chart_    │
        │             │   │             │   │  analysis   │
        └─────────────┘   └─────────────┘   └─────────────┘
```

---

## Phase Details

### 1. initial_research
**Prompt:** `prompts/initial_research.md`

**Purpose:** Quick context gathering to understand the topic.

**Input:**
- User query (from session.json)

**Output:**
- `state/initial_context.json`
  - key_facts
  - entities (companies, people, concepts)
  - tags (investment, crypto, etc.)
  - preliminary_questions

**Duration:** ~30 seconds

---

### 2. brief_builder
**Prompt:** `prompts/brief_builder.md`

**Purpose:** Auto-generate research brief based on query analysis.

**Input:**
- `state/initial_context.json`
- User query

**Output:**
- `state/brief.json`
  - goal
  - preferences (style, depth, format, tone)
  - scope_items (topics to cover)
  - constraints

**Key Logic:**
- Detects style from keywords ("Warp" → warp style)
- Detects depth from structure (numbered sections → deep_dive)
- Sets output format (default: html)

**Duration:** ~20 seconds

---

### 3. planning
**Prompt:** `prompts/planner.md`

**Purpose:** Decompose brief into executable tasks.

**Input:**
- `state/brief.json`

**Output:**
- `state/plan.json`
  - overview_tasks (o1, o2, ...)
  - data_tasks (d1, d2, ...)
  - research_tasks (r1, r2, ...)

**Task Types:**
| Type | Agent | Purpose |
|------|-------|---------|
| overview | Overview | Quick factual summary |
| data | Data | API calls, metrics |
| research | Research | Web search, analysis |

**Duration:** ~30 seconds

---

### 4. execution
**Prompt:** `prompts/overview.md`, `prompts/data.md`, `prompts/research.md`

**Purpose:** Execute tasks from plan.

**Input:**
- `state/plan.json`
- `session.json → execution.tasks_pending`

**Output:**
- `results/overview_N.json`
- `results/data_N.json`
- `results/research_N.json`
- `results/series/*.json` (time series)

**Flow:**
```
for each task in tasks_pending:
    execute_task()
    save_result()
    move task to tasks_completed
    → next iteration
```

**Duration:** ~60-180 seconds per task

---

### 5. questions_review
**Prompt:** `prompts/questions_planner.md`

**Purpose:** Evaluate coverage, decide if more research needed.

**Input:**
- All `results/*.json`
- `state/brief.json`
- `state/coverage.json`

**Output:**
- `state/coverage.json` (updated)
- `state/questions_plan.json` (if gaps found)
- Decision: continue execution OR proceed to aggregation

**Logic:**
```python
if coverage.current >= coverage.target:
    phase = "aggregation"  # or chart_analysis for deep_dive
else:
    phase = "execution"    # add more tasks
```

**Duration:** ~30 seconds

---

### 6. chart_analysis (deep_dive only)
**Prompt:** `prompts/chart_analyzer.md`

**Purpose:** Render charts and analyze visual patterns.

**Input:**
- `state/chart_data.json`
- `results/series/*.json`

**Output:**
- `output/charts/*.html` (pre-rendered Plotly)
- `state/charts_analyzed.json` (insights)

**CLI Used:**
```bash
python cli/render_charts.py \
  --chart-data state/chart_data.json \
  --series-dir results/series/ \
  --output-dir output/charts/
```

**Duration:** ~60 seconds

---

### 7. story_lining (deep_dive only)
**Prompt:** `prompts/story_liner.md`

**Purpose:** Create narrative structure for the report.

**Input:**
- `state/aggregation.json`
- `state/charts_analyzed.json`

**Output:**
- `state/story.json`
  - thesis (main question, answer)
  - narrative_arc (hook, context, development, climax)
  - chart_placements (which charts, where)
  - section_order

**Duration:** ~45 seconds

---

### 8. aggregation
**Prompt:** `prompts/aggregator.md`

**Purpose:** Synthesize all findings into coherent structure.

**Input:**
- All `results/*.json`
- `state/brief.json`

**Output:**
- `state/aggregation.json`
  - sections (with content)
  - recommendations
  - key_takeaways
- `state/chart_data.json`
- `state/citations.json`
- `state/glossary.json`

**Duration:** ~90 seconds

---

### 9. editing (deep_dive only)
**Prompt:** `prompts/editor.md`

**Purpose:** Polish and fact-check the report.

**Input:**
- `state/aggregation.json`
- `state/story.json`

**Output:**
- Updated `state/aggregation.json`
- Corrections and improvements

**Duration:** ~60 seconds

---

### 10. reporting
**Prompt:** `prompts/reporter.md`

**Purpose:** Generate final HTML report.

**Input:**
- `state/aggregation.json`
- `state/chart_data.json` (or `output/charts/`)
- `state/citations.json`
- `state/story.json` (deep_dive)
- `ralph/templates/Warp/base.html`

**Output:**
- `output/report.html`
- `output/report.pdf` (if requested)
- `output/data_pack.xlsx` (if requested)

**Key Rules:**
- Use pre-rendered charts (iframe) in deep_dive mode
- Follow Warp style guide
- No technical analysis indicators
- No unnecessary anglicisms

**Duration:** ~120 seconds

---

### 11. complete
**Signal:** `<promise>COMPLETE</promise>`

**Purpose:** End the loop.

No prompt — just a terminal state.

---

## Phase Transitions

| From | To | Condition |
|------|----|-----------|
| initial_research | brief_builder | Always |
| brief_builder | planning | Always |
| planning | execution | Always |
| execution | questions_review | All tasks done |
| questions_review | execution | Coverage < target |
| questions_review | chart_analysis | Coverage OK + deep_dive |
| questions_review | aggregation | Coverage OK + not deep_dive |
| chart_analysis | story_lining | Always |
| story_lining | aggregation | Always |
| aggregation | editing | deep_dive |
| aggregation | reporting | not deep_dive |
| editing | reporting | Always |
| reporting | complete | Always |

---

## Depth Modes

### standard (default)
```
initial → brief → planning → execution ⟷ questions → aggregation → reporting → complete
```
~8-12 phases, 50-80K tokens

### deep_dive
```
initial → brief → planning → execution ⟷ questions → chart_analysis → story_lining → aggregation → editing → reporting → complete
```
~12-16 phases, 100-200K tokens

### Triggers for deep_dive
- Query has numbered sections (## 1., ## 2.)
- Query specifies chart count ("6-8 графиков")
- Query contains tables (┌─, │, └─)
- Query > 1000 chars with structured content
- Keywords: "comprehensive", "detailed", "deep"
