# Data Sources Guide for Ralph Agents

Quick reference for selecting the right API for each data type.

---

# Part 1: Crypto Data APIs

Location: `ralph/integrations/crypto/`

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
| **BTC on-chain** | **BlockLens** | - | LTH/STH, MVRV, SOPR |
| **BTC market cycle** | **BlockLens** | - | Phase analysis, signals |

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
| BlockLens | 100k/day | Required | Enterprise tier |

## Quick Examples

### "Compare L2 fees and TVL"
```python
from integrations.crypto import defillama, l2beat

# Get TVL comparison
tvl = defillama.get_l2_comparison()

# Get fee data
fees = defillama.get_protocol_fees("arbitrum")

# Get security context
risks = l2beat.get_l2_risk_scores()
```

### "Analyze token price and market"
```python
from integrations.crypto import coingecko

# Get price with history
eth = coingecko.get_eth_price_with_history(days=30)

# Get market overview
market = coingecko.get_market_overview()

# Get L2 token prices
l2_prices = coingecko.get_l2_token_prices()
```

### "Check wallet across chains"
```python
from integrations.crypto import etherscan

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
from integrations.crypto import thegraph

# Top pools
pools = thegraph.get_uniswap_top_pools("arbitrum", limit=10)

# Specific pool stats
stats = thegraph.get_uniswap_pool_stats("0x...", chain="ethereum")
```

### "Custom on-chain analysis"
```python
from integrations.crypto import dune

# Run pre-defined query
fees = dune.get_l2_fees_comparison()

# Or run custom query by ID
results = dune.run_query(3237721, parameters={"days": 30})
```

### "BTC market cycle analysis"
```python
from integrations.crypto import blocklens

# Get comprehensive market cycle indicators
cycle = blocklens.get_market_cycle_indicators()
# Returns: market_phase, signal, mvrv, sopr, supply ratios

# Get holder supply distribution
supply = blocklens.get_holder_supply(limit=30)
# Returns: lth_supply, sth_supply over time
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
| BlockLens | Yes | No |

## Import Pattern
```python
# Import all crypto APIs at once
from integrations.crypto import defillama, l2beat, coingecko, etherscan, thegraph, dune, blocklens

# Or import specific module
from integrations.crypto.defillama import get_l2_comparison
```

---

# Part 2: Stock Market APIs

Location: `ralph/integrations/stocks/`

## Decision Matrix

| Data Need | Primary API | Fallback | Notes |
|-----------|-------------|----------|-------|
| Stock prices | yfinance | FMP | yfinance is free, no key |
| Price history | yfinance | Alpha Vantage | yfinance has 20+ years |
| Fundamentals | yfinance | FMP | P/E, Market Cap, ratios |
| Financial statements | yfinance | SEC EDGAR | Income, Balance, Cashflow |
| Real-time quotes | Finnhub | FMP | Finnhub is faster |
| Company news | Finnhub | - | With dates and source |
| Insider trading | Finnhub | SEC EDGAR | Form 4 filings |
| Analyst ratings | Finnhub | yfinance | Price targets, recommendations |
| SEC filings | SEC EDGAR | FMP | Official 10-K, 10-Q, 8-K |
| Macro data | FRED | - | Rates, inflation, GDP |
| DCF valuation | FMP | - | Ready-made model |
| Stock screener | FMP | - | Filter by criteria |

## API Selection by Research Topic

### Company Analysis
```
Primary: yfinance (fundamentals, financials)
         Finnhub (news, insider trading)
         SEC EDGAR (official filings)

Use yfinance for:
- Price history (daily, weekly, monthly)
- Fundamentals (P/E, Market Cap, ratios)
- Financial statements (Income, Balance, Cashflow)
- Dividends and yields
- Analyst recommendations

Use Finnhub for:
- Real-time quotes
- Company news with dates
- Insider trading activity
- Analyst price targets
```

### Valuation Analysis
```
Primary: yfinance (financials for your own model)
         FMP (ready DCF valuation)

Use yfinance for:
- Raw financial data for custom models
- Historical price data
- Comparable company data

Use FMP for:
- Pre-calculated DCF value
- All financial ratios at once
- Quick valuation check
```

### Macro/Economic Analysis
```
Primary: FRED (all macro data)

Use FRED for:
- Federal Funds Rate
- Treasury yields (2Y, 10Y, 30Y)
- Yield curve (recession indicator!)
- Inflation (CPI, PCE)
- Unemployment rate
- GDP growth
- VIX (volatility)
```

### Stock Discovery
```
Primary: FMP (stock screener)

