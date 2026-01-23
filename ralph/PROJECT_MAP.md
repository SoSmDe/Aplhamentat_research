# PROJECT_MAP.md

## Архитектура проекта

Проект Alphamentat Research Bot — Claude Code native State Machine.
- `ralph/` — Core движок (промпты, интеграции, CLI, шаблоны)
- Placeholders для будущих интеграций (frontend, telegram, api)

---

## Дерево файлов

```
Alphamentat_research_bot/
│
├── ralph/                           # Core движок
│   ├── PROMPT.md                    # State Machine definition (12 фаз)
│   ├── loop.sh                      # Runner script с Progress Tracker
│   ├── CLAUDE.md                    # Инструкции для Claude Code
│   ├── AGENTS.md                    # Краткая справка
│   ├── PROJECT_MAP.md               # Этот файл
│   │
│   ├── prompts/                     # 15 промптов агентов
│   │   ├── initial_research.md      # + Tags & Entities extraction
│   │   ├── brief_builder.md         # Auto-mode генерация Brief
│   │   ├── planner.md               # Декомпозиция Brief в tasks
│   │   ├── overview.md              # Deep Research skill (9 фаз)
│   │   ├── data.md                  # Структурированные данные via CLI
│   │   ├── research.md              # Качественный анализ
│   │   ├── literature.md            # Академические статьи (science domain)
│   │   ├── fact_check.md            # Верификация фактов (general domain)
│   │   ├── questions_planner.md     # Фильтрация + Coverage check
│   │   ├── aggregator.md            # Синтез и рекомендации
│   │   ├── story_liner.md           # Планирование layout отчета
│   │   ├── visual_designer.md       # Кастомная инфографика
│   │   ├── chart_analyzer.md        # Анализ временных рядов (deep_dive)
│   │   ├── reporter.md              # Генерация HTML отчетов
│   │   └── editor.md                # Финальная редактура (deep_dive)
│   │
│   ├── templates/                   # Шаблоны отчетов
│   │   ├── default.html             # Стандартный шаблон
│   │   └── warp.html                # Альтернативный стиль
│   │
│   ├── cli/                         # CLI утилиты
│   │   ├── fetch.py                 # Data Fetch CLI
│   │   └── render_charts.py         # Plotly chart renderer
│   │
│   ├── integrations/                # API интеграции
│   │   ├── core/                    # Resource tracking
│   │   │   ├── tracker.py           # API/LLM metrics tracker
│   │   │   ├── pricing.py           # Cost calculation
│   │   │   ├── http_wrapper.py      # HTTP request patching
│   │   │   ├── llm_estimator.py     # Token estimation
│   │   │   └── metrics_aggregator.py # Summary generation
│   │   │
│   │   ├── crypto/                  # Crypto APIs
│   │   │   ├── coingecko.py
│   │   │   ├── blocklens.py
│   │   │   ├── defillama.py
│   │   │   ├── l2beat.py
│   │   │   ├── etherscan.py
│   │   │   ├── thegraph.py
│   │   │   └── dune.py
│   │   │
│   │   ├── stocks/                  # Stock market APIs
│   │   │   ├── yfinance_client.py
│   │   │   ├── finnhub.py
│   │   │   ├── fred.py
│   │   │   ├── sec_edgar.py
│   │   │   └── fmp.py
│   │   │
│   │   ├── research/                # Research APIs
│   │   │   ├── serper.py            # Web search
│   │   │   ├── arxiv.py             # Academic papers
│   │   │   ├── pubmed.py            # Medical research
│   │   │   ├── wikipedia.py
│   │   │   ├── worldbank.py
│   │   │   ├── imf.py
│   │   │   ├── crunchbase.py        # Startup/company data
│   │   │   ├── sec_edgar.py         # SEC filings
│   │   │   ├── google_scholar.py    # Academic search
│   │   │   └── news_aggregator.py   # News APIs
│   │   │
│   │   ├── general/                 # General purpose
│   │   │   └── wikidata.py
│   │   │
│   │   └── analytics/               # Data analysis
│   │       └── series_analyzer.py   # Time series analysis
│   │
│   └── research_YYYYMMDD_HHMMSS_*/  # Per-research folders (gitignored)
│       ├── state/
│       │   ├── session.json         # <- Single source of truth
│       │   ├── initial_context.json
│       │   ├── brief.json
│       │   ├── plan.json
│       │   ├── coverage.json
│       │   ├── questions_plan.json
│       │   ├── aggregation.json
│       │   ├── citations.json       # Источники
│       │   ├── glossary.json        # Глоссарий
│       │   ├── chart_data.json      # Данные для чартов
│       │   ├── charts_analyzed.json # (deep_dive only)
│       │   ├── story.json           # Layout blueprint
│       │   ├── visuals.json         # Спецификации инфографики
│       │   ├── editor_log.json      # (deep_dive only)
│       │   └── metrics.json         # Resource tracking
│       ├── results/                 # Agent outputs
│       │   └── series/              # Time series data
│       ├── questions/               # Generated questions
│       └── output/
│           ├── report.html          # Primary output
│           ├── charts/              # Plotly charts (deep_dive)
│           └── visuals/             # Custom infographics
│
├── frontend/                        # Placeholder для React
│   └── .gitkeep
│
├── telegram/                        # Placeholder для Telegram bot
│   └── .gitkeep
│
├── api/                             # Placeholder для API layer
│   └── .gitkeep
│
└── .gitignore
```

