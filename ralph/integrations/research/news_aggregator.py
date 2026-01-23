# -*- coding: utf-8 -*-
"""
News Aggregator Integration

USE FOR:
- Recent news and events
- Market sentiment analysis
- Company news monitoring
- Industry trends
- Breaking news
- Press releases

DO NOT USE FOR:
- Academic research (use arxiv, google_scholar)
- Historical data (use data APIs)
- Company financials (use sec_edgar)
- Company profiles (use crunchbase)

RATE LIMIT: Varies by source
API KEYS: Optional (some sources free, some require keys)

Supported sources:
- NewsAPI (requires NEWSAPI_KEY)
- Google News RSS (free, no key)
- Bing News (requires BING_NEWS_KEY)
- CryptoPanic (requires CRYPTOPANIC_KEY)
"""

import requests
import os
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
import time

# Rate limiting
_last_request = {}
_min_intervals = {
    "newsapi": 1.0,
    "google": 2.0,
    "bing": 0.5,
    "cryptopanic": 1.0,
}


def _rate_limit(source: str):
    """Respect rate limits per source."""
    global _last_request
    interval = _min_intervals.get(source, 1.0)
    last = _last_request.get(source, 0)
    elapsed = time.time() - last
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_request[source] = time.time()


# ============ NEWSAPI ============

