# -*- coding: utf-8 -*-
"""
Wikipedia API Integration

USE FOR:
- General knowledge lookups
- Topic summaries and definitions
- Background research on concepts
- Historical facts and timelines
- References and citations from articles
- Cross-language article lookup

DO NOT USE FOR:
- Real-time data (use news APIs)
- Financial data (use yfinance, coingecko)
- Scientific papers (use arxiv, pubmed)
- Structured data (use wikidata)

RATE LIMIT: Fair use (be polite)
API KEY: Not required

Official API docs: https://www.mediawiki.org/wiki/API:Main_page
"""

import requests
from typing import Optional, List, Dict
from urllib.parse import quote

BASE_URL = "https://en.wikipedia.org/w/api.php"

# Required User-Agent for Wikipedia API
HEADERS = {
    "User-Agent": "RalphResearch/1.0 (https://github.com/SoSmDe/Ralph_research; research bot)"
}


def get_summary(topic: str, sentences: int = 5) -> dict:
    """
    Get a summary of a Wikipedia article.

    Args:
        topic: Article title or search term
        sentences: Number of sentences in summary (1-10)

    Returns:
        Dict with title, summary, url, and thumbnail if available

    Use case: Quick background on any topic

    Example:
        get_summary("Bitcoin")
        get_summary("Machine Learning")
    """
    # First, search for the exact page
    params = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "extracts|pageimages|info",
        "exintro": True,
        "explaintext": True,
        "exsentences": min(sentences, 10),
        "piprop": "thumbnail",
        "pithumbsize": 300,
        "inprop": "url",
        "redirects": 1,
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return {"error": "No results found", "topic": topic}

    # Get the first (and usually only) page
    page = list(pages.values())[0]

    if page.get("missing"):
        # Try search if exact title not found
        return search(topic, limit=1)

    return {
        "title": page.get("title"),
        "summary": page.get("extract", ""),
        "url": page.get("fullurl", f"https://en.wikipedia.org/wiki/{quote(topic)}"),
        "page_id": page.get("pageid"),
        "thumbnail": page.get("thumbnail", {}).get("source"),
    }


def get_full_article(topic: str, max_sections: int = 10) -> dict:
    """
    Get the full text of a Wikipedia article.

    Args:
        topic: Article title
        max_sections: Maximum number of sections to return

    Returns:
        Dict with title, sections, categories, and references

    Use case: Deep research on a topic

    Example:
        get_full_article("Blockchain")
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "extracts|categories|info",
        "explaintext": True,
        "exsectionformat": "plain",
        "inprop": "url",
        "redirects": 1,
        "cllimit": 20,
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return {"error": "No results found", "topic": topic}

    page = list(pages.values())[0]

    if page.get("missing"):
        return {"error": "Article not found", "topic": topic}

    # Parse sections from full text
    full_text = page.get("extract", "")
    sections = _parse_sections(full_text, max_sections)

    # Get categories
    categories = [
        cat["title"].replace("Category:", "")
        for cat in page.get("categories", [])
    ]

    return {
        "title": page.get("title"),
        "url": page.get("fullurl"),
        "page_id": page.get("pageid"),
        "sections": sections,
        "categories": categories,
        "word_count": len(full_text.split()),
    }


def _parse_sections(text: str, max_sections: int) -> list:
    """Parse text into sections based on headings."""
    lines = text.split("\n")
    sections = []
    current_section = {"title": "Introduction", "content": []}

    for line in lines:
        # Check if line looks like a heading (starts with == or similar pattern)
        stripped = line.strip()
        if stripped.startswith("==") and stripped.endswith("=="):
            # Save previous section if it has content
            if current_section["content"]:
                current_section["content"] = "\n".join(current_section["content"]).strip()
                sections.append(current_section)
                if len(sections) >= max_sections:
                    break
            # Start new section
            title = stripped.strip("= ")
            current_section = {"title": title, "content": []}
        else:
            current_section["content"].append(line)

    # Add last section
    if current_section["content"] and len(sections) < max_sections:
        current_section["content"] = "\n".join(current_section["content"]).strip()
        sections.append(current_section)

    return sections


def search(query: str, limit: int = 10) -> dict:
    """
    Search Wikipedia for articles.

    Args:
        query: Search query
        limit: Maximum number of results (1-50)

    Returns:
        Dict with list of matching articles

    Use case: Find relevant Wikipedia articles

    Example:
        search("cryptocurrency regulation")
        search("artificial intelligence applications")
    """
    params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, 50),
        "srprop": "snippet|titlesnippet|wordcount",
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    results = data.get("query", {}).get("search", [])

    return {
        "query": query,
        "total_hits": data.get("query", {}).get("searchinfo", {}).get("totalhits", 0),
        "results": [
            {
                "title": r["title"],
                "snippet": _clean_snippet(r.get("snippet", "")),
                "word_count": r.get("wordcount", 0),
                "url": f"https://en.wikipedia.org/wiki/{quote(r['title'])}",
            }
            for r in results
        ],
    }


def _clean_snippet(snippet: str) -> str:
    """Remove HTML tags from snippet."""
    import re
    return re.sub(r'<[^>]+>', '', snippet)


def get_references(topic: str, limit: int = 50) -> dict:
    """
    Get external references from a Wikipedia article.

    Args:
        topic: Article title
        limit: Maximum number of references

    Returns:
        Dict with list of external links and references

    Use case: Find authoritative sources on a topic

    Example:
        get_references("Bitcoin")
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "extlinks|references",
        "ellimit": min(limit, 500),
        "redirects": 1,
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return {"error": "No results found", "topic": topic}

    page = list(pages.values())[0]

    if page.get("missing"):
        return {"error": "Article not found", "topic": topic}

    # Extract external links
    ext_links = [
        link.get("*", "")
        for link in page.get("extlinks", [])
    ]

    return {
        "title": page.get("title"),
        "page_id": page.get("pageid"),
        "external_links": ext_links[:limit],
        "link_count": len(ext_links),
    }


