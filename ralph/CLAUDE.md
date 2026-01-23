# CLAUDE.md

## Project Overview
Ralph Deep Research — State Machine based multi-agent AI research system running entirely through Claude Code.
No Python backend — Claude Code handles web search, file generation, and state management natively.

## How It Works
1. User provides research query via ./loop.sh
2. loop.sh creates session.json with initial phase
3. Each iteration: Claude Code reads PROMPT.md, executes current phase, updates phase
4. State persists in state/session.json (single source of truth)
5. Loop continues until phase = "complete"

## State Machine

```
Standard flow:
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → story_lining → visual_design → reporting → complete

Deep_dive flow (adds 2 phases):
... → aggregation → chart_analysis → story_lining → visual_design → reporting → editing → complete
```

**Notes:**
- `story_lining` runs for ALL depths (creates layout blueprint for Reporter)
- `visual_design` runs for ALL depths (creates custom infographics: SWOT, timelines, comparison matrices)
- `chart_analysis` runs only for deep_dive (analyzes time series charts)
- `editing` runs only for deep_dive (final quality pass on report)

## Directory Structure
```
ralph/
├── PROMPT.md              # State Machine definition
├── loop.sh                # Runner script
├── research_XXXXX/        # Per-research folder (auto-created)
│   ├── state/
│   │   ├── session.json   # <- Single source of truth
│   │   ├── initial_context.json
│   │   ├── brief.json
│   │   ├── plan.json
│   │   ├── coverage.json
│   │   ├── questions_plan.json
│   │   ├── aggregation.json
│   │   ├── story.json          # Layout blueprint (ALL depths)
│   │   ├── visuals.json        # Custom infographics (ALL depths)
│   │   ├── charts_analyzed.json # (deep_dive only)
│   │   └── editor_log.json     # (deep_dive only)
│   ├── results/           # Agent outputs
│   ├── questions/         # Generated questions
│   └── output/
│       ├── report.html    # Final report
│       ├── visuals/       # Custom infographics (SWOT, timelines, etc.)
│       └── charts/        # Plotly charts (deep_dive only)
└── prompts/               # Agent prompts (13 files)
```

## Running Research
```bash
./loop.sh "Your research query"     # Start new
./loop.sh --resume                  # Continue
./loop.sh --status                  # Show detailed progress
./loop.sh --list                    # List all research
./loop.sh --search "keyword"        # Search by tags, entities, query
./loop.sh --clear                   # Delete research
./loop.sh --set-phase <folder> <phase>  # Debug: set phase manually
```

## Features

### Progress Tracker
`--status` shows visual progress:
- Progress bar with percentage
- Phase list with current marker
- Coverage bars per scope
- Task completion status
- Tags and entities
- Output file status

### Tagging & Search
- Auto-extracts tags and entities during initial_research phase
- Search across all research by: query text, tags, entity names
- Tags: investment, reit, tech, dividend, etc.
- Entities: companies, sectors, indices, concepts

### Quality Assurance

**Source Quality Tiers:**
- tier_1: Primary sources (SEC filings, on-chain data, official APIs)
- tier_2: Authoritative (Bloomberg, Reuters, major research firms)
- tier_3: Credible (industry publications, aggregators)
- tier_4: Secondary (news citing others, social media)
- tier_5: Unverified (anonymous, promotional)

**Data Freshness Tracking:**
- 🟢 Fresh (< 30 days) — Full confidence
- 🟡 Recent (30-90 days) — Check for updates
- 🟠 Dated (90-180 days) — Verify with newer source
- 🔴 Stale (180-365 days) — Use with caution
- ⚫ Outdated (> 365 days) — Historical context only

**Aggregation outputs:**
- `source_quality_summary` — Quality grade A-D based on source tiers
- `data_freshness` — Freshness grade A-D with stale data alerts

## State Pattern
Each phase:
1. Read state/session.json
2. Execute phase logic
3. Save outputs to appropriate files
4. Update phase in session.json
5. End iteration

## Pipeline Phases
1. **initial_research** — Quick context + extract tags/entities
2. **brief_builder** — Auto-generate research Brief
3. **planning** — Decompose brief into overview/data/research/literature/fact_check tasks
4. **execution** — Execute pending tasks (loops with questions_review)
5. **questions_review** — Evaluate questions, check coverage, decide next
6. **aggregation** — Synthesize findings, triangulate, prepare charts
7. **chart_analysis** — *(deep_dive only)* Analyze time series, write chart narratives
8. **story_lining** — Plan report layout (ALL depths)
9. **visual_design** — Create custom infographics: SWOT, timelines, comparison matrices (ALL depths)
10. **reporting** — Generate HTML reports following story.json + visuals.json layout
11. **editing** — *(deep_dive only)* Final quality pass, fix errors, polish text
12. **complete** — Signal completion

## session.json Structure
```json
{
  "id": "research_YYYYMMDD_HHMMSS_slug",
  "query": "User query",
  "language": "ru|en",
  "phase": "execution",
  "domain": "crypto|finance|business|science|technology|general",
  "domain_secondary": "business|null",
  "domain_confidence": "high|medium|low",
  "tags": ["investment", "reit"],
  "entities": [
    {"name": "Company", "type": "company", "ticker": "XYZ"}
  ],
  "preferences": {
    "depth": "executive|standard|comprehensive|deep_dive",
    "tone": "neutral_business",
    "style": "default|warp",
    "audience": "executives|analysts|researchers|general",
    "output_format": "html"
  },
  "execution": {
    "iteration": 2,
    "max_iterations": 5,
    "tasks_pending": ["d3", "r2", "l1"],
    "tasks_completed": ["o1", "d1", "d2", "r1", "f1"],
    "current_iteration_tasks": []
  },
  "coverage": {
    "current": 65,
    "target": 80,
    "by_scope": {"financials": 80, "risks": 50}
  },
  "created_at": "ISO",
  "updated_at": "ISO"
}
```

## Completion Signal
Pipeline ends when Claude outputs: `<promise>COMPLETE</promise>`
