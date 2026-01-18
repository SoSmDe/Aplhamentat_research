# Ralph Deep Research - Orchestrator package
"""
Pipeline coordination and parallel execution for the Ralph research system.

Components:
- ResearchPipeline: Coordinates all agents through the research workflow
- ParallelExecutor: Runs Data and Research agents concurrently via asyncio.gather()

State Flow:
CREATED → INITIAL_RESEARCH → BRIEF → PLANNING → EXECUTING ↔ REVIEW → AGGREGATING → REPORTING → DONE
"""
