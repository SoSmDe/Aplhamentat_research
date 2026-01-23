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
ALL depths:
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → story_lining → visual_design → reporting → complete

Deep Dive additions (depth: deep_dive):
... → aggregation → [chart_analysis] → story_lining → visual_design → reporting → editing → complete
```

**Notes:**
- `story_lining` runs for ALL depths (creates layout blueprint)
- `visual_design` runs for ALL depths (creates custom infographics)
- `chart_analysis` runs only for deep_dive (when results/series/ exists)
- `editing` runs only for deep_dive (final quality pass)

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

All in `prompts/`:

| Agent | File | Purpose |
|-------|------|---------|
| Initial Research | `initial_research.md` | Context + tags/entities |
| Brief Builder | `brief_builder.md` | Auto-generate Brief |
| Planner | `planner.md` | Decompose into tasks |
| Overview | `overview.md` | Deep Research (9 phases) |
| Data | `data.md` | Structured data via CLI |
| Research | `research.md` | Qualitative analysis |
| Literature | `literature.md` | Academic papers (science domain) |
| Fact Check | `fact_check.md` | Verification (general domain) |
| Questions | `questions_planner.md` | Filter + coverage |
| Aggregator | `aggregator.md` | Synthesize findings |
| Story Liner | `story_liner.md` | Report layout planning |
| Visual Designer | `visual_designer.md` | Custom infographics (SWOT, timelines) |
| Chart Analyzer | `chart_analyzer.md` | Time series analysis (deep_dive) |
| Reporter | `reporter.md` | Generate HTML reports |
| Editor | `editor.md` | Final polish (deep_dive) |

## Data Fetch CLI

```bash
# Available modules
python cli/fetch.py --list-modules

# Crypto
python cli/fetch.py coingecko get_price '["bitcoin"]'
python cli/fetch.py blocklens get_market_cycle_indicators

# Stocks
python cli/fetch.py yfinance get_price_history '{"symbol":"AAPL","start":"2024-01-01"}'

# Research
python cli/fetch.py serper search '{"query":"AI trends 2024"}'
python cli/fetch.py arxiv search '{"query":"machine learning"}'

# Analytics
python cli/fetch.py analytics basic_stats '{"file":"results/series/BTC_price.json"}'
```

## Completion

Research completes when Claude outputs:
```
<promise>COMPLETE</promise>
```
