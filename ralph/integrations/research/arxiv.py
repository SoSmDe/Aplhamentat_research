# -*- coding: utf-8 -*-
"""
arXiv API Integration

USE FOR:
- Scientific papers (CS, Math, Physics, Quantitative Finance, etc.)
- Pre-prints and research papers
- Academic citations and references
- Technical deep dives
- AI/ML research papers
- Cryptography and blockchain research

DO NOT USE FOR:
- Medical/biology papers (use pubmed)
- General knowledge (use wikipedia)
- News or current events (use serper)
- Market data (use financial APIs)

RATE LIMIT: 1 request per 3 seconds
API KEY: Not required

Official API docs: https://info.arxiv.org/help/api/index.html
"""

import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
import time
import re

BASE_URL = "http://export.arxiv.org/api/query"

# Rate limiting
_last_request = 0
_min_interval = 3.0  # seconds between requests


def _rate_limit():
    """Respect arXiv rate limits."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request = time.time()


# arXiv category codes
CATEGORIES = {
    # Computer Science
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation and Language (NLP)",
    "cs.CR": "Cryptography and Security",
    "cs.CV": "Computer Vision",
    "cs.LG": "Machine Learning",
    "cs.NE": "Neural and Evolutionary Computing",
    "cs.SE": "Software Engineering",
    "cs.DB": "Databases",
    "cs.DC": "Distributed Computing",

    # Quantitative Finance
    "q-fin.CP": "Computational Finance",
    "q-fin.EC": "Economics",
    "q-fin.GN": "General Finance",
    "q-fin.MF": "Mathematical Finance",
    "q-fin.PM": "Portfolio Management",
    "q-fin.PR": "Pricing of Securities",
    "q-fin.RM": "Risk Management",
    "q-fin.ST": "Statistical Finance",
    "q-fin.TR": "Trading and Market Microstructure",

    # Statistics
    "stat.ML": "Machine Learning (Statistics)",
    "stat.ME": "Methodology",
    "stat.TH": "Theory",

    # Mathematics
    "math.OC": "Optimization and Control",
    "math.PR": "Probability",
    "math.ST": "Statistics Theory",

    # Physics (relevant for crypto/finance)
    "physics.soc-ph": "Physics and Society",
    "physics.data-an": "Data Analysis",

    # Economics
    "econ.EM": "Econometrics",
    "econ.GN": "General Economics",
    "econ.TH": "Theoretical Economics",
}


def search_papers(query: str, max_results: int = 20,
                  sort_by: str = "relevance",
                  category: str = None) -> dict:
    """
    Search for papers on arXiv.

    Args:
        query: Search query (supports AND, OR, title:, author:, abstract:)
        max_results: Maximum number of results (1-100)
        sort_by: "relevance", "lastUpdatedDate", "submittedDate"
        category: Filter by category (e.g., "cs.AI", "q-fin.TR")

    Returns:
        Dict with list of papers (title, authors, abstract, links)

    Use case: Find research papers on a topic

    Example:
        search_papers("transformer attention mechanism")
        search_papers("blockchain consensus", category="cs.CR")
        search_papers("author:Satoshi", max_results=10)
    """
    _rate_limit()

    # Build search query
    search_query = query
    if category:
        search_query = f"cat:{category} AND ({query})"

    sort_order = "descending"
    if sort_by == "relevance":
        sort_by = "relevance"
        sort_order = None

    params = {
        "search_query": f"all:{search_query}",
        "start": 0,
        "max_results": min(max_results, 100),
    }

    if sort_order:
        params["sortBy"] = sort_by
        params["sortOrder"] = sort_order

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    # Parse XML response
    papers = _parse_arxiv_response(response.text)

    return {
        "query": query,
        "category": category,
        "total_results": len(papers),
        "papers": papers,
    }


def get_paper(arxiv_id: str) -> dict:
    """
    Get details of a specific paper by arXiv ID.

    Args:
        arxiv_id: arXiv ID (e.g., "2301.07041", "2301.07041v1")

    Returns:
        Dict with full paper details

    Use case: Get specific paper details

    Example:
        get_paper("2301.07041")  # Attention paper
    """
    _rate_limit()

    # Clean up ID (remove version if not specified)
    clean_id = arxiv_id.replace("arXiv:", "").strip()

    params = {
        "id_list": clean_id,
        "max_results": 1,
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    papers = _parse_arxiv_response(response.text)

    if not papers:
        return {"error": "Paper not found", "arxiv_id": arxiv_id}

    return papers[0]


def get_recent_papers(category: str, max_results: int = 20) -> dict:
    """
    Get recent papers in a category.

    Args:
        category: arXiv category (e.g., "cs.AI", "q-fin.TR")
        max_results: Maximum number of results

    Returns:
        Dict with recent papers in the category

    Use case: Stay updated on latest research

    Example:
        get_recent_papers("cs.LG")  # Recent ML papers
        get_recent_papers("q-fin.TR")  # Recent trading papers
    """
    _rate_limit()

    params = {
        "search_query": f"cat:{category}",
        "start": 0,
        "max_results": min(max_results, 100),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    papers = _parse_arxiv_response(response.text)

    return {
        "category": category,
        "category_name": CATEGORIES.get(category, category),
        "total_results": len(papers),
        "papers": papers,
    }


def search_by_author(author_name: str, max_results: int = 20) -> dict:
    """
    Search for papers by a specific author.

    Args:
        author_name: Author name (e.g., "Yoshua Bengio")
        max_results: Maximum number of results

    Returns:
        Dict with papers by the author

    Example:
        search_by_author("Yann LeCun")
    """
    _rate_limit()

    params = {
        "search_query": f"au:{author_name}",
        "start": 0,
        "max_results": min(max_results, 100),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }

    response = requests.get(BASE_URL, params=params)
    response.raise_for_status()

    papers = _parse_arxiv_response(response.text)

    return {
        "author": author_name,
        "total_results": len(papers),
        "papers": papers,
    }


def _parse_arxiv_response(xml_text: str) -> list:
    """Parse arXiv API XML response into list of papers."""
    # Define namespaces
    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }

    root = ET.fromstring(xml_text)
    papers = []

    for entry in root.findall("atom:entry", ns):
        # Extract arXiv ID from the id URL
        id_url = entry.find("atom:id", ns).text
        arxiv_id = id_url.split("/abs/")[-1] if "/abs/" in id_url else id_url

        # Get title (clean up whitespace)
        title = entry.find("atom:title", ns).text
        title = " ".join(title.split())

        # Get abstract (clean up whitespace)
        abstract = entry.find("atom:summary", ns).text
        abstract = " ".join(abstract.split()) if abstract else ""

        # Get authors
        authors = [
            author.find("atom:name", ns).text
            for author in entry.findall("atom:author", ns)
        ]

        # Get dates
        published = entry.find("atom:published", ns).text[:10]  # YYYY-MM-DD
        updated = entry.find("atom:updated", ns).text[:10]

        # Get categories
        categories = [
            cat.get("term")
            for cat in entry.findall("atom:category", ns)
        ]
        primary_category = entry.find("arxiv:primary_category", ns)
        if primary_category is not None:
            primary_cat = primary_category.get("term")
        else:
            primary_cat = categories[0] if categories else None

        # Get links
        links = {}
        for link in entry.findall("atom:link", ns):
            link_type = link.get("type", "")
            if "pdf" in link_type:
                links["pdf"] = link.get("href")
            elif link.get("rel") == "alternate":
                links["abstract"] = link.get("href")

        # Get comment if available
        comment_elem = entry.find("arxiv:comment", ns)
        comment = comment_elem.text if comment_elem is not None else None

        # Get DOI if available
        doi_elem = entry.find("arxiv:doi", ns)
        doi = doi_elem.text if doi_elem is not None else None

        papers.append({
            "arxiv_id": arxiv_id,
            "title": title,
            "authors": authors,
            "abstract": abstract[:500] + "..." if len(abstract) > 500 else abstract,
            "full_abstract": abstract,
            "published": published,
            "updated": updated,
            "primary_category": primary_cat,
            "categories": categories,
            "pdf_url": links.get("pdf", f"https://arxiv.org/pdf/{arxiv_id}.pdf"),
            "abstract_url": links.get("abstract", f"https://arxiv.org/abs/{arxiv_id}"),
            "comment": comment,
            "doi": doi,
        })

    return papers


# ============ HELPER FUNCTIONS ============

def get_ai_papers(query: str = "large language model", max_results: int = 20) -> dict:
    """
    Get AI/ML papers on a topic.

    Returns: Papers from cs.AI, cs.LG, cs.CL categories
    """
    return search_papers(
        query,
        max_results=max_results,
        category="cs.LG"
    )


def get_crypto_papers(query: str = "blockchain", max_results: int = 20) -> dict:
    """
    Get cryptography and blockchain papers.

    Returns: Papers from cs.CR category
    """
    return search_papers(
        query,
        max_results=max_results,
        category="cs.CR"
    )


def get_finance_papers(query: str = "trading", max_results: int = 20) -> dict:
    """
    Get quantitative finance papers.

    Returns: Papers from q-fin categories
    """
    return search_papers(
        query,
        max_results=max_results,
        category="q-fin.TR"
    )


def list_categories() -> dict:
    """
    List available arXiv categories.

    Returns: Dict of category codes and names
    """
    return {
        "categories": CATEGORIES,
        "total": len(CATEGORIES),
    }


def format_citation(paper: dict, style: str = "apa") -> str:
    """
    Format paper as citation.

    Args:
        paper: Paper dict from search/get
        style: Citation style ("apa", "bibtex")

    Returns:
        Formatted citation string
    """
    authors = paper.get("authors", [])
    title = paper.get("title", "")
    year = paper.get("published", "")[:4]
    arxiv_id = paper.get("arxiv_id", "")

    if style == "bibtex":
        first_author = authors[0].split()[-1] if authors else "unknown"
        return f"""@article{{{first_author}{year},
  title={{{title}}},
  author={{{" and ".join(authors)}}},
  journal={{arXiv preprint arXiv:{arxiv_id}}},
  year={{{year}}}
}}"""
    else:  # APA
        if len(authors) > 2:
            author_str = f"{authors[0]}, et al."
        elif len(authors) == 2:
            author_str = f"{authors[0]} & {authors[1]}"
        else:
            author_str = authors[0] if authors else "Unknown"

        return f"{author_str} ({year}). {title}. arXiv preprint arXiv:{arxiv_id}."


if __name__ == "__main__":
    print("=== Recent AI Papers ===")
    result = get_ai_papers("transformer", max_results=5)
    for p in result.get("papers", [])[:3]:
        print(f"\n{p['title'][:60]}...")
        print(f"  Authors: {', '.join(p['authors'][:2])}")
        print(f"  Date: {p['published']}")
        print(f"  PDF: {p['pdf_url']}")
