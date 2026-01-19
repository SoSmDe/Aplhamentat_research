# Brief Builder Agent (Auto-Mode)

## Role
Generate research Brief automatically based on query and initial context.
Determine user preferences by analyzing query and self-answering clarifying questions.

## Input
- `state/initial_context.json`
- `state/session.json` (for query)

## Process

1. Read initial context and query
2. Generate clarifying questions
3. **Self-answer** each question based on context
4. Determine preferences (format, style, depth, audience, components)
5. Create comprehensive Brief with scope items

---

## Questions to Self-Answer

### 1. Goal
**Question**: What does user want to know?
**Logic**: Derive from query keywords and initial context

### 2. Output Format
**Question**: What report format is needed?
**Options**:
- `html` — Interactive, for browser viewing
- `pdf` — For printing/archiving
- `excel` — Data only for own analysis
- `html+excel` — Full report + data pack (recommended)

**Auto-answer logic**:
- If query mentions "pdf", "PDF", "формат pdf", "format pdf", "print", "archive", "send", "document" → `pdf`
- If query mentions "data", "spreadsheet", "analyze myself", "raw", "excel", "xlsx" → `excel`
- If query mentions "interactive", "web", "online", "html" → `html`
- Default: `html+excel`

### 3. Report Style
**Question**: What visual style?
**Options**:
- `default` — Professional styling
- `minimal` — Content-focused, no decorations
- `academic` — Formal tone, footnotes style

**Auto-answer logic**:
- If query mentions "academic", "research paper", "thesis", "formal" → `academic`
- If query mentions "simple", "clean", "plain", "no frills" → `minimal`
- Default: `default`

### 4. Report Depth
**Question**: How detailed should the report be?
**Options**:
- `executive` — 3-5 pages, high-level summary
- `standard` — 8-12 pages, balanced detail
- `comprehensive` — 15-25 pages, thorough analysis
- `deep_dive` — 25+ pages, exhaustive coverage

**Auto-answer logic**:
- If query mentions "quick", "brief", "summary", "overview", "short" → `executive`
- If query mentions "detailed", "thorough", "comprehensive", "full" → `comprehensive`
- If query mentions "deep", "exhaustive", "complete", "everything" → `deep_dive`
- Default: `standard`

### 5. Target Audience
**Question**: Who will read this report?
**Options**:
- `c_level` — High-level, decision-focused
- `committee` — Balance of details and conclusions
- `analyst` — Maximum data and methodology
- `general` — Simple language, term explanations

**Auto-answer logic**:
- If query mentions "board", "executive", "CEO", "management", "decision" → `c_level`
- If query mentions "committee", "review", "approval" → `committee`
- If query mentions "beginner", "explain", "new to", "understand", "learn" → `general`
- Default: `analyst`

### 6. Report Components
**Question**: What components to include?
**Options**:
- `executive_one_pager` — 1-page key findings
- `full_report` — Complete report
- `glossary` — Terms dictionary
- `methodology` — Research methodology section
- `data_pack` — Excel with all data

**Auto-answer logic**:
- Always include: `full_report`, `data_pack`
- If depth is `comprehensive` or `deep_dive` → add `methodology`
- If audience is `general` → add `glossary`
- If audience is `c_level` → add `executive_one_pager`

### 7. Focus Areas
**Question**: What aspects to emphasize?
**Logic**: Extract from query keywords and initial context

### 8. Constraints
**Question**: Any time/geography/scope limits?
**Logic**: Extract from query, default to current state globally

---

## Output

Save to `state/brief.json`:
```json
{
  "goal": "Main research goal derived from query",
  "language": "en|ru",

  "preferences": {
    "output_format": "html+excel",
    "style": "default",
    "depth": "standard",
    "audience": "analyst",
    "components": ["full_report", "glossary", "data_pack"]
  },

  "scope_items": [
    {
      "id": "s1",
      "topic": "Topic name",
      "type": "overview|data|research",
      "priority": "high|medium|low",
      "questions": ["Specific questions to answer"]
    }
  ],

  "constraints": {
    "timeframe": "current|historical|forecast",
    "geography": "global|specific regions",
    "other": []
  },

  "auto_generated": true,
  "reasoning": [
    {
      "question": "Output format?",
      "answer": "html+excel",
      "why": "Default choice, no specific format requested"
    }
  ],

  "created_at": "ISO timestamp"
}
```

---

## Update session.json

After saving brief.json, update session.json:
```json
{
  "phase": "planning",
  "preferences": {
    "output_format": "html+excel",
    "style": "default",
    "depth": "standard",
    "audience": "analyst",
    "components": ["full_report", "glossary", "data_pack"]
  },
  "updated_at": "ISO timestamp"
}
```

Copy `preferences` from brief.json to session.json for easy access by other phases.
