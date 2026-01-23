# -*- coding: utf-8 -*-
"""
Crunchbase API Integration

USE FOR:
- Company information (funding, investors, team)
- Startup research and due diligence
- Market analysis and competitive intelligence
- Investor profiles and portfolios
- Acquisition and IPO data
- Industry trends and analysis

DO NOT USE FOR:
- Real-time stock prices (use financial APIs)
- News articles (use news_aggregator)
- Scientific research (use arxiv, pubmed)
- Government filings (use sec_edgar)

RATE LIMIT: Based on plan (Basic API: 200 calls/min)
API KEY: Required (CRUNCHBASE_API_KEY)

Official docs: https://data.crunchbase.com/docs
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime

BASE_URL = "https://api.crunchbase.com/api/v4"


def _get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("CRUNCHBASE_API_KEY")
    if not api_key:
        raise ValueError(
            "CRUNCHBASE_API_KEY not found in environment. "
            "Get your key at https://data.crunchbase.com/"
        )
    return api_key


def _make_request(endpoint: str, params: dict = None) -> dict:
    """Make request to Crunchbase API."""
    headers = {
        "X-cb-user-key": _get_api_key(),
        "Content-Type": "application/json"
    }

    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, headers=headers, params=params or {})
    response.raise_for_status()
    return response.json()


def search_organizations(query: str,
                         organization_types: List[str] = None,
                         locations: List[str] = None,
                         categories: List[str] = None,
                         num_results: int = 25) -> dict:
    """
    Search for organizations (companies, investors, schools).

    Args:
        query: Search query (company name, keyword)
        organization_types: Filter by type ["company", "investor", "school"]
        locations: Filter by location ["United States", "Dubai", etc.]
        categories: Filter by category ["Blockchain", "FinTech", etc.]
        num_results: Number of results (1-100)

    Returns:
        Dict with matching organizations

    Use case: Find companies in a specific sector

    Example:
        search_organizations("blockchain", categories=["FinTech"])
        search_organizations("tokenization", locations=["United Arab Emirates"])
    """
    params = {
        "query": query,
        "limit": min(num_results, 100),
    }

    if organization_types:
        params["organization_types"] = ",".join(organization_types)
    if locations:
        params["location_identifiers"] = ",".join(locations)
    if categories:
        params["categories"] = ",".join(categories)

    data = _make_request("searches/organizations", params)

    organizations = []
    for item in data.get("entities", []):
        props = item.get("properties", {})
        organizations.append({
            "uuid": item.get("uuid"),
            "name": props.get("name"),
            "short_description": props.get("short_description"),
            "description": props.get("description"),
            "founded_on": props.get("founded_on"),
            "location": props.get("location_identifiers", []),
            "categories": props.get("categories", []),
            "num_employees_enum": props.get("num_employees_enum"),
            "website_url": props.get("website_url"),
            "linkedin_url": props.get("linkedin_url"),
            "twitter_url": props.get("twitter_url"),
            "funding_total": props.get("funding_total", {}).get("value_usd"),
            "last_funding_type": props.get("last_funding_type"),
            "last_funding_at": props.get("last_funding_at"),
            "num_funding_rounds": props.get("num_funding_rounds"),
            "ipo_status": props.get("ipo_status"),
            "operating_status": props.get("operating_status"),
        })

    return {
        "query": query,
        "total_results": data.get("count", len(organizations)),
        "organizations": organizations,
    }


def get_organization(identifier: str) -> dict:
    """
    Get detailed information about a specific organization.

    Args:
        identifier: Organization permalink or UUID

    Returns:
        Dict with full organization details

    Use case: Deep dive into a specific company

    Example:
        get_organization("coinbase")
        get_organization("circle-internet-financial")
    """
    data = _make_request(f"entities/organizations/{identifier}")

    props = data.get("properties", {})
    cards = data.get("cards", {})

    # Parse funding rounds
    funding_rounds = []
    for round_data in cards.get("funding_rounds", {}).get("items", []):
        funding_rounds.append({
            "announced_on": round_data.get("announced_on"),
            "funding_type": round_data.get("funding_type"),
            "money_raised": round_data.get("money_raised", {}).get("value_usd"),
            "num_investors": round_data.get("num_investors"),
            "lead_investors": round_data.get("lead_investor_identifiers", []),
        })

    # Parse key people
    founders = []
    for person in cards.get("founders", {}).get("items", []):
        founders.append({
            "name": person.get("identifier", {}).get("value"),
            "title": person.get("title"),
            "linkedin_url": person.get("linkedin_url"),
        })

    # Parse investors
    investors = []
    for investor in cards.get("investors", {}).get("items", []):
        investors.append({
            "name": investor.get("identifier", {}).get("value"),
            "investor_type": investor.get("investor_type"),
            "num_investments": investor.get("num_investments"),
        })

    # Parse acquisitions
    acquisitions = []
    for acq in cards.get("acquisitions", {}).get("items", []):
        acquisitions.append({
            "acquiree_name": acq.get("acquiree_identifier", {}).get("value"),
            "announced_on": acq.get("announced_on"),
            "price": acq.get("price", {}).get("value_usd"),
            "acquisition_type": acq.get("acquisition_type"),
        })

    return {
        "uuid": data.get("uuid"),
        "name": props.get("name"),
        "legal_name": props.get("legal_name"),
        "short_description": props.get("short_description"),
        "description": props.get("description"),

        # Basic info
        "founded_on": props.get("founded_on"),
        "closed_on": props.get("closed_on"),
        "operating_status": props.get("operating_status"),
        "company_type": props.get("company_type"),

        # Location
        "headquarters": props.get("location_identifiers", []),
        "region": props.get("region_id"),
        "country": props.get("country_code"),

        # Categories
        "categories": props.get("categories", []),
        "category_groups": props.get("category_groups", []),

        # Employees
        "num_employees_enum": props.get("num_employees_enum"),

        # Funding
        "funding_total_usd": props.get("funding_total", {}).get("value_usd"),
        "funding_rounds_count": props.get("num_funding_rounds"),
        "last_funding_type": props.get("last_funding_type"),
        "last_funding_at": props.get("last_funding_at"),
        "funding_rounds": funding_rounds,

        # IPO
        "ipo_status": props.get("ipo_status"),
        "went_public_on": props.get("went_public_on"),
        "stock_exchange": props.get("stock_exchange_symbol"),
        "stock_symbol": props.get("stock_symbol"),

        # Revenue (if available)
        "revenue_range": props.get("revenue_range"),
        "estimated_revenue_range": props.get("estimated_revenue_range"),

        # Contact
        "website_url": props.get("website_url"),
        "linkedin_url": props.get("linkedin_url"),
        "twitter_url": props.get("twitter_url"),
        "facebook_url": props.get("facebook_url"),
        "email": props.get("contact_email"),
        "phone": props.get("phone_number"),

        # People
        "founders": founders,
        "num_founders": props.get("num_founders"),

        # Investors
        "investors": investors,
        "num_investors": props.get("num_investors"),

        # Acquisitions
        "acquisitions": acquisitions,
        "num_acquisitions": props.get("num_acquisitions"),

        # Rank
        "rank_org": props.get("rank_org"),
        "rank_org_company": props.get("rank_org_company"),
    }


def get_funding_rounds(organization_id: str, limit: int = 25) -> dict:
    """
    Get funding rounds for an organization.

    Args:
        organization_id: Organization permalink
        limit: Number of rounds to return

    Returns:
        Dict with funding rounds

    Example:
        get_funding_rounds("coinbase")
    """
    params = {
        "field_ids": "announced_on,funding_type,money_raised,num_investors,lead_investor_identifiers,investor_identifiers",
        "limit": limit,
    }

    data = _make_request(f"entities/organizations/{organization_id}/cards/funding_rounds", params)

    rounds = []
    for item in data.get("items", []):
        rounds.append({
            "announced_on": item.get("announced_on"),
            "funding_type": item.get("funding_type"),
            "money_raised_usd": item.get("money_raised", {}).get("value_usd"),
            "num_investors": item.get("num_investors"),
            "lead_investors": [
                inv.get("value") for inv in item.get("lead_investor_identifiers", [])
            ],
            "all_investors": [
                inv.get("value") for inv in item.get("investor_identifiers", [])
            ],
        })

    return {
        "organization": organization_id,
        "total_rounds": len(rounds),
        "funding_rounds": rounds,
    }


def search_investors(query: str = None,
                     investor_types: List[str] = None,
                     locations: List[str] = None,
                     num_results: int = 25) -> dict:
    """
    Search for investors (VCs, angels, accelerators).

    Args:
        query: Search query
        investor_types: ["venture_capital", "angel", "accelerator", "corporate_venture_capital", etc.]
        locations: Filter by location
        num_results: Number of results

    Returns:
        Dict with matching investors

    Example:
        search_investors("blockchain", investor_types=["venture_capital"])
        search_investors(locations=["Dubai"])
    """
    params = {
        "limit": min(num_results, 100),
        "organization_types": "investor",
    }

    if query:
        params["query"] = query
    if investor_types:
        params["investor_types"] = ",".join(investor_types)
    if locations:
        params["location_identifiers"] = ",".join(locations)

    data = _make_request("searches/organizations", params)

    investors = []
    for item in data.get("entities", []):
        props = item.get("properties", {})
        investors.append({
            "uuid": item.get("uuid"),
            "name": props.get("name"),
            "short_description": props.get("short_description"),
            "investor_type": props.get("investor_type"),
            "location": props.get("location_identifiers", []),
            "num_investments": props.get("num_investments"),
            "num_exits": props.get("num_exits"),
            "num_portfolio_organizations": props.get("num_portfolio_organizations"),
            "website_url": props.get("website_url"),
        })

    return {
        "query": query,
        "total_results": data.get("count", len(investors)),
        "investors": investors,
    }


def get_investor(identifier: str) -> dict:
    """
    Get detailed information about an investor.

    Args:
        identifier: Investor permalink or UUID

    Returns:
        Dict with full investor details

    Example:
        get_investor("andreessen-horowitz")
        get_investor("sequoia-capital")
    """
    data = _make_request(f"entities/organizations/{identifier}")

    props = data.get("properties", {})
    cards = data.get("cards", {})

    # Parse investments
    investments = []
    for inv in cards.get("investments", {}).get("items", [])[:50]:
        investments.append({
            "organization": inv.get("organization_identifier", {}).get("value"),
            "funding_round": inv.get("funding_round_identifier", {}).get("value"),
            "announced_on": inv.get("announced_on"),
            "money_invested": inv.get("money_invested", {}).get("value_usd"),
            "is_lead_investor": inv.get("is_lead_investor"),
        })

    return {
        "uuid": data.get("uuid"),
        "name": props.get("name"),
        "short_description": props.get("short_description"),
        "description": props.get("description"),

        "investor_type": props.get("investor_type"),
        "founded_on": props.get("founded_on"),
        "headquarters": props.get("location_identifiers", []),

        "num_investments": props.get("num_investments"),
        "num_exits": props.get("num_exits"),
        "num_portfolio_organizations": props.get("num_portfolio_organizations"),
        "num_funds": props.get("num_funds"),

        "investments": investments,

        "website_url": props.get("website_url"),
        "linkedin_url": props.get("linkedin_url"),
        "twitter_url": props.get("twitter_url"),
    }


def search_funding_rounds(query: str = None,
                          funding_types: List[str] = None,
                          min_amount: int = None,
                          max_amount: int = None,
                          announced_after: str = None,
                          num_results: int = 25) -> dict:
    """
    Search for recent funding rounds.

    Args:
        query: Search query (company name, keyword)
        funding_types: ["seed", "series_a", "series_b", "series_c", "ipo", etc.]
        min_amount: Minimum funding amount in USD
        max_amount: Maximum funding amount in USD
        announced_after: ISO date string (e.g., "2024-01-01")
        num_results: Number of results

    Returns:
        Dict with matching funding rounds

    Example:
        search_funding_rounds(funding_types=["series_a"], min_amount=10000000)
        search_funding_rounds(announced_after="2024-01-01")
    """
    params = {
        "limit": min(num_results, 100),
    }

    if query:
        params["query"] = query
    if funding_types:
        params["funding_types"] = ",".join(funding_types)
    if min_amount:
        params["money_raised.value_usd.gte"] = min_amount
    if max_amount:
        params["money_raised.value_usd.lte"] = max_amount
    if announced_after:
        params["announced_on.gte"] = announced_after

    data = _make_request("searches/funding_rounds", params)

    rounds = []
    for item in data.get("entities", []):
        props = item.get("properties", {})
        rounds.append({
            "uuid": item.get("uuid"),
            "organization": props.get("funded_organization_identifier", {}).get("value"),
            "announced_on": props.get("announced_on"),
            "funding_type": props.get("funding_type"),
            "money_raised_usd": props.get("money_raised", {}).get("value_usd"),
            "num_investors": props.get("num_investors"),
            "lead_investors": [
                inv.get("value") for inv in props.get("lead_investor_identifiers", [])
            ],
        })

    return {
        "query": query,
        "filters": {
            "funding_types": funding_types,
            "min_amount": min_amount,
            "max_amount": max_amount,
            "announced_after": announced_after,
        },
        "total_results": data.get("count", len(rounds)),
        "funding_rounds": rounds,
    }


def search_acquisitions(query: str = None,
                        announced_after: str = None,
                        min_price: int = None,
                        num_results: int = 25) -> dict:
    """
    Search for recent acquisitions.

    Args:
        query: Search query
        announced_after: ISO date string
        min_price: Minimum acquisition price in USD
        num_results: Number of results

    Returns:
        Dict with matching acquisitions

    Example:
        search_acquisitions(query="blockchain", announced_after="2024-01-01")
    """
    params = {
        "limit": min(num_results, 100),
    }

    if query:
        params["query"] = query
    if announced_after:
        params["announced_on.gte"] = announced_after
    if min_price:
        params["price.value_usd.gte"] = min_price

    data = _make_request("searches/acquisitions", params)

    acquisitions = []
    for item in data.get("entities", []):
        props = item.get("properties", {})
        acquisitions.append({
            "uuid": item.get("uuid"),
            "acquirer": props.get("acquirer_identifier", {}).get("value"),
            "acquiree": props.get("acquiree_identifier", {}).get("value"),
            "announced_on": props.get("announced_on"),
            "price_usd": props.get("price", {}).get("value_usd"),
            "acquisition_type": props.get("acquisition_type"),
            "acquisition_status": props.get("acquisition_status"),
        })

    return {
        "query": query,
        "total_results": data.get("count", len(acquisitions)),
        "acquisitions": acquisitions,
    }


# ============ HELPER FUNCTIONS ============

def get_blockchain_companies(num_results: int = 25) -> dict:
    """
    Get blockchain/crypto companies.

    Returns: Companies in Blockchain category
    """
    return search_organizations(
        query="blockchain",
        categories=["Blockchain", "Cryptocurrency", "FinTech"],
        num_results=num_results
    )


def get_rwa_companies(num_results: int = 25) -> dict:
    """
    Get companies working on Real World Asset tokenization.

    Returns: Companies in RWA/tokenization space
    """
    return search_organizations(
        query="tokenization OR 'real world assets' OR RWA",
        categories=["Blockchain", "FinTech", "Asset Management"],
        num_results=num_results
    )


def get_crypto_investors(num_results: int = 25) -> dict:
    """
    Get crypto-focused venture capital firms.

    Returns: VCs investing in crypto/blockchain
    """
    return search_investors(
        query="crypto OR blockchain",
        investor_types=["venture_capital", "corporate_venture_capital"],
        num_results=num_results
    )


def get_recent_crypto_funding(days: int = 30, min_amount: int = 1000000) -> dict:
    """
    Get recent crypto/blockchain funding rounds.

    Args:
        days: Look back period in days
        min_amount: Minimum funding amount

    Returns: Recent funding rounds
    """
    from datetime import datetime, timedelta

    announced_after = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    return search_funding_rounds(
        query="blockchain OR crypto OR web3",
        min_amount=min_amount,
        announced_after=announced_after,
        num_results=50
    )


def format_funding_summary(organization_data: dict) -> str:
    """
    Format funding information as a summary string.

    Args:
        organization_data: Organization data from get_organization

    Returns:
        Formatted funding summary
    """
    total = organization_data.get("funding_total_usd", 0)
    rounds = organization_data.get("funding_rounds_count", 0)
    last_type = organization_data.get("last_funding_type", "Unknown")

    if total:
        if total >= 1_000_000_000:
            total_str = f"${total / 1_000_000_000:.1f}B"
        elif total >= 1_000_000:
            total_str = f"${total / 1_000_000:.1f}M"
        else:
            total_str = f"${total / 1_000:.1f}K"
    else:
        total_str = "Undisclosed"

    return f"Total Funding: {total_str} across {rounds} rounds (Last: {last_type})"


if __name__ == "__main__":
    try:
        print("=== Crunchbase Test ===")
        result = search_organizations("tokenization", num_results=3)
        for org in result.get("organizations", []):
            print(f"\n{org['name']}")
            print(f"  {org.get('short_description', 'N/A')[:80]}")
            print(f"  Funding: ${org.get('funding_total', 'N/A')}")
    except ValueError as e:
        print(f"Error: {e}")
        print("Set CRUNCHBASE_API_KEY environment variable to use this module.")
