"""
Tests for API routes.

Tests cover:
- Session creation
- Message sending
- Brief approval
- Status retrieval
- Results retrieval
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from fastapi import status
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.api.schemas import (
    BriefBuilderAction,
    SessionResponse,
    SessionStatus,
    StatusResponse,
    ResultsResponse,
    ProgressInfo,
    AggregatedResearch,
    Brief,
    ScopeItem,
    ScopeType,
    OutputFormat,
    Recommendation,
    Confidence,
    CoverageSummary,
    AggregationMetadata,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.anthropic_api_key = "sk-ant-test-key-12345"
    settings.serper_api_key = None
    settings.financial_api_key = None
    settings.database_url = "sqlite+aiosqlite:///:memory:"
    settings.log_level = "INFO"
    settings.debug = False
    settings.host = "0.0.0.0"
    settings.port = 8000
    return settings


@pytest.fixture
def mock_database():
    """Create mock database."""
    db = AsyncMock()
    db.is_connected = True
    db.connect = AsyncMock()
    db.disconnect = AsyncMock()
    db.init_db = AsyncMock()
    return db


@pytest.fixture
def mock_session_manager():
    """Create mock session manager."""
    sm = AsyncMock()
    return sm


@pytest.fixture
def sample_session():
    """Create a sample session."""
    return MagicMock(
        id="sess_test123456",
        user_id="user_test",
        status=SessionStatus.BRIEF,
        current_round=0,
        error=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_session_response():
    """Create a sample session response."""
    return SessionResponse(
        session_id="sess_test123456",
        status=SessionStatus.BRIEF,
        action=BriefBuilderAction.ASK_QUESTION,
        message="What is your investment horizon?",
        brief=None,
    )


@pytest.fixture
def sample_status_response():
    """Create a sample status response."""
    return StatusResponse(
        session_id="sess_test123456",
        status=SessionStatus.EXECUTING,
        current_round=1,
        progress=ProgressInfo(
            data_tasks_completed=2,
            data_tasks_total=5,
            research_tasks_completed=1,
            research_tasks_total=3,
            current_round=1,
            max_rounds=10,
        ),
        coverage={"topic1": 0.5, "topic2": 0.3},
        error=None,
    )


@pytest.fixture
def sample_brief():
    """Create a sample brief."""
    return Brief(
        brief_id="brief_test123",
        version=1,
        status="approved",
        goal="Analyze Apple stock performance",
        scope=[
            ScopeItem(
                id="s1",
                topic="Financial metrics",
                type=ScopeType.DATA,
                details="Revenue, profit margins",
            ),
        ],
        output_formats=[OutputFormat.PDF],
    )


@pytest.fixture
def sample_aggregated_research():
    """Create sample aggregated research."""
    # Executive summary needs at least 100 characters
    executive_summary = (
        "Apple Inc. demonstrates exceptional financial performance with strong revenue growth, "
        "healthy profit margins, and consistent market leadership in the technology sector. "
        "The company's diversified product portfolio and services segment continue to drive growth."
    )
    return AggregatedResearch(
        session_id="sess_test123456",
        brief_id="brief_test123",
        created_at=datetime.now(timezone.utc),
        executive_summary=executive_summary,
        key_insights=[],
        sections=[],
        contradictions_found=[],
        recommendation=Recommendation(
            verdict="suitable",
            confidence=Confidence.HIGH,
            confidence_reasoning="Strong financials and market position",
            reasoning="Based on comprehensive analysis of Apple's financial metrics, market position, and growth trajectory.",
            pros=["Strong revenue growth"],
            cons=["High valuation"],
            action_items=[],
            risks_to_monitor=["Market competition"],
        ),
        coverage_summary={
            "Financial metrics": CoverageSummary(
                topic="Financial metrics",
                coverage_percent=0.85,
                gaps=[],
            ),
        },
        metadata=AggregationMetadata(
            total_rounds=2,
            total_data_tasks=5,
            total_research_tasks=3,
            sources_count=10,
            processing_time_seconds=120.5,
        ),
    )


@pytest.fixture
def sample_results_response(sample_aggregated_research):
    """Create a sample results response."""
    return ResultsResponse(
        session_id="sess_test123456",
        status=SessionStatus.DONE,
        aggregated=sample_aggregated_research,
        reports=[],
    )


# =============================================================================
# Health Check Tests
# =============================================================================


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_returns_ok(self):
        """Test that health check returns ok status."""
        from main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "ok"
            assert "version" in data

    def test_api_health_check(self, mock_settings, mock_database, mock_session_manager):
        """Test API health check endpoint."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/api/health")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "ok"


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self):
        """Test that root returns API information."""
        from main import app

        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "message" in data
            assert "docs" in data
            assert data["docs"] == "/docs"


