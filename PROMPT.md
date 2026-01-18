# Ralph Deep Research - Build Task

## Context
You are building a multi-agent deep research system.
All specifications are in the `docs/` folder:
- `docs/ralph_prd.md` - Product Requirements Document
- `docs/ARCHITECTURE.md` - Technical architecture
- `docs/DATA_SCHEMAS.md` - JSON schemas for all data structures
- `docs/PROMPTS.md` - System prompts for each agent
- `CLAUDE.md` - Project overview and conventions

## Current Task
Read `IMPLEMENTATION_PLAN.md` and complete the highest priority unchecked item.

After completing each task:
1. Run tests: `pytest tests/ -v`
2. Commit changes: `git add -A && git commit -m "feat: <description>"`
3. Mark item as [x] in IMPLEMENTATION_PLAN.md

## Rules
- Follow CLAUDE.md conventions strictly
- Use type hints in all Python code
- Write tests for new functionality
- Keep functions small and focused
- Use async/await for I/O operations

## Completion
When ALL items in IMPLEMENTATION_PLAN.md are checked [x], output:
<promise>COMPLETE</promise>
