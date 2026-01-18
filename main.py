"""
Ralph Deep Research - Application Entry Point

A multi-agent AI research automation system that accepts user queries,
conducts comprehensive research through specialized agents, and generates
professional reports (PDF, Excel, PowerPoint).

Usage:
    uvicorn main:app --reload --port 8000
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler for startup and shutdown events.

    Startup:
    - Initialize database connection
    - Create database tables if needed
    - Load configuration

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Startup
    # TODO: Initialize database in Phase 3
    # TODO: Load settings in Phase 1
    yield
    # Shutdown
    # TODO: Cleanup resources


app = FastAPI(
    title="Ralph Deep Research",
    description=(
        "Multi-agent AI research automation system that accepts user queries, "
        "conducts comprehensive research through specialized agents, and generates "
        "professional reports (PDF, Excel, PowerPoint)."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check() -> dict:
    """
    Health check endpoint.

    Returns:
        dict: Status and version information
    """
    return {
        "status": "ok",
        "version": "0.1.0",
    }


@app.get("/")
async def root() -> dict:
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
    }


# API routes will be added in Phase 10
# from src.api.routes import router as api_router
# app.include_router(api_router, prefix="/api")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
