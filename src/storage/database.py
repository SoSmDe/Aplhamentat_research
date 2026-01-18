"""
Ralph Deep Research - Database Layer

Async SQLite database operations using aiosqlite.
Based on specs/ARCHITECTURE.md (Section 4: State Management).

Why SQLite:
- Simple deployment (no separate server)
- Sufficient for MVP concurrent session limit (10)
- Easy to migrate to PostgreSQL if needed

Why aiosqlite:
- Non-blocking I/O for async FastAPI
- Works with asyncio.gather() for parallel operations

Usage:
    db = Database("sqlite+aiosqlite:///./ralph.db")
    await db.connect()
    try:
        row = await db.fetch_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
    finally:
        await db.disconnect()

    # Or using context manager:
    async with Database("...") as db:
        rows = await db.fetch_all("SELECT * FROM sessions")
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite

from src.tools.errors import DatabaseError
from src.tools.logging import get_logger

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# =============================================================================
# SQL SCHEMA
# =============================================================================

SCHEMA_SQL = """
-- Sessions table: Core session tracking
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'created',
    current_round INTEGER DEFAULT 0,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Session data table: All intermediate state (Ralph Pattern)
-- Stores: initial_context, brief, conversation, plan, data_result, research_result, etc.
CREATE TABLE IF NOT EXISTS session_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    data_type TEXT NOT NULL,
    round INTEGER,
    task_id TEXT,
    data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Session files table: Track generated reports
