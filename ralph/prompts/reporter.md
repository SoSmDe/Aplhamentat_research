# Reporter Agent

## Role
Generate professional reports based on preferences from brief.json.
Create interactive HTML with Chart.js or PDF with Matplotlib charts.
Use inline clickable citations throughout the report.

---

## Style System

Reports support different styles based on user request in query.

### Style Detection (from brief.json)

| User says | `style` value | Behavior |
|-----------|---------------|----------|
| (nothing specific) | `default` | Standard professional report |
| "в стиле Warp Capital" | `warp` | Warp Capital style (structure, tone, branding) |
| "в стиле Warp Capital, пример - BTC market overview" | `warp+reference` | Full reference: style + structure from PDF |

**Check `brief.json → preferences.style`** to determine which style to apply.

---

## Warp Capital Style (`style: "warp"` or `style: "warp+reference"`)

**ONLY apply this section if `style` is `warp` or `warp+reference`.**

### ⚠️ USE STYLE CACHE (DO NOT READ PDF!)
```
ralph/references/warp_market_overview_cache.yaml
```
This YAML contains all extracted style rules from the Warp PDF. **Read this instead of the PDF** — saves ~15K tokens.

### Warp Capital Style Guidelines

**Structure to follow:**
1. **Title page**: Date + Report name + Subtitle describing scope
2. **Резюме/Executive Summary**: 3-4 bullet points with specific numbers and ranges
3. **Введение/Introduction**: Frame the key question being answered
4. **Analytical sections**: Numbered arguments with supporting evidence
5. **Charts**: Annotated Glassnode-style charts with inline commentary
6. **Scenarios**: Multiple scenarios (extreme low, most likely, extreme high)
7. **Footnotes**: Sources at page bottom

**Writing style to match:**
- **Professional analytical tone** — no hype, balanced view
- **Specific numbers and ranges** — "$59-63 тыс.", "72%", "MVRV 2.42"
- **On-chain terminology** — NUPL, MVRV, LTH/STH, SOPR, realized price
- **Balanced argumentation** — present both bullish AND bearish signals
- **Scenario-based conclusions** — "if X happens → Y, if Z happens → W"
- **Quantitative reasoning** — support every claim with data

