# -*- coding: utf-8 -*-
"""
BlockLens API Integration — On-Chain Analytics for Bitcoin

USE FOR:
- Bitcoin price history (OHLCV)
- LTH/STH supply distribution
- MVRV ratio (Long-Term and Short-Term holders)
- Realized Price and Realized Cap
- SOPR (Spent Output Profit Ratio)
- UTXO age cohort analysis
- Market cycle indicators

DO NOT USE FOR:
- Altcoin prices (use CoinGecko)
- DeFi TVL (use DefiLlama)
- Ethereum on-chain (use Etherscan/Dune)
- L2 data (use L2Beat)
- Real-time trading data (use exchange APIs)

RATE LIMIT: 100,000 calls/day (Enterprise tier)
API KEY: Required (Enterprise subscription)
BASE URL: https://api.blocklens.co
"""

import requests
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import time

BASE_URL = "https://api.blocklens.co"
API_KEY = "blk_EeFHrH7Y7voJoZVrrTIn4Shk0y3JarjxGnFT8tuztBk"

# Rate limiting
_last_request = 0
_min_interval = 0.1  # 100ms between requests (safe for 100k/day)


def _rate_limit():
    """Simple rate limiter."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request = time.time()


def _get_headers() -> dict:
    """Get authorization headers."""
    return {"Authorization": f"Bearer {API_KEY}"}


def _make_request(endpoint: str, params: Optional[dict] = None) -> dict:
    """Make authenticated API request."""
    _rate_limit()
    url = f"{BASE_URL}{endpoint}"
    response = requests.get(url, headers=_get_headers(), params=params)
    response.raise_for_status()
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"API error: {data.get('message')}")
    return data


# ============ PRICE DATA ============

def get_prices(
    symbol: str = "BTC",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """
    Get historical OHLCV price data.

    Args:
        symbol: Cryptocurrency symbol (default: BTC)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Number of records (max 10000)

    Returns: List of price records with:
        - date, symbol, price, open, high, low, close
        - volume, market_cap

    Use case: Price charts, volatility analysis, backtesting
    """
    params = {"symbol": symbol, "limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    result = _make_request("/v1/prices", params)
    return result["data"]


# ============ HOLDER ANALYTICS ============

def get_holder_supply(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """
    Get LTH (Long-Term Holder) and STH (Short-Term Holder) supply.

    LTH = coins held > 155 days
    STH = coins held <= 155 days

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Number of records (max 10000)

    Returns: List of records with:
        - date_processed
        - lth_supply: BTC held by long-term holders
        - sth_supply: BTC held by short-term holders

    Use case:
        - Rising LTH supply = accumulation, holder conviction
        - Rising STH supply = distribution, potential market top
    """
    params = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    result = _make_request("/v1/holder/supply", params)
    return result["data"]


def get_holder_valuation(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """
    Get holder valuation metrics: Realized Price and MVRV.

    MVRV = Market Value / Realized Value
    - MVRV > 1: holders in profit (on average)
    - MVRV < 1: holders at loss (on average)
    - LTH MVRV > 3.5: historically overheated
    - STH MVRV < 1: short-term holders underwater

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Number of records (max 10000)

    Returns: List of records with:
        - date_processed
        - lth_realized_cap, sth_realized_cap
        - lth_realized_price, sth_realized_price
        - lth_unrealized_pl, sth_unrealized_pl
        - lth_mvrv, sth_mvrv

    Use case: Market cycle analysis, valuation assessment
    """
    params = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    result = _make_request("/v1/holder/valuation", params)
    return result["data"]


def get_holder_profit(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
) -> List[dict]:
    """
    Get holder profitability metrics: SOPR.

    SOPR = Spent Output Profit Ratio
    - SOPR > 1: coins sold at profit (bull market)
    - SOPR < 1: coins sold at loss (capitulation)
    - SOPR = 1: break-even (often support/resistance)

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        limit: Number of records (max 10000)

    Returns: List of records with:
        - date_processed
        - lth_realized_pl, sth_realized_pl (daily P/L)
        - lth_sopr, sth_sopr

    Use case: Market sentiment, capitulation detection
    """
    params = {"limit": limit}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    result = _make_request("/v1/holder/profit", params)
    return result["data"]


# ============ UTXO ANALYTICS ============

def get_utxo_history(
    date_processed: Optional[str] = None,
    cohort_start: Optional[str] = None,
    cohort_end: Optional[str] = None,
    limit: int = 1000
) -> List[dict]:
    """
    Get UTXO age cohort distribution.

    Shows how BTC supply is distributed by coin age.
    Useful for tracking dormant supply and "old hands" behavior.

    Args:
        date_processed: Specific date to analyze (YYYY-MM-DD)
        cohort_start: Filter cohorts starting from this date
        cohort_end: Filter cohorts ending at this date
        limit: Number of records (max 50000)

    Returns: List of records with:
        - date_processed
        - cohort_date: when coins were last moved
        - token_amount: BTC in this cohort
        - usd_value: USD value of cohort

    Use case: Dormancy analysis, whale tracking
    """
    params = {"limit": limit}
    if date_processed:
        params["date_processed"] = date_processed
    if cohort_start:
        params["cohort_start"] = cohort_start
    if cohort_end:
        params["cohort_end"] = cohort_end

    result = _make_request("/v1/utxo/history", params)
    return result["data"]


# ============ AGGREGATED METRICS ============

def get_latest_metrics() -> dict:
    """
    Get latest snapshot of all metrics in one call.

    Returns dict with:
        - prices: latest BTC OHLCV
        - supply: latest LTH/STH supply
        - valuation: latest MVRV, realized price
        - profit: latest SOPR

    Use case: Dashboard, quick market check
    """
    result = _make_request("/v1/metrics/latest")
    return result["data"]


# ============ HELPER FUNCTIONS ============

def get_market_cycle_indicators() -> dict:
    """
    Get key market cycle indicators.

    Returns comprehensive analysis:
        - Current price and trend
        - LTH/STH supply ratio
        - MVRV for both cohorts
        - SOPR signals
        - Market phase assessment

    Use case: Market cycle analysis, investment timing
    """
    latest = get_latest_metrics()

    price = float(latest["prices"]["price"])
    lth_supply = float(latest["supply"]["lth_supply"])
    sth_supply = float(latest["supply"]["sth_supply"])
    lth_mvrv = float(latest["valuation"]["lth_mvrv"])
    sth_mvrv = float(latest["valuation"]["sth_mvrv"])
    lth_sopr = float(latest["profit"]["lth_sopr"])
    sth_sopr = float(latest["profit"]["sth_sopr"])
    lth_realized_price = float(latest["valuation"]["lth_realized_price"])
    sth_realized_price = float(latest["valuation"]["sth_realized_price"])

    # Supply ratio
    total_supply = lth_supply + sth_supply
    lth_ratio = lth_supply / total_supply * 100

    # Market phase assessment
    if lth_mvrv > 3.5 and sth_mvrv > 1.2:
        phase = "euphoria"
        signal = "extreme_caution"
    elif lth_mvrv > 2.5 and sth_mvrv > 1:
        phase = "bull_market"
        signal = "caution"
    elif lth_mvrv > 1.5 and sth_mvrv < 1:
        phase = "distribution"
        signal = "neutral"
    elif lth_mvrv < 1.5 and sth_mvrv < 0.8:
        phase = "capitulation"
        signal = "accumulation_zone"
    elif lth_mvrv > 1 and sth_mvrv > 0.9:
        phase = "recovery"
        signal = "bullish"
    else:
        phase = "accumulation"
        signal = "bullish"

    return {
        "date": latest["prices"]["date"],
        "price": {
            "current": price,
            "lth_realized": lth_realized_price,
            "sth_realized": sth_realized_price,
            "vs_lth_realized": (price / lth_realized_price - 1) * 100,
            "vs_sth_realized": (price / sth_realized_price - 1) * 100
        },
        "supply": {
            "lth_btc": lth_supply,
            "sth_btc": sth_supply,
            "lth_ratio_pct": lth_ratio,
            "sth_ratio_pct": 100 - lth_ratio
        },
        "mvrv": {
            "lth": lth_mvrv,
            "sth": sth_mvrv,
            "lth_signal": "overheated" if lth_mvrv > 3.5 else "elevated" if lth_mvrv > 2.5 else "normal" if lth_mvrv > 1.5 else "undervalued",
            "sth_signal": "profit" if sth_mvrv > 1 else "near_breakeven" if sth_mvrv > 0.9 else "loss"
        },
        "sopr": {
            "lth": lth_sopr,
            "sth": sth_sopr,
            "lth_signal": "profit_taking" if lth_sopr > 1.2 else "selling_profit" if lth_sopr > 1 else "capitulation",
            "sth_signal": "profit_taking" if sth_sopr > 1 else "loss_taking" if sth_sopr < 1 else "breakeven"
        },
        "market_phase": phase,
        "signal": signal
    }


def get_historical_mvrv(days: int = 365) -> List[dict]:
    """
    Get historical MVRV data for charting.

    Args:
        days: Number of days of history

    Returns: List of records with date, lth_mvrv, sth_mvrv, price
    """
    # Get valuation data
    valuation = get_holder_valuation(limit=days)
    prices = get_prices(limit=days)

    # Create price lookup
    price_map = {p["date"]: float(p["price"]) for p in prices}

    result = []
    for v in valuation:
        date = v["date_processed"]
        result.append({
            "date": date,
            "lth_mvrv": float(v["lth_mvrv"]),
            "sth_mvrv": float(v["sth_mvrv"]),
            "price": price_map.get(date)
        })

    return result


def check_api_health() -> dict:
    """Check API health status."""
    _rate_limit()
    response = requests.get(f"{BASE_URL}/health", headers=_get_headers())
    return response.json()


# ============ CLI TEST ============

if __name__ == "__main__":
    print("=== BlockLens API Test ===\n")

    try:
        # Health check
        health = check_api_health()
        print(f"API Status: {health.get('status', 'unknown')}")

        # Market cycle indicators
        print("\n=== Market Cycle Indicators ===")
        indicators = get_market_cycle_indicators()

        print(f"Date: {indicators['date']}")
        print(f"BTC Price: ${indicators['price']['current']:,.0f}")
        print(f"  vs LTH Realized: {indicators['price']['vs_lth_realized']:+.1f}%")
        print(f"  vs STH Realized: {indicators['price']['vs_sth_realized']:+.1f}%")

        print(f"\nSupply Distribution:")
        print(f"  LTH: {indicators['supply']['lth_ratio_pct']:.1f}%")
        print(f"  STH: {indicators['supply']['sth_ratio_pct']:.1f}%")

        print(f"\nMVRV:")
        print(f"  LTH: {indicators['mvrv']['lth']:.2f} ({indicators['mvrv']['lth_signal']})")
        print(f"  STH: {indicators['mvrv']['sth']:.2f} ({indicators['mvrv']['sth_signal']})")

        print(f"\nSOPR:")
        print(f"  LTH: {indicators['sopr']['lth']:.2f} ({indicators['sopr']['lth_signal']})")
        print(f"  STH: {indicators['sopr']['sth']:.2f} ({indicators['sopr']['sth_signal']})")

        print(f"\n{'='*40}")
        print(f"Market Phase: {indicators['market_phase'].upper()}")
        print(f"Signal: {indicators['signal'].upper()}")

    except Exception as e:
        print(f"Error: {e}")
