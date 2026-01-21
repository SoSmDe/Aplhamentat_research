# -*- coding: utf-8 -*-
"""
Serper API Integration (Google Search)

USE FOR:
- General web search
- News search (recent articles)
- Scholar search (academic results)
- Image search
- Finding authoritative sources
- Fact verification
- Market research

DO NOT USE FOR:
- Scientific papers (use arxiv, pubmed)
- Financial data (use dedicated APIs)
- Wikipedia content (use wikipedia API)
- Structured data (use wikidata)

RATE LIMIT: Based on plan (2,500 free queries/month)
API KEY: Required (SERPER_API_KEY)

Official docs: https://serper.dev/
"""

import requests
import os
from typing import List, Dict, Optional

BASE_URL = "https://google.serper.dev"


def _get_api_key() -> str:
    """Get API key from environment."""
    api_key = os.environ.get("SERPER_API_KEY")
    if not api_key:
        raise ValueError(
            "SERPER_API_KEY not found in environment. "
            "Get your key at https://serper.dev/"
        )
    return api_key


def _make_request(endpoint: str, payload: dict) -> dict:
    """Make request to Serper API."""
    headers = {
        "X-API-KEY": _get_api_key(),
        "Content-Type": "application/json"
    }

    response = requests.post(
        f"{BASE_URL}/{endpoint}",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    return response.json()


def search(query: str, num_results: int = 10,
           country: str = "us", language: str = "en") -> dict:
    """
    Perform a Google web search.

    Args:
        query: Search query
        num_results: Number of results (1-100)
        country: Country code (us, uk, ru, de, etc.)
        language: Language code (en, ru, de, etc.)

    Returns:
        Dict with organic results, knowledge panel, related searches

    Use case: General research, finding sources

    Example:
        search("Bitcoin ETF approval")
        search("cryptocurrency regulation 2024")
    """
    payload = {
        "q": query,
        "num": min(num_results, 100),
        "gl": country,
        "hl": language,
    }

    data = _make_request("search", payload)

    # Parse organic results
    organic = []
    for item in data.get("organic", []):
        organic.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
            "position": item.get("position"),
            "date": item.get("date"),
        })

    # Parse knowledge graph if available
    knowledge_graph = None
    if "knowledgeGraph" in data:
        kg = data["knowledgeGraph"]
        knowledge_graph = {
            "title": kg.get("title"),
            "type": kg.get("type"),
            "description": kg.get("description"),
            "website": kg.get("website"),
            "attributes": kg.get("attributes", {}),
        }

    # Parse related searches
    related = [
        r.get("query") for r in data.get("relatedSearches", [])
    ]

    return {
        "query": query,
        "search_time": data.get("searchParameters", {}).get("timeTaken"),
        "total_results": len(organic),
        "results": organic,
        "knowledge_graph": knowledge_graph,
        "related_searches": related,
        "people_also_ask": [
            {"question": p.get("question"), "answer": p.get("snippet")}
            for p in data.get("peopleAlsoAsk", [])
        ],
    }


def search_news(query: str, num_results: int = 10,
                country: str = "us", time_period: str = None) -> dict:
    """
    Search for news articles.

    Args:
        query: Search query
        num_results: Number of results
        country: Country code
        time_period: Time filter ("h" = hour, "d" = day, "w" = week, "m" = month, "y" = year)

    Returns:
        Dict with news articles

    Use case: Current events, market news

    Example:
        search_news("Bitcoin price", time_period="d")
        search_news("Federal Reserve rate", num_results=20)
    """
    payload = {
        "q": query,
        "num": min(num_results, 100),
        "gl": country,
    }

    if time_period:
        payload["tbs"] = f"qdr:{time_period}"

    data = _make_request("news", payload)

    news = []
    for item in data.get("news", []):
        news.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
            "source": item.get("source"),
            "date": item.get("date"),
            "image_url": item.get("imageUrl"),
        })

    return {
        "query": query,
        "time_period": time_period,
        "total_results": len(news),
        "articles": news,
    }


def search_scholar(query: str, num_results: int = 10,
                   year_from: int = None, year_to: int = None) -> dict:
    """
    Search Google Scholar for academic content.

    Args:
        query: Search query
        num_results: Number of results
        year_from: Filter papers from this year
        year_to: Filter papers to this year

    Returns:
        Dict with academic results

    Use case: Academic research, finding papers

    Example:
        search_scholar("machine learning finance")
        search_scholar("blockchain scalability", year_from=2022)
    """
    payload = {
        "q": query,
        "num": min(num_results, 100),
    }

    if year_from:
        payload["as_ylo"] = year_from
    if year_to:
        payload["as_yhi"] = year_to

    data = _make_request("scholar", payload)

    papers = []
    for item in data.get("organic", []):
        papers.append({
            "title": item.get("title"),
            "url": item.get("link"),
            "snippet": item.get("snippet"),
            "authors": item.get("publication_info", {}).get("authors", []),
            "year": item.get("year"),
            "cited_by": item.get("inline_links", {}).get("cited_by", {}).get("total"),
            "pdf_url": item.get("resources", [{}])[0].get("link") if item.get("resources") else None,
        })

    return {
        "query": query,
        "year_range": f"{year_from or 'any'}-{year_to or 'any'}",
        "total_results": len(papers),
        "papers": papers,
    }


