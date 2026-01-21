# Style Guide (Warp Capital)

## Visual Identity

### Colors

| Element | Color | Hex |
|---------|-------|-----|
| Primary accent | Red | `#C41E3A` |
| Background | Dark | `#1a1a2e` |
| Text | Light | `#f8f9fa` |
| Secondary text | Gray | `#6b7280` |
| Success | Green | `#22c55e` |
| Warning | Yellow | `#eab308` |
| Danger | Red | `#ef4444` |

### Typography

- **Headers**: Bold, uppercase for section numbers
- **Body**: Clean, readable serif-like font
- **Code/metrics**: Monospace for numbers

### Branding Assets

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

---

## Report Structure

### Warp Market Overview

```
1. Title + Logo
2. Executive Summary (bullet points)
3. Numbered Sections (## 1., ## 2., etc.)
4. Charts (inline with analysis)
5. Scenarios Grid (bear/base/bull/extreme)
6. Recommendations (Pros/Cons)
7. Sources (footnotes style)
8. Footer with logo
```

### Section Format

```html
<section class="report-section">
  <h2><span class="section-number">1</span> Section Title</h2>
  <p>Content with <strong>bold highlights</strong>.</p>

  <div class="chart-container">
    <iframe src="charts/c1_xxx.html" class="chart-iframe"></iframe>
    <p class="chart-note">Source: Glassnode [1]</p>
  </div>

  <p>Analysis continues...</p>
</section>
```

---

## Writing Style

### Tone
- **Professional analytical** — no hype, balanced view
- **Neutral business** — objective, fact-based
- **Quantitative** — support claims with data

### Language Patterns (Russian)

✅ **Use:**
- "Данные ончейн анализа свидетельствуют о том, что..."
- "Примечательно, что..."
- "Резюмируя, можно утверждать, что..."
- "При этом имеется ряд тревожных сигналов..."
- "Наиболее вероятным [X] выступает диапазон..."

❌ **Avoid:**
- Generic marketing language
- One-sided analysis
- Unsubstantiated claims

---

## Terminology Rules

### On-Chain Metrics (Keep English)

| Term | OK to use | Description |
|------|-----------|-------------|
| MVRV | ✅ | Market Value to Realized Value |
| NUPL | ✅ | Net Unrealized Profit/Loss |
| SOPR | ✅ | Spent Output Profit Ratio |
| LTH/STH | ✅ | Long-Term/Short-Term Holders |
| Realized Price | ✅ | Average acquisition price |
| ATH/ATL | ✅ | All-Time High/Low |

### Financial Terms (Keep English)

| Term | OK to use |
|------|-----------|
| ETF | ✅ |
| AUM | ✅ |
| NAV / mNAV | ✅ |
| DAT | ✅ (Digital Asset Treasury) |

### Anglicisms (Use Russian)

| ❌ English | ✅ Russian |
|-----------|-----------|
| basis trade unwind | закрытие базисных сделок |
| breakeven | точка безубыточности |
| fee arbitrage | арбитраж комиссий |
| cost basis | себестоимость |
| outflow/inflow | отток/приток |
| rally | рост, подъём |
| dump | обвал, падение |
| supply squeeze | сжатие предложения |

---

## Technical Analysis Rule

**Warp Capital не использует традиционный теханализ. Фокус на on-chain данных.**

### ❌ Avoid

- RSI, MACD, Bollinger Bands
- Moving averages (50-day MA, 200-day MA)
- Chart patterns (head & shoulders, triangles)
- Support/resistance levels from TA

### ✅ OK

- Aggregated sentiment: "27 из 30 технических сигналов негативные"
- Fear & Greed Index (как индикатор настроений)
- Price relative to ATH (факт, не теханализ)

### ✅ Focus (On-Chain)

- LTH/STH behavior and supply
- MVRV, NUPL, SOPR metrics
- Realized Price levels
- ETF flows, institutional holdings
- Exchange balances

---

## Chart Guidelines

### Chart Types

| Data Type | Chart Type |
|-----------|------------|
| Time series | Line |
| Comparison | Bar |
| Distribution | Pie/Donut |
| Correlation | Dual-axis line |

### Styling

```javascript
const WARP_LAYOUT = {
  template: "plotly_dark",
  paper_bgcolor: "#1a1a2e",
  plot_bgcolor: "#1a1a2e",
  font: { color: "#f8f9fa" },
  title: { font: { color: "#f8f9fa" } }
};
```

### Color Palette

```javascript
const colors = [
  "#3366CC",  // Blue (primary)
  "#DC3912",  // Red
  "#FF9900",  // Orange
  "#109618",  // Green
  "#990099",  // Purple
  "#0099C6"   // Cyan
];
```

### Rules

1. **Solid lines, no markers** for time series
2. **Log scale** for price axis
3. **Dual Y-axis** for price + indicator
4. **Annotations** for key events
5. **Color zones** for NUPL (Capitulation/Hope/Optimism/Euphoria)

---

## Citations

### Format in Text

```
Текст с утверждением.[1] Другое утверждение.[2]
```

### Sources Section

```html
<section class="sources">
  <h2>Источники</h2>
  <ol>
    <li>[1] Source Title - <a href="full-url">full-url</a></li>
    <li>[2] Another Source - <a href="full-url">full-url</a></li>
  </ol>
</section>
```

### Rules

- **Full URLs** — not domain only
- **Verify numbers** — source must contain cited value
- **High confidence** — for key claims
- **Recency** — prefer recent sources

---

## DO NOT

1. ❌ Add disclaimers, footers, or "Generated by" text
2. ❌ Add watermarks or attribution
3. ❌ Use generic marketing language
4. ❌ Skip numerical evidence
5. ❌ Present one-sided analysis
6. ❌ Ignore contradicting data
7. ❌ Mention specific technical indicators (RSI, MACD, etc.)
8. ❌ Use unnecessary anglicisms
9. ❌ Truncate URLs to domain only
10. ❌ Cite numbers not found in source
