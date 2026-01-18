"""
Ralph Deep Research - Session Manager

Session lifecycle and state management following the Ralph Pattern.
Based on specs/ARCHITECTURE.md (Section 4: State Management).

Ralph Pattern: Execute task → Save result → Clear context → Next task

Why this design:
- Each state change persisted immediately for crash recovery
- All intermediate data stored with type classification
- Session can be restored from any point

Usage:
    manager = SessionManager(database)

    # Create session
    session = await manager.create_session("user_123", "Research Realty Income")

    # Save state (Ralph Pattern)
    await manager.save_state(session.id, DataType.INITIAL_CONTEXT, context_data)

    # Update status
    await manager.update_status(session.id, SessionStatus.BRIEF)

    # Restore for recovery
    full_state = await manager.restore_session(session.id)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from src.api.schemas import Session, SessionError, SessionStatus
from src.storage.database import Database, serialize_json, deserialize_json
from src.tools.errors import (
    DatabaseError,
    InvalidInputError,
    SessionNotFoundError,
    QuotaExceededError,
    StorageFullError,
)
from src.tools.logging import get_logger
from src.config.timeouts import get_limit

logger = get_logger(__name__)


def _utc_now() -> datetime:
    """Return current UTC time with timezone info."""
    return datetime.now(timezone.utc)


# =============================================================================
# DATA TYPE CONSTANTS
# =============================================================================


class DataType(str, Enum):
    """
    Data types stored in session_data table.

    Each type represents a different stage of the research pipeline.
    """

    INITIAL_CONTEXT = "initial_context"
    BRIEF = "brief"
    CONVERSATION = "conversation"  # Brief builder conversation messages
    PLAN = "plan"
    DATA_RESULT = "data_result"
    RESEARCH_RESULT = "research_result"
    PLANNER_DECISION = "planner_decision"
    AGGREGATION = "aggregation"
    REPORT_CONFIG = "report_config"


# Terminal session statuses (no longer active)
TERMINAL_STATUSES = frozenset({
    SessionStatus.DONE,
    SessionStatus.FAILED,
})


# =============================================================================
# SESSION MANAGER
# =============================================================================


class SessionManager:
    """
    Manages session lifecycle and state persistence.

    Implements the Ralph Pattern: After each task completion,
    state is immediately saved to database for crash recovery.

    Features:
    - Session creation with unique ID generation
    - Status transitions with validation
    - State persistence for all data types
    - Full session restoration for recovery
    - Scalability limit enforcement
    """

    def __init__(self, database: Database) -> None:
        """
        Initialize session manager.

        Args:
            database: Database instance for persistence
        """
        self._db = database

    # =========================================================================
    # SESSION CRUD
    # =========================================================================

    @staticmethod
    def _generate_session_id() -> str:
        """
        Generate unique session ID.

        Format: sess_{12 hex chars from uuid4}
        Example: sess_a1b2c3d4e5f6
        """
        return f"sess_{uuid.uuid4().hex[:12]}"

    async def create_session(
        self,
        user_id: str,
        initial_query: str,
    ) -> Session:
        """
        Create a new research session.

        Args:
            user_id: User identifier
            initial_query: Initial research query

        Returns:
            Created Session object

        Raises:
            QuotaExceededError: If max concurrent sessions reached
            InvalidInputError: If input validation fails
        """
        # Validate inputs
        if not user_id or not user_id.strip():
            raise InvalidInputError(
                message="user_id is required",
                field="user_id",
            )
        if not initial_query or len(initial_query.strip()) < 5:
            raise InvalidInputError(
                message="initial_query must be at least 5 characters",
                field="initial_query",
                value=initial_query,
            )

        # Check concurrent session limit
        await self._validate_session_limit()

        # Generate session ID
        session_id = self._generate_session_id()
        now = _utc_now()

        # Insert session
        await self._db.execute(
            """
            INSERT INTO sessions (id, user_id, status, current_round, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id.strip(), SessionStatus.CREATED.value, 0, now.isoformat(), now.isoformat()),
        )

        logger.info(
            "Session created",
            session_id=session_id,
            user_id=user_id,
        )

        return Session(
            id=session_id,
            user_id=user_id.strip(),
            status=SessionStatus.CREATED,
            current_round=0,
            created_at=now,
            updated_at=now,
        )

    async def get_session(self, session_id: str) -> Session:
        """
        Get session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session object

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        row = await self._db.fetch_one(
            "SELECT * FROM sessions WHERE id = ?",
            (session_id,),
        )

        if row is None:
            raise SessionNotFoundError(
                message=f"Session '{session_id}' not found",
                session_id=session_id,
            )

        return self._row_to_session(row)

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        count = await self._db.fetch_value(
            "SELECT COUNT(*) FROM sessions WHERE id = ?",
            (session_id,),
        )
        return count > 0

    async def list_sessions(
        self,
        user_id: str | None = None,
        status: SessionStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Session]:
        """
        List sessions with optional filters.

        Args:
            user_id: Filter by user
            status: Filter by status
            limit: Max results
            offset: Skip first N results

        Returns:
            List of Session objects
        """
        query = "SELECT * FROM sessions WHERE 1=1"
        params: list[Any] = []

        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = await self._db.fetch_all(query, tuple(params))
        return [self._row_to_session(row) for row in rows]

    @staticmethod
    def _row_to_session(row: dict[str, Any]) -> Session:
        """Convert database row to Session object."""
        error = None
        if row.get("error_code"):
            error = SessionError(
                code=row["error_code"],
                message=row.get("error_message", ""),
            )

        return Session(
            id=row["id"],
            user_id=row["user_id"],
            status=SessionStatus(row["status"]),
            current_round=row["current_round"],
            error=error,
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if isinstance(row["updated_at"], str) else row["updated_at"],
        )

    # =========================================================================
    # STATUS MANAGEMENT
    # =========================================================================

    async def update_status(
        self,
        session_id: str,
        status: SessionStatus,
    ) -> None:
        """
        Update session status.

        Args:
            session_id: Session identifier
            status: New status

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        now = _utc_now()

        result = await self._db.execute(
            """
            UPDATE sessions
            SET status = ?, updated_at = ?
            WHERE id = ?
            """,
            (status.value, now.isoformat(), session_id),
        )

        if result.rowcount == 0:
            raise SessionNotFoundError(
                message=f"Session '{session_id}' not found",
                session_id=session_id,
            )

        logger.info(
            "Session status updated",
            session_id=session_id,
            status=status.value,
        )

    async def increment_round(self, session_id: str) -> int:
        """
        Increment session round counter.

        Args:
            session_id: Session identifier

        Returns:
            New round number

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        now = _utc_now()

        # Get current round
        session = await self.get_session(session_id)
        new_round = session.current_round + 1

        await self._db.execute(
            """
            UPDATE sessions
            SET current_round = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_round, now.isoformat(), session_id),
        )

        logger.info(
            "Session round incremented",
            session_id=session_id,
            round=new_round,
        )

        return new_round

    async def set_error(
        self,
        session_id: str,
        error: SessionError,
    ) -> None:
        """
        Set session error and mark as failed.

        Args:
            session_id: Session identifier
            error: Error details
        """
        now = _utc_now()

        await self._db.execute(
            """
            UPDATE sessions
            SET status = ?, error_code = ?, error_message = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                SessionStatus.FAILED.value,
                error.code,
                error.message,
                now.isoformat(),
                session_id,
            ),
        )

        logger.error(
            "Session marked as failed",
            session_id=session_id,
            error_code=error.code,
            error_message=error.message,
        )

    # =========================================================================
    # STATE MANAGEMENT (Ralph Pattern)
    # =========================================================================

    async def save_state(
        self,
        session_id: str,
        data_type: DataType | str,
        data: dict[str, Any],
        round: int | None = None,
        task_id: str | None = None,
    ) -> int:
        """
        Save state to session_data table (Ralph Pattern).

        This is the core persistence method. Call after each agent task completes.

        Args:
            session_id: Session identifier
            data_type: Type of data being stored
            data: Data to store (will be JSON serialized)
            round: Round number (optional)
            task_id: Task ID for task results (optional)

        Returns:
            ID of inserted record

        Raises:
            StorageFullError: If session storage exceeds limit
        """
        # Validate storage limit
        await self._validate_storage_limit(session_id)

        # Serialize data
        json_data = serialize_json(data)
        data_type_value = data_type.value if isinstance(data_type, DataType) else data_type
        now = _utc_now()

        cursor = await self._db.execute(
            """
            INSERT INTO session_data (session_id, data_type, round, task_id, data, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session_id, data_type_value, round, task_id, json_data, now.isoformat()),
        )

        record_id = cursor.lastrowid

        logger.debug(
            "State saved",
            session_id=session_id,
            data_type=data_type_value,
            round=round,
            task_id=task_id,
            record_id=record_id,
        )

        # Update session timestamp
        await self._db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?",
            (now.isoformat(), session_id),
        )

        return record_id

    async def get_state(
        self,
        session_id: str,
        data_type: DataType | str,
        round: int | None = None,
    ) -> dict[str, Any] | None:
        """
        Get most recent state of given type.

        Args:
            session_id: Session identifier
            data_type: Type of data to retrieve
            round: Round number (optional, gets latest if not specified)

        Returns:
            Deserialized data dict, or None if not found
        """
        data_type_value = data_type.value if isinstance(data_type, DataType) else data_type

        if round is not None:
            query = """
                SELECT data FROM session_data
                WHERE session_id = ? AND data_type = ? AND round = ?
                ORDER BY created_at DESC LIMIT 1
            """
            params = (session_id, data_type_value, round)
        else:
            query = """
                SELECT data FROM session_data
                WHERE session_id = ? AND data_type = ?
                ORDER BY created_at DESC LIMIT 1
            """
            params = (session_id, data_type_value)

        row = await self._db.fetch_one(query, params)
        if row is None:
            return None

        return deserialize_json(row["data"])

    async def get_all_states(
        self,
        session_id: str,
        data_type: DataType | str,
    ) -> list[dict[str, Any]]:
        """
        Get all states of given type.

        Args:
            session_id: Session identifier
            data_type: Type of data to retrieve

        Returns:
            List of deserialized data dicts, ordered by creation time
        """
        data_type_value = data_type.value if isinstance(data_type, DataType) else data_type

        rows = await self._db.fetch_all(
            """
            SELECT round, task_id, data, created_at FROM session_data
            WHERE session_id = ? AND data_type = ?
            ORDER BY created_at ASC
            """,
            (session_id, data_type_value),
        )

        return [
            {
                "round": row["round"],
                "task_id": row["task_id"],
                "data": deserialize_json(row["data"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def get_task_result(
        self,
        session_id: str,
        task_id: str,
    ) -> dict[str, Any] | None:
        """
        Get result for a specific task.

        Args:
            session_id: Session identifier
            task_id: Task identifier (e.g., "d1", "r2")

        Returns:
            Deserialized task result, or None if not found
        """
        row = await self._db.fetch_one(
            """
            SELECT data FROM session_data
            WHERE session_id = ? AND task_id = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (session_id, task_id),
        )

        if row is None:
            return None

        return deserialize_json(row["data"])

    async def get_round_results(
        self,
        session_id: str,
        round: int,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Get all results for a specific round.

        Args:
            session_id: Session identifier
            round: Round number

        Returns:
            Dict with data_results and research_results lists
        """
        rows = await self._db.fetch_all(
            """
            SELECT data_type, task_id, data FROM session_data
            WHERE session_id = ? AND round = ? AND data_type IN (?, ?)
            ORDER BY created_at ASC
            """,
            (session_id, round, DataType.DATA_RESULT.value, DataType.RESEARCH_RESULT.value),
        )

        data_results = []
        research_results = []

        for row in rows:
            result = deserialize_json(row["data"])
            if row["data_type"] == DataType.DATA_RESULT.value:
                data_results.append(result)
            else:
                research_results.append(result)

        return {
            "data_results": data_results,
            "research_results": research_results,
        }

    # =========================================================================
    # RECOVERY
    # =========================================================================

    async def restore_session(self, session_id: str) -> dict[str, Any]:
        """
        Restore full session state for crash recovery.

        Reconstructs all data needed to resume a session.

        Args:
            session_id: Session identifier

        Returns:
            Dict containing session and all associated data
        """
        # Get session
        session = await self.get_session(session_id)

        # Get all data by type
        initial_context = await self.get_state(session_id, DataType.INITIAL_CONTEXT)
        brief = await self.get_state(session_id, DataType.BRIEF)
        conversations = await self.get_all_states(session_id, DataType.CONVERSATION)
        plans = await self.get_all_states(session_id, DataType.PLAN)
        planner_decisions = await self.get_all_states(session_id, DataType.PLANNER_DECISION)
        aggregation = await self.get_state(session_id, DataType.AGGREGATION)

        # Get all task results
        data_results = await self.get_all_states(session_id, DataType.DATA_RESULT)
        research_results = await self.get_all_states(session_id, DataType.RESEARCH_RESULT)

        # Get files
        files = await self._db.fetch_all(
            "SELECT * FROM session_files WHERE session_id = ?",
            (session_id,),
        )

        return {
            "session": {
                "id": session.id,
                "user_id": session.user_id,
                "status": session.status.value,
                "current_round": session.current_round,
                "error": session.error.model_dump() if session.error else None,
                "created_at": session.created_at.isoformat() if session.created_at else None,
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            },
            "initial_context": initial_context,
            "brief": brief,
            "conversations": conversations,
            "plans": plans,
            "planner_decisions": planner_decisions,
            "data_results": data_results,
            "research_results": research_results,
            "aggregation": aggregation,
            "files": [dict(f) for f in files],
        }

    async def get_resume_point(
        self,
        session_id: str,
    ) -> tuple[SessionStatus, int]:
        """
        Determine where to resume a session.

        Args:
            session_id: Session identifier

        Returns:
            Tuple of (status_to_resume_at, round_number)

        Raises:
            SessionNotFoundError: If session doesn't exist
        """
        session = await self.get_session(session_id)

        # If session is in terminal state, return current state
        if session.status in TERMINAL_STATUSES:
            return session.status, session.current_round

        # If failed, try to find last successful state
        if session.status == SessionStatus.FAILED:
            # Check what data exists to determine resume point
            if await self.get_state(session_id, DataType.AGGREGATION):
                return SessionStatus.REPORTING, session.current_round
            if await self.get_state(session_id, DataType.PLANNER_DECISION, session.current_round):
                return SessionStatus.REVIEW, session.current_round
            if session.current_round > 0:
                return SessionStatus.EXECUTING, session.current_round
            if await self.get_state(session_id, DataType.BRIEF):
                return SessionStatus.PLANNING, session.current_round
            if await self.get_state(session_id, DataType.INITIAL_CONTEXT):
                return SessionStatus.BRIEF, 0

            return SessionStatus.INITIAL_RESEARCH, 0

        return session.status, session.current_round

    # =========================================================================
    # SCALABILITY LIMIT ENFORCEMENT
    # =========================================================================

    async def _validate_session_limit(self) -> None:
        """
        Validate concurrent session limit.

        Raises:
            QuotaExceededError: If max concurrent sessions reached
        """
        max_sessions = get_limit("max_concurrent_sessions")
        active_count = await self._count_active_sessions()

        if active_count >= max_sessions:
            raise QuotaExceededError(
                message=f"Maximum concurrent sessions ({max_sessions}) reached",
                quota_type="concurrent_sessions",
                current_usage=active_count,
                limit=max_sessions,
            )

    async def _count_active_sessions(self) -> int:
        """Count non-terminal sessions."""
        terminal_values = ",".join(f"'{s.value}'" for s in TERMINAL_STATUSES)
        count = await self._db.fetch_value(
            f"SELECT COUNT(*) FROM sessions WHERE status NOT IN ({terminal_values})",
        )
        return count or 0

    async def _validate_storage_limit(self, session_id: str) -> None:
        """
        Validate session storage limit.

        Raises:
            StorageFullError: If session storage exceeds limit
        """
        max_storage_mb = get_limit("max_storage_per_session_mb")

        # Calculate approximate storage used (JSON data + file sizes)
        data_size = await self._db.fetch_value(
            "SELECT COALESCE(SUM(LENGTH(data)), 0) FROM session_data WHERE session_id = ?",
            (session_id,),
        )
        file_size = await self._db.fetch_value(
            "SELECT COALESCE(SUM(file_size), 0) FROM session_files WHERE session_id = ?",
            (session_id,),
        )

        total_bytes = (data_size or 0) + (file_size or 0)
        total_mb = total_bytes / (1024 * 1024)

        if total_mb >= max_storage_mb:
            raise StorageFullError(
                message=f"Session storage limit ({max_storage_mb}MB) exceeded",
                storage_type="session",
                current_size_mb=total_mb,
                limit_mb=max_storage_mb,
            )

    # =========================================================================
    # CLEANUP
    # =========================================================================

    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session and all associated data.

        Args:
            session_id: Session identifier
        """
        # Foreign key cascade will delete session_data and session_files
        await self._db.execute(
            "DELETE FROM sessions WHERE id = ?",
            (session_id,),
        )

        logger.info("Session deleted", session_id=session_id)

    async def cleanup_old_sessions(
        self,
        older_than_days: int = 30,
    ) -> int:
        """
        Delete sessions older than specified days.

        Args:
            older_than_days: Delete sessions older than this

        Returns:
            Number of sessions deleted
        """
        from datetime import timedelta

        cutoff = (_utc_now() - timedelta(days=older_than_days)).isoformat()

        # Count before delete
        count = await self._db.fetch_value(
            "SELECT COUNT(*) FROM sessions WHERE updated_at < ?",
            (cutoff,),
        )

        await self._db.execute(
            "DELETE FROM sessions WHERE updated_at < ?",
            (cutoff,),
        )

        logger.info("Old sessions cleaned up", count=count, older_than_days=older_than_days)

        return count or 0
