#!/bin/bash
# Ralph Deep Research - Claude Code Loop Runner
#
# Usage:
#   ./loop.sh "Your research query"     Start new research
#   ./loop.sh --resume                  Resume from existing state
#   ./loop.sh --clear                   Clear state and start fresh
#   ./loop.sh --status                  Show current status

set -e

# Configuration
MAX_ITERATIONS=15
STATE_DIR="state"
OUTPUT_DIR="output"
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

show_help() {
    cat << EOF
Ralph Deep Research - Claude Code Runner

Usage:
    ./loop.sh "Your research query"     Start new research
    ./loop.sh --resume                  Resume from existing state
    ./loop.sh --clear                   Clear state and start fresh
    ./loop.sh --status                  Show current status
    ./loop.sh --help                    Show this help

Examples:
    ./loop.sh "Analyze Realty Income Corporation for investment"
    ./loop.sh "Research the AI chip market in 2024"
    ./loop.sh --resume

The script executes the Ralph research pipeline through Claude Code,
managing state in state/ and generating reports in output/.
EOF
}

clear_state() {
    log_warning "Clearing all state..."
    rm -rf "$STATE_DIR"
    rm -rf "$OUTPUT_DIR"
    mkdir -p "$STATE_DIR"
    mkdir -p "$OUTPUT_DIR"
    log_success "State cleared"
}

show_status() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "         Ralph Research Status"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    [ -f "$STATE_DIR/session.json" ] && echo "Session: ✓" || echo "Session: Not started"
    [ -f "$STATE_DIR/initial_context.json" ] && echo "Initial Research: ✓" || echo "Initial Research: Pending"
    [ -f "$STATE_DIR/brief.json" ] && echo "Brief: ✓ Approved" || echo "Brief: Not approved"
    [ -f "$STATE_DIR/plan.json" ] && echo "Plan: ✓ Created" || echo "Plan: Not created"

    round_count=$(ls -d $STATE_DIR/round_* 2>/dev/null | wc -l)
    echo "Rounds completed: $round_count"

    [ -f "$STATE_DIR/coverage.json" ] && echo "Coverage: ✓ Checked" || echo "Coverage: Pending"
    [ -f "$STATE_DIR/aggregation.json" ] && echo "Aggregation: ✓ Complete" || echo "Aggregation: Pending"

    echo ""
    echo "Generated reports:"
    [ -f "$OUTPUT_DIR/report.pdf" ] && echo "  ✓ report.pdf"
    [ -f "$OUTPUT_DIR/report.xlsx" ] && echo "  ✓ report.xlsx"
    [ -f "$OUTPUT_DIR/report.pptx" ] && echo "  ✓ report.pptx"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

initialize() {
    mkdir -p "$STATE_DIR"
    mkdir -p "$OUTPUT_DIR"

    if [ ! -f "$STATE_DIR/session.json" ] && [ -n "$1" ]; then
        cat > "$STATE_DIR/session.json" << EOF
{
    "status": "initialized",
    "started_at": "$(date -Iseconds)",
    "query": "$1"
}
EOF
    fi
}

check_completion() {
    [ -f "$STATE_DIR/report_config.json" ] && \
    ([ -f "$OUTPUT_DIR/report.pdf" ] || [ -f "$OUTPUT_DIR/report.xlsx" ])
}

# Main execution
main() {
    case "$1" in
        --help|-h) show_help; exit 0 ;;
        --clear) clear_state; exit 0 ;;
        --status) show_status; exit 0 ;;
        --resume)
            log_info "Resuming from existing state..."
            initialize ""
            QUERY=""
            ;;
        "")
            log_error "No query provided. Use --help for usage."
            exit 1
            ;;
        *)
            QUERY="$1"
            initialize "$QUERY"
            ;;
    esac

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "         Ralph Deep Research"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "State:  $STATE_DIR/"
    echo "Output: $OUTPUT_DIR/"
    echo "Max iterations: $MAX_ITERATIONS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    for i in $(seq 1 $MAX_ITERATIONS); do
        log_info "=== Iteration $i of $MAX_ITERATIONS ==="

        if check_completion; then
            log_success "Research complete!"
            show_status
            exit 0
        fi

        # Build prompt for Claude Code
        if [ "$i" -eq 1 ] && [ -n "$QUERY" ]; then
            FULL_PROMPT="Read PROMPT.md and execute the Ralph research pipeline.

Query: $QUERY

Start with Phase 1: Initial Research."
        else
            FULL_PROMPT="Read PROMPT.md and continue the Ralph research pipeline.

Check state/ directory to determine current phase and continue.
Signal completion with <promise>COMPLETE</promise> when done."
        fi

        # Run Claude Code
        echo "$FULL_PROMPT" | claude -p \
            --dangerously-skip-permissions \
            --output-format=stream-json \
            --model opus \
            --verbose

        if check_completion; then
            log_success "Research complete!"
            show_status
            exit 0
        fi

        sleep 2
    done

    log_warning "Max iterations reached."
    show_status
    exit 1
}

main "$@"
