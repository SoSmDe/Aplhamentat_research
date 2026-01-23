"""
API and LLM Pricing Tables for Cost Calculation.

Prices as of January 2026 - update periodically.

Usage:
    from integrations.core.pricing import calculate_llm_cost, calculate_api_cost

    # LLM cost
    cost = calculate_llm_cost("claude-3-5-sonnet", input_tokens=15000, output_tokens=3500)
    # Returns: 0.0975

    # API cost
    cost = calculate_api_cost("serper", calls=10)
    # Returns: 0.01
"""

from typing import Dict, Tuple


# LLM Pricing (per 1M tokens)
# Format: (input_price, output_price)
LLM_PRICING: Dict[str, Tuple[float, float]] = {
    # Claude 3.5 family
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku": (1.00, 5.00),

    # Claude 3 family
    "claude-3-opus": (15.00, 75.00),
    "claude-3-opus-20240229": (15.00, 75.00),
    "claude-3-sonnet": (3.00, 15.00),
    "claude-3-haiku": (0.25, 1.25),

    # Claude 4 family (Opus 4.5)
    "claude-opus-4-5": (15.00, 75.00),
    "claude-opus-4-5-20251101": (15.00, 75.00),

    # OpenAI (for reference)
    "gpt-4-turbo": (10.00, 30.00),
    "gpt-4o": (5.00, 15.00),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-3.5-turbo": (0.50, 1.50),
}

# Default pricing for unknown models (assumes Claude Sonnet)
DEFAULT_LLM_PRICING = (3.00, 15.00)


# API Pricing (per call estimate in USD)
# Most APIs are free or have generous free tiers
API_PRICING: Dict[str, float] = {
    # Crypto APIs - mostly free
    "coingecko": 0.0,
    "defillama": 0.0,
    "l2beat": 0.0,
    "blocklens": 0.0,
    "etherscan": 0.0,       # Free tier: 5 calls/sec
    "thegraph": 0.00004,    # ~$0.00004 per query
    "dune": 0.004,          # ~12 credits per execution (~2500 free/month)

    # Stock/Finance APIs
    "yfinance": 0.0,        # Free (Yahoo Finance)
    "finnhub": 0.0001,      # Free tier: 60 calls/min
    "fred": 0.0,            # Free (Federal Reserve)
    "sec": 0.0,             # Free (SEC EDGAR)
    "sec_edgar": 0.0,
    "fmp": 0.0002,          # ~$19/mo = ~$0.0002/call

    # Research APIs
    "worldbank": 0.0,       # Free
    "imf": 0.0,             # Free
    "wikipedia": 0.0,       # Free
    "arxiv": 0.0,           # Free
    "pubmed": 0.0,          # Free
    "wikidata": 0.0,        # Free

    # Paid Search APIs
    "serper": 0.001,        # ~$1 per 1000 queries
    "google_scholar": 0.001,  # Via Serper
    "news_aggregator": 0.0005,  # Mix of free + Serper

    # Business APIs
    "crunchbase": 0.01,     # Enterprise pricing estimate
}


def calculate_llm_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost for LLM call.

    Args:
        model: Model name (e.g., claude-3-5-sonnet)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Cost in USD (rounded to 6 decimal places)
    """
    # Normalize model name
    model_lower = model.lower().replace("_", "-")

    # Get pricing (use default if unknown)
    pricing = LLM_PRICING.get(model_lower, DEFAULT_LLM_PRICING)

    # Calculate cost
    input_cost = (input_tokens / 1_000_000) * pricing[0]
    output_cost = (output_tokens / 1_000_000) * pricing[1]

    return round(input_cost + output_cost, 6)


def calculate_api_cost(module: str, calls: int = 1) -> float:
    """Calculate cost for API calls.

    Args:
        module: Module name (e.g., serper, coingecko)
        calls: Number of API calls

    Returns:
        Cost in USD (rounded to 6 decimal places)
    """
    per_call = API_PRICING.get(module.lower(), 0.0)
    return round(per_call * calls, 6)


def get_module_tier(module: str) -> str:
    """Get pricing tier for a module.

    Args:
        module: Module name

    Returns:
        Tier string: "free", "low", "medium", or "high"
    """
    cost = API_PRICING.get(module.lower(), 0.0)
    if cost == 0.0:
        return "free"
    elif cost < 0.001:
        return "low"
    elif cost < 0.01:
        return "medium"
    else:
        return "high"


def get_llm_pricing(model: str) -> Tuple[float, float]:
    """Get pricing tuple for a model.

    Args:
        model: Model name

    Returns:
        Tuple of (input_price, output_price) per 1M tokens
    """
    model_lower = model.lower().replace("_", "-")
    return LLM_PRICING.get(model_lower, DEFAULT_LLM_PRICING)


def estimate_llm_cost(model: str, prompt_chars: int, response_chars: int) -> float:
    """Estimate LLM cost from character counts.

    Uses ~4 chars per token estimation for English text.

    Args:
        model: Model name
        prompt_chars: Number of characters in prompt
        response_chars: Number of characters in response

    Returns:
        Estimated cost in USD
    """
    # Estimate tokens (~4 chars per token for English)
    input_tokens = int(prompt_chars / 4)
    output_tokens = int(response_chars / 4)

    return calculate_llm_cost(model, input_tokens, output_tokens)


def get_all_free_modules() -> list:
    """Get list of all free API modules.

    Returns:
        List of module names with zero cost
    """
    return [module for module, cost in API_PRICING.items() if cost == 0.0]


def get_paid_modules() -> Dict[str, float]:
    """Get dictionary of paid API modules with their costs.

    Returns:
        Dict mapping module name to per-call cost
    """
    return {module: cost for module, cost in API_PRICING.items() if cost > 0.0}
