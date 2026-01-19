# -*- coding: utf-8 -*-
"""
Finnhub API Integration

USE FOR:
- Real-time stock quotes (fast)
- Company news with dates
- Insider trading data
- Analyst price targets
- Analyst recommendations history
- Earnings calendar
- IPO calendar

DO NOT USE FOR:
- Historical prices (use yfinance - more data)
- Financial statements (use yfinance)
- Fundamentals (use yfinance)
- SEC filings (use SEC EDGAR)
- Macro data (use FRED)

RATE LIMIT: 60 calls/min (free tier)
API KEY: Required (free at finnhub.io)

Set environment variable: FINNHUB_API_KEY
"""

import os
import requests
from typing import Optional, List
from datetime import datetime, timedelta

BASE_URL = "https://finnhub.io/api/v1"
API_KEY = os.getenv("FINNHUB_API_KEY")


def _get_params(**kwargs) -> dict:
    """Add API token to params."""
    if not API_KEY:
        raise ValueError("FINNHUB_API_KEY environment variable not set")
    kwargs["token"] = API_KEY
    return kwargs


def get_quote(symbol: str) -> dict:
    """
    Get real-time stock quote.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        - c: Current price
        - h: High of day
        - l: Low of day
        - o: Open price
        - pc: Previous close
        - t: Timestamp

    Use case: Real-time price check
    """
    response = requests.get(
        f"{BASE_URL}/quote",
        params=_get_params(symbol=symbol)
    )
    response.raise_for_status()
    data = response.json()

    return {
        "symbol": symbol,
        "current_price": data.get("c"),
        "high": data.get("h"),
        "low": data.get("l"),
        "open": data.get("o"),
        "previous_close": data.get("pc"),
        "change": data.get("c", 0) - data.get("pc", 0),
        "change_percent": ((data.get("c", 0) / data.get("pc", 1)) - 1) * 100 if data.get("pc") else 0,
        "timestamp": data.get("t"),
    }


def get_company_news(symbol: str, from_date: str = None, to_date: str = None) -> list:
    """
    Get company news.

    Args:
        symbol: Stock symbol
        from_date: Start date (YYYY-MM-DD), default: 7 days ago
        to_date: End date (YYYY-MM-DD), default: today

    Returns: List of news articles with headline, summary, url, datetime

    Use case: News analysis, sentiment tracking
    """
    if not from_date:
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")

    response = requests.get(
        f"{BASE_URL}/company-news",
        params=_get_params(symbol=symbol, **{"from": from_date, "to": to_date})
    )
    response.raise_for_status()

    return [
        {
            "headline": item.get("headline"),
            "summary": item.get("summary"),
            "source": item.get("source"),
            "url": item.get("url"),
            "datetime": datetime.fromtimestamp(item.get("datetime", 0)).isoformat(),
            "category": item.get("category"),
        }
        for item in response.json()
    ]


def get_market_news(category: str = "general") -> list:
    """
    Get general market news.

    Args:
        category: "general", "forex", "crypto", "merger"

    Returns: List of news articles

    Use case: Market overview, trending topics
    """
    response = requests.get(
        f"{BASE_URL}/news",
        params=_get_params(category=category)
    )
    response.raise_for_status()
    return response.json()


def get_insider_transactions(symbol: str) -> list:
    """
    Get insider trading data.

    Args:
        symbol: Stock symbol

    Returns: List of insider transactions with:
        - name: Insider name
        - share: Shares bought/sold
        - change: Transaction type
        - transactionPrice: Price per share
        - transactionDate: Date

    Use case: Insider sentiment, smart money tracking
    """
    response = requests.get(
        f"{BASE_URL}/stock/insider-transactions",
        params=_get_params(symbol=symbol)
    )
    response.raise_for_status()
    return response.json().get("data", [])


def get_price_target(symbol: str) -> dict:
    """
    Get analyst price targets.

    Args:
        symbol: Stock symbol

    Returns:
        - targetHigh: Highest target
        - targetLow: Lowest target
        - targetMean: Average target
        - targetMedian: Median target

    Use case: Analyst consensus, upside potential
    """
    response = requests.get(
        f"{BASE_URL}/stock/price-target",
        params=_get_params(symbol=symbol)
    )
    response.raise_for_status()
    return response.json()


def get_recommendations(symbol: str) -> list:
    """
    Get analyst recommendations history.

    Args:
        symbol: Stock symbol

    Returns: List of monthly recommendations:
        - buy, hold, sell, strongBuy, strongSell counts
        - period: Month

    Use case: Recommendation trends, sentiment shifts
    """
    response = requests.get(
        f"{BASE_URL}/stock/recommendation",
        params=_get_params(symbol=symbol)
    )
    response.raise_for_status()
    return response.json()


