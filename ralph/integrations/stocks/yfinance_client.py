# -*- coding: utf-8 -*-
"""
Yahoo Finance API Integration (via yfinance)

USE FOR:
- Stock prices (current and historical)
- Company fundamentals (P/E, Market Cap, ratios)
- Financial statements (Income, Balance, Cashflow)
- Dividend history and yields
- Analyst recommendations
- Multiple stock comparison

DO NOT USE FOR:
- Real-time quotes (use Finnhub - faster)
- News with sentiment (use Finnhub)
- Insider trading data (use Finnhub or SEC EDGAR)
- Official SEC filings (use SEC EDGAR)
- Macro data (use FRED)
- DCF valuation (use FMP)

RATE LIMIT: ~2000 calls/hour (unofficial)
API KEY: Not required!

INSTALL: pip install yfinance pandas
"""

import yfinance as yf
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime


def get_stock_info(ticker: str) -> dict:
    """
    Get company fundamentals and key metrics.

    Args:
        ticker: Stock symbol (e.g., "AAPL", "MSFT")

    Returns:
        Dict with fundamentals: P/E, Market Cap, sector, etc.

    Use case: Company overview, fundamental analysis
    """
    stock = yf.Ticker(ticker)
    info = stock.info

    return {
        "ticker": ticker,
        "name": info.get("longName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "market_cap": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "forward_pe": info.get("forwardPE"),
        "peg_ratio": info.get("pegRatio"),
        "price_to_book": info.get("priceToBook"),
        "dividend_yield": info.get("dividendYield"),
        "profit_margin": info.get("profitMargins"),
        "roe": info.get("returnOnEquity"),
        "debt_to_equity": info.get("debtToEquity"),
        "current_price": info.get("currentPrice"),
        "52_week_high": info.get("fiftyTwoWeekHigh"),
        "52_week_low": info.get("fiftyTwoWeekLow"),
        "avg_volume": info.get("averageVolume"),
        "beta": info.get("beta"),
        "description": info.get("longBusinessSummary"),
    }


def get_price_history(ticker: str, period: str = "1y",
                      interval: str = "1d") -> pd.DataFrame:
    """
    Get historical OHLCV price data.

    Args:
        ticker: Stock symbol
        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        interval: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo

    Returns:
        DataFrame with Open, High, Low, Close, Volume

    Use case: Price charts, trend analysis
    """
    stock = yf.Ticker(ticker)
    return stock.history(period=period, interval=interval)


def get_financials(ticker: str) -> dict:
    """
    Get financial statements.

    Args:
        ticker: Stock symbol

    Returns:
        Dict with income statement, balance sheet, cash flow (annual + quarterly)

    Use case: Financial analysis, valuation
    """
    stock = yf.Ticker(ticker)

    return {
        "income_statement": stock.financials,
        "quarterly_income": stock.quarterly_financials,
        "balance_sheet": stock.balance_sheet,
        "quarterly_balance": stock.quarterly_balance_sheet,
        "cash_flow": stock.cashflow,
        "quarterly_cashflow": stock.quarterly_cashflow,
    }


def get_income_metrics(ticker: str) -> dict:
    """
    Get key income statement metrics.

    Returns: Revenue, Net Income, EPS trends
    """
    stock = yf.Ticker(ticker)
    income = stock.financials

    if income.empty:
        return {"error": "No income data available"}

    return {
        "total_revenue": income.loc["Total Revenue"].to_dict() if "Total Revenue" in income.index else None,
        "net_income": income.loc["Net Income"].to_dict() if "Net Income" in income.index else None,
        "operating_income": income.loc["Operating Income"].to_dict() if "Operating Income" in income.index else None,
        "gross_profit": income.loc["Gross Profit"].to_dict() if "Gross Profit" in income.index else None,
    }


def get_dividend_history(ticker: str) -> dict:
    """
    Get dividend payment history.

    Returns:
        - dividends: All dividend payments
        - annual_dividends: Aggregated by year
        - current_yield: Current dividend yield

    Use case: Dividend analysis, income investing
    """
    stock = yf.Ticker(ticker)
    dividends = stock.dividends

    if dividends.empty:
        return {"dividends": None, "annual_dividends": None, "current_yield": None}

    # Aggregate by year
    df = dividends.reset_index()
    df.columns = ["date", "dividend"]
    df["year"] = df["date"].dt.year
    annual = df.groupby("year")["dividend"].sum().to_dict()

    return {
        "dividends": dividends.to_dict(),
        "annual_dividends": annual,
        "current_yield": stock.info.get("dividendYield"),
        "ex_dividend_date": stock.info.get("exDividendDate"),
    }


def get_analyst_recommendations(ticker: str) -> pd.DataFrame:
    """
    Get analyst recommendations history.

    Returns: DataFrame with firm, rating, date

    Use case: Sentiment analysis, consensus view
    """
    stock = yf.Ticker(ticker)
    return stock.recommendations


def get_earnings(ticker: str) -> dict:
    """
    Get earnings history and estimates.

    Returns:
        - earnings_history: Historical EPS
        - earnings_dates: Upcoming/past earnings dates

    Use case: Earnings analysis, surprise detection
    """
    stock = yf.Ticker(ticker)

    return {
        "earnings_history": stock.earnings,
        "quarterly_earnings": stock.quarterly_earnings,
        "earnings_dates": stock.earnings_dates,
    }


def compare_stocks(tickers: List[str], period: str = "1y") -> dict:
    """
    Compare multiple stocks.

    Args:
        tickers: List of stock symbols
        period: Time period for comparison

    Returns:
        - prices: Adjusted close prices
        - normalized: Prices normalized to 100 at start
        - returns: Cumulative returns

    Use case: Portfolio comparison, sector analysis
    """
    data = yf.download(tickers, period=period)["Adj Close"]

    # Normalize to 100
    normalized = data / data.iloc[0] * 100

    # Calculate returns
    returns = (data.iloc[-1] / data.iloc[0] - 1) * 100

    return {
        "prices": data,
        "normalized": normalized,
        "returns": returns.to_dict(),
    }


def get_options_chain(ticker: str, expiration: Optional[str] = None) -> dict:
    """
    Get options chain data.

    Args:
        ticker: Stock symbol
        expiration: Expiration date (None = nearest)

    Returns:
        - calls: Call options
        - puts: Put options
        - expirations: Available expiration dates

    Use case: Options analysis, implied volatility
    """
    stock = yf.Ticker(ticker)

    expirations = stock.options
    if not expirations:
        return {"error": "No options available"}

    if expiration is None:
        expiration = expirations[0]

    chain = stock.option_chain(expiration)

    return {
        "calls": chain.calls,
        "puts": chain.puts,
        "expiration": expiration,
        "all_expirations": expirations,
    }


def download_to_csv(ticker: str, period: str = "5y", output_dir: str = ".") -> dict:
    """
    Download all data to CSV files.

    Args:
        ticker: Stock symbol
        period: Price history period
        output_dir: Output directory

    Returns: Dict of created file paths
    """
    stock = yf.Ticker(ticker)
    files = {}

    # Price history
    prices = stock.history(period=period)
    path = f"{output_dir}/{ticker}_prices.csv"
    prices.to_csv(path)
    files["prices"] = path

    # Financials
    if not stock.financials.empty:
        path = f"{output_dir}/{ticker}_income_statement.csv"
        stock.financials.to_csv(path)
        files["income_statement"] = path

    if not stock.balance_sheet.empty:
        path = f"{output_dir}/{ticker}_balance_sheet.csv"
        stock.balance_sheet.to_csv(path)
        files["balance_sheet"] = path

    if not stock.cashflow.empty:
        path = f"{output_dir}/{ticker}_cashflow.csv"
        stock.cashflow.to_csv(path)
        files["cashflow"] = path

    # Dividends
    if not stock.dividends.empty:
        path = f"{output_dir}/{ticker}_dividends.csv"
        stock.dividends.to_csv(path)
        files["dividends"] = path

    return files


# ============ QUICK HELPERS ============

def get_current_price(ticker: str) -> float:
    """Get current stock price."""
    stock = yf.Ticker(ticker)
    return stock.info.get("currentPrice") or stock.info.get("regularMarketPrice")


def get_market_cap(ticker: str) -> float:
    """Get market capitalization."""
    stock = yf.Ticker(ticker)
    return stock.info.get("marketCap")


def get_pe_ratio(ticker: str) -> float:
    """Get P/E ratio."""
    stock = yf.Ticker(ticker)
    return stock.info.get("trailingPE")


def get_dividend_yield(ticker: str) -> float:
    """Get dividend yield."""
    stock = yf.Ticker(ticker)
    return stock.info.get("dividendYield")


# ============ SECTOR ANALYSIS ============

SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
}


def get_sector_performance(period: str = "1mo") -> dict:
    """
    Get sector ETF performance.

    Returns: Dict of sector -> return %
    """
    etfs = list(SECTOR_ETFS.values())
    comparison = compare_stocks(etfs, period=period)

    return {
        sector: comparison["returns"].get(etf, 0)
        for sector, etf in SECTOR_ETFS.items()
    }


if __name__ == "__main__":
    print("=== Apple Info ===")
    info = get_stock_info("AAPL")
    print(f"Name: {info['name']}")
    print(f"P/E: {info['pe_ratio']}")
    print(f"Market Cap: ${info['market_cap']/1e9:.1f}B")

    print("\n=== Sector Performance (1mo) ===")
    sectors = get_sector_performance("1mo")
    for sector, ret in sorted(sectors.items(), key=lambda x: x[1], reverse=True):
        print(f"  {sector}: {ret:+.1f}%")
