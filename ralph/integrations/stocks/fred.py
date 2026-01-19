# -*- coding: utf-8 -*-
"""
FRED (Federal Reserve Economic Data) API Integration

USE FOR:
- Federal Funds Rate
- Treasury yields (2Y, 10Y, 30Y)
- Yield curve (10Y-2Y spread)
- Inflation data (CPI, PCE)
- Unemployment rate
- GDP growth
- M2 Money supply
- VIX (volatility index)
- USD Index

DO NOT USE FOR:
- Stock prices (use yfinance)
- Company data (use yfinance)
- Company news (use Finnhub)
- Crypto data (use crypto integrations)

RATE LIMIT: 120 requests/min
API KEY: Required (free at fred.stlouisfed.org)

Set environment variable: FRED_API_KEY
"""

import os
import requests
import pandas as pd
from typing import Optional, List, Dict
from datetime import datetime, timedelta

BASE_URL = "https://api.stlouisfed.org/fred"
API_KEY = os.getenv("FRED_API_KEY")


# ============ POPULAR SERIES IDS ============

SERIES = {
    # Interest Rates
    "fed_funds_rate": "DFF",           # Federal Funds Effective Rate
    "treasury_10y": "DGS10",           # 10-Year Treasury
    "treasury_2y": "DGS2",             # 2-Year Treasury
    "treasury_30y": "DGS30",           # 30-Year Treasury
    "treasury_3m": "DTB3",             # 3-Month Treasury
    "yield_curve": "T10Y2Y",           # 10Y-2Y Spread (inversion indicator!)

    # Inflation
    "cpi": "CPIAUCSL",                 # CPI All Urban Consumers
    "cpi_yoy": "CPIAUCSL",             # Same, calculate YoY
    "pce": "PCEPI",                    # PCE Price Index
    "core_pce": "PCEPILFE",            # Core PCE (ex food & energy)

    # Employment
    "unemployment": "UNRATE",          # Unemployment Rate
    "nonfarm_payrolls": "PAYEMS",      # Nonfarm Payrolls
    "jobless_claims": "ICSA",          # Initial Jobless Claims

    # GDP & Growth
    "gdp": "GDP",                      # Nominal GDP
    "real_gdp": "GDPC1",               # Real GDP
    "gdp_growth": "A191RL1Q225SBEA",   # Real GDP Growth Rate

    # Money Supply
    "m2": "M2SL",                      # M2 Money Supply
    "m1": "M1SL",                      # M1 Money Supply

    # Market Indicators
    "sp500": "SP500",                  # S&P 500 Index
    "vix": "VIXCLS",                   # VIX Volatility Index
    "usd_index": "DTWEXBGS",           # Trade Weighted USD Index

    # Housing
    "housing_starts": "HOUST",         # Housing Starts
    "home_prices": "CSUSHPINSA",       # Case-Shiller Home Price Index

    # Consumer
    "retail_sales": "RSXFS",           # Retail Sales
    "consumer_sentiment": "UMCSENT",   # Michigan Consumer Sentiment
}


def _check_api_key():
    """Verify API key is set."""
    if not API_KEY:
        raise ValueError("FRED_API_KEY environment variable not set. "
                        "Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html")


def get_series(series_id: str, start_date: str = None,
               end_date: str = None) -> pd.DataFrame:
    """
    Get FRED time series data.

    Args:
        series_id: FRED series ID (e.g., "DFF", "DGS10")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)

    Returns:
        DataFrame with date and value columns

    Use case: Historical macro data analysis
    """
    _check_api_key()

    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json"
    }
    if start_date:
        params["observation_start"] = start_date
    if end_date:
        params["observation_end"] = end_date

    response = requests.get(f"{BASE_URL}/series/observations", params=params)
    response.raise_for_status()
    data = response.json()["observations"]

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    return df[["date", "value"]].dropna()


def get_latest_value(series_id: str) -> dict:
    """
    Get latest value for a series.

    Returns: {value, date, series_id}
    """
    df = get_series(series_id)
    if df.empty:
        return {"error": f"No data for {series_id}"}

    latest = df.iloc[-1]
    return {
        "series_id": series_id,
        "value": latest["value"],
        "date": latest["date"].strftime("%Y-%m-%d"),
    }


def get_series_info(series_id: str) -> dict:
    """
    Get series metadata.

    Returns: Title, units, frequency, description
    """
    _check_api_key()

    response = requests.get(
        f"{BASE_URL}/series",
        params={"series_id": series_id, "api_key": API_KEY, "file_type": "json"}
    )
    response.raise_for_status()
    series = response.json()["seriess"][0]

    return {
        "id": series.get("id"),
        "title": series.get("title"),
        "units": series.get("units"),
        "frequency": series.get("frequency"),
        "seasonal_adjustment": series.get("seasonal_adjustment"),
    }


# ============ MACRO DASHBOARD ============

def get_macro_dashboard() -> dict:
    """
    Get key macro indicators dashboard.

    Returns: Dict of current values for major indicators

    Use case: Quick macro overview
    """
    indicators = {
        "fed_funds_rate": "DFF",
        "treasury_10y": "DGS10",
        "treasury_2y": "DGS2",
        "yield_curve_10y_2y": "T10Y2Y",
        "unemployment": "UNRATE",
        "vix": "VIXCLS",
    }

    dashboard = {}
    for name, series_id in indicators.items():
        try:
            result = get_latest_value(series_id)
            dashboard[name] = {
                "value": result["value"],
                "date": result["date"],
            }
        except Exception as e:
            dashboard[name] = {"error": str(e)}

    return dashboard


