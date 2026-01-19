# -*- coding: utf-8 -*-
"""
Etherscan API Integration (+ Arbiscan, Basescan, etc.)

USE FOR:
- Wallet balances (ETH and tokens)
- Transaction history
- Gas prices (real-time)
- Contract ABIs and source code
- Token transfers
- Block data

DO NOT USE FOR:
- Aggregated DeFi stats (use DefiLlama)
- Token prices (use CoinGecko)
- L2 security analysis (use L2Beat)
- Historical analytics (use Dune)

RATE LIMIT: 5 calls/sec (free), 10+ calls/sec (paid)
API KEY: Optional but recommended

SUPPORTED CHAINS:
- Ethereum (etherscan.io)
- Arbitrum (arbiscan.io)
- Optimism (optimistic.etherscan.io)
- Base (basescan.org)
- Polygon (polygonscan.com)
"""

import os
import requests
from typing import Optional, List

# Multi-chain configuration
CHAINS = {
    "ethereum": {
        "url": "https://api.etherscan.io/api",
        "key_env": "ETHERSCAN_API_KEY",
        "native": "ETH"
    },
    "arbitrum": {
        "url": "https://api.arbiscan.io/api",
        "key_env": "ARBISCAN_API_KEY",
        "native": "ETH"
    },
    "optimism": {
        "url": "https://api-optimistic.etherscan.io/api",
        "key_env": "OPTIMISM_ETHERSCAN_API_KEY",
        "native": "ETH"
    },
    "base": {
        "url": "https://api.basescan.org/api",
        "key_env": "BASESCAN_API_KEY",
        "native": "ETH"
    },
    "polygon": {
        "url": "https://api.polygonscan.com/api",
        "key_env": "POLYGONSCAN_API_KEY",
        "native": "MATIC"
    },
    "bsc": {
        "url": "https://api.bscscan.com/api",
        "key_env": "BSCSCAN_API_KEY",
        "native": "BNB"
    }
}


def _get_api_key(chain: str) -> str:
    """Get API key for chain from environment."""
    config = CHAINS.get(chain, CHAINS["ethereum"])
    return os.getenv(config["key_env"], "")


def _make_request(chain: str, params: dict) -> dict:
    """Make request to chain's block explorer API."""
    config = CHAINS.get(chain, CHAINS["ethereum"])
    api_key = _get_api_key(chain)

    if api_key:
        params["apikey"] = api_key

    response = requests.get(config["url"], params=params)
    response.raise_for_status()
    data = response.json()

    if data.get("status") == "0" and "rate limit" in data.get("message", "").lower():
        raise Exception(f"Rate limit exceeded for {chain}")

    return data


def get_balance(address: str, chain: str = "ethereum") -> float:
    """
    Get native token balance for address.

    Args:
        address: Wallet address
        chain: Chain name (ethereum, arbitrum, optimism, base, polygon)

    Returns: Balance in native token (ETH, MATIC, etc.)

    Use case: Wallet analysis, portfolio tracking
    """
    data = _make_request(chain, {
        "module": "account",
        "action": "balance",
        "address": address,
        "tag": "latest"
    })
    return int(data["result"]) / 1e18


def get_token_balance(address: str, contract: str, chain: str = "ethereum") -> float:
    """
    Get ERC-20 token balance.

    Args:
        address: Wallet address
        contract: Token contract address
        chain: Chain name

    Returns: Token balance (need to check decimals)
    """
    data = _make_request(chain, {
        "module": "account",
        "action": "tokenbalance",
        "contractaddress": contract,
        "address": address,
        "tag": "latest"
    })
    return int(data["result"])


def get_transactions(address: str, chain: str = "ethereum",
                    startblock: int = 0, endblock: int = 99999999,
                    sort: str = "desc") -> list:
    """
    Get transaction history for address.

    Args:
        address: Wallet address
        chain: Chain name
        startblock: Start block number
        endblock: End block number
        sort: "asc" or "desc"

    Returns: List of transactions

    Use case: Wallet activity analysis, transaction tracking
    """
    data = _make_request(chain, {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": startblock,
        "endblock": endblock,
        "sort": sort
    })
    return data.get("result", [])