def get_recommendation_summary(symbol: str) -> dict:
    """
    Get latest recommendation summary.

    Returns: Current counts of buy/hold/sell ratings
    """
    recs = get_recommendations(symbol)
    if not recs:
        return {"error": "No recommendations available"}

    latest = recs[0]
    total = (latest.get("strongBuy", 0) + latest.get("buy", 0) +
             latest.get("hold", 0) + latest.get("sell", 0) +
             latest.get("strongSell", 0))

    return {
        "period": latest.get("period"),
        "strong_buy": latest.get("strongBuy", 0),
        "buy": latest.get("buy", 0),
        "hold": latest.get("hold", 0),
        "sell": latest.get("sell", 0),
        "strong_sell": latest.get("strongSell", 0),
        "total_analysts": total,
        "bullish_percent": ((latest.get("strongBuy", 0) + latest.get("buy", 0)) / total * 100) if total else 0,
    }


def get_earnings_calendar(from_date: str = None, to_date: str = None) -> list:
    """
    Get earnings calendar.

    Args:
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)

    Returns: List of upcoming earnings with:
        - symbol
        - date
        - epsEstimate
        - epsActual
        - revenueEstimate
        - revenueActual

    Use case: Earnings tracking, event calendar
    """
    if not from_date:
        from_date = datetime.now().strftime("%Y-%m-%d")
    if not to_date:
        to_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

    response = requests.get(
        f"{BASE_URL}/calendar/earnings",
        params=_get_params(**{"from": from_date, "to": to_date})
    )
    response.raise_for_status()
    return response.json().get("earningsCalendar", [])


def get_ipo_calendar(from_date: str = None, to_date: str = None) -> list:
    """
    Get IPO calendar.

    Args:
        from_date: Start date
        to_date: End date

    Returns: List of upcoming IPOs

    Use case: IPO tracking, new listings
    """
    if not from_date:
        from_date = datetime.now().strftime("%Y-%m-%d")
    if not to_date:
        to_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    response = requests.get(
        f"{BASE_URL}/calendar/ipo",
        params=_get_params(**{"from": from_date, "to": to_date})
    )
    response.raise_for_status()
    return response.json().get("ipoCalendar", [])


def get_company_profile(symbol: str) -> dict:
    """
    Get basic company profile.

    Returns: Company name, industry, market cap, logo, website
    """
    response = requests.get(
        f"{BASE_URL}/stock/profile2",
        params=_get_params(symbol=symbol)
    )
    response.raise_for_status()
    return response.json()


def get_peers(symbol: str) -> list:
    """
    Get company peers/competitors.

    Returns: List of peer stock symbols

    Use case: Competitor analysis, sector comparison
    """
    response = requests.get(
        f"{BASE_URL}/stock/peers",
        params=_get_params(symbol=symbol)
    )
    response.raise_for_status()
    return response.json()


# ============ HELPER FUNCTIONS ============

def get_stock_overview(symbol: str) -> dict:
    """
    Get comprehensive stock overview.

    Combines quote, price target, and recommendations.
    """
    return {
        "quote": get_quote(symbol),
        "price_target": get_price_target(symbol),
        "recommendations": get_recommendation_summary(symbol),
        "peers": get_peers(symbol),
    }


def get_insider_sentiment(symbol: str) -> dict:
    """
    Analyze insider trading sentiment.

    Returns:
        - total_buys: Number of buy transactions
        - total_sells: Number of sell transactions
        - net_sentiment: "bullish", "bearish", or "neutral"
    """
    transactions = get_insider_transactions(symbol)

    buys = sum(1 for t in transactions if t.get("change") == "P")
    sells = sum(1 for t in transactions if t.get("change") == "S")

    if buys > sells * 1.5:
        sentiment = "bullish"
    elif sells > buys * 1.5:
        sentiment = "bearish"
    else:
        sentiment = "neutral"

    return {
        "total_buys": buys,
        "total_sells": sells,
        "net_sentiment": sentiment,
        "recent_transactions": transactions[:10],  # Last 10
    }


if __name__ == "__main__":
    if not API_KEY:
        print("FINNHUB_API_KEY not set")
        print("Get free key at: https://finnhub.io/")
    else:
        print("=== AAPL Quote ===")
        quote = get_quote("AAPL")
        print(f"Price: ${quote['current_price']}")
        print(f"Change: {quote['change_percent']:+.2f}%")

        print("\n=== Recent News ===")
        news = get_company_news("AAPL")
        for n in news[:3]:
            print(f"  - {n['headline'][:60]}...")
