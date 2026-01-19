# -*- coding: utf-8 -*-
"""
Goldman Sachs Public Research Parser

USE FOR:
- Market insights and analysis
- Economic outlook
- Thematic research
- "Top of Mind" series (flagship macro reports)
- Sustainability research

DO NOT USE FOR:
- Macro data (use World Bank, IMF, FRED)
- Stock prices (use yfinance)
- Real-time quotes (use Finnhub)
- Full research reports (paywall)

RATE LIMIT: Fair use
API KEY: Not required

Note: Only public insights are accessible. Full research requires subscription.
"""

import requests
from typing import List, Dict, Optional
import re

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


BASE_URL = "https://www.goldmansachs.com"


# ============ INSIGHT CATEGORIES ============

CATEGORIES = {
    "all": "/insights",
    "markets": "/insights/topics/markets",
    "economic_outlook": "/insights/topics/economic-outlook",
    "sustainability": "/insights/topics/sustainability",
    "technology": "/insights/topics/technology",
    "careers": "/insights/topics/careers-at-goldman-sachs",
}


# ============ FLAGSHIP SERIES ============

SERIES = {
    "top_of_mind": {
        "name": "Top of Mind",
        "description": "Flagship macro research series covering major market themes",
        "url": f"{BASE_URL}/insights/series/top-of-mind",
        "frequency": "Monthly",
    },
    "briefings": {
        "name": "Goldman Sachs Briefings",
        "description": "Quick insights on current market events",
        "url": f"{BASE_URL}/insights/series/gs-briefings",
        "frequency": "Weekly",
    },
    "exchanges": {
        "name": "Exchanges at Goldman Sachs",
        "description": "Podcast and video series with experts",
        "url": f"{BASE_URL}/insights/series/exchanges-at-goldman-sachs",
        "frequency": "Weekly",
    },
    "carbonomics": {
        "name": "Carbonomics",
        "description": "Climate and sustainability research",
        "url": f"{BASE_URL}/insights/series/carbonomics",
        "frequency": "Periodic",
    },
}


def search_insights(query: str) -> dict:
    """
    Search Goldman Sachs insights.

    Note: Use WebSearch for best results.

    Args:
        query: Search query

    Returns: Search guidance
    """
    return {
        "method": "web_search",
        "query_suggestion": f"site:goldmansachs.com/insights {query}",
        "alternative_queries": [
            f"site:goldmansachs.com/insights/topics/markets {query}",
            f"site:goldmansachs.com/insights/topics/economic-outlook {query}",
        ],
        "categories": list(CATEGORIES.keys()),
    }


def get_category_url(category: str) -> str:
    """Get URL for insights category."""
    path = CATEGORIES.get(category.lower(), CATEGORIES["all"])
    return f"{BASE_URL}{path}" if not path.startswith("http") else path


def get_category_insights(category: str) -> dict:
    """
    Get category insights info.

    Args:
        category: Category name (markets, economic_outlook, sustainability, etc.)

    Returns: Category info and search guidance
    """
    url = get_category_url(category)

    return {
        "category": category,
        "url": url,
        "search_suggestion": f"site:goldmansachs.com/insights/topics/{category.replace('_', '-')}",
        "note": "Use WebSearch for specific topics",
    }


def get_flagship_series() -> dict:
    """
    Get Goldman Sachs flagship research series.

    Returns: Info about major recurring research

    Use case: Access high-quality macro research
    """
    return {
        "series": SERIES,
        "recommendation": "Top of Mind series is their flagship macro research",
        "note": "Some content may require registration",
    }


def get_top_of_mind() -> dict:
    """
    Get "Top of Mind" series info.

    This is Goldman's flagship macro research series covering
    major market themes and economic issues.

    Returns: Series info and search guidance
    """
    return {
        "name": "Top of Mind",
        "description": "Goldman Sachs flagship macro research covering major market themes",
        "url": SERIES["top_of_mind"]["url"],
        "frequency": "Monthly",
        "topics_covered": [
            "Macro economic trends",
            "Market analysis",
            "Geopolitical issues",
            "Sector deep-dives",
        ],
        "search_suggestion": "site:goldmansachs.com/insights/series/top-of-mind",
        "note": "High-quality macro analysis, often cited in financial press",
    }


