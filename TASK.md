# Task: Implement --continue flag in loop.sh

## Status: ✅ IMPLEMENTED

## Problem
`./loop.sh --continue research_folder "additional context"`
was passing "--continue" as the query instead of continuing existing research.

## Solution Implemented (Commit: 9be9891)

### 1. loop.sh — Added `continue_research()` function

```bash
./loop.sh --continue research_20260119_mezen "добавь анализ конкурентов"
```

**Behavior:**
1. Validates source folder exists
2. Creates new folder with version suffix: `research_20260119_mezen_v2`
3. Copies entire research (state/, results/, questions/)
4. Updates session.json:
   - Sets `additional_context` field
   - Sets `continued_from` field (original folder)
   - Resets `phase` to `brief_builder`
5. Clears output/ folder for fresh generation
6. Runs research loop from brief_builder phase

### 2. brief_builder.md — Added Continuation Mode

When `continued_from` exists in session.json:
- Loads existing brief.json as base
- Parses additional_context for new requirements
- Adds new scope items marked with `added_in_continuation: true`
- Preserves previous preferences unless overridden

---

## Usage Examples

```bash
# Continue with additional context
./loop.sh --continue research_20260119_mezen "добавь детальный анализ конкурентов"

# Continue without additional context (just re-run from brief_builder)
./loop.sh --continue research_20260119_mezen

# Multiple continuations create versioned folders
# research_20260119_mezen
# research_20260119_mezen_v2
# research_20260119_mezen_v3
```

---

## session.json After Continue

```json
{
  "id": "research_20260119_mezen_v2",
  "query": "original query...",
  "additional_context": "добавь анализ конкурентов",
  "continued_from": "research_20260119_mezen",
  "phase": "brief_builder",
  ...
}
```

---

## Files Modified

1. `ralph/loop.sh` — Added `continue_research()` function and `--continue` case
2. `ralph/prompts/brief_builder.md` — Added Continuation Mode handling
