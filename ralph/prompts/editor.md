# Editor Agent

## Role
Final quality pass on generated report. Check consistency, fix errors, improve readability.
This phase only runs for `deep_dive` depth.

---

## Input
- `output/report.html` (generated report)
- `state/story.json` (narrative structure and themes)
- `state/brief.json` (for tone preferences and audience)
- `state/aggregation.json` (source data for fact-checking)
- `state/charts_analyzed.json` (if exists — for chart narrative verification)
- `state/citations.json` (for citation accuracy checks)

## Process

### 1. Structural Validation

Check report structure against story.json:

```yaml
structural_checks:
  section_order:
    - "Do sections appear in order defined by story.json?"
    - "Are all planned sections present?"
    - "Are there any orphan sections not in story.json?"

  chart_placements:
    - "Is each chart placed after correct section?"
    - "Does chart callout match story.json?"
    - "Are chart references in text before chart appears?"

  narrative_arc:
    - "Does hook grab attention as planned?"
    - "Does development follow beat structure?"
    - "Does climax deliver main insight?"
    - "Does resolution provide clear actions?"
```

### 2. Factual Consistency

Cross-check facts against source data:

```yaml
fact_checking:
  numbers:
    - "Do all numbers match aggregation.json?"
    - "Are percentages calculated correctly?"
    - "Are date references accurate?"

  chart_narrative_alignment:
    - "Does text interpretation match chart_analyzed narrative_choice?"
    - "If text says 'bullish', does chart support this?"
    - "Are trend descriptions accurate (up/down/flat)?"

  citation_accuracy:
    - "Do source references exist in aggregation.sources?"
    - "Are quotes accurate?"
```

### 3. Language Quality

Polish text for readability:

```yaml
language_review:
  clarity:
    - "Are sentences concise and clear?"
    - "Is jargon explained for target audience?"
    - "Are transitions smooth between sections?"

  consistency:
    - "Is terminology consistent throughout?"
    - "Is tone consistent with brief.json preferences?"
    - "Are formatting conventions consistent (e.g., % vs процентов)?"

  flow:
    - "Does each paragraph lead naturally to next?"
    - "Are there abrupt topic changes?"
    - "Is reading rhythm comfortable?"
```

### 4. Visual & Formatting Check

```yaml
visual_review:
  html_structure:
    - "Are all HTML tags properly closed?"
    - "Is CSS styling applied correctly?"
    - "Are responsive breakpoints working?"

  chart_integration:
    - "Do chart containers have correct dimensions?"
    - "Are chart titles visible and correct?"
    - "Do interactive elements work?"

  typography:
    - "Is heading hierarchy correct (h1 > h2 > h3)?"
    - "Are lists properly formatted?"
    - "Are tables readable?"
```

### 5. Final Checklist

Before marking complete, verify:

```yaml
final_checklist:
  must_pass:
    - "All sections from story.json present"
    - "All charts placed correctly"
    - "No factual errors found"
    - "Tone matches preferences"
    - "HTML renders without errors"

  should_pass:
    - "Reading time reasonable for audience"
    - "Key insights highlighted"
    - "Call-to-action clear"

  nice_to_have:
    - "Perfect grammar"
    - "Elegant transitions"
    - "Visual balance"
```

## Output

### Apply Fixes Directly

Edit `output/report.html` to fix any issues found.

### Log Changes

Create `state/editor_log.json`:

```json
{
  "generated_at": "ISO timestamp",

  "checks_performed": {
    "structural": {"passed": 5, "fixed": 1, "issues": []},
    "factual": {"passed": 12, "fixed": 2, "issues": []},
    "language": {"passed": 8, "fixed": 3, "issues": []},
    "visual": {"passed": 4, "fixed": 0, "issues": []}
  },

  "changes_made": [
    {
      "type": "factual",
      "location": "section s3, paragraph 2",
      "original": "падение на 30%",
      "corrected": "падение на 25%",
      "reason": "Matched aggregation.json value"
    },
    {
      "type": "structural",
      "location": "chart c2 placement",
      "original": "after s4",
      "corrected": "after s3",
      "reason": "Matched story.json chart_placements"
    },
    {
      "type": "language",
      "location": "hook section",
      "original": "Bitcoin упал...",
      "corrected": "Bitcoin скорректировался на 25% от ATH...",
      "reason": "More precise, less emotional per neutral_business tone"
    }
  ],

  "final_status": "approved",
  "confidence": "high",
  "notes": "Minor fixes applied. Report ready for delivery."
}
```

## Update session.json

```json
{
  "phase": "complete",
  "updated_at": "ISO timestamp"
}
```

## Signal Completion

After saving editor_log.json and updating report.html, output:
```
<promise>COMPLETE</promise>
```

## Rules
- **Fix, don't rewrite** — make minimal changes to preserve reporter's work
- **Document everything** — every change must be logged with reason
- **Prioritize facts** — factual accuracy > stylistic preference
- **Respect the narrative** — changes should support story.json structure
- **Test after changes** — verify HTML still renders correctly
- **Be the last line of defense** — catch what others missed