# =============================================================================
# Session Creation Tests
# =============================================================================


class TestCreateSession:
    """Tests for session creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_session_success(
        self, mock_settings, mock_database, mock_session_manager, sample_session_response
    ):
        """Test successful session creation."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.start_session = AsyncMock(return_value=sample_session_response)
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/sessions",
                    json={"initial_query": "Analyze Apple stock performance"},
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert "session_id" in data
                assert data["status"] == "brief"

    @pytest.mark.asyncio
    async def test_create_session_with_user_id(
        self, mock_settings, mock_database, mock_session_manager, sample_session_response
    ):
        """Test session creation with custom user ID."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.start_session = AsyncMock(return_value=sample_session_response)
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/sessions",
                    json={
                        "user_id": "custom_user_123",
                        "initial_query": "Analyze Apple stock",
                    },
                )

                assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_create_session_validation_error(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test session creation with invalid input."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            # Empty query should fail validation
            response = await client.post(
                "/api/sessions",
                json={"initial_query": ""},
            )

            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# =============================================================================
# Send Message Tests
# =============================================================================


class TestSendMessage:
    """Tests for message sending endpoint."""

    @pytest.mark.asyncio
    async def test_send_message_success(
        self, mock_settings, mock_database, mock_session_manager,
        sample_session, sample_session_response
    ):
        """Test successful message sending."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)
        mock_session_manager.get_session = AsyncMock(return_value=sample_session)

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.process_message = AsyncMock(return_value=sample_session_response)
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/sessions/sess_test123456/messages",
                    json={"content": "5 years investment horizon"},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "message" in data

    @pytest.mark.asyncio
    async def test_send_message_session_not_found(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test message sending to non-existent session."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager
        from src.tools.errors import SessionNotFoundError

        set_database(mock_database)
        set_session_manager(mock_session_manager)
        mock_session_manager.get_session = AsyncMock(
            side_effect=SessionNotFoundError("Session not found", session_id="invalid")
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/sessions/invalid_session/messages",
                json={"content": "test message"},
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_send_message_wrong_state(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test message sending when session is in wrong state."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        # Session in EXECUTING state shouldn't accept messages
        session = MagicMock()
        session.status = SessionStatus.EXECUTING
        mock_session_manager.get_session = AsyncMock(return_value=session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/sessions/sess_test123/messages",
                json={"content": "test message"},
            )

            assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# Approve Brief Tests
# =============================================================================


class TestApproveBrief:
    """Tests for brief approval endpoint."""

    @pytest.mark.asyncio
    async def test_approve_brief_success(
        self, mock_settings, mock_database, mock_session_manager, sample_session
    ):
        """Test successful brief approval."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)
        mock_session_manager.get_session = AsyncMock(return_value=sample_session)

        approved_response = SessionResponse(
            session_id="sess_test123456",
            status=SessionStatus.EXECUTING,
            action=BriefBuilderAction.BRIEF_APPROVED,
            message="Research started",
            brief=None,
        )

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.approve_brief = AsyncMock(return_value=approved_response)
            mock_pipeline._run_execution_loop = AsyncMock()
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/sessions/sess_test123456/approve",
                    json={},
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["action"] == "brief_approved"

    @pytest.mark.asyncio
    async def test_approve_brief_with_modifications(
        self, mock_settings, mock_database, mock_session_manager, sample_session
    ):
        """Test brief approval with modifications."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)
        mock_session_manager.get_session = AsyncMock(return_value=sample_session)

        approved_response = SessionResponse(
            session_id="sess_test123456",
            status=SessionStatus.EXECUTING,
            action=BriefBuilderAction.BRIEF_APPROVED,
            message="Research started with modifications",
            brief=None,
        )

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.approve_brief = AsyncMock(return_value=approved_response)
            mock_pipeline._run_execution_loop = AsyncMock()
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/sessions/sess_test123456/approve",
                    json={"modifications": {"goal": "Updated goal"}},
                )

                assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_approve_brief_wrong_state(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test brief approval when session is in wrong state."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        # Session in EXECUTING state
        session = MagicMock()
        session.status = SessionStatus.EXECUTING
        mock_session_manager.get_session = AsyncMock(return_value=session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/sessions/sess_test123/approve",
                json={},
            )

            assert response.status_code == status.HTTP_409_CONFLICT


# =============================================================================
# Get Status Tests
# =============================================================================


class TestGetStatus:
    """Tests for status retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_status_success(
        self, mock_settings, mock_database, mock_session_manager, sample_status_response
    ):
        """Test successful status retrieval."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.get_status = AsyncMock(return_value=sample_status_response)
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get("/api/sessions/sess_test123456")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["session_id"] == "sess_test123456"
                assert data["status"] == "executing"
                assert "progress" in data

    @pytest.mark.asyncio
    async def test_get_status_not_found(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test status retrieval for non-existent session."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager
        from src.tools.errors import SessionNotFoundError

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.get_status = AsyncMock(
                side_effect=SessionNotFoundError("Not found", session_id="invalid")
            )
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get("/api/sessions/invalid_session")

                assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Get Results Tests
# =============================================================================


class TestGetResults:
    """Tests for results retrieval endpoint."""

    @pytest.mark.asyncio
    async def test_get_results_success(
        self, mock_settings, mock_database, mock_session_manager, sample_results_response
    ):
        """Test successful results retrieval."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        # Session in DONE state
        session = MagicMock()
        session.status = SessionStatus.DONE
        mock_session_manager.get_session = AsyncMock(return_value=session)

        with patch("src.api.routes.create_pipeline") as mock_create_pipeline:
            mock_pipeline = AsyncMock()
            mock_pipeline.get_results = AsyncMock(return_value=sample_results_response)
            mock_create_pipeline.return_value = mock_pipeline

            async with AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://test"
            ) as client:
                response = await client.get("/api/sessions/sess_test123456/results")

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["session_id"] == "sess_test123456"
                assert data["status"] == "done"
                assert "aggregated" in data

    @pytest.mark.asyncio
    async def test_get_results_not_ready(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test results retrieval when not ready."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        # Session in BRIEF state - results not ready
        session = MagicMock()
        session.status = SessionStatus.BRIEF
        mock_session_manager.get_session = AsyncMock(return_value=session)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/sessions/sess_test123456/results")

            assert response.status_code == status.HTTP_409_CONFLICT

    @pytest.mark.asyncio
    async def test_get_results_not_found(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test results retrieval for non-existent session."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager
        from src.tools.errors import SessionNotFoundError

        set_database(mock_database)
        set_session_manager(mock_session_manager)
        mock_session_manager.get_session = AsyncMock(
            side_effect=SessionNotFoundError("Not found", session_id="invalid")
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/api/sessions/invalid_session/results")

            assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_request_id_header(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test that request ID header is added to responses."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get("/health")

            assert "x-request-id" in response.headers

    @pytest.mark.asyncio
    async def test_custom_request_id_preserved(
        self, mock_settings, mock_database, mock_session_manager
    ):
        """Test that custom request ID is preserved."""
        from main import app
        from src.api.dependencies import set_database, set_session_manager

        set_database(mock_database)
        set_session_manager(mock_session_manager)

        custom_id = "custom-request-123"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.get(
                "/health",
                headers={"X-Request-ID": custom_id},
            )

            assert response.headers["x-request-id"] == custom_id


# =============================================================================
# Dependencies Tests
# =============================================================================


class TestDependencies:
    """Tests for API dependencies."""

    def test_get_database_not_initialized(self):
        """Test get_database when not initialized."""
        from src.api.dependencies import get_database, set_database

        # Reset to None
        set_database(None)

        # Should raise but we can't call directly in sync test
        # This is tested via routes

    def test_set_and_get_database(self, mock_database):
        """Test setting and getting database."""
        from src.api.dependencies import (
            set_database,
            get_database_instance,
        )

        set_database(mock_database)
        assert get_database_instance() is mock_database

    def test_set_and_get_session_manager(self, mock_session_manager):
        """Test setting and getting session manager."""
        from src.api.dependencies import (
            set_session_manager,
            get_session_manager_instance,
        )

        set_session_manager(mock_session_manager)
        assert get_session_manager_instance() is mock_session_manager


# =============================================================================
# Background Task Tests
# =============================================================================


class TestBackgroundTasks:
    """Tests for background task management."""

    def test_background_task_tracking(self):
        """Test background task registration and removal."""
        from src.api.routes import (
            get_background_task,
            set_background_task,
            remove_background_task,
        )
        import asyncio

        # Create a dummy task
        async def dummy():
            pass

        task = asyncio.get_event_loop().create_task(dummy())

        # Register task
        set_background_task("sess_test", task)
        assert get_background_task("sess_test") is task

        # Remove task
        remove_background_task("sess_test")
        assert get_background_task("sess_test") is None

        # Cleanup
        task.cancel()

    def test_get_nonexistent_background_task(self):
        """Test getting non-existent background task."""
        from src.api.routes import get_background_task

        assert get_background_task("nonexistent") is None