Use FMP screener for:
- Filter by market cap
- Filter by P/E ratio
- Filter by dividend yield
- Filter by sector/industry
- Find value stocks
- Find growth stocks
```

## Rate Limits & Costs

| API | Rate Limit | API Key | Cost |
|-----|------------|---------|------|
| yfinance | ~2000/hour | No | Free |
| Finnhub | 60/min | Required | Free tier |
| FRED | 120/min | Required | Free |
| SEC EDGAR | 10/sec | No | Free |
| FMP | 250/day | Required | Free tier |

## Quick Examples

### "Get stock fundamentals"
```python
from integrations.stocks import yfinance_client

# Company overview
info = yfinance_client.get_stock_info("AAPL")
# Returns: name, sector, P/E, market_cap, dividend_yield, etc.

# Financial statements
financials = yfinance_client.get_financials("AAPL")
# Returns: income_statement, balance_sheet, cash_flow
```

### "Get stock news and sentiment"
```python
from integrations.stocks import finnhub

# Company news
news = finnhub.get_company_news("AAPL")

# Insider trading
insiders = finnhub.get_insider_transactions("AAPL")

# Analyst price targets
targets = finnhub.get_price_target("AAPL")
```

### "Get macro data"
```python
from integrations.stocks import fred

# Macro dashboard
macro = fred.get_macro_dashboard()
# Returns: fed_funds_rate, treasury_10y, unemployment, vix

# Yield curve status (recession indicator!)
yc = fred.get_yield_curve_status()
# Returns: spread, is_inverted, status

# Interest rates
rates = fred.get_interest_rates()
```

### "Get SEC filings"
```python
from integrations.stocks import sec_edgar

# Get 10-K annual reports
filings_10k = sec_edgar.get_10k_filings("AAPL")

# Get company facts (structured financial data)
facts = sec_edgar.get_company_facts("AAPL")

# Get revenue history from filings
revenue = sec_edgar.get_revenue_history("AAPL")
```

### "Valuation and screening"
```python
from integrations.stocks import fmp

# DCF valuation
dcf = fmp.get_dcf("AAPL")
# Returns: intrinsic value per share

# All financial ratios
ratios = fmp.get_ratios_ttm("AAPL")

# Screen for value stocks
stocks = fmp.screen_stocks(
    sector="Technology",
    pe_max=15,
    dividend_min=0.02,
    market_cap_min=1e9
)
```

### "Compare multiple stocks"
```python
from integrations.stocks import yfinance_client

# Compare FAANG stocks
faang = ["META", "AAPL", "AMZN", "NFLX", "GOOGL"]
comparison = yfinance_client.compare_stocks(faang, period="1y")
# Returns: prices, normalized (to 100), returns
```

## Common Mistakes to Avoid

1. **Don't use FMP for price history** - Use yfinance (free, more data)
2. **Don't use yfinance for real-time** - Use Finnhub (faster)
3. **Don't use Finnhub for financials** - Use yfinance (more complete)
4. **Don't use FMP for macro** - Use FRED (official source)
5. **Don't guess SEC data** - Use SEC EDGAR (official source)

## API Availability

| API | Requires API Key | Works Without Key |
|-----|------------------|-------------------|
| yfinance | No | Yes (full access) |
| Finnhub | Yes | No |
| FRED | Yes | No |
| SEC EDGAR | No | Yes (full access) |
| FMP | Yes | No |

## Import Pattern
```python
# Import stock modules
from integrations.stocks import yfinance_client, finnhub, fred, sec_edgar, fmp

# Or import specific function
from integrations.stocks.yfinance_client import get_stock_info
from integrations.stocks.fred import get_macro_dashboard
```

---

# Choosing Between Crypto and Stock APIs

| Research Topic | Use Crypto APIs | Use Stock APIs |
|----------------|-----------------|----------------|
| Bitcoin/Ethereum price | coingecko | - |
| AAPL/MSFT price | - | yfinance |
| DeFi protocols | defillama, thegraph | - |
| Public companies | - | yfinance, sec_edgar |
| L2 rollups | l2beat, defillama | - |
| REITs | - | yfinance, fmp |
| Wallet analysis | etherscan | - |
| Insider trading | - | finnhub, sec_edgar |
| Macro/rates | - | fred |
| On-chain SQL | dune | - |

---

# Part 3: Research & Consulting APIs

Location: `ralph/integrations/research/`

## Decision Matrix

| Data Need | Primary API | Fallback | Notes |
|-----------|-------------|----------|-------|
| GDP data | World Bank | IMF | World Bank has historical |
| GDP forecasts | IMF | - | WEO forecasts |
| Inflation data | World Bank | FRED | Historical |
| Inflation forecast | IMF | - | WEO forecasts |
| Country comparison | World Bank | - | 200+ countries |
| Industry research | Deloitte RSS | McKinsey | Deloitte has RSS |
| Tech trends | Deloitte | McKinsey | Annual reports |
| Market outlook | Goldman | McKinsey | Top of Mind series |
| Strategy research | McKinsey | BCG | MGI reports |

## API Selection by Research Topic

### Macro Economic Research
```
Primary: World Bank (historical data)
         IMF (forecasts)

