# -*- coding: utf-8 -*-
"""
Google Scholar Integration (via scholarly library)

USE FOR:
- Academic paper search
- Citation analysis
- Author profiles and h-index
- Research trends
- Finding highly-cited papers
- Academic due diligence

DO NOT USE FOR:
- Pre-prints (use arxiv)
- Medical papers (use pubmed)
- News articles (use news_aggregator)
- Company data (use crunchbase)

RATE LIMIT: Use with delays to avoid blocking
API KEY: Not required (uses scholarly library)

Note: Google Scholar doesn't have an official API.
This uses the 'scholarly' library which scrapes Google Scholar.
For production use, consider SerpAPI or ProxyCrawl.
"""

import time
from typing import List, Dict, Optional
from datetime import datetime
import warnings

# Try to import scholarly, with fallback
try:
    from scholarly import scholarly, ProxyGenerator
    SCHOLARLY_AVAILABLE = True
except ImportError:
    SCHOLARLY_AVAILABLE = False
    warnings.warn(
        "scholarly library not installed. "
        "Install with: pip install scholarly"
    )

# Rate limiting
_last_request = 0
_min_interval = 5.0  # Be conservative to avoid blocking


def _rate_limit():
    """Respect rate limits to avoid blocking."""
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request = time.time()


def _check_available():
    """Check if scholarly is available."""
    if not SCHOLARLY_AVAILABLE:
        raise ImportError(
            "scholarly library not installed. "
            "Install with: pip install scholarly"
        )


def search_papers(query: str,
                  num_results: int = 20,
                  year_from: int = None,
                  year_to: int = None) -> dict:
    """
    Search for academic papers on Google Scholar.

    Args:
        query: Search query
        num_results: Maximum number of results (1-100)
        year_from: Filter papers from this year
        year_to: Filter papers to this year

    Returns:
        Dict with list of papers

    Use case: Find academic research on a topic

    Example:
        search_papers("blockchain tokenization")
        search_papers("machine learning finance", year_from=2022)
    """
    _check_available()
    _rate_limit()

    # Build search query with year filters
    search_query = query

    papers = []
    search_result = scholarly.search_pubs(search_query)

    for i, paper in enumerate(search_result):
        if i >= num_results:
            break

        _rate_limit()

        # Get paper info
        bib = paper.get("bib", {})
        pub_year = bib.get("pub_year")

        # Filter by year if specified
        if pub_year:
            try:
                year = int(pub_year)
                if year_from and year < year_from:
                    continue
                if year_to and year > year_to:
                    continue
            except (ValueError, TypeError):
                pass

        papers.append({
            "title": bib.get("title"),
            "authors": bib.get("author", "").split(" and ") if bib.get("author") else [],
            "abstract": bib.get("abstract", "")[:500] if bib.get("abstract") else "",
            "year": pub_year,
            "venue": bib.get("venue"),
            "publisher": bib.get("publisher"),
            "citations": paper.get("num_citations", 0),
            "url": paper.get("pub_url"),
            "eprint_url": paper.get("eprint_url"),
            "scholar_url": f"https://scholar.google.com/scholar?q={query}",
        })

    return {
        "query": query,
        "year_range": f"{year_from or 'any'}-{year_to or 'any'}",
        "total_results": len(papers),
        "papers": papers,
    }


def get_paper_details(title: str) -> dict:
    """
    Get detailed information about a specific paper.

    Args:
        title: Paper title (exact or partial)

    Returns:
        Dict with full paper details

    Example:
        get_paper_details("Attention is all you need")
    """
    _check_available()
    _rate_limit()

    search_result = scholarly.search_pubs(title)

    try:
        paper = next(search_result)
    except StopIteration:
        return {"error": "Paper not found", "title": title}

    # Fill in details
    _rate_limit()
    try:
        paper = scholarly.fill(paper)
    except Exception:
        pass  # Some details may not be available

    bib = paper.get("bib", {})

    # Get citing papers
    citedby_url = paper.get("citedby_url")

    return {
        "title": bib.get("title"),
        "authors": bib.get("author", "").split(" and ") if bib.get("author") else [],
        "abstract": bib.get("abstract"),
        "year": bib.get("pub_year"),
        "venue": bib.get("venue"),
        "publisher": bib.get("publisher"),
        "volume": bib.get("volume"),
        "pages": bib.get("pages"),
        "citations": paper.get("num_citations", 0),
        "url": paper.get("pub_url"),
        "eprint_url": paper.get("eprint_url"),
        "citedby_url": citedby_url,
        "related_articles_url": paper.get("related_articles_url"),
    }


