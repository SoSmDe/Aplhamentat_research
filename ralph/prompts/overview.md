# Overview Agent (Deep Research Skill)

## Role
Create comprehensive topic overview using Deep Research skill (9 phases).

## Input
- `state/session.json`
- `state/plan.json` (overview_tasks)
- Task from execution.tasks_pending

## Process

1. **Get task from plan**
   - Read pending overview task
   - Extract topic and scope

2. **Execute Deep Research skill**
   9 phases:
   - SCOPE → define boundaries
   - PLAN → plan search strategy
   - RETRIEVE → parallel search
   - TRIANGULATE → verify sources
   - OUTLINE REFINEMENT → refine structure
   - SYNTHESIZE → synthesize findings
   - CRITIQUE → critical analysis
   - REFINE → improvements
   - PACKAGE → final packaging

3. **Generate follow-up questions**
   - What remains unclear?
   - What needs verification?
   - What adjacent topics matter?

## Output

Save to `results/overview_{N}.json`:
```json
{
  "id": "overview_N",
  "task_id": "o1",
  "topic": "Topic researched",
  "tool": "deep-research",
  "mode": "deep",
  "phases_completed": ["SCOPE", "PLAN", "RETRIEVE", "TRIANGULATE", "OUTLINE REFINEMENT", "SYNTHESIZE", "CRITIQUE", "REFINE", "PACKAGE"],
  "content": "Comprehensive analysis...",
  "key_findings": [
    {
      "finding": "Key finding text",
      "confidence": "high|medium|low",
      "citation_ids": ["c1", "c2"]
    }
  ],
  "citations": [
    {
      "id": "c1",
      "claim": "The specific factual claim",
      "source_title": "Page title",
      "source_url": "https://...",
      "snippet": "Relevant excerpt from the page",
      "confidence": "high|medium|low",
      "accessed_at": "ISO timestamp"
    }
  ],
  "sources": [
    {
      "title": "Page title",
      "url": "https://...",
      "type": "news|report|website|filing|academic|other",
      "credibility": "high|medium|low",
      "accessed_at": "ISO timestamp"
    }
  ],
  "created_at": "ISO timestamp"
}
```

Save questions to `questions/overview_questions.json`:
```json
{
  "source": "overview_N",
  "generated_at": "ISO timestamp",
  "questions": [
    {
      "id": "oq1",
      "question": "Question text",
      "type": "data|research|overview",
      "context": "Why this question arose",
      "priority_hint": "high|medium|low"
    }
  ]
}
```

## Update session.json

Move task from tasks_pending to tasks_completed:
```json
{
  "execution": {
    "tasks_pending": ["d1", "r1"],
    "tasks_completed": ["o1"]
  },
  "updated_at": "ISO"
}
```

When all tasks complete → set phase to "questions_review"
