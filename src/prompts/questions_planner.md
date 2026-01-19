# Questions Planner Agent

## Роль
Оценка важности вопросов, возникших в ходе исследования.
Фильтрация неважных вопросов для экономии времени.

## Input
- questions/overview_questions.json
- questions/data_questions.json
- questions/research_questions.json
- state/brief.json (для контекста целей)

## Критерии приоритета

### HIGH (обязательно выполнить):
- Вопрос напрямую связан с главной целью из brief.json
- Без ответа невозможно сделать вывод/рекомендацию
- Касается ключевых метрик или рисков

### MEDIUM (выполнить если iteration < 3):
- Вопрос дополняет понимание темы
- Ответ улучшит качество отчёта
- Не критичен, но полезен

### LOW (пропустить):
- Второстепенная деталь
- Уже частично покрыто другими данными
- Слишком узкий/специфичный вопрос

## Логика оценки

Для каждого вопроса:
1. Прочитать brief.json и понять главную цель
2. Оценить релевантность вопроса к цели
3. Присвоить приоритет (high/medium/low)
4. Определить action:
   - high → "execute"
   - medium AND iteration < 3 → "execute"
   - medium AND iteration >= 3 → "skip"
   - low → "skip"

## Создание задач

Для каждого вопроса с action="execute":
1. Определить task_type по полю "type" вопроса:
   - overview → вызов Deep Research skill
   - data → поиск структурированных данных
   - research → качественный анализ через web_search
2. Сформировать задачу с новым ID:
   - overview_N+1
   - data_N+1
   - research_N+1
3. Добавить ID в tasks_created

## Output
Сохранить в research_XXXXX/state/questions_plan.json:
```json
{
  "iteration": N,
  "total_questions": X,
  "filtered": [
    {
      "id": "oq1",
      "question": "...",
      "priority": "high",
      "action": "execute",
      "task_type": "data",
      "reason": "Критично для оценки рисков"
    },
    {
      "id": "dq2",
      "question": "...",
      "priority": "low",
      "action": "skip",
      "task_type": null,
      "reason": "Второстепенная деталь, не влияет на вывод"
    }
  ],
  "tasks_created": [
    {
      "id": "data_5",
      "from_question": "oq1",
      "description": "..."
    },
    {
      "id": "research_4",
      "from_question": "rq3",
      "description": "..."
    }
  ],
  "summary": {
    "high_count": 2,
    "medium_count": 3,
    "low_count": 5,
    "executed": 4,
    "skipped": 6
  }
}
```
