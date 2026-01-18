"""
Ralph Deep Research - Application Settings

Configuration management using pydantic-settings for environment variable loading.
All settings have sensible defaults for development, with required API keys validated.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Required:
        ANTHROPIC_API_KEY: Claude API key for LLM calls

    Optional (with defaults):
        DATABASE_URL: SQLite database location
        HOST/PORT: Server binding
        DEBUG: Enable debug mode
        LOG_LEVEL: Logging verbosity
        MAX_*: Scalability limits
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ==========================================================================
    # Required Settings
    # ==========================================================================

    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude models",
        min_length=10,
    )

    # ==========================================================================
    # Database Settings
    # ==========================================================================

    database_url: str = Field(
        default="sqlite+aiosqlite:///./ralph.db",
        description="Database connection URL",
    )

    # ==========================================================================
    # Server Settings
    # ==========================================================================

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, ge=1, le=65535, description="Server port")
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level",
    )

    # ==========================================================================
    # Scalability Limits (MVP)
    # ==========================================================================

    max_concurrent_sessions: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of concurrent research sessions",
    )
    max_rounds_per_session: int = Field(
        default=10,
        ge=1,
        le=20,
        description="Maximum research rounds per session",
    )
    max_tasks_per_round: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum tasks per research round",
    )
    round_timeout_seconds: int = Field(
        default=300,
        ge=60,
        le=600,
        description="Timeout for parallel round execution in seconds",
    )
    max_storage_per_session_mb: int = Field(
        default=50,
        ge=10,
        le=500,
        description="Maximum storage per session in MB",
    )
    max_report_size_mb: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Maximum report file size in MB",
    )

    # ==========================================================================
    # External API Keys (Optional)
    # ==========================================================================

    financial_api_key: str | None = Field(
        default=None,
        description="API key for financial data provider",
    )
    news_api_key: str | None = Field(
        default=None,
        description="API key for news provider",
    )
    serper_api_key: str | None = Field(
        default=None,
        description="Serper API key for web search",
    )

    # ==========================================================================
    # Validators
    # ==========================================================================

    @field_validator("anthropic_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate Anthropic API key format."""
        if not v.startswith("sk-ant-"):
            raise ValueError("Anthropic API key must start with 'sk-ant-'")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v.startswith(("sqlite", "postgresql", "mysql")):
            raise ValueError("Database URL must be SQLite, PostgreSQL, or MySQL")
        return v


@lru_cache
def get_settings() -> Settings:
    """
    Get cached application settings.

    Returns:
        Settings: Application settings instance

    Raises:
        ValidationError: If required settings are missing or invalid
    """
    return Settings()
