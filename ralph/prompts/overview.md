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

Append questions to `questions/overview_questions.json`:
```json
{
  "questions": [
    {
      "id": "oq1",
      "source": "overview_1",
      "generated_at": "ISO timestamp",
      "question": "Question text",
      "type": "data|research|overview",
      "context": "Why this question arose",
      "priority_hint": "high|medium|low"
    }
  ]
}
```
**⚠️ APPEND mode:** If file exists, add new questions to the array. Do NOT overwrite previous questions.

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

## Rules
- Deep Research skill handles timing internally — take the time needed for quality
- Focus on Brief scope — don't expand beyond what was requested
- Prioritize authoritative sources
- Generate follow-up questions for gaps and uncertainties
- **STOP after completing assigned task** — do not execute other agents' work (data, research)
- **Stay in your lane** — you are Overview agent; finish your task and end
