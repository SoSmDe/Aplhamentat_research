# Crypto Data Sources Guide for Ralph Agents

Quick reference for selecting the right API for each data type.

## Decision Matrix

| Data Need | Primary API | Fallback | Notes |
|-----------|-------------|----------|-------|
| Token prices | CoinGecko | Etherscan (ETH only) | CoinGecko has 10K+ tokens |
| Market cap | CoinGecko | - | Best for rankings |
| TVL (DeFi) | DefiLlama | TheGraph | DefiLlama is aggregated |
| L2 security | L2Beat | - | Only source for risk scores |
| L2 activity | L2Beat | DefiLlama | L2Beat has TPS, batches |
| Protocol fees | DefiLlama | Dune | DefiLlama is pre-aggregated |
| Wallet balance | Etherscan | - | Multi-chain support |
| Gas prices | Etherscan | - | Real-time gas oracle |
| DEX pools | TheGraph | DefiLlama | TheGraph has granular data |
| Lending rates | TheGraph | DefiLlama | TheGraph for specific pools |
| Custom queries | Dune | - | When others don't have data |

## API Selection by Research Topic

### L2/Rollup Analysis
```
Primary: L2Beat (risks, security, activity)
         DefiLlama (TVL, fees)
         CoinGecko (L2 token prices)

Use L2Beat for:
- Security assessments (risk scores, stages)
- Technology comparisons (DA layer, proof system)
- Activity metrics (TPS, batch frequency)

Use DefiLlama for:
- TVL comparisons
- Fee/revenue analysis
- Historical trends
```

### DeFi Protocol Research
```
Primary: DefiLlama (TVL, fees, yields)
         TheGraph (protocol-specific data)
         CoinGecko (governance token prices)

Use DefiLlama for:
- Protocol TVL rankings
- Yield comparisons
- Fee generation

Use TheGraph for:
- Specific pool data (Uniswap, Aave)
- User positions
- Transaction history
```

### Token/Price Analysis
```
Primary: CoinGecko (prices, market data)

Use CoinGecko for:
- Current and historical prices
- Market cap rankings
- Trading volumes
- Token metadata (links, description)
- Global market stats
```

### Wallet/On-Chain Analysis
```
Primary: Etherscan (balances, transactions)
         Dune (complex queries)

Use Etherscan for:
- Wallet balances (multi-chain)
- Transaction history
- Token transfers
- Contract verification

Use Dune for:
- Complex on-chain analytics
- Historical patterns
- Custom metrics
```

## Rate Limits & Costs

| API | Rate Limit | API Key | Cost |
|-----|------------|---------|------|
| DefiLlama | Fair use | No | Free |
| L2Beat | Fair use | No | Free |
| CoinGecko | 10-50/min | Optional | Free tier |
| Etherscan | 5/sec | Recommended | Free tier |
| TheGraph | Fair use | No | Free (hosted) |
| Dune | 2500 credits/mo | Required | Free tier limited |

## Quick Examples

### "Compare L2 fees and TVL"
```python
from integrations import defillama, l2beat

# Get TVL comparison
tvl = defillama.get_l2_comparison()

# Get fee data
fees = defillama.get_protocol_fees("arbitrum")

# Get security context
risks = l2beat.get_l2_risk_scores()
```

### "Analyze token price and market"
```python
from integrations import coingecko

# Get price with history
eth = coingecko.get_eth_price_with_history(days=30)

# Get market overview
market = coingecko.get_market_overview()

# Get L2 token prices
l2_prices = coingecko.get_l2_token_prices()
```

### "Check wallet across chains"
```python
from integrations import etherscan

# Multi-chain balance
balances = etherscan.get_multi_chain_balance(
    "0x...",
    chains=["ethereum", "arbitrum", "optimism", "base"]
)

# Large transactions
whales = etherscan.get_whale_transactions("0x...", min_value_eth=100)
```

### "Get Uniswap pool data"
```python
from integrations import thegraph

# Top pools
pools = thegraph.get_uniswap_top_pools("arbitrum", limit=10)

# Specific pool stats
stats = thegraph.get_uniswap_pool_stats("0x...", chain="ethereum")
```

### "Custom on-chain analysis"
```python
from integrations import dune

# Run pre-defined query
fees = dune.get_l2_fees_comparison()

# Or run custom query by ID
results = dune.run_query(3237721, parameters={"days": 30})
```

## Common Mistakes to Avoid

1. **Don't use Dune for simple data** - It's slow (10-60s per query) and has limited credits
2. **Don't use TheGraph for aggregated stats** - Use DefiLlama instead
3. **Don't use CoinGecko for on-chain data** - It only has market data
4. **Don't use Etherscan for DeFi TVL** - Use DefiLlama
5. **Don't use L2Beat for non-L2 protocols** - It only covers L2s

## API Availability

| API | Requires API Key | Works Without Key |
|-----|------------------|-------------------|
| DefiLlama | No | Yes (full access) |
| L2Beat | No | Yes (full access) |
| CoinGecko | No | Yes (rate limited) |
| Etherscan | Recommended | Yes (very limited) |
| TheGraph | No | Yes (hosted service) |
| Dune | Yes | No |

## Import Pattern
```python
# Import all at once
from integrations import defillama, l2beat, coingecko, etherscan, thegraph, dune

# Or import specific module
from integrations.defillama import get_l2_comparison
```
