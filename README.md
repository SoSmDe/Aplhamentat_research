# Ralph Deep Research

**AI-powered multi-agent research system running entirely through Claude Code.**

Ralph is a state machine-based research pipeline that autonomously conducts deep research on any topic. No Python backend required — Claude Code handles web search, data collection, analysis, and report generation natively.

## Features

- **Autonomous Research Pipeline** — From query to PDF report without manual intervention
- **Multi-Agent Architecture** — 9 specialized agents (Initial Research, Brief Builder, Planner, Overview, Data, Research, Questions, Aggregator, Reporter)
- **State Machine Execution** — Reliable phase transitions with progress tracking
- **Smart Coverage System** — Iterates until 80% research coverage achieved
- **Multiple Data Sources** — Crypto (BlockLens, CoinGecko, DefiLlama), Stocks (yFinance, SEC EDGAR, FRED), Research (World Bank, IMF)
- **Professional Reports** — HTML, PDF, Excel output with Plotly charts
- **Progress Visualization** — Real-time progress bars, phase markers, coverage metrics

## Quick Start

```bash
cd ralph/

# Start new research
./loop.sh "Bitcoin market analysis Q1 2025"

# Check progress
./loop.sh --status

# Resume interrupted research
./loop.sh --resume

# Search past research
./loop.sh --search "bitcoin"
```

## Architecture

### State Machine

```
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → reporting → complete
```

| Phase | Agent | Purpose |
|-------|-------|---------|
| `initial_research` | Initial Research | Quick context gathering, extract tags & entities |
| `brief_builder` | Brief Builder | Auto-generate research brief with scope items |
| `planning` | Planner | Decompose brief into overview/data/research tasks |
| `execution` | Overview, Data, Research | Execute tasks, collect data, generate questions |
| `questions_review` | Questions Planner | Evaluate coverage, create follow-up tasks |
| `aggregation` | Aggregator | Synthesize findings, prepare charts, citations |
| `reporting` | Reporter | Generate HTML/PDF/Excel reports |

### Execution Loop

```
┌──────────────────────────────────────────────────────┐
│                    loop.sh                           │
│                                                      │
│   1. Read state/session.json                         │
│   2. Get current phase                               │
│   3. Call Claude Code with phase-specific prompt     │
│   4. Claude executes phase, updates session.json     │
│   5. Repeat until phase = "complete"                 │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Data Sources

### Crypto Analytics

| Source | Data | API Key |
|--------|------|---------|
| **BlockLens** | BTC on-chain: LTH/STH supply, MVRV, SOPR, UTXO | Required |
| **CoinGecko** | Price history (CSV export), market data | Free |
| **DefiLlama** | TVL, protocol metrics | Free |
| **Etherscan** | Ethereum transactions, contracts | Optional |
| **Dune** | Custom SQL queries | Optional |
| **The Graph** | Subgraph queries | Optional |
| **L2Beat** | Layer 2 metrics | Free |

### Stock & Macro

| Source | Data | API Key |
|--------|------|---------|
| **yFinance** | Stock prices, fundamentals | Free |
| **SEC EDGAR** | Company filings (10-K, 10-Q) | Free |
| **FRED** | Macroeconomic indicators | Free |
| **Finnhub** | Real-time quotes, news | Optional |
| **FMP** | Financial statements | Optional |

### Research

| Source | Data |
|--------|------|
| **World Bank** | Global economic indicators |
| **IMF** | International financial data |
| **Web Search** | News, articles, reports |

## Commands

```bash
# New research
./loop.sh "Your research query"

# Resume latest
./loop.sh --resume

# Resume specific folder
./loop.sh --resume research_btc_market_overview

# Continue with additional context
./loop.sh --continue research_btc "add competitor analysis"

# Show detailed status
./loop.sh --status [folder]

# List all research
./loop.sh --list

# Search by tags/entities/query
./loop.sh --search "keyword"

# Delete research folder
./loop.sh --clear [folder]

