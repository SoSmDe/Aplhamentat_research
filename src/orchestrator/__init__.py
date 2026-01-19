# Ralph Deep Research - Orchestrator package
"""
Pipeline coordination and parallel execution for the Ralph research system.

Components:
- ResearchPipeline: Coordinates all agents through the research workflow
- ParallelExecutor: Runs Data and Research agents concurrently via asyncio.gather()

State Flow:
CREATED → INITIAL_RESEARCH → BRIEF → PLANNING → EXECUTING ↔ REVIEW → AGGREGATING → REPORTING → DONE
"""

from src.orchestrator.parallel import (
    ParallelExecutor,
    RoundTimeoutError,
    TaskExecutionError,
    create_parallel_executor,
)
from src.orchestrator.pipeline import (
    ResearchPipeline,
    PipelineError,
    InvalidStateTransitionError,
    MaxRoundsExceededError,
    create_research_pipeline,
    VALID_TRANSITIONS,
)

__all__ = [
    # Parallel executor
    "ParallelExecutor",
    "RoundTimeoutError",
    "TaskExecutionError",
    "create_parallel_executor",
    # Research pipeline
    "ResearchPipeline",
    "PipelineError",
    "InvalidStateTransitionError",
    "MaxRoundsExceededError",
    "create_research_pipeline",
    "VALID_TRANSITIONS",
]
