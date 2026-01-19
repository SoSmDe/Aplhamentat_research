# CLAUDE.md

## Project Overview
Ralph Deep Research — multi-agent AI research system running entirely through Claude Code.
No Python backend — Claude Code handles web search, file generation, and state management natively.

## How It Works
1. User provides research query via ./loop.sh
2. Claude Code executes pipeline from PROMPT.md
3. Each phase reads prompts from src/prompts/*.md
4. State persists in state/*.json (Ralph Pattern)
5. Reports generate to output/

## Directory Structure
```
ralph/
├── PROMPT.md              # Main pipeline definition
├── loop.sh                # Runner script
├── src/
│   ├── prompts/           # Agent prompts (7 files)
│   └── templates/         # Report templates (PDF/Excel/PPTX)
├── specs/                 # Documentation
├── state/                 # JSON state (auto-created)
└── output/                # Reports (auto-created)
```

## Running Research
```bash
./loop.sh "Your research query"     # Start new
./loop.sh --resume                  # Continue
./loop.sh --status                  # Check progress
./loop.sh --clear                   # Reset state
```

## Ralph Pattern
Execute task → Save result to state/ → Clear context → Next task

## Pipeline Phases
1. **Initial Research** — Quick context gathering via web_search
2. **Brief Builder** — Interactive dialog to clarify requirements
3. **Planner** — Decompose brief into data/research tasks
4. **Data + Research** — Parallel execution with web_search
5. **Coverage Check** — Loop until ≥80% coverage (max 10 rounds)
6. **Aggregator** — Synthesize findings into recommendations
7. **Reporter** — Generate PDF/Excel/PPTX reports

## Completion Signal
Pipeline ends when Claude outputs: `<promise>COMPLETE</promise>`
