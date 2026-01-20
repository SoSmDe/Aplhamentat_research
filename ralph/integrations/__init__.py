# -*- coding: utf-8 -*-
"""
Ralph Data Integrations

Organized by domain:
- crypto: Blockchain, DeFi, on-chain analytics
- stocks: Equities, ETFs, macroeconomic data
- research: Reports from major institutions

Quick start:
    # Crypto
    from integrations.crypto import coingecko, defillama, blocklens
    prices = coingecko.get_price(["bitcoin"])
    btc_cycle = blocklens.get_market_cycle_indicators()

    # Stocks
    from integrations.stocks import yfinance_client, fmp
    spy = yfinance_client.get_price_history("SPY", period="1y")

    # Research
    from integrations.research import worldbank, imf
    gdp = worldbank.get_indicator("NY.GDP.MKTP.CD", "USA")
"""

from . import crypto
from . import stocks
from . import research

__all__ = [
    "crypto",
    "stocks",
    "research",
]

# Version
__version__ = "0.2.0"
