# -*- coding: utf-8 -*-
"""
Wikidata API Integration

USE FOR:
- Structured entity data (people, companies, places, concepts)
- Relationships between entities
- Official identifiers (stock tickers, ISIN, LEI)
- Dates and facts (founding date, CEO, headquarters)
- Cross-references (Wikipedia, official websites)
- Semantic queries (SPARQL)

DO NOT USE FOR:
- Long-form text (use Wikipedia)
- Real-time data (use dedicated APIs)
- Financial data (use yfinance, coingecko)
- News (use serper)

RATE LIMIT: Fair use
API KEY: Not required

Official docs: https://www.wikidata.org/wiki/Wikidata:Data_access
"""

import requests
from typing import List, Dict, Optional, Union
from urllib.parse import quote

BASE_URL = "https://www.wikidata.org/w/api.php"
SPARQL_URL = "https://query.wikidata.org/sparql"

# Required User-Agent for Wikidata/Wikimedia APIs
HEADERS = {
    "User-Agent": "RalphResearch/1.0 (https://github.com/SoSmDe/Ralph_research; research bot)"
}


# Common property IDs
PROPERTIES = {
    # Identifiers
    "instance_of": "P31",
    "subclass_of": "P279",
    "image": "P18",
    "logo": "P154",
    "official_website": "P856",

    # Organization
    "founded": "P571",
    "founder": "P112",
    "ceo": "P169",
    "headquarters": "P159",
    "industry": "P452",
    "employees": "P1128",
    "revenue": "P2139",
    "parent_org": "P749",
    "subsidiary": "P355",

    # Financial
    "stock_exchange": "P414",
    "ticker_symbol": "P249",
    "isin": "P946",
    "lei": "P1278",
    "market_cap": "P2226",

    # Person
    "birth_date": "P569",
    "death_date": "P570",
    "nationality": "P27",
    "occupation": "P106",
    "employer": "P108",
    "education": "P69",
    "net_worth": "P2218",

    # Location
    "country": "P17",
    "capital": "P36",
    "population": "P1082",
    "area": "P2046",
    "coordinates": "P625",
    "timezone": "P421",

    # Links
    "wikipedia": "P373",
    "twitter": "P2002",
    "linkedin": "P4264",
    "github": "P2037",
}


