"""
Ralph Deep Research - Database Query Client

Read-only database query client for the Data agent to fetch structured data.
Based on specs/ARCHITECTURE.md and IMPLEMENTATION_PLAN.md Phase 4.5.

Why this module:
- Data agent may need to query external databases
- Enforces read-only access for security
- Provides schema introspection
- Integrates with retry logic

IMPORTANT SECURITY NOTES:
- This client ONLY allows SELECT queries
- All queries are parameterized to prevent SQL injection
- Query execution is time-limited (30s default)

Usage:
    from src.tools.db_client import DatabaseQueryClient

    client = DatabaseQueryClient(connection_string="sqlite:///data.db")

    # Execute read-only query
    results = await client.execute_query(
        "SELECT * FROM products WHERE category = ?",
        params=["electronics"]
    )

    # Get table schema
    schema = await client.get_schema_info("products")
"""

from __future__ import annotations

import asyncio
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from src.config.settings import get_settings
from src.tools.errors import (
    DatabaseError,
    InvalidInputError,
)
from src.tools.logging import get_logger
from src.tools.retry import RETRY_CONFIGS, RetryHandler

logger = get_logger(__name__)

# Maximum query execution time
DEFAULT_QUERY_TIMEOUT = 30.0

# Dangerous SQL keywords that indicate non-SELECT queries
DANGEROUS_KEYWORDS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bCREATE\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bREPLACE\b",
    r"\bMERGE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
]


# =============================================================================
# DATA MODELS
# =============================================================================


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    type: str
    nullable: bool = True
    primary_key: bool = False
    default: Any = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type,
            "nullable": self.nullable,
            "primary_key": self.primary_key,
            "default": self.default,
        }


@dataclass
class TableSchema:
    """Schema information for a database table."""
    name: str
    columns: list[ColumnInfo]
    row_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "columns": [col.to_dict() for col in self.columns],
            "row_count": self.row_count,
        }


@dataclass
class QueryResult:
    """Result from a database query."""
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    execution_time: float

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time": self.execution_time,
        }


# =============================================================================
# DATABASE QUERY CLIENT
# =============================================================================


