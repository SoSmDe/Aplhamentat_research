# -*- coding: utf-8 -*-
"""
Stock Market Data API Integrations for Ralph

Available integrations:
- yfinance: Prices, fundamentals, financials (no API key needed)
- finnhub: News, insider trading, real-time quotes
- fred: Macro data, rates, economic indicators
- sec_edgar: Official SEC filings (10-K, 10-Q, 13-F)
- fmp: DCF valuation, ratios, stock screener

Quick start:
    from integrations.stocks import yfinance_client, finnhub, fred

    # Get stock fundamentals
    info = yfinance_client.get_stock_info("AAPL")

    # Get macro data
    rates = fred.get_macro_dashboard()

    # Get company news
    news = finnhub.get_company_news("AAPL")
"""

from . import yfinance_client
from . import finnhub
from . import fred
from . import sec_edgar
from . import fmp

__all__ = [
    "yfinance_client",
    "finnhub",
    "fred",
    "sec_edgar",
    "fmp",
]

__version__ = "0.1.0"
