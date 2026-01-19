"""
Ralph Deep Research - Application Entry Point

A multi-agent AI research automation system that accepts user queries,
conducts comprehensive research through specialized agents, and generates
professional reports (PDF, Excel, PowerPoint).

Usage:
    uvicorn main:app --reload --port 8000
    # or
    python main.py
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.dependencies import set_database, set_session_manager
from src.api.routes import router as api_router
from src.api.schemas import ErrorResponse
from src.config.settings import get_settings
from src.storage.database import Database
from src.storage.session import SessionManager
from src.tools.errors import (
    InvalidInputError,
    PermanentError,
    RalphError,
    SessionFailedError,
    SessionNotFoundError,
    TransientError,
)
from src.tools.logging import configure_logging, get_logger

# Get logger (logging will be configured during lifespan)
logger = get_logger(__name__)


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.

    Startup:
    - Initialize database connection
    - Create database tables if needed
    - Initialize session manager
    - Store instances in app state and dependencies

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Configure logging
    settings = get_settings()
    configure_logging(log_level=settings.log_level, json_output=not settings.debug)

    logger.info("Starting Ralph Deep Research API")

    # Initialize database
    logger.info("Initializing database", database_url=settings.database_url)
    database = Database(settings.database_url)
    await database.connect()
    await database.init_db()

    # Initialize session manager
    session_manager = SessionManager(database)

    # Store in app state for access in routes
    app.state.database = database
    app.state.session_manager = session_manager

    # Set global instances for dependency injection
    set_database(database)
    set_session_manager(session_manager)

    logger.info("Ralph Deep Research API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Ralph Deep Research API")

    # Close database connection
    if database.is_connected:
        await database.disconnect()
        logger.info("Database connection closed")

    logger.info("Ralph Deep Research API shutdown complete")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Ralph Deep Research",
    description=(
        "Multi-agent AI research automation system that accepts user queries, "
        "conducts comprehensive research through specialized agents, and generates "
        "professional reports (PDF, Excel, PowerPoint)."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# =============================================================================
# Middleware
# =============================================================================

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """
    Add request ID to each request for tracing.

    Extracts X-Request-ID header or generates a new UUID.
    """
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    """
    Log request/response information for debugging.
    """
    start_time = datetime.now(timezone.utc)

    # Skip logging for health checks
    if request.url.path in ["/health", "/api/health"]:
        return await call_next(request)

    request_id = getattr(request.state, "request_id", "unknown")
    logger.info(
        "Request started",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    response = await call_next(request)

    duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    logger.info(
        "Request completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=round(duration_ms, 2),
    )

    return response


# =============================================================================
# Exception Handlers
# =============================================================================


@app.exception_handler(SessionNotFoundError)
async def session_not_found_handler(
    request: Request, exc: SessionNotFoundError
) -> JSONResponse:
    """Handle session not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content=ErrorResponse(
            error="SESSION_NOT_FOUND",
            message=str(exc),
            details=exc.details,
            session_id=exc.details.get("session_id") if exc.details else None,
        ).model_dump(),
    )


@app.exception_handler(SessionFailedError)
async def session_failed_handler(
    request: Request, exc: SessionFailedError
) -> JSONResponse:
    """Handle session failed errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(
            error="SESSION_FAILED",
            message=str(exc),
            details=exc.details,
            session_id=exc.details.get("session_id") if exc.details else None,
        ).model_dump(),
    )


@app.exception_handler(InvalidInputError)
async def invalid_input_handler(
    request: Request, exc: InvalidInputError
) -> JSONResponse:
    """Handle invalid input errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(
            error="INVALID_INPUT",
            message=str(exc),
            details=exc.details,
        ).model_dump(),
    )


@app.exception_handler(TransientError)
async def transient_error_handler(
    request: Request, exc: TransientError
) -> JSONResponse:
    """Handle transient (retryable) errors."""
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=ErrorResponse(
            error=exc.code,
            message=str(exc),
            details=exc.details,
        ).model_dump(),
        headers={"Retry-After": "60"},  # Suggest retry after 60 seconds
    )


@app.exception_handler(PermanentError)
async def permanent_error_handler(
    request: Request, exc: PermanentError
) -> JSONResponse:
    """Handle permanent (non-retryable) errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error=exc.code,
            message=str(exc),
            details=exc.details,
        ).model_dump(),
    )


@app.exception_handler(RalphError)
async def ralph_error_handler(request: Request, exc: RalphError) -> JSONResponse:
    """Handle generic Ralph errors."""
    logger.error("Unhandled Ralph error", error=str(exc), code=exc.code)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=exc.code,
            message=str(exc),
            details=exc.details,
        ).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors."""
    logger.exception("Unexpected error", error=str(exc))
    try:
        debug_mode = get_settings().debug
    except Exception:
        debug_mode = False
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="INTERNAL_ERROR",
            message="An unexpected error occurred",
            details={"error_type": type(exc).__name__} if debug_mode else None,
        ).model_dump(),
    )


# =============================================================================
# Root Endpoints
# =============================================================================


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint.

    Returns:
        dict: Status and version information
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
async def root() -> dict[str, Any]:
    """
    Root endpoint with API information.

    Returns:
        dict: Welcome message and API documentation link
    """
    return {
        "message": "Welcome to Ralph Deep Research API",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api": "/api",
    }


# =============================================================================
# Include API Router
# =============================================================================

app.include_router(api_router)


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    run_settings = get_settings()
    uvicorn.run(
        "main:app",
        host=run_settings.host,
        port=run_settings.port,
        reload=run_settings.debug,
    )