CREATE TABLE IF NOT EXISTS session_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    file_type TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- Performance indexes
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_session_data_lookup ON session_data(session_id, data_type, round);
CREATE INDEX IF NOT EXISTS idx_session_data_task ON session_data(session_id, task_id);
CREATE INDEX IF NOT EXISTS idx_session_files_session ON session_files(session_id);
"""


# =============================================================================
# DATABASE CLASS
# =============================================================================


class Database:
    """
    Async SQLite database wrapper using aiosqlite.

    Features:
    - Connection pooling via single connection (sufficient for MVP)
    - Auto-creation of tables on init_db()
    - Transaction support via context manager
    - JSON serialization for complex data

    Why single connection:
    - SQLite writes are serialized anyway
    - MVP limit is 10 concurrent sessions
    - Simpler implementation, easy to scale later
    """

    def __init__(self, database_url: str) -> None:
        """
        Initialize database.

        Args:
            database_url: SQLite URL (e.g., "sqlite+aiosqlite:///./ralph.db")
                         Supports both "sqlite+aiosqlite:///" and plain paths
        """
        # Parse database URL to get path
        self._database_url = database_url
        self._db_path = self._parse_url(database_url)
        self._connection: aiosqlite.Connection | None = None
        self._connected = False

    @staticmethod
    def _parse_url(url: str) -> str:
        """
        Parse database URL to extract file path.

        Supports:
        - sqlite+aiosqlite:///./ralph.db
        - sqlite:///./ralph.db
        - ./ralph.db (plain path)
        """
        if url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite+aiosqlite:///", "")
        if url.startswith("sqlite:///"):
            return url.replace("sqlite:///", "")
        # Assume it's a plain path
        return url

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected and self._connection is not None

    async def connect(self) -> None:
        """
        Open database connection.

        Creates the database file if it doesn't exist.
        Enables foreign key support and WAL mode for better concurrency.
        """
        if self._connected:
            return

        try:
            # Ensure directory exists
            db_path = Path(self._db_path)
            if db_path.parent.name:  # Not root
                db_path.parent.mkdir(parents=True, exist_ok=True)

            self._connection = await aiosqlite.connect(
                self._db_path,
                isolation_level=None,  # Autocommit mode
            )

            # Enable foreign keys (disabled by default in SQLite)
            await self._connection.execute("PRAGMA foreign_keys = ON")

            # WAL mode for better read concurrency
            await self._connection.execute("PRAGMA journal_mode = WAL")

            # Return rows as dict-like objects
            self._connection.row_factory = aiosqlite.Row

            self._connected = True
            logger.info("Database connected", db_path=self._db_path)

        except Exception as e:
            logger.error(
                "Database connection failed",
                db_path=self._db_path,
                error=str(e),
            )
            raise DatabaseError(
                message=f"Failed to connect to database: {e}",
                operation="connect",
                original_error=str(e),
            )

    async def disconnect(self) -> None:
        """Close database connection."""
        if self._connection is not None:
            try:
                await self._connection.close()
            except Exception as e:
                logger.warning("Error closing database", error=str(e))
            finally:
                self._connection = None
                self._connected = False
                logger.info("Database disconnected")

    async def init_db(self) -> None:
        """
        Initialize database schema.

        Creates all tables if they don't exist.
        Safe to call multiple times (idempotent).
        """
        if not self._connected:
            await self.connect()

        try:
            await self._connection.executescript(SCHEMA_SQL)
            await self._connection.commit()
            logger.info("Database schema initialized")
        except Exception as e:
            logger.error("Schema initialization failed", error=str(e))
            raise DatabaseError(
                message=f"Failed to initialize schema: {e}",
                operation="init_db",
                original_error=str(e),
            )

    async def execute(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> aiosqlite.Cursor:
        """
        Execute a SQL query.

        Args:
            query: SQL query with ? placeholders
            params: Query parameters

        Returns:
            Cursor object for accessing results

        Raises:
            DatabaseError: On query execution failure
        """
        if not self._connected:
            raise DatabaseError(
                message="Database not connected",
                operation="execute",
            )

        try:
            cursor = await self._connection.execute(query, params or ())
            await self._connection.commit()
            return cursor
        except Exception as e:
            logger.error(
                "Query execution failed",
                query=query[:100],  # Truncate for logging
                error=str(e),
            )
            raise DatabaseError(
                message=f"Query execution failed: {e}",
                operation="execute",
                original_error=str(e),
            )

    async def execute_many(
        self,
        query: str,
        params_seq: list[tuple[Any, ...]],
    ) -> None:
        """
        Execute a query with multiple parameter sets.

        Args:
            query: SQL query with ? placeholders
            params_seq: Sequence of parameter tuples
        """
        if not self._connected:
            raise DatabaseError(
                message="Database not connected",
                operation="execute_many",
            )

        try:
            await self._connection.executemany(query, params_seq)
            await self._connection.commit()
        except Exception as e:
            raise DatabaseError(
                message=f"Batch execution failed: {e}",
                operation="execute_many",
                original_error=str(e),
            )

    async def fetch_one(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Fetch a single row.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Row as dict, or None if not found
        """
        if not self._connected:
            raise DatabaseError(
                message="Database not connected",
                operation="fetch_one",
            )

        try:
            cursor = await self._connection.execute(query, params or ())
            row = await cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        except Exception as e:
            raise DatabaseError(
                message=f"Fetch failed: {e}",
                operation="fetch_one",
                original_error=str(e),
            )

    async def fetch_all(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fetch all matching rows.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            List of rows as dicts
        """
        if not self._connected:
            raise DatabaseError(
                message="Database not connected",
                operation="fetch_all",
            )

        try:
            cursor = await self._connection.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            raise DatabaseError(
                message=f"Fetch failed: {e}",
                operation="fetch_all",
                original_error=str(e),
            )

    async def fetch_value(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> Any:
        """
        Fetch a single value (first column of first row).

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Single value, or None if not found
        """
        if not self._connected:
            raise DatabaseError(
                message="Database not connected",
                operation="fetch_value",
            )

        try:
            cursor = await self._connection.execute(query, params or ())
            row = await cursor.fetchone()
            if row is None:
                return None
            return row[0]
        except Exception as e:
            raise DatabaseError(
                message=f"Fetch failed: {e}",
                operation="fetch_value",
                original_error=str(e),
            )

    # Context manager support
    async def __aenter__(self) -> "Database":
        """Enter async context, connecting to database."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit async context, disconnecting from database."""
        await self.disconnect()


# =============================================================================
# JSON HELPERS
# =============================================================================


def serialize_json(data: Any) -> str:
    """
    Serialize data to JSON string for storage.

    Handles datetime objects and other common types.
    """

    def default_serializer(obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    return json.dumps(data, default=default_serializer, ensure_ascii=False)


def deserialize_json(data: str | None) -> Any:
    """
    Deserialize JSON string from storage.

    Returns None if data is None or empty.
    """
    if not data:
        return None
    return json.loads(data)
