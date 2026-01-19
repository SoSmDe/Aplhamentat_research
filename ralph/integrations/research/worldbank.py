# -*- coding: utf-8 -*-
"""
World Bank Data API Integration

USE FOR:
- GDP data (nominal, per capita, growth)
- Population statistics
- Inflation rates
- Unemployment data
- Trade statistics
- Development indicators
- Country comparisons

DO NOT USE FOR:
- Real-time market data (use stock/crypto APIs)
- Company-specific data (use yfinance)
- Consulting research (use mckinsey, deloitte)

RATE LIMIT: Fair use
API KEY: Not required

Official API docs: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime

BASE_URL = "https://api.worldbank.org/v2"


# ============ POPULAR INDICATORS ============

INDICATORS = {
    # GDP
    "gdp": "NY.GDP.MKTP.CD",              # GDP (current US$)
    "gdp_per_capita": "NY.GDP.PCAP.CD",   # GDP per capita (current US$)
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",    # GDP growth (annual %)

    # Population
    "population": "SP.POP.TOTL",           # Total population
    "population_growth": "SP.POP.GROW",    # Population growth (annual %)

    # Inflation & Prices
    "inflation": "FP.CPI.TOTL.ZG",         # Inflation, consumer prices (annual %)
    "cpi": "FP.CPI.TOTL",                  # Consumer price index

    # Employment
    "unemployment": "SL.UEM.TOTL.ZS",      # Unemployment (% of labor force)
    "labor_force": "SL.TLF.TOTL.IN",       # Labor force, total

    # Trade
    "exports_gdp": "NE.EXP.GNFS.ZS",       # Exports (% of GDP)
    "imports_gdp": "NE.IMP.GNFS.ZS",       # Imports (% of GDP)
    "trade_balance": "NE.RSB.GNFS.ZS",     # Trade balance (% of GDP)
    "fdi": "BX.KLT.DINV.WD.GD.ZS",         # FDI net inflows (% of GDP)

    # Finance
    "interest_rate": "FR.INR.RINR",        # Real interest rate
    "credit_private": "FS.AST.PRVT.GD.ZS", # Domestic credit to private sector (% of GDP)

    # Government
    "gov_debt": "GC.DOD.TOTL.GD.ZS",       # Government debt (% of GDP)
    "gov_spending": "GC.XPN.TOTL.GD.ZS",   # Government expenditure (% of GDP)

    # Development
    "gini": "SI.POV.GINI",                 # Gini index
    "poverty": "SI.POV.DDAY",              # Poverty headcount ratio
    "life_expectancy": "SP.DYN.LE00.IN",   # Life expectancy at birth

    # Technology
    "internet_users": "IT.NET.USER.ZS",    # Internet users (% of population)
    "mobile_subs": "IT.CEL.SETS.P2",       # Mobile subscriptions (per 100 people)
}

# Country codes
COUNTRIES = {
    "USA": "US", "United States": "US",
    "China": "CN", "CHN": "CN",
    "Japan": "JP", "JPN": "JP",
    "Germany": "DE", "DEU": "DE",
    "UK": "GB", "United Kingdom": "GB",
    "France": "FR", "FRA": "FR",
    "India": "IN", "IND": "IN",
    "Brazil": "BR", "BRA": "BR",
    "Russia": "RU", "RUS": "RU",
    "World": "WLD",
}


def get_indicator(indicator: str, country: str = "WLD",
                  start_year: int = 2010, end_year: int = None) -> dict:
    """
    Get World Bank indicator data.

    Args:
        indicator: Indicator code or name (e.g., "gdp", "NY.GDP.MKTP.CD")
        country: Country code (e.g., "US", "WLD" for world)
        start_year: Start year
        end_year: End year (default: current year)

    Returns:
        Dict with indicator data, metadata, and time series

    Use case: Macro economic analysis, country comparison
    """
    # Resolve indicator name to code
    indicator_code = INDICATORS.get(indicator.lower(), indicator)

    # Resolve country code
    country_code = COUNTRIES.get(country, country)

    if end_year is None:
        end_year = datetime.now().year

    url = f"{BASE_URL}/country/{country_code}/indicator/{indicator_code}"
    params = {
        "date": f"{start_year}:{end_year}",
        "format": "json",
        "per_page": 500
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if len(data) < 2:
        return {"error": "No data found", "indicator": indicator_code, "country": country_code}

    metadata = data[0]
    values = data[1]

    # Process time series
    time_series = []
    for item in values:
        if item.get("value") is not None:
            time_series.append({
                "year": int(item["date"]),
                "value": item["value"],
            })

    # Sort by year
    time_series = sorted(time_series, key=lambda x: x["year"])

    return {
        "indicator": {
            "code": indicator_code,
            "name": values[0]["indicator"]["value"] if values else indicator_code,
        },
        "country": {
            "code": country_code,
            "name": values[0]["country"]["value"] if values else country_code,
        },
        "data": time_series,
        "latest": time_series[-1] if time_series else None,
        "total_records": metadata.get("total", 0),
    }


def get_multiple_indicators(indicators: List[str], country: str = "WLD",
                            start_year: int = 2015) -> dict:
    """
    Get multiple indicators for a country.

    Args:
        indicators: List of indicator names or codes
        country: Country code
        start_year: Start year

    Returns: Dict with all indicators
    """
    result = {}
    for ind in indicators:
        data = get_indicator(ind, country, start_year)
        result[ind] = data
    return result


def get_country_profile(country: str) -> dict:
    """
    Get comprehensive country profile.

    Returns: GDP, population, inflation, unemployment, trade data

    Use case: Country overview, investment research
    """
    indicators = ["gdp", "gdp_per_capita", "gdp_growth", "population",
                  "inflation", "unemployment", "exports_gdp"]

    profile = {
        "country": country,
        "indicators": {}
    }

    for ind in indicators:
        data = get_indicator(ind, country, start_year=2018)
        if data.get("latest"):
            profile["indicators"][ind] = {
                "value": data["latest"]["value"],
                "year": data["latest"]["year"],
                "name": data["indicator"]["name"],
            }

    return profile


def compare_countries(countries: List[str], indicator: str,
                      start_year: int = 2015) -> dict:
    """
    Compare indicator across countries.

    Args:
        countries: List of country codes
        indicator: Indicator name or code
        start_year: Start year

    Returns: Comparison data for all countries

    Use case: Cross-country analysis
    """
    comparison = {
        "indicator": indicator,
        "countries": {}
    }

    for country in countries:
        data = get_indicator(indicator, country, start_year)
        if data.get("latest"):
            comparison["countries"][country] = {
                "name": data["country"]["name"],
                "latest_value": data["latest"]["value"],
                "latest_year": data["latest"]["year"],
                "time_series": data["data"],
            }

    # Rank by latest value
    ranked = sorted(
        comparison["countries"].items(),
        key=lambda x: x[1].get("latest_value", 0) or 0,
        reverse=True
    )
    comparison["ranking"] = [c[0] for c in ranked]

    return comparison


def get_gdp_ranking(limit: int = 20, year: int = None) -> list:
    """
    Get top countries by GDP.

    Returns: List of countries ranked by GDP

    Use case: Global economic overview
    """
    if year is None:
        year = datetime.now().year - 1  # Latest available

    url = f"{BASE_URL}/country/all/indicator/NY.GDP.MKTP.CD"
    params = {
        "date": year,
        "format": "json",
        "per_page": 300
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if len(data) < 2:
        return []

    # Filter and sort
    countries = []
    for item in data[1]:
        if item.get("value") and item.get("countryiso3code"):
            countries.append({
                "country": item["country"]["value"],
                "code": item["countryiso3code"],
                "gdp": item["value"],
                "year": year,
            })

    # Sort by GDP
    countries = sorted(countries, key=lambda x: x["gdp"], reverse=True)

    return countries[:limit]


# ============ HELPER FUNCTIONS ============

def get_macro_summary(country: str = "WLD") -> dict:
    """
    Get macro economic summary.

    Returns: Key indicators in readable format
    """
    indicators = {
        "GDP": "gdp",
        "GDP Growth": "gdp_growth",
        "GDP per Capita": "gdp_per_capita",
        "Inflation": "inflation",
        "Unemployment": "unemployment",
        "Population": "population",
    }

    summary = {"country": country, "data": {}}

    for name, code in indicators.items():
        data = get_indicator(code, country, start_year=2020)
        if data.get("latest"):
            value = data["latest"]["value"]

            # Format value
            if code == "gdp":
                formatted = f"${value/1e12:.2f}T" if value > 1e12 else f"${value/1e9:.1f}B"
            elif code == "population":
                formatted = f"{value/1e9:.2f}B" if value > 1e9 else f"{value/1e6:.1f}M"
            elif code in ["gdp_growth", "inflation", "unemployment"]:
                formatted = f"{value:.1f}%"
            elif code == "gdp_per_capita":
                formatted = f"${value:,.0f}"
            else:
                formatted = str(value)

            summary["data"][name] = {
                "value": value,
                "formatted": formatted,
                "year": data["latest"]["year"],
            }

    return summary


def search_indicators(query: str) -> list:
    """
    Search for indicators by keyword.

    Returns: List of matching indicators
    """
    url = f"{BASE_URL}/indicator"
    params = {"format": "json", "per_page": 1000}

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if len(data) < 2:
        return []

    query_lower = query.lower()
    matches = []

    for item in data[1]:
        name = item.get("name", "").lower()
        if query_lower in name:
            matches.append({
                "code": item["id"],
                "name": item["name"],
                "source": item.get("source", {}).get("value", ""),
            })

    return matches[:20]  # Limit results


if __name__ == "__main__":
    print("=== World Macro Summary ===")
    summary = get_macro_summary("WLD")
    for name, data in summary["data"].items():
        print(f"  {name}: {data['formatted']} ({data['year']})")

    print("\n=== Top 10 GDP Countries ===")
    ranking = get_gdp_ranking(10)
    for i, c in enumerate(ranking, 1):
        print(f"  {i}. {c['country']}: ${c['gdp']/1e12:.2f}T")
