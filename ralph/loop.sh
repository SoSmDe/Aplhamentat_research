#!/bin/bash
# Ralph Deep Research - Claude Code Loop Runner
#
# Usage:
#   ./loop.sh "Your research query"     Start new research
#   ./loop.sh --resume [folder]         Resume from existing research
#   ./loop.sh --clear [folder]          Clear specific research folder
#   ./loop.sh --status [folder]         Show status
#   ./loop.sh --list                    List all research folders

set -e

# Configuration
MAX_ITERATIONS=15
PROMPTS_DIR="../src/prompts"
PROMPT_FILE="PROMPT.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Generate slug from query
generate_slug() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/_/g' | cut -c1-30
}

# Generate research folder name
generate_research_folder() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local slug=$(generate_slug "$1")
    echo "research_${timestamp}_${slug}"
}

# Find latest research folder
find_latest_research() {
    ls -d research_* 2>/dev/null | sort -r | head -n1
}

show_help() {
    cat << EOF
Ralph Deep Research - Claude Code Runner

Usage:
    ./loop.sh "Your research query"     Start new research
    ./loop.sh --resume [folder]         Resume from existing (latest if no folder)
    ./loop.sh --clear [folder]          Clear specific research folder
    ./loop.sh --status [folder]         Show status (latest if no folder)
    ./loop.sh --list                    List all research folders
    ./loop.sh --help                    Show this help

Examples:
    ./loop.sh "Analyze Realty Income Corporation for investment"
    ./loop.sh "Research the AI chip market in 2024"
    ./loop.sh --resume
    ./loop.sh --resume research_20260119_realty_income

Research data is stored in: ralph/research_YYYYMMDD_HHMMSS_slug/
    state/      JSON state files
    results/    Agent outputs
    questions/  Generated questions
    output/     Final reports (PDF, Excel, PPTX)
EOF
}

list_research() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "         Research Folders"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    for dir in research_*; do
        if [ -d "$dir" ]; then
            query=""
            [ -f "$dir/state/session.json" ] && query=$(grep -o '"query": "[^"]*"' "$dir/state/session.json" | cut -d'"' -f4 | head -c50)
            echo "  $dir"
            [ -n "$query" ] && echo "    Query: $query..."
        fi
    done
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

clear_research() {
    local folder="$1"
    if [ -z "$folder" ]; then
        folder=$(find_latest_research)
    fi
    if [ -z "$folder" ] || [ ! -d "$folder" ]; then
        log_error "Research folder not found: $folder"
        exit 1
    fi
    log_warning "Clearing research: $folder"
    rm -rf "$folder"
    log_success "Research cleared"
}