def get_author_profile(author_name: str) -> dict:
    """
    Get author profile from Google Scholar.

    Args:
        author_name: Author name

    Returns:
        Dict with author profile and publications

    Example:
        get_author_profile("Geoffrey Hinton")
        get_author_profile("Vitalik Buterin")
    """
    _check_available()
    _rate_limit()

    search_result = scholarly.search_author(author_name)

    try:
        author = next(search_result)
    except StopIteration:
        return {"error": "Author not found", "name": author_name}

    # Fill in author details
    _rate_limit()
    try:
        author = scholarly.fill(author)
    except Exception:
        pass

    # Parse publications
    publications = []
    for pub in author.get("publications", [])[:20]:
        bib = pub.get("bib", {})
        publications.append({
            "title": bib.get("title"),
            "year": bib.get("pub_year"),
            "citations": pub.get("num_citations", 0),
        })

    return {
        "name": author.get("name"),
        "affiliation": author.get("affiliation"),
        "email_domain": author.get("email_domain"),
        "interests": author.get("interests", []),
        "citations": author.get("citedby", 0),
        "h_index": author.get("hindex", 0),
        "i10_index": author.get("i10index", 0),
        "scholar_url": f"https://scholar.google.com/citations?user={author.get('scholar_id', '')}",
        "publications_count": len(author.get("publications", [])),
        "top_publications": sorted(publications, key=lambda x: x.get("citations", 0), reverse=True)[:10],
    }


def get_citations(paper_title: str, num_citations: int = 20) -> dict:
    """
    Get papers that cite a specific paper.

    Args:
        paper_title: Title of the paper
        num_citations: Number of citing papers to return

    Returns:
        Dict with citing papers

    Example:
        get_citations("Bitcoin: A Peer-to-Peer Electronic Cash System")
    """
    _check_available()
    _rate_limit()

    search_result = scholarly.search_pubs(paper_title)

    try:
        paper = next(search_result)
    except StopIteration:
        return {"error": "Paper not found", "title": paper_title}

    citations = []

    try:
        _rate_limit()
        citing_papers = scholarly.citedby(paper)

        for i, citing in enumerate(citing_papers):
            if i >= num_citations:
                break

            _rate_limit()
            bib = citing.get("bib", {})
            citations.append({
                "title": bib.get("title"),
                "authors": bib.get("author", "").split(" and ") if bib.get("author") else [],
                "year": bib.get("pub_year"),
                "citations": citing.get("num_citations", 0),
            })
    except Exception as e:
        return {
            "paper": paper_title,
            "error": f"Could not retrieve citations: {str(e)}",
            "total_citations": paper.get("num_citations", 0),
        }

    return {
        "paper": paper_title,
        "total_citations": paper.get("num_citations", 0),
        "retrieved_citations": len(citations),
        "citing_papers": citations,
    }


def search_by_author(author_name: str, num_results: int = 20) -> dict:
    """
    Search papers by a specific author.

    Args:
        author_name: Author name
        num_results: Maximum number of papers

    Returns:
        Dict with author's papers

    Example:
        search_by_author("Satoshi Nakamoto")
    """
    _check_available()
    _rate_limit()

    query = f'author:"{author_name}"'
    search_result = scholarly.search_pubs(query)

    papers = []
    for i, paper in enumerate(search_result):
        if i >= num_results:
            break

        _rate_limit()
        bib = paper.get("bib", {})

        papers.append({
            "title": bib.get("title"),
            "authors": bib.get("author", "").split(" and ") if bib.get("author") else [],
            "year": bib.get("pub_year"),
            "venue": bib.get("venue"),
            "citations": paper.get("num_citations", 0),
            "url": paper.get("pub_url"),
        })

    return {
        "author": author_name,
        "total_results": len(papers),
        "papers": sorted(papers, key=lambda x: x.get("citations", 0), reverse=True),
    }


