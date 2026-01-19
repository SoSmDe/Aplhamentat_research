# Task: Fix --continue to actually execute new research

## Status: ✅ FIXED

## Problem (was)
When using `--continue` with additional_context, the system:
1. ✅ Correctly copied previous state
2. ✅ Added additional_context to session.json
3. ❌ BUT did NOT create new tasks based on additional_context
4. Result: same report regenerated without new research

## Root Cause
- `continue_research()` preserved old coverage (90%) and tasks_completed
- Planner saw coverage >= target and skipped to aggregation
- No new tasks were created for updated scope items

## Fix Applied (commit 4588fa8)

### 1. loop.sh changes:
- Reset `coverage.current = 0` for continuation
- Reset `coverage.by_scope = {}`
- Clear `tasks_pending = []` (keep tasks_completed)
- Set `is_continuation = true` flag in session.json

### 2. planner.md changes:
- Added Section "0. Check for Continuation Mode (CRITICAL)"
- Instructions to detect `is_continuation: true`
- Create NEW tasks with `c_` prefix for updated scope items
- Rules: NEVER skip planning in continuation mode

## Expected Behavior Now
`--continue "analyze Konstantin Molodych X account"` should:
1. Brief Builder parses additional_context ✅
2. Creates/updates scope items with `updated_in_continuation: true` ✅
3. Coverage reset to 0 in session.json ✅ (NEW)
4. Planner creates NEW tasks (c_r1, c_d1) for updated scope items ✅ (NEW)
5. Execution runs new tasks
6. Aggregation merges old + new results
7. Report reflects new findings
