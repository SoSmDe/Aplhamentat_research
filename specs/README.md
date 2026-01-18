# Ralph Deep Research

**Автономный AI-агент для глубокого исследования с генерацией профессиональных отчётов**

Ralph — это multi-agent система, которая принимает запрос пользователя, проводит комплексное исследование из множества источников (веб, API, базы данных, документы) и генерирует структурированные отчёты в нужном формате.

## Ключевые особенности

- 🔍 **Initial Research** — быстрый первичный ресёрч для понимания контекста темы
- 💬 **Brief Builder** — интерактивное уточнение задачи с пользователем
- 🔄 **Итеративный сбор данных** — агенты сами добавляют задачи по ходу исследования
- ⚡ **Параллельная работа** — Data и Research агенты работают одновременно
- 📊 **Мульти-форматные отчёты** — PDF, Excel, PowerPoint, CSV
- 🔌 **Расширяемые источники** — легко добавлять новые API и базы данных

## Архитектура

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────┐
│        INITIAL RESEARCH                 │
│  Быстрый ресёрч по сырому запросу       │
│  Output: initial_context.json           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│        BRIEF BUILDER (Opus)             │
│  Уточняет задачу, формирует ТЗ          │
│  Output: approved_brief.json            │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           PLANNER (Opus)                │
│  Генерирует data_tasks + research_tasks │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┐
        ▼                 ▼
┌───────────────┐ ┌───────────────────┐
│ DATA (Sonnet) │ │  RESEARCH (Opus)  │
│ API, метрики  │ │  анализ, синтез   │
└───────┬───────┘ └─────────┬─────────┘
        │      PARALLEL     │
        └────────┬──────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│           PLANNER (Opus)                │
│  Проверяет coverage → loop или done     │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         AGGREGATOR (Opus)               │
│  Собирает всё, пишет выводы             │
│  Output: aggregated_research.json       │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│          REPORTER (Opus)                │
│  Генерирует PDF/Excel/PPTX              │
│  Output: report files                   │
└────────────────┬────────────────────────┘
                 │
                 ▼
            USER OUTPUT
```

## Быстрый старт

### Требования

- Python 3.11+
- Node.js 18+ (для frontend)
- Anthropic API key

### Установка

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/ralph-research.git
cd ralph-research

# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..

# Настройка
cp .env.example .env
# Добавить ANTHROPIC_API_KEY в .env
```

### Запуск

```bash
# Backend (терминал 1)
uvicorn main:app --reload --port 8000

# Frontend (терминал 2)
cd frontend && npm run dev
```

Открыть http://localhost:3000

## Структура проекта

```
ralph/
├── api/                    # FastAPI endpoints
│   ├── routes.py
│   └── schemas.py
│
├── agents/                 # AI агенты
│   ├── base.py            # Базовый класс
│   ├── initial_research.py # Первичный ресёрч
│   ├── brief_builder.py   # Формирование ТЗ
│   ├── planner.py         # Планирование задач
│   ├── data.py            # Сбор данных
│   ├── research.py        # Глубокий анализ
│   ├── aggregator.py      # Синтез результатов
│   └── reporter.py        # Генерация отчётов
│
├── orchestrator/          # Координация агентов
│   ├── pipeline.py        # Основной pipeline
│   └── parallel.py        # Параллельное выполнение
│
├── tools/                 # Инструменты агентов
│   ├── api_client.py      # Внешние API
│   ├── web_search.py      # Веб-поиск
│   ├── db_client.py       # База данных
│   └── llm.py             # Claude API wrapper
│
├── storage/               # Хранение данных
│   ├── session.py         # Состояние сессии
│   └── files.py           # Файлы результатов
│
├── templates/             # Шаблоны отчётов
│   ├── pdf/
│   ├── excel/
│   └── pptx/
│
├── prompts/               # Промпты агентов
│   ├── initial_research.md
│   ├── brief_builder.md
│   ├── planner.md
│   ├── data.md
│   ├── research.md
│   ├── aggregator.md
│   └── reporter.md
│
├── frontend/              # React приложение
│   └── src/
│
├── main.py               # Entry point
├── requirements.txt
└── README.md
```

## Модели

| Агент | Модель | Причина |
|-------|--------|---------|
| Initial Research | Deep Research API | Быстрый обзор темы |
| Brief Builder | Claude Opus | Reasoning для уточнения задачи |
| Planner | Claude Opus | Критичный этап планирования |
| Data | Claude Sonnet | Простые задачи: API, extraction |
| Research | Claude Opus | Сложный анализ и синтез |
| Aggregator | Claude Opus | Синтез всех данных |
| Reporter | Claude Opus | Качественное форматирование |

## Конфигурация

### Переменные окружения

```env
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql://localhost/ralph
REDIS_URL=redis://localhost:6379

# Опционально: внешние API
FINANCIAL_API_KEY=...
NEWS_API_KEY=...
```

### Настройка моделей

```python
# config/models.py
AGENT_MODELS = {
    "initial_research": "deep-research",
    "brief_builder": "claude-opus-4-20250514",
    "planner": "claude-opus-4-20250514",
    "data": "claude-sonnet-4-20250514",
    "research": "claude-opus-4-20250514",
    "aggregator": "claude-opus-4-20250514",
    "reporter": "claude-opus-4-20250514",
}
```

## API

### Создать исследование

```bash
POST /api/research
Content-Type: application/json

{
  "query": "Расскажи про Realty Income, хочу инвестировать",
  "output_formats": ["pdf", "excel"]
}
```

### Статус исследования

```bash
GET /api/research/{session_id}/status
```

### Получить результат

```bash
GET /api/research/{session_id}/result
```

## Примеры использования

### Инвестиционный анализ

```
User: "Проанализируй Apple как инвестицию на 5 лет"

Ralph:
1. Initial Research → узнаёт что это tech-гигант, тикер AAPL
2. Brief Builder → уточняет фокус (дивиденды? рост? риски?)
3. Data → собирает финансовые метрики, мультипликаторы
4. Research → анализирует стратегию, конкурентов, тренды
5. Aggregator → синтезирует bull/bear case
6. Reporter → генерирует PDF-отчёт с графиками
```

### Рыночное исследование

```
User: "Исследуй рынок электросамокатов в России"

Ralph:
1. Initial Research → основные игроки, объём рынка
2. Brief Builder → уточняет (B2B sharing? B2C продажи? регуляции?)
3. Data → статистика, финансы компаний
4. Research → тренды, барьеры входа, прогнозы
5. Reporter → презентация для инвесторов
```

## Roadmap

- [x] Базовая архитектура
- [x] Initial Research фаза
- [ ] Brief Builder с диалогом
- [ ] Data Agent с API интеграциями
- [ ] Research Agent с веб-поиском
- [ ] Planner loop с coverage check
- [ ] Aggregator с визуализациями
- [ ] Reporter (PDF, Excel, PPTX)
- [ ] React frontend
- [ ] WebSocket для real-time updates
- [ ] RAG для пользовательских документов

## Contributing

1. Fork репозитория
2. Создать feature branch (`git checkout -b feature/amazing`)
3. Commit изменения (`git commit -m 'Add amazing feature'`)
4. Push в branch (`git push origin feature/amazing`)
5. Открыть Pull Request

## License

MIT