def get_interest_rates() -> dict:
    """
    Get current interest rates.

    Returns: Fed funds, treasury yields, spread
    """
    rates = {}

    for name in ["fed_funds_rate", "treasury_2y", "treasury_10y", "treasury_30y", "yield_curve"]:
        series_id = SERIES[name]
        result = get_latest_value(series_id)
        rates[name] = result.get("value")

    return rates


def get_inflation_data() -> dict:
    """
    Get inflation indicators.

    Returns: CPI, PCE, Core PCE
    """
    inflation = {}

    # CPI
    cpi_df = get_series("CPIAUCSL")
    if not cpi_df.empty:
        # Calculate YoY change
        cpi_df["yoy"] = cpi_df["value"].pct_change(periods=12) * 100
        inflation["cpi_yoy"] = cpi_df.iloc[-1]["yoy"]
        inflation["cpi_latest"] = cpi_df.iloc[-1]["value"]

    # Core PCE
    pce = get_latest_value("PCEPILFE")
    inflation["core_pce"] = pce.get("value")

    return inflation


def get_yield_curve_status() -> dict:
    """
    Analyze yield curve status.

    Returns:
        - spread: 10Y-2Y spread
        - is_inverted: True if spread < 0
        - status: "inverted", "flat", or "normal"

    Use case: Recession indicator
    """
    spread_data = get_latest_value("T10Y2Y")
    spread = spread_data.get("value", 0)

    if spread < 0:
        status = "inverted"
    elif spread < 0.5:
        status = "flat"
    else:
        status = "normal"

    return {
        "spread": spread,
        "is_inverted": spread < 0,
        "status": status,
        "date": spread_data.get("date"),
        "note": "Inverted yield curve often precedes recession by 12-18 months"
    }


def get_employment_data() -> dict:
    """
    Get employment indicators.

    Returns: Unemployment rate, nonfarm payrolls
    """
    unemployment = get_latest_value("UNRATE")
    payrolls = get_latest_value("PAYEMS")
    claims = get_latest_value("ICSA")

    return {
        "unemployment_rate": unemployment.get("value"),
        "nonfarm_payrolls_thousands": payrolls.get("value"),
        "initial_jobless_claims": claims.get("value"),
        "date": unemployment.get("date"),
    }


def get_gdp_data() -> dict:
    """
    Get GDP indicators.

    Returns: GDP, Real GDP, Growth rate
    """
    gdp = get_latest_value("GDP")
    real_gdp = get_latest_value("GDPC1")
    growth = get_latest_value("A191RL1Q225SBEA")

    return {
        "nominal_gdp_billions": gdp.get("value"),
        "real_gdp_billions": real_gdp.get("value"),
        "gdp_growth_rate": growth.get("value"),
        "date": gdp.get("date"),
    }


def get_money_supply() -> dict:
    """
    Get money supply data.

    Returns: M1, M2
    """
    m1 = get_latest_value("M1SL")
    m2 = get_latest_value("M2SL")

    # Calculate M2 YoY growth
    m2_df = get_series("M2SL")
    m2_yoy = None
    if not m2_df.empty:
        m2_df["yoy"] = m2_df["value"].pct_change(periods=12) * 100
        m2_yoy = m2_df.iloc[-1]["yoy"]

    return {
        "m1_billions": m1.get("value"),
        "m2_billions": m2.get("value"),
        "m2_yoy_growth": m2_yoy,
        "date": m2.get("date"),
    }


# ============ HISTORICAL ANALYSIS ============

def get_recession_indicators() -> dict:
    """
    Get key recession indicators.

    Returns: Yield curve, unemployment trend, LEI
    """
    yield_curve = get_yield_curve_status()

    # Unemployment trend
    unemp_df = get_series("UNRATE")
    unemp_3m_ago = unemp_df.iloc[-4]["value"] if len(unemp_df) > 3 else None
    unemp_current = unemp_df.iloc[-1]["value"]
    unemp_rising = unemp_current > unemp_3m_ago if unemp_3m_ago else None

    return {
        "yield_curve": yield_curve,
        "unemployment": {
            "current": unemp_current,
            "3m_ago": unemp_3m_ago,
            "rising": unemp_rising,
        },
        "warning_signs": sum([
            yield_curve["is_inverted"],
            unemp_rising or False,
        ]),
    }


def compare_to_history(series_id: str, percentile: bool = True) -> dict:
    """
    Compare current value to historical range.

    Returns: Current, min, max, average, percentile
    """
    df = get_series(series_id)
    if df.empty:
        return {"error": "No data"}

    current = df.iloc[-1]["value"]
    hist_min = df["value"].min()
    hist_max = df["value"].max()
    hist_avg = df["value"].mean()

    pct = (df["value"] <= current).sum() / len(df) * 100 if percentile else None

    return {
        "current": current,
        "historical_min": hist_min,
        "historical_max": hist_max,
        "historical_avg": hist_avg,
        "percentile": pct,
        "date_range": f"{df.iloc[0]['date'].strftime('%Y-%m-%d')} to {df.iloc[-1]['date'].strftime('%Y-%m-%d')}",
    }


if __name__ == "__main__":
    if not API_KEY:
        print("FRED_API_KEY not set")
        print("Get free key at: https://fred.stlouisfed.org/docs/api/api_key.html")
    else:
        print("=== Macro Dashboard ===")
        dashboard = get_macro_dashboard()
        for name, data in dashboard.items():
            if "error" not in data:
                print(f"  {name}: {data['value']}")

        print("\n=== Yield Curve Status ===")
        yc = get_yield_curve_status()
        print(f"  Spread: {yc['spread']:.2f}%")
        print(f"  Status: {yc['status']}")
