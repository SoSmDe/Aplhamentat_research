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
- crunchbase: Company data, funding, investors (requires CRUNCHBASE_API_KEY)
- sec_edgar: SEC filings (10-K, 10-Q, 8-K, 13F)
- google_scholar: Academic papers, citations, author profiles
- news_aggregator: Multi-source news aggregation

Quick start:
    from integrations.research import worldbank, wikipedia, arxiv

    # Get GDP data
    gdp = worldbank.get_indicator("NY.GDP.MKTP.CD", country="USA")

    # Get Wikipedia summary
    summary = wikipedia.get_summary("Bitcoin")

    # Search arXiv papers
    papers = arxiv.search_papers("transformer attention")

    # Search company data
    from integrations.research import crunchbase
    company = crunchbase.get_organization("coinbase")

    # Get SEC filings
    from integrations.research import sec_edgar
    filings = sec_edgar.get_company_filings("COIN", filing_types=["10-K"])

    # Search academic papers
    from integrations.research import google_scholar
    papers = google_scholar.search_papers("blockchain tokenization")

    # Get news
    from integrations.research import news_aggregator
    news = news_aggregator.get_crypto_news()
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
from . import crunchbase
from . import sec_edgar
from . import google_scholar
from . import news_aggregator

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
    "crunchbase",
    "sec_edgar",
    "google_scholar",
    "news_aggregator",
]

__version__ = "0.2.0"
