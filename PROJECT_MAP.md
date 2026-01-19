# PROJECT_MAP.md (Post-Refactoring)

## Claude Code Native Workflow

После рефакторинга проект работает напрямую через Claude Code:
- Встроенный `web_search` tool для исследований
- State сохраняется в JSON файлах
- Отчеты генерируются через Claude Code

## Дерево файлов проекта

```
ralph/
├── main.py                          # FastAPI (legacy, опционально)
├── PROMPT.md                        # Главный промпт пайплайна
├── loop.sh                          # Скрипт запуска
├── requirements.txt                 # Python зависимости
├── CLAUDE.md                        # Инструкции для Claude Code
├── PROJECT_MAP.md                   # Этот файл
│
├── state/                           # Состояние исследования (JSON)
│   ├── session.json
│   ├── initial_context.json
│   ├── conversation.json
│   ├── brief.json
│   ├── plan.json
│   ├── coverage.json
│   ├── round_N/
│   │   ├── data_results.json
│   │   └── research_results.json
│   ├── aggregation.json
│   └── report_config.json
│
├── output/                          # Сгенерированные отчеты
│   ├── report.pdf
│   ├── report.xlsx
│   └── report.pptx
│
├── src/
│   ├── __init__.py
│   │
│   ├── agents/                      # AI Агенты (prompt-driven)
│   │   ├── __init__.py              # 57 строк
│   │   ├── base.py                  # 386 строк - StateManager, BaseAgent
│   │   ├── initial_research.py      # 144 строки
│   │   ├── brief_builder.py         # 169 строк
│   │   ├── planner.py               # 202 строки
│   │   ├── data.py                  # 164 строки
│   │   ├── research.py              # 183 строки
│   │   ├── aggregator.py            # 201 строка
│   │   └── reporter.py              # 192 строки
│   │
│   ├── api/                         # FastAPI (опционально)
│   │   ├── __init__.py
│   │   ├── routes.py                # 585 строк
│   │   ├── schemas.py               # 788 строк - Pydantic модели
│   │   └── dependencies.py          # 140 строк
│   │
│   ├── tools/                       # Инструменты (минимальный набор)
│   │   ├── __init__.py              # 107 строк
│   │   ├── errors.py                # 570 строк - Иерархия ошибок
│   │   ├── logging.py               # 253 строки
│   │   └── db_client.py             # 573 строки
│   │
│   ├── storage/                     # Хранение данных
│   │   ├── __init__.py
│   │   ├── database.py              # 443 строки
│   │   ├── session.py               # 813 строк
│   │   └── files.py                 # 418 строк
│   │
│   ├── config/                      # Конфигурация
│   │   ├── __init__.py
│   │   ├── settings.py              # 158 строк
│   │   ├── models.py                # 56 строк
│   │   └── timeouts.py              # 104 строки
│   │
│   ├── prompts/                     # Системные промпты агентов
│   │   ├── aggregator.md
│   │   ├── brief_builder.md
│   │   ├── data.md
│   │   ├── initial_research.md
│   │   ├── planner.md
│   │   ├── reporter.md
│   │   └── research.md
│   │
│   └── templates/                   # Шаблоны отчетов
│       └── pdf/
│           └── report.html          # Jinja2 шаблон PDF
│
├── specs/                           # Документация
│   ├── README.md
│   ├── ralph_prd.md
│   ├── ARCHITECTURE.md
│   ├── DATA_SCHEMAS.md
│   └── PROMPTS.md
│
└── tests/                           # Тесты
    ├── test_agents/
    ├── test_api/
    ├── test_storage/
    └── test_tools/                  # Только errors, logging, db_client
```

---

## Удаленные файлы (Claude Code делает это нативно)

| Файл | Строк | Причина удаления |
|------|-------|------------------|
| `src/tools/llm.py` | 620 | Claude Code = Claude API |
| `src/tools/web_search.py` | 589 | Встроенный web_search tool |
| `src/tools/api_client.py` | 635 | Claude делает HTTP напрямую |
| `src/tools/retry.py` | 653 | Claude обрабатывает retry |
| `src/tools/file_generator.py` | 885 | Claude генерирует файлы |
| `src/orchestrator/pipeline.py` | 1131 | Логика в PROMPT.md |
| `src/orchestrator/parallel.py` | 568 | Не нужен для Claude Code |
| **Итого удалено** | **~5,081** | |

---

## Описание файлов по модулям

### Корневые файлы

| Файл | Строк | Описание |
|------|-------|----------|
| `PROMPT.md` | ~250 | Главный промпт пайплайна Ralph для Claude Code |
| `loop.sh` | ~180 | Скрипт запуска и управления итерациями |
| `main.py` | 360 | FastAPI приложение (опционально, для веб-интерфейса) |

