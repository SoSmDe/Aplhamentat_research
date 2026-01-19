# PROJECT_MAP.md

## Архитектура проекта

Проект Alphamentat Research Bot с разделением:
- `ralph/` — Core движок (Claude Code native)
- `src/` — Общие ресурсы (промпты, шаблоны)
- Placeholders для будущих интеграций

---

## Дерево файлов

```
Alphamentat_research_bot/
│
├── ralph/                           # Core движок
│   ├── PROMPT.md                    # Главный pipeline
│   ├── loop.sh                      # Runner script
│   ├── CLAUDE.md                    # Инструкции для Claude Code
│   ├── AGENTS.md                    # Краткая справка
│   ├── PROJECT_MAP.md               # Этот файл
│   │
│   └── research_YYYYMMDD_HHMMSS_*/  # Per-research folders (gitignored)
│       ├── state/                   # JSON state files
│       ├── results/                 # Agent outputs
│       ├── questions/               # Generated questions
│       └── output/                  # Final reports
│
├── src/                             # Общие ресурсы
│   ├── prompts/                     # 9 промптов агентов
│   │   ├── initial_research.md
│   │   ├── brief_builder.md
│   │   ├── planner.md
│   │   ├── overview.md              # Deep Research skill
│   │   ├── data.md
│   │   ├── research.md
│   │   ├── questions_planner.md     # Фильтрация вопросов
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
└── task.md                          # Task instructions
```

---

## Описание компонентов

### ralph/ — Core движок

| Файл | Описание |
|------|----------|
| `PROMPT.md` | Главный pipeline с 8 фазами |
| `loop.sh` | Runner script с генерацией research folders |
| `CLAUDE.md` | Инструкции для Claude Code |
| `AGENTS.md` | Краткая справка по запуску |
| `PROJECT_MAP.md` | Карта проекта |

### src/prompts/ — Системные промпты (9 файлов)

| Файл | Описание |
|------|----------|
| `initial_research.md` | Быстрый сбор контекста |
| `brief_builder.md` | Интерактивный диалог для ТЗ |
| `planner.md` | Декомпозиция + coverage check |
| `overview.md` | **NEW** — Deep Research skill (8 фаз) |
| `data.md` | Сбор структурированных данных |
| `research.md` | Качественный анализ |
| `questions_planner.md` | **NEW** — Фильтрация вопросов по приоритету |
| `aggregator.md` | Синтез и рекомендации |
| `reporter.md` | Генерация отчетов |

### src/templates/ — Шаблоны отчетов

| Папка | Описание |
|-------|----------|
| `pdf/report.html` | Jinja2 шаблон для PDF |
| `excel/` | Excel шаблоны (placeholder) |
| `pptx/` | PowerPoint шаблоны (placeholder) |

---

## Pipeline (обновленный)

```
User Query
    │
    ▼
Initial Research
    │
    ▼
Brief Builder
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
│   Questions Planner                 │
│   (filter by priority)              │
│           │                         │
│           ▼                         │
│   Coverage Check (≥80%?)            │
│           │                         │
│           └── Loop if needed        │
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

# Проверить статус
./loop.sh --status

# Продолжить последнее
./loop.sh --resume

# Продолжить конкретное
./loop.sh --resume research_20260119_realty_income

# Очистить
./loop.sh --clear research_20260119_realty_income
```

---

## Research Folder Structure

Каждое исследование создает папку `research_YYYYMMDD_HHMMSS_slug/`:

```
research_20260119_143052_realty_income/
├── state/
│   ├── session.json
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

## Placeholders для будущего

| Папка | Назначение |
|-------|------------|
| `frontend/` | React веб-интерфейс |
| `telegram/` | Telegram bot интеграция |
| `api/` | FastAPI REST API layer |

---

*Документ обновлен: 2026-01-19*
