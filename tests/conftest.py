# Ralph Deep Research - Test Configuration
"""
pytest fixtures and configuration for the Ralph research system tests.

Provides:
- Test database (in-memory SQLite)
- Mock LLM client with canned responses
- Mock web search client
- Sample data fixtures (Brief, Plan, DataResult, ResearchResult)
- Session manager instance
- pytest-asyncio configuration
- Test settings override
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

# Set test environment variables BEFORE any imports that need them
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-testing-12345")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("LOG_LEVEL", "WARNING")

# Configure pytest-asyncio mode
pytest_plugins = ("pytest_asyncio",)


# Configure pytest-asyncio to use function scope event loop by default
@pytest.fixture(scope="function")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# Placeholder fixtures - to be implemented in Phase 11
# These will be expanded as the codebase is built

@pytest.fixture
def sample_session_id() -> str:
    """Sample session ID for testing."""
    return "sess_test12345678"


@pytest.fixture
def sample_brief_id() -> str:
    """Sample brief ID for testing."""
    return "brief_test12345678"


@pytest.fixture
def sample_user_id() -> str:
    """Sample user ID for testing."""
    return "user_test123"
