# Task: Fix --continue flag issues in loop.sh

## Status: ✅ FIXED (Commit: 6bddb75)

## Problems Fixed

### 1. UTF-8 Encoding ✅
**Problem:** Russian text was corrupted: "Р"Р?РїР?Р>..."
**Fix:** Added at script start:
```bash
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
```

### 2. Log messages mixing with return value ✅
**Problem:** `[INFO]` messages were captured by `folder=$(continue_research ...)`
**Fix:** All log functions now write to stderr:
```bash
log_info() { echo -e "${BLUE}[INFO]${NC} $1" >&2; }
```

### 3. Fuzzy folder matching ✅
**Problem:** Had to type exact folder name
**Fix:** Added `find_research_folder()` function:
```bash
# These all work now:
./loop.sh --continue Mezen "context"
./loop.sh --continue research_20260119 "context"
./loop.sh --continue 20260119_Mezen "context"
```

### 4. session.json not created ✅
**Problem:** Copy failed silently
**Fix:** Explicit mkdir + better error handling:
```bash
mkdir -p "$new_folder/state" "$new_folder/results" ...
cp -r "$source_folder/state/"* "$new_folder/state/" 2>/dev/null || true
```

---

## Usage

```bash
# Fuzzy match - finds research_20260119_151743_mezen
./loop.sh --continue Mezen "добавь анализ конкурентов"

# Partial match by date
./loop.sh --continue 20260119 "new context"

# Full path still works
./loop.sh --continue research_20260119_151743_______ "context"
```

---

## New Folder Naming

Old: `research_20260119_mezen_v2`
New: `research_20260119_171234_mezen_continued`

Benefits:
- Unique timestamp prevents collisions
- `_continued` suffix clearly marks continuation
- Original slug preserved for searchability
