# Ralph Deep Research - Quick Reference

## Quick Start

```bash
cd ralph/

# New research
./loop.sh "Your research query"

# Check status (with progress bar)
./loop.sh --status

# Resume
./loop.sh --resume

# Search
./loop.sh --search "keyword"
```

## Commands

| Command | Description |
|---------|-------------|
| `./loop.sh "query"` | Start new research |
| `./loop.sh --resume` | Continue latest research |
| `./loop.sh --status` | Show progress with visual tracker |
| `./loop.sh --list` | List all research folders |
| `./loop.sh --search "term"` | Search by tags, entities, query |
| `./loop.sh --clear` | Delete latest research |
| `./loop.sh --set-phase <folder> <phase>` | Debug: set phase manually |

## State Machine

```
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → reporting → complete
```

## Key Concepts

### Ralph Pattern
Execute task → Save to state/ → Update phase → Next iteration

### session.json
Single source of truth. Contains:
- Current phase
- Tags & entities
- Execution state (iteration, tasks)
- Coverage metrics

### Progress Tracking
- Visual progress bar (0-100%)
- Phase completion markers (✓ ● ○)
- Coverage bars per scope item
- Task completion status

## Agent Prompts

All in `../src/prompts/`:

| Agent | File | Purpose |
|-------|------|---------|
| Initial Research | `initial_research.md` | Context + tags/entities |
| Brief Builder | `brief_builder.md` | Auto-generate Brief |
| Planner | `planner.md` | Decompose into tasks |
| Overview | `overview.md` | Deep Research (9 phases) |
| Data | `data.md` | Structured data |
| Research | `research.md` | Qualitative analysis |
| Questions | `questions_planner.md` | Filter + coverage |
| Aggregator | `aggregator.md` | Synthesize findings |
| Reporter | `reporter.md` | Generate reports |

## Completion

Research completes when Claude outputs:
```
<promise>COMPLETE</promise>
```
