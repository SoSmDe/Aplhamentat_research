# -*- coding: utf-8 -*-
"""
Dune Analytics API Integration

USE FOR:
- Custom on-chain SQL queries
- Historical blockchain data
- Complex analytics not available elsewhere
- L2 sequencer revenue analysis
- Whale tracking and wallet analysis
- Custom metrics and KPIs

DO NOT USE FOR:
- Real-time data (has ~1 hour delay)
- Simple price data (use CoinGecko)
- Protocol TVL (use DefiLlama - faster)
- Quick lookups (API is slow)

RATE LIMIT: 2,500 credits/month (free tier)
- Execute query: 10 credits
- Get results: 1 credit
- Cancel: 1 credit

API KEY: Required (set DUNE_API_KEY env var)

NOTE: Dune queries can take 10-60 seconds to execute
"""

import os
import time
import requests
from typing import Optional

BASE_URL = "https://api.dune.com/api/v1"
API_KEY = os.getenv("DUNE_API_KEY")


def _get_headers() -> dict:
    """Get API headers."""
    if not API_KEY:
        raise ValueError("DUNE_API_KEY environment variable not set")
    return {"X-Dune-API-Key": API_KEY}


def execute_query(query_id: int, parameters: dict = None) -> str:
    """
    Start query execution.

    Args:
        query_id: Dune query ID (from URL)
        parameters: Optional query parameters

    Returns: execution_id

    Cost: 10 credits
    """
    url = f"{BASE_URL}/query/{query_id}/execute"
    payload = {}
    if parameters:
        payload["query_parameters"] = parameters

    response = requests.post(url, headers=_get_headers(), json=payload)
    response.raise_for_status()
    return response.json()["execution_id"]


def get_execution_status(execution_id: str) -> dict:
    """
    Check execution status.

    Returns:
    - state: QUERY_STATE_PENDING, QUERY_STATE_EXECUTING,
             QUERY_STATE_COMPLETED, QUERY_STATE_FAILED
    - queue_position: position in queue

    Cost: 1 credit
    """
    url = f"{BASE_URL}/execution/{execution_id}/status"
    response = requests.get(url, headers=_get_headers())
    response.raise_for_status()
    return response.json()


def get_execution_results(execution_id: str) -> dict:
    """
    Get query results.

    Returns:
    - result.rows: List of result rows
    - result.metadata: Column info

    Cost: 1 credit
    """
    url = f"{BASE_URL}/execution/{execution_id}/results"
    response = requests.get(url, headers=_get_headers())
    response.raise_for_status()
    return response.json()


def run_query(query_id: int, parameters: dict = None,
              timeout: int = 300, poll_interval: int = 5) -> list:
    """
    Execute query and wait for results.

    Args:
        query_id: Dune query ID
        parameters: Optional query parameters
        timeout: Max wait time in seconds
        poll_interval: Time between status checks

    Returns: List of result rows

    Total cost: ~12 credits per execution
    """
    # Start execution
    execution_id = execute_query(query_id, parameters)

    # Poll for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = get_execution_status(execution_id)
        state = status.get("state")

        if state == "QUERY_STATE_COMPLETED":
            results = get_execution_results(execution_id)
            return results.get("result", {}).get("rows", [])

        elif state == "QUERY_STATE_FAILED":
            raise Exception(f"Query failed: {status}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Query {query_id} timed out after {timeout}s")


def get_latest_results(query_id: int) -> list:
    """
    Get cached results from last execution (no new execution).

    Args:
        query_id: Dune query ID

    Returns: Cached result rows

    Cost: 1 credit
    Use case: Get pre-computed dashboard data
    """
    url = f"{BASE_URL}/query/{query_id}/results"
    response = requests.get(url, headers=_get_headers())
    response.raise_for_status()
    return response.json().get("result", {}).get("rows", [])


# ============ USEFUL QUERY IDS ============

# NOTE: These are example IDs - replace with actual working queries
USEFUL_QUERIES = {
    # L2 Economics
    "l2_daily_fees": 3237721,              # L2 fees comparison
    "arbitrum_sequencer_revenue": 2741652,  # Arbitrum revenue
    "optimism_sequencer_revenue": 2741653,  # Optimism revenue
    "base_economics": 3456789,              # Base metrics

    # ETH Analysis
    "eth_staking_ratio": 2340697,           # ETH staked %
    "eth_supply_dynamics": 2399358,         # Burn vs issuance
    "eth_whale_movements": 1234567,         # Large transfers

    # DeFi
    "dex_volume_24h": 2438940,              # DEX volumes
    "defi_tvl_by_protocol": 2567890,        # TVL breakdown

    # NFT
    "nft_marketplace_volume": 3141592,      # NFT sales

    # Stablecoins
    "stablecoin_flows": 2718281,            # USDT/USDC flows
}


# ============ HELPER FUNCTIONS ============

def get_l2_fees_comparison() -> list:
    """
    Get L2 fees comparison from Dune.

    Returns: Daily fees for major L2s

    Use case: L2 revenue analysis
    """
    return run_query(USEFUL_QUERIES["l2_daily_fees"])


def get_eth_staking_stats() -> list:
    """
    Get ETH staking statistics.

    Returns: Staking ratio, validator count, etc.
    """
    return run_query(USEFUL_QUERIES["eth_staking_ratio"])


def get_dex_volumes() -> list:
    """
    Get 24h DEX volumes.

    Returns: Volume by DEX
    """
    return run_query(USEFUL_QUERIES["dex_volume_24h"])


def check_credits() -> dict:
    """
    Check remaining API credits.

    Returns: Credits info
    """
    # Note: Dune doesn't have a direct endpoint for this
    # Track credits manually or check dashboard
    return {
        "note": "Check credits at https://dune.com/settings/api",
        "free_tier_limit": 2500,
        "cost_per_execution": 12  # approx
    }


# ============ CUSTOM QUERY BUILDER ============

def build_l2_revenue_query(l2_name: str, days: int = 30) -> str:
    """
    Build SQL query for L2 revenue analysis.

    NOTE: This returns the SQL string - you'll need to create
    a query on Dune dashboard and use its ID.
    """
    return f"""
    SELECT
        date_trunc('day', block_time) as day,
        SUM(gas_used * gas_price / 1e18) as revenue_eth,
        COUNT(*) as tx_count
    FROM {l2_name}.transactions
    WHERE block_time >= NOW() - INTERVAL '{days} days'
    GROUP BY 1
    ORDER BY 1 DESC
    """


if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  DUNE_API_KEY not set")
        print("Set it with: export DUNE_API_KEY='your-key'")
        print("\nGet your API key at: https://dune.com/settings/api")
    else:
        print("✅ DUNE_API_KEY is set")
        print(f"\nUseful queries available:")
        for name, qid in USEFUL_QUERIES.items():
            print(f"  {name}: {qid}")
