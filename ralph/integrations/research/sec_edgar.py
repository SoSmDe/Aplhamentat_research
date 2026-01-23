# -*- coding: utf-8 -*-
"""
SEC EDGAR API Integration

USE FOR:
- Company financial filings (10-K, 10-Q, 8-K)
- Insider trading data (Form 4)
- Institutional holdings (13F)
- Registration statements (S-1, S-3)
- Proxy statements (DEF 14A)
- Fund prospectuses
- Company facts and financials

DO NOT USE FOR:
- Non-US companies (use local regulators)
- Real-time stock prices (use financial APIs)
- Company research (use crunchbase, web search)
- News and events (use news_aggregator)

RATE LIMIT: 10 requests per second
API KEY: Not required (but User-Agent header required)

Official docs: https://www.sec.gov/developer
"""

import requests
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json

BASE_URL = "https://data.sec.gov"
SUBMISSIONS_URL = f"{BASE_URL}/submissions"
COMPANY_FACTS_URL = f"{BASE_URL}/api/xbrl/companyfacts"
FULL_TEXT_URL = "https://efts.sec.gov/LATEST/search-index"

# Required by SEC
USER_AGENT = "Ralph Research Bot research@example.com"

# Rate limiting
_last_request = 0
_min_interval = 0.1  # 10 requests per second


