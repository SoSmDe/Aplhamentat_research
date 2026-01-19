"""
Ralph Deep Research - API Dependencies

FastAPI dependency injection functions for database, session management,
and pipeline access. These provide singleton instances and validation helpers.
"""

from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Path, status

from src.api.schemas import Session
from src.config.settings import Settings, get_settings
from src.storage.database import Database
from src.storage.session import SessionManager
from src.tools.errors import SessionNotFoundError


# =============================================================================
# Global Instances (initialized during app lifespan)
# =============================================================================

# These are set during application startup in main.py lifespan handler
_database: Database | None = None
_session_manager: SessionManager | None = None


def set_database(db: Database) -> None:
    """Set the global database instance during app startup."""
    global _database
    _database = db


def set_session_manager(sm: SessionManager) -> None:
    """Set the global session manager instance during app startup."""
    global _session_manager
    _session_manager = sm


def get_database_instance() -> Database | None:
    """Get the current database instance (for testing/inspection)."""
    return _database


def get_session_manager_instance() -> SessionManager | None:
    """Get the current session manager instance (for testing/inspection)."""
    return _session_manager


# =============================================================================
# FastAPI Dependencies
# =============================================================================


async def get_database() -> Database:
    """
    Get database connection dependency.

    Returns:
        Database: The database instance

    Raises:
        HTTPException: 503 if database not initialized
    """
    if _database is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not initialized",
        )
    return _database


async def get_session_manager(
    db: Annotated[Database, Depends(get_database)],
) -> SessionManager:
    """
    Get session manager dependency.

    Args:
        db: Database dependency (injected)

    Returns:
        SessionManager: The session manager instance

    Raises:
        HTTPException: 503 if session manager not initialized
    """
    if _session_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session manager not initialized",
        )
    return _session_manager


async def get_settings_dep() -> Settings:
    """
    Get application settings dependency.

    Returns:
        Settings: Application configuration
    """
    return get_settings()


async def verify_session(
    session_id: Annotated[str, Path(description="Session ID")],
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
) -> Session:
    """
    Verify session exists and return it.

    Args:
        session_id: Session ID from path parameter
        session_manager: Session manager dependency

    Returns:
        Session: The validated session

    Raises:
        HTTPException: 404 if session not found
    """
    try:
        session = await session_manager.get_session(session_id)
        return session
    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )


# =============================================================================
# Type Aliases for cleaner route signatures
# =============================================================================

DatabaseDep = Annotated[Database, Depends(get_database)]
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
SessionDep = Annotated[Session, Depends(verify_session)]