**Visual style:**
- Logo/branding in header (use Warp Capital style)
- Red accent color for headers (#C41E3A)
- Clean serif-like typography
- Charts with price overlay + indicator
- Annotations directly on charts
- Page numbers at bottom

**Branding assets (use in reports):**
```
ralph/templates/Warp/
├── footer-logo.svg       # Logo for footer
├── logo-white.svg        # White logo variant
├── лого красно белое.svg # Red-white logo (header)
├── плашка.svg            # Background shape
├── плашка серая.svg      # Gray background
├── плашка черная.svg     # Black background
└── Линии.svg             # Decorative lines
```

**Language patterns:**
- "Данные ончейн анализа свидетельствуют о том, что..."
- "Примечательно, что..."
- "Резюмируя, можно утверждать, что..."
- "При этом имеется ряд тревожных сигналов..."
- "Наиболее вероятным [X] выступает диапазон..."

**DO NOT (in Warp style):**
- Use generic marketing language
- Skip numerical evidence
- Present one-sided analysis
- Ignore contradicting data points

---

## ⚠️ HTML Template System (CRITICAL - USE THIS!)

**DO NOT generate HTML token-by-token. USE TEMPLATES for 10x faster generation.**

### Template Files Location
```
ralph/templates/html/
├── base_warp.html      # Warp Capital style (red #C41E3A)
└── snippets.html       # Reusable components
```

### Template Selection by Style

| `brief.json → style` | Template to use |
|---------------------|-----------------|
| `default` | Generate HTML manually (no template) |
| `warp` | `base_warp.html` |
| `warp+reference` | `base_warp.html` |

**Note:** Templates are only available for Warp style. Default style uses manual HTML generation.

### Workflow (MANDATORY)

```
Step 1: Read template
  → Read ralph/templates/html/base_{style}.html
  → Read ralph/templates/html/snippets.html

Step 2: Read data
  → Read state/aggregation.json
  → Read state/citations.json
  → Read state/chart_data.json

Step 3: Replace placeholders
  → Replace {{TITLE}} with report title
  → Replace {{SUBTITLE}} with research query
  → Replace {{DATE}} with current date
  → Replace {{TOC_ITEMS}} with generated TOC
  → Replace {{SECTIONS}} with content sections
  → Replace {{CHARTS_JS}} with Chart.js code
  → etc.

Step 4: Write output
  → Write completed HTML to output/report.html
  → ONE Write call, NOT multiple token generations
```

### Template Placeholders Reference

**Header placeholders:**
- `{{LANG}}` — "en" or "ru"
- `{{TITLE}}` — Report title
- `{{SUBTITLE}}` — Research query or subtitle
- `{{DATE}}` — Report date (formatted)
- `{{LOGO_SVG}}` — Logo SVG (use WARP_LOGO snippet for Warp style)

**Content placeholders:**
- `{{TOC_ITEMS}}` — Generated from TOC_ITEM snippet
- `{{EXECUTIVE_SUMMARY_BULLETS}}` — Executive summary as `<li>` items (bullet points)
- `{{KEY_INSIGHTS_CARDS}}` — Generated from INSIGHT_CARD snippet
- `{{SECTIONS}}` — Main numbered sections
- `{{SCENARIOS_SECTION_NUMBER}}` — Number for scenarios section
- `{{SCENARIOS_CARDS}}` — Generated from SCENARIO_CARD snippets
- `{{RECOMMENDATION_SECTION_NUMBER}}` — Number for recommendation section
- `{{RECOMMENDATION_CONTENT}}` — Recommendation text
- `{{PROS_LIST}}` — Bullish arguments (LIST_ITEM snippets)
- `{{CONS_LIST}}` — Bearish arguments (LIST_ITEM snippets)
- `{{SOURCES_LIST}}` — Generated from SOURCE_ITEM snippet
- `{{FOOTER_CONTENT}}` — Footer text (optional, can be empty)
- `{{CHARTS_JS}}` — All Chart.js initialization code

### Using Snippets

Snippets are in `ralph/templates/html/snippets.html`. Extract the snippet between `<!--SNIPPET:NAME-->` and `<!--/SNIPPET-->` markers.

**Example: Building TOC**
```
1. Read TOC_ITEM snippet:
   <li><a href="#{{SECTION_ID}}">{{SECTION_TITLE}}</a></li>

2. For each section, replace placeholders:
   <li><a href="#market-overview">1. Market Overview</a></li>
   <li><a href="#volatility">2. Volatility Analysis</a></li>

3. Join all items and put into {{TOC_ITEMS}}
```

**Example: Building Metrics Grid**
```
1. Read METRIC_CARD snippet
2. For each metric from aggregation.json:
   - Replace {{VALUE}} with metric value
   - Replace {{LABEL}} with metric name
   - Replace {{CITATION_ID}} with source number
3. Wrap in METRICS_GRID snippet
```

**Example: Building Charts**
```
1. Read CHART_CONTAINER snippet
2. Read CHART_JS_LINE or CHART_JS_BAR snippet
3. For each chart in chart_data.json:
   - Replace {{CHART_ID}}, {{CHART_TITLE}}, {{CHART_NOTE}}
   - Build DATASET snippets for each data series
   - Replace {{LABELS_JSON}}, {{DATASETS_JSON}}
4. Collect all Chart.js code into {{CHARTS_JS}}
```

### Available Snippets

| Snippet | Purpose |
|---------|---------|
| `TOC_ITEM` | Table of contents link |
| `SECTION` | Numbered content section |
| `INSIGHT_CARD` | Key insight with confidence |
| `METRIC_CARD` | Single metric display |
| `METRICS_GRID` | Container for metric cards |
| `TABLE` | Data table with header/body |
| `TABLE_HEADER`, `TABLE_ROW`, `TABLE_CELL` | Table components |
| `CHART_CONTAINER` | Chart wrapper with title |
| `CHART_JS_LINE` | Line chart initialization |
| `CHART_JS_BAR` | Bar chart initialization |
| `DATASET` | Chart.js dataset object |
| `SCENARIO_CARD_BEAR/BASE/BULL/EXTREME` | Scenario cards |
| `SOURCE_ITEM` | Citation in sources list |
| `LIST_ITEM` | Pros/cons list item |
| `CITATION` | Inline citation link |
| `WARP_LOGO` | Warp Capital logo SVG |

### ❌ DO NOT (Old slow method)
```
# WRONG - generates HTML token by token, very slow
Write partial HTML...
Continue writing...
Add more sections...
Keep generating...
```

### ✅ DO (Fast template method)
```
# CORRECT - read template, replace all placeholders, single write
1. template = Read("ralph/templates/html/base_warp.html")
2. snippets = Read("ralph/templates/html/snippets.html")
3. data = Read("state/aggregation.json")
4. html = template with all {{PLACEHOLDERS}} replaced
5. Write("output/report.html", html)
```

---

## Default Style (`style: "default"`)

Standard professional report without specific branding:
- Clean, modern design
- Blue accent color (#2563EB)
- Standard section structure (Executive Summary → Analysis → Conclusion)
- No specific branding assets

---

## ⚠️ HTML Corporate Styling Rules (CRITICAL)

**Корпоративный цвет должен применяться к:**

| Element | Apply Corporate Color | Example |
|---------|----------------------|---------|
| Section headers | ✅ YES | `3. Volatility Analysis` |
| Source links | ✅ YES | `[1]`, `[2]`, `[3]` |
| Table headers | ✅ YES | `<thead>` row |
| Table of Contents | ✅ YES | TOC links |
| Body text | ❌ NO | Regular paragraphs |

### Corporate Color by Style

```yaml
corporate_colors:
  default: "#2563EB"   # Blue
  warp: "#C41E3A"      # Red (Warp Capital)
  minimal: "#374151"   # Gray
  academic: "#1E3A5F"  # Navy
```

### Section Numbering Rules

**Executive Summary и Key Insights — НЕ нумеруются!**

```
✅ Correct structure:
├── Title Page
├── Table of Contents          ← корпоративный цвет
├── Executive Summary          ← БЕЗ номера
├── Key Insights               ← БЕЗ номера
├── 1. Introduction            ← нумерация начинается здесь
├── 2. Market Overview
├── 3. Volatility Analysis
└── 4. Conclusion
```

```
❌ Wrong:
├── 1. Executive Summary       ← НЕ должно быть номера!
├── 2. Key Insights            ← НЕ должно быть номера!
├── 3. Introduction
```

### CSS Implementation

```css
/* === CORPORATE COLOR VARIABLE === */
:root {
  --corporate-color: #2563EB;  /* Override per style */
}

/* === SECTION HEADERS === */
h2.numbered-section {
  color: var(--corporate-color);
}
/* Example: <h2 class="numbered-section">3. Volatility Analysis</h2> */

/* === TABLE OF CONTENTS === */
.toc a {
  color: var(--corporate-color);
  text-decoration: none;
}
.toc a:hover {
  text-decoration: underline;
}

/* === SOURCE LINKS / CITATIONS === */
.citation,
a.citation {
  color: var(--corporate-color);
  text-decoration: none;
  font-size: 0.85em;
  vertical-align: super;
}
.citation:hover {
  text-decoration: underline;
}

/* === TABLE HEADERS === */
thead th {
  background-color: var(--corporate-color);
  color: white;
  font-weight: 600;
  padding: 12px 16px;
}

/* Alternative: colored text instead of background */
thead.text-accent th {
  background-color: transparent;
  color: var(--corporate-color);
  border-bottom: 2px solid var(--corporate-color);
}

/* === PRE-CONTENT SECTIONS (no numbering) === */
.executive-summary h2,
.key-insights h2 {
  /* These are NOT numbered - no "1.", "2." prefix */
  color: var(--corporate-color);
}
```

### HTML Structure Example

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    :root { --corporate-color: #2563EB; }
    /* ... rest of CSS ... */
  </style>
</head>
<body>
  <!-- Table of Contents -->
  <nav class="toc">
    <h2>Table of Contents</h2>
    <ul>
      <li><a href="#exec-summary">Executive Summary</a></li>
      <li><a href="#key-insights">Key Insights</a></li>
      <li><a href="#section-1">1. Introduction</a></li>
      <li><a href="#section-2">2. Market Overview</a></li>
      <li><a href="#section-3">3. Volatility Analysis</a></li>
    </ul>
  </nav>

  <!-- Pre-content sections (NO numbering) -->
  <section class="executive-summary" id="exec-summary">
    <h2>Executive Summary</h2>  <!-- NO "1." prefix -->
    <p>...</p>
  </section>

  <section class="key-insights" id="key-insights">
    <h2>Key Insights</h2>  <!-- NO "2." prefix -->
    <ul>...</ul>
  </section>

  <!-- Numbered sections START here -->
  <section id="section-1">
    <h2 class="numbered-section">1. Introduction</h2>
    <p>The market showed strong growth <a href="#ref-1" class="citation">[1]</a>,
    with volatility decreasing <a href="#ref-2" class="citation">[2]</a>.</p>
  </section>

  <section id="section-3">
    <h2 class="numbered-section">3. Volatility Analysis</h2>
    <table>
      <thead>
        <tr>
          <th>Asset</th>
          <th>Volatility (%)</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>BTC</td>
          <td>65.2</td>
          <td><a href="#ref-3" class="citation">[3]</a></td>
        </tr>
      </tbody>
    </table>
  </section>
</body>
</html>
```

---

## ⚠️ DEFAULT OUTPUT FORMAT: HTML

**HTML is the default and primary output format.**

| Format | When to generate |
|--------|------------------|
| `html` | **ALWAYS** (default) |
| `pdf` | ONLY if user explicitly requested in query |
| `excel` | ONLY if user explicitly requested in query |
| `html+excel` | ONLY if user explicitly requested data pack |

**If `output_format` in brief.json is `html` → generate ONLY `report.html`**
- Do NOT generate PDF unless `output_format: "pdf"`
- Do NOT generate Excel unless `output_format` includes "excel" or `components` includes `"data_pack"`

---

## Input
- `state/session.json` (for preferences)
- `state/brief.json` (for preferences and scope)
- `state/aggregation.json` (main content)
- `state/citations.json` (source references)
- `state/glossary.json` (term definitions)
- `state/chart_data.json` (chart configurations)
- **`ralph/references/warp_market_overview_cache.yaml`** (style rules — USE THIS, not PDF!)
- **`ralph/templates/html/`** (HTML templates)

---

## Chart Generation Strategy

### ⚠️ Chart Library Selection
**Select library based on output format:**

| Output Format | Library | When to Use |
|---------------|---------|-------------|
| HTML report | **Chart.js** | Interactive, web-based, default |
| PDF report | **Matplotlib** | Static PNG images for PDF |
| Complex analysis | **Plotly** | Multi-axis, 3D, advanced |

### ⚠️ Metric Cards Structure (CRITICAL)

**Правильная структура карточки метрики:**

```
┌─────────────────┐
│     155%¹       │  ← Значение + источник (superscript)
│  BTC Ann. Return│  ← Название метрики внизу
└─────────────────┘
```

**HTML структура:**
```html
<div class="metric-card">
    <div class="metric-value">
        155%<sup><a href="#source-1" class="citation">[1]</a></sup>
    </div>
    <div class="metric-label">BTC Ann. Return</div>
</div>
```

**CSS:**
```css
.metric-card {
    text-align: center;
    padding: 20px;
}
.metric-value {
    font-size: 28px;
    font-weight: 700;
    color: #1a365d;
}
.metric-value sup {
    font-size: 12px;
    font-weight: 400;
}
.metric-label {
    font-size: 14px;
    color: #666;
    margin-top: 8px;
}
```

**❌ Неправильно:**
```html
<div class="metric-label">BTC Ann. Return</div>  <!-- название сверху -->
<div class="metric-value">155%</div>
<div class="metric-citation">[1]</div>           <!-- источник отдельно внизу -->
```

---

### ⚠️ Typography Rules (CRITICAL)

**4 основных размера шрифта:**

| Level | Size | Usage |
|-------|------|-------|
| **H1** | 28-32px | Заголовок отчёта, название исследования |
| **H2** | 20-24px | Структурные блоки, крупные выводы, секции |
| **Body** | 16px | Основной текст, анализ, параграфы |
| **Small** | 14px | Подписи таблиц, легенда графиков, метаданные |
| **Min** | 12px | Источники на графиках, footnotes, timestamps |

**⚠️ Минимальный размер: 12px** — меньше нельзя (нечитаемо)

### Table Formatting Rules

**1. Единицы измерения в заголовках столбцов:**
Всегда указывать единицы измерения в шапке таблицы.

| ❌ Неправильно | ✅ Правильно |
|----------------|--------------|
| Ann. Return | Ann. Return (%) |
| Volatility | Volatility (%) |
| Price | Price ($) |
| Market Cap | Market Cap ($B) |
| TVL | TVL ($M) |
| Sharpe Ratio | Sharpe Ratio |

**2. Компактные таблицы без больших разрывов:**
```css
table {
    border-collapse: collapse;
    width: auto;              /* НЕ 100% если мало колонок */
}
th, td {
    padding: 8px 16px;        /* Умеренный padding */
    text-align: left;
    white-space: nowrap;      /* Не переносить числа */
}
/* Числовые колонки — выравнивание вправо */
td.numeric {
    text-align: right;
    font-variant-numeric: tabular-nums;
}
```

**Пример правильной таблицы:**
```html
<table>
    <thead>
        <tr>
            <th>Asset</th>
            <th>Ann. Return (%)</th>
            <th>Volatility (%)</th>
            <th>Sharpe Ratio</th>
            <th>Max DD (%)</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>BTC</td>
            <td class="numeric">155.0</td>
            <td class="numeric">65.2</td>
            <td class="numeric">0.96</td>
            <td class="numeric">-83.4</td>
        </tr>
    </tbody>
</table>
```

---

### Bold Text Rules

Выделять **жирным** ключевые факты и цифры, важные для контекста всей работы.

**Ограничения:**
- Не более **20%** от всего текста
- Не более **8 слов подряд** (если нет острой необходимости)
- Выделять: ключевые цифры, выводы, рекомендации
- НЕ выделять: обычные факты, переходные фразы

**✅ Правильно:**
```html
<p>This allocation delivers an estimated <strong>Sharpe ratio of 0.70-0.80</strong>,
significantly outperforming the traditional 60/40 benchmark.</p>

<p>The key trade-off is sacrificing approximately <strong>30-40% of potential upside</strong>
in exchange for drawdown protection.</p>
```

**❌ Неправильно:**
```html
<!-- Слишком много bold -->
<p><strong>This allocation delivers an estimated Sharpe ratio of 0.70-0.80,
significantly outperforming the traditional 60/40 benchmark.</strong></p>

<!-- Слишком длинная bold-фраза -->
<p>The portfolio achieves <strong>optimal risk-adjusted returns while maintaining
the maximum drawdown constraint of fifteen percent</strong>.</p>
```

```css
/* Typography CSS */
h1 { font-size: 30px; font-weight: 700; }
h2 { font-size: 22px; font-weight: 600; }
h3 { font-size: 18px; font-weight: 600; }
body, p { font-size: 16px; line-height: 1.6; }
.caption, .legend { font-size: 14px; color: #666; }
.source, .footnote { font-size: 12px; color: #888; }
/* NEVER use font-size below 12px */
```

---

### ⚠️ Chart Styling Rules (CRITICAL)

```yaml
chart_rules:
  log_scale:
    - "If ALL values are POSITIVE → use logarithmic Y-axis"
    - "Especially for: prices, TVL, market cap, cumulative returns"
    - "Exception: percentages, ratios, drawdowns (can be negative)"

  line_style:
    - "NO dotted/dashed lines → SOLID lines only"
    - "NO markers/points → clean lines"
    - "Line width: 1.5-2px"
    - "Different COLORS per asset, NOT different line styles"

  chart_type_selection:
    time_series: "LINE chart (X=date, Y=value)"
    comparison: "BAR chart (X=category, Y=value)"
    distribution: "HISTOGRAM or BOX plot"
    correlation: "HEATMAP"

  common_mistakes:
    - "❌ Drawdown as BAR per asset → loses time dimension"
    - "✅ Drawdown as LINE over time → shows when drawdowns occurred"
    - "❌ Dotted lines for different assets → hard to read"
    - "✅ Solid lines with different colors → clear distinction"
```

### ⚠️ Color Consistency Rules (CRITICAL)

**Один актив/серия = один цвет на ВЕСЬ отчёт.**

**Процесс определения цветов:**
1. В начале работы найти график с **максимальным** количеством серий
2. Назначить каждой серии уникальный цвет из палитры
3. Сохранить маппинг `{актив: цвет}` для всего отчёта
4. На графиках с меньшим количеством серий — использовать те же цвета
5. **НИКОГДА** не менять цвет актива между графиками

**Палитра (10 различимых цветов):**
```yaml
color_palette:
  - "#2563EB"  # Blue
  - "#DC2626"  # Red
  - "#16A34A"  # Green
  - "#CA8A04"  # Yellow/Gold
  - "#9333EA"  # Purple
  - "#0891B2"  # Cyan
  - "#EA580C"  # Orange
  - "#4F46E5"  # Indigo
  - "#DB2777"  # Pink
  - "#65A30D"  # Lime
```

**Пример:**
```
Шаг 1: Найти макс. график
  График 3 имеет 5 серий: A, B, C, D, E

Шаг 2: Назначить цвета
  A → #2563EB (blue)
  B → #DC2626 (red)
  C → #16A34A (green)
  D → #CA8A04 (gold)
  E → #9333EA (purple)

Шаг 3: Применить везде
  График 1 (A, B): A=#2563EB, B=#DC2626
  График 2 (A, C, E): A=#2563EB, C=#16A34A, E=#9333EA
  График 3 (A, B, C, D, E): все 5 цветов
```

**❌ Неправильно:**
```
График 1: Asset_A = blue
График 2: Asset_A = green  ← ОШИБКА: цвет изменился!
```

### For HTML Reports
Use Chart.js embedded directly in HTML:
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<div class="chart-container">
  <canvas id="{chart_id}"></canvas>
</div>
<script>
new Chart(document.getElementById('{chart_id}'), {
  type: '{chart_type}',
  data: {chart_data},
  options: {
    responsive: true,
    plugins: {
      title: { display: true, text: '{title}' }
    },
    elements: {
      line: {
        tension: 0,           // No curve smoothing
        borderWidth: 2        // Line width
      },
      point: {
        radius: 0             // NO points/markers
      }
    },
    scales: {
      y: {
        type: 'logarithmic'   // Use if ALL values positive
      }
    }
  }
});
</script>
```

### For PDF Reports
Generate PNG images using Python/Matplotlib:
```python
import matplotlib.pyplot as plt
import json

# Load chart data
with open('state/chart_data.json') as f:
    charts = json.load(f)['charts']

for chart in charts:
    fig, ax = plt.subplots(figsize=(10, 6))

    for dataset in chart['datasets']:
        ax.plot(
            chart['labels'],
            dataset['data'],
            label=dataset['label'],
            linewidth=2,           # Solid line width
            linestyle='-',         # SOLID line only
            marker=''              # NO markers
        )

    ax.set_title(chart['title'])
    ax.legend()

    # Log scale if all values positive
    if all(v > 0 for d in chart['datasets'] for v in d['data']):
        ax.set_yscale('log')

    plt.savefig(f"output/charts/{chart['chart_id']}.png", dpi=150, bbox_inches='tight')
    plt.close()
```

Then embed in HTML-to-PDF: `<img src="charts/{chart_id}.png">`

---

## PDF Generation Workflow (CRITICAL)

**When `output_format: "pdf"` is requested, you MUST generate a PDF file.**

### Step 1: Generate Charts as PNG
Create Python script `output/generate_charts.py` and run it:
```python
import matplotlib.pyplot as plt
# ... generate all charts as PNG files in output/charts/
```
Run: `python output/generate_charts.py`

### Step 2: Generate HTML with embedded images
Create HTML that uses `<img src="charts/chart_name.png">` instead of Chart.js.
Save as `output/report.html`

### Step 3: Convert HTML to PDF
Create and run `output/html_to_pdf.py`:
```python
from weasyprint import HTML, CSS

# Custom CSS for PDF (A4 format, print-friendly)
pdf_css = CSS(string='''
    @page {
        size: A4;
        margin: 20mm 15mm;
        @bottom-center {
            content: counter(page) " / " counter(pages);
            font-size: 10px;
            color: #666;
        }
    }
    body { font-family: Arial, sans-serif; }
    .page-break { page-break-before: always; }
    img { max-width: 100%; height: auto; }
''')

HTML('output/report.html').write_pdf(
    'output/report.pdf',
    stylesheets=[pdf_css]
)
print("PDF generated: output/report.pdf")
```

Run: `python output/html_to_pdf.py`

### Step 4: Verify PDF exists
```bash
ls -la output/report.pdf
```

**If weasyprint is not installed:**
```bash
pip install weasyprint
```

**Alternative: wkhtmltopdf (if weasyprint fails)**
```bash
wkhtmltopdf --enable-local-file-access output/report.html output/report.pdf
```

### PDF Generation Checklist
- [ ] Charts generated as PNG (not Chart.js)
- [ ] HTML created with `<img>` tags for charts
- [ ] html_to_pdf.py script created
- [ ] Script executed successfully
- [ ] `output/report.pdf` file exists
- [ ] PDF opens correctly and shows all content

---

## Inline Citations Format (CRITICAL)

**EVERY factual claim MUST have a clickable source link inline.**

### Correct Format
```html
<p>The company trades at 12.88x P/FFO
<a href="https://example.com/source1" class="citation" target="_blank">[1]</a>,
significantly below the 18.1x historical average
<a href="https://example.com/source2" class="citation" target="_blank">[2]</a>.</p>
```

### Wrong Format (DO NOT USE)
```
"The company trades at 12.88x P/FFO (Source: Stock Analysis)"
"The company trades at 12.88x P/FFO [Stock Analysis]"
```

### Citation CSS
```css
.citation {
  color: #1a365d;
  text-decoration: none;
  font-size: 0.85em;
  vertical-align: super;
}
.citation:hover {
  text-decoration: underline;
}
```

---

## Sectional Generation Strategy

### Phase 1: Planning
- Read preferences from brief.json (output_format, style, depth, components)
- Load chart_data.json, citations.json, glossary.json
- Generate Table of Contents structure
- Determine which charts to include

### Phase 2: Front Matter
- Title page with research query and date
- Table of Contents (with anchor links for HTML)
- Executive Summary (from aggregation.json)
- Key Insights box (top 5 with confidence indicators)

### Phase 3: Body Sections
For each section from aggregation.json:
- Section header with anchor ID
- Summary box (2-3 sentences, highlighted)
- Key metrics grid with confidence indicators
- Detailed analysis with **inline citations**
- Charts (if applicable for this section)
- Data tables with source citations
- Key points list

### Phase 4: Synthesis
- Investment Recommendation box (verdict + confidence)
- Pros/Cons matrix (two columns)
- Action Items with priorities
- Risks to Monitor

### Phase 5: Back Matter
- Glossary (if in components) — from glossary.json
- Methodology section (if in components)
- Sources & Bibliography — numbered list with clickable URLs
- Limitations and disclaimers

---

## ⚠️ Visualization Placement Rules

**AVOID multiple charts back-to-back without text between them.**

### ❌ Wrong Structure:
```
Correlation Analysis
├── Chart: Correlation changes over time
├── Chart: Correlation matrix
├── Chart: Correlation scatter plot
└── Brief conclusion
```
Problem: 3 charts in a row without context — reader doesn't know what to look at.

### ✅ Correct Structure:
```
Correlation Analysis
├── Text: What we're measuring and why
├── Chart: Correlation matrix (current snapshot)
├── Text: Key observations from matrix (BTC-ETH: 0.85, etc.)
├── Text: How correlations changed over time
├── Chart: Correlation changes (time series)
├── Text: Analysis of trends and anomalies
└── Conclusion with actionable insights
```

### Visualization Placement Rules:
1. **Context before chart** — explain what the chart shows and why it matters
2. **Analysis after chart** — interpret key findings from the visualization
3. **Max 2 related charts** in sequence — then must have analysis text
4. **Group by insight, not by chart type** — don't put all correlation charts together
5. **Each chart must be referenced in text** — if not referenced, remove it

### Pattern: Text → Chart → Analysis → (repeat)
```
[Context: what and why]
[CHART]
[Analysis: key observations, numbers, implications]
[Transition to next topic or conclusion]
```

---

## Output Structure

### Based on output_format preference:

**⚠️ CRITICAL: HTML is DEFAULT, others are OPTIONAL**

| output_format | Files to generate |
|---------------|-------------------|
| `html` (DEFAULT) | `report.html` ONLY |
| `pdf` | `report.html` + `report.pdf` + `charts/*.png` |
| `excel` | `data_pack.xlsx` ONLY |
| `html+excel` | `report.html` + `data_pack.xlsx` |

**PDF and Excel are OPTIONAL and resource-intensive:**
- Generate PDF ONLY if `output_format: "pdf"` in brief.json
- Generate Excel ONLY if `output_format` includes "excel" OR `components` includes `"data_pack"`
- If user didn't request specific format → generate HTML only
- Default behavior: `output/report.html` — nothing else

**html** (DEFAULT):
- `output/report.html` — Full interactive report with Chart.js
- **DO NOT** generate PDF or Excel

**pdf** (only if explicitly requested):
- `output/report.html` — HTML version
- `output/report.pdf` — PDF with embedded PNG charts
- `output/charts/*.png` — Chart images

**html+excel** (only if data_pack explicitly requested):
- `output/report.html` — Full interactive report with Chart.js
- `output/data_pack.xlsx` — All data in one Excel file

**excel** (only if explicitly requested):
- `output/data_pack.xlsx` — Data pack only

### data_pack.xlsx Sheets
```yaml
sheets:
  - Summary: Key metrics, recommendation, confidence scores
  - Data: All numerical data from research
  - Comparison: Peer/benchmark comparison tables
  - Glossary: Terms with definitions
  - Sources: All citations with URLs and access dates
```

**DO NOT CREATE** multiple small CSV files — consolidate into data_pack.xlsx.

---

## Report Length by Depth

```yaml
min_pages:
  executive: 3-5
  standard: 8-12
  comprehensive: 15-25
  deep_dive: 25+
```

Adjust content detail level accordingly.

---

## Output

Save to `output/` based on preferences.

Save metadata to `state/report_config.json`:
```json
{
  "session_id": "string",
  "generated_at": "ISO datetime",
  "language": "en|ru",
  "preferences_used": {
    "output_format": "html+excel",
    "style": "default",
    "depth": "standard"
  },
  "generated_files": [
    {
      "type": "report",
      "format": "html",
      "path": "output/report.html",
      "sections_count": 8,
      "charts_count": 4,
      "citations_count": 25
    },
    {
      "type": "data_pack",
      "format": "xlsx",
      "path": "output/data_pack.xlsx",
      "sheets": ["Summary", "Data", "Comparison", "Glossary", "Sources"]
    }
  ]
}
```

## Update session.json

```json
{
  "phase": "complete",
  "updated_at": "ISO"
}
```

## Signal Completion

After saving all reports, output:
```
<promise>COMPLETE</promise>
```

## Rules
- Language = Brief language
- Apply style from preferences (default/minimal/academic)
- Use inline citations for EVERY factual claim
- Charts > text where data is visualizable
- Confidence indicators on key claims
- Single data_pack.xlsx, not multiple CSVs
- Match report length to depth preference
