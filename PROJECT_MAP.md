# PROJECT_MAP.md

## Claude Code Native Workflow

Проект Ralph работает напрямую через Claude Code:
- Встроенный `web_search` tool для исследований
- State сохраняется в JSON файлах (state/)
- Отчеты генерируются через Claude Code (output/)
- Пайплайн описан в PROMPT.md

---

## Дерево файлов проекта

```
ralph/
├── PROMPT.md                        # 265 строк — Главный промпт пайплайна
├── PROMPT_build.md                  # 19 строк — Промпт для сборки
├── PROMPT_plan.md                   # 19 строк — Промпт для планирования
├── loop.sh                          # 178 строк — Скрипт запуска
├── main.py                          # 360 строк — FastAPI (legacy)
├── requirements.txt                 # 37 строк — Python зависимости
├── CLAUDE.md                        # 128 строк — Инструкции для Claude Code
├── AGENTS.md                        # 32 строки — Build & Run инструкции
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
├── src/                             # 1,583 строки
│   ├── __init__.py                  # 16 строк
│   │
│   ├── prompts/                     # 667 строк — Системные промпты агентов
│   │   ├── initial_research.md      # 54 строки
│   │   ├── brief_builder.md         # 91 строка
│   │   ├── planner.md               # 107 строк
│   │   ├── data.md                  # 78 строк
│   │   ├── research.md              # 89 строк
│   │   ├── aggregator.md            # 119 строк
│   │   └── reporter.md              # 129 строк
│   │
│   └── templates/                   # 883 строки — Шаблоны отчетов
│       ├── pdf/
│       │   └── report.html          # 748 строк — Jinja2 шаблон PDF
│       ├── excel/
│       │   └── README.md            # 61 строка
│       └── pptx/
│           └── README.md            # 74 строки
│
├── specs/                           # 5,924 строки — Документация
│   ├── README.md                    # 290 строк
│   ├── ralph_prd.md                 # 1,254 строки — PRD
│   ├── ARCHITECTURE.md              # 1,353 строки
│   ├── DATA_SCHEMAS.md              # 1,482 строки
│   └── PROMPTS.md                   # 1,545 строк
│
└── tests/                           # Тесты (требуют обновления)
    ├── conftest.py
    ├── test_agents/                 # Тесты удаленных агентов
    ├── test_api/                    # Тесты удаленного API
    ├── test_orchestrator/           # Тесты удаленного оркестратора
    ├── test_storage/                # Тесты удаленного storage
    └── test_tools/                  # Частично актуальны
```

---

## Описание файлов

### Корневые файлы (1,038 строк)

| Файл | Строк | Описание |
|------|-------|----------|
| `PROMPT.md` | 265 | Главный промпт пайплайна Ralph для Claude Code |
| `PROMPT_build.md` | 19 | Промпт для сборки проекта |
| `PROMPT_plan.md` | 19 | Промпт для планирования |
| `loop.sh` | 178 | Скрипт запуска и управления итерациями |
| `main.py` | 360 | FastAPI приложение (legacy, для веб-интерфейса) |
| `requirements.txt` | 37 | Python зависимости |
| `CLAUDE.md` | 128 | Инструкции для Claude Code |
| `AGENTS.md` | 32 | Build & Run инструкции |

---

### src/prompts/ — Системные промпты агентов (667 строк)

| Файл | Строк | Описание |
|------|-------|----------|
| `initial_research.md` | 54 | Быстрый сбор контекста, парсинг запроса |
| `brief_builder.md` | 91 | Интерактивный диалог для формирования ТЗ |
| `planner.md` | 107 | Декомпозиция на задачи, проверка покрытия |
| `data.md` | 78 | Сбор структурированных данных через API |
| `research.md` | 89 | Качественный анализ через web_search |
| `aggregator.md` | 119 | Синтез находок и формирование рекомендаций |
| `reporter.md` | 129 | Генерация PDF/Excel/PPTX отчетов |

---

### src/templates/ — Шаблоны отчетов (883 строки)

| Файл | Строк | Описание |
|------|-------|----------|
| `pdf/report.html` | 748 | Jinja2 шаблон для PDF (WeasyPrint) |
| `excel/README.md` | 61 | Документация Excel шаблонов |
| `pptx/README.md` | 74 | Документация PowerPoint шаблонов |

---

### specs/ — Документация (5,924 строки)

| Файл | Строк | Описание |
|------|-------|----------|
| `README.md` | 290 | Обзор проекта |
| `ralph_prd.md` | 1,254 | Product Requirements Document |
| `ARCHITECTURE.md` | 1,353 | Техническая архитектура |
| `DATA_SCHEMAS.md` | 1,482 | JSON Schema и TypeScript типы |
| `PROMPTS.md` | 1,545 | Системные промпты (справка) |

---

## Сводная статистика

| Метрика | Значение |
|---------|----------|
| Всего строк (активный код) | ~2,621 |
| src/ | 1,583 строки |
| Корневые файлы | 1,038 строк |
| specs/ (документация) | 5,924 строки |
| **Экономия vs оригинал** | **~84%** |

### Распределение по модулям

| Модуль | Строк | % |
|--------|-------|---|
| `PROMPT*.md` | 303 | 12% |
| `src/prompts/` | 667 | 25% |
| `src/templates/` | 883 | 34% |
| `loop.sh + main.py` | 538 | 20% |
| Прочее | 230 | 9% |

---

## Удаленные модули (Claude Code делает это нативно)

| Модуль | Строк | Причина |
|--------|-------|---------|
| `src/agents/` | ~1,700 | Логика в PROMPT.md + src/prompts/ |
| `src/api/` | ~1,500 | FastAPI не нужен для Claude Code |
| `src/tools/` | ~1,500 | Claude Code имеет web_search, file ops |
| `src/storage/` | ~1,700 | State через JSON файлы |
| `src/config/` | ~370 | Конфигурация не нужна |
| `src/orchestrator/` | ~1,700 | Логика в PROMPT.md |
| **Итого** | **~8,470** | |

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      loop.sh                                │
│   Управляет итерациями, проверяет completion               │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Claude Code                              │
│   Читает PROMPT.md + src/prompts/*.md                      │
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

*Документ обновлен: 2026-01-19*