class DatabaseQueryClient:
    """
    Read-only database query client.

    Provides secure, read-only access to databases for the Data agent.
    All queries are validated to ensure they are SELECT-only.

    Why this design:
    - Security: Only SELECT queries allowed
    - Parameterized queries prevent SQL injection
    - Timeout protection prevents long-running queries
    - Schema introspection for query building

    Example:
        client = DatabaseQueryClient("sqlite:///data.db")

        # Simple query
        result = await client.execute_query(
            "SELECT name, price FROM products WHERE category = ?",
            params=["electronics"]
        )

        # With formatting
        data = client.format_as_table(result)
    """

    def __init__(
        self,
        connection_string: str | None = None,
        *,
        query_timeout: float = DEFAULT_QUERY_TIMEOUT,
    ) -> None:
        """
        Initialize database query client.

        Args:
            connection_string: Database connection string (None = use settings)
            query_timeout: Maximum query execution time in seconds
        """
        if connection_string is None:
            settings = get_settings()
            connection_string = settings.database_url

        # Parse connection string to extract database type and path
        self.connection_string = connection_string
        self.query_timeout = query_timeout
        self.retry_handler = RetryHandler(RETRY_CONFIGS["database"])

        # Currently only SQLite is supported
        self.db_type = self._parse_db_type(connection_string)
        self.db_path = self._parse_db_path(connection_string)

        logger.debug(
            "DatabaseQueryClient initialized",
            db_type=self.db_type,
            query_timeout=query_timeout,
        )

    def _parse_db_type(self, connection_string: str) -> str:
        """Extract database type from connection string."""
        if connection_string.startswith("sqlite"):
            return "sqlite"
        elif connection_string.startswith("postgresql"):
            return "postgresql"
        elif connection_string.startswith("mysql"):
            return "mysql"
        else:
            # Default to sqlite
            return "sqlite"

    def _parse_db_path(self, connection_string: str) -> str:
        """Extract database path from connection string."""
        # Handle sqlite+aiosqlite:///./path.db or sqlite:///path.db
        if ":///" in connection_string:
            path = connection_string.split("///")[-1]
            # Handle relative paths
            if path.startswith("./"):
                path = path[2:]
            return path
        return connection_string

    async def execute_query(
        self,
        query: str,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> QueryResult:
        """
        Execute a read-only database query.

        Args:
            query: SQL SELECT query
            params: Query parameters (list for ? placeholders, dict for :name)

        Returns:
            QueryResult with columns, rows, and metadata

        Raises:
            InvalidInputError: If query is not a SELECT query
            DatabaseError: If query execution fails
        """
        # Validate query is read-only
        self._validate_query(query)

        async def _execute() -> QueryResult:
            import time
            start_time = time.time()

            try:
                # Use synchronous SQLite in a thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self._execute_sync,
                        query,
                        params,
                    ),
                    timeout=self.query_timeout,
                )

                execution_time = time.time() - start_time

                return QueryResult(
                    columns=result["columns"],
                    rows=result["rows"],
                    row_count=len(result["rows"]),
                    execution_time=execution_time,
                )

            except asyncio.TimeoutError:
                raise DatabaseError(
                    message=f"Query timed out after {self.query_timeout}s",
                    operation="execute_query",
                )

            except Exception as e:
                raise DatabaseError(
                    message=f"Query execution failed: {e}",
                    operation="execute_query",
                    original_error=str(e),
                )

        return await self.retry_handler.execute(_execute)

    def _execute_sync(
        self,
        query: str,
        params: list[Any] | dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Execute query synchronously (called from thread pool)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        try:
            cursor = conn.cursor()

            if params:
                if isinstance(params, list):
                    cursor.execute(query, params)
                else:
                    cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [description[0] for description in cursor.description or []]

            # Fetch all rows
            rows = [dict(row) for row in cursor.fetchall()]

            return {
                "columns": columns,
                "rows": rows,
            }

        finally:
            conn.close()

    def _validate_query(self, query: str) -> None:
        """
        Validate that query is read-only (SELECT only).

        Raises:
            InvalidInputError: If query contains dangerous keywords
        """
        # Normalize query for checking
        normalized = query.upper().strip()

        # Must start with SELECT, WITH, or EXPLAIN
        valid_starts = ["SELECT", "WITH", "EXPLAIN"]
        if not any(normalized.startswith(start) for start in valid_starts):
            raise InvalidInputError(
                message="Only SELECT queries are allowed",
                field="query",
                expected="SELECT statement",
            )

        # Check for dangerous keywords
        for pattern in DANGEROUS_KEYWORDS:
            if re.search(pattern, normalized, re.IGNORECASE):
                keyword = pattern.replace(r"\b", "").strip()
                raise InvalidInputError(
                    message=f"Query contains forbidden keyword: {keyword}",
                    field="query",
                    expected="read-only SELECT query",
                )

        # Check for semicolons (multiple statements)
        if ";" in query and query.strip().rstrip(";").count(";") > 0:
            raise InvalidInputError(
                message="Multiple statements not allowed",
                field="query",
                expected="single SELECT statement",
            )

        logger.debug("Query validated as read-only", query_preview=query[:100])

    async def get_schema_info(self, table_name: str) -> TableSchema:
        """
        Get schema information for a table.

        Args:
            table_name: Name of the table

        Returns:
            TableSchema with column information

        Raises:
            DatabaseError: If table doesn't exist or query fails
        """
        async def _get_schema() -> TableSchema:
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._get_schema_sync,
                    table_name,
                )
                return result

            except Exception as e:
                raise DatabaseError(
                    message=f"Failed to get schema for {table_name}: {e}",
                    operation="get_schema_info",
                    original_error=str(e),
                )

        return await self.retry_handler.execute(_get_schema)

    def _get_schema_sync(self, table_name: str) -> TableSchema:
        """Get schema information synchronously."""
        # Validate table name to prevent injection
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            raise InvalidInputError(
                message="Invalid table name",
                field="table_name",
                value=table_name,
                expected="alphanumeric with underscores",
            )

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Get column info using PRAGMA
            cursor.execute(f"PRAGMA table_info({table_name})")
            pragma_result = cursor.fetchall()

            if not pragma_result:
                raise DatabaseError(
                    message=f"Table not found: {table_name}",
                    operation="get_schema_info",
                )

            columns = []
            for row in pragma_result:
                columns.append(ColumnInfo(
                    name=row[1],
                    type=row[2],
                    nullable=not row[3],
                    primary_key=bool(row[5]),
                    default=row[4],
                ))

            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]

            return TableSchema(
                name=table_name,
                columns=columns,
                row_count=row_count,
            )

        finally:
            conn.close()

    async def list_tables(self) -> list[str]:
        """
        List all tables in the database.

        Returns:
            List of table names
        """
        result = await self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row["name"] for row in result.rows]

    def format_as_table(self, result: QueryResult) -> list[dict[str, Any]]:
        """
        Format query result as a list of dictionaries.

        This is already the format returned by execute_query,
        but this method is provided for consistency with DataResult.tables.
        """
        return result.rows

    def format_as_data_table(self, result: QueryResult, name: str = "Data") -> dict[str, Any]:
        """
        Format query result as DataTable structure for Data agent.

        Args:
            result: Query result
            name: Table name

        Returns:
            Dictionary matching DataTable schema
        """
        return {
            "name": name,
            "headers": result.columns,
            "rows": [[row.get(col, "") for col in result.columns] for row in result.rows],
        }


