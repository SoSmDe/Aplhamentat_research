# -*- coding: utf-8 -*-
"""
CoinGecko API Integration

USE FOR:
- Token/coin prices (current and historical)
- Market cap rankings
- Price charts and sparklines
- Global crypto market stats
- Token metadata (description, links, social)
- Exchange volumes
- Derivatives data (futures, options)

DO NOT USE FOR:
- On-chain data (use Etherscan/Dune)
- DeFi TVL (use DefiLlama)
- L2 security analysis (use L2Beat)
- Wallet balances (use Etherscan)
- Protocol-specific data (use TheGraph)

RATE LIMIT: 10-50 calls/min (demo), unlimited (pro)
API KEY: Not required for basic usage
"""

import requests
from typing import Optional, List
from datetime import datetime
import time

BASE_URL = "https://api.coingecko.com/api/v3"

# Rate limiting
_last_request = 0
_min_interval = 1.5  # seconds between requests


def _rate_limit():
    """Simple rate limiter."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request = time.time()


def get_price(coin_ids: List[str], vs_currencies: str = "usd",
              include_24h_change: bool = True,
              include_market_cap: bool = True) -> dict:
    """
    Get current prices for coins.

    Args:
        coin_ids: List of CoinGecko IDs (e.g., ["bitcoin", "ethereum"])
        vs_currencies: Currency to compare (default: usd)
        include_24h_change: Include 24h price change
        include_market_cap: Include market cap

    Returns: Price data per coin

    Use case: Quick price check, portfolio valuation
    """
    _rate_limit()
    ids = ",".join(coin_ids)
    params = {
        "ids": ids,
        "vs_currencies": vs_currencies,
        "include_24hr_change": str(include_24h_change).lower(),
        "include_market_cap": str(include_market_cap).lower()
    }
    response = requests.get(f"{BASE_URL}/simple/price", params=params)
    response.raise_for_status()
    return response.json()


def get_coin_details(coin_id: str) -> dict:
    """
    Get comprehensive coin data.

    Args:
        coin_id: CoinGecko ID (e.g., "ethereum", "arbitrum")

    Returns:
    - Description, links, social
    - Market data (price, volume, market cap)
    - Developer data (github stats)
    - Community data (social followers)

    Use case: Token deep dive, fundamental analysis
    """
    _rate_limit()
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "true",
        "developer_data": "true"
    }
    response = requests.get(f"{BASE_URL}/coins/{coin_id}", params=params)
    response.raise_for_status()
    return response.json()


def get_price_history(coin_id: str, days: int = 30,
                      vs_currency: str = "usd") -> dict:
    """
    Get historical price data.

    Args:
        coin_id: CoinGecko ID
        days: Number of days (1, 7, 14, 30, 90, 180, 365, max)
        vs_currency: Currency to compare

    Returns:
    - prices: [[timestamp, price], ...]
    - market_caps: [[timestamp, market_cap], ...]
    - total_volumes: [[timestamp, volume], ...]

    Use case: Price charts, trend analysis
    """
    _rate_limit()
    response = requests.get(
        f"{BASE_URL}/coins/{coin_id}/market_chart",
        params={"vs_currency": vs_currency, "days": days}
    )
    response.raise_for_status()
    return response.json()


def get_top_coins(limit: int = 100, vs_currency: str = "usd") -> list:
    """
    Get top coins by market cap.

    Args:
        limit: Number of coins (max 250)
        vs_currency: Currency to compare

    Returns: List of coins with full market data

    Use case: Market overview, rankings
    """
    _rate_limit()
    response = requests.get(
        f"{BASE_URL}/coins/markets",
        params={
            "vs_currency": vs_currency,
            "order": "market_cap_desc",
            "per_page": limit,
            "sparkline": "true"
        }
    )
    response.raise_for_status()
    return response.json()


def get_global_stats() -> dict:
    """
    Get global crypto market statistics.

    Returns:
    - total_market_cap
    - total_volume
    - btc_dominance
    - eth_dominance
    - market_cap_change_24h
    - active_cryptocurrencies

    Use case: Market overview, macro analysis
    """
    _rate_limit()
    response = requests.get(f"{BASE_URL}/global")
    response.raise_for_status()
    return response.json()["data"]


def get_defi_stats() -> dict:
    """
    Get DeFi market statistics.

    Returns:
    - defi_market_cap
    - eth_market_cap
    - defi_to_eth_ratio
    - trading_volume_24h
    - defi_dominance

    Use case: DeFi market overview
    """
    _rate_limit()
    response = requests.get(f"{BASE_URL}/global/decentralized_finance_defi")
    response.raise_for_status()
    return response.json()["data"]


def get_trending() -> dict:
    """
    Get trending coins (most searched).

    Returns: List of trending coins

    Use case: Market sentiment, hot topics
    """
    _rate_limit()
    response = requests.get(f"{BASE_URL}/search/trending")
    response.raise_for_status()
    return response.json()


def search_coins(query: str) -> dict:
    """
    Search for coins by name or symbol.

    Args:
        query: Search term

    Returns: List of matching coins with IDs

    Use case: Find CoinGecko ID for a token
    """
    _rate_limit()
    response = requests.get(f"{BASE_URL}/search", params={"query": query})
    response.raise_for_status()
    return response.json()


# ============ HELPER FUNCTIONS ============

# Common coin IDs for quick reference
COIN_IDS = {
    # Major
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
    "USDC": "usd-coin",
    "BNB": "binancecoin",
    "SOL": "solana",

    # L2 tokens
    "ARB": "arbitrum",
    "OP": "optimism",
    "MATIC": "matic-network",
    "STRK": "starknet",
    "MNT": "mantle",
    "METIS": "metis-token",
    "IMX": "immutable-x",

    # DeFi
    "UNI": "uniswap",
    "AAVE": "aave",
    "LINK": "chainlink",
    "LDO": "lido-dao",
    "MKR": "maker",
    "CRV": "curve-dao-token",
}


def get_l2_token_prices() -> dict:
    """
    Get prices for major L2 tokens.

    Returns: Dict with L2 token prices
    """
    l2_ids = [
        "arbitrum", "optimism", "matic-network",
        "starknet", "mantle", "metis-token", "immutable-x"
    ]
    return get_price(l2_ids)


def get_eth_price_with_history(days: int = 30) -> dict:
    """
    Get ETH price with history.

    Returns:
    - current_price
    - price_change_24h
    - price_change_7d
    - history: [[timestamp, price], ...]
    """
    current = get_price(["ethereum"])
    history = get_price_history("ethereum", days=days)

    return {
        "current_price": current["ethereum"]["usd"],
        "market_cap": current["ethereum"].get("usd_market_cap"),
        "change_24h": current["ethereum"].get("usd_24h_change"),
        "history": history["prices"]
    }


def get_market_overview() -> dict:
    """
    Get comprehensive market overview.

    Returns:
    - Global stats
    - DeFi stats
    - Top coins
    - Trending
    """
    global_stats = get_global_stats()
    defi_stats = get_defi_stats()
    top_5 = get_top_coins(5)
    trending = get_trending()

    return {
        "global": {
            "total_market_cap": global_stats["total_market_cap"]["usd"],
            "total_volume_24h": global_stats["total_volume"]["usd"],
            "btc_dominance": global_stats["market_cap_percentage"]["btc"],
            "eth_dominance": global_stats["market_cap_percentage"]["eth"],
            "market_cap_change_24h": global_stats["market_cap_change_percentage_24h_usd"]
        },
        "defi": {
            "market_cap": defi_stats["defi_market_cap"],
            "dominance": defi_stats["defi_dominance"]
        },
        "top_coins": [
            {"name": c["name"], "symbol": c["symbol"], "price": c["current_price"],
             "change_24h": c["price_change_percentage_24h"]}
            for c in top_5
        ],
        "trending": [c["item"]["name"] for c in trending["coins"][:5]]
    }


if __name__ == "__main__":
    print("=== Market Overview ===")
    overview = get_market_overview()
    print(f"Total Market Cap: ${overview['global']['total_market_cap']/1e12:.2f}T")
    print(f"BTC Dominance: {overview['global']['btc_dominance']:.1f}%")
    print(f"ETH Dominance: {overview['global']['eth_dominance']:.1f}%")

    print("\n=== Top 5 Coins ===")
    for c in overview["top_coins"]:
        print(f"  {c['symbol']}: ${c['price']:,.2f} ({c['change_24h']:+.1f}%)")

    print("\n=== Trending ===")
    print(f"  {', '.join(overview['trending'])}")