def _rate_limit():
    """Respect SEC rate limits."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request = time.time()


def _make_request(url: str, params: dict = None) -> dict:
    """Make request to SEC API."""
    _rate_limit()

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }

    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()


def _get_cik(identifier: str) -> str:
    """
    Convert ticker symbol or company name to CIK.
    CIK must be 10 digits with leading zeros.
    """
    # If already a CIK (all digits)
    if identifier.isdigit():
        return identifier.zfill(10)

    # Try to resolve ticker
    ticker = identifier.upper()

    # Fetch company tickers mapping
    _rate_limit()
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(
        "https://www.sec.gov/files/company_tickers.json",
        headers=headers
    )
    response.raise_for_status()
    tickers_data = response.json()

    for item in tickers_data.values():
        if item.get("ticker") == ticker:
            return str(item.get("cik_str")).zfill(10)

    raise ValueError(f"Could not find CIK for: {identifier}")


# Filing type descriptions
FILING_TYPES = {
    "10-K": "Annual report with comprehensive business overview",
    "10-Q": "Quarterly financial report",
    "8-K": "Current report (material events)",
    "10-K/A": "Amended annual report",
    "10-Q/A": "Amended quarterly report",
    "4": "Insider trading report",
    "13F-HR": "Institutional holdings report",
    "S-1": "Registration statement (IPO)",
    "S-3": "Registration statement (follow-on)",
    "DEF 14A": "Proxy statement",
    "SC 13D": "Beneficial ownership report (>5%)",
    "SC 13G": "Beneficial ownership report (passive)",
    "20-F": "Annual report (foreign private issuer)",
    "6-K": "Current report (foreign private issuer)",
}


def get_company_filings(identifier: str,
                        filing_types: List[str] = None,
                        limit: int = 50) -> dict:
    """
    Get recent filings for a company.

    Args:
        identifier: Ticker symbol or CIK number
        filing_types: Filter by form types (e.g., ["10-K", "10-Q", "8-K"])
        limit: Maximum number of filings to return

    Returns:
        Dict with company info and recent filings

    Use case: Get all SEC filings for a company

    Example:
        get_company_filings("AAPL")
        get_company_filings("COIN", filing_types=["10-K", "10-Q"])
        get_company_filings("0001679788")  # Using CIK
    """
    cik = _get_cik(identifier)

    data = _make_request(f"{SUBMISSIONS_URL}/CIK{cik}.json")

    # Parse company info
    company_info = {
        "cik": cik,
        "name": data.get("name"),
        "ticker": data.get("tickers", [None])[0],
        "sic": data.get("sic"),
        "sic_description": data.get("sicDescription"),
        "state": data.get("stateOfIncorporation"),
        "fiscal_year_end": data.get("fiscalYearEnd"),
        "ein": data.get("ein"),
        "exchanges": data.get("exchanges", []),
    }

    # Parse filings
    filings_data = data.get("filings", {}).get("recent", {})

    filings = []
    for i in range(len(filings_data.get("accessionNumber", []))):
        form_type = filings_data["form"][i]

        # Filter by filing types if specified
        if filing_types and form_type not in filing_types:
            continue

        accession = filings_data["accessionNumber"][i].replace("-", "")

        filings.append({
            "accession_number": filings_data["accessionNumber"][i],
            "form": form_type,
            "form_description": FILING_TYPES.get(form_type, ""),
            "filing_date": filings_data["filingDate"][i],
            "report_date": filings_data.get("reportDate", [None] * len(filings_data["form"]))[i],
            "primary_document": filings_data.get("primaryDocument", [None] * len(filings_data["form"]))[i],
            "description": filings_data.get("primaryDocDescription", [None] * len(filings_data["form"]))[i],
            "filing_url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}",
            "html_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}",
        })

        if len(filings) >= limit:
            break

    return {
        "company": company_info,
        "total_filings": len(filings),
        "filings": filings,
    }


def get_company_facts(identifier: str) -> dict:
    """
    Get XBRL facts (financials) for a company.

    Args:
        identifier: Ticker symbol or CIK number

    Returns:
        Dict with financial facts from XBRL filings

    Use case: Get structured financial data

    Example:
        get_company_facts("AAPL")
    """
    cik = _get_cik(identifier)

    data = _make_request(f"{COMPANY_FACTS_URL}/CIK{cik}.json")

    # Extract key financial metrics
    facts = data.get("facts", {})

    # Common metrics from US GAAP
    us_gaap = facts.get("us-gaap", {})

    extracted_metrics = {}

    # Key metrics to extract
    key_metrics = [
        "Revenues",
        "NetIncomeLoss",
        "Assets",
        "Liabilities",
        "StockholdersEquity",
        "OperatingIncomeLoss",
        "EarningsPerShareBasic",
        "EarningsPerShareDiluted",
        "CashAndCashEquivalentsAtCarryingValue",
        "LongTermDebt",
        "CommonStockSharesOutstanding",
    ]

    for metric in key_metrics:
        if metric in us_gaap:
            metric_data = us_gaap[metric]
            units = metric_data.get("units", {})

            # Get USD values if available
            if "USD" in units:
                values = sorted(
                    units["USD"],
                    key=lambda x: x.get("end", ""),
                    reverse=True
                )[:5]

                extracted_metrics[metric] = [
                    {
                        "value": v.get("val"),
                        "period_end": v.get("end"),
                        "period_start": v.get("start"),
                        "form": v.get("form"),
                        "filed": v.get("filed"),
                    }
                    for v in values
                ]
            elif "shares" in units:
                values = sorted(
                    units["shares"],
                    key=lambda x: x.get("end", ""),
                    reverse=True
                )[:5]

                extracted_metrics[metric] = [
                    {
                        "value": v.get("val"),
                        "period_end": v.get("end"),
                        "form": v.get("form"),
                    }
                    for v in values
                ]

    return {
        "cik": cik,
        "entity_name": data.get("entityName"),
        "metrics": extracted_metrics,
        "available_metrics": list(us_gaap.keys()),
    }


def get_filing_document(accession_number: str, cik: str, document: str = None) -> dict:
    """
    Get a specific filing document.

    Args:
        accession_number: Accession number (e.g., "0001193125-24-012345")
        cik: Company CIK
        document: Specific document filename (optional)

    Returns:
        Dict with document URLs and metadata

    Example:
        get_filing_document("0001193125-24-012345", "320193")
    """
    cik = cik.zfill(10)
    accession = accession_number.replace("-", "")

    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/index.json"

    _rate_limit()
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(index_url, headers=headers)
    response.raise_for_status()
    index_data = response.json()

    documents = []
    for item in index_data.get("directory", {}).get("item", []):
        doc_name = item.get("name", "")
        documents.append({
            "name": doc_name,
            "type": item.get("type"),
            "size": item.get("size"),
            "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc_name}",
        })

    return {
        "accession_number": accession_number,
        "cik": cik,
        "documents": documents,
    }


def search_filings(query: str,
                   filing_types: List[str] = None,
                   date_from: str = None,
                   date_to: str = None,
                   limit: int = 50) -> dict:
    """
    Full-text search across all SEC filings.

    Args:
        query: Search query
        filing_types: Filter by form types
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        limit: Maximum results

    Returns:
        Dict with matching filings

    Use case: Find specific disclosures across all companies

    Example:
        search_filings("bitcoin", filing_types=["10-K"])
        search_filings("tokenization", date_from="2024-01-01")
    """
    params = {
        "q": query,
        "dateRange": "custom",
        "startdt": date_from or "2020-01-01",
        "enddt": date_to or datetime.now().strftime("%Y-%m-%d"),
        "from": 0,
        "size": min(limit, 100),
    }

    if filing_types:
        params["forms"] = ",".join(filing_types)

    _rate_limit()
    headers = {"User-Agent": USER_AGENT}
    response = requests.get(FULL_TEXT_URL, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()

    results = []
    for hit in data.get("hits", {}).get("hits", []):
        source = hit.get("_source", {})
        results.append({
            "cik": source.get("ciks", [None])[0],
            "company_name": source.get("display_names", [None])[0],
            "ticker": source.get("tickers", [None])[0] if source.get("tickers") else None,
            "form": source.get("form"),
            "filing_date": source.get("file_date"),
            "accession_number": source.get("adsh"),
            "description": source.get("file_description"),
            "url": f"https://www.sec.gov/Archives/edgar/data/{source.get('ciks', [''])[0]}/{source.get('adsh', '').replace('-', '')}",
        })

    return {
        "query": query,
        "total_hits": data.get("hits", {}).get("total", {}).get("value", 0),
        "results": results,
    }


def get_insider_transactions(identifier: str, limit: int = 50) -> dict:
    """
    Get insider trading transactions (Form 4).

    Args:
        identifier: Ticker symbol or CIK
        limit: Maximum number of transactions

    Returns:
        Dict with insider transactions

    Example:
        get_insider_transactions("AAPL")
    """
    filings = get_company_filings(identifier, filing_types=["4"], limit=limit)

    return {
        "company": filings["company"],
        "total_transactions": filings["total_filings"],
        "transactions": filings["filings"],
    }


def get_institutional_holdings(identifier: str) -> dict:
    """
    Get institutional holdings (13F filings).

    Args:
        identifier: Ticker symbol or CIK

    Returns:
        Dict with recent 13F filings

    Example:
        get_institutional_holdings("AAPL")
    """
    filings = get_company_filings(identifier, filing_types=["13F-HR"], limit=10)

    return {
        "company": filings["company"],
        "filings": filings["filings"],
    }


def get_recent_ipos(limit: int = 50) -> dict:
    """
    Get recent IPO registration statements (S-1).

    Args:
        limit: Maximum number of results

    Returns:
        Dict with recent S-1 filings

    Example:
        get_recent_ipos()
    """
    date_from = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

    return search_filings(
        query="*",
        filing_types=["S-1", "S-1/A"],
        date_from=date_from,
        limit=limit
    )


# ============ HELPER FUNCTIONS ============

def get_annual_reports(identifier: str, years: int = 5) -> dict:
    """
    Get recent annual reports (10-K).

    Args:
        identifier: Ticker or CIK
        years: Number of years to retrieve

    Returns: 10-K filings
    """
    return get_company_filings(
        identifier,
        filing_types=["10-K", "10-K/A"],
        limit=years
    )


def get_quarterly_reports(identifier: str, quarters: int = 8) -> dict:
    """
    Get recent quarterly reports (10-Q).

    Args:
        identifier: Ticker or CIK
        quarters: Number of quarters to retrieve

    Returns: 10-Q filings
    """
    return get_company_filings(
        identifier,
        filing_types=["10-Q", "10-Q/A"],
        limit=quarters
    )


def get_material_events(identifier: str, limit: int = 20) -> dict:
    """
    Get recent material events (8-K).

    Args:
        identifier: Ticker or CIK
        limit: Number of events

    Returns: 8-K filings
    """
    return get_company_filings(
        identifier,
        filing_types=["8-K", "8-K/A"],
        limit=limit
    )


def get_crypto_related_filings(limit: int = 50) -> dict:
    """
    Get filings mentioning cryptocurrency/blockchain.

    Returns: Filings with crypto keywords
    """
    return search_filings(
        query="cryptocurrency OR blockchain OR bitcoin OR 'digital assets'",
        date_from=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        limit=limit
    )


def get_rwa_related_filings(limit: int = 50) -> dict:
    """
    Get filings mentioning tokenization/RWA.

    Returns: Filings with tokenization keywords
    """
    return search_filings(
        query="tokenization OR 'real world assets' OR 'security token'",
        date_from=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"),
        limit=limit
    )


def format_filing_summary(filing: dict) -> str:
    """
    Format filing as a summary string.

    Args:
        filing: Filing dict from get_company_filings

    Returns:
        Formatted string
    """
    form = filing.get("form", "Unknown")
    date = filing.get("filing_date", "Unknown")
    desc = filing.get("description") or FILING_TYPES.get(form, "")

    return f"{form} ({date}): {desc[:60]}..."


if __name__ == "__main__":
    print("=== SEC EDGAR Test ===")

    # Test with Apple
    result = get_company_filings("AAPL", filing_types=["10-K"], limit=3)
    print(f"\n{result['company']['name']} (CIK: {result['company']['cik']})")

    for filing in result["filings"]:
        print(f"\n  {filing['form']} - {filing['filing_date']}")
        print(f"  URL: {filing['filing_url']}")