show_status() {
    local folder="$1"
    if [ -z "$folder" ]; then
        folder=$(find_latest_research)
    fi
    if [ -z "$folder" ] || [ ! -d "$folder" ]; then
        log_error "Research folder not found"
        exit 1
    fi

    local STATE_DIR="$folder/state"
    local OUTPUT_DIR="$folder/output"

    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "         Ralph Research Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Folder: $folder"
    echo ""

    [ -f "$STATE_DIR/session.json" ] && echo "Session: ✓" || echo "Session: Not started"
    [ -f "$STATE_DIR/initial_context.json" ] && echo "Initial Research: ✓" || echo "Initial Research: Pending"
    [ -f "$STATE_DIR/brief.json" ] && echo "Brief: ✓ Approved" || echo "Brief: Not approved"
    [ -f "$STATE_DIR/plan.json" ] && echo "Plan: ✓ Created" || echo "Plan: Not created"

    round_count=$(ls -d "$STATE_DIR/round_"* 2>/dev/null | wc -l)
    echo "Rounds completed: $round_count"

    [ -f "$STATE_DIR/coverage.json" ] && echo "Coverage: ✓ Checked" || echo "Coverage: Pending"
    [ -f "$STATE_DIR/questions_plan.json" ] && echo "Questions Plan: ✓" || echo "Questions Plan: Pending"
    [ -f "$STATE_DIR/aggregation.json" ] && echo "Aggregation: ✓ Complete" || echo "Aggregation: Pending"

    echo ""
    echo "Results:"
    [ -d "$folder/results" ] && ls "$folder/results"/*.json 2>/dev/null | wc -l | xargs -I{} echo "  {} result files"

    echo ""
    echo "Generated reports:"
    [ -f "$OUTPUT_DIR/report.pdf" ] && echo "  ✓ report.pdf"
    [ -f "$OUTPUT_DIR/report.xlsx" ] && echo "  ✓ report.xlsx"
    [ -f "$OUTPUT_DIR/report.pptx" ] && echo "  ✓ report.pptx"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

initialize() {
    local folder="$1"
    local query="$2"

    mkdir -p "$folder/state"
    mkdir -p "$folder/results"
    mkdir -p "$folder/questions"
    mkdir -p "$folder/output"

    if [ ! -f "$folder/state/session.json" ] && [ -n "$query" ]; then
        cat > "$folder/state/session.json" << EOF
{
    "status": "initialized",
    "started_at": "$(date -Iseconds)",
    "query": "$query",
    "research_folder": "$folder"
}
EOF
    fi
}

check_completion() {
    local folder="$1"
    [ -f "$folder/state/report_config.json" ] && \
    ([ -f "$folder/output/report.pdf" ] || [ -f "$folder/output/report.xlsx" ])
}

# Main execution
main() {
    case "$1" in
        --help|-h) show_help; exit 0 ;;
        --list) list_research; exit 0 ;;
        --clear) clear_research "$2"; exit 0 ;;
        --status) show_status "$2"; exit 0 ;;
        --resume)
            RESEARCH_FOLDER="$2"
            if [ -z "$RESEARCH_FOLDER" ]; then
                RESEARCH_FOLDER=$(find_latest_research)
            fi
            if [ -z "$RESEARCH_FOLDER" ] || [ ! -d "$RESEARCH_FOLDER" ]; then
                log_error "No research folder found to resume"
                exit 1
            fi
            log_info "Resuming: $RESEARCH_FOLDER"
            QUERY=""
            ;;
        "")
            log_error "No query provided. Use --help for usage."
            exit 1
            ;;
        *)
            QUERY="$1"
            RESEARCH_FOLDER=$(generate_research_folder "$QUERY")
            initialize "$RESEARCH_FOLDER" "$QUERY"
            log_info "Created: $RESEARCH_FOLDER"
            ;;
    esac

    STATE_DIR="$RESEARCH_FOLDER/state"
    OUTPUT_DIR="$RESEARCH_FOLDER/output"
    RESULTS_DIR="$RESEARCH_FOLDER/results"
    QUESTIONS_DIR="$RESEARCH_FOLDER/questions"

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "         Ralph Deep Research"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Research: $RESEARCH_FOLDER"
    echo "Prompts:  $PROMPTS_DIR/"
    echo "Max iterations: $MAX_ITERATIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    for i in $(seq 1 $MAX_ITERATIONS); do
        log_info "=== Iteration $i of $MAX_ITERATIONS ==="

        if check_completion "$RESEARCH_FOLDER"; then
            log_success "Research complete!"
            show_status "$RESEARCH_FOLDER"
            exit 0
        fi

        # Build prompt for Claude Code
        if [ "$i" -eq 1 ] && [ -n "$QUERY" ]; then
            FULL_PROMPT="Read PROMPT.md and execute the Ralph research pipeline.

Research folder: $RESEARCH_FOLDER
Prompts: $PROMPTS_DIR/
Query: $QUERY

Start with Phase 1: Initial Research."
        else
            FULL_PROMPT="Read PROMPT.md and continue the Ralph research pipeline.

Research folder: $RESEARCH_FOLDER
Prompts: $PROMPTS_DIR/

Check $STATE_DIR/ to determine current phase and continue.
Signal completion with <promise>COMPLETE</promise> when done."
        fi

        # Run Claude Code
        echo "$FULL_PROMPT" | claude -p \
            --dangerously-skip-permissions \
            --output-format=stream-json \
            --model opus \
            --verbose

        if check_completion "$RESEARCH_FOLDER"; then
            log_success "Research complete!"
            show_status "$RESEARCH_FOLDER"
            exit 0
        fi

        sleep 2
    done

    log_warning "Max iterations reached."
    show_status "$RESEARCH_FOLDER"
    exit 1
}

main "$@"
