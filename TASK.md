# Task: Improve Ralph Deep Research Prompts

## Overview
Refactor the Ralph Deep Research system prompts to improve report quality, user customization, and output format.

## Files to Modify
- `ralph/prompts/brief_builder.md`
- `ralph/prompts/planner.md`
- `ralph/prompts/aggregator.md`
- `ralph/prompts/reporter.md`
- `ralph/prompts/initial_research.md` — save sources with URLs
- `ralph/prompts/overview.md` — save citations
- `ralph/prompts/data.md` — save citations
- `ralph/prompts/research.md` — save citations
- `ralph/loop.sh` — update session.json structure

## NOT in scope (for now)
- ~~`prompts/charts.md`~~ — Claude generates charts inline
- ~~`prompts/templates/`~~ — already exists in `ralph/templates/`

---

## 1. Brief Builder Enhancements (`brief_builder.md`)

Add auto-answered questions (agent answers them based on query context):

### Output Format
```yaml
question: "В каком формате нужен отчёт?"
options:
  - "HTML (интерактивный, для браузера)"
  - "PDF (для печати/архива)"
  - "Excel (с данными для анализа)"
  - "HTML + Excel data pack (рекомендуется)"
default: "HTML + Excel data pack"
auto_answer_logic: |
  - If query mentions "print", "archive", "send" → PDF
  - If query mentions "data", "analyze myself" → Excel
  - Default: HTML + Excel
```

### Report Style
```yaml
question: "Какой стиль оформления?"
options:
  - "Default (Ralph брендинг)"
  - "Minimal (только контент, без украшений)"
  - "Academic (с footnotes и formal tone)"
default: "Default"
auto_answer_logic: |
  - If query mentions "academic", "research paper" → Academic
  - If query mentions "simple", "clean" → Minimal
  - Default: Default
```

### Report Depth
```yaml
question: "Какой объём отчёта?"
options:
  - "Executive Summary (3-5 страниц)"
  - "Standard (8-12 страниц)"
  - "Comprehensive (15-25 страниц)"
  - "Deep Dive (25+ страниц)"
default: "Standard"
auto_answer_logic: |
  - If query mentions "quick", "brief", "summary" → Executive
  - If query mentions "detailed", "thorough", "comprehensive" → Comprehensive
  - If query mentions "deep", "exhaustive", "complete" → Deep Dive
  - Default: Standard
```

### Target Audience
```yaml
question: "Кто будет читать отчёт?"
options:
  - "C-level / Board (высокоуровневый, фокус на решениях)"
  - "Investment Committee (баланс деталей и выводов)"
  - "Analyst / Researcher (максимум данных и методологии)"
  - "General audience (простой язык, объяснения терминов)"
default: "Analyst / Researcher"
auto_answer_logic: |
  - If query mentions "board", "executive", "CEO" → C-level
  - If query mentions "committee", "investment decision" → Investment Committee
  - If query mentions "beginner", "explain", "new to" → General audience
  - Default: Analyst
```

### Report Components
```yaml
question: "Какие компоненты включить в отчёт?"
options:
  - executive_one_pager: "Executive One-Pager (1 страница с ключевыми выводами)"
  - full_report: "Full Report (полный отчёт)"
  - glossary: "Glossary (словарь терминов)"
  - methodology: "Methodology Section (описание методологии)"
  - data_pack: "Excel Data Pack (все данные в Excel)"
default: ["full_report", "glossary", "data_pack"]
auto_answer_logic: |
  - Always include: full_report, data_pack
  - If depth is Comprehensive or Deep Dive → add methodology
  - If audience is General → add glossary
  - If audience is C-level → add executive_one_pager
```

### Save to brief.json
```json
{
  "preferences": {
    "output_format": "html+excel",
    "style": "default",
    "depth": "standard",
    "audience": "analyst",
    "components": ["full_report", "glossary", "data_pack"]
  },
  "reasoning": [
    {"question": "Output format?", "answer": "HTML + Excel", "why": "Default, no specific request"}
  ]
}
```

---

## 2. Planner Enhancements (`planner.md`)

Update planner to use depth from brief.json:

```yaml
depth_multipliers:
  executive:
    tasks_per_scope: 1
    max_iterations: 1
    target_coverage: 70%
  standard:
    tasks_per_scope: 2
    max_iterations: 2
    target_coverage: 80%
  comprehensive:
    tasks_per_scope: 3
    max_iterations: 3
    target_coverage: 90%
  deep_dive:
    tasks_per_scope: 4
    max_iterations: 4
    target_coverage: 95%
```

Update session.json with depth-based settings:
```json
{
  "execution": {
    "max_iterations": 2,  // from depth
    "tasks_pending": [...],
    "tasks_completed": []
  },
  "coverage": {
    "target": 80  // from depth
  }
}
```

---

## 3. Aggregator Enhancements (`aggregator.md`)

### Glossary Extraction
```yaml
glossary_generation:
  trigger: "auto"

  extract_terms:
    - Acronyms (AFFO, NNN, REIT, FFO, NAV, etc.)
    - Technical metrics (P/FFO, Debt/EBITDA, Cap Rate, Payout Ratio)
    - Industry-specific terms (Triple-net lease, Rent escalation)
    - Company-specific terminology

  output_format:
    term: "string"
    definition: "string (1-2 sentences)"
    context: "string (why it matters in this report)"
```

### Confidence Scoring
```yaml
confidence_indicators:
  per_claim: true

  levels:
    high:
      criteria: "3+ independent sources agree"
      indicator: "●●●"
    medium:
      criteria: "2 sources or 1 authoritative source"
      indicator: "●●○"
    low:
      criteria: "1 non-authoritative source"
      indicator: "●○○"

  display: "Show indicator next to key claims"
```

