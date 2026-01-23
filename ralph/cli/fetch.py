#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ralph Data Fetch CLI

Usage:
    python fetch.py <module> <method> [args_json]

Examples:
    python fetch.py coingecko get_price '["bitcoin","ethereum"]'
    python fetch.py blocklens get_market_cycle_indicators
    python fetch.py blocklens get_holder_supply '{"start_date":"2024-01-01","limit":365}'
    python fetch.py defillama get_protocol_tvl '{"protocol":"aave"}'
    python fetch.py yfinance get_price_history '{"symbol":"BTC-USD","start":"2024-01-01"}'

Analytics (series analysis):
    python fetch.py analytics analyze '{"file":"results/series/BTC_MVRV.json"}'
    python fetch.py analytics basic_stats '{"file":"results/series/BTC_price.json"}'
    python fetch.py analytics trend_direction '{"file":"results/series/BTC_price.json","window":30}'
    python fetch.py analytics correlation '{"file1":"results/series/BTC_price.json","file2":"results/series/BTC_MVRV.json"}'

Output:
    JSON to stdout on success
    {"error": "message"} on failure
"""

import sys
import os
import json
import importlib

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add ralph directory to path for imports
RALPH_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RALPH_DIR)

# Import and enable resource tracking
try:
    from integrations.core.http_wrapper import patch_requests
    from integrations.core.tracker import tracker
    from integrations.core.pricing import calculate_api_cost

    # Apply HTTP tracking patch
    patch_requests()

    # Initialize tracker from environment variables
    _SESSION_ID = os.environ.get("RALPH_SESSION_ID")
    _STATE_DIR = os.environ.get("RALPH_STATE_DIR")
    if _SESSION_ID and _STATE_DIR:
        tracker.start_session(_SESSION_ID, _STATE_DIR)

    _TRACKING_ENABLED = True
except ImportError:
    # Tracking module not available - continue without it
    _TRACKING_ENABLED = False
    tracker = None


# Module mapping: short name -> full import path
MODULES = {
    # Crypto
    "coingecko": "integrations.crypto.coingecko",
    "blocklens": "integrations.crypto.blocklens",
    "defillama": "integrations.crypto.defillama",
    "l2beat": "integrations.crypto.l2beat",
    "etherscan": "integrations.crypto.etherscan",
    "thegraph": "integrations.crypto.thegraph",
    "dune": "integrations.crypto.dune",

    # Stocks
    "yfinance": "integrations.stocks.yfinance_client",
    "finnhub": "integrations.stocks.finnhub",
    "fred": "integrations.stocks.fred",
    "sec": "integrations.stocks.sec_edgar",
    "fmp": "integrations.stocks.fmp",

    # Research
    "worldbank": "integrations.research.worldbank",
    "imf": "integrations.research.imf",
    "wikipedia": "integrations.research.wikipedia",
    "arxiv": "integrations.research.arxiv",
    "serper": "integrations.research.serper",
    "pubmed": "integrations.research.pubmed",
    "crunchbase": "integrations.research.crunchbase",
    "sec_edgar": "integrations.research.sec_edgar",
    "google_scholar": "integrations.research.google_scholar",
    "news_aggregator": "integrations.research.news_aggregator",

    # General
    "wikidata": "integrations.general.wikidata",

    # Analytics
    "analytics": "integrations.analytics.series_analyzer",
}


def print_usage():
    """Print usage information."""
    print("""
Ralph Data Fetch CLI

Usage:
    python fetch.py <module> <method> [args_json]

Available modules:
    Crypto:    coingecko, blocklens, defillama, l2beat, etherscan, thegraph, dune
    Stocks:    yfinance, finnhub, fred, sec, fmp
    Research:  worldbank, imf, wikipedia, arxiv, serper, pubmed, crunchbase, sec_edgar, google_scholar, news_aggregator
    General:   wikidata
    Analytics: analytics (series analysis for chart data)

Examples:
    python fetch.py coingecko get_price '["bitcoin"]'
    python fetch.py blocklens get_market_cycle_indicators
    python fetch.py blocklens get_holder_supply '{"start_date":"2024-01-01","limit":365}'
    python fetch.py yfinance get_price_history '{"symbol":"SPY","start":"2024-01-01"}'
    python fetch.py defillama get_l2_comparison

Analytics (series analysis):
    python fetch.py analytics basic_stats '{"file":"results/series/BTC_price.json"}'
    python fetch.py analytics trend_direction '{"file":"results/series/BTC_price.json","window":30}'
    python fetch.py analytics correlation '{"file1":"results/series/BTC_price.json","file2":"results/series/BTC_MVRV.json"}'
    python fetch.py analytics detect_anomalies '{"file":"results/series/BTC_price.json","column":"value","z_threshold":2.5}'
    python fetch.py analytics volatility_regime '{"file":"results/series/BTC_price.json","column":"value"}'

To list methods for a module:
    python fetch.py <module> --list