def search_images(query: str, num_results: int = 10,
                  safe_search: bool = True) -> dict:
    """
    Search for images.

    Args:
        query: Search query
        num_results: Number of results
        safe_search: Enable safe search filter

    Returns:
        Dict with image results

    Example:
        search_images("Bitcoin logo")
    """
    payload = {
        "q": query,
        "num": min(num_results, 100),
    }

    if safe_search:
        payload["safe"] = "active"

    data = _make_request("images", payload)

    images = []
    for item in data.get("images", []):
        images.append({
            "title": item.get("title"),
            "image_url": item.get("imageUrl"),
            "thumbnail_url": item.get("thumbnailUrl"),
            "source_url": item.get("link"),
            "source": item.get("source"),
            "width": item.get("imageWidth"),
            "height": item.get("imageHeight"),
        })

    return {
        "query": query,
        "total_results": len(images),
        "images": images,
    }


def search_places(query: str, location: str = None) -> dict:
    """
    Search for places/businesses.

    Args:
        query: Search query (e.g., "crypto exchanges in Dubai")
        location: Location to search around

    Returns:
        Dict with place results

    Example:
        search_places("blockchain companies", location="Dubai")
    """
    payload = {
        "q": query,
    }

    if location:
        payload["location"] = location

    data = _make_request("places", payload)

    places = []
    for item in data.get("places", []):
        places.append({
            "title": item.get("title"),
            "address": item.get("address"),
            "rating": item.get("rating"),
            "reviews": item.get("reviews"),
            "type": item.get("type"),
            "phone": item.get("phone"),
            "website": item.get("website"),
            "hours": item.get("hours"),
        })

    return {
        "query": query,
        "location": location,
        "total_results": len(places),
        "places": places,
    }


# ============ HELPER FUNCTIONS ============

def search_with_site(query: str, site: str, num_results: int = 10) -> dict:
    """
    Search within a specific website.

    Args:
        query: Search query
        site: Website domain (e.g., "reddit.com", "twitter.com")
        num_results: Number of results

    Returns:
        Results from the specified site only

    Example:
        search_with_site("Bitcoin ETF", "reddit.com")
        search_with_site("Ethereum merge", "twitter.com")
    """
    return search(f"site:{site} {query}", num_results=num_results)


def search_recent(query: str, period: str = "d", num_results: int = 10) -> dict:
    """
    Search for recent results only.

    Args:
        query: Search query
        period: "h" (hour), "d" (day), "w" (week), "m" (month)
        num_results: Number of results

    Returns:
        Recent results only
    """
    return search_news(query, num_results=num_results, time_period=period)


def search_filetype(query: str, filetype: str, num_results: int = 10) -> dict:
    """
    Search for specific file types.

    Args:
        query: Search query
        filetype: File extension (pdf, xls, doc, ppt)
        num_results: Number of results

    Returns:
        Results of specific file type

    Example:
        search_filetype("tokenomics whitepaper", "pdf")
    """
    return search(f"filetype:{filetype} {query}", num_results=num_results)


def get_answer(question: str) -> dict:
    """
    Get a direct answer to a question.

    Args:
        question: Question to answer

    Returns:
        Dict with answer from knowledge graph or snippets

    Example:
        get_answer("What is the market cap of Bitcoin?")
    """
    result = search(question, num_results=5)

    answer = None

    # Check knowledge graph first
    if result.get("knowledge_graph"):
        kg = result["knowledge_graph"]
        if kg.get("description"):
            answer = kg["description"]

    # Check People Also Ask
    if not answer and result.get("people_also_ask"):
        for paa in result["people_also_ask"]:
            if paa.get("answer"):
                answer = paa["answer"]
                break

    # Fall back to first snippet
    if not answer and result.get("results"):
        answer = result["results"][0].get("snippet")

    return {
        "question": question,
        "answer": answer,
        "source": result["results"][0] if result.get("results") else None,
        "related_questions": [
            q["question"] for q in result.get("people_also_ask", [])
        ],
    }


def verify_fact(claim: str) -> dict:
    """
    Search for sources to verify a factual claim.

    Args:
        claim: The claim to verify

    Returns:
        Dict with supporting and relevant sources

    Example:
        verify_fact("Bitcoin has a maximum supply of 21 million")
    """
    result = search(claim, num_results=10)

    sources = []
    for r in result.get("results", []):
        # Prioritize authoritative sources
        url = r.get("url", "")
        authority = "low"
        if any(d in url for d in [".gov", ".edu", ".org", "wikipedia"]):
            authority = "high"
        elif any(d in url for d in ["reuters", "bloomberg", "wsj", "ft.com"]):
            authority = "high"
        elif any(d in url for d in ["forbes", "techcrunch", "coindesk", "cointelegraph"]):
            authority = "medium"

        sources.append({
            "title": r.get("title"),
            "url": url,
            "snippet": r.get("snippet"),
            "authority": authority,
        })

    # Sort by authority
    authority_order = {"high": 0, "medium": 1, "low": 2}
    sources.sort(key=lambda x: authority_order.get(x["authority"], 3))

    return {
        "claim": claim,
        "sources_found": len(sources),
        "high_authority_sources": [s for s in sources if s["authority"] == "high"],
        "all_sources": sources,
    }


if __name__ == "__main__":
    # Note: Requires SERPER_API_KEY environment variable
    try:
        print("=== Serper Search Test ===")
        result = search("Bitcoin ETF", num_results=3)
        for r in result.get("results", []):
            print(f"\n{r['title']}")
            print(f"  {r['url']}")
    except ValueError as e:
        print(f"Error: {e}")
        print("Set SERPER_API_KEY environment variable to use this module.")
