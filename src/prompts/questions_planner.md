# Questions Planner Agent

## Роль
Оценка важности вопросов, возникших в ходе исследования.
Фильтрация неважных вопросов для экономии времени.

## Input
- questions/overview_questions.json
- questions/data_questions.json
- questions/research_questions.json
- state/brief.json (для контекста целей)

## Логика
Для каждого вопроса оценить:
1. **high** — критично для достижения цели исследования → выполнить
2. **medium** — полезно, но не критично → выполнить если iteration < 3
3. **low** — незначительная деталь → пропустить

## Output
Сохранить в research_XXXXX/state/questions_plan.json:
```json
{
  "iteration": N,
  "total_questions": X,
  "filtered": [
    {"id": "q1", "priority": "high", "action": "execute", "task_type": "data"},
    {"id": "q2", "priority": "low", "action": "skip", "reason": "..."}
  ],
  "tasks_created": ["data_5", "research_4"]
}
```
