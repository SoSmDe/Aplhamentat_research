# -*- coding: utf-8 -*-
"""
DefiLlama API Integration

USE FOR:
- DeFi protocol TVL (total value locked)
- L2/Chain TVL comparison
- Protocol fees and revenue
- Stablecoin market caps
- DeFi yields and APYs
- Bridge volumes
- Historical TVL trends

DO NOT USE FOR:
- Token prices (use CoinGecko)
- Wallet balances (use Etherscan)
- Transaction details (use Etherscan/Dune)
- L2 security/risk assessment (use L2Beat)

RATE LIMIT: None (fair use)
API KEY: Not required
"""

import requests
from typing import Optional
from datetime import datetime

BASE_URL = "https://api.llama.fi"


def get_all_protocols() -> list:
    """
    Get all DeFi protocols with their TVL.

    Returns list of protocols with:
    - name, symbol, chain, tvl, change_1d, change_7d
    - category (DEX, Lending, Bridge, etc.)

    Use case: DeFi market overview, protocol comparison
    """
    response = requests.get(f"{BASE_URL}/protocols")
    response.raise_for_status()
    return response.json()


def get_protocol(name: str) -> dict:
    """
    Get detailed info for a specific protocol.

    Args:
        name: Protocol slug (e.g., "aave", "uniswap", "lido")

    Returns:
    - TVL history (daily)
    - TVL by chain
    - Token info
    - Category, description

    Use case: Deep dive into specific protocol
    """
    response = requests.get(f"{BASE_URL}/protocol/{name}")
    response.raise_for_status()
    return response.json()


def get_all_chains() -> list:
    """
    Get TVL for all chains/L2s.

    Returns list with:
    - name, tvl, tokenSymbol
    - chainId

    Use case: L2 TVL comparison, chain market share
    """
    response = requests.get(f"{BASE_URL}/v2/chains")
    response.raise_for_status()
    return response.json()


def get_chain_tvl(chain: str) -> dict:
    """
    Get historical TVL for a specific chain.

    Args:
        chain: Chain name (e.g., "Ethereum", "Arbitrum", "Optimism")

    Returns: Daily TVL history

    Use case: Chain growth analysis, TVL trends
    """
    response = requests.get(f"{BASE_URL}/v2/historicalChainTvl/{chain}")
    response.raise_for_status()
    return response.json()


def get_all_fees() -> dict:
    """
    Get fees overview for all protocols.

    Returns:
    - total24h, total7d, total30d per protocol
    - Sorted by fees

    Use case: Protocol revenue comparison, fee analysis
    """
    response = requests.get(f"{BASE_URL}/overview/fees")
    response.raise_for_status()
    return response.json()


def get_protocol_fees(protocol: str) -> dict:
    """
    Get detailed fees for a specific protocol.

    Args:
        protocol: Protocol slug (e.g., "arbitrum", "optimism", "uniswap")

    Returns:
    - total24h, total7d, total30d, totalAllTime
    - Daily breakdown

    Use case: L2 fee revenue analysis, protocol economics
    """
    response = requests.get(f"{BASE_URL}/summary/fees/{protocol}")
    response.raise_for_status()
    return response.json()


def get_all_revenue() -> dict:
    """
    Get revenue (fees minus incentives) for all protocols.

    Returns: Net revenue per protocol

    Use case: Real profitability analysis
    """
    response = requests.get(f"{BASE_URL}/overview/revenue")
    response.raise_for_status()
    return response.json()


def get_stablecoins() -> dict:
    """
    Get all stablecoins with market caps.

    Returns:
    - Market cap per stablecoin
    - Chain distribution
    - Peg deviation

    Use case: Stablecoin analysis, liquidity assessment
    """
    response = requests.get(f"{BASE_URL}/stablecoins")
    response.raise_for_status()
    return response.json()


def get_yields() -> list:
    """
    Get DeFi yields across all pools.

    Returns:
    - APY, TVL per pool
    - Protocol, chain
    - Risk indicators

    Use case: Yield farming analysis, APY comparison
    """
    response = requests.get(f"{BASE_URL}/pools")
    response.raise_for_status()
    return response.json().get("data", [])


def get_bridges() -> dict:
    """
    Get bridge volumes and TVL.

    Returns:
    - Volume per bridge
    - Chains supported

    Use case: Cross-chain flow analysis
    """
    response = requests.get(f"{BASE_URL}/bridges")
    response.raise_for_status()
    return response.json()


# ============ HELPER FUNCTIONS ============

def get_top_protocols_by_tvl(limit: int = 20) -> list:
    """Get top protocols sorted by TVL."""
    protocols = get_all_protocols()
    sorted_protocols = sorted(protocols, key=lambda x: x.get("tvl", 0), reverse=True)
    return sorted_protocols[:limit]


def get_l2_comparison() -> list:
    """
    Get L2 chains comparison by TVL.

    Returns: List of L2s with TVL, sorted descending
    """
    L2_NAMES = [
        "Arbitrum", "Optimism", "Base", "zkSync Era", "Polygon zkEVM",
        "Linea", "Scroll", "Starknet", "Mantle", "Blast", "Manta", "Mode"
    ]
    chains = get_all_chains()
    l2s = [c for c in chains if c.get("name") in L2_NAMES]
    return sorted(l2s, key=lambda x: x.get("tvl", 0), reverse=True)


def get_l2_fees_comparison() -> list:
    """
    Get L2 fees comparison.

    Returns: List of L2s with fees data
    """
    L2_SLUGS = [
        "arbitrum", "optimism", "base", "zksync-era", "polygon-zkevm",
        "linea", "scroll", "starknet", "mantle", "blast"
    ]
    all_fees = get_all_fees()
    protocols = all_fees.get("protocols", [])
    l2_fees = [p for p in protocols if p.get("name", "").lower() in L2_SLUGS or
               p.get("slug", "").lower() in L2_SLUGS]
    return sorted(l2_fees, key=lambda x: x.get("total24h", 0), reverse=True)


if __name__ == "__main__":
    # Test
    print("=== Top 5 Protocols by TVL ===")
    for p in get_top_protocols_by_tvl(5):
        print(f"  {p['name']}: ${p['tvl']/1e9:.2f}B")

    print("\n=== L2 TVL Comparison ===")
    for l2 in get_l2_comparison()[:5]:
        print(f"  {l2['name']}: ${l2['tvl']/1e9:.2f}B")