---

## Описание компонентов

### ralph/ — Core движок

| Файл | Описание |
|------|----------|
| `PROMPT.md` | State Machine с 12 фазами |
| `loop.sh` | Runner с Progress Tracker и Search |
| `CLAUDE.md` | Инструкции для Claude Code |
| `AGENTS.md` | Краткая справка по запуску |
| `PROJECT_MAP.md` | Карта проекта |

### prompts/ — Системные промпты (15 файлов)

Каждый промпт содержит стандартные секции:
- **Input** — что читать
- **Process** — что делать
- **Output** — что сохранять (JSON структура)
- **Update session.json** — какую фазу поставить

| Файл | Описание |
|------|----------|
| `initial_research.md` | Быстрый сбор контекста + Tags & Entities |
| `brief_builder.md` | Auto-mode генерация Brief |
| `planner.md` | Декомпозиция Brief в tasks |
| `overview.md` | Deep Research skill (9 фаз) |
| `data.md` | Сбор структурированных данных via CLI |
| `research.md` | Качественный анализ |
| `literature.md` | Академические статьи (arxiv, pubmed) |
| `fact_check.md` | Верификация фактов |
| `questions_planner.md` | Фильтрация вопросов + Coverage |
| `aggregator.md` | Синтез, триангуляция, рекомендации |
| `story_liner.md` | Планирование layout отчета |
| `visual_designer.md` | Кастомная инфографика (SWOT, timelines) |
| `chart_analyzer.md` | Анализ временных рядов (deep_dive) |
| `reporter.md` | Генерация HTML отчетов |
| `editor.md` | Финальная редактура (deep_dive) |

### integrations/ — API интеграции

| Модуль | APIs |
|--------|------|
| `core/` | Resource tracking (metrics, costs) |
| `crypto/` | CoinGecko, BlockLens, DeFiLlama, L2Beat, Etherscan, TheGraph, Dune |
| `stocks/` | yFinance, Finnhub, FRED, SEC EDGAR, FMP |
| `research/` | Serper, arXiv, PubMed, Wikipedia, World Bank, IMF, Crunchbase |
| `general/` | Wikidata |
| `analytics/` | Series analyzer (trends, stats, anomalies) |

---

## State Machine Pipeline

```
ALL depths:
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → story_lining → visual_design → reporting → complete

Deep Dive additions (depth: deep_dive):
... → aggregation → [chart_analysis] → story_lining → visual_design → reporting → editing → complete
```

Детальная схема:
```
User Query
    │
    ▼
Initial Research (+ extract tags & entities)
    │
    ▼
Brief Builder (auto-mode)
    │
    ▼
Planning
    │
    ▼
┌─────────────────────────────────────┐
│         EXECUTION LOOP              │
│   (max 5 iterations)                │
│                                     │
│   Overview (Deep Research) ──┐      │
│   Data ─────────────────────┤      │
│   Research ─────────────────┤      │
│   Literature ───────────────┤      │
│   Fact Check ───────────────┘      │
│           │                         │
│           ▼                         │
│   Questions Review                  │
│   (filter + coverage check)         │
│           │                         │
│           ▼                         │
│   Coverage ≥80%? ─────── No ───┐   │
│           │                     │   │
│          Yes                    │   │
│           └─────────────────────┘   │
└─────────────────────────────────────┘
    │
    ▼
Aggregator
    │
    ▼
[Chart Analysis] ← only if deep_dive + series/
    │
    ▼
Story Liner (ALL depths)
    │
    ▼
Visual Designer (ALL depths)
    │
    ▼
Reporter
    │
    ▼
[Editor] ← only if deep_dive
    │
    ▼
<promise>COMPLETE</promise>
```