### Chart Data Preparation
```yaml
chart_data_extraction:
  identify_chartable_metrics:
    - Time series data (dividend history, stock price, AFFO per share)
    - Composition data (portfolio breakdown, tenant mix)
    - Comparison data (peer metrics, valuation vs historical)

  output_format:
    chart_id: "string"
    chart_type: "line|bar|pie|doughnut"
    title: "string"
    data: { labels: [], datasets: [] }

  save_to: "state/chart_data.json"
```

### Collect All Citations
```yaml
citations_collection:
  gather_from:
    - results/overview_*.json
    - results/data_*.json
    - results/research_*.json

  output_format:
    id: "[1]"
    title: "Source title"
    url: "https://..."
    accessed: "ISO date"
    used_for: "What claim this supports"

  save_to: "state/citations.json"
```

---

## 4. Reporter Enhancements (`reporter.md`)

### Chart Generation Strategy
```yaml
charts:
  html_format:
    library: "Chart.js"
    embed: |
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <canvas id="{chart_id}"></canvas>
      <script>
      new Chart(document.getElementById('{chart_id}'), {
        type: '{type}',
        data: {data},
        options: { responsive: true }
      });
      </script>

  pdf_format:
    library: "Matplotlib"
    method: |
      Claude generates and executes Python code:
      ```python
      import matplotlib.pyplot as plt
      # ... generate chart ...
      plt.savefig('output/charts/{chart_id}.png')
      ```
      Then embeds: <img src="charts/{chart_id}.png">
```

### Sectional Generation Strategy
```yaml
generation_strategy: "sectional"

phases:
  phase_1_planning:
    - Parse brief.json for preferences
    - Generate TOC with estimated sections
    - Load chart_data.json
    - Load citations.json

  phase_2_front_matter:
    - Title page with metadata
    - Table of Contents (linked)
    - Executive Summary
    - Key Insights (top 5)

  phase_3_body_sections:
    for_each_section:
      - Section header with anchor
      - Summary box (2-3 sentences)
      - Key metrics grid
      - Detailed analysis
      - Charts (if applicable)
      - INLINE CITATIONS with clickable links

  phase_4_synthesis:
    - Investment Recommendation box
    - Pros/Cons matrix
    - Action Items
    - Risks to Monitor

  phase_5_back_matter:
    - Glossary (from aggregator)
    - Methodology (if requested)
    - Sources & Bibliography (numbered, with URLs)
```

### Inline Citations Format (CRITICAL)
```yaml
citation_style: "inline_linked"

format: |
  EVERY factual claim MUST have a clickable source link inline.

  CORRECT:
  "Realty Income trades at 12.88x P/FFO <a href="https://..." class="citation">[1]</a>,
   below the 18.1x historical average <a href="https://..." class="citation">[2]</a>."

  WRONG:
  "Realty Income trades at 12.88x P/FFO (Source: Stock Analysis)"

css: |
  .citation {
    color: #1a365d;
    text-decoration: none;
    font-size: 0.85em;
    vertical-align: super;
  }
  .citation:hover { text-decoration: underline; }
```

### Output Files Structure
```yaml
output_structure:
  html_report:
    - "output/report.html"  # Single file with embedded Chart.js

  pdf_report:
    - "output/report.pdf"   # With embedded PNG charts
    - "output/charts/*.png" # Generated by matplotlib

  data_pack:
    - "output/data_pack.xlsx"
      sheets:
        - "Summary"         # Key metrics, recommendation
        - "Financial Data"  # All numerical data
        - "Peer Comparison" # Comparison tables
        - "Dividend Data"   # For charting
        - "Glossary"        # Terms with definitions
        - "Sources"         # All citations with URLs

  DO_NOT_CREATE:
    - Multiple small CSV files (consolidate into data_pack.xlsx)
```

---

## 5. Update Other Prompts for Citations

### initial_research.md — add:
```yaml
save_sources:
  for_each_search_result:
    - title: "Page title"
    - url: "Full URL"
    - snippet: "Relevant excerpt"
    - accessed_at: "ISO timestamp"

  save_to: "state/initial_context.json" under "sources" key
```

### overview.md, data.md, research.md — add:
```yaml
citation_tracking:
  for_each_fact:
    - claim: "The factual statement"
    - source_url: "https://..."
    - source_title: "Title"
    - confidence: "high|medium|low"

  save_to: "results/{type}_{N}.json" under "citations" key
```

---

## 6. Update session.json Structure

Add preferences field in initialize() in loop.sh:
```json
{
  "id": "research_...",
  "query": "...",
  "phase": "initial_research",
  "tags": [],
  "entities": [],
  "preferences": {
    "output_format": "html+excel",
    "style": "default",
    "depth": "standard",
    "audience": "analyst",
    "components": ["full_report", "glossary", "data_pack"]
  },
  "execution": {...},
  "coverage": {...}
}
```

---

## Testing

After implementation, test with:
```bash
./loop.sh "Analyze Realty Income Corporation for long-term investment"
```

Expected improvements:
1. ✅ Brief auto-answers format, style, depth, audience questions
2. ✅ Planner uses depth multipliers
3. ✅ All agents save citations with URLs
4. ✅ Aggregator extracts glossary + confidence scores + chart data
5. ✅ Reporter generates charts (Chart.js for HTML, Matplotlib for PDF)
6. ✅ Report has clickable inline citations [1], [2], [3]
7. ✅ Single data_pack.xlsx instead of many CSVs
8. ✅ Glossary with AFFO, NNN, P/FFO definitions