def search_newsapi(query: str,
                   language: str = "en",
                   sort_by: str = "relevancy",
                   from_date: str = None,
                   to_date: str = None,
                   domains: List[str] = None,
                   num_results: int = 50) -> dict:
    """
    Search news via NewsAPI.

    Args:
        query: Search query
        language: Language code (en, ru, de, etc.)
        sort_by: "relevancy", "popularity", "publishedAt"
        from_date: Start date (YYYY-MM-DD)
        to_date: End date (YYYY-MM-DD)
        domains: List of domains to search (e.g., ["reuters.com", "bloomberg.com"])
        num_results: Maximum results (1-100)

    Returns:
        Dict with news articles

    Requires: NEWSAPI_KEY environment variable

    Example:
        search_newsapi("Bitcoin ETF")
        search_newsapi("tokenization", domains=["reuters.com"])
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        raise ValueError(
            "NEWSAPI_KEY not found in environment. "
            "Get your key at https://newsapi.org/"
        )

    _rate_limit("newsapi")

    params = {
        "q": query,
        "apiKey": api_key,
        "language": language,
        "sortBy": sort_by,
        "pageSize": min(num_results, 100),
    }

    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if domains:
        params["domains"] = ",".join(domains)

    response = requests.get(
        "https://newsapi.org/v2/everything",
        params=params
    )
    response.raise_for_status()
    data = response.json()

    articles = []
    for item in data.get("articles", []):
        articles.append({
            "title": item.get("title"),
            "description": item.get("description"),
            "content": item.get("content"),
            "url": item.get("url"),
            "source": item.get("source", {}).get("name"),
            "author": item.get("author"),
            "published_at": item.get("publishedAt"),
            "image_url": item.get("urlToImage"),
        })

    return {
        "query": query,
        "source": "newsapi",
        "total_results": data.get("totalResults", len(articles)),
        "articles": articles,
    }


def get_top_headlines(category: str = None,
                      country: str = "us",
                      sources: List[str] = None,
                      num_results: int = 50) -> dict:
    """
    Get top headlines from NewsAPI.

    Args:
        category: "business", "technology", "science", "health", "entertainment", "sports"
        country: Country code (us, gb, ru, de, etc.)
        sources: Specific sources (overrides country/category)
        num_results: Maximum results

    Returns:
        Dict with top headlines

    Example:
        get_top_headlines(category="business")
        get_top_headlines(sources=["reuters", "bloomberg"])
    """
    api_key = os.environ.get("NEWSAPI_KEY")
    if not api_key:
        raise ValueError("NEWSAPI_KEY not found in environment.")

    _rate_limit("newsapi")

    params = {
        "apiKey": api_key,
        "pageSize": min(num_results, 100),
    }

    if sources:
        params["sources"] = ",".join(sources)
    else:
        if country:
            params["country"] = country
        if category:
            params["category"] = category

    response = requests.get(
        "https://newsapi.org/v2/top-headlines",
        params=params
    )
    response.raise_for_status()
    data = response.json()

    articles = []
    for item in data.get("articles", []):
        articles.append({
            "title": item.get("title"),
            "description": item.get("description"),
            "url": item.get("url"),
            "source": item.get("source", {}).get("name"),
            "published_at": item.get("publishedAt"),
        })

    return {
        "category": category,
        "country": country,
        "source": "newsapi",
        "total_results": data.get("totalResults", len(articles)),
        "articles": articles,
    }


# ============ GOOGLE NEWS RSS ============

def search_google_news(query: str,
                       language: str = "en",
                       region: str = "US",
                       num_results: int = 50) -> dict:
    """
    Search news via Google News RSS (free, no API key).

    Args:
        query: Search query
        language: Language code
        region: Region code (US, GB, RU, etc.)
        num_results: Maximum results

    Returns:
        Dict with news articles

    Example:
        search_google_news("blockchain regulation")
        search_google_news("криптовалюты", language="ru", region="RU")
    """
    _rate_limit("google")

    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl={language}&gl={region}&ceid={region}:{language}"

    response = requests.get(url)
    response.raise_for_status()

    # Parse RSS
    root = ET.fromstring(response.content)
    channel = root.find("channel")

    articles = []
    for item in channel.findall("item")[:num_results]:
        # Parse publication date
        pub_date = item.find("pubDate")
        if pub_date is not None:
            pub_date = pub_date.text

        # Extract source from title (Google News format: "Title - Source")
        title_text = item.find("title").text or ""
        if " - " in title_text:
            parts = title_text.rsplit(" - ", 1)
            title = parts[0]
            source = parts[1] if len(parts) > 1 else None
        else:
            title = title_text
            source = None

        articles.append({
            "title": title,
            "url": item.find("link").text,
            "source": source,
            "published_at": pub_date,
            "description": item.find("description").text if item.find("description") is not None else None,
        })

    return {
        "query": query,
        "source": "google_news",
        "language": language,
        "region": region,
        "total_results": len(articles),
        "articles": articles,
    }


def get_google_news_topic(topic: str,
                          language: str = "en",
                          region: str = "US",
                          num_results: int = 50) -> dict:
    """
    Get Google News by topic.

    Args:
        topic: "business", "technology", "science", "health", "world", "nation"
        language: Language code
        region: Region code
        num_results: Maximum results

    Returns:
        Dict with topic news

    Example:
        get_google_news_topic("business")
        get_google_news_topic("technology")
    """
    _rate_limit("google")

    # Topic IDs for Google News
    topic_ids = {
        "world": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx1YlY4U0FtVnVHZ0pWVXlnQVAB",
        "business": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pWVXlnQVAB",
        "technology": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB",
        "science": "CAAqJggKIiBDQkFTRWdvSUwyMHZNRFp0Y1RjU0FtVnVHZ0pWVXlnQVAB",
        "health": "CAAqIQgKIhtDQkFTRGdvSUwyMHZNR3QwTlRFU0FtVnVLQUFQAQ",
    }

    topic_id = topic_ids.get(topic.lower())
    if not topic_id:
        # Fall back to search
        return search_google_news(topic, language, region, num_results)

    url = f"https://news.google.com/rss/topics/{topic_id}?hl={language}&gl={region}&ceid={region}:{language}"

    response = requests.get(url)
    response.raise_for_status()

    root = ET.fromstring(response.content)
    channel = root.find("channel")

    articles = []
    for item in channel.findall("item")[:num_results]:
        title_text = item.find("title").text or ""
        if " - " in title_text:
            parts = title_text.rsplit(" - ", 1)
            title = parts[0]
            source = parts[1] if len(parts) > 1 else None
        else:
            title = title_text
            source = None

        articles.append({
            "title": title,
            "url": item.find("link").text,
            "source": source,
            "published_at": item.find("pubDate").text if item.find("pubDate") is not None else None,
        })

    return {
        "topic": topic,
        "source": "google_news",
        "total_results": len(articles),
        "articles": articles,
    }


# ============ CRYPTOPANIC ============

def search_cryptopanic(currencies: List[str] = None,
                       filter_type: str = None,
                       kind: str = None,
                       num_results: int = 50) -> dict:
    """
    Get crypto news from CryptoPanic.

    Args:
        currencies: Filter by currencies (e.g., ["BTC", "ETH"])
        filter_type: "rising", "hot", "bullish", "bearish", "important", "lol"
        kind: "news", "media"
        num_results: Maximum results

    Returns:
        Dict with crypto news

    Requires: CRYPTOPANIC_KEY environment variable (optional for basic access)

    Example:
        search_cryptopanic(currencies=["BTC"])
        search_cryptopanic(filter_type="bullish")
    """
    _rate_limit("cryptopanic")

    params = {}

    api_key = os.environ.get("CRYPTOPANIC_KEY")
    if api_key:
        params["auth_token"] = api_key

    if currencies:
        params["currencies"] = ",".join(currencies)
    if filter_type:
        params["filter"] = filter_type
    if kind:
        params["kind"] = kind

    response = requests.get(
        "https://cryptopanic.com/api/v1/posts/",
        params=params
    )
    response.raise_for_status()
    data = response.json()

    articles = []
    for item in data.get("results", [])[:num_results]:
        articles.append({
            "title": item.get("title"),
            "url": item.get("url"),
            "source": item.get("source", {}).get("title"),
            "published_at": item.get("published_at"),
            "currencies": [c.get("code") for c in item.get("currencies", [])],
            "votes": {
                "positive": item.get("votes", {}).get("positive", 0),
                "negative": item.get("votes", {}).get("negative", 0),
                "important": item.get("votes", {}).get("important", 0),
            },
            "kind": item.get("kind"),
        })

    return {
        "currencies": currencies,
        "filter": filter_type,
        "source": "cryptopanic",
        "total_results": len(articles),
        "articles": articles,
    }


# ============ AGGREGATOR ============

def search_all_sources(query: str,
                       language: str = "en",
                       num_results_per_source: int = 20) -> dict:
    """
    Search across all available news sources.

    Args:
        query: Search query
        language: Language code
        num_results_per_source: Results per source

    Returns:
        Dict with combined results from all sources

    Example:
        search_all_sources("Bitcoin ETF")
    """
    results = {
        "query": query,
        "sources_searched": [],
        "total_articles": 0,
        "articles_by_source": {},
    }

    # Google News (always available)
    try:
        google_results = search_google_news(query, language, num_results=num_results_per_source)
        results["sources_searched"].append("google_news")
        results["articles_by_source"]["google_news"] = google_results["articles"]
        results["total_articles"] += len(google_results["articles"])
    except Exception as e:
        results["articles_by_source"]["google_news"] = {"error": str(e)}

    # NewsAPI (if key available)
    if os.environ.get("NEWSAPI_KEY"):
        try:
            newsapi_results = search_newsapi(query, language, num_results=num_results_per_source)
            results["sources_searched"].append("newsapi")
            results["articles_by_source"]["newsapi"] = newsapi_results["articles"]
            results["total_articles"] += len(newsapi_results["articles"])
        except Exception as e:
            results["articles_by_source"]["newsapi"] = {"error": str(e)}

    # CryptoPanic (if crypto-related)
    crypto_keywords = ["crypto", "bitcoin", "btc", "ethereum", "eth", "blockchain", "defi", "nft", "web3"]
    if any(kw in query.lower() for kw in crypto_keywords):
        try:
            crypto_results = search_cryptopanic(num_results=num_results_per_source)
            results["sources_searched"].append("cryptopanic")
            results["articles_by_source"]["cryptopanic"] = crypto_results["articles"]
            results["total_articles"] += len(crypto_results["articles"])
        except Exception as e:
            results["articles_by_source"]["cryptopanic"] = {"error": str(e)}

    return results


def get_combined_articles(query: str,
                          language: str = "en",
                          num_results: int = 50,
                          deduplicate: bool = True) -> dict:
    """
    Get combined and deduplicated articles from all sources.

    Args:
        query: Search query
        language: Language code
        num_results: Total maximum results
        deduplicate: Remove duplicate articles

    Returns:
        Dict with combined deduplicated articles

    Example:
        get_combined_articles("tokenization regulation")
    """
    all_results = search_all_sources(query, language, num_results_per_source=30)

    # Combine all articles
    all_articles = []
    for source, articles in all_results["articles_by_source"].items():
        if isinstance(articles, list):
            for article in articles:
                article["_source"] = source
                all_articles.append(article)

    # Deduplicate by title similarity
    if deduplicate:
        seen_titles = set()
        unique_articles = []

        for article in all_articles:
            title = article.get("title", "").lower()[:50]  # First 50 chars
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)

        all_articles = unique_articles

    # Sort by date (newest first)
    def parse_date(article):
        pub_date = article.get("published_at")
        if pub_date:
            try:
                return datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            except:
                pass
        return datetime.min

    all_articles.sort(key=parse_date, reverse=True)

    return {
        "query": query,
        "sources_searched": all_results["sources_searched"],
        "total_articles": len(all_articles[:num_results]),
        "articles": all_articles[:num_results],
    }


# ============ HELPER FUNCTIONS ============

def get_crypto_news(num_results: int = 50) -> dict:
    """
    Get latest cryptocurrency news.

    Returns: Combined crypto news
    """
    return get_combined_articles(
        "cryptocurrency OR bitcoin OR ethereum OR blockchain",
        num_results=num_results
    )


def get_defi_news(num_results: int = 30) -> dict:
    """
    Get DeFi news.

    Returns: DeFi related news
    """
    return search_google_news(
        "DeFi OR 'decentralized finance' OR 'yield farming'",
        num_results=num_results
    )


def get_rwa_news(num_results: int = 30) -> dict:
    """
    Get RWA/tokenization news.

    Returns: Tokenization news
    """
    return search_google_news(
        "tokenization OR 'real world assets' OR RWA OR 'security tokens'",
        num_results=num_results
    )


def get_regulation_news(region: str = "US", num_results: int = 30) -> dict:
    """
    Get cryptocurrency regulation news.

    Args:
        region: Region code

    Returns: Regulation news
    """
    return search_google_news(
        "cryptocurrency regulation OR SEC crypto OR 'digital asset' regulation",
        region=region,
        num_results=num_results
    )


def get_company_news(company_name: str, num_results: int = 30) -> dict:
    """
    Get news about a specific company.

    Args:
        company_name: Company name

    Returns: Company-specific news
    """
    return search_google_news(
        f'"{company_name}"',
        num_results=num_results
    )


def get_market_sentiment(topic: str = "cryptocurrency") -> dict:
    """
    Analyze market sentiment from news.

    Args:
        topic: Topic to analyze

    Returns:
        Dict with sentiment indicators
    """
    articles = get_combined_articles(topic, num_results=50)

    # Simple sentiment keywords
    positive_words = ["surge", "soar", "bullish", "gain", "rise", "rally", "boost", "growth", "breakthrough", "adoption"]
    negative_words = ["crash", "plunge", "bearish", "drop", "fall", "decline", "fear", "risk", "ban", "hack", "scam"]

    positive_count = 0
    negative_count = 0
    neutral_count = 0

    for article in articles["articles"]:
        title = (article.get("title") or "").lower()
        desc = (article.get("description") or "").lower()
        text = title + " " + desc

        pos = sum(1 for w in positive_words if w in text)
        neg = sum(1 for w in negative_words if w in text)

        if pos > neg:
            positive_count += 1
        elif neg > pos:
            negative_count += 1
        else:
            neutral_count += 1

    total = positive_count + negative_count + neutral_count or 1

    return {
        "topic": topic,
        "articles_analyzed": len(articles["articles"]),
        "sentiment": {
            "positive": positive_count,
            "negative": negative_count,
            "neutral": neutral_count,
            "positive_pct": round(positive_count / total * 100, 1),
            "negative_pct": round(negative_count / total * 100, 1),
            "score": round((positive_count - negative_count) / total * 100, 1),
        },
        "sample_positive": [a["title"] for a in articles["articles"] if any(w in (a.get("title") or "").lower() for w in positive_words)][:3],
        "sample_negative": [a["title"] for a in articles["articles"] if any(w in (a.get("title") or "").lower() for w in negative_words)][:3],
    }


if __name__ == "__main__":
    print("=== News Aggregator Test ===")

    # Test Google News (always available)
    result = search_google_news("Bitcoin", num_results=3)
    print(f"\nGoogle News - Found {result['total_results']} articles:")
    for article in result["articles"][:3]:
        print(f"  - {article['title'][:60]}...")
        print(f"    Source: {article['source']}")
