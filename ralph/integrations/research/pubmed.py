# -*- coding: utf-8 -*-
"""
PubMed / NCBI API Integration

USE FOR:
- Biomedical literature
- Medical research papers
- Clinical trials data
- Drug and pharmaceutical research
- Healthcare industry research
- Life sciences papers

DO NOT USE FOR:
- CS/AI papers (use arxiv)
- Finance papers (use arxiv q-fin)
- General knowledge (use wikipedia)
- News (use serper)

RATE LIMIT: 3 requests/second (without API key), 10/second (with key)
API KEY: Optional (NCBI_API_KEY) but recommended

Official docs: https://www.ncbi.nlm.nih.gov/books/NBK25500/
"""

import requests
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
import time

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# Rate limiting
_last_request = 0
_min_interval = 0.34  # ~3 requests per second without API key


def _rate_limit():
    """Respect NCBI rate limits."""
    global _last_request
    api_key = os.environ.get("NCBI_API_KEY")
    interval = 0.1 if api_key else _min_interval

    elapsed = time.time() - _last_request
    if elapsed < interval:
        time.sleep(interval - elapsed)
    _last_request = time.time()


def _get_params() -> dict:
    """Get base params with optional API key."""
    params = {}
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    return params


def search(query: str, max_results: int = 20,
           sort: str = "relevance",
           date_from: str = None, date_to: str = None) -> dict:
    """
    Search PubMed for articles.

    Args:
        query: Search query (supports MeSH terms, author names, etc.)
        max_results: Maximum number of results (1-10000)
        sort: Sort order ("relevance", "pub_date", "first_author")
        date_from: Start date (YYYY/MM/DD)
        date_to: End date (YYYY/MM/DD)

    Returns:
        Dict with list of article IDs and count

    Use case: Find medical/bio research papers

    Example:
        search("COVID-19 vaccine efficacy")
        search("CRISPR gene editing", max_results=50)
        search("author:Smith cancer", sort="pub_date")
    """
    _rate_limit()

    params = _get_params()
    params.update({
        "db": "pubmed",
        "term": query,
        "retmax": min(max_results, 10000),
        "retmode": "json",
        "sort": sort,
        "usehistory": "y",
    })

    if date_from:
        params["mindate"] = date_from
    if date_to:
        params["maxdate"] = date_to
    if date_from or date_to:
        params["datetype"] = "pdat"  # Publication date

    response = requests.get(f"{BASE_URL}/esearch.fcgi", params=params)
    response.raise_for_status()
    data = response.json()

    result = data.get("esearchresult", {})
    pmids = result.get("idlist", [])

    # Get details for the PMIDs
    articles = []
    if pmids:
        articles = _fetch_summaries(pmids[:max_results])

    return {
        "query": query,
        "total_count": int(result.get("count", 0)),
        "returned_count": len(articles),
        "articles": articles,
        "query_translation": result.get("querytranslation"),
    }


