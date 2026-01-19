# Overview Agent (Deep Research Skill)

## Роль
Создание глубокого обзора темы с использованием Deep Research skill.

## Инструмент
Deep Research skill (9 фаз):
1. SCOPE — определение границ
2. PLAN — планирование поиска
3. RETRIEVE — параллельный поиск
4. TRIANGULATE — триангуляция источников
5. OUTLINE REFINEMENT — уточнение структуры
6. SYNTHESIZE — синтез
7. CRITIQUE — критический анализ
8. REFINE — доработка
9. PACKAGE — упаковка результата

## Вызов
claude --dangerously-skip-permissions "Используй deep-research skill. Режим: deep (9 phases). Тема: {topic}. Выполни все 9 фаз. Сохрани в {output_path}."

## Input
- task: описание задачи из plan.json
- topic: тема для исследования

## Output
Сохранить в research_XXXXX/results/overview_N.json:
```json
{
  "id": "overview_N",
  "task": "...",
  "tool": "deep-research",
  "mode": "deep",
  "phases_completed": ["SCOPE", "PLAN", "RETRIEVE", "TRIANGULATE", "OUTLINE REFINEMENT", "SYNTHESIZE", "CRITIQUE", "REFINE", "PACKAGE"],
  "content": "...",
  "sources": [...],
  "questions_generated": [...],
  "created_at": "ISO timestamp"
}
```

## Формат вопросов
Сохранить в research_XXXXX/questions/overview_questions.json:
```json
{
  "source": "overview_N",
  "generated_at": "ISO timestamp",
  "questions": [
    {
      "id": "oq1",
      "question": "Текст вопроса",
      "type": "data|research|overview",
      "context": "Почему возник этот вопрос",
      "priority_hint": "high|medium|low"
    }
  ]
}
```
