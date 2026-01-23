"""
HTTP Request Wrapper for automatic tracking.

Patches the requests library to track all API calls without
modifying individual integration modules.

Usage:
    from integrations.core.http_wrapper import patch_requests, unpatch_requests

    # Enable automatic tracking
    patch_requests()

    # All subsequent requests.get/post/etc calls are now tracked
    response = requests.get("https://api.example.com/data")

    # Disable tracking (for testing)
    unpatch_requests()
"""

import requests
import time
from datetime import datetime
from functools import wraps
from urllib.parse import urlparse
from typing import Optional

from .tracker import tracker, APICallMetric
from .pricing import calculate_api_cost


# Store original request method
_original_request = requests.Session.request
_patched = False


# Domain to module mapping
DOMAIN_TO_MODULE = {
    # Crypto
    "api.coingecko.com": "coingecko",
    "pro-api.coingecko.com": "coingecko",
    "api.blocklens.io": "blocklens",
    "api.llama.fi": "defillama",
    "l2beat.com": "l2beat",
    "api.l2beat.com": "l2beat",
    "api.etherscan.io": "etherscan",
    "arbiscan.io": "etherscan",
    "optimistic.etherscan.io": "etherscan",
    "basescan.org": "etherscan",
    "api.thegraph.com": "thegraph",
    "gateway.thegraph.com": "thegraph",
    "api.dune.com": "dune",

    # Stocks/Finance
    "query1.finance.yahoo.com": "yfinance",
    "query2.finance.yahoo.com": "yfinance",
    "finnhub.io": "finnhub",
    "api.stlouisfed.org": "fred",
    "data.sec.gov": "sec_edgar",
    "www.sec.gov": "sec_edgar",
    "financialmodelingprep.com": "fmp",

    # Research
    "api.worldbank.org": "worldbank",
    "dataservices.imf.org": "imf",
    "en.wikipedia.org": "wikipedia",
    "ru.wikipedia.org": "wikipedia",
    "export.arxiv.org": "arxiv",
    "arxiv.org": "arxiv",
    "eutils.ncbi.nlm.nih.gov": "pubmed",
    "www.wikidata.org": "wikidata",
    "query.wikidata.org": "wikidata",

    # Search APIs
    "google.serper.dev": "serper",
    "newsapi.org": "news_aggregator",
    "cryptopanic.com": "news_aggregator",

    # Business
    "api.crunchbase.com": "crunchbase",
}


def _extract_module_name(url: str) -> str:
    """Extract module name from URL domain.

    Args:
        url: Full URL string

    Returns:
        Module name (e.g., coingecko, serper)
    """
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()

        # Try exact match first
        if host in DOMAIN_TO_MODULE:
            return DOMAIN_TO_MODULE[host]

        # Try partial match
        for domain, module in DOMAIN_TO_MODULE.items():
            if domain in host:
                return module

        # Fallback: use first part of domain
        parts = host.replace("www.", "").split(".")
        if parts:
            return parts[0]

        return "unknown"
    except Exception:
        return "unknown"


def _tracked_request(self, method: str, url: str, **kwargs):
    """Wrapped request method that tracks metrics.

    This replaces requests.Session.request to automatically
    record all HTTP calls to the tracker.
    """
    start_time = time.time()
    start_ts = datetime.utcnow().isoformat() + "Z"
    error: Optional[str] = None
    status_code = 0
    response_size = 0

    try:
        response = _original_request(self, method, url, **kwargs)
        status_code = response.status_code
        response_size = len(response.content) if response.content else 0
        return response
    except Exception as e:
        error = f"{type(e).__name__}: {str(e)}"
        raise
    finally:
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000
        module = _extract_module_name(url)

        # Create metric
        metric = APICallMetric(
            endpoint=url[:500],  # Truncate long URLs
            method=method.upper(),
            module=module,
            start_time=start_ts,
            end_time=datetime.utcnow().isoformat() + "Z",
            duration_ms=round(duration_ms, 2),
            status_code=status_code,
            response_size_bytes=response_size,
            error=error,
        )

        # Record to tracker
        tracker.record_api_call(metric)

        # Add API cost
        api_cost = calculate_api_cost(module)
        if api_cost > 0:
            tracker.add_api_cost(module, api_cost)


def patch_requests() -> None:
    """Apply monkey-patch to requests library.

    After calling this, all requests.get/post/etc calls
    will be automatically tracked.
    """
    global _patched
    if not _patched:
        requests.Session.request = _tracked_request
        _patched = True


def unpatch_requests() -> None:
    """Remove monkey-patch (for testing).

    Restores original requests behavior without tracking.
    """
    global _patched
    if _patched:
        requests.Session.request = _original_request
        _patched = False


def is_patched() -> bool:
    """Check if requests is currently patched.

    Returns:
        True if tracking is active
    """
    return _patched


class TrackedSession(requests.Session):
    """A requests Session that always tracks API calls.

    Use this for explicit tracking without global patching.

    Example:
        session = TrackedSession()
        response = session.get("https://api.example.com/data")
    """

    def request(self, method: str, url: str, **kwargs):
        """Make a request with automatic tracking."""
        start_time = time.time()
        start_ts = datetime.utcnow().isoformat() + "Z"
        error: Optional[str] = None
        status_code = 0
        response_size = 0

        try:
            response = super().request(method, url, **kwargs)
            status_code = response.status_code
            response_size = len(response.content) if response.content else 0
            return response
        except Exception as e:
            error = f"{type(e).__name__}: {str(e)}"
            raise
        finally:
            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000
            module = _extract_module_name(url)

            metric = APICallMetric(
                endpoint=url[:500],
                method=method.upper(),
                module=module,
                start_time=start_ts,
                end_time=datetime.utcnow().isoformat() + "Z",
                duration_ms=round(duration_ms, 2),
                status_code=status_code,
                response_size_bytes=response_size,
                error=error,
            )
            tracker.record_api_call(metric)

            api_cost = calculate_api_cost(module)
            if api_cost > 0:
                tracker.add_api_cost(module, api_cost)