# =============================================================================
# MOCK CLIENT (Testing)
# =============================================================================


class MockDatabaseClient(DatabaseQueryClient):
    """
    Mock database client for testing.

    Returns predefined results without actual database access.
    """

    def __init__(
        self,
        mock_results: dict[str, QueryResult] | None = None,
    ) -> None:
        """
        Initialize mock client.

        Args:
            mock_results: Dictionary mapping query patterns to results
        """
        self.mock_results = mock_results or {}
        self.query_history: list[dict[str, Any]] = []
        self.query_timeout = DEFAULT_QUERY_TIMEOUT

    async def execute_query(
        self,
        query: str,
        params: list[Any] | dict[str, Any] | None = None,
    ) -> QueryResult:
        """Return mock query result."""
        self._validate_query(query)

        self.query_history.append({
            "query": query,
            "params": params,
        })

        # Look for matching mock result
        for pattern, result in self.mock_results.items():
            if pattern in query:
                return result

        # Default mock result
        return QueryResult(
            columns=["id", "name", "value"],
            rows=[
                {"id": 1, "name": "mock_item", "value": 100},
            ],
            row_count=1,
            execution_time=0.01,
        )

    def set_result(self, pattern: str, result: QueryResult) -> None:
        """Set mock result for a query pattern."""
        self.mock_results[pattern] = result

    def get_queries(self) -> list[dict[str, Any]]:
        """Get history of queries executed."""
        return self.query_history

    def clear_history(self) -> None:
        """Clear query history."""
        self.query_history = []


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def get_db_client(
    connection_string: str | None = None,
) -> DatabaseQueryClient:
    """
    Get database query client.

    Args:
        connection_string: Database connection string (None = use settings)

    Returns:
        Configured DatabaseQueryClient
    """
    return DatabaseQueryClient(connection_string=connection_string)


def create_mock_db_client(
    results: dict[str, QueryResult] | None = None,
) -> MockDatabaseClient:
    """
    Create mock database client for testing.

    Args:
        results: Dictionary of mock results

    Returns:
        MockDatabaseClient instance
    """
    return MockDatabaseClient(mock_results=results)
