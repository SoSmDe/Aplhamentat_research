#!/bin/bash
# Ralph Deep Research - State Machine Runner

set -e

MAX_ITERATIONS=20
PROMPTS_DIR="../src/prompts"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_phase() { echo -e "${CYAN}[PHASE]${NC} $1"; }

generate_slug() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | cut -c1-30
}

generate_research_folder() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local slug=$(generate_slug "$1")
    echo "research_${timestamp}_${slug}"
}

find_latest_research() {
    ls -d research_* 2>/dev/null | sort -r | head -n1
}

show_help() {
    cat << EOF
Ralph Deep Research - State Machine Runner

Usage:
    ./loop.sh "Your research query"     Start new research
    ./loop.sh --resume [folder]         Resume (latest if no folder)
    ./loop.sh --status [folder]         Show detailed status with progress
    ./loop.sh --list                    List all research folders
    ./loop.sh --search <query>          Search by tags, entities, query text
    ./loop.sh --clear [folder]          Delete research folder
    ./loop.sh --set-phase <f> <p>       Manually set phase (debug)

Examples:
    ./loop.sh "Analyze Tesla stock"
    ./loop.sh --search "investment"
    ./loop.sh --search "reit"
    ./loop.sh --status

Phases:
    initial_research → brief_builder → planning → execution ⟷
    questions_review → aggregation → reporting → complete
EOF
}

get_phase() {
    local folder="$1"
    jq -r '.phase // "initial_research"' "$folder/state/session.json" 2>/dev/null || echo "initial_research"
}

get_iteration() {
    local folder="$1"
    jq -r '.execution.iteration // 0' "$folder/state/session.json" 2>/dev/null || echo "0"
}

# Progress bar function
progress_bar() {
    local percent=$1
    local width=40
    local filled=$((percent * width / 100))
    local empty=$((width - filled))
    printf "["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] %d%%" "$percent"
}