Use World Bank for:
- GDP, population, inflation history
- Country comparisons
- Development indicators
- Trade statistics

Use IMF for:
- Economic outlook forecasts
- GDP growth projections
- Inflation forecasts
- Government debt analysis
```

### Industry Research
```
Primary: Deloitte (RSS feeds - easy access)
         McKinsey (MGI, industry insights)
         Goldman (market analysis)

Use Deloitte for:
- Tech Trends reports
- CFO Signals survey
- Industry outlooks
- Quick category browsing via RSS

Use McKinsey for:
- Deep industry analysis
- Strategy frameworks
- MGI macro research

Use Goldman for:
- Market outlook
- Top of Mind series (flagship)
- Economic analysis
```

## Rate Limits & Costs

| API | Rate Limit | API Key | Cost |
|-----|------------|---------|------|
| World Bank | Fair use | No | Free |
| IMF | Fair use | No | Free |
| Deloitte RSS | Fair use | No | Free |
| McKinsey | Web scraping | No | Free (public) |
| Goldman | Web scraping | No | Free (public) |

## Quick Examples

### "Get macro data"
```python
from integrations.research import worldbank, imf

# World Bank historical data
gdp = worldbank.get_indicator("gdp", country="USA")
profile = worldbank.get_country_profile("USA")

# IMF forecasts
outlook = imf.get_economic_outlook("USA")
growth = imf.get_global_growth_forecast()
```

### "Get industry research"
```python
from integrations.research import deloitte, aggregator

# Deloitte latest via RSS
tech_articles = deloitte.get_latest("tech", limit=10)
finance_articles = deloitte.get_latest("finance", limit=10)

# Multi-source search
results = aggregator.get_industry_research("technology")
```

### "Search consulting research"
```python
from integrations.research import aggregator

# Get web search queries for all sources
queries = aggregator.get_web_search_queries("AI productivity")
# Returns: [
#   {"source": "mckinsey", "query": "site:mckinsey.com AI productivity"},
#   {"source": "deloitte", "query": "site:deloitte.com/insights AI productivity"},
#   {"source": "goldman", "query": "site:goldmansachs.com/insights AI productivity"},
# ]

# Build research brief
brief = aggregator.build_research_brief("artificial intelligence", country="USA")
```

### "Compare countries"
```python
from integrations.research import worldbank

# Compare GDP across countries
comparison = worldbank.compare_countries(
    countries=["USA", "CHN", "JPN", "DEU"],
    indicator="gdp_growth"
)

# Get GDP ranking
top_20 = worldbank.get_gdp_ranking(limit=20)
```

## Common Mistakes to Avoid

1. **Don't scrape McKinsey for data** - Use for research guidance, WebSearch for content
2. **Don't use IMF for historical** - Use World Bank (more complete history)
3. **Don't skip Deloitte RSS** - Easiest access to consulting insights
4. **Don't expect full reports** - Most consulting content is summaries/teasers

## API Availability

| API | Requires API Key | Works Without Key |
|-----|------------------|-------------------|
| World Bank | No | Yes (full API) |
| IMF | No | Yes (full API) |
| Deloitte | No | Yes (RSS feeds) |
| McKinsey | No | Web search only |
| Goldman | No | Web search only |

## Import Pattern
```python
# Import research modules
from integrations.research import worldbank, imf, deloitte, mckinsey, goldman, aggregator

# Or import specific function
from integrations.research.worldbank import get_country_profile
from integrations.research.aggregator import build_research_brief
```

---

# Complete API Selection Guide

## By Data Type

| Data Type | Best Source | Module |
|-----------|-------------|--------|
| Crypto prices | CoinGecko | `integrations.coingecko` |
| Stock prices | yfinance | `integrations.stocks.yfinance_client` |
| DeFi TVL | DefiLlama | `integrations.defillama` |
| L2 security | L2Beat | `integrations.l2beat` |
| Macro rates | FRED | `integrations.stocks.fred` |
| GDP/country data | World Bank | `integrations.research.worldbank` |
| Economic forecasts | IMF | `integrations.research.imf` |
| Industry research | Deloitte | `integrations.research.deloitte` |
| Strategy research | McKinsey | `integrations.research.mckinsey` |
| Market outlook | Goldman | `integrations.research.goldman` |

## By Research Topic

| Topic | Primary Sources |
|-------|-----------------|
| Crypto/DeFi analysis | coingecko, defillama, l2beat, dune |
| Stock analysis | yfinance, finnhub, sec_edgar, fmp |
| Macro economics | fred, worldbank, imf |
| Industry trends | deloitte, mckinsey, goldman |
| Company fundamentals | yfinance, sec_edgar |
| Market sentiment | finnhub (news), goldman (outlook) |
