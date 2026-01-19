# -*- coding: utf-8 -*-
"""
SEC EDGAR API Integration

USE FOR:
- Official SEC filings (10-K, 10-Q, 8-K)
- Institutional holdings (13-F filings)
- Insider trading (Form 4)
- Proxy statements (DEF 14A)
- Company facts and financials
- Primary source verification

DO NOT USE FOR:
- Real-time prices (use Finnhub)
- Quick fundamentals lookup (use yfinance - faster)
- News (use Finnhub)
- Macro data (use FRED)

RATE LIMIT: 10 requests/second
API KEY: Not required!

IMPORTANT: Must include User-Agent header
"""

import requests
from typing import Optional, List, Dict
from datetime import datetime

# Required header for SEC API
SEC_HEADERS = {
    "User-Agent": "Ralph Research Bot research@example.com",
    "Accept-Encoding": "gzip, deflate",
}


# ============ CIK LOOKUP ============

# Common company CIKs (Central Index Key)
COMPANY_CIKS = {
    # Tech Giants
    "AAPL": "320193",
    "MSFT": "789019",
    "GOOGL": "1652044",
    "AMZN": "1018724",
    "META": "1326801",
    "NVDA": "1045810",
    "TSLA": "1318605",

    # Finance
    "JPM": "19617",
    "BAC": "70858",
    "GS": "886982",
    "BRK-A": "1067983",
    "BRK-B": "1067983",

    # REITs
    "O": "726728",       # Realty Income
    "AMT": "1053507",    # American Tower
    "PLD": "1045609",    # Prologis
    "SPG": "1063761",    # Simon Property

    # Other
    "JNJ": "200406",
    "PG": "80424",
    "KO": "21344",
    "DIS": "1744489",
    "V": "1403161",
}


def get_cik(ticker: str) -> str:
    """
    Get CIK for a ticker.

    Args:
        ticker: Stock symbol

    Returns: 10-digit CIK (with leading zeros)
    """
    # Check cache first
    if ticker.upper() in COMPANY_CIKS:
        return COMPANY_CIKS[ticker.upper()].zfill(10)

    # Lookup from SEC
    response = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=SEC_HEADERS
    )
    response.raise_for_status()
    data = response.json()

    for entry in data.values():
        if entry.get("ticker", "").upper() == ticker.upper():
            return str(entry.get("cik_str")).zfill(10)

    raise ValueError(f"CIK not found for ticker: {ticker}")


# ============ FILINGS ============

def get_company_filings(ticker: str, filing_type: str = None) -> list:
    """
    Get SEC filings for a company.

    Args:
        ticker: Stock symbol
        filing_type: Filter by type (10-K, 10-Q, 8-K, etc.)

    Returns: List of filings with form type, date, accession number

    Use case: Find specific filings, audit trail
    """
    cik = get_cik(ticker)

    response = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=SEC_HEADERS
    )
    response.raise_for_status()
    data = response.json()

    filings = data.get("filings", {}).get("recent", {})

    result = []
    for i, form in enumerate(filings.get("form", [])):
        if filing_type and form != filing_type:
            continue

        result.append({
            "form": form,
            "filing_date": filings["filingDate"][i],
            "accession_number": filings["accessionNumber"][i],
            "primary_document": filings["primaryDocument"][i],
            "description": filings.get("primaryDocDescription", [""])[i] if i < len(filings.get("primaryDocDescription", [])) else "",
        })

    return result


def get_10k_filings(ticker: str, limit: int = 5) -> list:
    """
    Get annual reports (10-K).

    Returns: List of 10-K filings

    Use case: Annual financial review
    """
    filings = get_company_filings(ticker, "10-K")
    return filings[:limit]


def get_10q_filings(ticker: str, limit: int = 4) -> list:
    """
    Get quarterly reports (10-Q).

    Returns: List of 10-Q filings

    Use case: Quarterly financial review
    """
    filings = get_company_filings(ticker, "10-Q")
    return filings[:limit]


def get_8k_filings(ticker: str, limit: int = 10) -> list:
    """
    Get current reports (8-K).

    8-K filings report material events:
    - Earnings announcements
    - Acquisitions
    - Management changes
    - Material agreements

    Use case: Event tracking, news verification
    """
    filings = get_company_filings(ticker, "8-K")
    return filings[:limit]


def get_filing_url(ticker: str, accession_number: str, document: str) -> str:
    """
    Get URL to download a filing document.

    Args:
        ticker: Stock symbol
        accession_number: Filing accession number
        document: Document filename

    Returns: Full URL to document
    """
    cik = get_cik(ticker)
    accession_clean = accession_number.replace("-", "")

    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{document}"


def download_filing(ticker: str, accession_number: str, document: str) -> str:
    """
    Download filing document content.

    Returns: Document content (HTML or text)
    """
    url = get_filing_url(ticker, accession_number, document)
    response = requests.get(url, headers=SEC_HEADERS)
    response.raise_for_status()
    return response.text


# ============ COMPANY FACTS ============

