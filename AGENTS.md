## Build & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
python -m uvicorn main:app --reload --port 8000

# Start without reload
python main.py
```

## Validation

Run these after implementing to get immediate feedback:

- Tests: `python -m pytest tests/ -v --tb=short`
- Typecheck: `python -m mypy src/ --ignore-missing-imports`
- Lint: `python -m black src/ tests/ --check`

## Operational Notes

- Server runs at http://localhost:8000 (docs at /docs)
- Health check: GET /health
- Uvicorn binary may not be in PATH; use `python -m uvicorn` instead

### Codebase Patterns

- Ralph Pattern: Execute task → Save result → Clear context → Next task
- Model selection: Opus for reasoning agents, Sonnet for data extraction
- State flow: CREATED → INITIAL_RESEARCH → BRIEF → PLANNING → EXECUTING → AGGREGATING → REPORTING → DONE
