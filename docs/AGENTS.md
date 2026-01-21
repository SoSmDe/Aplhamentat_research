# Agents

## Overview

Ralph использует 11 специализированных агентов, каждый с отдельным промптом.

```
┌─────────────────────────────────────────────────────────────────┐
│                         AGENTS                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Initial    │  │   Brief     │  │   Planner   │              │
│  │  Research   │  │   Builder   │  │             │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Overview   │  │    Data     │  │  Research   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Questions  │  │   Chart     │  │   Story     │              │
│  │  Planner    │  │  Analyzer   │  │   Liner     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │ Aggregator  │  │  Reporter   │                               │
│  └─────────────┘  └─────────────┘                               │
│                                                                  │
│  ┌─────────────┐                                                │
│  │   Editor    │  (deep_dive only)                              │
│  └─────────────┘                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Agent Details

### Initial Research Agent
**File:** `prompts/initial_research.md`

**Role:** Quick context gathering.

**Capabilities:**
- Web search for basic facts
- Entity extraction (companies, people, concepts)
- Tag classification (crypto, investment, tech, etc.)
- Preliminary question generation

**Output:** `state/initial_context.json`

---

### Brief Builder Agent
**File:** `prompts/brief_builder.md`

**Role:** Auto-generate research brief.

**Capabilities:**
- Analyze query for intent
- Detect output format (html/pdf/excel)
- Detect style (default/warp/minimal)
- Detect depth (executive/standard/comprehensive/deep_dive)
- Generate scope items with questions
- Self-answer clarifying questions

**Output:** `state/brief.json`

**Key Rules:**
- Structured queries → deep_dive (numbered sections, tables, chart specs)
- "Warp" keywords → warp style
- Default: html, standard depth, analyst audience

---

### Planner Agent
**File:** `prompts/planner.md`

**Role:** Decompose brief into tasks.

**Capabilities:**
- Create overview tasks (quick facts)
- Create data tasks (API calls)
- Create research tasks (deep analysis)
- Estimate coverage per task
- Prioritize critical tasks

**Output:** `state/plan.json`

**Task Naming:**
- `o1`, `o2`, ... — overview tasks
- `d1`, `d2`, ... — data tasks
- `r1`, `r2`, ... — research tasks

---

### Overview Agent
**File:** `prompts/overview.md`

**Role:** Quick factual summaries.

**Capabilities:**
- Web search for current state
- Extract key metrics
- Summarize in 2-3 paragraphs
- Note data sources

**Output:** `results/overview_N.json`

**Best For:**
- "Current state of X"
- "What is Y?"
- Quick context

---

### Data Agent
**File:** `prompts/data.md`

**Role:** Quantitative data collection.

**Capabilities:**
- Call APIs via CLI (`cli/fetch.py`)
- Download price history (CoinGecko CSV)
- Get on-chain metrics (BlockLens)
- Get DeFi data (DefiLlama, L2Beat)
- Save time series to separate files

**Output:**
- `results/data_N.json`
- `results/series/*.json`

**APIs Available:**
| API | Data Types |
|-----|------------|
| BlockLens | MVRV, NUPL, SOPR, LTH/STH supply, realized price |
| CoinGecko | Price, market cap, volume |
| DefiLlama | TVL, protocol metrics |
| L2Beat | L2 security scores |
| yfinance | Stock/ETF prices |

**Key Rules:**
- Use CLI, not web search for API data
- Save large arrays to series/ folder
- Full URLs for citations

---

### Research Agent
**File:** `prompts/research.md`

**Role:** Qualitative analysis.

**Capabilities:**
- Web search for news, opinions
- Expert analysis synthesis
- Trend identification
- Scenario building
- Source evaluation

**Output:** `results/research_N.json`

**Key Rules:**
- Full URLs (not domain only)
- Verify sources via WebFetch
- Separate facts from opinions
- No specific technical indicators (RSI, MACD, etc.)
- Focus on on-chain metrics for crypto

---

### Questions Planner Agent
**File:** `prompts/questions_planner.md`

**Role:** Evaluate coverage, generate follow-up questions.

**Capabilities:**
- Analyze completed tasks
- Calculate coverage per scope item
- Identify gaps
- Generate specific questions
- Decide: more research or proceed

**Output:**
- `state/coverage.json`
- `state/questions_plan.json`

---

### Chart Analyzer Agent (deep_dive)
**File:** `prompts/chart_analyzer.md`

**Role:** Render charts, analyze patterns.

**Capabilities:**
- Call `render_charts.py` CLI
- Analyze time series trends
- Identify patterns (accumulation, distribution, etc.)
- Generate narrative options per chart

**Output:**
- `output/charts/*.html`
- `state/charts_analyzed.json`

---

### Story Liner Agent (deep_dive)
**File:** `prompts/story_liner.md`

**Role:** Create narrative structure.

**Capabilities:**
- Define thesis (main question, answer)
- Build narrative arc (hook → context → development → climax → resolution)
- Place charts in narrative
- Choose chart narrative tone (bullish/bearish/neutral)

**Output:** `state/story.json`

---

### Aggregator Agent
**File:** `prompts/aggregator.md`

**Role:** Synthesize all findings.

**Capabilities:**
- Merge all results into sections
- Deduplicate information
- Build recommendations
- Create chart specifications
- Compile citations
- Generate glossary

**Output:**
- `state/aggregation.json`
- `state/chart_data.json`
- `state/citations.json`
- `state/glossary.json`

---

### Editor Agent (deep_dive)
**File:** `prompts/editor.md`

**Role:** Polish and fact-check.

**Capabilities:**
- Check consistency
- Verify numbers
- Improve flow
- Fix terminology
- Ensure style compliance

**Output:** Updated `state/aggregation.json`

---

### Reporter Agent
**File:** `prompts/reporter.md`

**Role:** Generate final report.

**Capabilities:**
- Load HTML template
- Embed charts (iframe for pre-rendered)
- Format sections with proper styling
- Apply Warp branding
- Generate PDF (if requested)
- Generate Excel (if requested)

**Output:**
- `output/report.html`
- `output/report.pdf` (optional)
- `output/data_pack.xlsx` (optional)

**Key Rules:**
- Use pre-rendered charts in deep_dive mode
- No technical indicators (RSI, MACD, Bollinger)
- No unnecessary anglicisms
- On-chain terminology OK (MVRV, NUPL, LTH/STH)
- Warp style: red accent #C41E3A

---

## Agent Communication

Agents don't communicate directly. They share data via state files:

```
Agent A → writes → state/file.json → reads → Agent B
```

**State Flow:**
```
initial_research → initial_context.json
brief_builder    → brief.json
planner          → plan.json
data/research    → results/*.json
questions        → coverage.json, questions_plan.json
chart_analyzer   → charts_analyzed.json, output/charts/
story_liner      → story.json
aggregator       → aggregation.json, chart_data.json, citations.json
editor           → aggregation.json (updated)
reporter         → output/report.html
```
