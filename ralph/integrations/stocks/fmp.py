# -*- coding: utf-8 -*-
"""
Financial Modeling Prep (FMP) API Integration

USE FOR:
- DCF valuation (ready-made model)
- Financial ratios (all ratios at once)
- Stock screener (filter by criteria)
- SEC filings links
- Company profile
- Real-time quotes

DO NOT USE FOR:
- Historical prices (use yfinance - more data, free)
- News (use Finnhub)
- Insider trading (use Finnhub or SEC EDGAR)
- Macro data (use FRED)
- Technical indicators (use Alpha Vantage)

RATE LIMIT: 250 calls/day (free tier)
API KEY: Required (free at financialmodelingprep.com)

Set environment variable: FMP_API_KEY
"""

import os
import requests
from typing import Optional, List

BASE_URL = "https://financialmodelingprep.com/api/v3"
API_KEY = os.getenv("FMP_API_KEY")


def _check_api_key():
    """Verify API key is set."""
    if not API_KEY:
        raise ValueError("FMP_API_KEY environment variable not set. "
                        "Get free key at: https://financialmodelingprep.com/")


def _get(endpoint: str, **params) -> dict:
    """Make API request."""
    _check_api_key()
    params["apikey"] = API_KEY
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


# ============ QUOTES & PRICES ============

def get_quote(symbol: str) -> dict:
    """
    Get real-time stock quote.

    Returns: Price, change, volume, market cap, P/E, etc.

    Use case: Quick price check
    """
    data = _get(f"quote/{symbol}")
    return data[0] if data else {}


def get_quote_short(symbol: str) -> dict:
    """
    Get minimal quote data.

    Returns: Price, volume only
    """
    data = _get(f"quote-short/{symbol}")
    return data[0] if data else {}


def get_historical_prices(symbol: str, limit: int = None) -> list:
    """
    Get historical daily prices.

    Args:
        symbol: Stock symbol
        limit: Number of days (None = all)

    Returns: List of daily OHLCV

    Note: Use yfinance for better free access
    """
    params = {}
    if limit:
        params["limit"] = limit
    data = _get(f"historical-price-full/{symbol}", **params)
    return data.get("historical", [])


# ============ COMPANY INFO ============

def get_profile(symbol: str) -> dict:
    """
    Get company profile.

    Returns:
        - Name, description, sector, industry
        - CEO, employees, headquarters
        - Market cap, price, beta
        - Website, logo

    Use case: Company overview
    """
    data = _get(f"profile/{symbol}")
    return data[0] if data else {}


def get_key_metrics(symbol: str, period: str = "annual", limit: int = 5) -> list:
    """
    Get key financial metrics.

    Returns: Revenue per share, PE, PB, ROE, ROA, etc.

    Use case: Quick fundamental analysis
    """
    return _get(f"key-metrics/{symbol}", period=period, limit=limit)


def get_key_metrics_ttm(symbol: str) -> dict:
    """
    Get trailing twelve months key metrics.

    Returns: Latest TTM metrics
    """
    data = _get(f"key-metrics-ttm/{symbol}")
    return data[0] if data else {}


# ============ FINANCIAL RATIOS ============

def get_ratios(symbol: str, period: str = "annual", limit: int = 5) -> list:
    """
    Get all financial ratios.

    Returns comprehensive ratios:
        - Profitability: ROE, ROA, Profit Margin
        - Liquidity: Current Ratio, Quick Ratio
        - Leverage: Debt/Equity, Interest Coverage
        - Efficiency: Asset Turnover, Inventory Turnover
        - Valuation: P/E, P/B, P/S, EV/EBITDA

    Use case: Complete ratio analysis
    """
    return _get(f"ratios/{symbol}", period=period, limit=limit)


def get_ratios_ttm(symbol: str) -> dict:
    """
    Get trailing twelve months ratios.

    Returns: Latest TTM ratios
    """
    data = _get(f"ratios-ttm/{symbol}")
    return data[0] if data else {}


# ============ FINANCIAL STATEMENTS ============

def get_income_statement(symbol: str, period: str = "annual", limit: int = 5) -> list:
    """
    Get income statement.

    Returns: Revenue, expenses, net income, EPS

    Use case: Profitability analysis
    """
    return _get(f"income-statement/{symbol}", period=period, limit=limit)


def get_balance_sheet(symbol: str, period: str = "annual", limit: int = 5) -> list:
    """
    Get balance sheet.

    Returns: Assets, liabilities, equity

    Use case: Financial health analysis
    """
    return _get(f"balance-sheet-statement/{symbol}", period=period, limit=limit)


def get_cash_flow(symbol: str, period: str = "annual", limit: int = 5) -> list:
    """
    Get cash flow statement.

    Returns: Operating CF, Investing CF, Financing CF

    Use case: Cash generation analysis
    """
    return _get(f"cash-flow-statement/{symbol}", period=period, limit=limit)


# ============ VALUATION ============

def get_dcf(symbol: str) -> dict:
    """
    Get DCF (Discounted Cash Flow) valuation.

    Returns:
        - dcf: Intrinsic value per share
        - Stock Price: Current price
        - date: Calculation date

    Use case: Intrinsic value estimation

    Note: This is FMP's calculated DCF model
    """
    data = _get(f"discounted-cash-flow/{symbol}")
    return data[0] if data else {}


def get_advanced_dcf(symbol: str) -> dict:
    """
    Get detailed DCF with assumptions.

    Returns: DCF with growth rates, WACC, terminal value
    """
    data = _get(f"advanced_discounted_cash_flow/{symbol}")
    return data[0] if data else {}