def get_company_facts(ticker: str) -> dict:
    """
    Get company facts from SEC.

    Contains all reported financial data in structured format.

    Returns: Dict with all reported facts organized by taxonomy

    Use case: Programmatic access to financial data
    """
    cik = get_cik(ticker)

    response = requests.get(
        f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
        headers=SEC_HEADERS
    )
    response.raise_for_status()
    return response.json()


def get_revenue_history(ticker: str) -> list:
    """
    Get revenue history from SEC filings.

    Returns: List of {period, value, filed_date}
    """
    facts = get_company_facts(ticker)

    # Try different revenue tags
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    revenue_tags = [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "SalesRevenueNet",
        "TotalRevenue",
    ]

    for tag in revenue_tags:
        if tag in us_gaap:
            units = us_gaap[tag].get("units", {})
            usd = units.get("USD", [])

            # Filter for annual (10-K) filings
            annual = [
                {
                    "period": item.get("fy"),
                    "value": item.get("val"),
                    "filed": item.get("filed"),
                    "form": item.get("form"),
                }
                for item in usd
                if item.get("form") == "10-K"
            ]

            # Deduplicate by year
            seen_years = set()
            result = []
            for item in sorted(annual, key=lambda x: x["filed"], reverse=True):
                if item["period"] not in seen_years:
                    seen_years.add(item["period"])
                    result.append(item)

            return sorted(result, key=lambda x: x["period"])

    return []


def get_net_income_history(ticker: str) -> list:
    """
    Get net income history from SEC filings.

    Returns: List of {period, value, filed_date}
    """
    facts = get_company_facts(ticker)
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    income_tags = ["NetIncomeLoss", "ProfitLoss", "NetIncome"]

    for tag in income_tags:
        if tag in us_gaap:
            units = us_gaap[tag].get("units", {})
            usd = units.get("USD", [])

            annual = [
                {
                    "period": item.get("fy"),
                    "value": item.get("val"),
                    "filed": item.get("filed"),
                }
                for item in usd
                if item.get("form") == "10-K"
            ]

            seen_years = set()
            result = []
            for item in sorted(annual, key=lambda x: x["filed"], reverse=True):
                if item["period"] not in seen_years:
                    seen_years.add(item["period"])
                    result.append(item)

            return sorted(result, key=lambda x: x["period"])

    return []


# ============ INSTITUTIONAL HOLDINGS (13-F) ============

def get_13f_filings(ticker: str, limit: int = 4) -> list:
    """
    Get 13-F institutional holdings filings.

    13-F filings show what institutions hold.

    Returns: List of 13-F filings

    Use case: Institutional ownership tracking
    """
    filings = get_company_filings(ticker, "13F-HR")
    return filings[:limit]


# ============ INSIDER TRADING (Form 4) ============

def get_insider_filings(ticker: str, limit: int = 20) -> list:
    """
    Get Form 4 insider trading filings.

    Form 4 reports insider buys/sells.

    Returns: List of Form 4 filings

    Use case: Insider trading analysis
    """
    filings = get_company_filings(ticker, "4")
    return filings[:limit]


# ============ HELPER FUNCTIONS ============

def get_company_info(ticker: str) -> dict:
    """
    Get basic company info from SEC.

    Returns: Name, CIK, SIC code, state, fiscal year end
    """
    cik = get_cik(ticker)

    response = requests.get(
        f"https://data.sec.gov/submissions/CIK{cik}.json",
        headers=SEC_HEADERS
    )
    response.raise_for_status()
    data = response.json()

    return {
        "name": data.get("name"),
        "cik": cik,
        "sic": data.get("sic"),
        "sic_description": data.get("sicDescription"),
        "state": data.get("stateOfIncorporation"),
        "fiscal_year_end": data.get("fiscalYearEnd"),
        "tickers": data.get("tickers", []),
        "exchanges": data.get("exchanges", []),
    }


def get_recent_filings_summary(ticker: str) -> dict:
    """
    Get summary of recent filings.

    Returns: Count by filing type
    """
    filings = get_company_filings(ticker)

    # Count by type
    by_type = {}
    for f in filings[:50]:  # Last 50
        form = f["form"]
        by_type[form] = by_type.get(form, 0) + 1

    # Get latest of each major type
    latest = {}
    for form_type in ["10-K", "10-Q", "8-K"]:
        for f in filings:
            if f["form"] == form_type:
                latest[form_type] = f["filing_date"]
                break

    return {
        "counts": by_type,
        "latest": latest,
        "total_filings": len(filings),
    }


if __name__ == "__main__":
    print("=== Apple SEC Info ===")
    info = get_company_info("AAPL")
    print(f"Name: {info['name']}")
    print(f"CIK: {info['cik']}")
    print(f"SIC: {info['sic_description']}")

    print("\n=== Recent 10-K Filings ===")
    filings = get_10k_filings("AAPL", limit=3)
    for f in filings:
        print(f"  {f['filing_date']}: {f['form']}")

    print("\n=== Revenue History ===")
    revenue = get_revenue_history("AAPL")
    for r in revenue[-5:]:
        print(f"  FY{r['period']}: ${r['value']/1e9:.1f}B")