# Debug: set phase manually
./loop.sh --set-phase <folder> <phase>
```

## Directory Structure

```
ralph/
├── PROMPT.md                  # State machine definition
├── loop.sh                    # Runner script
├── prompts/                   # Agent prompts
│   ├── initial_research.md
│   ├── brief_builder.md
│   ├── planner.md
│   ├── overview.md
│   ├── data.md
│   ├── research.md
│   ├── questions_planner.md
│   ├── aggregator.md
│   └── reporter.md
├── integrations/              # Data source clients
│   ├── crypto/                # BlockLens, CoinGecko, DefiLlama...
│   ├── stocks/                # yFinance, SEC, FRED...
│   └── research/              # World Bank, IMF...
├── cli/                       # CLI tools
│   └── fetch.py               # Data fetching CLI
├── templates/                 # Report templates
│   ├── html/
│   ├── Warp/                  # Brand assets
│   ├── excel/
│   └── pdf/
└── research_*/                # Research outputs (auto-created)
    ├── state/
    │   ├── session.json       # Single source of truth
    │   ├── brief.json
    │   ├── plan.json
    │   ├── coverage.json
    │   └── aggregation.json
    ├── results/
    │   ├── overview_*.json
    │   ├── data_*.json
    │   ├── research_*.json
    │   └── series/            # Time series data files
    │       ├── BTC_price.json
    │       ├── BTC_LTH_MVRV.json
    │       └── ...
    ├── questions/
    └── output/
        ├── report.html
        ├── report.pdf
        └── data_pack.xlsx
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env`:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional - Data Sources
BLOCKLENS_API_KEY=blk_...     # Bitcoin on-chain analytics
SERPER_API_KEY=...            # Web search
FINNHUB_API_KEY=...           # Real-time stock data
```

### Research Settings

Configured in `state/session.json`:

```json
{
  "preferences": {
    "output_format": "html+excel",
    "style": "default",
    "depth": "standard",
    "audience": "analyst"
  },
  "execution": {
    "max_iterations": 5
  },
  "coverage": {
    "target": 80
  }
}
```

## Output Formats

### HTML Report
- Interactive Plotly charts
- Warp Capital branding
- Table of contents
- Citations with sources
- Responsive design

### PDF Report
- Print-optimized layout
- Static chart images (via Kaleido)
- Professional formatting

### Excel Data Pack
- Raw time series data
- Metric summaries
- Source citations

## Progress Tracking

```
════════════════════════════════════════════════════════════════
                      Ralph Deep Research
════════════════════════════════════════════════════════════════

  Folder: research_btc_market_overview
  Query:  Bitcoin market analysis Q1 2025

  Progress: [████████████████████░░░░░░░░░░░░░░░░░░░░] 45%

  ┌─────────────────────────────────────────────────────────────┐
  │ Phases                                                      │
  ├─────────────────────────────────────────────────────────────┤
  │  ✓ Initial Research
  │  ✓ Brief Builder
  │  ✓ Planning
  │  ● Execution          ← current (iteration 2/5)
  │  ○ Questions Review
  │  ○ Aggregation
  │  ○ Reporting
  │  ○ Complete
  └─────────────────────────────────────────────────────────────┘

  ┌─────────────────────────────────────────────────────────────┐
  │ Coverage: 45% / 80% target                                  │
  ├─────────────────────────────────────────────────────────────┤
  │  █████████░░░░░░░░░░░ price_analysis     45%
  │  ████████████░░░░░░░░ on_chain_metrics   60%
  │  ██████░░░░░░░░░░░░░░ market_sentiment   30%
  └─────────────────────────────────────────────────────────────┘
```

## Requirements

- **Claude Code CLI** with Anthropic API key
- **Bash** (Linux/macOS/WSL)
- **jq** for JSON processing
- **Python 3.10+** (for data fetching CLI)

## Tech Stack

- **Orchestration**: Claude Code (Opus model)
- **State Management**: JSON files (no database)
- **Charts**: Plotly.js
- **Reports**: HTML → PDF (WeasyPrint/Playwright)
- **Data**: Python integrations with rate limiting

## License

MIT License

---

**Built with Claude Code by Warp Capital**
