# -*- coding: utf-8 -*-
"""
IMF (International Monetary Fund) Data API Integration

USE FOR:
- World Economic Outlook (WEO) forecasts
- GDP growth projections
- Inflation forecasts
- Current account balances
- Government debt statistics
- Global economic reports

DO NOT USE FOR:
- Historical macro data (use World Bank - more complete)
- Real-time market data (use stock/crypto APIs)
- Company data (use yfinance)

RATE LIMIT: Fair use
API KEY: Not required

Official docs: https://datahelp.imf.org/
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime

BASE_URL = "http://dataservices.imf.org/REST/SDMX_JSON.svc"

# WEO (World Economic Outlook) indicators
WEO_INDICATORS = {
    # Growth
    "gdp_growth": "NGDP_RPCH",          # Real GDP growth (%)
    "gdp_ppp": "PPPGDP",                # GDP based on PPP
    "gdp_current": "NGDPD",             # GDP, current prices (USD)

    # Inflation
    "inflation": "PCPIPCH",             # Inflation, average consumer prices (%)
    "inflation_end": "PCPIEPCH",        # Inflation, end of period (%)

    # Employment
    "unemployment": "LUR",              # Unemployment rate (%)

    # Government
    "gov_debt": "GGXWDG_NGDP",         # Government gross debt (% of GDP)
    "gov_balance": "GGXCNL_NGDP",      # Government net lending/borrowing (% of GDP)
    "gov_revenue": "GGR_NGDP",         # Government revenue (% of GDP)

    # External
    "current_account": "BCA_NGDPD",    # Current account balance (% of GDP)
    "exports": "NXF",                  # Volume of exports
    "imports": "NMF",                  # Volume of imports
}

# Country codes (ISO 3-letter)
IMF_COUNTRIES = {
    "USA": "USA", "US": "USA",
    "China": "CHN", "CN": "CHN",
    "Japan": "JPN", "JP": "JPN",
    "Germany": "DEU", "DE": "DEU",
    "UK": "GBR", "GB": "GBR",
    "France": "FRA", "FR": "FRA",
    "India": "IND", "IN": "IND",
    "Brazil": "BRA", "BR": "BRA",
    "Russia": "RUS", "RU": "RUS",
    "World": "001",  # IMF code for World
}


def get_weo_data(indicator: str, countries: List[str] = None,
                 start_year: int = 2020, end_year: int = None) -> dict:
    """
    Get World Economic Outlook data.

    Args:
        indicator: Indicator code or name (e.g., "gdp_growth", "NGDP_RPCH")
        countries: List of country codes (default: major economies)
        start_year: Start year
        end_year: End year (default: +5 years forecast)

    Returns:
        Dict with indicator data and forecasts

    Use case: Economic forecasts, macro analysis
    """
    # Resolve indicator
    indicator_code = WEO_INDICATORS.get(indicator.lower(), indicator)

    if countries is None:
        countries = ["USA", "CHN", "JPN", "DEU", "GBR", "FRA", "IND"]

    # Resolve country codes
    country_codes = [IMF_COUNTRIES.get(c, c) for c in countries]

    if end_year is None:
        end_year = datetime.now().year + 5

    # IMF WEO API endpoint
    url = f"{BASE_URL}/CompactData/WEO/{indicator_code}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        return {"error": f"IMF API request failed: {str(e)}"}

    # Parse response (IMF uses SDMX format)
    result = {
        "indicator": indicator_code,
        "indicator_name": indicator,
        "countries": {},
        "years_range": f"{start_year}-{end_year}",
    }

    # IMF API response structure is complex, simplified parsing
    try:
        series_data = data.get("CompactData", {}).get("DataSet", {}).get("Series", [])

        if not isinstance(series_data, list):
            series_data = [series_data]

        for series in series_data:
            country = series.get("@REF_AREA", "")
            if country not in country_codes:
                continue

            obs = series.get("Obs", [])
            if not isinstance(obs, list):
                obs = [obs]

            time_series = []
            for o in obs:
                year = int(o.get("@TIME_PERIOD", 0))
                value = o.get("@OBS_VALUE")
                if year >= start_year and year <= end_year and value:
                    time_series.append({
                        "year": year,
                        "value": float(value),
                    })

            if time_series:
                result["countries"][country] = {
                    "data": sorted(time_series, key=lambda x: x["year"]),
                    "latest": time_series[-1] if time_series else None,
                }
    except Exception as e:
        result["parse_error"] = str(e)

    return result


def get_economic_outlook(country: str = "USA") -> dict:
    """
    Get comprehensive economic outlook for a country.

    Returns: GDP growth, inflation, unemployment forecasts

    Use case: Country economic analysis
    """
    country_code = IMF_COUNTRIES.get(country, country)

    indicators = ["gdp_growth", "inflation", "unemployment", "gov_debt", "current_account"]

    outlook = {
        "country": country_code,
        "indicators": {},
        "source": "IMF World Economic Outlook",
    }

    for ind in indicators:
        data = get_weo_data(ind, [country_code])
        if data.get("countries", {}).get(country_code):
            outlook["indicators"][ind] = data["countries"][country_code]

    return outlook


def get_global_growth_forecast() -> dict:
    """
    Get global GDP growth forecast.

    Returns: World and major economies growth forecast

    Use case: Global macro overview
    """
    countries = ["001", "USA", "CHN", "JPN", "DEU", "IND", "GBR"]  # 001 = World

    data = get_weo_data("gdp_growth", countries)

    forecast = {
        "indicator": "Real GDP Growth (%)",
        "source": "IMF World Economic Outlook",
        "forecasts": {},
    }

    country_names = {
        "001": "World",
        "USA": "United States",
        "CHN": "China",
        "JPN": "Japan",
        "DEU": "Germany",
        "IND": "India",
        "GBR": "United Kingdom",
    }

    for code, country_data in data.get("countries", {}).items():
        name = country_names.get(code, code)
        forecast["forecasts"][name] = country_data.get("data", [])

    return forecast


def get_inflation_forecast(countries: List[str] = None) -> dict:
    """
    Get inflation forecast.

    Returns: Inflation forecasts for countries

    Use case: Inflation analysis, monetary policy
    """
    if countries is None:
        countries = ["USA", "CHN", "JPN", "DEU", "GBR"]

    data = get_weo_data("inflation", countries)

    return {
        "indicator": "Inflation, avg consumer prices (%)",
        "source": "IMF WEO",
        "countries": data.get("countries", {}),
    }


# ============ ALTERNATIVE: WEO DATABASE DOWNLOAD ============

def get_weo_report_links() -> dict:
    """
    Get links to latest WEO reports.

    Returns: URLs to IMF WEO publications

    Use case: Access full reports for detailed analysis
    """
    current_year = datetime.now().year

    return {
        "latest_weo": f"https://www.imf.org/en/Publications/WEO/Issues/{current_year}",
        "data_download": "https://www.imf.org/en/Publications/WEO/weo-database",
        "api_docs": "https://datahelp.imf.org/knowledgebase/articles/630877-data-services",
        "datasets": [
            {
                "name": "World Economic Outlook Database",
                "description": "Full WEO dataset in Excel/CSV",
                "url": "https://www.imf.org/en/Publications/WEO/weo-database",
            },
            {
                "name": "International Financial Statistics",
                "description": "Exchange rates, interest rates, prices",
                "url": "https://data.imf.org/?sk=4c514d48-b6ba-49ed-8ab9-52b0c1a0179b",
            },
            {
                "name": "Government Finance Statistics",
                "description": "Government revenues, expenditures, debt",
                "url": "https://data.imf.org/?sk=a0867067-d23c-4ebc-ad23-d3b015045405",
            },
        ]
    }


# ============ HELPER FUNCTIONS ============

def format_forecast_table(indicator: str, countries: List[str] = None) -> str:
    """
    Format forecast data as table string.

    Returns: Formatted table for reports
    """
    data = get_weo_data(indicator, countries)

    if "error" in data:
        return f"Error: {data['error']}"

    lines = [f"IMF Forecast: {indicator}", "-" * 60]

    for country, country_data in data.get("countries", {}).items():
        values = country_data.get("data", [])
        if values:
            value_str = " | ".join([f"{v['year']}:{v['value']:.1f}" for v in values[-5:]])
            lines.append(f"{country}: {value_str}")

    return "\n".join(lines)


def get_key_forecasts() -> dict:
    """
    Get key economic forecasts for research.

    Returns: Summary of major forecasts

    Use case: Quick macro overview for reports
    """
    current_year = datetime.now().year

    return {
        "source": "IMF World Economic Outlook",
        "note": "Use get_weo_data() for detailed forecasts",
        "key_indicators": [
            {"name": "Global GDP Growth", "code": "NGDP_RPCH", "unit": "%"},
            {"name": "Inflation", "code": "PCPIPCH", "unit": "%"},
            {"name": "Unemployment", "code": "LUR", "unit": "%"},
            {"name": "Government Debt", "code": "GGXWDG_NGDP", "unit": "% of GDP"},
            {"name": "Current Account", "code": "BCA_NGDPD", "unit": "% of GDP"},
        ],
        "major_economies": ["USA", "CHN", "JPN", "DEU", "IND", "GBR", "FRA"],
        "forecast_horizon": f"{current_year}-{current_year + 5}",
    }


if __name__ == "__main__":
    print("=== IMF Key Forecasts Info ===")
    info = get_key_forecasts()
    print(f"Source: {info['source']}")
    print(f"Forecast horizon: {info['forecast_horizon']}")
    print(f"Major economies: {', '.join(info['major_economies'])}")

    print("\n=== WEO Report Links ===")
    links = get_weo_report_links()
    print(f"Data download: {links['data_download']}")