def _fetch_summaries(pmids: List[str]) -> list:
    """Fetch article summaries for a list of PMIDs."""
    if not pmids:
        return []

    _rate_limit()

    params = _get_params()
    params.update({
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    })

    response = requests.get(f"{BASE_URL}/esummary.fcgi", params=params)
    response.raise_for_status()
    data = response.json()

    articles = []
    result = data.get("result", {})

    for pmid in pmids:
        if pmid not in result:
            continue

        article = result[pmid]
        articles.append({
            "pmid": pmid,
            "title": article.get("title", ""),
            "authors": [
                a.get("name", "") for a in article.get("authors", [])
            ],
            "source": article.get("source", ""),  # Journal name
            "pub_date": article.get("pubdate", ""),
            "volume": article.get("volume", ""),
            "issue": article.get("issue", ""),
            "pages": article.get("pages", ""),
            "doi": _extract_doi(article.get("articleids", [])),
            "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        })

    return articles


def _extract_doi(articleids: list) -> Optional[str]:
    """Extract DOI from article IDs list."""
    for aid in articleids:
        if aid.get("idtype") == "doi":
            return aid.get("value")
    return None


def get_abstract(pmid: str) -> dict:
    """
    Get the abstract for a specific article.

    Args:
        pmid: PubMed ID

    Returns:
        Dict with full abstract and metadata

    Use case: Read article abstract

    Example:
        get_abstract("32491334")
    """
    _rate_limit()

    params = _get_params()
    params.update({
        "db": "pubmed",
        "id": pmid,
        "retmode": "xml",
    })

    response = requests.get(f"{BASE_URL}/efetch.fcgi", params=params)
    response.raise_for_status()

    # Parse XML
    root = ET.fromstring(response.text)
    article = root.find(".//PubmedArticle")

    if article is None:
        return {"error": "Article not found", "pmid": pmid}

    # Extract abstract
    abstract_elem = article.find(".//Abstract")
    if abstract_elem is not None:
        abstract_texts = []
        for text in abstract_elem.findall(".//AbstractText"):
            label = text.get("Label", "")
            content = text.text or ""
            if label:
                abstract_texts.append(f"{label}: {content}")
            else:
                abstract_texts.append(content)
        abstract = " ".join(abstract_texts)
    else:
        abstract = ""

    # Extract title
    title = article.findtext(".//ArticleTitle", "")

    # Extract authors
    authors = []
    for author in article.findall(".//Author"):
        last_name = author.findtext("LastName", "")
        first_name = author.findtext("ForeName", "")
        if last_name:
            authors.append(f"{last_name} {first_name}".strip())

    # Extract journal info
    journal = article.findtext(".//Journal/Title", "")

    # Extract publication date
    pub_date_elem = article.find(".//PubDate")
    if pub_date_elem is not None:
        year = pub_date_elem.findtext("Year", "")
        month = pub_date_elem.findtext("Month", "")
        day = pub_date_elem.findtext("Day", "")
        pub_date = f"{year} {month} {day}".strip()
    else:
        pub_date = ""

    # Extract keywords
    keywords = [
        kw.text for kw in article.findall(".//Keyword")
        if kw.text
    ]

    # Extract MeSH terms
    mesh_terms = [
        mesh.findtext("DescriptorName", "")
        for mesh in article.findall(".//MeshHeading")
    ]

    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal,
        "pub_date": pub_date,
        "keywords": keywords,
        "mesh_terms": mesh_terms,
        "pubmed_url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
    }


def get_article_details(pmid: str) -> dict:
    """
    Get full metadata for an article.

    Args:
        pmid: PubMed ID

    Returns:
        Dict with comprehensive article information

    Use case: Full article analysis

    Example:
        get_article_details("32491334")
    """
    # Get abstract (includes most metadata)
    article = get_abstract(pmid)

    if "error" in article:
        return article

    # Get citation info
    _rate_limit()

    params = _get_params()
    params.update({
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "linkname": "pubmed_pubmed_citedin",
        "retmode": "json",
    })

    try:
        response = requests.get(f"{BASE_URL}/elink.fcgi", params=params)
        response.raise_for_status()
        data = response.json()

        # Count citations
        linksets = data.get("linksets", [])
        cited_by = 0
        if linksets:
            links = linksets[0].get("linksetdbs", [])
            for link in links:
                if link.get("linkname") == "pubmed_pubmed_citedin":
                    cited_by = len(link.get("links", []))

        article["cited_by_count"] = cited_by
    except Exception:
        article["cited_by_count"] = None

    return article


def get_related_articles(pmid: str, max_results: int = 10) -> dict:
    """
    Get articles related to a given article.

    Args:
        pmid: PubMed ID
        max_results: Maximum related articles

    Returns:
        Dict with related articles

    Use case: Find similar research

    Example:
        get_related_articles("32491334")
    """
    _rate_limit()

    params = _get_params()
    params.update({
        "dbfrom": "pubmed",
        "db": "pubmed",
        "id": pmid,
        "linkname": "pubmed_pubmed",
        "retmode": "json",
    })

    response = requests.get(f"{BASE_URL}/elink.fcgi", params=params)
    response.raise_for_status()
    data = response.json()

    # Extract related PMIDs
    related_pmids = []
    linksets = data.get("linksets", [])
    if linksets:
        links = linksets[0].get("linksetdbs", [])
        for link in links:
            if link.get("linkname") == "pubmed_pubmed":
                related_pmids = link.get("links", [])[:max_results]

    # Fetch summaries
    if related_pmids:
        articles = _fetch_summaries(related_pmids)
    else:
        articles = []

    return {
        "source_pmid": pmid,
        "related_count": len(articles),
        "related_articles": articles,
    }


# ============ HELPER FUNCTIONS ============

def search_clinical_trials(query: str, max_results: int = 20) -> dict:
    """
    Search for clinical trial publications.

    Args:
        query: Search query
        max_results: Maximum results

    Returns:
        Clinical trial related publications

    Example:
        search_clinical_trials("mRNA vaccine")
    """
    return search(
        f"{query} AND (clinical trial[pt] OR randomized controlled trial[pt])",
        max_results=max_results
    )


def search_reviews(query: str, max_results: int = 20) -> dict:
    """
    Search for review articles.

    Args:
        query: Search query
        max_results: Maximum results

    Returns:
        Review articles on the topic

    Example:
        search_reviews("CRISPR applications")
    """
    return search(
        f"{query} AND (review[pt] OR systematic review[pt] OR meta-analysis[pt])",
        max_results=max_results
    )


def search_recent(query: str, days: int = 30, max_results: int = 20) -> dict:
    """
    Search for recent publications.

    Args:
        query: Search query
        days: Number of days back
        max_results: Maximum results

    Returns:
        Recent publications

    Example:
        search_recent("COVID-19", days=7)
    """
    from datetime import datetime, timedelta

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    return search(
        query,
        max_results=max_results,
        date_from=start_date.strftime("%Y/%m/%d"),
        date_to=end_date.strftime("%Y/%m/%d"),
        sort="pub_date"
    )


def format_citation(article: dict, style: str = "apa") -> str:
    """
    Format article as citation.

    Args:
        article: Article dict from search/get
        style: Citation style ("apa", "vancouver")

    Returns:
        Formatted citation string
    """
    authors = article.get("authors", [])
    title = article.get("title", "")
    journal = article.get("journal") or article.get("source", "")
    year = article.get("pub_date", "")[:4]
    volume = article.get("volume", "")
    issue = article.get("issue", "")
    pages = article.get("pages", "")
    pmid = article.get("pmid", "")

    if style == "vancouver":
        # Vancouver style (numbered)
        author_str = ", ".join(authors[:6])
        if len(authors) > 6:
            author_str += ", et al"
        return f"{author_str}. {title} {journal}. {year};{volume}({issue}):{pages}. PMID: {pmid}"
    else:
        # APA style
        if len(authors) > 2:
            author_str = f"{authors[0]}, et al."
        elif len(authors) == 2:
            author_str = f"{authors[0]} & {authors[1]}"
        else:
            author_str = authors[0] if authors else "Unknown"

        return f"{author_str} ({year}). {title} {journal}, {volume}({issue}), {pages}."


if __name__ == "__main__":
    print("=== PubMed Search Test ===")
    result = search("CRISPR gene editing", max_results=5)
    print(f"Found {result['total_count']} articles")

    for article in result.get("articles", [])[:3]:
        print(f"\n{article['title'][:60]}...")
        print(f"  Authors: {', '.join(article['authors'][:2])}")
        print(f"  Journal: {article['source']}")
        print(f"  PMID: {article['pmid']}")
