"""
Tests for SessionManager class (Phase 3.2).

Verifies:
- Session creation and retrieval
- Status updates and round management
- State persistence (Ralph Pattern)
- Recovery and restore functionality
- Scalability limit enforcement
"""

import asyncio
import os
import tempfile

import pytest
import pytest_asyncio

from src.api.schemas import SessionStatus, SessionError
from src.storage.database import Database
from src.storage.session import (
    SessionManager,
    DataType,
    TERMINAL_STATUSES,
)
from src.tools.errors import (
    InvalidInputError,
    SessionNotFoundError,
    QuotaExceededError,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)
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


@pytest_asyncio.fixture
async def session_manager(database):
    """Create a session manager."""
    return SessionManager(database)


class TestSessionCreation:
    """Tests for session creation."""

    @pytest.mark.asyncio
    async def test_create_session_returns_session(self, session_manager) -> None:
        """create_session should return a Session object."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Research Realty Income for investment",
        )

        assert session is not None
        assert session.id.startswith("sess_")
        assert len(session.id) == 17  # "sess_" + 12 chars
        assert session.user_id == "user_123"
        assert session.status == SessionStatus.CREATED
        assert session.current_round == 0

    @pytest.mark.asyncio
    async def test_create_session_generates_unique_ids(self, session_manager) -> None:
        """Each session should have a unique ID."""
        sessions = []
        for i in range(5):
            session = await session_manager.create_session(
                user_id=f"user_{i}",
                initial_query="Test query for research",
            )
            sessions.append(session)

        ids = [s.id for s in sessions]
        assert len(ids) == len(set(ids))  # All unique

    @pytest.mark.asyncio
    async def test_create_session_validates_user_id(self, session_manager) -> None:
        """create_session should validate user_id."""
        with pytest.raises(InvalidInputError) as exc_info:
            await session_manager.create_session(
                user_id="",
                initial_query="Valid query here",
            )
        assert "user_id" in exc_info.value.details.get("field", "")

    @pytest.mark.asyncio
    async def test_create_session_validates_query_length(self, session_manager) -> None:
        """create_session should validate initial_query length."""
        with pytest.raises(InvalidInputError) as exc_info:
            await session_manager.create_session(
                user_id="user_123",
                initial_query="Hi",  # Too short
            )
        assert "initial_query" in exc_info.value.details.get("field", "")

    @pytest.mark.asyncio
    async def test_create_session_trims_whitespace(self, session_manager) -> None:
        """create_session should trim whitespace from user_id."""
        session = await session_manager.create_session(
            user_id="  user_123  ",
            initial_query="Valid query here",
        )
        assert session.user_id == "user_123"


class TestSessionRetrieval:
    """Tests for session retrieval."""

    @pytest.mark.asyncio
    async def test_get_session_returns_existing(self, session_manager) -> None:
        """get_session should return existing session."""
        created = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test research query",
        )

        retrieved = await session_manager.get_session(created.id)

        assert retrieved.id == created.id
        assert retrieved.user_id == created.user_id
        assert retrieved.status == created.status

    @pytest.mark.asyncio
    async def test_get_session_raises_for_nonexistent(self, session_manager) -> None:
        """get_session should raise for non-existent session."""
        with pytest.raises(SessionNotFoundError) as exc_info:
            await session_manager.get_session("sess_nonexistent")

        assert "sess_nonexistent" in exc_info.value.details.get("session_id", "")

    @pytest.mark.asyncio
    async def test_session_exists(self, session_manager) -> None:
        """session_exists should check existence."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        assert await session_manager.session_exists(session.id) is True
        assert await session_manager.session_exists("sess_nonexistent") is False

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_manager) -> None:
        """list_sessions should return all sessions."""
        for i in range(3):
            await session_manager.create_session(
                user_id="user_123",
                initial_query=f"Query {i} for testing",
            )

        sessions = await session_manager.list_sessions()

        assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_user(self, session_manager) -> None:
        """list_sessions should filter by user_id."""
        await session_manager.create_session("user_1", "Query for user 1")
        await session_manager.create_session("user_1", "Another query for user 1")
        await session_manager.create_session("user_2", "Query for user 2")

        sessions = await session_manager.list_sessions(user_id="user_1")

        assert len(sessions) == 2
        assert all(s.user_id == "user_1" for s in sessions)


