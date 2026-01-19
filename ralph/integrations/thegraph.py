# -*- coding: utf-8 -*-
"""
The Graph API Integration

USE FOR:
- Protocol-specific on-chain data (Uniswap, Aave, etc.)
- DeFi analytics (pools, swaps, loans)
- Historical on-chain queries
- Custom GraphQL queries on indexed data
- Token holder analysis
- Liquidity data

DO NOT USE FOR:
- Aggregated cross-protocol data (use DefiLlama)
- Token prices (use CoinGecko)
- L2 TVL/security (use L2Beat)
- Wallet balances (use Etherscan)

RATE LIMIT: Fair use on hosted service
API KEY: Not required for hosted subgraphs

NOTE: The Graph indexes specific protocols. Each protocol has its own subgraph.
"""

import requests
from typing import Optional

# Popular subgraph URLs
SUBGRAPHS = {
    # DEXes
    "uniswap_v3_ethereum": "https://api.thegraph.com/subgraphs/name/uniswap/uniswap-v3",
    "uniswap_v3_arbitrum": "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-arbitrum",
    "uniswap_v3_optimism": "https://api.thegraph.com/subgraphs/name/ianlapham/optimism-post-regenesis",
    "uniswap_v3_base": "https://api.thegraph.com/subgraphs/name/ianlapham/uniswap-v3-base",
    "sushiswap_ethereum": "https://api.thegraph.com/subgraphs/name/sushi-v3/v3-ethereum",

    # Lending
    "aave_v3_ethereum": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3",
    "aave_v3_arbitrum": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-arbitrum",
    "aave_v3_optimism": "https://api.thegraph.com/subgraphs/name/aave/protocol-v3-optimism",
    "compound_v3": "https://api.thegraph.com/subgraphs/name/messari/compound-v3-ethereum",

    # Bridges
    "arbitrum_bridge": "https://api.thegraph.com/subgraphs/name/arbitrum/arbitrum-bridge",

    # Staking
    "lido": "https://api.thegraph.com/subgraphs/name/lidofinance/lido",

    # Other
    "ens": "https://api.thegraph.com/subgraphs/name/ensdomains/ens",
}


def query_subgraph(subgraph_url: str, query: str, variables: dict = None) -> dict:
    """
    Execute GraphQL query on a subgraph.

    Args:
        subgraph_url: Full subgraph URL
        query: GraphQL query string
        variables: Optional variables for query

    Returns: Query results

    Use case: Any protocol-specific data
    """
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(subgraph_url, json=payload)
    response.raise_for_status()

    data = response.json()
    if "errors" in data:
        raise Exception(f"GraphQL error: {data['errors']}")

    return data.get("data", {})


# ============ UNISWAP QUERIES ============

def get_uniswap_top_pools(chain: str = "ethereum", limit: int = 10) -> list:
    """
    Get top Uniswap V3 pools by TVL.

    Args:
        chain: ethereum, arbitrum, optimism, base
        limit: Number of pools

    Returns: List of pools with TVL, volume, fees

    Use case: DEX liquidity analysis
    """
    subgraph_key = f"uniswap_v3_{chain}"
    subgraph = SUBGRAPHS.get(subgraph_key)
    if not subgraph:
        raise ValueError(f"Unknown chain: {chain}")

    query = """
    query TopPools($limit: Int!) {
        pools(first: $limit, orderBy: totalValueLockedUSD, orderDirection: desc) {
            id
            token0 { symbol, name }
            token1 { symbol, name }
            feeTier
            totalValueLockedUSD
            volumeUSD
            txCount
        }
    }
    """
    data = query_subgraph(subgraph, query, {"limit": limit})
    return data.get("pools", [])


def get_uniswap_pool_stats(pool_id: str, chain: str = "ethereum") -> dict:
    """
    Get detailed stats for a specific pool.

    Args:
        pool_id: Pool contract address
        chain: Chain name

    Returns: Pool details with current and historical data
    """
    subgraph = SUBGRAPHS.get(f"uniswap_v3_{chain}")

    query = """
    query PoolStats($poolId: String!) {
        pool(id: $poolId) {
            id
            token0 { symbol, name, decimals }
            token1 { symbol, name, decimals }
            feeTier
            liquidity
            sqrtPrice
            tick
            totalValueLockedUSD
            totalValueLockedToken0
            totalValueLockedToken1
            volumeUSD
            feesUSD
            txCount
            poolDayData(first: 30, orderBy: date, orderDirection: desc) {
                date
                volumeUSD
                tvlUSD
                feesUSD
            }
        }
    }
    """
    data = query_subgraph(subgraph, query, {"poolId": pool_id.lower()})
    return data.get("pool", {})


