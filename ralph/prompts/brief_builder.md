# Brief Builder Agent (Auto-Mode)

## Role
Generate research Brief automatically based on query and initial context.
Determine user preferences by analyzing query and self-answering clarifying questions.

## Input
- `state/initial_context.json`
- `state/session.json` (for query, additional_context, continued_from)
- `state/brief.json` (if continuing from previous research)

## Process

1. Read initial context and query
2. **Check for continuation mode**: If `session.json` has `continued_from` field:
   - Load existing `brief.json` as base
   - Read `additional_context` from session.json
   - Merge new context into existing scope items
   - Add new scope items if additional_context requires them
   - Preserve previous preferences unless overridden
3. Generate clarifying questions
4. **Self-answer** each question based on context
5. Determine preferences (format, style, depth, audience, components)
6. Create comprehensive Brief with scope items

### Continuation Mode
When `continued_from` exists in session.json:
```json
{
  "continued_from": "research_20260119_mezen",
  "additional_context": "добавь анализ конкурентов"
}
```

Actions:
- Keep existing scope items from previous brief
- Parse additional_context for new requirements
- Add new scope items with `"added_in_continuation": true`
- Update goal to reflect expanded scope
- Set `"is_continuation": true` in brief.json

---

## Questions to Self-Answer

### 1. Goal
**Question**: What does user want to know?
**Logic**: Derive from query keywords and initial context

### 2. Output Format
**Question**: What report format is needed?
**Options**:
- `html` — Interactive, for browser viewing **(DEFAULT)**
- `pdf` — For printing/archiving (only if user explicitly requests)
- `excel` — Data only for own analysis (only if user explicitly requests)
- `html+excel` — Full report + data pack (only if user explicitly requests)

**⚠️ IMPORTANT: HTML is the DEFAULT output format.**
- PDF and Excel are OPTIONAL and resource-intensive
- Generate PDF/Excel ONLY if user explicitly requests them
- If user doesn't specify format → use `html`

```yaml
auto_answer_logic:
  pdf:
    keywords: ["pdf", "PDF", "формат pdf", "format pdf", "print", "archive", "send", "document"]
  excel:
    keywords: ["data", "spreadsheet", "analyze myself", "raw", "excel", "xlsx"]
  html+excel:
    keywords: ["html+excel", "data pack", "full package"]
  html:
    keywords: ["interactive", "web", "online", "html"]
  default: "html"
```

### 3. Report Style
**Question**: What visual style?
**Options**:
- `default` — Professional styling (blue accent, standard structure)
- `minimal` — Content-focused, no decorations
- `academic` — Formal tone, footnotes style
- `warp` — Warp Capital style (red accent, branding, balanced analysis)
- `warp+reference` — Warp Capital style + follow reference PDF exactly

```yaml
auto_answer_logic:
  warp+reference:
    keywords: ["Warp Capital", "Warp"]
    requires_also: ["пример", "example", "reference", "как в"]
  warp:
    keywords: ["Warp Capital", "Warp", "стиле Warp", "стиль Warp"]
  academic:
    keywords: ["academic", "research paper", "thesis", "formal"]
  minimal:
    keywords: ["simple", "clean", "plain", "no frills"]
  default: "default"
```

**When `warp` or `warp+reference` is detected:**
- Set `style_reference` in preferences pointing to **YAML cache** (NOT PDF!)
- This affects Planner (story-line, data needs) and Reporter (visual style)

```json
"preferences": {
  "style": "warp+reference",
  "style_reference": "ralph/references/warp_market_overview_cache.yaml"
}
```

**⚠️ DO NOT use PDF path!** The YAML cache contains all extracted style rules and saves ~15K tokens.

### 4. Report Depth
**Question**: How detailed should the report be?
**Options**:
- `executive` — 3-5 pages, high-level summary
- `standard` — 8-12 pages, balanced detail
- `comprehensive` — 15-25 pages, thorough analysis
- `deep_dive` — 25+ pages, exhaustive coverage

```yaml
auto_answer_logic:
  executive:
    keywords: ["quick", "brief", "summary", "overview", "short"]
  comprehensive:
    keywords: ["detailed", "thorough", "comprehensive", "full"]
  deep_dive:
    keywords: ["deep", "exhaustive", "complete", "everything"]
  default: "standard"
```

### 5. Target Audience
**Question**: Who will read this report?
**Options**:
- `c_level` — High-level, decision-focused
- `committee` — Balance of details and conclusions
- `analyst` — Maximum data and methodology
- `general` — Simple language, term explanations

```yaml
auto_answer_logic:
  c_level:
    keywords: ["board", "executive", "CEO", "management", "decision"]
  committee:
    keywords: ["committee", "review", "approval"]
  general:
    keywords: ["beginner", "explain", "new to", "understand", "learn"]
  default: "analyst"
```

### 6. Report Components
**Question**: What components to include?
**Options**:
- `executive_one_pager` — 1-page key findings
- `full_report` — Complete report
- `glossary` — Terms dictionary
- `methodology` — Research methodology section
- `data_pack` — Excel with all data (OPTIONAL, resource-intensive)

```yaml
auto_answer_logic:
  always_include:
    - "full_report"

  conditional:
    methodology:
      if_depth: ["comprehensive", "deep_dive"]
    glossary:
      if_audience: ["general"]
    executive_one_pager:
      if_audience: ["c_level"]

  data_pack:
    trigger: "explicit_request_only"
    keywords: ["excel", "xlsx", "data export", "raw data", "spreadsheet"]
    note: "Resource-intensive — never auto-add based on depth or audience"
```

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
    "output_format": "html",
    "style": "default",
    "style_reference": null,
    "depth": "standard",
    "audience": "analyst",
    "components": ["full_report"]
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
      "answer": "html",
      "why": "Default choice (HTML), no specific format requested by user"
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
    "output_format": "html",
    "style": "default",
    "style_reference": null,
    "depth": "standard",
    "audience": "analyst",
    "components": ["full_report"]
  },
  "updated_at": "ISO timestamp"
}
```

Copy `preferences` from brief.json to session.json for easy access by other phases.