show_status() {
    local folder="${1:-$(find_latest_research)}"
    [ -z "$folder" ] || [ ! -d "$folder" ] && { log_error "No research folder found"; exit 1; }

    # Read session data
    local session="$folder/state/session.json"
    [ ! -f "$session" ] && { echo "Session not initialized"; return; }

    local query=$(jq -r '.query' "$session")
    local phase=$(jq -r '.phase' "$session")
    local iteration=$(jq -r '.execution.iteration // 0' "$session")
    local max_iter=$(jq -r '.execution.max_iterations // 5' "$session")
    local coverage=$(jq -r '.coverage.current // 0' "$session")
    local target=$(jq -r '.coverage.target // 80' "$session")
    local tasks_done=$(jq -r '.execution.tasks_completed | length // 0' "$session")
    local tasks_pending=$(jq -r '.execution.tasks_pending | length // 0' "$session")
    local total_tasks=$((tasks_done + tasks_pending))

    # Calculate progress percentage
    local progress=0
    case "$phase" in
        "initial_research") progress=5 ;;
        "brief_builder") progress=15 ;;
        "planning") progress=25 ;;
        "execution") progress=$((25 + (coverage * 50 / 100))) ;;
        "questions_review") progress=$((25 + (coverage * 50 / 100))) ;;
        "aggregation") progress=85 ;;
        "reporting") progress=95 ;;
        "complete") progress=100 ;;
    esac

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "                      Ralph Deep Research"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "  Folder: $folder"
    echo "  Query:  $query"
    echo ""
    echo "  Progress: $(progress_bar $progress)"
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────────┐"
    echo "  │ Phases                                                      │"
    echo "  ├─────────────────────────────────────────────────────────────┤"

    # Phase list with status
    local phases=("initial_research" "brief_builder" "planning" "execution" "questions_review" "aggregation" "reporting" "complete")
    local phase_names=("Initial Research" "Brief Builder" "Planning" "Execution" "Questions Review" "Aggregation" "Reporting" "Complete")

    for i in "${!phases[@]}"; do
        local p="${phases[$i]}"
        local name="${phase_names[$i]}"
        local icon="○"
        local extra=""

        if [ "$p" = "$phase" ]; then
            icon="●"
            extra=" ← current"
            [ "$p" = "execution" ] && extra=" ← current (iteration $iteration/$max_iter)"
        elif [[ " initial_research brief_builder planning " =~ " $p " ]] && \
             [[ " execution questions_review aggregation reporting complete " =~ " $phase " ]]; then
            icon="✓"
        elif [[ " initial_research brief_builder " =~ " $p " ]] && \
             [[ " planning execution questions_review aggregation reporting complete " =~ " $phase " ]]; then
            icon="✓"
        elif [ "$p" = "initial_research" ] && [ "$phase" != "initial_research" ]; then
            icon="✓"
        fi

        printf "  │  %s %-20s %s\n" "$icon" "$name" "$extra"
    done

    echo "  └─────────────────────────────────────────────────────────────┘"
    echo ""

    # Coverage bar
    if [ "$coverage" -gt 0 ] || [ "$phase" = "execution" ] || [ "$phase" = "questions_review" ]; then
        echo "  ┌─────────────────────────────────────────────────────────────┐"
        printf "  │ Coverage: %d%% / %d%% target                              │\n" "$coverage" "$target"
        echo "  ├─────────────────────────────────────────────────────────────┤"

        # Per-scope coverage if available
        local scopes=$(jq -r '.coverage.by_scope // {} | keys[]' "$session" 2>/dev/null)
        if [ -n "$scopes" ]; then
            for scope in $scopes; do
                local scope_cov=$(jq -r ".coverage.by_scope[\"$scope\"]" "$session")
                local bar_width=20
                local filled=$((scope_cov * bar_width / 100))
                local bar=$(printf "%${filled}s" | tr ' ' '█')
                local empty=$(printf "%$((bar_width - filled))s" | tr ' ' '░')
                printf "  │  %s%s %-15s %3d%%\n" "$bar" "$empty" "$scope" "$scope_cov"
            done
        fi

        echo "  └─────────────────────────────────────────────────────────────┘"
        echo ""
    fi

    # Tasks
    if [ "$total_tasks" -gt 0 ]; then
        echo "  ┌─────────────────────────────────────────────────────────────┐"
        printf "  │ Tasks: %d/%d completed                                     │\n" "$tasks_done" "$total_tasks"
        echo "  ├─────────────────────────────────────────────────────────────┤"

        # Completed tasks
        local completed=$(jq -r '.execution.tasks_completed[]?' "$session" 2>/dev/null)
        for task in $completed; do
            printf "  │  ✓ %s\n" "$task"
        done

        # Pending tasks
        local pending=$(jq -r '.execution.tasks_pending[]?' "$session" 2>/dev/null)
        for task in $pending; do
            printf "  │  ○ %s\n" "$task"
        done

        echo "  └─────────────────────────────────────────────────────────────┘"
        echo ""
    fi

    # Tags
    local tags=$(jq -r '.tags // [] | join(", ")' "$session" 2>/dev/null)
    if [ -n "$tags" ] && [ "$tags" != "" ]; then
        echo "  Tags: $tags"
        echo ""
    fi

    # Output files
    echo "  ┌─────────────────────────────────────────────────────────────┐"
    echo "  │ Output                                                      │"
    echo "  ├─────────────────────────────────────────────────────────────┤"
    [ -f "$folder/output/report.pdf" ] && echo "  │  ✓ report.pdf" || echo "  │  ○ report.pdf"
    [ -f "$folder/output/report.xlsx" ] && echo "  │  ✓ report.xlsx" || echo "  │  ○ report.xlsx"
    [ -f "$folder/output/report.pptx" ] && echo "  │  ✓ report.pptx" || echo "  │  ○ report.pptx"
    echo "  └─────────────────────────────────────────────────────────────┘"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
}