def get_uniswap_recent_swaps(chain: str = "ethereum", limit: int = 20) -> list:
    """
    Get recent swaps on Uniswap.

    Use case: DEX activity monitoring, whale watching
    """
    subgraph = SUBGRAPHS.get(f"uniswap_v3_{chain}")

    query = """
    query RecentSwaps($limit: Int!) {
        swaps(first: $limit, orderBy: timestamp, orderDirection: desc) {
            id
            timestamp
            pool { token0 { symbol } token1 { symbol } }
            sender
            recipient
            amount0
            amount1
            amountUSD
        }
    }
    """
    data = query_subgraph(subgraph, query, {"limit": limit})
    return data.get("swaps", [])


# ============ AAVE QUERIES ============

def get_aave_markets(chain: str = "ethereum") -> list:
    """
    Get Aave V3 lending markets.

    Returns: List of markets with:
    - Total supply and borrow
    - APY rates
    - Utilization

    Use case: Lending protocol analysis
    """
    subgraph = SUBGRAPHS.get(f"aave_v3_{chain}")
    if not subgraph:
        raise ValueError(f"No Aave subgraph for: {chain}")

    query = """
    {
        markets(first: 20, orderBy: totalValueLockedUSD, orderDirection: desc) {
            id
            name
            inputToken { symbol, name }
            totalValueLockedUSD
            totalBorrowBalanceUSD
            rates {
                rate
                side
            }
        }
    }
    """
    data = query_subgraph(subgraph, query)
    return data.get("markets", [])


def get_aave_user_positions(user_address: str, chain: str = "ethereum") -> list:
    """
    Get user's Aave positions.

    Args:
        user_address: User wallet address
        chain: Chain name

    Returns: User's supply and borrow positions
    """
    subgraph = SUBGRAPHS.get(f"aave_v3_{chain}")

    query = """
    query UserPositions($user: String!) {
        account(id: $user) {
            id
            positions {
                market { name, inputToken { symbol } }
                balance
                side
            }
        }
    }
    """
    data = query_subgraph(subgraph, query, {"user": user_address.lower()})
    return data.get("account", {}).get("positions", [])


# ============ LIDO QUERIES ============

def get_lido_stats() -> dict:
    """
    Get Lido staking statistics.

    Returns:
    - Total staked ETH
    - Number of stakers
    - Protocol stats

    Use case: ETH staking analysis
    """
    query = """
    {
        lidoTotals(id: "") {
            totalPooledEther
            totalShares
        }
        lidoStats(id: "lido") {
            uniqueHolders
            uniqueAnytimeHolders
        }
    }
    """
    return query_subgraph(SUBGRAPHS["lido"], query)


# ============ ENS QUERIES ============

def search_ens_domains(search_term: str, limit: int = 10) -> list:
    """
    Search ENS domains.

    Use case: ENS analysis, domain lookup
    """
    query = """
    query SearchDomains($search: String!, $limit: Int!) {
        domains(first: $limit, where: {name_contains: $search}) {
            id
            name
            owner { id }
            registrant { id }
            expiryDate
        }
    }
    """
    data = query_subgraph(SUBGRAPHS["ens"], query, {"search": search_term, "limit": limit})
    return data.get("domains", [])


# ============ HELPER FUNCTIONS ============

def get_defi_overview(chain: str = "ethereum") -> dict:
    """
    Get DeFi overview for a chain from The Graph.

    Combines Uniswap + Aave data.
    """
    result = {
        "chain": chain,
        "dex": {},
        "lending": {}
    }

    try:
        pools = get_uniswap_top_pools(chain, 5)
        result["dex"] = {
            "top_pools": [
                {"pair": f"{p['token0']['symbol']}/{p['token1']['symbol']}",
                 "tvl": float(p["totalValueLockedUSD"]),
                 "volume": float(p["volumeUSD"])}
                for p in pools
            ],
            "total_tvl": sum(float(p["totalValueLockedUSD"]) for p in pools)
        }
    except Exception as e:
        result["dex"]["error"] = str(e)

    try:
        markets = get_aave_markets(chain)
        result["lending"] = {
            "top_markets": [
                {"asset": m["inputToken"]["symbol"],
                 "tvl": float(m["totalValueLockedUSD"]),
                 "borrowed": float(m["totalBorrowBalanceUSD"])}
                for m in markets[:5]
            ],
            "total_tvl": sum(float(m["totalValueLockedUSD"]) for m in markets)
        }
    except Exception as e:
        result["lending"]["error"] = str(e)

    return result


if __name__ == "__main__":
    print("=== Uniswap Top Pools (Ethereum) ===")
    pools = get_uniswap_top_pools("ethereum", 5)
    for p in pools:
        pair = f"{p['token0']['symbol']}/{p['token1']['symbol']}"
        tvl = float(p["totalValueLockedUSD"]) / 1e6
        print(f"  {pair}: ${tvl:.1f}M TVL")

    print("\n=== Aave Markets (Ethereum) ===")
    try:
        markets = get_aave_markets("ethereum")
        for m in markets[:5]:
            tvl = float(m["totalValueLockedUSD"]) / 1e6
            print(f"  {m['inputToken']['symbol']}: ${tvl:.1f}M")
    except Exception as e:
        print(f"  Error: {e}")
