# PROJECT_MAP.md

## Архитектура проекта

Проект Alphamentat Research Bot с разделением:
- `ralph/` — Core движок (Claude Code native, State Machine)
- `src/` — Общие ресурсы (промпты, шаблоны)
- Placeholders для будущих интеграций

---

## Дерево файлов

```
Alphamentat_research_bot/
│
├── ralph/                           # Core движок
│   ├── PROMPT.md                    # State Machine definition
│   ├── loop.sh                      # Runner script с Progress Tracker
│   ├── CLAUDE.md                    # Инструкции для Claude Code
│   ├── AGENTS.md                    # Краткая справка
│   ├── PROJECT_MAP.md               # Этот файл
│   │
│   └── research_YYYYMMDD_HHMMSS_*/  # Per-research folders (gitignored)
│       ├── state/
│       │   ├── session.json         # <- Single source of truth
│       │   ├── initial_context.json
│       │   ├── brief.json
│       │   ├── plan.json
│       │   ├── coverage.json
│       │   ├── questions_plan.json
│       │   └── aggregation.json
│       ├── results/                 # Agent outputs
│       ├── questions/               # Generated questions
│       └── output/                  # Final reports
│
├── src/                             # Общие ресурсы
│   ├── prompts/                     # 9 промптов агентов
│   │   ├── initial_research.md      # + Tags & Entities extraction
│   │   ├── brief_builder.md         # Auto-mode (no user dialog)
│   │   ├── planner.md
│   │   ├── overview.md              # Deep Research skill (9 фаз)
│   │   ├── data.md
│   │   ├── research.md
│   │   ├── questions_planner.md     # Фильтрация + Coverage check
│   │   ├── aggregator.md
│   │   └── reporter.md
│   │
│   └── templates/
│       ├── pdf/
│       │   └── report.html
│       ├── excel/
│       │   └── README.md
│       └── pptx/
│           └── README.md
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
├── .gitignore
├── Task1.md                         # State Machine refactoring task
└── Task2.md                         # Progress Tracker & Search task
```

---

## Описание компонентов

### ralph/ — Core движок

| Файл | Описание |
|------|----------|
| `PROMPT.md` | State Machine с 8 фазами |
| `loop.sh` | Runner с Progress Tracker и Search |
| `CLAUDE.md` | Инструкции для Claude Code |
| `AGENTS.md` | Краткая справка по запуску |
| `PROJECT_MAP.md` | Карта проекта |

### src/prompts/ — Системные промпты (9 файлов)

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
| `data.md` | Сбор структурированных данных |
| `research.md` | Качественный анализ |
| `questions_planner.md` | Фильтрация вопросов + Coverage |
| `aggregator.md` | Синтез и рекомендации |
| `reporter.md` | Генерация отчетов |

### src/templates/ — Шаблоны отчетов

| Папка | Описание |
|-------|----------|
| `pdf/report.html` | Jinja2 шаблон для PDF |
| `excel/` | Excel шаблоны (placeholder) |
| `pptx/` | PowerPoint шаблоны (placeholder) |

---

## State Machine Pipeline

```
initial_research → brief_builder → planning → execution ⟷ questions_review → aggregation → reporting → complete
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
│   Research ─────────────────┘      │
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
Reporter
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
  "phase": "execution",

  "tags": ["investment", "reit", "real-estate", "dividend"],
  "entities": [
    {"name": "Realty Income Corporation", "type": "company", "ticker": "O"},
    {"name": "REIT", "type": "sector"},
    {"name": "S&P 500", "type": "index"}
  ],

  "execution": {
    "iteration": 2,
    "max_iterations": 5,
    "tasks_pending": ["d3", "r2"],
    "tasks_completed": ["o1", "d1", "d2", "r1"]
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
│   └── aggregation.json
│
├── results/
│   ├── overview_1.json
│   ├── data_1.json
│   └── research_1.json
│
├── questions/
│   ├── overview_questions.json
│   ├── data_questions.json
│   └── research_questions.json
│
└── output/
    ├── report.pdf
    ├── report.xlsx
    └── report.pptx
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

---

## Placeholders для будущего

| Папка | Назначение |
|-------|------------|
| `frontend/` | React веб-интерфейс |
| `telegram/` | Telegram bot интеграция |
| `api/` | FastAPI REST API layer |

---

*Документ обновлен: 2026-01-19*
