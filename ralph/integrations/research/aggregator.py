# -*- coding: utf-8 -*-
"""
Research Aggregator - Multi-Source Search and Data Collection

USE FOR:
- Searching across multiple research sources
- Combining macro data from World Bank + IMF
- Getting industry research from multiple consulting firms
- Building comprehensive research briefs

This is the main entry point for research data collection.
"""

from typing import List, Dict, Optional
from datetime import datetime

from . import worldbank
from . import imf
from . import deloitte
from . import mckinsey
from . import goldman


# ============ SOURCE REGISTRY ============

SOURCES = {
    # Structured Data APIs
    "worldbank": {
        "name": "World Bank",
        "type": "api",
        "data": ["GDP", "population", "inflation", "trade", "development"],
        "module": worldbank,
    },
    "imf": {
        "name": "IMF",
        "type": "api",
        "data": ["GDP forecasts", "inflation forecasts", "economic outlook"],
        "module": imf,
    },

    # Consulting Firms
    "deloitte": {
        "name": "Deloitte Insights",
        "type": "rss",
        "data": ["tech trends", "industry research", "surveys"],
        "module": deloitte,
    },
    "mckinsey": {
        "name": "McKinsey",
        "type": "web",
        "data": ["MGI research", "industry insights", "strategy"],
        "module": mckinsey,
    },
    "goldman": {
        "name": "Goldman Sachs",
        "type": "web",
        "data": ["market outlook", "macro research", "Top of Mind"],
        "module": goldman,
    },
}


# ============ MULTI-SOURCE SEARCH ============

def search(query: str, sources: List[str] = None) -> dict:
    """
    Search across multiple research sources.

    Args:
        query: Search query
        sources: List of source names (default: all)

    Returns:
        Dict with search guidance for each source

    Use case: Find research across multiple sources
    """
    if sources is None:
        sources = list(SOURCES.keys())

    results = {
        "query": query,
        "timestamp": datetime.now().isoformat(),
        "sources": {},
    }

    for source in sources:
        if source not in SOURCES:
            results["sources"][source] = {"error": f"Unknown source: {source}"}
            continue

        source_info = SOURCES[source]
        module = source_info["module"]

        if hasattr(module, "search_insights"):
            results["sources"][source] = module.search_insights(query)
        else:
            results["sources"][source] = {
                "note": f"Use WebSearch with site-specific query for {source_info['name']}",
            }

    return results


def get_web_search_queries(query: str, sources: List[str] = None) -> list:
    """
    Generate web search queries for all sources.

    Args:
        query: Base search query
        sources: Sources to search (default: consulting firms)

    Returns:
        List of site-specific search queries

    Use case: Prepare queries for WebSearch tool
    """
    if sources is None:
        sources = ["mckinsey", "deloitte", "goldman"]

    site_mappings = {
        "mckinsey": "mckinsey.com",
        "deloitte": "deloitte.com/insights",
        "goldman": "goldmansachs.com/insights",
        "worldbank": "worldbank.org",
        "imf": "imf.org",
    }

    queries = []
    for source in sources:
        site = site_mappings.get(source)
        if site:
            queries.append({
                "source": source,
                "query": f"site:{site} {query}",
            })

    return queries


# ============ MACRO DATA AGGREGATION ============

def get_macro_data(country: str = "USA", indicators: List[str] = None) -> dict:
    """
    Get macro data from multiple sources.

    Args:
        country: Country code
        indicators: List of indicators (default: key macro)

    Returns:
        Combined data from World Bank and IMF

    Use case: Comprehensive macro analysis
    """
    if indicators is None:
        indicators = ["gdp", "gdp_growth", "inflation", "unemployment"]

    result = {
        "country": country,
        "timestamp": datetime.now().isoformat(),
        "worldbank": {},
        "imf": {},
    }

    # World Bank data (historical)
    for ind in indicators:
        try:
            data = worldbank.get_indicator(ind, country)
            if "error" not in data:
                result["worldbank"][ind] = data
        except Exception as e:
            result["worldbank"][ind] = {"error": str(e)}

    # IMF data (forecasts)
    try:
        outlook = imf.get_economic_outlook(country)
        result["imf"] = outlook
    except Exception as e:
        result["imf"]["error"] = str(e)

    return result


def get_country_profile(country: str) -> dict:
    """
    Get comprehensive country profile.

    Combines World Bank historical data with IMF forecasts.

    Use case: Country research, investment analysis
    """
    result = {
        "country": country,
        "timestamp": datetime.now().isoformat(),
    }

    # World Bank profile
    try:
        wb_profile = worldbank.get_country_profile(country)
        result["historical"] = wb_profile.get("indicators", {})
    except Exception as e:
        result["historical_error"] = str(e)

    # IMF outlook
    try:
        imf_outlook = imf.get_economic_outlook(country)
        result["forecast"] = imf_outlook.get("indicators", {})
    except Exception as e:
        result["forecast_error"] = str(e)

    return result


# ============ INDUSTRY RESEARCH ============