---

### src/agents/ — AI Агенты (Claude Code Native)

**Всего: ~1,698 строк** (было 5,155)

| Файл | Строк | Описание | Ключевые классы |
|------|-------|----------|-----------------|
| `base.py` | 386 | StateManager для JSON state, BaseAgent с промптами | `StateManager`, `BaseAgent`, `StateFiles` |
| `initial_research.py` | 144 | Быстрый сбор контекста через web_search | `InitialResearchAgent`, `InitialResearchOutput` |
| `brief_builder.py` | 169 | Интерактивный диалог для спецификации | `BriefBuilderAgent`, `BriefOutput` |
| `planner.py` | 202 | Декомпозиция на задачи, проверка покрытия | `PlannerAgent`, `PlanOutput`, `CoverageCheckOutput` |
| `data.py` | 164 | Сбор структурированных данных | `DataAgent`, `DataResultsOutput` |
| `research.py` | 183 | Качественный анализ через web_search | `ResearchAgent`, `ResearchResultsOutput` |
| `aggregator.py` | 201 | Синтез и рекомендации | `AggregatorAgent`, `AggregationOutput` |
| `reporter.py` | 192 | Генерация PDF/Excel/PPTX | `ReporterAgent`, `ReporterOutput` |

---

### src/tools/ — Инструменты (минимальный набор)

**Всего: ~1,503 строки** (было 5,778)

| Файл | Строк | Описание |
|------|-------|----------|
| `errors.py` | 570 | Иерархия ошибок (TransientError, PermanentError, SystemError) |
| `logging.py` | 253 | Structured logging через structlog |
| `db_client.py` | 573 | Read-only клиент БД для внешних данных |
| `__init__.py` | 107 | Экспорты |

---

### src/api/ — API Layer (опционально)

**Всего: 1,524 строки**

| Файл | Строк | Описание |
|------|-------|----------|
| `routes.py` | 585 | FastAPI endpoints (если нужен веб-интерфейс) |
| `schemas.py` | 788 | 50+ Pydantic моделей — структуры данных |
| `dependencies.py` | 140 | Dependency Injection |

---

### src/storage/ — Хранение данных

**Всего: 1,688 строк**

| Файл | Строк | Описание |
|------|-------|----------|
| `database.py` | 443 | Async SQLite (для веб-интерфейса) |
| `session.py` | 813 | SessionManager для SQLite state |
| `files.py` | 418 | Управление файлами отчетов |

---

### templates/ — Шаблоны

| Файл | Описание |
|------|----------|
| `templates/pdf/report.html` | Jinja2 шаблон для PDF отчетов (WeasyPrint) |

---

## Сводная статистика

### До рефакторинга
| Метрика | Значение |
|---------|----------|
| Всего строк (src/) | ~16,254 |
| Файлов .py | ~35 |

### После рефакторинга
| Метрика | Значение |
|---------|----------|
| Всего строк (src/) | ~8,300 |
| Файлов .py | ~25 |
| **Экономия** | **~49%** |

### Распределение по модулям (после)

| Модуль | Строк | % |
|--------|-------|---|
| `agents/` | 1,698 | 20% |
| `tools/` | 1,503 | 18% |
| `storage/` | 1,688 | 20% |
| `api/` | 1,524 | 18% |
| `config/` | 369 | 5% |
| Прочее | ~1,500 | 19% |

---

## Архитектура Claude Code Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                      loop.sh                                │
│   Управляет итерациями, проверяет completion               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code                              │
│   Читает PROMPT.md, выполняет пайплайн                     │
└─────────────────────────┬───────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    web_search      Write/Read        State JSON
    (built-in)       (files)          (state/)
                          │
                          ▼
                    output/*.pdf
                    output/*.xlsx
                    output/*.pptx
```

---

## Workflow

```
User Query
    │
    ▼
Initial Research (web_search → state/initial_context.json)
    │
    ▼
Brief Builder (dialog → state/brief.json)
    │
    ▼
┌─────────────────────────────────────┐
│            Research Loop            │
│   Planner → Data + Research         │
│   → Coverage Check → (repeat?)      │
│   state/round_N/*.json              │
└─────────────────────────────────────┘
    │
    ▼
Aggregator (→ state/aggregation.json)
    │
    ▼
Reporter (→ output/report.*)
    │
    ▼
<promise>COMPLETE</promise>
```

---

## Запуск

```bash
# Новое исследование
./loop.sh "Analyze Realty Income Corporation for investment"

# Проверить статус
./loop.sh --status

# Продолжить
./loop.sh --resume

# Очистить и начать заново
./loop.sh --clear
```

---

*Документ обновлен: 2026-01-19 (после рефакторинга для Claude Code)*
