"""
Tests for Database class (Phase 3.1).

Verifies:
- Database connection and disconnection
- Schema initialization
- CRUD operations
- Error handling
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio

from src.storage.database import (
    Database,
    serialize_json,
    deserialize_json,
)
from src.tools.errors import DatabaseError


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)
    # Also remove WAL and SHM files if they exist
    for ext in ["-wal", "-shm"]:
        wal_path = path + ext
        if os.path.exists(wal_path):
            os.unlink(wal_path)


@pytest_asyncio.fixture
async def database(temp_db_path):
    """Create and initialize a test database."""
    db = Database(temp_db_path)
    await db.connect()
    await db.init_db()
    yield db
    await db.disconnect()


class TestDatabaseConnection:
    """Tests for database connection management."""

    @pytest.mark.asyncio
    async def test_connect_creates_database_file(self, temp_db_path) -> None:
        """Database file should be created on connect."""
        db = Database(temp_db_path)
        await db.connect()
        try:
            assert Path(temp_db_path).exists()
            assert db.is_connected
        finally:
            await db.disconnect()

    @pytest.mark.asyncio
    async def test_disconnect_closes_connection(self, temp_db_path) -> None:
        """Disconnect should close the connection."""
        db = Database(temp_db_path)
        await db.connect()
        assert db.is_connected

        await db.disconnect()
        assert not db.is_connected

    @pytest.mark.asyncio
    async def test_context_manager(self, temp_db_path) -> None:
        """Database should work as async context manager."""
        async with Database(temp_db_path) as db:
            assert db.is_connected
        # After context exit
        assert not db.is_connected

    @pytest.mark.asyncio
    async def test_parse_sqlite_url(self) -> None:
        """Should parse various SQLite URL formats."""
        # aiosqlite format
        assert Database._parse_url("sqlite+aiosqlite:///./test.db") == "./test.db"
        # Standard sqlite format
        assert Database._parse_url("sqlite:///./test.db") == "./test.db"
        # Plain path
        assert Database._parse_url("./test.db") == "./test.db"

    @pytest.mark.asyncio
    async def test_double_connect_is_safe(self, temp_db_path) -> None:
        """Calling connect twice should be safe."""
        db = Database(temp_db_path)
        await db.connect()
        await db.connect()  # Should not raise
        assert db.is_connected
        await db.disconnect()

    @pytest.mark.asyncio
    async def test_double_disconnect_is_safe(self, temp_db_path) -> None:
        """Calling disconnect twice should be safe."""
        db = Database(temp_db_path)
        await db.connect()
        await db.disconnect()
        await db.disconnect()  # Should not raise
        assert not db.is_connected


class TestSchemaInitialization:
    """Tests for database schema initialization."""

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, database) -> None:
        """init_db should create all required tables."""
        # Check sessions table exists
        result = await database.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert result is not None
        assert result["name"] == "sessions"

        # Check session_data table exists
        result = await database.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session_data'"
        )
        assert result is not None

        # Check session_files table exists
        result = await database.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='session_files'"
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_init_db_creates_indexes(self, database) -> None:
        """init_db should create performance indexes."""
        indexes = await database.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='index'"
        )
        index_names = {idx["name"] for idx in indexes}

        assert "idx_sessions_status" in index_names
        assert "idx_session_data_lookup" in index_names
        assert "idx_session_files_session" in index_names

    @pytest.mark.asyncio
    async def test_init_db_is_idempotent(self, database) -> None:
        """init_db should be safe to call multiple times."""
        await database.init_db()  # Second call
        await database.init_db()  # Third call
        # Should not raise

        # Tables should still exist
        result = await database.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        assert result is not None


class TestCRUDOperations:
    """Tests for database CRUD operations."""

    @pytest.mark.asyncio
    async def test_execute_insert(self, database) -> None:
        """execute should insert rows."""
        await database.execute(
            "INSERT INTO sessions (id, user_id, status) VALUES (?, ?, ?)",
            ("sess_test123", "user1", "created"),
        )

        row = await database.fetch_one(
            "SELECT * FROM sessions WHERE id = ?",
            ("sess_test123",),
        )
        assert row is not None
        assert row["id"] == "sess_test123"
        assert row["user_id"] == "user1"

    @pytest.mark.asyncio
    async def test_execute_update(self, database) -> None:
        """execute should update rows."""
        await database.execute(
            "INSERT INTO sessions (id, user_id, status) VALUES (?, ?, ?)",
            ("sess_test123", "user1", "created"),
        )

        await database.execute(
            "UPDATE sessions SET status = ? WHERE id = ?",
            ("executing", "sess_test123"),
        )

        row = await database.fetch_one(
            "SELECT status FROM sessions WHERE id = ?",
            ("sess_test123",),
        )
        assert row["status"] == "executing"

    @pytest.mark.asyncio
    async def test_fetch_one_returns_dict(self, database) -> None:
        """fetch_one should return a dict."""
        await database.execute(
            "INSERT INTO sessions (id, user_id, status) VALUES (?, ?, ?)",
            ("sess_test123", "user1", "created"),
        )

        row = await database.fetch_one(
            "SELECT * FROM sessions WHERE id = ?",
            ("sess_test123",),
        )
        assert isinstance(row, dict)
        assert "id" in row
        assert "user_id" in row

    @pytest.mark.asyncio
    async def test_fetch_one_returns_none_when_not_found(self, database) -> None:
        """fetch_one should return None for non-existent row."""
        row = await database.fetch_one(
            "SELECT * FROM sessions WHERE id = ?",
            ("nonexistent",),
        )
        assert row is None

    @pytest.mark.asyncio
    async def test_fetch_all_returns_list(self, database) -> None:
        """fetch_all should return a list of dicts."""
        # Insert multiple rows
        for i in range(3):
            await database.execute(
                "INSERT INTO sessions (id, user_id, status) VALUES (?, ?, ?)",
                (f"sess_test{i}", "user1", "created"),
            )

        rows = await database.fetch_all(
            "SELECT * FROM sessions WHERE user_id = ?",
            ("user1",),
        )
        assert isinstance(rows, list)
        assert len(rows) == 3
        assert all(isinstance(row, dict) for row in rows)

    @pytest.mark.asyncio
    async def test_fetch_all_returns_empty_list_when_not_found(self, database) -> None:
        """fetch_all should return empty list when no rows match."""
        rows = await database.fetch_all(
            "SELECT * FROM sessions WHERE user_id = ?",
            ("nonexistent",),
        )
        assert rows == []

    @pytest.mark.asyncio
    async def test_fetch_value_returns_single_value(self, database) -> None:
        """fetch_value should return a single value."""
        await database.execute(
            "INSERT INTO sessions (id, user_id, status) VALUES (?, ?, ?)",
            ("sess_test123", "user1", "created"),
        )

        count = await database.fetch_value(
            "SELECT COUNT(*) FROM sessions WHERE user_id = ?",
            ("user1",),
        )
        assert count == 1

    @pytest.mark.asyncio
    async def test_fetch_value_returns_none_when_not_found(self, database) -> None:
        """fetch_value should return None for non-existent row."""
        result = await database.fetch_value(
            "SELECT status FROM sessions WHERE id = ?",
            ("nonexistent",),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_execute_many(self, database) -> None:
        """execute_many should batch insert multiple rows."""
        params = [
            ("sess_test1", "user1", "created"),
            ("sess_test2", "user2", "created"),
            ("sess_test3", "user3", "created"),
        ]

        await database.execute_many(
            "INSERT INTO sessions (id, user_id, status) VALUES (?, ?, ?)",
            params,
        )

        count = await database.fetch_value("SELECT COUNT(*) FROM sessions")
        assert count == 3


class TestErrorHandling:
    """Tests for database error handling."""

    @pytest.mark.asyncio
    async def test_execute_without_connection_raises_error(self, temp_db_path) -> None:
        """Operations without connection should raise DatabaseError."""
        db = Database(temp_db_path)
        # Not connected

        with pytest.raises(DatabaseError) as exc_info:
            await db.execute("SELECT 1")

        assert "not connected" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_fetch_one_without_connection_raises_error(self, temp_db_path) -> None:
        """fetch_one without connection should raise DatabaseError."""
        db = Database(temp_db_path)

        with pytest.raises(DatabaseError):
            await db.fetch_one("SELECT 1")

    @pytest.mark.asyncio
    async def test_invalid_sql_raises_error(self, database) -> None:
        """Invalid SQL should raise DatabaseError."""
        with pytest.raises(DatabaseError):
            await database.execute("INVALID SQL SYNTAX")


class TestJSONHelpers:
    """Tests for JSON serialization helpers."""

    def test_serialize_simple_dict(self) -> None:
        """serialize_json should handle simple dicts."""
        data = {"key": "value", "number": 42}
        result = serialize_json(data)
        assert isinstance(result, str)
        assert "key" in result
        assert "value" in result

    def test_serialize_nested_dict(self) -> None:
        """serialize_json should handle nested structures."""
        data = {
            "outer": {
                "inner": {
                    "value": [1, 2, 3]
                }
            }
        }
        result = serialize_json(data)
        assert isinstance(result, str)

    def test_serialize_datetime(self) -> None:
        """serialize_json should handle datetime objects."""
        from datetime import datetime, timezone
        data = {
            "timestamp": datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        }
        result = serialize_json(data)
        assert "2024-01-15" in result

    def test_deserialize_json(self) -> None:
        """deserialize_json should parse JSON strings."""
        json_str = '{"key": "value", "number": 42}'
        result = deserialize_json(json_str)
        assert result == {"key": "value", "number": 42}

    def test_deserialize_none(self) -> None:
        """deserialize_json should handle None."""
        assert deserialize_json(None) is None

    def test_deserialize_empty_string(self) -> None:
        """deserialize_json should handle empty string."""
        assert deserialize_json("") is None

    def test_roundtrip(self) -> None:
        """serialize and deserialize should be inverse operations."""
        original = {
            "string": "hello",
            "number": 123,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }
        serialized = serialize_json(original)
        deserialized = deserialize_json(serialized)
        assert deserialized == original
