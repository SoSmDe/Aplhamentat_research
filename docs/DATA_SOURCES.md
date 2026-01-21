# Data Sources

## Overview

Ralph использует несколько API для сбора данных:

```
┌─────────────────────────────────────────────────────────────────┐
│                      DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐  On-Chain Metrics                              │
│  │  BlockLens  │  MVRV, NUPL, SOPR, LTH/STH, Realized Price     │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐  Prices & Market Data                          │
│  │  CoinGecko  │  Price history, market cap, volume             │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐  DeFi & TVL                                    │
│  │  DefiLlama  │  Protocol TVL, chain comparison                │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐  L2 Security                                   │
│  │   L2Beat    │  Risk scores, L2 metrics                       │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐  Traditional Finance                           │
│  │  yfinance   │  Stock/ETF prices, indices                     │
│  └─────────────┘                                                │
│                                                                  │
│  ┌─────────────┐  General Research                              │
│  │  WebSearch  │  News, analysis, reports                       │
│  │  WebFetch   │  Article content, verification                 │
│  └─────────────┘                                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## BlockLens API

**Purpose:** On-chain Bitcoin metrics (Glassnode alternative)

**CLI:** `python cli/fetch.py blocklens <function> '<params>'`

### Available Functions

| Function | Description | Output |
|----------|-------------|--------|
| `get_prices()` | Current BTC price + 24h change | `{price, change_24h, timestamp}` |
| `get_holder_supply()` | LTH/STH supply breakdown | `{lth_supply, sth_supply, pct}` |
| `get_holder_valuation()` | MVRV, NUPL, Realized Price | `{mvrv, nupl, realized_price}` |
| `get_holder_profit()` | SOPR metrics | `{sopr, lth_sopr, sth_sopr}` |
| `get_market_cycle_indicators()` | Cycle position metrics | `{pi_cycle, puell, mvrv_zscore}` |

### Example Usage

```bash
# Get current holder metrics
python cli/fetch.py blocklens get_holder_supply

# Get MVRV and realized price
python cli/fetch.py blocklens get_holder_valuation

# With parameters
python cli/fetch.py blocklens get_holder_supply '{"holder_type": "lth"}'
```

### Output Format (series)

```json
{
  "asset": "BTC",
  "metric": "LTH_supply",
  "unit": "BTC",
  "labels": ["2024-01-01", "2024-01-02", ...],
  "values": [14500000, 14510000, ...]
}
```

---

## CoinGecko

**Purpose:** Price data, market metrics

### CSV Export (Recommended for History)

```bash
# Full price history - NO API LIMITS!
curl -o btc_prices.csv "https://www.coingecko.com/price_charts/export/bitcoin/usd.csv"
curl -o eth_prices.csv "https://www.coingecko.com/price_charts/export/ethereum/usd.csv"
```

**URL Format:**
```
https://www.coingecko.com/price_charts/export/{coin_id}/usd.csv
```

**Popular coin_ids:**
- `bitcoin`, `ethereum`, `solana`, `cardano`
- `avalanche-2`, `polygon-ecosystem-token`
- Check CoinGecko URL for exact slug

### API (Current Data Only)

```bash
# Current price
python cli/fetch.py coingecko get_price '["bitcoin", "ethereum"]'

# Top coins by market cap
python cli/fetch.py coingecko get_top_coins 100
```

---

## DefiLlama

**Purpose:** DeFi TVL, protocol metrics

**CLI:** `python cli/fetch.py defillama <function>`

### Available Functions

| Function | Description |
|----------|-------------|
| `get_protocol_tvl("aave")` | Single protocol TVL |
| `get_historical_tvl("aave")` | TVL history |
| `get_l2_comparison()` | All L2s comparison |
| `get_chain_tvl("arbitrum")` | Chain total TVL |

### Example Usage

```bash
# Get Aave TVL
python cli/fetch.py defillama get_protocol_tvl '{"protocol": "aave"}'

# Compare all L2s
python cli/fetch.py defillama get_l2_comparison
```

---

## L2Beat

**Purpose:** L2 security and risk metrics

**CLI:** `python cli/fetch.py l2beat <function>`

### Available Functions

| Function | Description |
|----------|-------------|
| `get_l2_risk_scores()` | Security scores for all L2s |
| `get_project_details("arbitrum")` | Detailed project info |

### Example Usage

```bash
# Get all L2 risk scores
python cli/fetch.py l2beat get_l2_risk_scores

# Get specific project
python cli/fetch.py l2beat get_project_details '{"project": "optimism"}'
```

---

## yfinance

**Purpose:** Traditional finance data (stocks, ETFs, indices)

**CLI:** `python cli/fetch.py yfinance <function> '<params>'`

### Available Functions

| Function | Description |
|----------|-------------|
| `get_price_history` | OHLCV data |
| `get_current_price` | Current quote |

### Example Usage

```bash
# Get SPY history
python cli/fetch.py yfinance get_price_history '{"ticker": "SPY", "period": "5y", "interval": "1d"}'

# Get BTC-USD (fallback for CoinGecko)
python cli/fetch.py yfinance get_price_history '{"ticker": "BTC-USD", "period": "max"}'

# Get MSTR (Strategy/MicroStrategy)
python cli/fetch.py yfinance get_price_history '{"ticker": "MSTR", "period": "2y"}'
```

---

## WebSearch & WebFetch

**Purpose:** News, analysis, verification

### WebSearch
Use for finding articles, news, analysis:

```
WebSearch: "Bitcoin ETF flows January 2026"
WebSearch: "Strategy mNAV current"
WebSearch: "LTH supply glassnode analysis"
```

### WebFetch
Use for reading and verifying content:

```
WebFetch: https://beincrypto.com/article-url/
→ Returns article text for verification
```

**Rules:**
- Always verify data with WebFetch before citing
- Save full URLs, not domain only
- If number cited, source must contain that number

---

## API Priority

| Data Need | Primary Source | Fallback |
|-----------|----------------|----------|
| BTC on-chain (MVRV, LTH/STH) | BlockLens | - |
| BTC price history | CoinGecko CSV | yfinance BTC-USD |
| ETH price history | CoinGecko CSV | yfinance ETH-USD |
| DeFi TVL | DefiLlama | - |
| L2 security | L2Beat | - |
| Stock/ETF prices | yfinance | - |
| News/Analysis | WebSearch | - |
| Verification | WebFetch | - |

---

## Series File Format

All time series data saved to `results/series/`:

```json
{
  "asset": "BTC",
  "metric": "price",
  "unit": "USD",
  "source": "coingecko",
  "labels": ["2024-01-01", "2024-01-02", ...],
  "values": [42000, 42150, ...]
}
```

**Naming Convention:**
```
{ASSET}_{metric}.json
```

Examples:
- `BTC_price.json`
- `BTC_LTH_MVRV.json`
- `BTC_STH_supply.json`
- `ETH_price.json`

---

## Citation Format

Every data point needs a citation:

```json
{
  "id": "c1",
  "claim": "BTC LTH MVRV is 2.37",
  "source_title": "BlockLens API",
  "source_url": "https://api.blocklens.io/v1/btc/holder_valuation",
  "snippet": "Current LTH MVRV: 2.37",
  "confidence": "high",
  "accessed_at": "2026-01-21T10:00:00Z"
}
```

**Rules:**
- Full URL (not domain only)
- Snippet must contain the cited number
- Verify via WebFetch if web source
