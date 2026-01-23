"""
Analytics Module — Statistical Analysis for Time Series Data

Provides functions for analyzing time series data from APIs (BlockLens, CoinGecko, etc.)
Used by Chart Analyzer and Aggregator agents for deeper insights.

Usage:
    from integrations.analytics import series_analyzer

    # Load JSON data
    data = json.load(open("results/series/BTC_MVRV.json"))

    # Full analysis (recommended)
    result = series_analyzer.full_analysis(data["values"], data.get("labels"))

    # Individual functions
    stats = series_analyzer.basic_stats(data["values"])
    trend = series_analyzer.trend_direction(data["values"], window=30)

CLI:
    # Full structured analysis (recommended for aggregator)
    python cli/fetch.py analytics full_analysis '{"file": "results/series/BTC_MVRV.json"}'

    # Individual analyses
    python cli/fetch.py analytics basic_stats '{"file": "results/series/BTC_MVRV.json"}'
    python cli/fetch.py analytics trend_direction '{"file": "results/series/BTC_price.json", "window": 30}'
    python cli/fetch.py analytics correlation '{"file1": "series/A.json", "file2": "series/B.json"}'

Available Functions:
    Basic: basic_stats, mean, std, percentile, current_percentile
    Extremes: find_max, find_min, distance_from_ath, distance_from_atl, calculate_range
    Trends: trend_direction, trend_strength, moving_average, ema, momentum, acceleration
    Volatility: volatility, atr, bollinger_position, volatility_regime
    Correlations: correlation, rolling_correlation, correlation_matrix, lead_lag
    Comparisons: compare_periods, compare_to_history, yoy_change, mom_change
    Anomalies: detect_anomalies, detect_regime_change, find_divergence, detect_breakout
    Distribution: distribution_stats, value_at_risk, probability_above, expected_range
    Crypto: mvrv_zscore, supply_distribution, funding_rate_signal
    Meta: summarize_signals, find_contradictions, full_analysis
"""

from . import series_analyzer

__all__ = [
    "series_analyzer",
]
