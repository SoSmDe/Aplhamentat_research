"""
Ralph Deep Research - Base Agent (Claude Code Native)

Abstract base class for all research agents.
Implements the Ralph Pattern: Execute → Save → Clear → Next.

Claude Code Native Workflow:
- Agents are prompt-driven (src/prompts/*.md)
- Claude Code executes prompts directly
- State is saved to JSON files following Ralph Pattern
- No LLM wrapper needed - Claude Code IS Claude
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from src.config.timeouts import get_timeout
from src.tools.errors import InvalidInputError
from src.tools.logging import get_logger

# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Path to state directory (Ralph Pattern)
STATE_DIR = Path(__file__).parent.parent.parent / "state"


class StateManager:
    """
    Manages state persistence for Claude Code workflow.

    Saves/loads JSON files following Ralph Pattern:
    - state/session.json - Current session info
    - state/brief.json - User-approved research brief
    - state/plan.json - Current research plan
    - state/round_N/ - Per-round results
    - state/aggregation.json - Final aggregated results
    """

    def __init__(self, session_id: str | None = None):
        self.session_id = session_id
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        """Create state directory if it doesn't exist."""
        STATE_DIR.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        filename: str,
        data: dict[str, Any],
        round_num: int | None = None,
    ) -> Path:
        """Save state to JSON file."""
        if round_num is not None:
            round_dir = STATE_DIR / f"round_{round_num}"
            round_dir.mkdir(exist_ok=True)
            filepath = round_dir / filename
        else:
            filepath = STATE_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

        return filepath

    def load(
        self,
        filename: str,
        round_num: int | None = None,
    ) -> dict[str, Any] | None:
        """Load state from JSON file."""
        if round_num is not None:
            filepath = STATE_DIR / f"round_{round_num}" / filename
        else:
            filepath = STATE_DIR / filename

        if not filepath.exists():
            return None

        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_rounds(self) -> list[int]:
        """List completed round numbers."""
        rounds = []
        for path in STATE_DIR.iterdir():
            if path.is_dir() and path.name.startswith("round_"):
                try:
                    num = int(path.name.split("_")[1])
                    rounds.append(num)
                except (IndexError, ValueError):
                    pass
        return sorted(rounds)

    def clear(self) -> None:
        """Clear all state (start fresh)."""
        import shutil
        if STATE_DIR.exists():
            shutil.rmtree(STATE_DIR)
        self._ensure_state_dir()


class BaseAgent(ABC):
    """
    Abstract base class for Ralph agents (Claude Code native).

    Provides:
    - System prompt loading from markdown files
    - State persistence following Ralph Pattern
    - Timeout configuration
    - Structured logging

    Claude Code executes agents by:
    1. Loading prompt from src/prompts/{agent_name}.md
    2. Processing with web_search and other tools
    3. Saving results via StateManager
    4. Moving to next agent
    """

    def __init__(self, state_manager: StateManager | None = None) -> None:
        self._state = state_manager or StateManager()
        self._logger = get_logger(f"agents.{self.agent_name}")
        self._system_prompt: str | None = None

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Return agent name for prompt loading and logging."""
        pass

    @abstractmethod
    def get_prompt_context(self, context: dict[str, Any]) -> str:
        """Get the context string to append to the system prompt."""
        pass

    @property
    def system_prompt(self) -> str:
        """Get system prompt for this agent."""
        if self._system_prompt is None:
            self._system_prompt = self._load_prompt()
        return self._system_prompt

    @property
    def timeout_seconds(self) -> float:
        """Get timeout for this agent from configuration."""
        return get_timeout(self.agent_name)

    def _load_prompt(self) -> str:
        """Load system prompt from markdown file."""
        prompt_path = PROMPTS_DIR / f"{self.agent_name}.md"

        if not prompt_path.exists():
            self._logger.warning("Prompt file not found", prompt_path=str(prompt_path))
            return ""

        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def get_full_prompt(self, context: dict[str, Any]) -> str:
        """Get full prompt with context for Claude Code execution."""
        base = self.system_prompt
        ctx = self.get_prompt_context(context)
        return f"{base}\n\n---\n\n## Current Context\n\n{ctx}"

    def save_result(
        self,
        filename: str,
        result: dict[str, Any],
        round_num: int | None = None,
    ) -> Path:
        """Save result to state storage (Ralph Pattern)."""
        filepath = self._state.save(filename, result, round_num)
        self._logger.info("Result saved", filename=filename, round=round_num)
        return filepath

    def load_state(
        self,
        filename: str,
        round_num: int | None = None,
    ) -> dict[str, Any] | None:
        """Load state from storage."""
        return self._state.load(filename, round_num)

    def validate_input(self, context: dict[str, Any]) -> None:
        """Validate input context. Override in subclass for custom validation."""
        pass

    @property
    def output_filename(self) -> str:
        """Default output filename for this agent's results."""
        return f"{self.agent_name}.json"


class StateFiles:
    """Constants for state file names."""

    SESSION = "session.json"
    INITIAL_CONTEXT = "initial_context.json"
    BRIEF = "brief.json"
    CONVERSATION = "conversation.json"
    PLAN = "plan.json"
    COVERAGE = "coverage.json"
    DATA_RESULTS = "data_results.json"
    RESEARCH_RESULTS = "research_results.json"
    AGGREGATION = "aggregation.json"
    REPORT_CONFIG = "report_config.json"


def get_state_manager(session_id: str | None = None) -> StateManager:
    """Factory function for StateManager."""
    return StateManager(session_id)


def load_agent_prompt(agent_name: str) -> str:
    """Load system prompt for an agent."""
    prompt_path = PROMPTS_DIR / f"{agent_name}.md"
    if not prompt_path.exists():
        return ""
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()