def get_market_outlook() -> dict:
    """
    Get market outlook resources.

    Returns: URLs and search guidance for market research
    """
    return {
        "economic_outlook": {
            "url": f"{BASE_URL}/insights/topics/economic-outlook",
            "search": "site:goldmansachs.com economic outlook 2024",
        },
        "market_outlook": {
            "url": f"{BASE_URL}/insights/topics/markets",
            "search": "site:goldmansachs.com market outlook",
        },
        "interest_rates": {
            "search": "site:goldmansachs.com interest rates forecast",
        },
        "equities": {
            "search": "site:goldmansachs.com equity market outlook",
        },
    }


def get_sustainability_research() -> dict:
    """
    Get sustainability/ESG research resources.

    Returns: URLs for sustainability research
    """
    return {
        "main_page": f"{BASE_URL}/insights/topics/sustainability",
        "carbonomics": {
            "name": "Carbonomics",
            "url": SERIES["carbonomics"]["url"],
            "description": "Deep research on climate economics and net zero transition",
        },
        "search_suggestions": [
            "site:goldmansachs.com carbonomics",
            "site:goldmansachs.com net zero",
            "site:goldmansachs.com ESG investing",
        ],
    }


# ============ WEB SCRAPING (if BeautifulSoup available) ============

def fetch_insights_page(url: str = None, limit: int = 10) -> list:
    """
    Fetch and parse Goldman insights page.

    Note: Basic scraping, may not work if page structure changes.
    Prefer using WebSearch tool for reliability.

    Args:
        url: Page URL (default: main insights page)
        limit: Max articles

    Returns: List of articles (basic info)
    """
    if not HAS_BS4:
        return [{"error": "BeautifulSoup not installed"}]

    if url is None:
        url = f"{BASE_URL}/insights"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        articles = []

        # Try common article patterns
        for item in soup.select('.article-block, .insight-card, article, .card')[:limit]:
            title_el = item.select_one('h2, h3, .title, .headline')
            link_el = item.select_one('a')
            date_el = item.select_one('.date, time, .timestamp')

            if title_el:
                href = ""
                if link_el:
                    href = link_el.get('href', '')
                    if href and not href.startswith('http'):
                        href = BASE_URL + href

                articles.append({
                    "title": title_el.get_text(strip=True),
                    "url": href,
                    "date": date_el.get_text(strip=True) if date_el else "",
                    "source": "Goldman Sachs",
                })

        return articles if articles else [{"note": "No articles found"}]

    except Exception as e:
        return [{"error": f"Failed to fetch: {str(e)}"}]


# ============ HELPER FUNCTIONS ============

def get_all_categories() -> list:
    """Get list of available categories."""
    return list(CATEGORIES.keys())


def format_search_guidance(query: str) -> str:
    """
    Format search guidance as text.

    Returns: Instructions for searching Goldman content
    """
    guidance = search_insights(query)

    lines = [
        f"Goldman Sachs Search Guidance for: '{query}'",
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
        "Available categories:",
        ", ".join(guidance['categories']),
    ])

    return "\n".join(lines)


def get_research_overview() -> dict:
    """
    Get overview of available Goldman research.

    Returns: Summary of research resources
    """
    return {
        "source": "Goldman Sachs Insights",
        "url": f"{BASE_URL}/insights",
        "categories": list(CATEGORIES.keys()),
        "flagship_series": list(SERIES.keys()),
        "best_for": [
            "Macro market analysis",
            "Economic outlook",
            "Thematic research (AI, climate, etc.)",
            "Investment themes",
        ],
        "note": "Full research reports require subscription. Public insights are summarized versions.",
    }


if __name__ == "__main__":
    print("=== Goldman Sachs Research Overview ===")
    overview = get_research_overview()
    print(f"URL: {overview['url']}")
    print(f"Categories: {', '.join(overview['categories'])}")
    print(f"Flagship series: {', '.join(overview['flagship_series'])}")

    print("\n=== Top of Mind Series ===")
    tom = get_top_of_mind()
    print(f"Description: {tom['description']}")
    print(f"URL: {tom['url']}")

    print("\n=== Search Example ===")
    print(format_search_guidance("interest rates 2024"))
