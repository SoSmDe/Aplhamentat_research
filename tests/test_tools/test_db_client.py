"""
Tests for the Database Query Client module.

Tests cover:
- Query validation (read-only enforcement)
- Query execution
- Schema introspection
- Mock client functionality
- Error handling
"""

import pytest
import tempfile
import sqlite3
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from src.tools.db_client import (
    ColumnInfo,
    TableSchema,
    QueryResult,
    DatabaseQueryClient,
    MockDatabaseClient,
    get_db_client,
    create_mock_db_client,
    DEFAULT_QUERY_TIMEOUT,
)
from src.tools.errors import DatabaseError, InvalidInputError


# =============================================================================
# DATA MODEL TESTS
# =============================================================================


class TestColumnInfo:
    """Tests for ColumnInfo dataclass."""

    def test_column_info_creation(self):
        """Test creating column info."""
        col = ColumnInfo(
            name="id",
            type="INTEGER",
            nullable=False,
            primary_key=True,
            default=None,
        )

        assert col.name == "id"
        assert col.type == "INTEGER"
        assert col.nullable is False
        assert col.primary_key is True

    def test_column_info_to_dict(self):
        """Test converting to dictionary."""
        col = ColumnInfo(name="name", type="TEXT")
        data = col.to_dict()

        assert data["name"] == "name"
        assert data["type"] == "TEXT"
        assert data["nullable"] is True
        assert data["primary_key"] is False


class TestTableSchema:
    """Tests for TableSchema dataclass."""

    def test_table_schema_creation(self):
        """Test creating table schema."""
        columns = [
            ColumnInfo(name="id", type="INTEGER", primary_key=True),
            ColumnInfo(name="name", type="TEXT"),
        ]
        schema = TableSchema(name="users", columns=columns, row_count=100)

        assert schema.name == "users"
        assert len(schema.columns) == 2
        assert schema.row_count == 100

    def test_table_schema_to_dict(self):
        """Test converting to dictionary."""
        columns = [ColumnInfo(name="id", type="INTEGER")]
        schema = TableSchema(name="users", columns=columns)

        data = schema.to_dict()

        assert data["name"] == "users"
        assert len(data["columns"]) == 1


class TestQueryResult:
    """Tests for QueryResult dataclass."""

    def test_query_result_creation(self):
        """Test creating query result."""
        result = QueryResult(
            columns=["id", "name"],
            rows=[{"id": 1, "name": "Test"}],
            row_count=1,
            execution_time=0.05,
        )

        assert result.columns == ["id", "name"]
        assert result.row_count == 1
        assert result.execution_time == 0.05

    def test_query_result_to_dict(self):
        """Test converting to dictionary."""
        result = QueryResult(
            columns=["id"],
            rows=[{"id": 1}],
            row_count=1,
            execution_time=0.01,
        )

        data = result.to_dict()

        assert data["columns"] == ["id"]
        assert data["row_count"] == 1
        assert "execution_time" in data


# =============================================================================
# QUERY VALIDATION TESTS
# =============================================================================


