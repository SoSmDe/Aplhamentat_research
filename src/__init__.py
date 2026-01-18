# Ralph Deep Research - Main package
"""
Ralph Deep Research System

A multi-agent AI research automation system that accepts user queries,
conducts comprehensive research through specialized agents, and generates
professional reports (PDF, Excel, PowerPoint).

Architecture:
- 7 specialized agents (Initial Research, Brief Builder, Planner, Data, Research, Aggregator, Reporter)
- Ralph Pattern: Execute task → Save result → Clear context → Next task
- Parallel execution of Data and Research agents via asyncio.gather()
"""

__version__ = "0.1.0"
__author__ = "Ralph Team"