class TestStatusManagement:
    """Tests for session status management."""

    @pytest.mark.asyncio
    async def test_update_status(self, session_manager) -> None:
        """update_status should change session status."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        await session_manager.update_status(session.id, SessionStatus.BRIEF)

        updated = await session_manager.get_session(session.id)
        assert updated.status == SessionStatus.BRIEF

    @pytest.mark.asyncio
    async def test_update_status_raises_for_nonexistent(self, session_manager) -> None:
        """update_status should raise for non-existent session."""
        with pytest.raises(SessionNotFoundError):
            await session_manager.update_status(
                "sess_nonexistent",
                SessionStatus.BRIEF,
            )

    @pytest.mark.asyncio
    async def test_increment_round(self, session_manager) -> None:
        """increment_round should increase round counter."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )
        assert session.current_round == 0

        new_round = await session_manager.increment_round(session.id)
        assert new_round == 1

        new_round = await session_manager.increment_round(session.id)
        assert new_round == 2

        updated = await session_manager.get_session(session.id)
        assert updated.current_round == 2

    @pytest.mark.asyncio
    async def test_set_error(self, session_manager) -> None:
        """set_error should mark session as failed with error details."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        error = SessionError(code="TEST_ERROR", message="Test error message")
        await session_manager.set_error(session.id, error)

        updated = await session_manager.get_session(session.id)
        assert updated.status == SessionStatus.FAILED
        assert updated.error is not None
        assert updated.error.code == "TEST_ERROR"
        assert updated.error.message == "Test error message"


class TestStateManagement:
    """Tests for state persistence (Ralph Pattern)."""

    @pytest.mark.asyncio
    async def test_save_and_get_state(self, session_manager) -> None:
        """save_state and get_state should work together."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        test_data = {"key": "value", "number": 42}
        await session_manager.save_state(
            session.id,
            DataType.INITIAL_CONTEXT,
            test_data,
        )

        retrieved = await session_manager.get_state(
            session.id,
            DataType.INITIAL_CONTEXT,
        )

        assert retrieved == test_data

    @pytest.mark.asyncio
    async def test_save_state_with_round(self, session_manager) -> None:
        """save_state should support round-specific data."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        await session_manager.save_state(
            session.id,
            DataType.PLAN,
            {"tasks": ["d1", "r1"]},
            round=1,
        )
        await session_manager.save_state(
            session.id,
            DataType.PLAN,
            {"tasks": ["d2", "r2"]},
            round=2,
        )

        round1_plan = await session_manager.get_state(
            session.id,
            DataType.PLAN,
            round=1,
        )
        round2_plan = await session_manager.get_state(
            session.id,
            DataType.PLAN,
            round=2,
        )

        assert round1_plan["tasks"] == ["d1", "r1"]
        assert round2_plan["tasks"] == ["d2", "r2"]

    @pytest.mark.asyncio
    async def test_save_state_with_task_id(self, session_manager) -> None:
        """save_state should support task-specific data."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        await session_manager.save_state(
            session.id,
            DataType.DATA_RESULT,
            {"metric": "revenue", "value": 1000000},
            round=1,
            task_id="d1",
        )

        result = await session_manager.get_task_result(session.id, "d1")

        assert result["metric"] == "revenue"
        assert result["value"] == 1000000

    @pytest.mark.asyncio
    async def test_get_all_states(self, session_manager) -> None:
        """get_all_states should return all states of a type."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        for i in range(3):
            await session_manager.save_state(
                session.id,
                DataType.CONVERSATION,
                {"message": f"Message {i}"},
            )

        states = await session_manager.get_all_states(
            session.id,
            DataType.CONVERSATION,
        )

        assert len(states) == 3
        messages = [s["data"]["message"] for s in states]
        assert "Message 0" in messages
        assert "Message 1" in messages
        assert "Message 2" in messages

    @pytest.mark.asyncio
    async def test_get_round_results(self, session_manager) -> None:
        """get_round_results should return all results for a round."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        # Save data results
        await session_manager.save_state(
            session.id,
            DataType.DATA_RESULT,
            {"task_id": "d1", "metrics": {}},
            round=1,
            task_id="d1",
        )
        await session_manager.save_state(
            session.id,
            DataType.DATA_RESULT,
            {"task_id": "d2", "metrics": {}},
            round=1,
            task_id="d2",
        )

        # Save research results
        await session_manager.save_state(
            session.id,
            DataType.RESEARCH_RESULT,
            {"task_id": "r1", "findings": []},
            round=1,
            task_id="r1",
        )

        results = await session_manager.get_round_results(session.id, 1)

        assert len(results["data_results"]) == 2
        assert len(results["research_results"]) == 1


