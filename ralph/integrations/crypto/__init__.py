# -*- coding: utf-8 -*-
"""
Crypto Data API Integrations

Available integrations:
- defillama: DeFi TVL, fees, revenue
- l2beat: L2 security, risks, activity
- coingecko: Token prices, market data
- etherscan: Wallet data, gas, transactions
- thegraph: Protocol-specific GraphQL
- dune: Custom SQL queries (requires API key)
- blocklens: Bitcoin on-chain analytics (LTH/STH, MVRV, SOPR)

Quick start:
    from integrations.crypto import coingecko, defillama, blocklens

    # Get token prices
    prices = coingecko.get_price(["ethereum", "arbitrum"])

    # Get L2 TVL comparison
    l2s = defillama.get_l2_comparison()

    # Get Bitcoin market cycle indicators
    btc_cycle = blocklens.get_market_cycle_indicators()
"""

from . import defillama
from . import l2beat
from . import coingecko
from . import etherscan
from . import thegraph
from . import dune
from . import blocklens

__all__ = [
    "defillama",
    "l2beat",
    "coingecko",
    "etherscan",
    "thegraph",
    "dune",
    "blocklens",
]