def get_enterprise_value(symbol: str, period: str = "annual", limit: int = 5) -> list:
    """
    Get enterprise value metrics.

    Returns: EV, EV/Revenue, EV/EBITDA
    """
    return _get(f"enterprise-values/{symbol}", period=period, limit=limit)


def get_rating(symbol: str) -> dict:
    """
    Get FMP's stock rating.

    Returns:
        - rating: Overall rating (S, A, B, C, D, F)
        - ratingScore: Numeric score
        - ratingRecommendation: Buy/Hold/Sell

    Use case: Quick rating check
    """
    data = _get(f"rating/{symbol}")
    return data[0] if data else {}


# ============ STOCK SCREENER ============

def screen_stocks(
    market_cap_min: int = None,
    market_cap_max: int = None,
    price_min: float = None,
    price_max: float = None,
    sector: str = None,
    industry: str = None,
    dividend_min: float = None,
    pe_min: float = None,
    pe_max: float = None,
    beta_min: float = None,
    beta_max: float = None,
    volume_min: int = None,
    limit: int = 100,
) -> list:
    """
    Screen stocks by criteria.

    Args:
        market_cap_min/max: Market cap range
        price_min/max: Price range
        sector: Sector filter (e.g., "Technology")
        industry: Industry filter
        dividend_min: Minimum dividend yield
        pe_min/max: P/E ratio range
        beta_min/max: Beta range
        volume_min: Minimum average volume
        limit: Max results

    Returns: List of matching stocks

    Use case: Stock discovery, filtering
    """
    params = {"limit": limit}

    if market_cap_min:
        params["marketCapMoreThan"] = market_cap_min
    if market_cap_max:
        params["marketCapLowerThan"] = market_cap_max
    if price_min:
        params["priceMoreThan"] = price_min
    if price_max:
        params["priceLowerThan"] = price_max
    if sector:
        params["sector"] = sector
    if industry:
        params["industry"] = industry
    if dividend_min:
        params["dividendMoreThan"] = dividend_min
    if pe_min:
        params["peRatioMoreThan"] = pe_min
    if pe_max:
        params["peRatioLowerThan"] = pe_max
    if beta_min:
        params["betaMoreThan"] = beta_min
    if beta_max:
        params["betaLowerThan"] = beta_max
    if volume_min:
        params["volumeMoreThan"] = volume_min

    return _get("stock-screener", **params)


# ============ SEC FILINGS ============

def get_sec_filings(symbol: str, filing_type: str = None, limit: int = 20) -> list:
    """
    Get SEC filings list.

    Args:
        symbol: Stock symbol
        filing_type: Filter by type (10-K, 10-Q, 8-K, etc.)
        limit: Max results

    Returns: List of filings with links

    Note: For full filing content, use sec_edgar module
    """
    params = {"limit": limit}
    if filing_type:
        params["type"] = filing_type

    return _get(f"sec_filings/{symbol}", **params)


# ============ HELPER FUNCTIONS ============

def get_valuation_summary(symbol: str) -> dict:
    """
    Get valuation summary.

    Combines DCF, ratios, and rating.
    """
    dcf = get_dcf(symbol)
    ratios = get_ratios_ttm(symbol)
    rating = get_rating(symbol)

    current_price = dcf.get("Stock Price", 0)
    intrinsic_value = dcf.get("dcf", 0)

    upside = ((intrinsic_value / current_price) - 1) * 100 if current_price else 0

    return {
        "current_price": current_price,
        "dcf_value": intrinsic_value,
        "upside_percent": upside,
        "pe_ratio": ratios.get("peRatioTTM"),
        "pb_ratio": ratios.get("priceToBookRatioTTM"),
        "ev_ebitda": ratios.get("enterpriseValueMultipleTTM"),
        "dividend_yield": ratios.get("dividendYielTTM"),
        "rating": rating.get("rating"),
        "rating_score": rating.get("ratingScore"),
    }


def find_undervalued_stocks(sector: str = None, max_pe: float = 15,
                            min_dividend: float = 0.02) -> list:
    """
    Find potentially undervalued dividend stocks.

    Returns: List of stocks with low P/E and dividend
    """
    return screen_stocks(
        sector=sector,
        pe_max=max_pe,
        dividend_min=min_dividend,
        market_cap_min=1e9,  # At least $1B market cap
        limit=50,
    )


def find_growth_stocks(sector: str = None, min_market_cap: int = 10e9) -> list:
    """
    Find growth stocks.

    Returns: Large cap stocks with high growth potential
    """
    return screen_stocks(
        sector=sector,
        market_cap_min=min_market_cap,
        beta_min=1.0,  # Higher volatility
        limit=50,
    )


if __name__ == "__main__":
    if not API_KEY:
        print("FMP_API_KEY not set")
        print("Get free key at: https://financialmodelingprep.com/")
    else:
        print("=== Apple Valuation ===")
        val = get_valuation_summary("AAPL")
        print(f"Price: ${val['current_price']}")
        print(f"DCF Value: ${val['dcf_value']:.2f}")
        print(f"Upside: {val['upside_percent']:+.1f}%")
        print(f"P/E: {val['pe_ratio']:.1f}")
        print(f"Rating: {val['rating']}")

        print("\n=== Value Stocks (Tech) ===")
        stocks = find_undervalued_stocks(sector="Technology")[:5]
        for s in stocks:
            print(f"  {s['symbol']}: P/E {s.get('pe', 'N/A')}, Div {s.get('dividendYield', 0)*100:.1f}%")