class TestQueryValidation:
    """Tests for query validation (read-only enforcement)."""

    @pytest.fixture
    def client(self):
        """Create client for validation testing."""
        return DatabaseQueryClient(connection_string="sqlite:///test.db")

    def test_select_allowed(self, client):
        """Test SELECT queries are allowed."""
        # Should not raise
        client._validate_query("SELECT * FROM users")
        client._validate_query("SELECT id, name FROM users WHERE id = 1")
        client._validate_query("SELECT COUNT(*) FROM users")

    def test_select_with_joins_allowed(self, client):
        """Test SELECT with JOINs allowed."""
        client._validate_query(
            "SELECT u.name, o.total FROM users u JOIN orders o ON u.id = o.user_id"
        )

    def test_with_clause_allowed(self, client):
        """Test WITH clause (CTE) allowed."""
        client._validate_query(
            "WITH recent AS (SELECT * FROM orders) SELECT * FROM recent"
        )

    def test_explain_allowed(self, client):
        """Test EXPLAIN allowed."""
        client._validate_query("EXPLAIN SELECT * FROM users")

    def test_insert_blocked(self, client):
        """Test INSERT is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("INSERT INTO users (name) VALUES ('test')")

        # Validation blocks non-SELECT queries at the start check
        assert "SELECT" in str(exc_info.value) or "INSERT" in str(exc_info.value)

    def test_update_blocked(self, client):
        """Test UPDATE is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("UPDATE users SET name = 'test'")

        assert "SELECT" in str(exc_info.value) or "UPDATE" in str(exc_info.value)

    def test_delete_blocked(self, client):
        """Test DELETE is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("DELETE FROM users")

        assert "SELECT" in str(exc_info.value) or "DELETE" in str(exc_info.value)

    def test_drop_blocked(self, client):
        """Test DROP is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("DROP TABLE users")

        assert "SELECT" in str(exc_info.value) or "DROP" in str(exc_info.value)

    def test_create_blocked(self, client):
        """Test CREATE is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("CREATE TABLE test (id INTEGER)")

        assert "SELECT" in str(exc_info.value) or "CREATE" in str(exc_info.value)

    def test_alter_blocked(self, client):
        """Test ALTER is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("ALTER TABLE users ADD COLUMN email TEXT")

        assert "SELECT" in str(exc_info.value) or "ALTER" in str(exc_info.value)

    def test_truncate_blocked(self, client):
        """Test TRUNCATE is blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("TRUNCATE TABLE users")

        assert "SELECT" in str(exc_info.value) or "TRUNCATE" in str(exc_info.value)

    def test_multiple_statements_blocked(self, client):
        """Test multiple statements are blocked."""
        with pytest.raises(InvalidInputError) as exc_info:
            client._validate_query("SELECT 1; DROP TABLE users")

        # Could be blocked for multiple statements OR for DROP keyword
        assert "Multiple" in str(exc_info.value) or "DROP" in str(exc_info.value)

    def test_case_insensitive_blocking(self, client):
        """Test blocking is case insensitive."""
        with pytest.raises(InvalidInputError):
            client._validate_query("insert into users values (1)")

        with pytest.raises(InvalidInputError):
            client._validate_query("InSeRt InTo users VALUES (1)")


# =============================================================================
# DATABASE QUERY CLIENT TESTS
# =============================================================================


class TestDatabaseQueryClient:
    """Tests for DatabaseQueryClient with real SQLite database."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary SQLite database with test data."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        # Create test schema and data
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                active INTEGER DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                total REAL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Insert test data
        cursor.executemany(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            [
                ("Alice", "alice@example.com"),
                ("Bob", "bob@example.com"),
                ("Charlie", "charlie@example.com"),
            ]
        )

        cursor.executemany(
            "INSERT INTO orders (user_id, total) VALUES (?, ?)",
            [
                (1, 100.00),
                (1, 200.00),
                (2, 150.00),
            ]
        )

        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        os.unlink(db_path)

    @pytest.fixture
    def client(self, temp_db):
        """Create client with test database."""
        return DatabaseQueryClient(connection_string=f"sqlite:///{temp_db}")

    @pytest.mark.asyncio
    async def test_execute_simple_query(self, client):
        """Test executing a simple SELECT query."""
        result = await client.execute_query("SELECT * FROM users")

        assert result.row_count == 3
        assert "id" in result.columns
        assert "name" in result.columns

    @pytest.mark.asyncio
    async def test_execute_query_with_params_list(self, client):
        """Test executing query with list parameters."""
        result = await client.execute_query(
            "SELECT * FROM users WHERE id = ?",
            params=[1]
        )

        assert result.row_count == 1
        assert result.rows[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_execute_query_with_multiple_params(self, client):
        """Test executing query with multiple parameters."""
        result = await client.execute_query(
            "SELECT * FROM users WHERE id > ? AND active = ?",
            params=[1, 1]
        )

        assert result.row_count == 2

    @pytest.mark.asyncio
    async def test_execute_aggregate_query(self, client):
        """Test executing aggregate query."""
        result = await client.execute_query(
            "SELECT COUNT(*) as count FROM users"
        )

        assert result.row_count == 1
        assert result.rows[0]["count"] == 3

    @pytest.mark.asyncio
    async def test_execute_join_query(self, client):
        """Test executing JOIN query."""
        result = await client.execute_query("""
            SELECT u.name, o.total
            FROM users u
            JOIN orders o ON u.id = o.user_id
            ORDER BY o.total DESC
        """)

        assert result.row_count == 3
        assert result.rows[0]["total"] == 200.00

    @pytest.mark.asyncio
    async def test_get_schema_info(self, client):
        """Test getting table schema."""
        schema = await client.get_schema_info("users")

        assert schema.name == "users"
        assert schema.row_count == 3
        assert len(schema.columns) == 4

        # Check column details
        col_names = [c.name for c in schema.columns]
        assert "id" in col_names
        assert "name" in col_names

    @pytest.mark.asyncio
    async def test_get_schema_primary_key(self, client):
        """Test schema includes primary key info."""
        schema = await client.get_schema_info("users")

        id_col = next(c for c in schema.columns if c.name == "id")
        assert id_col.primary_key is True

    @pytest.mark.asyncio
    async def test_list_tables(self, client):
        """Test listing all tables."""
        tables = await client.list_tables()

        assert "users" in tables
        assert "orders" in tables

    def test_format_as_data_table(self, client):
        """Test formatting result as DataTable."""
        result = QueryResult(
            columns=["id", "name"],
            rows=[{"id": 1, "name": "Test"}],
            row_count=1,
            execution_time=0.01,
        )

        table = client.format_as_data_table(result, "Test Table")

        assert table["name"] == "Test Table"
        assert table["headers"] == ["id", "name"]
        assert table["rows"] == [[1, "Test"]]


class TestDatabaseClientErrors:
    """Tests for database client error handling."""

    @pytest.fixture
    def client(self):
        """Create client for testing."""
        return DatabaseQueryClient(connection_string="sqlite:///nonexistent.db")

    @pytest.mark.asyncio
    async def test_invalid_table_name(self):
        """Test invalid table name validation."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        client = DatabaseQueryClient(connection_string=f"sqlite:///{db_path}")

        # Invalid table name should raise either InvalidInputError or DatabaseError
        # (DatabaseError wraps the InvalidInputError in some cases)
        with pytest.raises((InvalidInputError, DatabaseError)):
            await client.get_schema_info("invalid; DROP TABLE users")

        os.unlink(db_path)


# =============================================================================
# MOCK CLIENT TESTS
# =============================================================================


class TestMockDatabaseClient:
    """Tests for MockDatabaseClient."""

    @pytest.fixture
    def client(self):
        """Create mock client."""
        return MockDatabaseClient()

    @pytest.mark.asyncio
    async def test_execute_query_default_result(self, client):
        """Test default mock result."""
        result = await client.execute_query("SELECT * FROM test")

        assert result.row_count == 1
        assert "id" in result.columns

    @pytest.mark.asyncio
    async def test_execute_query_custom_result(self, client):
        """Test custom mock result."""
        custom_result = QueryResult(
            columns=["custom"],
            rows=[{"custom": "value"}],
            row_count=1,
            execution_time=0.01,
        )
        client.set_result("custom_table", custom_result)

        result = await client.execute_query("SELECT * FROM custom_table")

        assert result.columns == ["custom"]

    @pytest.mark.asyncio
    async def test_query_history(self, client):
        """Test query history tracking."""
        await client.execute_query("SELECT 1", params=[1])
        await client.execute_query("SELECT 2", params=[2])

        history = client.get_queries()

        assert len(history) == 2
        assert history[0]["query"] == "SELECT 1"
        assert history[1]["params"] == [2]

    @pytest.mark.asyncio
    async def test_clear_history(self, client):
        """Test clearing query history."""
        await client.execute_query("SELECT 1")
        client.clear_history()

        assert len(client.get_queries()) == 0

    @pytest.mark.asyncio
    async def test_validates_queries(self, client):
        """Test mock client still validates queries."""
        with pytest.raises(InvalidInputError):
            await client.execute_query("INSERT INTO test VALUES (1)")


# =============================================================================
# FACTORY FUNCTION TESTS
# =============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_get_db_client(self):
        """Test getting database client."""
        with patch("src.tools.db_client.get_settings") as mock_settings:
            mock_settings.return_value.database_url = "sqlite:///test.db"
            client = get_db_client()

            assert isinstance(client, DatabaseQueryClient)

    def test_get_db_client_custom_connection(self):
        """Test getting client with custom connection string."""
        client = get_db_client(connection_string="sqlite:///custom.db")
        assert client.db_path == "custom.db"

    def test_create_mock_db_client(self):
        """Test creating mock client."""
        client = create_mock_db_client()
        assert isinstance(client, MockDatabaseClient)

    def test_create_mock_db_client_with_results(self):
        """Test creating mock client with predefined results."""
        results = {
            "test": QueryResult(
                columns=["a"], rows=[{"a": 1}], row_count=1, execution_time=0.01
            )
        }
        client = create_mock_db_client(results=results)

        assert "test" in client.mock_results


# =============================================================================
# CONNECTION STRING PARSING TESTS
# =============================================================================


class TestConnectionStringParsing:
    """Tests for connection string parsing."""

    def test_parse_sqlite_type(self):
        """Test parsing SQLite connection string."""
        client = DatabaseQueryClient(connection_string="sqlite:///test.db")
        assert client.db_type == "sqlite"

    def test_parse_sqlite_aiosqlite_type(self):
        """Test parsing SQLite+aiosqlite connection string."""
        client = DatabaseQueryClient(
            connection_string="sqlite+aiosqlite:///./test.db"
        )
        assert client.db_type == "sqlite"

    def test_parse_postgresql_type(self):
        """Test parsing PostgreSQL connection string."""
        client = DatabaseQueryClient(
            connection_string="postgresql://localhost/test"
        )
        assert client.db_type == "postgresql"

    def test_parse_mysql_type(self):
        """Test parsing MySQL connection string."""
        client = DatabaseQueryClient(connection_string="mysql://localhost/test")
        assert client.db_type == "mysql"

    def test_parse_db_path_relative(self):
        """Test parsing relative database path."""
        client = DatabaseQueryClient(
            connection_string="sqlite+aiosqlite:///./data/test.db"
        )
        assert client.db_path == "data/test.db"

    def test_parse_db_path_absolute(self):
        """Test parsing absolute database path."""
        client = DatabaseQueryClient(
            connection_string="sqlite:////absolute/path/test.db"
        )
        assert "test.db" in client.db_path
