# -*- coding: utf-8 -*-
"""
L2Beat API Integration

USE FOR:
- L2 TVL (more accurate than DefiLlama for L2s)
- L2 security/risk assessment (Stage 0/1/2)
- L2 technology comparison (Optimistic vs ZK)
- Network activity (TPS, transactions)
- L1 settlement costs
- Decentralization metrics

DO NOT USE FOR:
- DeFi protocols inside L2s (use DefiLlama/TheGraph)
- Token prices (use CoinGecko)
- Wallet balances (use Etherscan)
- General DeFi TVL (use DefiLlama)

RATE LIMIT: Fair use
API KEY: Not required

NOTE: L2Beat is the authoritative source for L2 security analysis
"""

import requests
from typing import Optional

BASE_URL = "https://l2beat.com/api"


def get_tvl() -> dict:
    """
    Get TVL for all L2 projects.

    Returns:
    - TVL per project with history
    - Breakdown by token type (canonical, external, native)

    Use case: L2 market share, TVL comparison
    """
    response = requests.get(f"{BASE_URL}/tvl.json")
    response.raise_for_status()
    return response.json()


def get_activity() -> dict:
    """
    Get network activity for all L2s.

    Returns:
    - TPS (transactions per second)
    - Daily transaction count
    - User activity metrics

    Use case: L2 adoption analysis, network usage comparison
    """
    response = requests.get(f"{BASE_URL}/activity.json")
    response.raise_for_status()
    return response.json()


def get_scaling_summary() -> dict:
    """
    Get scaling summary with risk assessment.

    Returns per L2:
    - Stage (0, 1, 2)
    - Risk scores by category
    - Technology type
    - Data availability method

    Use case: L2 security analysis, risk comparison

    RISK CATEGORIES:
    - stateValidation: ZK proofs | Fraud proofs | None
    - dataAvailability: On-chain | DAC | External
    - exitWindow: 7 days | None | Instant
    - sequencerFailure: Self-propose | Whitelisted | Centralized
    - proposerFailure: Self-propose | Whitelisted | Centralized
    """
    response = requests.get(f"{BASE_URL}/scaling/summary")
    response.raise_for_status()
    return response.json()


def get_costs() -> dict:
    """
    Get L1 settlement costs for L2s.

    Returns:
    - Daily L1 costs (gas spent on Ethereum)
    - Cost breakdown by type

    Use case: L2 profitability analysis (revenue - costs)
    """
    response = requests.get(f"{BASE_URL}/costs")
    response.raise_for_status()
    return response.json()


# ============ HELPER FUNCTIONS ============

def get_l2_risk_scores() -> list:
    """
    Get L2s with their risk scores and stages.

    Returns: List of L2s sorted by stage (best first)

    STAGES:
    - Stage 2: Fully decentralized (no training wheels)
    - Stage 1: Limited training wheels
    - Stage 0: Full training wheels (most centralized)
    """
    summary = get_scaling_summary()
    projects = summary.get("projects", [])

    result = []
    for p in projects:
        result.append({
            "name": p.get("name"),
            "slug": p.get("slug"),
            "stage": p.get("stage", "Stage 0"),
            "category": p.get("category"),  # Optimistic Rollup, ZK Rollup, etc.
            "risks": p.get("risks", {}),
            "tvl": p.get("tvl", {}).get("value", 0)
        })

    # Sort by stage (Stage 2 first)
    stage_order = {"Stage 2": 0, "Stage 1": 1, "Stage 0": 2}
    result.sort(key=lambda x: stage_order.get(x["stage"], 3))

    return result


def get_l2_by_technology() -> dict:
    """
    Group L2s by technology type.

    Returns: Dict with keys:
    - "Optimistic Rollup": [arbitrum, optimism, base, ...]
    - "ZK Rollup": [zksync, starknet, scroll, ...]
    - "Validium": [...]
    """
    summary = get_scaling_summary()
    projects = summary.get("projects", [])

    by_tech = {}
    for p in projects:
        tech = p.get("category", "Unknown")
        if tech not in by_tech:
            by_tech[tech] = []
        by_tech[tech].append({
            "name": p.get("name"),
            "stage": p.get("stage"),
            "tvl": p.get("tvl", {}).get("value", 0)
        })

    return by_tech


def get_l2_tvl_ranking() -> list:
    """
    Get L2s ranked by TVL.

    Returns: List of L2s with TVL, sorted descending
    """
    tvl_data = get_tvl()
    projects = tvl_data.get("projects", {})

    result = []
    for slug, data in projects.items():
        tvl = data.get("tvl", {}).get("value", 0)
        if isinstance(tvl, dict):
            tvl = tvl.get("usd", 0)
        result.append({
            "slug": slug,
            "tvl": tvl
        })

    return sorted(result, key=lambda x: x["tvl"], reverse=True)


def get_l2_activity_ranking() -> list:
    """
    Get L2s ranked by transaction activity.

    Returns: List of L2s with TPS and tx count
    """
    activity = get_activity()
    projects = activity.get("projects", {})

    result = []
    for slug, data in projects.items():
        result.append({
            "slug": slug,
            "tps": data.get("tps", 0),
            "daily_txs": data.get("dailyTxCount", 0)
        })

    return sorted(result, key=lambda x: x["daily_txs"], reverse=True)


def analyze_l2_security(l2_name: str) -> dict:
    """
    Get detailed security analysis for specific L2.

    Args:
        l2_name: L2 name or slug (e.g., "arbitrum", "optimism")

    Returns:
    - Stage classification
    - Risk breakdown
    - Technology details
    - Recommendations
    """
    summary = get_scaling_summary()
    projects = summary.get("projects", [])

    # Find L2
    l2 = None
    for p in projects:
        if p.get("slug", "").lower() == l2_name.lower() or \
           p.get("name", "").lower() == l2_name.lower():
            l2 = p
            break

    if not l2:
        return {"error": f"L2 not found: {l2_name}"}

    risks = l2.get("risks", {})

    return {
        "name": l2.get("name"),
        "stage": l2.get("stage"),
        "category": l2.get("category"),
        "risks": {
            "state_validation": risks.get("stateValidation", {}).get("value", "Unknown"),
            "data_availability": risks.get("dataAvailability", {}).get("value", "Unknown"),
            "exit_window": risks.get("exitWindow", {}).get("value", "Unknown"),
            "sequencer_failure": risks.get("sequencerFailure", {}).get("value", "Unknown"),
            "proposer_failure": risks.get("proposerFailure", {}).get("value", "Unknown"),
        },
        "analysis": _generate_risk_analysis(l2)
    }


def _generate_risk_analysis(l2: dict) -> str:
    """Generate human-readable risk analysis."""
    stage = l2.get("stage", "Stage 0")
    category = l2.get("category", "Unknown")

    if stage == "Stage 2":
        return f"{l2['name']} is a {category} at Stage 2 - fully decentralized with no training wheels. Highest security tier."
    elif stage == "Stage 1":
        return f"{l2['name']} is a {category} at Stage 1 - has limited training wheels. Security council can intervene in emergencies."
    else:
        return f"{l2['name']} is a {category} at Stage 0 - has full training wheels. More centralized, team can upgrade contracts."


if __name__ == "__main__":
    print("=== L2 Risk Scores ===")
    for l2 in get_l2_risk_scores()[:5]:
        print(f"  {l2['name']}: {l2['stage']} ({l2['category']})")

    print("\n=== L2 by Technology ===")
    by_tech = get_l2_by_technology()
    for tech, projects in by_tech.items():
        print(f"\n{tech}:")
        for p in projects[:3]:
            print(f"  - {p['name']} ({p['stage']})")
