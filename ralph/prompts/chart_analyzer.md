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

### 3. Analyze Each Chart with Analytics CLI

**Use the analytics module for statistical analysis — DON'T calculate manually!**

```bash
# Run from ralph/ folder

# Basic statistics
python cli/fetch.py analytics basic_stats '{"file":"research_XXXXX/results/series/BTC_LTH_supply.json"}'

# Trend direction (30-day window)
python cli/fetch.py analytics trend_direction '{"file":"research_XXXXX/results/series/BTC_price.json","window":30}'

# Volatility regime
python cli/fetch.py analytics volatility_regime '{"file":"research_XXXXX/results/series/BTC_price.json"}'

# Current percentile vs history
python cli/fetch.py analytics current_percentile '{"file":"research_XXXXX/results/series/BTC_MVRV.json"}'

# Distance from ATH
python cli/fetch.py analytics distance_from_ath '{"file":"research_XXXXX/results/series/BTC_price.json"}'

# Detect anomalies
python cli/fetch.py analytics detect_anomalies '{"file":"research_XXXXX/results/series/BTC_price.json","z_threshold":2.5}'

# Detect regime changes
python cli/fetch.py analytics detect_regime_change '{"file":"research_XXXXX/results/series/BTC_MVRV.json"}'

# Correlation between two series
python cli/fetch.py analytics correlation '{"file1":"research_XXXXX/results/series/BTC_price.json","file2":"research_XXXXX/results/series/BTC_MVRV.json"}'

# Breakout detection
python cli/fetch.py analytics detect_breakout '{"file":"research_XXXXX/results/series/BTC_price.json","lookback":90}'
```

**Available analytics functions:**
| Function | Purpose |
|----------|---------|
| `basic_stats` | Mean, std, percentiles, current value |
| `trend_direction` | Up/down/sideways with confidence |
| `trend_strength` | 0-1 scale trend strength |
| `volatility_regime` | Low/normal/high/extreme |
| `current_percentile` | Where current value ranks vs history |
| `distance_from_ath` | Drawdown from all-time high |
| `detect_anomalies` | Find outliers by z-score |
| `detect_regime_change` | Find trend reversal points |
| `detect_breakout` | Check if breaking resistance/support |
| `correlation` | Correlation between two series |
| `mvrv_zscore` | MVRV z-score with market phase |

For each chart in chart_data.json, collect analysis results:

```yaml
analysis_per_chart:
  trends:
    - trend_90d: "Use trend_direction with window=90"
    - trend_30d: "Use trend_direction with window=30"
    - trend_7d: "Use trend_direction with window=7"

  patterns:
    - accumulation: "Steady increase (trend_direction up + low volatility)"
    - distribution: "Steady decrease (trend_direction down)"
    - consolidation: "Sideways movement (trend_direction sideways)"
    - reversal: "Use detect_regime_change"
    - spike: "Use detect_anomalies"
    - plateau: "Flat after trend"

  key_values:
    - current: "From basic_stats.current"
    - min: "From basic_stats.min"
    - max: "From basic_stats.max"
    - avg: "From basic_stats.mean"
    - percentile: "From current_percentile"

  visual_summary:
    - "1-2 sentence description based on analytics results"

  narrative_options:
    - bullish: "How to interpret if telling bullish story"
    - bearish: "How to interpret if telling bearish story"
    - neutral: "Balanced interpretation"
```

### 4. Cross-Chart Analysis

**Use analytics correlation to find relationships:**

```bash
# Correlation between price and supply
python cli/fetch.py analytics correlation '{"file1":"research_XXXXX/results/series/BTC_price.json","file2":"research_XXXXX/results/series/BTC_LTH_supply.json"}'

# Find divergences - price vs indicator
python cli/fetch.py analytics find_divergence '{"file1":"research_XXXXX/results/series/BTC_price.json","file2":"research_XXXXX/results/series/BTC_MVRV.json"}'

# Lead/lag analysis - does one series lead another?
python cli/fetch.py analytics lead_lag '{"file1":"research_XXXXX/results/series/BTC_price.json","file2":"research_XXXXX/results/series/BTC_STH_supply.json","max_lag":30}'
```

Look for relationships between charts:
- Do price and supply move together? (use `correlation`)
- Are there divergences between metrics? (use `find_divergence`)
- Does one metric lead another? (use `lead_lag`)
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