def get_entity(entity_id: str, languages: List[str] = None) -> dict:
    """
    Get full entity data from Wikidata.

    Args:
        entity_id: Wikidata entity ID (e.g., "Q312" for Apple Inc.)
        languages: List of language codes for labels (default: ["en", "ru"])

    Returns:
        Dict with entity data, labels, descriptions, aliases, claims

    Use case: Get structured data about any entity

    Example:
        get_entity("Q312")  # Apple Inc.
        get_entity("Q2283")  # Microsoft
        get_entity("Q20826")  # Satoshi Nakamoto
    """
    if languages is None:
        languages = ["en", "ru"]

    params = {
        "action": "wbgetentities",
        "ids": entity_id,
        "format": "json",
        "languages": "|".join(languages),
        "props": "labels|descriptions|aliases|claims|sitelinks",
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    entities = data.get("entities", {})
    if entity_id not in entities:
        return {"error": "Entity not found", "entity_id": entity_id}

    entity = entities[entity_id]

    # Parse labels
    labels = {}
    for lang, label_data in entity.get("labels", {}).items():
        labels[lang] = label_data.get("value")

    # Parse descriptions
    descriptions = {}
    for lang, desc_data in entity.get("descriptions", {}).items():
        descriptions[lang] = desc_data.get("value")

    # Parse aliases
    aliases = {}
    for lang, alias_list in entity.get("aliases", {}).items():
        aliases[lang] = [a.get("value") for a in alias_list]

    # Parse important claims
    claims = entity.get("claims", {})
    properties = _extract_key_properties(claims)

    # Get Wikipedia link
    sitelinks = entity.get("sitelinks", {})
    wikipedia_links = {}
    for site, link_data in sitelinks.items():
        if site.endswith("wiki") and not site.startswith("common"):
            lang = site.replace("wiki", "")
            wikipedia_links[lang] = {
                "title": link_data.get("title"),
                "url": f"https://{lang}.wikipedia.org/wiki/{quote(link_data.get('title', ''))}"
            }

    return {
        "id": entity_id,
        "type": entity.get("type"),
        "labels": labels,
        "descriptions": descriptions,
        "aliases": aliases,
        "properties": properties,
        "wikipedia_links": wikipedia_links,
        "wikidata_url": f"https://www.wikidata.org/wiki/{entity_id}",
    }


def _extract_key_properties(claims: dict) -> dict:
    """Extract commonly useful properties from claims."""
    properties = {}

    for prop_name, prop_id in PROPERTIES.items():
        if prop_id in claims:
            values = []
            for claim in claims[prop_id]:
                value = _parse_claim_value(claim)
                if value:
                    values.append(value)
            if values:
                properties[prop_name] = values[0] if len(values) == 1 else values

    return properties


def _parse_claim_value(claim: dict) -> Optional[Union[str, dict]]:
    """Parse a single claim value."""
    mainsnak = claim.get("mainsnak", {})
    datavalue = mainsnak.get("datavalue", {})
    datatype = mainsnak.get("datatype")

    if not datavalue:
        return None

    value = datavalue.get("value")

    if datatype == "wikibase-item":
        # Reference to another entity
        return {
            "id": value.get("id"),
            "type": "entity",
        }
    elif datatype == "time":
        # Date/time value
        time_str = value.get("time", "")
        # Convert from "+2024-01-15T00:00:00Z" format
        return time_str.lstrip("+").split("T")[0] if time_str else None
    elif datatype == "quantity":
        # Numeric value
        amount = value.get("amount", "").lstrip("+")
        unit = value.get("unit", "")
        if unit and "wikidata" in unit:
            unit_id = unit.split("/")[-1]
            return {"amount": amount, "unit_id": unit_id}
        return amount
    elif datatype == "monolingualtext":
        return value.get("text")
    elif datatype == "string" or datatype == "url" or datatype == "external-id":
        return value
    elif datatype == "globe-coordinate":
        return {
            "latitude": value.get("latitude"),
            "longitude": value.get("longitude"),
        }
    else:
        return str(value) if value else None


def search_entities(query: str, entity_type: str = None,
                    language: str = "en", limit: int = 10) -> dict:
    """
    Search for entities by text.

    Args:
        query: Search query
        entity_type: Filter by type ("item", "property", "lexeme")
        language: Language for search
        limit: Maximum results

    Returns:
        Dict with matching entities

    Use case: Find Wikidata ID for an entity

    Example:
        search_entities("Apple")
        search_entities("Ethereum", limit=5)
        search_entities("Vitalik Buterin")
    """
    params = {
        "action": "wbsearchentities",
        "search": query,
        "format": "json",
        "language": language,
        "limit": min(limit, 50),
    }

    if entity_type:
        params["type"] = entity_type

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("search", []):
        results.append({
            "id": item.get("id"),
            "label": item.get("label"),
            "description": item.get("description"),
            "url": item.get("concepturi"),
        })

    return {
        "query": query,
        "total_results": len(results),
        "results": results,
    }


def get_properties(entity_id: str, property_ids: List[str] = None) -> dict:
    """
    Get specific properties for an entity.

    Args:
        entity_id: Wikidata entity ID
        property_ids: List of property IDs to fetch (e.g., ["P571", "P112"])
                     If None, fetches all common properties

    Returns:
        Dict with requested properties

    Use case: Get specific facts about an entity

    Example:
        get_properties("Q312", ["P571", "P112", "P169"])  # Apple: founded, founder, CEO
    """
    entity = get_entity(entity_id)

    if "error" in entity:
        return entity

    if property_ids:
        # Filter to requested properties only
        props = {}
        all_props = entity.get("properties", {})

        # Map property IDs to names
        id_to_name = {v: k for k, v in PROPERTIES.items()}

        for pid in property_ids:
            prop_name = id_to_name.get(pid, pid)
            if prop_name in all_props:
                props[prop_name] = all_props[prop_name]
            elif pid in all_props:
                props[pid] = all_props[pid]

        return {
            "id": entity_id,
            "label": entity.get("labels", {}).get("en"),
            "properties": props,
        }

    return {
        "id": entity_id,
        "label": entity.get("labels", {}).get("en"),
        "properties": entity.get("properties", {}),
    }


def sparql_query(query: str) -> dict:
    """
    Execute a SPARQL query against Wikidata.

    Args:
        query: SPARQL query string

    Returns:
        Dict with query results

    Use case: Complex semantic queries

    Example:
        sparql_query('''
            SELECT ?company ?companyLabel WHERE {
                ?company wdt:P31 wd:Q891723.  # instance of: public company
                ?company wdt:P17 wd:Q30.      # country: United States
                SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
            }
            LIMIT 10
        ''')
    """
    headers = {
        "Accept": "application/sparql-results+json",
        "User-Agent": "RalphResearch/1.0",
    }

    response = requests.get(
        SPARQL_URL,
        params={"query": query},
        headers=headers
    )
    response.raise_for_status()
    data = response.json()

    # Parse results
    results = []
    bindings = data.get("results", {}).get("bindings", [])

    for binding in bindings:
        row = {}
        for var, value in binding.items():
            row[var] = value.get("value")
        results.append(row)

    return {
        "query": query[:100] + "..." if len(query) > 100 else query,
        "total_results": len(results),
        "results": results,
    }


# ============ HELPER FUNCTIONS ============

def get_company_info(company_name: str) -> dict:
    """
    Get structured info about a company.

    Args:
        company_name: Company name to search

    Returns:
        Dict with company data (founded, CEO, ticker, etc.)

    Example:
        get_company_info("Apple")
        get_company_info("MicroStrategy")
    """
    # Search for the company
    search_result = search_entities(company_name, limit=5)

    if not search_result.get("results"):
        return {"error": "Company not found", "query": company_name}

    # Get the first result
    entity_id = search_result["results"][0]["id"]

    # Get full entity data
    entity = get_entity(entity_id)

    # Extract company-specific properties
    props = entity.get("properties", {})

    return {
        "id": entity_id,
        "name": entity.get("labels", {}).get("en"),
        "description": entity.get("descriptions", {}).get("en"),
        "founded": props.get("founded"),
        "founder": props.get("founder"),
        "ceo": props.get("ceo"),
        "headquarters": props.get("headquarters"),
        "industry": props.get("industry"),
        "employees": props.get("employees"),
        "ticker_symbol": props.get("ticker_symbol"),
        "stock_exchange": props.get("stock_exchange"),
        "official_website": props.get("official_website"),
        "wikidata_url": entity.get("wikidata_url"),
        "wikipedia": entity.get("wikipedia_links", {}).get("en", {}).get("url"),
    }


def get_person_info(person_name: str) -> dict:
    """
    Get structured info about a person.

    Args:
        person_name: Person name to search

    Returns:
        Dict with person data

    Example:
        get_person_info("Elon Musk")
        get_person_info("Satoshi Nakamoto")
    """
    search_result = search_entities(person_name, limit=5)

    if not search_result.get("results"):
        return {"error": "Person not found", "query": person_name}

    entity_id = search_result["results"][0]["id"]
    entity = get_entity(entity_id)
    props = entity.get("properties", {})

    return {
        "id": entity_id,
        "name": entity.get("labels", {}).get("en"),
        "description": entity.get("descriptions", {}).get("en"),
        "birth_date": props.get("birth_date"),
        "nationality": props.get("nationality"),
        "occupation": props.get("occupation"),
        "employer": props.get("employer"),
        "education": props.get("education"),
        "net_worth": props.get("net_worth"),
        "twitter": props.get("twitter"),
        "wikidata_url": entity.get("wikidata_url"),
        "wikipedia": entity.get("wikipedia_links", {}).get("en", {}).get("url"),
    }


def get_crypto_info(crypto_name: str) -> dict:
    """
    Get structured info about a cryptocurrency.

    Args:
        crypto_name: Cryptocurrency name

    Returns:
        Dict with crypto data

    Example:
        get_crypto_info("Bitcoin")
        get_crypto_info("Ethereum")
    """
    search_result = search_entities(crypto_name, limit=5)

    if not search_result.get("results"):
        return {"error": "Cryptocurrency not found", "query": crypto_name}

    entity_id = search_result["results"][0]["id"]
    entity = get_entity(entity_id)
    props = entity.get("properties", {})

    return {
        "id": entity_id,
        "name": entity.get("labels", {}).get("en"),
        "description": entity.get("descriptions", {}).get("en"),
        "founded": props.get("founded"),
        "founder": props.get("founder"),
        "official_website": props.get("official_website"),
        "github": props.get("github"),
        "wikidata_url": entity.get("wikidata_url"),
        "wikipedia": entity.get("wikipedia_links", {}).get("en", {}).get("url"),
    }


def list_properties() -> dict:
    """
    List available property mappings.

    Returns:
        Dict of property names and IDs
    """
    return {
        "properties": PROPERTIES,
        "total": len(PROPERTIES),
    }


if __name__ == "__main__":
    print("=== Wikidata Search Test ===")
    result = search_entities("Bitcoin", limit=3)
    for r in result.get("results", []):
        print(f"\n{r['id']}: {r['label']}")
        print(f"  {r.get('description', '')}")

    print("\n=== Company Info ===")
    company = get_company_info("Apple")
    print(f"Name: {company.get('name')}")
    print(f"Founded: {company.get('founded')}")
    print(f"CEO: {company.get('ceo')}")