class TestRecovery:
    """Tests for session recovery functionality."""

    @pytest.mark.asyncio
    async def test_restore_session(self, session_manager) -> None:
        """restore_session should return full session state."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        # Save various states
        await session_manager.save_state(
            session.id,
            DataType.INITIAL_CONTEXT,
            {"entities": ["Company A"]},
        )
        await session_manager.save_state(
            session.id,
            DataType.BRIEF,
            {"goal": "Research goal"},
        )

        restored = await session_manager.restore_session(session.id)

        assert restored["session"]["id"] == session.id
        assert restored["initial_context"]["entities"] == ["Company A"]
        assert restored["brief"]["goal"] == "Research goal"

    @pytest.mark.asyncio
    async def test_get_resume_point_for_created(self, session_manager) -> None:
        """get_resume_point should return CREATED for new session."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )

        status, round = await session_manager.get_resume_point(session.id)

        assert status == SessionStatus.CREATED
        assert round == 0

    @pytest.mark.asyncio
    async def test_get_resume_point_for_done(self, session_manager) -> None:
        """get_resume_point should return DONE for completed session."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )
        await session_manager.update_status(session.id, SessionStatus.DONE)

        status, round = await session_manager.get_resume_point(session.id)

        assert status == SessionStatus.DONE


class TestScalabilityLimits:
    """Tests for scalability limit enforcement."""

    @pytest.mark.asyncio
    async def test_session_limit_enforcement(self, session_manager, monkeypatch) -> None:
        """Should enforce concurrent session limit."""
        # Mock get_limit to return 2 for testing
        def mock_get_limit(name):
            if name == "max_concurrent_sessions":
                return 2
            return 50  # Default for other limits

        monkeypatch.setattr("src.storage.session.get_limit", mock_get_limit)

        # Create 2 sessions (at limit)
        await session_manager.create_session("user_1", "Query 1 for testing")
        await session_manager.create_session("user_2", "Query 2 for testing")

        # Third should fail
        with pytest.raises(QuotaExceededError) as exc_info:
            await session_manager.create_session("user_3", "Query 3 for testing")

        assert exc_info.value.details["limit"] == 2

    @pytest.mark.asyncio
    async def test_terminal_sessions_not_counted(self, session_manager, monkeypatch) -> None:
        """Terminal sessions should not count toward limit."""
        def mock_get_limit(name):
            if name == "max_concurrent_sessions":
                return 2
            return 50

        monkeypatch.setattr("src.storage.session.get_limit", mock_get_limit)

        # Create and complete 2 sessions
        s1 = await session_manager.create_session("user_1", "Query 1 for testing")
        await session_manager.update_status(s1.id, SessionStatus.DONE)

        s2 = await session_manager.create_session("user_2", "Query 2 for testing")
        await session_manager.update_status(s2.id, SessionStatus.FAILED)

        # Should be able to create 2 more (terminal ones don't count)
        await session_manager.create_session("user_3", "Query 3 for testing")
        await session_manager.create_session("user_4", "Query 4 for testing")


class TestCleanup:
    """Tests for session cleanup."""

    @pytest.mark.asyncio
    async def test_delete_session(self, session_manager) -> None:
        """delete_session should remove session and data."""
        session = await session_manager.create_session(
            user_id="user_123",
            initial_query="Test query here",
        )
        await session_manager.save_state(
            session.id,
            DataType.INITIAL_CONTEXT,
            {"test": "data"},
        )

        await session_manager.delete_session(session.id)

        assert await session_manager.session_exists(session.id) is False


class TestDataTypes:
    """Tests for DataType enum."""

    def test_all_data_types_defined(self) -> None:
        """All expected data types should be defined."""
        expected = {
            "initial_context",
            "brief",
            "conversation",
            "plan",
            "data_result",
            "research_result",
            "planner_decision",
            "aggregation",
            "report_config",
        }
        actual = {dt.value for dt in DataType}
        assert actual == expected

    def test_terminal_statuses(self) -> None:
        """Terminal statuses should be DONE and FAILED."""
        assert SessionStatus.DONE in TERMINAL_STATUSES
        assert SessionStatus.FAILED in TERMINAL_STATUSES
        assert SessionStatus.CREATED not in TERMINAL_STATUSES