def get_industry_research(industry: str) -> dict:
    """
    Get industry research from multiple sources.

    Args:
        industry: Industry name (tech, finance, healthcare, energy, etc.)

    Returns:
        Research guidance from consulting firms

    Use case: Industry analysis, sector research
    """
    industry_mappings = {
        "tech": ["technology", "tech", "digital"],
        "technology": ["technology", "tech", "digital"],
        "finance": ["financial_services", "finance", "banking"],
        "financial_services": ["financial_services", "finance", "banking"],
        "healthcare": ["healthcare", "life_sciences", "health"],
        "energy": ["energy", "oil_and_gas", "sustainability"],
        "retail": ["retail", "consumer"],
    }

    search_terms = industry_mappings.get(industry.lower(), [industry])

    result = {
        "industry": industry,
        "timestamp": datetime.now().isoformat(),
        "sources": {},
    }

    # Deloitte RSS
    for term in search_terms:
        try:
            articles = deloitte.get_latest(term, limit=5)
            if articles and "error" not in articles[0]:
                result["sources"]["deloitte"] = {
                    "articles": articles,
                    "category": term,
                }
                break
        except:
            pass

    # McKinsey guidance
    result["sources"]["mckinsey"] = mckinsey.get_industry_insights(industry)

    # Goldman guidance
    result["sources"]["goldman"] = {
        "search": f"site:goldmansachs.com/insights {industry}",
        "url": f"https://www.goldmansachs.com/insights/topics/{industry}",
    }

    return result


# ============ RESEARCH BRIEF BUILDER ============

def build_research_brief(topic: str, include_macro: bool = True,
                         country: str = "USA") -> dict:
    """
    Build comprehensive research brief on a topic.

    Args:
        topic: Research topic
        include_macro: Include macro data
        country: Country focus

    Returns:
        Structured research brief with multiple sources

    Use case: Starting point for deep research
    """
    brief = {
        "topic": topic,
        "country": country,
        "timestamp": datetime.now().isoformat(),
        "sections": {},
    }

    # 1. Web search queries
    brief["sections"]["search_queries"] = get_web_search_queries(topic)

    # 2. Deloitte latest (if relevant category exists)
    try:
        deloitte_articles = deloitte.get_latest("all", limit=10)
        # Filter by topic
        relevant = [a for a in deloitte_articles
                    if topic.lower() in a.get("title", "").lower()
                    or topic.lower() in a.get("summary", "").lower()]
        if relevant:
            brief["sections"]["deloitte_insights"] = relevant[:5]
    except:
        pass

    # 3. McKinsey guidance
    brief["sections"]["mckinsey"] = mckinsey.search_insights(topic)

    # 4. Goldman guidance
    brief["sections"]["goldman"] = goldman.search_insights(topic)

    # 5. Macro data (if requested)
    if include_macro:
        try:
            brief["sections"]["macro_data"] = worldbank.get_macro_summary(country)
        except Exception as e:
            brief["sections"]["macro_data"] = {"error": str(e)}

    return brief


# ============ HELPER FUNCTIONS ============

def get_available_sources() -> dict:
    """
    Get list of available research sources.

    Returns: Source info and capabilities
    """
    return {
        name: {
            "name": info["name"],
            "type": info["type"],
            "data_types": info["data"],
        }
        for name, info in SOURCES.items()
    }


def get_source_for_data(data_type: str) -> list:
    """
    Find best source for specific data type.

    Args:
        data_type: Type of data needed

    Returns: Ranked list of sources
    """
    data_type_lower = data_type.lower()

    recommendations = []

    for name, info in SOURCES.items():
        for data in info["data"]:
            if data_type_lower in data.lower():
                recommendations.append({
                    "source": name,
                    "name": info["name"],
                    "match": data,
                })

    return recommendations


def format_research_brief(brief: dict) -> str:
    """
    Format research brief as readable text.

    Returns: Formatted brief string
    """
    lines = [
        f"Research Brief: {brief['topic']}",
        f"Country Focus: {brief['country']}",
        f"Generated: {brief['timestamp']}",
        "=" * 60,
    ]

    # Search queries
    if "search_queries" in brief["sections"]:
        lines.append("\n## Web Search Queries")
        for q in brief["sections"]["search_queries"]:
            lines.append(f"  [{q['source']}] {q['query']}")

    # Deloitte
    if "deloitte_insights" in brief["sections"]:
        lines.append("\n## Deloitte Insights")
        for a in brief["sections"]["deloitte_insights"]:
            lines.append(f"  - {a.get('title', 'N/A')}")
            lines.append(f"    {a.get('url', '')}")

    # Macro
    if "macro_data" in brief["sections"]:
        lines.append("\n## Macro Data")
        macro = brief["sections"]["macro_data"]
        if "data" in macro:
            for name, data in macro["data"].items():
                lines.append(f"  {name}: {data.get('formatted', 'N/A')}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== Available Research Sources ===")
    sources = get_available_sources()
    for name, info in sources.items():
        print(f"\n{info['name']} ({info['type']})")
        print(f"  Data: {', '.join(info['data_types'])}")

    print("\n=== Search Queries for 'AI productivity' ===")
    queries = get_web_search_queries("AI productivity")
    for q in queries:
        print(f"  [{q['source']}] {q['query']}")

    print("\n=== Building Research Brief ===")
    brief = build_research_brief("artificial intelligence", include_macro=False)
    print(f"Sections: {list(brief['sections'].keys())}")
