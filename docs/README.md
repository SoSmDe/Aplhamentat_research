# Ralph Deep Research

**AI-powered research system for comprehensive market analysis reports.**

## What It Does

Ralph автоматически создаёт профессиональные аналитические отчёты:
- Собирает данные из 10+ источников (on-chain, DeFi, price APIs)
- Проводит качественный анализ (новости, мнения экспертов)
- Синтезирует findings в структурированный отчёт
- Генерирует интерактивные графики (Plotly)
- Выводит HTML/PDF отчёт в стиле Warp Capital

## Quick Start

```bash
cd ralph/
./loop.sh "Комплексный обзор рынка Bitcoin"
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER QUERY                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      loop.sh (Runner)                            │
│  - Creates session.json                                          │
│  - Iterates phases until complete                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     State Machine                                │
│                                                                  │
│  initial_research → brief_builder → planning → execution         │
│                                         ↓          ↑             │
│                                    questions_review              │
│                                         ↓                        │
│  (deep_dive only)  chart_analysis → story_lining → editing       │
│                                         ↓                        │
│                                    aggregation → reporting       │
│                                         ↓                        │
│                                      complete                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       OUTPUT                                     │
│  - output/report.html (interactive)                              │
│  - output/charts/*.html (Plotly charts)                          │
│  - state/*.json (all intermediate data)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Documentation

| File | Description |
|------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture and design |
| [PHASES.md](PHASES.md) | State machine phases in detail |
| [AGENTS.md](AGENTS.md) | Agent roles and responsibilities |
| [DATA_SOURCES.md](DATA_SOURCES.md) | API integrations and data sources |
| [STYLE_GUIDE.md](STYLE_GUIDE.md) | Report styling (Warp Capital) |

## Key Features

### Multi-Agent System
- **Overview Agent** — quick context gathering
- **Data Agent** — API calls, on-chain metrics
- **Research Agent** — web search, qualitative analysis
- **Aggregator** — synthesis and recommendations
- **Reporter** — HTML/PDF generation

### Smart Data Collection
- BlockLens API for on-chain (MVRV, NUPL, LTH/STH)
- CoinGecko for prices (CSV export for history)
- DefiLlama for DeFi TVL
- Web search for news and analysis

### Professional Output
- Warp Capital branding and style
- Interactive Plotly charts
- Proper citations with full URLs
- Russian language with correct terminology

## Project Structure

```
ralph/
├── loop.sh                 # Main runner script
├── PROMPT.md               # State machine definition
├── cli/
│   ├── fetch.py            # API client CLI
│   └── render_charts.py    # Chart rendering CLI
├── prompts/                # Agent prompts (11 files)
├── integrations/           # API integrations
├── templates/              # HTML templates (Warp style)
├── references/             # Style references
└── research_XXXXX/         # Per-research output folder
    ├── state/              # Session state files
    ├── results/            # Agent outputs
    ├── questions/          # Generated questions
    └── output/             # Final reports
```

## Technology Stack

- **Runtime**: Claude Code (no Python backend)
- **Charts**: Plotly.js
- **APIs**: BlockLens, CoinGecko, DefiLlama, L2Beat, yfinance
- **Output**: HTML (primary), PDF (optional)