""", file=sys.stderr)


def list_methods(module_name: str) -> None:
    """List available methods for a module."""
    if module_name not in MODULES:
        print(json.dumps({"error": f"Unknown module: {module_name}. Available: {list(MODULES.keys())}"}))
        return

    try:
        module = importlib.import_module(MODULES[module_name])
        methods = [m for m in dir(module) if not m.startswith('_') and callable(getattr(module, m))]
        print(json.dumps({"module": module_name, "methods": methods}))
    except Exception as e:
        print(json.dumps({"error": f"Failed to import {module_name}: {str(e)}"}))


def load_series_data(file_path: str, column: str = None) -> list:
    """Load time series data from JSON file.

    Handles multiple formats:
    1. {"values": [...], "labels": [...]} - returns values
    2. [{"date": "...", "value": 100}, ...] - extracts column values
    3. Raw list [100, 101, 102] - returns as-is
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle different data formats
    if isinstance(data, list):
        # Check if list of dicts (e.g., [{"date": "...", "value": 100}])
        if data and isinstance(data[0], dict) and column:
            return [item.get(column, 0) for item in data if column in item]
        return data
    elif isinstance(data, dict):
        # Standard series format: {"values": [...], "labels": [...]}
        for key in ["values", "data", "series", "results"]:
            if key in data:
                values = data[key]
                # If values is list of dicts, extract column
                if values and isinstance(values[0], dict) and column:
                    return [item.get(column, 0) for item in values if column in item]
                return values
        # Return dict as-is if no known key found
        return data
    return data


def load_series_with_dates(file_path: str) -> tuple:
    """Load series data with both values and dates/labels."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    values = []
    dates = []

    if isinstance(data, list):
        if data and isinstance(data[0], dict):
            # List of dicts: [{"date": "...", "value": 100}]
            for item in data:
                if "value" in item:
                    values.append(item["value"])
                    dates.append(item.get("date", item.get("date_processed", "")))
        else:
            values = data
    elif isinstance(data, dict):
        values = data.get("values", data.get("data", []))
        dates = data.get("labels", data.get("dates", []))

    return values, dates


def call_method(module_name: str, method_name: str, args_json: str = None) -> None:
    """Call a method from a module and print result as JSON."""

    # Validate module
    if module_name not in MODULES:
        print(json.dumps({"error": f"Unknown module: {module_name}", "available": list(MODULES.keys())}))
        sys.exit(1)

    try:
        # Import module
        module = importlib.import_module(MODULES[module_name])

        # Get method
        if not hasattr(module, method_name):
            methods = [m for m in dir(module) if not m.startswith('_') and callable(getattr(module, m))]
            print(json.dumps({"error": f"Method '{method_name}' not found in {module_name}", "available_methods": methods}))
            sys.exit(1)

        method = getattr(module, method_name)

        # Parse args
        if args_json:
            args = json.loads(args_json)
        else:
            args = None

        # Special handling for analytics module - load data from files
        if module_name == "analytics" and isinstance(args, dict):
            # Handle file-based analytics calls
            if "file" in args:
                file_path = args.pop("file")
                column = args.pop("column", None)
                # Load data with optional column extraction
                data = load_series_data(file_path, column)
                result = method(data, **args)
            elif "file1" in args and "file2" in args:
                # Correlation between two series
                column1 = args.pop("column1", None)
                column2 = args.pop("column2", None)
                data1 = load_series_data(args.pop("file1"), column1)
                data2 = load_series_data(args.pop("file2"), column2)
                result = method(data1, data2, **args)
            else:
                # Pass args as-is for functions not requiring file loading
                result = method(**args)
        else:
            # Standard call handling for other modules
            # - None: no args
            # - List: pass as first positional arg (e.g., get_price(["bitcoin"]))
            # - Dict: pass as kwargs (e.g., get_price_history(coin_id="bitcoin", days=30))
            # - Other: pass as single arg
            if args is None:
                result = method()
            elif isinstance(args, list):
                # Pass list as first argument (don't unpack!)
                # This is for functions like get_price(coin_ids: List[str])
                result = method(args)
            elif isinstance(args, dict):
                result = method(**args)
            else:
                result = method(args)

        # Output result
        print(json.dumps(result, default=str, ensure_ascii=False))

    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON args: {str(e)}", "args_received": args_json}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e), "type": type(e).__name__}))
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    module_name = sys.argv[1]

    # Special case: list modules
    if module_name in ("--help", "-h", "help"):
        print_usage()
        sys.exit(0)

    if module_name == "--list-modules":
        print(json.dumps({"modules": list(MODULES.keys())}))
        sys.exit(0)

    if len(sys.argv) < 3:
        print(json.dumps({"error": "Method name required", "usage": "python fetch.py <module> <method> [args_json]"}))
        sys.exit(1)

    method_name = sys.argv[2]

    # Special case: list methods for module
    if method_name == "--list":
        list_methods(module_name)
        sys.exit(0)

    # Get optional args
    args_json = sys.argv[3] if len(sys.argv) > 3 else None

    # Set tracking context
    if _TRACKING_ENABLED and tracker:
        tracker.set_context(task_type=f"{module_name}.{method_name}")

    try:
        # Call the method
        call_method(module_name, method_name, args_json)
    finally:
        # End tracking session and save metrics
        if _TRACKING_ENABLED and tracker and tracker.is_active:
            tracker.end_session()


if __name__ == "__main__":
    main()
