# -*- coding: utf-8 -*-
"""
Research & Knowledge Integrations for Ralph

Available integrations:
- worldbank: Macro indicators, GDP, inflation, development data (API)
- imf: Economic outlook, forecasts (API)
- deloitte: Industry insights via RSS feeds
- mckinsey: Global Institute reports, industry insights
- goldman: Public market research
- aggregator: Multi-source search
- wikipedia: Article summaries, full text, references
- arxiv: Scientific papers (CS, ML, Finance, Crypto)
- serper: Google Search API (requires SERPER_API_KEY)
- pubmed: Medical/biomedical literature from NCBI

Quick start:
    from integrations.research import worldbank, wikipedia, arxiv

    # Get GDP data
    gdp = worldbank.get_indicator("NY.GDP.MKTP.CD", country="USA")

    # Get Wikipedia summary
    summary = wikipedia.get_summary("Bitcoin")

    # Search arXiv papers
    papers = arxiv.search_papers("transformer attention")
"""

from . import worldbank
from . import imf
from . import deloitte
from . import mckinsey
from . import goldman
from . import aggregator
from . import wikipedia
from . import arxiv
from . import serper
from . import pubmed

__all__ = [
    "worldbank",
    "imf",
    "deloitte",
    "mckinsey",
    "goldman",
    "aggregator",
    "wikipedia",
    "arxiv",
    "serper",
    "pubmed",
]

__version__ = "0.1.0"
