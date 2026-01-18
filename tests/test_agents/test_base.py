"""
Ralph Deep Research - Base Agent Tests

Unit tests for the BaseAgent abstract class.

Why these tests:
- Verify abstract interface is properly defined
- Test system prompt loading
- Test timeout enforcement
- Test state persistence integration
- Test error handling patterns
"""

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.base import BaseAgent, PROMPTS_DIR
from src.tools.errors import (
    AgentExecutionError,
    AgentTimeoutError,
    InvalidInputError,
)


# =============================================================================
# CONCRETE IMPLEMENTATION FOR TESTING
# =============================================================================


class ConcreteAgent(BaseAgent):
    """Concrete implementation for testing abstract BaseAgent."""

    def __init__(
        self,
        llm: Any,
        session_manager: Any,
        execute_result: dict[str, Any] | None = None,
        execute_delay: float = 0,
        execute_error: Exception | None = None,
    ):
        super().__init__(llm, session_manager)
        self._execute_result = execute_result or {"status": "done"}
        self._execute_delay = execute_delay
        self._execute_error = execute_error

    @property
    def agent_name(self) -> str:
        return "test_agent"

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        if self._execute_delay > 0:
            await asyncio.sleep(self._execute_delay)
        if self._execute_error:
            raise self._execute_error
        return self._execute_result


class CustomTimeoutAgent(ConcreteAgent):
    """Agent with custom timeout key."""

    def get_timeout_key(self) -> str:
        return "data_task"


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def mock_llm():
    """Create mock LLM client."""
    client = MagicMock()
    client.create_message = AsyncMock(return_value="Test response")
    client.create_structured = AsyncMock()
    return client


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    manager = MagicMock()
    manager.save_state = AsyncMock(return_value=1)
    manager.get_state = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def agent(mock_llm, mock_session_manager):
    """Create concrete agent for testing."""
    return ConcreteAgent(mock_llm, mock_session_manager)


# =============================================================================
# BASIC PROPERTIES TESTS
# =============================================================================


class TestBaseAgentProperties:
    """Test BaseAgent properties."""

    def test_agent_name(self, agent):
        """Test agent_name property returns correct value."""
        assert agent.agent_name == "test_agent"

    def test_model_property(self, agent):
        """Test model property returns configured model."""
        # Mock the model lookup since test_agent is not a real agent
        with patch("src.agents.base.get_model_for_agent", return_value="claude-sonnet-4-20250514"):
            model = agent.model
            assert isinstance(model, str)
            assert len(model) > 0

    def test_timeout_property(self, agent):
        """Test timeout_seconds property."""
        # Mock the timeout lookup since test_agent is not a real agent
        with patch("src.agents.base.get_timeout", return_value=30):
            timeout = agent.timeout_seconds
            assert isinstance(timeout, (int, float))
            assert timeout > 0

    def test_custom_timeout_key(self, mock_llm, mock_session_manager):
        """Test custom timeout key for agent."""
        agent = CustomTimeoutAgent(mock_llm, mock_session_manager)
        assert agent.get_timeout_key() == "data_task"


# =============================================================================
# PROMPT LOADING TESTS
# =============================================================================


class TestPromptLoading:
    """Test system prompt loading."""

    def test_prompts_dir_exists(self):
        """Test that prompts directory path is correct."""
        assert PROMPTS_DIR.name == "prompts"

    def test_load_nonexistent_prompt(self, agent):
        """Test loading prompt for agent without prompt file."""
        # test_agent doesn't have a prompt file
        prompt = agent.system_prompt
        assert prompt == ""

    def test_load_existing_prompt(self, mock_llm, mock_session_manager):
        """Test loading prompt that exists."""
        # Create agent with name matching an existing prompt
        class InitialResearchTestAgent(ConcreteAgent):
            @property
            def agent_name(self) -> str:
                return "initial_research"

        agent = InitialResearchTestAgent(mock_llm, mock_session_manager)
        prompt = agent.system_prompt
        assert len(prompt) > 0
        assert "Initial Research" in prompt or "Initial Research Agent" in prompt.replace("—", "-")


# =============================================================================
# INPUT VALIDATION TESTS
# =============================================================================


