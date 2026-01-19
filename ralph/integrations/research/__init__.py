# -*- coding: utf-8 -*-
"""
Research & Consulting Firm Data Integrations for Ralph

Available integrations:
- worldbank: Macro indicators, GDP, inflation, development data (API)
- imf: Economic outlook, forecasts (API)
- deloitte: Industry insights via RSS feeds
- mckinsey: Global Institute reports, industry insights
- goldman: Public market research
- aggregator: Multi-source search

Quick start:
    from integrations.research import worldbank, deloitte, aggregator

    # Get GDP data
    gdp = worldbank.get_indicator("NY.GDP.MKTP.CD", country="USA")

    # Get latest Deloitte insights
    articles = deloitte.get_latest("tech", limit=10)

    # Search across all sources
    results = aggregator.search("AI productivity impact")
"""

from . import worldbank
from . import imf
from . import deloitte
from . import mckinsey
from . import goldman
from . import aggregator

__all__ = [
    "worldbank",
    "imf",
    "deloitte",
    "mckinsey",
    "goldman",
    "aggregator",
]

__version__ = "0.1.0"