search_research() {
    local query="$1"
    [ -z "$query" ] && { log_error "Usage: --search <query>"; exit 1; }

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "  Search: \"$query\""
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    local found=0
    for dir in research_*; do
        [ -d "$dir" ] || continue
        local session="$dir/state/session.json"
        [ -f "$session" ] || continue

        # Search in query, tags, entities
        local match=$(jq -r "
            .query + \" \" +
            (.tags // [] | join(\" \")) + \" \" +
            (.entities // [] | map(.name) | join(\" \"))
        " "$session" | grep -i "$query" || true)

        if [ -n "$match" ]; then
            found=$((found + 1))
            local q=$(jq -r '.query' "$session" | cut -c1-50)
            local phase=$(jq -r '.phase' "$session")
            local tags=$(jq -r '.tags // [] | join(", ")' "$session")
            local date=$(echo "$dir" | grep -oE '[0-9]{8}' | head -1)

            echo "  📁 $dir"
            echo "     Query: $q..."
            echo "     Phase: $phase"
            echo "     Tags:  $tags"
            echo "     Date:  ${date:0:4}-${date:4:2}-${date:6:2}"
            echo ""
        fi
    done

    if [ "$found" -eq 0 ]; then
        echo "  No research found matching \"$query\""
    else
        echo "  Found: $found research(es)"
    fi
    echo ""
    echo "════════════════════════════════════════════════════════════════"
}

list_research() {
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "         Research Folders"
    echo "════════════════════════════════════════════════════════════════"

    for dir in research_*; do
        [ -d "$dir" ] || continue
        local session="$dir/state/session.json"
        if [ -f "$session" ]; then
            local phase=$(get_phase "$dir")
            local query=$(jq -r '.query // "?"' "$session" 2>/dev/null | cut -c1-40)
            local tags=$(jq -r '.tags // [] | join(", ")' "$session" 2>/dev/null)
            echo ""
            echo "  📁 $dir"
            echo "     Phase: $phase"
            echo "     Query: $query..."
            [ -n "$tags" ] && [ "$tags" != "" ] && echo "     Tags:  $tags"
        fi
    done
    echo ""
    echo "════════════════════════════════════════════════════════════════"
}

clear_research() {
    local folder="${1:-$(find_latest_research)}"
    [ -z "$folder" ] && { log_error "No folder specified"; exit 1; }
    log_warning "Deleting: $folder"
    rm -rf "$folder"
    log_success "Deleted"
}

set_phase() {
    local folder="$1"
    local phase="$2"
    [ -z "$folder" ] || [ -z "$phase" ] && { log_error "Usage: --set-phase <folder> <phase>"; exit 1; }

    jq --arg p "$phase" '.phase = $p | .updated_at = now' "$folder/state/session.json" > tmp.json
    mv tmp.json "$folder/state/session.json"
    log_success "Phase set to: $phase"
}

initialize() {
    local folder="$1"
    local query="$2"

    mkdir -p "$folder/state" "$folder/results" "$folder/questions" "$folder/output"

    cat > "$folder/state/session.json" << EOF
{
  "id": "$folder",
  "query": "$query",
  "phase": "initial_research",
  "tags": [],
  "entities": [],
  "execution": {
    "iteration": 0,
    "max_iterations": 5,
    "tasks_pending": [],
    "tasks_completed": []
  },
  "coverage": {
    "current": 0,
    "target": 80,
    "by_scope": {}
  },
  "created_at": "$(date -Iseconds)",
  "updated_at": "$(date -Iseconds)"
}
EOF
}

run_loop() {
    local folder="$1"
    local query="$2"

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "                      Ralph Deep Research"
    echo "════════════════════════════════════════════════════════════════"
    echo "  Folder:  $folder"
    echo "  Query:   $query"
    echo "════════════════════════════════════════════════════════════════"
    echo ""

    for i in $(seq 1 $MAX_ITERATIONS); do
        local phase=$(get_phase "$folder")
        local iteration=$(get_iteration "$folder")

        log_phase "[$i/$MAX_ITERATIONS] Phase: $phase (iteration: $iteration)"

        if [ "$phase" = "complete" ]; then
            log_success "Research complete!"
            show_status "$folder"
            return 0
        fi

        if [ "$phase" = "failed" ]; then
            log_error "Research failed. Check logs."
            return 1
        fi

        # Run Claude Code
        claude --dangerously-skip-permissions \
               --model opus \
               "Read PROMPT.md. Execute phase '$phase'.

Research folder: $folder
Prompts: $PROMPTS_DIR/

Read state/session.json, execute current phase, update phase, save session.json."

        sleep 1
    done

    log_warning "Max loop iterations reached"
    show_status "$folder"
    return 1
}

main() {
    case "$1" in
        --help|-h) show_help; exit 0 ;;
        --list) list_research; exit 0 ;;
        --status) show_status "$2"; exit 0 ;;
        --search) search_research "$2"; exit 0 ;;
        --clear) clear_research "$2"; exit 0 ;;
        --set-phase) set_phase "$2" "$3"; exit 0 ;;
        --resume)
            folder="${2:-$(find_latest_research)}"
            [ -z "$folder" ] || [ ! -d "$folder" ] && { log_error "No research to resume"; exit 1; }
            query=$(jq -r '.query' "$folder/state/session.json")
            run_loop "$folder" "$query"
            ;;
        "")
            log_error "No query provided. Use --help."
            exit 1
            ;;
        *)
            query="$1"
            folder=$(generate_research_folder "$query")
            initialize "$folder" "$query"
            log_info "Created: $folder"
            run_loop "$folder" "$query"
            ;;
    esac
}

main "$@"