def get_token_transfers(address: str, chain: str = "ethereum",
                       contract: Optional[str] = None) -> list:
    """
    Get ERC-20 token transfers for address.

    Args:
        address: Wallet address
        chain: Chain name
        contract: Optional - filter by token contract

    Returns: List of token transfers

    Use case: Token flow analysis, whale tracking
    """
    params = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "sort": "desc"
    }
    if contract:
        params["contractaddress"] = contract

    data = _make_request(chain, params)
    return data.get("result", [])


def get_gas_prices(chain: str = "ethereum") -> dict:
    """
    Get current gas prices.

    Returns:
    - SafeGasPrice (slow)
    - ProposeGasPrice (average)
    - FastGasPrice (fast)
    - suggestBaseFee

    Use case: Transaction cost estimation, gas tracking
    """
    data = _make_request(chain, {
        "module": "gastracker",
        "action": "gasoracle"
    })
    return data.get("result", {})


def get_contract_abi(contract: str, chain: str = "ethereum") -> list:
    """
    Get contract ABI.

    Args:
        contract: Contract address
        chain: Chain name

    Returns: Contract ABI as list

    Use case: Contract interaction, decoding transactions
    """
    data = _make_request(chain, {
        "module": "contract",
        "action": "getabi",
        "address": contract
    })
    import json
    return json.loads(data.get("result", "[]"))


def get_contract_source(contract: str, chain: str = "ethereum") -> dict:
    """
    Get verified contract source code.

    Args:
        contract: Contract address
        chain: Chain name

    Returns: Source code and compiler info

    Use case: Contract analysis, security review
    """
    data = _make_request(chain, {
        "module": "contract",
        "action": "getsourcecode",
        "address": contract
    })
    return data.get("result", [{}])[0]


def get_eth_price() -> dict:
    """
    Get current ETH price from Etherscan.

    Returns:
    - ethusd: ETH price in USD
    - ethbtc: ETH price in BTC

    Use case: Quick price check
    """
    data = _make_request("ethereum", {
        "module": "stats",
        "action": "ethprice"
    })
    return data.get("result", {})


# ============ HELPER FUNCTIONS ============

def get_multi_chain_balance(address: str, chains: List[str] = None) -> dict:
    """
    Get balance across multiple chains.

    Args:
        address: Wallet address
        chains: List of chains (default: all)

    Returns: Dict of chain -> balance
    """
    if chains is None:
        chains = ["ethereum", "arbitrum", "optimism", "base", "polygon"]

    balances = {}
    for chain in chains:
        try:
            balances[chain] = get_balance(address, chain)
        except Exception as e:
            balances[chain] = f"Error: {e}"

    return balances


def get_whale_transactions(address: str, min_value_eth: float = 100,
                          chain: str = "ethereum") -> list:
    """
    Get large transactions from an address.

    Args:
        address: Wallet address
        min_value_eth: Minimum ETH value
        chain: Chain name

    Returns: List of whale transactions
    """
    txs = get_transactions(address, chain)
    whales = [
        tx for tx in txs
        if int(tx.get("value", 0)) / 1e18 >= min_value_eth
    ]
    return whales


# Known whale/exchange wallets
KNOWN_WALLETS = {
    "binance_hot": "0x28C6c06298d514Db089934071355E5743bf21d60",
    "binance_cold": "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",
    "coinbase": "0x71660c4005BA85c37ccec55d0C4493E66Fe775d3",
    "kraken": "0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0",
    "ftx_cold": "0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2",  # Historical
}


def monitor_exchange_flows(exchange: str = "binance_hot", chain: str = "ethereum") -> dict:
    """
    Monitor exchange wallet activity.

    Args:
        exchange: Exchange name from KNOWN_WALLETS
        chain: Chain name

    Returns: Recent transactions and balance
    """
    address = KNOWN_WALLETS.get(exchange)
    if not address:
        return {"error": f"Unknown exchange: {exchange}"}

    return {
        "address": address,
        "balance": get_balance(address, chain),
        "recent_txs": get_transactions(address, chain)[:10]
    }


if __name__ == "__main__":
    # Test
    print("=== Gas Prices ===")
    gas = get_gas_prices()
    print(f"  Safe: {gas.get('SafeGasPrice')} gwei")
    print(f"  Average: {gas.get('ProposeGasPrice')} gwei")
    print(f"  Fast: {gas.get('FastGasPrice')} gwei")

    print("\n=== ETH Price ===")
    price = get_eth_price()
    print(f"  ETH/USD: ${price.get('ethusd')}")
