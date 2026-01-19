"""
Ralph Deep Research - API Routes

FastAPI router with all endpoints for research session management.
Reference: specs/ralph_prd.md Section 8

Endpoints:
- POST /api/sessions - Start new research session
- POST /api/sessions/{session_id}/messages - Send message during brief building
- POST /api/sessions/{session_id}/approve - Approve brief and start research
- GET /api/sessions/{session_id} - Get session status
- GET /api/sessions/{session_id}/results - Get results and reports
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Path, status

from src.api.dependencies import (
    SessionManagerDep,
    SettingsDep,
    get_session_manager,
)
from src.api.schemas import (
    AggregatedResearch,
    ApproveBriefRequest,
    BriefBuilderAction,
    CreateSessionRequest,
    ErrorResponse,
    HealthResponse,
    ProgressInfo,
    ReportInfo,
    ResultsResponse,
    SendMessageRequest,
    Session,
    SessionResponse,
    SessionStatus,
    StatusResponse,
)
from src.tools.errors import (
    BriefNotApprovedError,
    InvalidInputError,
    RalphError,
    SessionFailedError,
    SessionNotFoundError,
)
from src.tools.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Router Setup
# =============================================================================

router = APIRouter(prefix="/api", tags=["research"])


# =============================================================================
# Background Task Tracking
# =============================================================================

# Track running background tasks by session_id
_background_tasks: dict[str, asyncio.Task[Any]] = {}


def get_background_task(session_id: str) -> asyncio.Task[Any] | None:
    """Get a running background task for a session."""
    return _background_tasks.get(session_id)


def set_background_task(session_id: str, task: asyncio.Task[Any]) -> None:
    """Register a background task for a session."""
    _background_tasks[session_id] = task


def remove_background_task(session_id: str) -> None:
    """Remove a background task registration."""
    _background_tasks.pop(session_id, None)


# =============================================================================
# Pipeline Factory (Lazy Import to Avoid Circular Dependencies)
# =============================================================================


async def create_pipeline(session_manager: SessionManagerDep, settings: SettingsDep):
    """
    Create a ResearchPipeline instance with all required dependencies.

    This factory function handles lazy imports to avoid circular dependencies
    and creates fresh agent instances for each pipeline.
    """
    from src.agents.aggregator import AggregatorAgent
    from src.agents.brief_builder import BriefBuilderAgent
    from src.agents.data import DataAgent
    from src.agents.initial_research import InitialResearchAgent
    from src.agents.planner import PlannerAgent
    from src.agents.reporter import ReporterAgent
    from src.agents.research import ResearchAgent
    from src.orchestrator.pipeline import ResearchPipeline
    from src.storage.files import FileStorage
    from src.tools.api_client import FinancialAPIClient
    from src.tools.file_generator import FileGenerator
    from src.tools.llm import create_llm_client
    from src.tools.web_search import get_search_client

    # Create LLM client
    llm_client = create_llm_client(api_key=settings.anthropic_api_key)

    # Create tool clients
    search_client = get_search_client(api_key=settings.serper_api_key)
    financial_client = FinancialAPIClient(api_key=settings.financial_api_key)
    file_storage = FileStorage()
    file_generator = FileGenerator()

    # Create agents
    initial_research_agent = InitialResearchAgent(
        llm_client=llm_client,
        session_manager=session_manager,
        search_client=search_client,
    )

    brief_builder_agent = BriefBuilderAgent(
        llm_client=llm_client,
        session_manager=session_manager,
    )

    planner_agent = PlannerAgent(
        llm_client=llm_client,
        session_manager=session_manager,
    )

    data_agent = DataAgent(
        llm_client=llm_client,
        session_manager=session_manager,
        financial_client=financial_client,
    )

    research_agent = ResearchAgent(
        llm_client=llm_client,
        session_manager=session_manager,
        search_client=search_client,
    )

    aggregator_agent = AggregatorAgent(
        llm_client=llm_client,
        session_manager=session_manager,
    )

    reporter_agent = ReporterAgent(
        llm_client=llm_client,
        session_manager=session_manager,
        file_generator=file_generator,
        file_storage=file_storage,
    )

    # Create pipeline
    pipeline = ResearchPipeline(
        session_manager=session_manager,
        initial_research_agent=initial_research_agent,
        brief_builder_agent=brief_builder_agent,
        planner_agent=planner_agent,
        data_agent=data_agent,
        research_agent=research_agent,
        aggregator_agent=aggregator_agent,
        reporter_agent=reporter_agent,
    )

    return pipeline


# =============================================================================
# Health Check
# =============================================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check API health and get version information",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse: Status, version, and timestamp
    """
    return HealthResponse(
        status="ok",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


# =============================================================================
# Session Management Endpoints
# =============================================================================


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start new research session",
    description="Create a new research session and run initial research",
    responses={
        201: {"description": "Session created successfully"},
        422: {"description": "Validation error", "model": ErrorResponse},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
async def create_session(
    request: CreateSessionRequest,
    session_manager: SessionManagerDep,
    settings: SettingsDep,
) -> SessionResponse:
    """
    Start a new research session.

    This endpoint:
    1. Creates a new session in the database
    2. Runs Initial Research to analyze the query
    3. Starts Brief Builder conversation

    Args:
        request: Session creation request with initial query
        session_manager: Session manager dependency
        settings: Application settings

    Returns:
        SessionResponse: Session info with first Brief Builder message
    """
    try:
        # Generate user_id if not provided
        user_id = request.user_id or f"user_{uuid.uuid4().hex[:8]}"

        logger.info(
            "Creating new session",
            user_id=user_id,
            query_length=len(request.initial_query),
        )

        # Create pipeline and start session
        pipeline = await create_pipeline(session_manager, settings)
        response = await pipeline.start_session(
            user_id=user_id,
            initial_query=request.initial_query,
        )

        logger.info(
            "Session created",
            session_id=response.session_id,
            status=response.status,
        )

        return response

    except InvalidInputError as e:
        logger.warning("Invalid input for session creation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.to_dict(),
        )
    except RalphError as e:
        logger.error("Error creating session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=SessionResponse,
    summary="Send message during brief building",
    description="Send a message to the Brief Builder agent",
    responses={
        200: {"description": "Message processed"},
        404: {"description": "Session not found", "model": ErrorResponse},
        409: {"description": "Session in invalid state", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def send_message(
    session_id: Annotated[str, Path(description="Session ID")],
    request: SendMessageRequest,
    session_manager: SessionManagerDep,
    settings: SettingsDep,
) -> SessionResponse:
    """
    Send a message during brief building phase.

    This endpoint processes user messages through the Brief Builder agent
    to refine the research specification.

    Args:
        session_id: Session ID
        request: Message content
        session_manager: Session manager dependency
        settings: Application settings

    Returns:
        SessionResponse: Brief Builder response with updated brief
    """
    try:
        logger.info(
            "Processing message",
            session_id=session_id,
            message_length=len(request.content),
        )

        # Verify session exists
        session = await session_manager.get_session(session_id)

        # Check session is in brief building state
        if session.status not in [SessionStatus.BRIEF, SessionStatus.INITIAL_RESEARCH]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session is in {session.status} state, cannot send messages",
            )

        # Create pipeline and process message
        pipeline = await create_pipeline(session_manager, settings)
        response = await pipeline.process_message(
            session_id=session_id,
            content=request.content,
        )

        logger.info(
            "Message processed",
            session_id=session_id,
            action=response.action,
        )

        return response

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    except SessionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.to_dict(),
        )
    except InvalidInputError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=e.to_dict(),
        )
    except RalphError as e:
        logger.error("Error processing message", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )


@router.post(
    "/sessions/{session_id}/approve",
    response_model=SessionResponse,
    summary="Approve brief and start research",
    description="Approve the research brief and start background execution",
    responses={
        200: {"description": "Brief approved, research started"},
        400: {"description": "Brief not ready for approval", "model": ErrorResponse},
        404: {"description": "Session not found", "model": ErrorResponse},
        409: {"description": "Session in invalid state", "model": ErrorResponse},
    },
)
async def approve_brief(
    session_id: Annotated[str, Path(description="Session ID")],
    request: ApproveBriefRequest,
    background_tasks: BackgroundTasks,
    session_manager: SessionManagerDep,
    settings: SettingsDep,
) -> SessionResponse:
    """
    Approve the research brief and start execution.

    This endpoint:
    1. Approves the brief (with optional modifications)
    2. Triggers background research execution
    3. Returns immediately with executing status

    Args:
        session_id: Session ID
        request: Optional modifications to the brief
        background_tasks: FastAPI background tasks
        session_manager: Session manager dependency
        settings: Application settings

    Returns:
        SessionResponse: Session with executing status
    """
    try:
        logger.info(
            "Approving brief",
            session_id=session_id,
            has_modifications=request.modifications is not None,
        )

        # Verify session exists
        session = await session_manager.get_session(session_id)

        # Check session is in brief state
        if session.status != SessionStatus.BRIEF:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Session is in {session.status} state, cannot approve brief",
            )

        # Create pipeline and approve brief
        pipeline = await create_pipeline(session_manager, settings)
        response = await pipeline.approve_brief(
            session_id=session_id,
            modifications=request.modifications,
        )

        # Start background execution if brief was approved
        if response.action == BriefBuilderAction.BRIEF_APPROVED:
            logger.info("Starting background research execution", session_id=session_id)

            async def run_research():
                """Background task to run research pipeline."""
                try:
                    # Create fresh pipeline for background execution
                    bg_pipeline = await create_pipeline(session_manager, settings)
                    await bg_pipeline._run_execution_loop(session_id)
                except Exception as e:
                    logger.error(
                        "Background research failed",
                        session_id=session_id,
                        error=str(e),
                    )
                    # Error handling is done within the pipeline
                finally:
                    remove_background_task(session_id)

            # Create and track background task
            task = asyncio.create_task(run_research())
            set_background_task(session_id, task)

        logger.info(
            "Brief approved",
            session_id=session_id,
            status=response.status,
        )

        return response

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    except BriefNotApprovedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.to_dict(),
        )
    except SessionFailedError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.to_dict(),
        )
    except RalphError as e:
        logger.error("Error approving brief", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )


