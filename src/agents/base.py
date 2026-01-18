"""
Ralph Deep Research - Base Agent

Abstract base class for all research agents.
Implements the Ralph Pattern: Execute → Save → Clear → Next.

Based on specs/PROMPTS.md and IMPLEMENTATION_PLAN.md Phase 5.1.

Why this design:
- Centralizes common agent behavior (LLM calls, state saving, logging)
- Enforces consistent interface across all 7 agents
- Provides system prompt loading from markdown files
- Integrates with SessionManager for state persistence
- Tracks token usage per agent

Usage:
    class InitialResearchAgent(BaseAgent):
        @property
        def agent_name(self) -> str:
            return "initial_research"

        async def execute(self, context: dict) -> dict:
            # Implementation
            pass
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from src.config.models import get_model_for_agent
from src.config.settings import get_settings
from src.config.timeouts import get_timeout
from src.storage.session import DataType, SessionManager
from src.tools.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    InvalidInputError,
    RalphError,
)
from src.tools.llm import LLMClient
from src.tools.logging import LogContext, get_logger

# Type variable for generic Pydantic models
T = TypeVar("T", bound=BaseModel)

# Path to prompts directory
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


class BaseAgent(ABC):
    """
    Abstract base class for all Ralph agents.

    Provides:
    - System prompt loading from markdown files
    - LLM calling with agent's configured model
    - State persistence following Ralph Pattern
    - Timeout enforcement
    - Structured logging with agent context

    All agents must implement:
    - agent_name property: Returns agent identifier for model selection and logging
    - execute method: Performs the agent's core task

    Optionally override:
    - validate_input: Custom input validation
    - get_timeout_key: Custom timeout key (defaults to agent_name)
    """

    def __init__(
        self,
        llm: LLMClient,
        session_manager: SessionManager,
    ) -> None:
        """
        Initialize base agent.

        Args:
            llm: LLM client for Claude API calls
            session_manager: Session manager for state persistence
        """
        self._llm = llm
        self._session = session_manager
        self._logger = get_logger(f"agents.{self.agent_name}")
        self._system_prompt: str | None = None

    # =========================================================================
    # ABSTRACT PROPERTIES AND METHODS
    # =========================================================================

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """
        Return agent name for model selection and logging.

        Must match one of: initial_research, brief_builder, planner,
        data, research, aggregator, reporter
        """
        pass

    @abstractmethod
    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute agent's core task.

        Args:
            context: Input context for the agent task

        Returns:
            Result dictionary in agent-specific format

        Raises:
            AgentExecutionError: If execution fails
            AgentTimeoutError: If execution times out
        """
        pass

    # =========================================================================
    # PROPERTIES
    # =========================================================================

    @property
    def model(self) -> str:
        """Get Claude model ID for this agent."""
        return get_model_for_agent(self.agent_name)

    @property
    def system_prompt(self) -> str:
        """
        Get system prompt for this agent.

        Loads from src/prompts/{agent_name}.md on first access.
        """
        if self._system_prompt is None:
            self._system_prompt = self._load_prompt()
        return self._system_prompt

    @property
    def timeout_seconds(self) -> float:
        """Get timeout for this agent from configuration."""
        timeout_key = self.get_timeout_key()
        return get_timeout(timeout_key)

    # =========================================================================
    # PROMPT LOADING
    # =========================================================================

    def _load_prompt(self) -> str:
        """
        Load system prompt from markdown file.

        Returns:
            System prompt text

        Raises:
            FileNotFoundError: If prompt file doesn't exist
        """
        prompt_path = PROMPTS_DIR / f"{self.agent_name}.md"

        if not prompt_path.exists():
            self._logger.warning(
                "Prompt file not found, using empty prompt",
                prompt_path=str(prompt_path),
            )
            return ""

        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt = f.read()

        self._logger.debug(
            "Loaded system prompt",
            prompt_path=str(prompt_path),
            length=len(prompt),
        )

        return prompt

    def get_timeout_key(self) -> str:
        """
        Get the timeout configuration key for this agent.

        Override in subclass if timeout key differs from agent_name.
        For example, data and research tasks use 'data_task' and 'research_task'.
        """
        return self.agent_name

    # =========================================================================
    # LLM CALLING
    # =========================================================================

    async def _call_llm(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        """
        Call LLM with this agent's model and system prompt.

        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            system_prompt: Override system prompt (optional)

        Returns:
            Generated text response
        """
        prompt = system_prompt if system_prompt is not None else self.system_prompt

        self._logger.debug(
            "Calling LLM",
            model=self.model,
            message_count=len(messages),
            max_tokens=max_tokens,
        )

        response = await self._llm.create_message(
            model=self.model,
            system=prompt,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return response

    async def _call_llm_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        system_prompt: str | None = None,
    ) -> T:
        """
        Call LLM with structured output using a Pydantic model.

        Args:
            messages: Conversation messages
            response_model: Pydantic model class for response
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower for consistency)
            system_prompt: Override system prompt (optional)

        Returns:
            Parsed Pydantic model instance
        """
        prompt = system_prompt if system_prompt is not None else self.system_prompt

        self._logger.debug(
            "Calling LLM for structured output",
            model=self.model,
            response_model=response_model.__name__,
        )

        result = await self._llm.create_structured(
            model=self.model,
            system=prompt,
            messages=messages,
            response_model=response_model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return result

    # =========================================================================
    # STATE PERSISTENCE (Ralph Pattern)
    # =========================================================================

    async def _save_result(
        self,
        session_id: str,
        data_type: DataType | str,
        result: dict[str, Any],
        round: int | None = None,
        task_id: str | None = None,
    ) -> int:
        """
        Save result to session storage (Ralph Pattern).

        This method should be called after agent task completes
        to persist the result for crash recovery.

        Args:
            session_id: Session identifier
            data_type: Type of data being stored
            result: Result data to store
            round: Round number (optional)
            task_id: Task ID for task results (optional)

        Returns:
            ID of inserted record
        """
        record_id = await self._session.save_state(
            session_id=session_id,
            data_type=data_type,
            data=result,
            round=round,
            task_id=task_id,
        )

        self._logger.info(
            "Result saved",
            session_id=session_id,
            data_type=data_type if isinstance(data_type, str) else data_type.value,
            record_id=record_id,
        )

        return record_id

    async def _get_state(
        self,
        session_id: str,
        data_type: DataType | str,
        round: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Get state from session storage.

        Args:
            session_id: Session identifier
            data_type: Type of data to retrieve
            round: Round number (optional)

        Returns:
            Retrieved data or None if not found
        """
        return await self._session.get_state(
            session_id=session_id,
            data_type=data_type,
            round=round,
        )

    # =========================================================================
    # EXECUTION WITH TIMEOUT
    # =========================================================================

    async def run(
        self,
        session_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute agent with timeout and error handling.

        This is the main entry point for running an agent.
        It wraps execute() with:
        - Timeout enforcement
        - Error handling and logging
        - Context binding for structured logs

        Args:
            session_id: Session identifier for logging and state
            context: Input context for the agent

        Returns:
            Result from execute()

        Raises:
            AgentTimeoutError: If execution times out
            AgentExecutionError: If execution fails
        """
        # Bind logging context
        with LogContext(session_id=session_id, agent=self.agent_name):
            self._logger.info(
                "Agent starting",
                timeout_seconds=self.timeout_seconds,
            )

            try:
                # Validate input
                self.validate_input(context)

                # Execute with timeout
                result = await asyncio.wait_for(
                    self.execute(context),
                    timeout=self.timeout_seconds,
                )

                self._logger.info(
                    "Agent completed successfully",
                )

                return result

            except asyncio.TimeoutError:
                self._logger.error(
                    "Agent timed out",
                    timeout_seconds=self.timeout_seconds,
                )
                raise AgentTimeoutError(
                    message=f"Agent '{self.agent_name}' timed out after {self.timeout_seconds}s",
                    agent_name=self.agent_name,
                    timeout_seconds=self.timeout_seconds,
                )

            except RalphError:
                # Re-raise Ralph errors as-is
                raise

            except Exception as e:
                self._logger.error(
                    "Agent execution failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
                raise AgentExecutionError(
                    message=f"Agent '{self.agent_name}' execution failed: {e}",
                    agent_name=self.agent_name,
                    original_error=str(e),
                )

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Override in subclass for custom validation.
        Default implementation checks for required session_id.

        Args:
            context: Input context to validate

        Raises:
            InvalidInputError: If validation fails
        """
        if "session_id" not in context:
            raise InvalidInputError(
                message="session_id is required in context",
                field="session_id",
            )

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def format_messages(
        self,
        user_content: str,
        assistant_content: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Format messages for LLM call.

        Args:
            user_content: User message content
            assistant_content: Optional assistant response for multi-turn

        Returns:
            List of message dictionaries
        """
        messages = [{"role": "user", "content": user_content}]

        if assistant_content:
            messages.append({"role": "assistant", "content": assistant_content})

        return messages

    def format_conversation(
        self,
        history: list[dict[str, str]],
        new_content: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Format conversation history for LLM call.

        Args:
            history: Previous conversation messages
            new_content: Optional new user message to append

        Returns:
            List of message dictionaries
        """
        messages = []

        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        if new_content:
            messages.append({"role": "user", "content": new_content})

        return messages
