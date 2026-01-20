# Questions Planner Agent

## Role
Evaluate question importance, filter low-priority questions, calculate coverage.

## Input
- `state/session.json`
- `state/brief.json`
- `questions/overview_questions.json`
- `questions/data_questions.json`
- `questions/research_questions.json`
- `results/*.json` (all results)

## Process

1. **Collect all questions**
   - Load questions from all question files
   - Count total questions

2. **Evaluate each question**

```yaml
priority_criteria:
  high:
    action: "must_execute"
    conditions:
      - "Directly related to Brief goal"
      - "Cannot make conclusion without answer"
      - "Concerns key metrics or risks"

  medium:
    action: "execute_if_iteration_lt_3"
    conditions:
      - "Enhances understanding"
      - "Improves report quality"
      - "Useful but not critical"

  low:
    action: "skip"
    conditions:
      - "Secondary detail"
      - "Already partially covered"
      - "Too narrow/specific"
```

3. **Calculate coverage**
   For each scope_item in brief.json:
   - Match results to scope items
   - Calculate coverage percentage (0-100)
   - Identify covered and missing aspects

4. **Make decision**

```yaml
decision_inputs:
  from_session_json:
    - coverage.target      # varies by depth: 70-95
    - coverage.current     # calculated in step 3
    - execution.iteration  # current iteration
    - execution.max_iterations  # varies by depth: 1-4

decision_logic:
  aggregation:
    conditions:
      - "coverage.current >= coverage.target"
      - "iteration >= max_iterations"
    result: "phase = aggregation"

  continue_execution:
    conditions:
      - "coverage.current < coverage.target"
      - "iteration < max_iterations"
      - "high_priority_questions exist"
    result: "phase = execution, iteration += 1"
    actions:
      - "create_tasks_from_high_priority_questions()"
      - "add new tasks to plan.json"
      - "add task IDs to tasks_pending"
```

5. **Create tasks from questions**
   For each question with action="execute":
   - Determine task_type from question.type
   - Create new task with ID: {type}_{N+1}
   - Add to plan.json

## Output

Save to `state/questions_plan.json`:
```json
{
  "iteration": 2,
  "total_questions": 15,
  "filtered": [
    {
      "id": "oq1",
      "question": "...",
      "priority": "high",
      "action": "execute",
      "task_type": "data",
      "reason": "Critical for risk assessment"
    },
    {
      "id": "dq2",
      "question": "...",
      "priority": "low",
      "action": "skip",
      "task_type": null,
      "reason": "Secondary detail, doesn't affect conclusion"
    }
  ],
  "tasks_created": [
    {
      "id": "data_5",
      "from_question": "oq1",
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

Save to `state/coverage.json`:
```json
{
  "iteration": 2,
  "overall_coverage": 75,
  "target": 80,
  "by_scope": {
    "s1": {
      "topic": "Financial metrics",
      "coverage_percent": 90,
      "covered_aspects": ["revenue", "profit"],
      "missing_aspects": ["debt ratio"]
    },
    "s2": {
      "topic": "Risks",
      "coverage_percent": 60,
      "covered_aspects": ["market risk"],
      "missing_aspects": ["regulatory risk", "competition risk"]
    }
  },
  "decision": "continue|done",
  "reason": "Coverage below 80%, iteration 2 of 5"
}
```

## Update session.json

If continuing:
```json
{
  "phase": "execution",
  "execution": {
    "iteration": 3,
    "tasks_pending": ["d5", "r4"],
    "tasks_completed": ["o1", "d1", "d2", "r1", "r2", "r3"]
  },
  "coverage": {
    "current": 75,
    "target": 80
  },
  "updated_at": "ISO"
}
```

If done:
```json
{
  "phase": "aggregation",
  "coverage": {
    "current": 85,
    "target": 80
  },
  "updated_at": "ISO"
}
```
