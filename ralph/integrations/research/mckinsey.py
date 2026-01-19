# -*- coding: utf-8 -*-
"""
McKinsey & Company Insights Parser

USE FOR:
- McKinsey Global Institute (MGI) research
- Industry insights and analysis
- Digital transformation research
- Strategy frameworks
- CEO/executive surveys

DO NOT USE FOR:
- Macro data (use World Bank, IMF, FRED)
- Real-time market data (use stock/crypto APIs)
- Quick statistics (use structured APIs)

RATE LIMIT: Fair use
API KEY: Not required

Note: McKinsey doesn't have public API, use web search for best results.
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import re

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


BASE_URL = "https://www.mckinsey.com"


# ============ INDUSTRY SECTIONS ============

INDUSTRIES = {
    "financial_services": "/industries/financial-services/our-insights",
    "healthcare": "/industries/healthcare/our-insights",
    "technology": "/industries/technology-media-and-telecommunications/our-insights",
    "retail": "/industries/retail/our-insights",
    "energy": "/industries/oil-and-gas/our-insights",
    "automotive": "/industries/automotive-and-assembly/our-insights",
    "real_estate": "/industries/real-estate/our-insights",
    "private_equity": "/industries/private-equity-and-principal-investors/our-insights",
    "public_sector": "/industries/public-and-social-sector/our-insights",
}

# Featured topics
TOPICS = {
    "ai": "/featured-insights/artificial-intelligence",
    "artificial_intelligence": "/featured-insights/artificial-intelligence",
    "sustainability": "/featured-insights/sustainability",
    "future_of_work": "/featured-insights/future-of-work",
    "digital": "/capabilities/mckinsey-digital/how-we-help-clients",
    "growth": "/capabilities/growth-marketing-and-sales/how-we-help-clients",
}


def get_industry_url(industry: str) -> str:
    """Get URL for industry insights page."""
    path = INDUSTRIES.get(industry.lower().replace(" ", "_"), "")
    return f"{BASE_URL}{path}" if path else None


def get_topic_url(topic: str) -> str:
    """Get URL for topic page."""
    path = TOPICS.get(topic.lower().replace(" ", "_"), "")
    return f"{BASE_URL}{path}" if path else None


# ============ SEARCH GUIDANCE ============

def search_insights(query: str) -> dict:
    """
    Search McKinsey insights.

    Note: McKinsey doesn't have public search API.
    Use WebSearch tool for best results.

    Args:
        query: Search query

    Returns: Search guidance and suggested queries
    """
    return {
        "method": "web_search",
        "query_suggestion": f"site:mckinsey.com {query}",
        "alternative_queries": [
            f"site:mckinsey.com/mgi {query}",  # McKinsey Global Institute
            f"site:mckinsey.com/industries {query}",  # Industry insights
            f"site:mckinsey.com/featured-insights {query}",  # Featured
        ],
        "direct_urls": {
            "mgi_research": f"{BASE_URL}/mgi/our-research",
            "all_insights": f"{BASE_URL}/featured-insights",
        },
    }


def get_mgi_research() -> dict:
    """
    Get McKinsey Global Institute research info.

    Returns: URLs and categories for MGI research

    Use case: Access macro-level research from MGI
    """
    return {
        "name": "McKinsey Global Institute",
        "description": "McKinsey's business and economics research arm",
        "url": f"{BASE_URL}/mgi",
        "research_url": f"{BASE_URL}/mgi/our-research",
        "categories": [
            {
                "name": "Future of Work",
                "url": f"{BASE_URL}/mgi/our-research/future-of-work",
                "description": "Labor markets, automation, skills",
            },
            {
                "name": "Productivity & Growth",
                "url": f"{BASE_URL}/mgi/our-research/productivity-and-growth",
                "description": "Economic growth, productivity trends",
            },
            {
                "name": "Global Economy",
                "url": f"{BASE_URL}/mgi/our-research/global-economy",
                "description": "Trade, capital flows, global trends",
            },
            {
                "name": "Digital Economy",
                "url": f"{BASE_URL}/mgi/our-research/digital-economy",
                "description": "Tech impact on economy, digitization",
            },
        ],
        "note": "Use WebSearch with 'site:mckinsey.com/mgi' for specific topics",
    }


def get_industry_insights(industry: str) -> dict:
    """
    Get industry insights page info.

    Args:
        industry: Industry name (financial_services, healthcare, tech, etc.)

    Returns: URLs and suggested searches for industry

    Use case: Industry-specific research
    """
    url = get_industry_url(industry)

    if not url:
        return {
            "error": f"Industry '{industry}' not found",
            "available_industries": list(INDUSTRIES.keys()),
        }

    return {
        "industry": industry,
        "url": url,
        "search_suggestion": f"site:mckinsey.com/industries/{industry.replace('_', '-')}",
        "note": "Use WebSearch for specific topics within industry",
    }


# ============ POPULAR REPORTS ============

def get_popular_reports() -> dict:
    """
    Get links to popular McKinsey report series.

    Returns: URLs to major recurring reports
    """
    return {
        "global_surveys": {
            "name": "McKinsey Global Surveys",
            "description": "Executive and business leader surveys",
            "url": f"{BASE_URL}/featured-insights/mckinsey-global-surveys",
        },
        "state_of_ai": {
            "name": "The State of AI",
            "description": "Annual AI adoption survey",
            "url": f"{BASE_URL}/capabilities/quantumblack/our-insights",
        },
        "women_in_workplace": {
            "name": "Women in the Workplace",
            "description": "Annual diversity study with LeanIn",
            "url": f"{BASE_URL}/featured-insights/diversity-and-inclusion/women-in-the-workplace",
        },
        "economic_conditions": {
            "name": "Economic Conditions Outlook",
            "description": "Quarterly executive survey on economy",
            "search": "site:mckinsey.com economic conditions outlook",
        },
        "consumer_sentiment": {
            "name": "Consumer Sentiment Survey",
            "description": "Consumer behavior and sentiment tracking",
            "search": "site:mckinsey.com consumer sentiment survey",
        },
    }


def get_ai_research() -> dict:
    """
    Get AI/ML research resources.

    Returns: URLs for AI-related research
    """
    return {
        "quantumblack": {
            "name": "QuantumBlack (McKinsey AI)",
            "url": f"{BASE_URL}/capabilities/quantumblack/our-insights",
            "description": "AI and advanced analytics insights",
        },
        "generative_ai": {
            "name": "Generative AI Research",
            "search": "site:mckinsey.com generative AI",
            "description": "GenAI impact on business and economy",
        },
        "ai_adoption": {
            "name": "AI Adoption Studies",
            "search": "site:mckinsey.com state of AI",
            "description": "Enterprise AI adoption trends",
        },
    }


# ============ WEB SCRAPING (if BeautifulSoup available) ============

def fetch_insights_page(url: str, limit: int = 10) -> list:
    """
    Fetch and parse McKinsey insights page.

    Note: Basic scraping, may not work if page structure changes.
    Prefer using WebSearch tool for reliability.

    Args:
        url: McKinsey page URL
        limit: Max articles to extract

    Returns: List of articles (basic info)
    """
    if not HAS_BS4:
        return [{"error": "BeautifulSoup not installed. Use: pip install beautifulsoup4"}]

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        articles = []

        # Try common article patterns
        for selector in ['.article-block', '.insight-card', '.content-block', 'article']:
            items = soup.select(selector)
            if items:
                for item in items[:limit]:
                    title_el = item.select_one('h2, h3, .title, .headline')
                    link_el = item.select_one('a')

                    if title_el and link_el:
                        href = link_el.get('href', '')
                        if href and not href.startswith('http'):
                            href = BASE_URL + href

                        articles.append({
                            "title": title_el.get_text(strip=True),
                            "url": href,
                            "source": "McKinsey",
                        })

                break  # Use first successful selector

        return articles if articles else [{"note": "No articles found. Page structure may have changed."}]

    except Exception as e:
        return [{"error": f"Failed to fetch page: {str(e)}"}]


# ============ HELPER FUNCTIONS ============

def get_all_industries() -> list:
    """Get list of available industries."""
    return list(INDUSTRIES.keys())


def get_all_topics() -> list:
    """Get list of featured topics."""
    return list(TOPICS.keys())


def format_search_guidance(query: str) -> str:
    """
    Format search guidance as text.

    Returns: Instructions for searching McKinsey content
    """
    guidance = search_insights(query)

    lines = [
        f"McKinsey Search Guidance for: '{query}'",
        "=" * 50,
        "",
        "Recommended WebSearch query:",
        f"  {guidance['query_suggestion']}",
        "",
        "Alternative queries:",
    ]

    for q in guidance['alternative_queries']:
        lines.append(f"  - {q}")

    lines.extend([
        "",
        "Direct URLs:",
        f"  MGI Research: {guidance['direct_urls']['mgi_research']}",
        f"  All Insights: {guidance['direct_urls']['all_insights']}",
    ])

    return "\n".join(lines)


if __name__ == "__main__":
    print("=== McKinsey Industries ===")
    for ind in get_all_industries():
        print(f"  - {ind}")

    print("\n=== McKinsey Topics ===")
    for topic in get_all_topics():
        print(f"  - {topic}")

    print("\n=== MGI Research ===")
    mgi = get_mgi_research()
    print(f"URL: {mgi['url']}")
    for cat in mgi['categories']:
        print(f"  - {cat['name']}: {cat['description']}")

    print("\n=== Search Example ===")
    print(format_search_guidance("AI productivity impact"))