@router.get(
    "/sessions/{session_id}",
    response_model=StatusResponse,
    summary="Get session status",
    description="Get current status and progress of a research session",
    responses={
        200: {"description": "Session status"},
        404: {"description": "Session not found", "model": ErrorResponse},
    },
)
async def get_session_status(
    session_id: Annotated[str, Path(description="Session ID")],
    session_manager: SessionManagerDep,
    settings: SettingsDep,
) -> StatusResponse:
    """
    Get session status and progress.

    Args:
        session_id: Session ID
        session_manager: Session manager dependency
        settings: Application settings

    Returns:
        StatusResponse: Current status with progress info
    """
    try:
        logger.debug("Getting session status", session_id=session_id)

        # Create pipeline and get status
        pipeline = await create_pipeline(session_manager, settings)
        response = await pipeline.get_status(session_id)

        return response

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    except RalphError as e:
        logger.error("Error getting status", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )


@router.get(
    "/sessions/{session_id}/results",
    response_model=ResultsResponse,
    summary="Get research results",
    description="Get aggregated research results and report download links",
    responses={
        200: {"description": "Research results"},
        404: {"description": "Session not found", "model": ErrorResponse},
        409: {"description": "Results not ready", "model": ErrorResponse},
    },
)
async def get_session_results(
    session_id: Annotated[str, Path(description="Session ID")],
    session_manager: SessionManagerDep,
    settings: SettingsDep,
) -> ResultsResponse:
    """
    Get research results.

    Args:
        session_id: Session ID
        session_manager: Session manager dependency
        settings: Application settings

    Returns:
        ResultsResponse: Aggregated research and report links
    """
    try:
        logger.debug("Getting session results", session_id=session_id)

        # Verify session exists
        session = await session_manager.get_session(session_id)

        # Check if results are ready
        if session.status not in [SessionStatus.DONE, SessionStatus.REPORTING, SessionStatus.AGGREGATING]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Results not ready. Session is in {session.status} state",
            )

        # Create pipeline and get results
        pipeline = await create_pipeline(session_manager, settings)
        response = await pipeline.get_results(session_id)

        return response

    except SessionNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session not found: {session_id}",
        )
    except RalphError as e:
        logger.error("Error getting results", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.to_dict(),
        )
