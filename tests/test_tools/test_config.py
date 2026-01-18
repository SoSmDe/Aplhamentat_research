"""
Tests for configuration system (Phase 1.1).

Verifies:
- Settings loading and validation
- Model configuration
- Timeout configuration
- Scalability limits
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config.models import (
    AGENT_MODELS,
    OPUS_MODEL,
    SONNET_MODEL,
    get_model_for_agent,
)
from src.config.settings import Settings
from src.config.timeouts import (
    AGENT_TIMEOUTS,
    SCALABILITY_LIMITS,
    get_limit,
    get_timeout,
)


class TestSettings:
    """Tests for Settings configuration class."""

    def test_settings_requires_api_key(self) -> None:
        """Settings should require ANTHROPIC_API_KEY."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_settings_validates_api_key_format(self) -> None:
        """Settings should validate API key format."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "invalid_key"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "sk-ant-" in str(exc_info.value)

    def test_settings_accepts_valid_api_key(self) -> None:
        """Settings should accept valid API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123456"}, clear=True):
            settings = Settings()
            assert settings.anthropic_api_key == "sk-ant-test123456"

    def test_settings_has_defaults(self) -> None:
        """Settings should have sensible defaults."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123456"}, clear=True):
            settings = Settings()
            assert settings.host == "0.0.0.0"
            assert settings.port == 8000
            assert settings.debug is False
            assert settings.log_level == "INFO"
            assert settings.max_concurrent_sessions == 10
            assert settings.max_rounds_per_session == 10

    def test_settings_database_url_default(self) -> None:
        """Settings should default to SQLite database."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test123456"}, clear=True):
            settings = Settings()
            assert "sqlite" in settings.database_url

    def test_settings_validates_database_url(self) -> None:
        """Settings should validate database URL format."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test123456",
            "DATABASE_URL": "invalid://database"
        }, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_settings_accepts_postgres_url(self) -> None:
        """Settings should accept PostgreSQL database URL."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "sk-ant-test123456",
            "DATABASE_URL": "postgresql://user:pass@localhost/db"
        }, clear=True):
            settings = Settings()
            assert "postgresql" in settings.database_url


class TestModelConfiguration:
    """Tests for model configuration."""

    def test_agent_models_defined(self) -> None:
        """All agents should have model assignments."""
        expected_agents = {
            "initial_research",
            "brief_builder",
            "planner",
            "data",
            "research",
            "aggregator",
            "reporter",
        }
        assert set(AGENT_MODELS.keys()) == expected_agents

    def test_data_agent_uses_sonnet(self) -> None:
        """Data agent should use Sonnet for cost efficiency."""
        assert AGENT_MODELS["data"] == SONNET_MODEL

    def test_reasoning_agents_use_opus(self) -> None:
        """Complex reasoning agents should use Opus."""
        opus_agents = ["brief_builder", "planner", "research", "aggregator", "reporter"]
        for agent in opus_agents:
            assert AGENT_MODELS[agent] == OPUS_MODEL

    def test_get_model_for_agent_returns_correct_model(self) -> None:
        """get_model_for_agent should return correct model ID."""
        assert get_model_for_agent("data") == SONNET_MODEL
        assert get_model_for_agent("research") == OPUS_MODEL

    def test_get_model_for_unknown_agent_raises_error(self) -> None:
        """get_model_for_agent should raise error for unknown agent."""
        with pytest.raises(ValueError) as exc_info:
            get_model_for_agent("unknown_agent")
        assert "unknown_agent" in str(exc_info.value)


class TestTimeoutConfiguration:
    """Tests for timeout configuration."""

    def test_all_timeouts_defined(self) -> None:
        """All operation timeouts should be defined."""
        expected_timeouts = {
            "initial_research",
            "brief_builder",
            "planner",
            "data_task",
            "research_task",
            "round_timeout",
            "aggregation",
            "reporting",
        }
        assert set(AGENT_TIMEOUTS.keys()) == expected_timeouts

    def test_timeout_values_reasonable(self) -> None:
        """Timeout values should be reasonable."""
        assert AGENT_TIMEOUTS["brief_builder"] <= 30  # Quick response
        assert AGENT_TIMEOUTS["data_task"] <= 60  # Moderate
        assert AGENT_TIMEOUTS["research_task"] <= 120  # Can take time
        assert AGENT_TIMEOUTS["round_timeout"] >= 120  # Parallel execution

    def test_get_timeout_returns_correct_value(self) -> None:
        """get_timeout should return correct timeout."""
        assert get_timeout("data_task") == 45
        assert get_timeout("research_task") == 90

    def test_get_timeout_unknown_operation_raises_error(self) -> None:
        """get_timeout should raise error for unknown operation."""
        with pytest.raises(ValueError):
            get_timeout("unknown_operation")


class TestScalabilityLimits:
    """Tests for scalability limits."""

    def test_all_limits_defined(self) -> None:
        """All scalability limits should be defined."""
        expected_limits = {
            "max_concurrent_sessions",
            "max_tasks_per_round",
            "max_rounds_per_session",
            "max_tasks_per_session",
            "max_storage_per_session_mb",
            "max_report_size_mb",
            "min_coverage_percent",
        }
        assert set(SCALABILITY_LIMITS.keys()) == expected_limits

    def test_mvp_limits_match_spec(self) -> None:
        """MVP limits should match specification."""
        assert SCALABILITY_LIMITS["max_concurrent_sessions"] == 10
        assert SCALABILITY_LIMITS["max_tasks_per_round"] == 10
        assert SCALABILITY_LIMITS["max_rounds_per_session"] == 10
        assert SCALABILITY_LIMITS["max_tasks_per_session"] == 100
        assert SCALABILITY_LIMITS["max_storage_per_session_mb"] == 50
        assert SCALABILITY_LIMITS["max_report_size_mb"] == 20

    def test_coverage_threshold(self) -> None:
        """Coverage threshold should be 80%."""
        assert SCALABILITY_LIMITS["min_coverage_percent"] == 80

    def test_get_limit_returns_correct_value(self) -> None:
        """get_limit should return correct limit value."""
        assert get_limit("max_concurrent_sessions") == 10
        assert get_limit("min_coverage_percent") == 80

    def test_get_limit_unknown_raises_error(self) -> None:
        """get_limit should raise error for unknown limit."""
        with pytest.raises(ValueError):
            get_limit("unknown_limit")
