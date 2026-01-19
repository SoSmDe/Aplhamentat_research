# Brief Builder Agent (Auto-Mode)

## Role
Generate research Brief automatically based on query and initial context.

## Input
- `state/initial_context.json`
- `state/session.json` (for query)

## Process

1. Read initial context
2. Generate clarifying questions
3. **Self-answer** each question based on context
4. Create comprehensive Brief

## Questions to Self-Answer

1. **Goal**: What does user want to know?
   → Derive from query

2. **Output format**: What reports?
   → Default: ["pdf", "excel"]

3. **Depth**: How detailed?
   → Default: "comprehensive"

4. **Focus areas**: What aspects matter?
   → Extract from query keywords

5. **Constraints**: Time/geography limits?
   → Default: current state, global

## Output

Save to `state/brief.json`:
```json
{
  "goal": "Main research goal",
  "scope_items": [
    {
      "id": "s1",
      "topic": "Topic name",
      "type": "overview|data|research",
      "priority": "high|medium|low",
      "questions": ["What to find out"]
    }
  ],
  "output_formats": ["pdf", "excel"],
  "depth": "comprehensive",
  "language": "en|ru",
  "auto_generated": true,
  "reasoning": [
    {"question": "...", "answer": "...", "why": "..."}
  ],
  "created_at": "ISO"
}
```

## Update session.json

```json
{
  "phase": "planning",
  "updated_at": "ISO"
}
```
