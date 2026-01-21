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

    # General
    "wikidata": "integrations.general.wikidata",
}


def print_usage():
    """Print usage information."""
    print("""
Ralph Data Fetch CLI

Usage:
    python fetch.py <module> <method> [args_json]

Available modules:
    Crypto:   coingecko, blocklens, defillama, l2beat, etherscan, thegraph, dune
    Stocks:   yfinance, finnhub, fred, sec, fmp
    Research: worldbank, imf, wikipedia, arxiv, serper, pubmed
    General:  wikidata

Examples:
    python fetch.py coingecko get_price '["bitcoin"]'
    python fetch.py blocklens get_market_cycle_indicators
    python fetch.py blocklens get_holder_supply '{"start_date":"2024-01-01","limit":365}'
    python fetch.py yfinance get_price_history '{"symbol":"SPY","start":"2024-01-01"}'
    python fetch.py defillama get_l2_comparison

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

        # Call method with appropriate argument passing
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

    # Call the method
    call_method(module_name, method_name, args_json)


if __name__ == "__main__":
    main()
