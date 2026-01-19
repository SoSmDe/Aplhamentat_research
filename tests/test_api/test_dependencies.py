"""
Tests for API dependencies.

Tests cover:
- Database dependency injection
- Session manager dependency injection
- Session verification
- Settings dependency
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException

from src.api.dependencies import (
    get_database,
    get_session_manager,
    get_settings_dep,
    verify_session,
    set_database,
    set_session_manager,
    get_database_instance,
    get_session_manager_instance,
    DatabaseDep,
    SessionManagerDep,
    SettingsDep,
    SessionDep,
)
from src.api.schemas import Session, SessionStatus
from src.tools.errors import SessionNotFoundError


# =============================================================================
# Database Dependency Tests
# =============================================================================


class TestGetDatabase:
    """Tests for get_database dependency."""

    @pytest.mark.asyncio
    async def test_get_database_when_initialized(self):
        """Test getting database when it's initialized."""
        mock_db = MagicMock()
        set_database(mock_db)

        result = await get_database()
        assert result is mock_db

    @pytest.mark.asyncio
    async def test_get_database_when_not_initialized(self):
        """Test getting database when not initialized raises 503."""
        set_database(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_database()

        assert exc_info.value.status_code == 503
        assert "Database not initialized" in exc_info.value.detail


class TestSetDatabase:
    """Tests for set_database function."""

    def test_set_database_stores_instance(self):
        """Test that set_database stores the instance."""
        mock_db = MagicMock()
        set_database(mock_db)

        assert get_database_instance() is mock_db

    def test_set_database_can_be_reset(self):
        """Test that database can be reset to None."""
        mock_db = MagicMock()
        set_database(mock_db)
        set_database(None)

        assert get_database_instance() is None


# =============================================================================
# Session Manager Dependency Tests
# =============================================================================


class TestGetSessionManager:
    """Tests for get_session_manager dependency."""

    @pytest.mark.asyncio
    async def test_get_session_manager_when_initialized(self):
        """Test getting session manager when it's initialized."""
        mock_db = MagicMock()
        mock_sm = MagicMock()
        set_database(mock_db)
        set_session_manager(mock_sm)

        result = await get_session_manager(mock_db)
        assert result is mock_sm

    @pytest.mark.asyncio
    async def test_get_session_manager_when_not_initialized(self):
        """Test getting session manager when not initialized raises 503."""
        mock_db = MagicMock()
        set_database(mock_db)
        set_session_manager(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_session_manager(mock_db)

        assert exc_info.value.status_code == 503
        assert "Session manager not initialized" in exc_info.value.detail


class TestSetSessionManager:
    """Tests for set_session_manager function."""

    def test_set_session_manager_stores_instance(self):
        """Test that set_session_manager stores the instance."""
        mock_sm = MagicMock()
        set_session_manager(mock_sm)

        assert get_session_manager_instance() is mock_sm

    def test_set_session_manager_can_be_reset(self):
        """Test that session manager can be reset to None."""
        mock_sm = MagicMock()
        set_session_manager(mock_sm)
        set_session_manager(None)

        assert get_session_manager_instance() is None


# =============================================================================
# Settings Dependency Tests
# =============================================================================


class TestGetSettingsDep:
    """Tests for get_settings_dep dependency."""

    @pytest.mark.asyncio
    async def test_get_settings_returns_settings(self):
        """Test that get_settings_dep returns settings object."""
        result = await get_settings_dep()

        # Should return a Settings object
        assert result is not None
        assert hasattr(result, "anthropic_api_key")
        assert hasattr(result, "database_url")


# =============================================================================
# Verify Session Dependency Tests
# =============================================================================


class TestVerifySession:
    """Tests for verify_session dependency."""

    @pytest.mark.asyncio
    async def test_verify_session_found(self):
        """Test verification when session exists."""
        mock_sm = AsyncMock()
        mock_session = MagicMock(spec=Session)
        mock_session.id = "sess_test123456"
        mock_session.status = SessionStatus.BRIEF
        mock_sm.get_session = AsyncMock(return_value=mock_session)

        result = await verify_session("sess_test123456", mock_sm)

        assert result is mock_session
        mock_sm.get_session.assert_called_once_with("sess_test123456")

    @pytest.mark.asyncio
    async def test_verify_session_not_found(self):
        """Test verification when session doesn't exist."""
        mock_sm = AsyncMock()
        mock_sm.get_session = AsyncMock(
            side_effect=SessionNotFoundError("Session not found", session_id="invalid")
        )

        with pytest.raises(HTTPException) as exc_info:
            await verify_session("invalid", mock_sm)

        assert exc_info.value.status_code == 404
        assert "Session not found" in exc_info.value.detail


# =============================================================================
# Type Alias Tests
# =============================================================================


class TestTypeAliases:
    """Tests for dependency type aliases."""

    def test_database_dep_is_annotated(self):
        """Test DatabaseDep is an Annotated type."""
        # Just verify the type alias exists and is usable
        assert DatabaseDep is not None

    def test_session_manager_dep_is_annotated(self):
        """Test SessionManagerDep is an Annotated type."""
        assert SessionManagerDep is not None

    def test_settings_dep_is_annotated(self):
        """Test SettingsDep is an Annotated type."""
        assert SettingsDep is not None

    def test_session_dep_is_annotated(self):
        """Test SessionDep is an Annotated type."""
        assert SessionDep is not None


# =============================================================================
# Integration Tests
# =============================================================================


class TestDependencyIntegration:
    """Integration tests for dependencies working together."""

    @pytest.mark.asyncio
    async def test_full_dependency_chain(self):
        """Test the full dependency chain from database to session."""
        # Setup
        mock_db = MagicMock()
        mock_db.is_connected = True

        mock_sm = AsyncMock()
        mock_session = MagicMock(spec=Session)
        mock_session.id = "sess_integration_test"
        mock_session.status = SessionStatus.BRIEF
        mock_sm.get_session = AsyncMock(return_value=mock_session)

        # Register dependencies
        set_database(mock_db)
        set_session_manager(mock_sm)

        # Test chain
        db = await get_database()
        assert db is mock_db

        sm = await get_session_manager(db)
        assert sm is mock_sm

        session = await verify_session("sess_integration_test", sm)
        assert session is mock_session

    @pytest.mark.asyncio
    async def test_dependency_reset_and_reinitialize(self):
        """Test that dependencies can be reset and reinitialized."""
        # Initial setup
        mock_db1 = MagicMock()
        mock_sm1 = MagicMock()
        set_database(mock_db1)
        set_session_manager(mock_sm1)

        assert get_database_instance() is mock_db1
        assert get_session_manager_instance() is mock_sm1

        # Reset
        set_database(None)
        set_session_manager(None)

        assert get_database_instance() is None
        assert get_session_manager_instance() is None

        # Reinitialize with different instances
        mock_db2 = MagicMock()
        mock_sm2 = MagicMock()
        set_database(mock_db2)
        set_session_manager(mock_sm2)

        assert get_database_instance() is mock_db2
        assert get_session_manager_instance() is mock_sm2