def get_links(topic: str, limit: int = 100) -> dict:
    """
    Get internal Wikipedia links from an article.

    Args:
        topic: Article title
        limit: Maximum number of links

    Returns:
        Dict with list of linked Wikipedia articles

    Use case: Explore related topics

    Example:
        get_links("Ethereum")
    """
    params = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "links",
        "pllimit": min(limit, 500),
        "redirects": 1,
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return {"error": "No results found", "topic": topic}

    page = list(pages.values())[0]

    links = [
        link.get("title", "")
        for link in page.get("links", [])
    ]

    return {
        "title": page.get("title"),
        "linked_articles": links,
        "link_count": len(links),
    }


def get_article_in_language(topic: str, lang: str = "ru") -> dict:
    """
    Get article summary in a specific language.

    Args:
        topic: Article title (in English)
        lang: Language code (ru, de, fr, es, zh, ja, etc.)

    Returns:
        Dict with article in requested language

    Use case: Get localized content

    Example:
        get_article_in_language("Bitcoin", "ru")
    """
    # First get langlinks from English Wikipedia
    params = {
        "action": "query",
        "format": "json",
        "titles": topic,
        "prop": "langlinks",
        "lllang": lang,
        "redirects": 1,
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})

    if not pages:
        return {"error": "No results found", "topic": topic}

    page = list(pages.values())[0]
    langlinks = page.get("langlinks", [])

    if not langlinks:
        return {"error": f"No {lang} version found", "topic": topic}

    # Get the foreign language title
    foreign_title = langlinks[0].get("*", "")

    # Now fetch from foreign language Wikipedia
    foreign_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "format": "json",
        "titles": foreign_title,
        "prop": "extracts|info",
        "exintro": True,
        "explaintext": True,
        "exsentences": 5,
        "inprop": "url",
    }

    response = requests.get(foreign_url, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    foreign_page = list(pages.values())[0]

    return {
        "original_title": topic,
        "title": foreign_page.get("title"),
        "language": lang,
        "summary": foreign_page.get("extract", ""),
        "url": foreign_page.get("fullurl"),
    }


# ============ HELPER FUNCTIONS ============

def get_random_articles(count: int = 5) -> list:
    """
    Get random Wikipedia articles.

    Returns: List of random articles with summaries
    """
    params = {
        "action": "query",
        "format": "json",
        "list": "random",
        "rnlimit": min(count, 10),
        "rnnamespace": 0,  # Main namespace only
    }

    response = requests.get(BASE_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    data = response.json()

    random_pages = data.get("query", {}).get("random", [])

    return [
        {"title": p["title"], "url": f"https://en.wikipedia.org/wiki/{quote(p['title'])}"}
        for p in random_pages
    ]


def get_page_views(topic: str, days: int = 30) -> dict:
    """
    Get page view statistics for an article.

    Args:
        topic: Article title
        days: Number of days of data

    Returns:
        Dict with daily page views

    Use case: Measure topic popularity/interest
    """
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    # Use Wikimedia REST API for pageviews
    title = topic.replace(" ", "_")
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{quote(title)}/daily/{start_date.strftime('%Y%m%d')}/{end_date.strftime('%Y%m%d')}"

    try:
        response = requests.get(url, headers={"User-Agent": "RalphResearch/1.0"})
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        views = [
            {"date": item["timestamp"][:8], "views": item["views"]}
            for item in items
        ]

        total_views = sum(item["views"] for item in items)
        avg_views = total_views / len(items) if items else 0

        return {
            "title": topic,
            "period_days": days,
            "total_views": total_views,
            "average_daily_views": round(avg_views),
            "daily_views": views,
        }
    except Exception as e:
        return {"error": str(e), "topic": topic}


if __name__ == "__main__":
    print("=== Wikipedia Summary ===")
    result = get_summary("Bitcoin")
    print(f"Title: {result.get('title')}")
    print(f"Summary: {result.get('summary', '')[:200]}...")

    print("\n=== Wikipedia Search ===")
    results = search("cryptocurrency regulation", limit=5)
    for r in results.get("results", [])[:3]:
        print(f"  - {r['title']}")
