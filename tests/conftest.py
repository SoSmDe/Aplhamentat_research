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
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio


# Configure pytest-asyncio to use session scope for event loop
@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
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