def get_highly_cited(query: str,
                     min_citations: int = 100,
                     num_results: int = 20) -> dict:
    """
    Get highly cited papers on a topic.

    Args:
        query: Search query
        min_citations: Minimum citation count
        num_results: Maximum number of results

    Returns:
        Dict with highly cited papers

    Example:
        get_highly_cited("blockchain", min_citations=500)
    """
    _check_available()
    _rate_limit()

    search_result = scholarly.search_pubs(query)

    papers = []
    checked = 0
    max_to_check = num_results * 5  # Check more papers to find highly cited ones

    for paper in search_result:
        if checked >= max_to_check or len(papers) >= num_results:
            break

        checked += 1

        citations = paper.get("num_citations", 0)
        if citations >= min_citations:
            _rate_limit()
            bib = paper.get("bib", {})

            papers.append({
                "title": bib.get("title"),
                "authors": bib.get("author", "").split(" and ") if bib.get("author") else [],
                "year": bib.get("pub_year"),
                "venue": bib.get("venue"),
                "citations": citations,
                "url": paper.get("pub_url"),
            })

    return {
        "query": query,
        "min_citations": min_citations,
        "total_results": len(papers),
        "papers": sorted(papers, key=lambda x: x.get("citations", 0), reverse=True),
    }


# ============ HELPER FUNCTIONS ============

def get_blockchain_papers(num_results: int = 20) -> dict:
    """
    Get academic papers on blockchain.

    Returns: Blockchain research papers
    """
    return search_papers(
        "blockchain consensus mechanism",
        num_results=num_results,
        year_from=2018
    )


def get_defi_papers(num_results: int = 20) -> dict:
    """
    Get academic papers on DeFi.

    Returns: DeFi research papers
    """
    return search_papers(
        "decentralized finance DeFi",
        num_results=num_results,
        year_from=2020
    )


def get_tokenization_papers(num_results: int = 20) -> dict:
    """
    Get academic papers on asset tokenization.

    Returns: Tokenization research papers
    """
    return search_papers(
        "asset tokenization securities blockchain",
        num_results=num_results,
        year_from=2019
    )


def get_ml_finance_papers(num_results: int = 20) -> dict:
    """
    Get ML/AI papers in finance.

    Returns: ML finance papers
    """
    return search_papers(
        "machine learning finance trading",
        num_results=num_results,
        year_from=2020
    )


def format_citation_apa(paper: dict) -> str:
    """
    Format paper as APA citation.

    Args:
        paper: Paper dict from search results

    Returns:
        Formatted APA citation
    """
    authors = paper.get("authors", [])
    title = paper.get("title", "")
    year = paper.get("year", "n.d.")
    venue = paper.get("venue", "")

    if len(authors) > 2:
        author_str = f"{authors[0]}, et al."
    elif len(authors) == 2:
        author_str = f"{authors[0]} & {authors[1]}"
    elif len(authors) == 1:
        author_str = authors[0]
    else:
        author_str = "Unknown"

    return f"{author_str} ({year}). {title}. {venue}."


def format_citation_bibtex(paper: dict, key: str = None) -> str:
    """
    Format paper as BibTeX entry.

    Args:
        paper: Paper dict from search results
        key: BibTeX key (auto-generated if not provided)

    Returns:
        BibTeX entry
    """
    authors = paper.get("authors", [])
    title = paper.get("title", "")
    year = paper.get("year", "")
    venue = paper.get("venue", "")

    if not key:
        first_author = authors[0].split()[-1] if authors else "unknown"
        key = f"{first_author}{year}"

    return f"""@article{{{key},
  title={{{title}}},
  author={{{" and ".join(authors)}}},
  journal={{{venue}}},
  year={{{year}}}
}}"""


def calculate_h_index(papers: List[dict]) -> int:
    """
    Calculate h-index from a list of papers.

    Args:
        papers: List of paper dicts with "citations" field

    Returns:
        h-index value
    """
    citations = sorted(
        [p.get("citations", 0) for p in papers],
        reverse=True
    )

    h = 0
    for i, c in enumerate(citations, 1):
        if c >= i:
            h = i
        else:
            break

    return h


if __name__ == "__main__":
    if SCHOLARLY_AVAILABLE:
        print("=== Google Scholar Test ===")
        result = search_papers("blockchain tokenization", num_results=3)
        for p in result.get("papers", []):
            print(f"\n{p['title'][:60]}...")
            print(f"  Citations: {p['citations']}")
            print(f"  Year: {p['year']}")
    else:
        print("scholarly library not installed.")
        print("Install with: pip install scholarly")
