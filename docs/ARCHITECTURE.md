# Architecture

## Design Principles

### 1. State Machine Pattern
Каждая фаза исследования — отдельное состояние. Claude Code читает текущее состояние, выполняет работу, обновляет состояние, завершает итерацию.

```
session.json (source of truth)
     │
     ├── phase: "execution"      ← текущая фаза
     ├── execution.tasks_pending ← что осталось
     ├── execution.tasks_completed ← что сделано
     └── coverage.current        ← % покрытия brief
```

### 2. Single Source of Truth
Все данные хранятся в `state/session.json`. Агенты читают и пишут только в этот файл (и связанные state файлы).

### 3. Idempotent Phases
Каждая фаза может быть перезапущена без side effects. Если что-то упало — просто `./loop.sh --resume`.

### 4. Separation of Concerns
- **Prompts** — инструкции для агентов (markdown)
- **CLI Tools** — API клиенты и утилиты (Python)
- **Templates** — визуальное оформление (HTML/CSS)
- **State** — данные исследования (JSON)

---

## Component Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              loop.sh                                      │
│                         (Orchestrator)                                    │
└──────────────────────────────────────────────────────────────────────────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│   PROMPT.md   │       │  session.json │       │   prompts/*   │
│ (State Machine│       │ (State Store) │       │   (Agents)    │
│  Definition)  │       │               │       │               │
└───────────────┘       └───────────────┘       └───────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
        ┌───────────┐   ┌───────────┐   ┌───────────┐
        │ cli/      │   │ templates/│   │ integr./  │
        │ fetch.py  │   │ Warp/     │   │ crypto/   │
        │ render_   │   │ html/     │   │ blocklens │
        │ charts.py │   │           │   │ coingecko │
        └───────────┘   └───────────┘   └───────────┘
```

---

## Data Flow

### Phase: initial_research
```
User Query
    │
    ▼
┌─────────────────┐     ┌─────────────────┐
│ Web Search      │────▶│ initial_context │
│ (quick context) │     │ .json           │
└─────────────────┘     └─────────────────┘
    │
    ▼
Extract: tags, entities, key_facts
```

### Phase: execution
```
plan.json (tasks)
    │
    ├─▶ Overview Tasks ─▶ overview_*.json
    │
    ├─▶ Data Tasks ────▶ data_*.json
    │   │
    │   └─▶ CLI APIs ─▶ series/*.json (time series)
    │
    └─▶ Research Tasks ─▶ research_*.json
```

### Phase: aggregation
```
All results/*.json
    │
    ▼
┌─────────────────┐
│   Aggregator    │
│                 │
│ - Synthesize    │
│ - Deduplicate   │
│ - Build recs    │
└─────────────────┘
    │
    ├─▶ aggregation.json (main content)
    ├─▶ chart_data.json (chart specs)
    ├─▶ citations.json (all sources)
    └─▶ glossary.json (terms)
```

### Phase: reporting
```
aggregation.json + chart_data.json + story.json
    │
    ▼
┌─────────────────┐
│    Reporter     │
│                 │
│ - Load template │
│ - Embed charts  │
│ - Format text   │
└─────────────────┘
    │
    ▼
output/report.html
```

---

## File Structure Detail

```
research_XXXXX/
│
├── state/                      # State files (JSON)
│   ├── session.json            # ★ Main state (source of truth)
│   ├── initial_context.json    # Quick research results
│   ├── brief.json              # Research scope and preferences
│   ├── plan.json               # Task decomposition
│   ├── coverage.json           # Scope coverage tracking
│   ├── questions_plan.json     # Follow-up questions
│   ├── aggregation.json        # Synthesized findings
│   ├── chart_data.json         # Chart specifications
│   ├── citations.json          # All sources
│   ├── glossary.json           # Term definitions
│   ├── story.json              # (deep_dive) Narrative structure
│   └── charts_analyzed.json    # (deep_dive) Chart analysis
│
├── results/                    # Agent outputs
│   ├── overview_1.json         # Overview agent results
│   ├── data_1.json             # Data agent results
│   ├── data_2.json
│   ├── research_1.json         # Research agent results
│   └── series/                 # Time series data
│       ├── BTC_price.json
│       ├── BTC_LTH_MVRV.json
│       └── ...
│
├── questions/                  # Generated questions
│   └── questions.json
│
└── output/                     # Final output
    ├── report.html             # Main report
    ├── report.pdf              # (optional) PDF version
    ├── data_pack.xlsx          # (optional) Excel data
    └── charts/                 # (deep_dive) Pre-rendered charts
        ├── c1_*.html
        ├── c2_*.html
        └── ...
```

---

## Error Handling

### Retry Logic
```
loop.sh:
  while phase != "complete":
      run_claude_code()
      if error:
          log_error()
          continue  # retry same phase
```

### Recovery
```bash
# Check current state
./loop.sh --status

# Resume from last successful phase
./loop.sh --resume

# Force specific phase (debug)
./loop.sh --set-phase research_xxx execution
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Phase loops forever | Task not completing | Check agent output, fix prompt |
| Empty chart files | Missing series data | Verify data_*.json has source_files |
| Wrong style | style not detected | Check brief.json preferences |
| Missing citations | URL truncated | Verify full URLs in results |

---

## Performance Considerations

### Token Usage
- `deep_dive` mode: ~100-200K tokens total
- `standard` mode: ~50-80K tokens total
- Chart rendering: ~10-20K tokens (CLI offload)

### Optimization
1. **CLI offload** — heavy data processing in Python, not Claude
2. **Series files** — large arrays stored separately, not in main JSON
3. **Template system** — pre-built HTML, just fill placeholders
4. **Pre-rendered charts** — Plotly HTML files, embed via iframe