class TestInputValidation:
    """Test input validation."""

    def test_validate_missing_session_id(self, agent):
        """Test validation fails without session_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            agent.validate_input({"user_query": "test"})
        assert "session_id" in str(exc_info.value.message)

    def test_validate_with_session_id(self, agent):
        """Test validation passes with session_id."""
        # Should not raise
        agent.validate_input({"session_id": "sess_123"})


# =============================================================================
# LLM CALLING TESTS
# =============================================================================


class TestLLMCalling:
    """Test LLM calling methods."""

    @pytest.mark.asyncio
    async def test_call_llm(self, agent, mock_llm):
        """Test _call_llm method."""
        mock_llm.create_message = AsyncMock(return_value="Test response")

        # Mock model lookup since test_agent is not a real agent
        with patch("src.agents.base.get_model_for_agent", return_value="claude-sonnet-4-20250514"):
            result = await agent._call_llm(
                messages=[{"role": "user", "content": "Hello"}],
            )

            assert result == "Test response"
            mock_llm.create_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_llm_with_custom_prompt(self, agent, mock_llm):
        """Test _call_llm with custom system prompt."""
        mock_llm.create_message = AsyncMock(return_value="Response")

        # Mock model lookup since test_agent is not a real agent
        with patch("src.agents.base.get_model_for_agent", return_value="claude-sonnet-4-20250514"):
            await agent._call_llm(
                messages=[{"role": "user", "content": "Test"}],
                system_prompt="Custom prompt",
            )

            # Verify custom prompt was passed
            call_kwargs = mock_llm.create_message.call_args
            assert call_kwargs[1]["system"] == "Custom prompt"


# =============================================================================
# STATE PERSISTENCE TESTS
# =============================================================================


class TestStatePersistence:
    """Test state persistence methods."""

    @pytest.mark.asyncio
    async def test_save_result(self, agent, mock_session_manager):
        """Test _save_result method."""
        mock_session_manager.save_state = AsyncMock(return_value=42)

        record_id = await agent._save_result(
            session_id="sess_123",
            data_type="test_data",
            result={"key": "value"},
        )

        assert record_id == 42
        mock_session_manager.save_state.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_state(self, agent, mock_session_manager):
        """Test _get_state method."""
        expected_state = {"key": "value"}
        mock_session_manager.get_state = AsyncMock(return_value=expected_state)

        result = await agent._get_state(
            session_id="sess_123",
            data_type="test_data",
        )

        assert result == expected_state


# =============================================================================
# EXECUTION TESTS
# =============================================================================


class TestAgentExecution:
    """Test agent execution with run() method."""

    @pytest.mark.asyncio
    async def test_run_success(self, mock_llm, mock_session_manager):
        """Test successful run() execution."""
        agent = ConcreteAgent(
            mock_llm,
            mock_session_manager,
            execute_result={"status": "done", "data": "test"},
        )

        # Mock timeout lookup since test_agent is not a real agent
        with patch("src.agents.base.get_timeout", return_value=30):
            result = await agent.run(
                session_id="sess_123",
                context={"session_id": "sess_123"},
            )

            assert result["status"] == "done"
            assert result["data"] == "test"

    @pytest.mark.asyncio
    async def test_run_validation_error(self, agent):
        """Test run() with validation error."""
        # Mock timeout lookup since test_agent is not a real agent
        with patch("src.agents.base.get_timeout", return_value=30):
            with pytest.raises(InvalidInputError):
                await agent.run(
                    session_id="sess_123",
                    context={},  # Missing session_id
                )

    @pytest.mark.asyncio
    async def test_run_timeout(self, mock_llm, mock_session_manager):
        """Test run() timeout handling."""
        # Create agent that takes longer than timeout
        agent = ConcreteAgent(
            mock_llm,
            mock_session_manager,
            execute_delay=0.5,  # 500ms delay
        )

        # Mock get_timeout to return very short timeout for test
        with patch("src.agents.base.get_timeout", return_value=0.1):
            with pytest.raises(AgentTimeoutError) as exc_info:
                await agent.run(
                    session_id="sess_123",
                    context={"session_id": "sess_123"},
                )

            assert "timed out" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_run_execution_error(self, mock_llm, mock_session_manager):
        """Test run() handles execution errors."""
        agent = ConcreteAgent(
            mock_llm,
            mock_session_manager,
            execute_error=ValueError("Test error"),
        )

        # Mock timeout lookup since test_agent is not a real agent
        with patch("src.agents.base.get_timeout", return_value=30):
            with pytest.raises(AgentExecutionError) as exc_info:
                await agent.run(
                    session_id="sess_123",
                    context={"session_id": "sess_123"},
                )

            assert "execution failed" in str(exc_info.value.message)
            assert "Test error" in str(exc_info.value.message)


# =============================================================================
# UTILITY METHODS TESTS
# =============================================================================


class TestUtilityMethods:
    """Test utility methods."""

    def test_format_messages_user_only(self, agent):
        """Test format_messages with user content only."""
        messages = agent.format_messages("Hello")

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

    def test_format_messages_with_assistant(self, agent):
        """Test format_messages with assistant response."""
        messages = agent.format_messages("Hello", "Hi there!")

        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hi there!"

    def test_format_conversation_empty(self, agent):
        """Test format_conversation with empty history."""
        messages = agent.format_conversation([])

        assert len(messages) == 0

    def test_format_conversation_with_history(self, agent):
        """Test format_conversation with history."""
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
        ]

        messages = agent.format_conversation(history)

        assert len(messages) == 3
        assert messages[0]["content"] == "Q1"
        assert messages[2]["content"] == "Q2"

    def test_format_conversation_with_new_content(self, agent):
        """Test format_conversation with new user message."""
        history = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
        ]

        messages = agent.format_conversation(history, "New question")

        assert len(messages) == 3
        assert messages[2]["content"] == "New question"


# =============================================================================
# ABSTRACT METHOD TESTS
# =============================================================================


class TestAbstractMethods:
    """Test that abstract methods are properly enforced."""

    def test_cannot_instantiate_base_agent(self, mock_llm, mock_session_manager):
        """Test that BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent(mock_llm, mock_session_manager)

    def test_must_implement_agent_name(self, mock_llm, mock_session_manager):
        """Test that agent_name must be implemented."""

        class IncompleteAgent(BaseAgent):
            async def execute(self, context):
                return {}

        with pytest.raises(TypeError):
            IncompleteAgent(mock_llm, mock_session_manager)

    def test_must_implement_execute(self, mock_llm, mock_session_manager):
        """Test that execute must be implemented."""

        class IncompleteAgent(BaseAgent):
            @property
            def agent_name(self):
                return "incomplete"

        with pytest.raises(TypeError):
            IncompleteAgent(mock_llm, mock_session_manager)