---

## Запуск

```bash
cd ralph/

# Новое исследование
./loop.sh "Analyze Realty Income Corporation for investment"

# Список исследований
./loop.sh --list

# Проверить статус (с Progress Bar)
./loop.sh --status

# Поиск по тегам/сущностям
./loop.sh --search "reit"
./loop.sh --search "investment"

# Продолжить последнее
./loop.sh --resume

# Продолжить конкретное
./loop.sh --resume research_20260119_realty_income

# Очистить
./loop.sh --clear research_20260119_realty_income

# Debug: установить фазу вручную
./loop.sh --set-phase research_20260119_realty_income execution
```

---

## session.json Structure

```json
{
  "id": "research_20260119_143052_realty_income",
  "query": "Analyze Realty Income Corporation for investment",
  "language": "en",
  "phase": "execution",
  "domain": "finance",
  "domain_secondary": "business",
  "domain_confidence": "high",

  "tags": ["investment", "reit", "real-estate", "dividend"],
  "entities": [
    {"name": "Realty Income Corporation", "type": "company", "ticker": "O"},
    {"name": "REIT", "type": "sector"},
    {"name": "S&P 500", "type": "index"}
  ],

  "preferences": {
    "depth": "standard",
    "tone": "neutral_business",
    "style": "default",
    "audience": "analysts",
    "output_format": "html"
  },

  "execution": {
    "iteration": 2,
    "max_iterations": 5,
    "tasks_pending": ["d3", "r2", "l1"],
    "tasks_completed": ["o1", "d1", "d2", "r1", "f1"]
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

  "created_at": "2026-01-19T14:30:52+03:00",
  "updated_at": "2026-01-19T15:45:30+03:00"
}
```

---

## Research Folder Structure

Каждое исследование создает папку `research_YYYYMMDD_HHMMSS_slug/`:

```
research_20260119_143052_realty_income/
├── state/
│   ├── session.json         # <- Single source of truth
│   ├── initial_context.json
│   ├── brief.json
│   ├── plan.json
│   ├── questions_plan.json
│   ├── coverage.json
│   ├── aggregation.json
│   ├── citations.json
│   ├── glossary.json
│   ├── chart_data.json
│   ├── charts_analyzed.json # (deep_dive only)
│   ├── story.json           # Layout blueprint
│   ├── visuals.json         # Infographic specs
│   ├── editor_log.json      # (deep_dive only)
│   └── metrics.json         # Resource tracking
│
├── results/
│   ├── overview_1.json
│   ├── data_1.json
│   ├── research_1.json
│   ├── literature_1.json
│   ├── fact_check_1.json
│   └── series/              # Time series data
│       └── *.json
│
├── questions/
│   ├── overview_questions.json
│   ├── data_questions.json
│   ├── research_questions.json
│   ├── literature_questions.json
│   └── fact_check_questions.json
│
└── output/
    ├── report.html          # Primary output
    ├── charts/              # Plotly charts (deep_dive)
    └── visuals/             # Custom infographics
```

---

## Features

### Progress Tracker
`--status` показывает визуальный прогресс:
- Progress bar с процентами
- Список фаз с маркером текущей
- Coverage bars по scope items
- Статус выполнения tasks
- Tags и entities
- Статус output файлов

### Tagging & Search
- Автоматическое извлечение tags и entities в initial_research
- Поиск по всем исследованиям: query, tags, entity names
- Tags: investment, reit, tech, dividend, etc.
- Entities: companies, sectors, indices, concepts

### Quality Assurance
- Source quality tiers (tier_1 → tier_5)
- Data freshness tracking (fresh → outdated)
- Triangulation of sources
- Self-calculation verification

### Resource Tracking
- API call metrics (endpoint, duration, status)
- LLM token estimation
- Cost calculation per module
- Session-level aggregation

---

## Placeholders для будущего

| Папка | Назначение |
|-------|------------|
| `frontend/` | React веб-интерфейс |
| `telegram/` | Telegram bot интеграция |
| `api/` | FastAPI REST API layer |

---

*Документ обновлен: 2026-01-23*
