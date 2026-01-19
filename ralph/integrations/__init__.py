# -*- coding: utf-8 -*-
"""
Crypto Data API Integrations for Ralph

Available integrations:
- defillama: DeFi TVL, fees, revenue
- l2beat: L2 security, risks, activity
- coingecko: Token prices, market data
- etherscan: Wallet data, gas, transactions
- thegraph: Protocol-specific GraphQL
- dune: Custom SQL queries (requires API key)

Quick start:
    from integrations import defillama, l2beat, coingecko

    # Get L2 TVL comparison
    l2s = defillama.get_l2_comparison()

    # Get L2 security analysis
    risks = l2beat.get_l2_risk_scores()

    # Get token prices
    prices = coingecko.get_price(["ethereum", "arbitrum"])
"""

from . import defillama
from . import l2beat
from . import coingecko
from . import etherscan
from . import thegraph
from . import dune

__all__ = [
    "defillama",
    "l2beat",
    "coingecko",
    "etherscan",
    "thegraph",
    "dune",
]

# Version
__version__ = "0.1.0"
