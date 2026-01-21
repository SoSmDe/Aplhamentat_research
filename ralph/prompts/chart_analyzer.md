# Chart Analyzer Agent

## Role
Analyze time series data from `results/series/`, extract trends and patterns, render charts via CLI.
This phase only runs for `deep_dive` depth when `results/series/` directory exists.

---

## Input
- `state/session.json` (for preferences)
- `state/chart_data.json` (chart specifications from aggregator)
- `results/series/*.json` (raw time series data)

## Process

### 1. Check Prerequisites

```bash
# Verify series directory exists
ls results/series/
```

If no series files exist → skip to next phase (story_lining).

### 2. Render Charts via CLI

**CRITICAL: Use CLI to render charts — do NOT copy large arrays manually.**

Run from the research folder (e.g., `research_20260120_btc/`):

```bash
# From research folder:
python ../cli/render_charts.py \
  --chart-data state/chart_data.json \
  --series-dir results/series/ \
  --output-dir output/charts/

# Or from ralph/ folder:
python cli/render_charts.py \
  --chart-data research_XXXXX/state/chart_data.json \
  --series-dir research_XXXXX/results/series/ \
  --output-dir research_XXXXX/output/charts/
```

CLI script will:
- Read all series files accurately (no data loss)
- Generate Plotly HTML charts
- Output chart analysis summary

### 3. Analyze Each Chart

For each chart in chart_data.json, analyze the corresponding series:

```yaml
analysis_per_chart:
  trends:
    - trend_90d: "Direction and magnitude over 90 days"
    - trend_30d: "Direction and magnitude over 30 days"
    - trend_7d: "Direction and magnitude over 7 days"

  patterns:
    - accumulation: "Steady increase"
    - distribution: "Steady decrease"
    - consolidation: "Sideways movement"
    - reversal: "Direction change"
    - spike: "Sudden sharp move"
    - plateau: "Flat after trend"

  key_values:
    - current: "Latest value"
    - min: "Minimum in period"
    - max: "Maximum in period"
    - avg: "Average"

  visual_summary:
    - "1-2 sentence description of what the chart shows"

  narrative_options:
    - bullish: "How to interpret if telling bullish story"
    - bearish: "How to interpret if telling bearish story"
    - neutral: "Balanced interpretation"
```

### 4. Cross-Chart Analysis

Look for relationships between charts:
- Do price and supply move together?
- Are there divergences between metrics?
- What story do the charts tell together?

## Output

### state/charts_analyzed.json

```json
{
  "generated_at": "ISO timestamp",
  "series_files_processed": 16,
  "charts_rendered": 8,

  "charts": [
    {
      "chart_id": "c1",
      "title": "LTH Supply + BTC Price",
      "rendered_file": "output/charts/c1_lth_supply.html",

      "series_analysis": [
        {
          "series": "BTC_LTH_supply",
          "file": "series/BTC_LTH_supply.json",
          "data_points": 1825,
          "period": "2021-01-01 to 2026-01-20",

          "current_value": 14169732,
          "unit": "BTC",

          "trends": {
            "trend_90d": {"direction": "up", "change": "+312k BTC", "percent": "+2.3%"},
            "trend_30d": {"direction": "up", "change": "+158k BTC", "percent": "+1.1%"},
            "trend_7d": {"direction": "flat", "change": "+8k BTC", "percent": "+0.06%"}
          },

          "pattern": "accumulation_slowing",
          "pattern_description": "Strong accumulation in Q4 2025, now stabilizing",

          "key_levels": {
            "min_90d": 13857000,
            "max_90d": 14169732,
            "avg_90d": 13980000
          }
        }
      ],

      "visual_summary": "LTH накопление продолжается, но темп замедлился. Q4 2025 показал сильный рост (+312k), последняя неделя — стабилизация.",

      "narrative_options": {
        "bullish": "LTH активно накапливают, переход от распределения завершён",
        "bearish": "Темп накопления падает, возможна пауза или разворот",
        "neutral": "Стабилизация после активного накопления Q4 2025"
      },

      "chart_insight": "График подтверждает переход LTH к накоплению после трёх волн распределения"
    }
  ],

  "cross_chart_analysis": {
    "correlations": [
      {
        "charts": ["c1", "c3"],
        "observation": "LTH supply растёт пока drawdown уменьшается — классический паттерн накопления на коррекции"
      }
    ],
    "divergences": [
      {
        "charts": ["c2", "c6"],
        "observation": "STH NUPL негативный, но LTH MVRV всё ещё высокий — разные когорты в разных состояниях"
      }
    ],
    "overall_story": "Графики показывают: LTH накапливают на фоне коррекции, STH в стрессе, институционалы держат позиции"
  }
}
```

## Update session.json

```json
{
  "phase": "story_lining",
  "updated_at": "ISO timestamp"
}
```

## Rules
- **ALWAYS use CLI** for reading series data — Claude loses data when copying large arrays
- Generate both analysis AND rendered chart files
- Provide multiple narrative interpretations — let Story-liner choose
- Focus on what charts SHOW, not what we hope they show
- Note any data quality issues (gaps, anomalies)
- Cross-reference charts to find patterns
