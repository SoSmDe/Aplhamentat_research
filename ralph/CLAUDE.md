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
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → story_lining → reporting → complete
```

**Note:** `story_lining` runs for ALL depths (creates layout blueprint for Reporter).

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
│   │   └── story.json     # Layout blueprint (ALL depths)
│   ├── results/           # Agent outputs
│   ├── questions/         # Generated questions
│   └── output/            # Final reports
└── src/
    ├── prompts/           # Agent prompts (12 files)
    └── templates/         # Report templates
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
6. **aggregation** — Synthesize findings into recommendations
7. **story_lining** — Plan report layout (ALL depths)
8. **reporting** — Generate HTML reports following story.json layout
9. **complete** — Signal completion

## session.json Structure
```json
{
  "id": "research_YYYYMMDD_HHMMSS_slug",
  "query": "User query",
  "phase": "execution",
  "tags": ["investment", "reit"],
  "entities": [
    {"name": "Company", "type": "company", "ticker": "XYZ"}
  ],
  "execution": {
    "iteration": 2,
    "max_iterations": 5,
    "tasks_pending": ["d3", "r2", "l1"],
    "tasks_completed": ["o1", "d1", "d2", "r1", "f1"]
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
