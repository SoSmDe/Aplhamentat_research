# -*- coding: utf-8 -*-
"""
Deloitte Insights Parser

USE FOR:
- Industry research reports
- Technology trends
- Financial services insights
- CEO/CFO surveys
- Sector analysis

DO NOT USE FOR:
- Macro data (use World Bank, IMF)
- Real-time market data (use stock/crypto APIs)
- Historical statistics (use official sources)

RATE LIMIT: Fair use (RSS feeds)
API KEY: Not required

RSS feeds provide easy access to latest insights.
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import re

try:
    import feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False


# ============ RSS FEEDS ============

RSS_FEEDS = {
    "all": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/all.rss.xml",
    "tech": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/technology.rss.xml",
    "technology": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/technology.rss.xml",
    "finance": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/financial-services.rss.xml",
    "financial_services": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/financial-services.rss.xml",
    "energy": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/energy-resources.rss.xml",
    "government": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/government-public-services.rss.xml",
    "healthcare": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/life-sciences-health-care.rss.xml",
    "consumer": "https://www2.deloitte.com/content/www/us/en/insights/rss-feeds/consumer.rss.xml",
}


def get_latest(category: str = "all", limit: int = 20) -> list:
    """
    Get latest Deloitte Insights articles from RSS.

    Args:
        category: Category name (all, tech, finance, energy, healthcare, etc.)
        limit: Maximum number of articles

    Returns:
        List of articles with title, url, summary, date

    Use case: Stay updated on industry research
    """
    if not HAS_FEEDPARSER:
        return _get_latest_fallback(category, limit)

    feed_url = RSS_FEEDS.get(category.lower(), RSS_FEEDS["all"])

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        return [{"error": f"Failed to parse feed: {str(e)}"}]

    articles = []
    for entry in feed.entries[:limit]:
        # Clean summary
        summary = entry.get("summary", "")
        summary = re.sub(r'<[^>]+>', '', summary)  # Remove HTML tags
        summary = summary[:500] + "..." if len(summary) > 500 else summary

        articles.append({
            "title": entry.get("title", ""),
            "url": entry.get("link", ""),
            "summary": summary,
            "date": entry.get("published", ""),
            "source": "Deloitte Insights",
            "category": category,
        })

    return articles


def _get_latest_fallback(category: str, limit: int) -> list:
    """
    Fallback method using requests (if feedparser not installed).
    """
    feed_url = RSS_FEEDS.get(category.lower(), RSS_FEEDS["all"])

    try:
        response = requests.get(feed_url, timeout=30)
        response.raise_for_status()
        content = response.text

        # Basic XML parsing
        articles = []
        items = re.findall(r'<item>(.*?)</item>', content, re.DOTALL)

        for item in items[:limit]:
            title = re.search(r'<title>(.*?)</title>', item)
            link = re.search(r'<link>(.*?)</link>', item)
            desc = re.search(r'<description>(.*?)</description>', item, re.DOTALL)
            pub_date = re.search(r'<pubDate>(.*?)</pubDate>', item)

            articles.append({
                "title": title.group(1) if title else "",
                "url": link.group(1) if link else "",
                "summary": re.sub(r'<[^>]+>', '', desc.group(1)[:500] if desc else ""),
                "date": pub_date.group(1) if pub_date else "",
                "source": "Deloitte Insights",
                "category": category,
            })

        return articles
    except Exception as e:
        return [{"error": f"Fallback parsing failed: {str(e)}"}]


def get_tech_trends(limit: int = 10) -> list:
    """
    Get latest technology trends articles.

    Use case: Tech industry research
    """
    return get_latest("tech", limit)


def get_finance_insights(limit: int = 10) -> list:
    """
    Get latest financial services insights.

    Use case: Banking, fintech, insurance research
    """
    return get_latest("finance", limit)


def get_all_categories() -> list:
    """
    Get articles from all categories.

    Returns: Combined list from all RSS feeds

    Use case: Broad research scan
    """
    all_articles = []
    categories = ["tech", "finance", "healthcare", "energy", "consumer"]

    for cat in categories:
        articles = get_latest(cat, limit=5)
        all_articles.extend(articles)

    return all_articles


# ============ WEB SEARCH (for specific topics) ============

def search_insights(query: str, limit: int = 10) -> list:
    """
    Search Deloitte Insights (via web search).

    Note: Uses site-specific web search

    Args:
        query: Search query
        limit: Max results

    Returns: List of matching articles
    """
    # This would typically use web search API
    # For now, return guidance
    return {
        "note": "Use WebSearch tool with site:deloitte.com/insights",
        "query_suggestion": f"site:deloitte.com/insights {query}",
        "alternative": "Use get_latest() to browse by category",
    }


# ============ POPULAR REPORTS ============

def get_popular_reports() -> dict:
    """
    Get links to popular Deloitte report series.

    Returns: URLs to major recurring reports
    """
    return {
        "tech_trends": {
            "name": "Tech Trends",
            "description": "Annual technology trends report",
            "url": "https://www2.deloitte.com/us/en/insights/focus/tech-trends.html",
        },
        "global_human_capital": {
            "name": "Global Human Capital Trends",
            "description": "Annual HR and workforce trends",
            "url": "https://www2.deloitte.com/us/en/insights/focus/human-capital-trends.html",
        },
        "cfo_signals": {
            "name": "CFO Signals",
            "description": "Quarterly CFO survey",
            "url": "https://www2.deloitte.com/us/en/pages/finance/articles/cfo-signals-survey.html",
        },
        "banking_outlook": {
            "name": "Banking Industry Outlook",
            "description": "Annual banking sector outlook",
            "url": "https://www2.deloitte.com/us/en/insights/industry/financial-services/financial-services-industry-outlooks/banking-industry-outlook.html",
        },
        "insurance_outlook": {
            "name": "Insurance Industry Outlook",
            "description": "Annual insurance sector outlook",
            "url": "https://www2.deloitte.com/us/en/insights/industry/financial-services/financial-services-industry-outlooks/insurance-industry-outlook.html",
        },
        "private_equity": {
            "name": "Private Equity Outlook",
            "description": "PE market trends and outlook",
            "url": "https://www2.deloitte.com/us/en/pages/mergers-and-acquisitions/articles/private-equity-outlook.html",
        },
    }


# ============ HELPER FUNCTIONS ============

def format_articles(articles: list) -> str:
    """
    Format articles list as readable text.

    Returns: Formatted string for reports
    """
    if not articles:
        return "No articles found"

    lines = ["Deloitte Insights Articles", "=" * 50]

    for i, article in enumerate(articles, 1):
        if "error" in article:
            lines.append(f"Error: {article['error']}")
            continue

        lines.append(f"\n{i}. {article['title']}")
        lines.append(f"   Date: {article.get('date', 'N/A')}")
        lines.append(f"   URL: {article['url']}")
        if article.get('summary'):
            lines.append(f"   Summary: {article['summary'][:200]}...")

    return "\n".join(lines)


def get_category_list() -> list:
    """
    Get available categories.

    Returns: List of category names
    """
    return list(RSS_FEEDS.keys())


if __name__ == "__main__":
    print("=== Available Categories ===")
    print(", ".join(get_category_list()))

    print("\n=== Latest Tech Insights ===")
    articles = get_tech_trends(5)
    for a in articles:
        if "error" not in a:
            print(f"  - {a['title'][:60]}...")
            print(f"    {a['url']}")

    print("\n=== Popular Reports ===")
    reports = get_popular_reports()
    for key, report in reports.items():
        print(f"  - {report['name']}: {report['description']}")
