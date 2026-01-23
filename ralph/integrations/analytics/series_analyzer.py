"""
Series Analyzer — Statistical Analysis Functions for Time Series

Provides comprehensive statistical analysis for Chart Analyzer agent.
Works with data from BlockLens, CoinGecko, and other APIs.

Usage:
    python cli/fetch.py analytics basic_stats '{"file": "results/series/BTC_MVRV.json"}'
    python cli/fetch.py analytics trend_direction '{"file": "results/series/BTC_price.json", "window": 30}'
"""

import json
import math
from typing import List, Dict, Tuple, Optional, Union
from datetime import datetime, timedelta


# =============================================================================
# BASIC STATISTICS
# =============================================================================

def mean(values: List[float]) -> float:
    """Calculate arithmetic mean."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def median(values: List[float]) -> float:
    """Calculate median value."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2
    return sorted_vals[mid]


def std(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)


def percentile(values: List[float], p: int) -> float:
    """Calculate p-th percentile (0-100)."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[int(f)] * (c - k) + sorted_vals[int(c)] * (k - f)


def current_percentile(values: List[float]) -> int:
    """Get percentile rank of current (last) value vs history."""
    if len(values) < 2:
        return 50
    current = values[-1]
    below = sum(1 for v in values[:-1] if v < current)
    return int(100 * below / (len(values) - 1))


def basic_stats(values: List[float]) -> Dict:
    """Get comprehensive basic statistics."""
    if not values:
        return {"error": "Empty data"}

    return {
        "count": len(values),
        "mean": round(mean(values), 6),
        "median": round(median(values), 6),
        "std": round(std(values), 6),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "current": round(values[-1], 6),
        "current_percentile": current_percentile(values),
        "p25": round(percentile(values, 25), 6),
        "p75": round(percentile(values, 75), 6),
        "p10": round(percentile(values, 10), 6),
        "p90": round(percentile(values, 90), 6),
    }


# =============================================================================
# EXTREMES AND RANGES
# =============================================================================

def find_max(values: List[float], dates: List[str] = None) -> Dict:
    """Find maximum value and its date."""
    if not values:
        return {"error": "Empty data"}
    max_val = max(values)
    max_idx = values.index(max_val)
    result = {"value": round(max_val, 6), "index": max_idx}
    if dates and max_idx < len(dates):
        result["date"] = dates[max_idx]
    return result


def find_min(values: List[float], dates: List[str] = None) -> Dict:
    """Find minimum value and its date."""
    if not values:
        return {"error": "Empty data"}
    min_val = min(values)
    min_idx = values.index(min_val)
    result = {"value": round(min_val, 6), "index": min_idx}
    if dates and min_idx < len(dates):
        result["date"] = dates[min_idx]
    return result


def find_local_maxima(values: List[float], window: int = 5, dates: List[str] = None) -> List[Dict]:
    """Find local maxima with given window size."""
    if len(values) < window * 2 + 1:
        return []

    maxima = []
    for i in range(window, len(values) - window):
        is_max = all(values[i] >= values[j] for j in range(i - window, i + window + 1))
        if is_max:
            point = {"value": round(values[i], 6), "index": i}
            if dates and i < len(dates):
                point["date"] = dates[i]
            maxima.append(point)
    return maxima


def find_local_minima(values: List[float], window: int = 5, dates: List[str] = None) -> List[Dict]:
    """Find local minima with given window size."""
    if len(values) < window * 2 + 1:
        return []

    minima = []
    for i in range(window, len(values) - window):
        is_min = all(values[i] <= values[j] for j in range(i - window, i + window + 1))
        if is_min:
            point = {"value": round(values[i], 6), "index": i}
            if dates and i < len(dates):
                point["date"] = dates[i]
            minima.append(point)
    return minima


def calculate_range(values: List[float]) -> Dict:
    """Calculate value range and current position within it."""
    if not values:
        return {"error": "Empty data"}

    min_val = min(values)
    max_val = max(values)
    current = values[-1]
    range_size = max_val - min_val

    position_pct = 0 if range_size == 0 else (current - min_val) / range_size * 100

    return {
        "min": round(min_val, 6),
        "max": round(max_val, 6),
        "range": round(range_size, 6),
        "current": round(current, 6),
        "position_pct": round(position_pct, 2),
        "interpretation": "bottom" if position_pct < 20 else "lower" if position_pct < 40 else "middle" if position_pct < 60 else "upper" if position_pct < 80 else "top"
    }


def distance_from_ath(values: List[float], dates: List[str] = None) -> Dict:
    """Calculate distance from all-time high."""
    if not values:
        return {"error": "Empty data"}

    ath = max(values)
    ath_idx = values.index(ath)
    current = values[-1]
    drawdown = (current - ath) / ath * 100 if ath != 0 else 0

    result = {
        "ath": round(ath, 6),
        "ath_index": ath_idx,
        "current": round(current, 6),
        "drawdown_pct": round(drawdown, 2),
        "recovery_needed_pct": round((ath - current) / current * 100 if current != 0 else 0, 2)
    }
    if dates and ath_idx < len(dates):
        result["ath_date"] = dates[ath_idx]
    return result


def distance_from_atl(values: List[float], dates: List[str] = None) -> Dict:
    """Calculate distance from all-time low."""
    if not values:
        return {"error": "Empty data"}

    atl = min(values)
    atl_idx = values.index(atl)
    current = values[-1]
    gain = (current - atl) / atl * 100 if atl != 0 else 0

    result = {
        "atl": round(atl, 6),
        "atl_index": atl_idx,
        "current": round(current, 6),
        "gain_from_atl_pct": round(gain, 2)
    }
    if dates and atl_idx < len(dates):
        result["atl_date"] = dates[atl_idx]
    return result


# =============================================================================
# TRENDS AND MOMENTUM
# =============================================================================

def moving_average(values: List[float], window: int) -> List[float]:
    """Calculate simple moving average."""
    if len(values) < window:
        return []

    ma = []
    for i in range(window - 1, len(values)):
        ma.append(round(mean(values[i - window + 1:i + 1]), 6))
    return ma


def ema(values: List[float], window: int) -> List[float]:
    """Calculate exponential moving average."""
    if not values:
        return []

    multiplier = 2 / (window + 1)
    ema_values = [values[0]]

    for i in range(1, len(values)):
        ema_val = (values[i] - ema_values[-1]) * multiplier + ema_values[-1]
        ema_values.append(round(ema_val, 6))

    return ema_values


def rate_of_change(values: List[float], periods: int) -> List[float]:
    """Calculate rate of change (ROC) as percentage."""
    if len(values) <= periods:
        return []

    roc = []
    for i in range(periods, len(values)):
        if values[i - periods] != 0:
            change = (values[i] - values[i - periods]) / values[i - periods] * 100
            roc.append(round(change, 4))
        else:
            roc.append(0.0)
    return roc


def trend_direction(values: List[float], window: int = 20) -> Dict:
    """Determine trend direction: up, down, or sideways."""
    if len(values) < window:
        return {"direction": "unknown", "confidence": 0}

    recent = values[-window:]
    ma = moving_average(values, window)

    if not ma:
        return {"direction": "unknown", "confidence": 0}

    # Linear regression slope
    x_mean = (window - 1) / 2
    y_mean = mean(recent)

    numerator = sum((i - x_mean) * (recent[i] - y_mean) for i in range(window))
    denominator = sum((i - x_mean) ** 2 for i in range(window))

    slope = numerator / denominator if denominator != 0 else 0

    # Normalize slope relative to mean
    normalized_slope = slope / y_mean * 100 if y_mean != 0 else 0

    # Determine direction
    if normalized_slope > 0.5:
        direction = "up"
    elif normalized_slope < -0.5:
        direction = "down"
    else:
        direction = "sideways"

    # Confidence based on R-squared
    ss_tot = sum((recent[i] - y_mean) ** 2 for i in range(window))
    predicted = [y_mean + slope * (i - x_mean) for i in range(window)]
    ss_res = sum((recent[i] - predicted[i]) ** 2 for i in range(window))
    r_squared = 1 - ss_res / ss_tot if ss_tot != 0 else 0

    return {
        "direction": direction,
        "slope": round(normalized_slope, 4),
        "confidence": round(max(0, min(1, r_squared)), 4),
        "interpretation": f"{'Strong' if abs(normalized_slope) > 2 else 'Moderate' if abs(normalized_slope) > 1 else 'Weak'} {direction}trend" if direction != "sideways" else "Consolidation"
    }


def trend_strength(values: List[float], window: int = 20) -> float:
    """Calculate trend strength from 0 (no trend) to 1 (strong trend)."""
    trend = trend_direction(values, window)
    return abs(trend.get("slope", 0)) / 10  # Normalize to 0-1 range roughly


def momentum(values: List[float], periods: int = 14) -> float:
    """Calculate momentum (current - n periods ago)."""
    if len(values) <= periods:
        return 0.0
    return round(values[-1] - values[-periods - 1], 6)


def acceleration(values: List[float], periods: int = 14) -> float:
    """Calculate acceleration (change in momentum)."""
    if len(values) <= periods * 2:
        return 0.0

    mom_current = values[-1] - values[-periods - 1]
    mom_previous = values[-periods - 1] - values[-periods * 2 - 1]

    return round(mom_current - mom_previous, 6)


# =============================================================================
# VOLATILITY
# =============================================================================

def volatility(values: List[float], window: int = 20) -> float:
    """Calculate rolling volatility (std of returns)."""
    if len(values) < window + 1:
        return 0.0

    # Calculate returns
    returns = [(values[i] - values[i-1]) / values[i-1] * 100
               for i in range(1, len(values)) if values[i-1] != 0]

    if len(returns) < window:
        return 0.0

    recent_returns = returns[-window:]
    return round(std(recent_returns), 4)


def atr(highs: List[float], lows: List[float], closes: List[float], window: int = 14) -> float:
    """Calculate Average True Range."""
    if len(highs) < window + 1 or len(lows) < window + 1 or len(closes) < window + 1:
        return 0.0

    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i-1]),
            abs(lows[i] - closes[i-1])
        )
        true_ranges.append(tr)

    if len(true_ranges) < window:
        return 0.0

    return round(mean(true_ranges[-window:]), 6)


def bollinger_position(values: List[float], window: int = 20) -> Dict:
    """Calculate position within Bollinger Bands (-1 to +1)."""
    if len(values) < window:
        return {"error": "Insufficient data"}

    ma = mean(values[-window:])
    sigma = std(values[-window:])

    upper = ma + 2 * sigma
    lower = ma - 2 * sigma
    current = values[-1]

    # Position: -1 at lower band, 0 at MA, +1 at upper band
    band_width = upper - lower
    if band_width == 0:
        position = 0
    else:
        position = (current - ma) / (sigma * 2) if sigma != 0 else 0

    return {
        "position": round(position, 4),
        "upper_band": round(upper, 6),
        "middle_band": round(ma, 6),
        "lower_band": round(lower, 6),
        "current": round(current, 6),
        "bandwidth_pct": round(band_width / ma * 100 if ma != 0 else 0, 2),
        "interpretation": "overbought" if position > 1 else "upper_zone" if position > 0.5 else "neutral" if position > -0.5 else "lower_zone" if position > -1 else "oversold"
    }


def volatility_regime(values: List[float], window: int = 20) -> Dict:
    """Determine volatility regime: low, normal, high, extreme."""
    if len(values) < window * 4:
        return {"regime": "unknown", "current_vol": 0, "avg_vol": 0}

    # Calculate historical volatility series
    vol_series = []
    for i in range(window, len(values)):
        vol = volatility(values[:i+1], window)
        vol_series.append(vol)

    current_vol = vol_series[-1] if vol_series else 0
    avg_vol = mean(vol_series) if vol_series else 0
    vol_std = std(vol_series) if len(vol_series) > 1 else 0

    # Determine regime
    if vol_std == 0:
        z_score = 0
    else:
        z_score = (current_vol - avg_vol) / vol_std

    if z_score < -1:
        regime = "low"
    elif z_score < 1:
        regime = "normal"
    elif z_score < 2:
        regime = "high"
    else:
        regime = "extreme"

    return {
        "regime": regime,
        "current_vol": round(current_vol, 4),
        "avg_vol": round(avg_vol, 4),
        "z_score": round(z_score, 2),
        "interpretation": f"{regime.capitalize()} volatility environment"
    }


# =============================================================================
# CORRELATIONS
# =============================================================================

def correlation(values1: List[float], values2: List[float]) -> float:
    """Calculate Pearson correlation coefficient."""
    n = min(len(values1), len(values2))
    if n < 2:
        return 0.0

    v1, v2 = values1[-n:], values2[-n:]
    mean1, mean2 = mean(v1), mean(v2)

    numerator = sum((v1[i] - mean1) * (v2[i] - mean2) for i in range(n))
    denom1 = math.sqrt(sum((v1[i] - mean1) ** 2 for i in range(n)))
    denom2 = math.sqrt(sum((v2[i] - mean2) ** 2 for i in range(n)))

    if denom1 == 0 or denom2 == 0:
        return 0.0

    return round(numerator / (denom1 * denom2), 4)


def rolling_correlation(values1: List[float], values2: List[float], window: int = 30) -> List[float]:
    """Calculate rolling correlation."""
    n = min(len(values1), len(values2))
    if n < window:
        return []

    correlations = []
    for i in range(window, n + 1):
        corr = correlation(values1[i-window:i], values2[i-window:i])
        correlations.append(corr)

    return correlations


def correlation_matrix(datasets: Dict[str, List[float]]) -> Dict:
    """Calculate correlation matrix for multiple datasets."""
    names = list(datasets.keys())
    n = len(names)

    matrix = {}
    for i in range(n):
        matrix[names[i]] = {}
        for j in range(n):
            if i == j:
                matrix[names[i]][names[j]] = 1.0
            else:
                corr = correlation(datasets[names[i]], datasets[names[j]])
                matrix[names[i]][names[j]] = corr

    return matrix


def lead_lag(values1: List[float], values2: List[float], max_lag: int = 30) -> Dict:
    """Determine if one series leads or lags another."""
    n = min(len(values1), len(values2))
    if n < max_lag * 2:
        return {"error": "Insufficient data"}

    correlations = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            corr = correlation(values1[-lag:n], values2[:n+lag])
        elif lag > 0:
            corr = correlation(values1[:n-lag], values2[lag:n])
        else:
            corr = correlation(values1[-n:], values2[-n:])
        correlations[lag] = corr

    best_lag = max(correlations, key=lambda x: abs(correlations[x]))

    return {
        "best_lag": best_lag,
        "max_correlation": correlations[best_lag],
        "interpretation": f"Series 1 {'leads' if best_lag > 0 else 'lags' if best_lag < 0 else 'is synchronous with'} Series 2 by {abs(best_lag)} periods"
    }


# =============================================================================
# COMPARISONS
# =============================================================================

def compare_periods(values: List[float], period1: Tuple[int, int], period2: Tuple[int, int]) -> Dict:
    """Compare two periods of data."""
    slice1 = values[period1[0]:period1[1]]
    slice2 = values[period2[0]:period2[1]]

    if not slice1 or not slice2:
        return {"error": "Invalid periods"}

    avg1, avg2 = mean(slice1), mean(slice2)
    change_pct = (avg2 - avg1) / avg1 * 100 if avg1 != 0 else 0

    return {
        "period1_avg": round(avg1, 6),
        "period2_avg": round(avg2, 6),
        "change_pct": round(change_pct, 2),
        "period1_volatility": round(std(slice1), 6),
        "period2_volatility": round(std(slice2), 6),
        "period1_count": len(slice1),
        "period2_count": len(slice2)
    }


def compare_to_history(values: List[float], current_window: int = 30) -> Dict:
    """Compare current period to entire history."""
    if len(values) < current_window * 2:
        return {"error": "Insufficient data"}

    current = values[-current_window:]
    history = values[:-current_window]

    current_avg = mean(current)
    history_avg = mean(history)
    change = (current_avg - history_avg) / history_avg * 100 if history_avg != 0 else 0

    current_vol = std(current)
    history_vol = std(history)

    return {
        "current_avg": round(current_avg, 6),
        "history_avg": round(history_avg, 6),
        "change_pct": round(change, 2),
        "current_volatility": round(current_vol, 6),
        "history_volatility": round(history_vol, 6),
        "current_vs_history_percentile": current_percentile(history + [current_avg]),
        "interpretation": "above_average" if change > 10 else "below_average" if change < -10 else "in_line"
    }


def yoy_change(values: List[float], periods_per_year: int = 365) -> float:
    """Calculate year-over-year change."""
    if len(values) <= periods_per_year:
        return 0.0

    current = values[-1]
    year_ago = values[-periods_per_year - 1]

    if year_ago == 0:
        return 0.0

    return round((current - year_ago) / year_ago * 100, 2)


def mom_change(values: List[float], periods_per_month: int = 30) -> float:
    """Calculate month-over-month change."""
    if len(values) <= periods_per_month:
        return 0.0

    current = values[-1]
    month_ago = values[-periods_per_month - 1]

    if month_ago == 0:
        return 0.0

    return round((current - month_ago) / month_ago * 100, 2)


# =============================================================================
# ANOMALIES AND PATTERNS
# =============================================================================

def detect_anomalies(values: List[float], z_threshold: float = 2.5, dates: List[str] = None) -> List[Dict]:
    """Detect anomalies using z-score method."""
    if len(values) < 10:
        return []

    avg = mean(values)
    sigma = std(values)

    if sigma == 0:
        return []

    anomalies = []
    for i, v in enumerate(values):
        z = (v - avg) / sigma
        if abs(z) > z_threshold:
            anomaly = {
                "index": i,
                "value": round(v, 6),
                "z_score": round(z, 2),
                "type": "high" if z > 0 else "low"
            }
            if dates and i < len(dates):
                anomaly["date"] = dates[i]
            anomalies.append(anomaly)

    return anomalies


def detect_regime_change(values: List[float], window: int = 20, threshold: float = 2.0, dates: List[str] = None) -> List[Dict]:
    """Detect regime change points."""
    if len(values) < window * 3:
        return []

    changes = []
    for i in range(window * 2, len(values)):
        before = values[i-window*2:i-window]
        after = values[i-window:i]

        mean_before = mean(before)
        mean_after = mean(after)
        vol_before = std(before)

        if vol_before > 0:
            change_zscore = abs(mean_after - mean_before) / vol_before
            if change_zscore > threshold:
                point = {
                    "index": i - window,
                    "z_score": round(change_zscore, 2),
                    "mean_before": round(mean_before, 6),
                    "mean_after": round(mean_after, 6),
                    "direction": "up" if mean_after > mean_before else "down"
                }
                if dates and i - window < len(dates):
                    point["date"] = dates[i - window]
                changes.append(point)

    return changes


def find_divergence(price: List[float], indicator: List[float], window: int = 14) -> List[Dict]:
    """Find divergences between price and indicator."""
    n = min(len(price), len(indicator))
    if n < window * 2:
        return []

    divergences = []
    price_highs = find_local_maxima(price[-n:], window)
    price_lows = find_local_minima(price[-n:], window)

    # Bullish divergence: price lower low, indicator higher low
    for i in range(1, len(price_lows)):
        if price_lows[i]["value"] < price_lows[i-1]["value"]:
            idx1, idx2 = price_lows[i-1]["index"], price_lows[i]["index"]
            if idx1 < len(indicator) and idx2 < len(indicator):
                if indicator[idx2] > indicator[idx1]:
                    divergences.append({
                        "type": "bullish",
                        "price_index": idx2,
                        "description": "Price lower low, indicator higher low"
                    })

    # Bearish divergence: price higher high, indicator lower high
    for i in range(1, len(price_highs)):
        if price_highs[i]["value"] > price_highs[i-1]["value"]:
            idx1, idx2 = price_highs[i-1]["index"], price_highs[i]["index"]
            if idx1 < len(indicator) and idx2 < len(indicator):
                if indicator[idx2] < indicator[idx1]:
                    divergences.append({
                        "type": "bearish",
                        "price_index": idx2,
                        "description": "Price higher high, indicator lower high"
                    })

    return divergences


def detect_breakout(values: List[float], lookback: int = 20, dates: List[str] = None) -> Dict:
    """Detect if current value is breaking out of recent range."""
    if len(values) < lookback + 1:
        return {"breakout": False}

    recent = values[-lookback-1:-1]
    current = values[-1]

    high = max(recent)
    low = min(recent)

    is_breakout_up = current > high
    is_breakout_down = current < low

    result = {
        "breakout": is_breakout_up or is_breakout_down,
        "direction": "up" if is_breakout_up else "down" if is_breakout_down else None,
        "current": round(current, 6),
        "resistance": round(high, 6),
        "support": round(low, 6),
        "breakout_pct": round((current - high) / high * 100 if is_breakout_up else (current - low) / low * 100 if is_breakout_down else 0, 2)
    }

    if dates:
        result["date"] = dates[-1] if len(dates) > 0 else None

    return result


# =============================================================================
# DISTRIBUTION AND PROBABILITIES
# =============================================================================

def distribution_stats(values: List[float]) -> Dict:
    """Calculate distribution statistics."""
    if len(values) < 4:
        return {"error": "Insufficient data"}

    n = len(values)
    avg = mean(values)
    sigma = std(values)

    # Skewness
    if sigma == 0:
        skew = 0
    else:
        skew = sum(((v - avg) / sigma) ** 3 for v in values) / n

    # Kurtosis
    if sigma == 0:
        kurt = 0
    else:
        kurt = sum(((v - avg) / sigma) ** 4 for v in values) / n - 3  # Excess kurtosis

    return {
        "skewness": round(skew, 4),
        "kurtosis": round(kurt, 4),
        "interpretation_skew": "right_skewed" if skew > 0.5 else "left_skewed" if skew < -0.5 else "symmetric",
        "interpretation_kurtosis": "fat_tails" if kurt > 1 else "thin_tails" if kurt < -1 else "normal_tails"
    }


def value_at_risk(values: List[float], confidence: float = 0.95) -> Dict:
    """Calculate Value at Risk."""
    if len(values) < 30:
        return {"error": "Insufficient data"}

    # Calculate returns
    returns = [(values[i] - values[i-1]) / values[i-1] * 100
               for i in range(1, len(values)) if values[i-1] != 0]

    p = (1 - confidence) * 100
    var = percentile(returns, p)

    return {
        "var": round(var, 4),
        "confidence": confidence,
        "interpretation": f"With {confidence*100}% confidence, daily loss will not exceed {abs(var):.2f}%"
    }


def probability_above(values: List[float], threshold: float) -> float:
    """Calculate historical probability of being above threshold."""
    if not values:
        return 0.0

    above = sum(1 for v in values if v > threshold)
    return round(above / len(values) * 100, 2)


def expected_range(values: List[float], days: int = 30, confidence: float = 0.95) -> Dict:
    """Calculate expected price range for next N days."""
    if len(values) < 60:
        return {"error": "Insufficient data"}

    # Calculate daily returns
    returns = [(values[i] - values[i-1]) / values[i-1]
               for i in range(1, len(values)) if values[i-1] != 0]

    avg_return = mean(returns)
    vol = std(returns)

    current = values[-1]

    # Z-score for confidence
    z = 1.96 if confidence == 0.95 else 2.58 if confidence == 0.99 else 1.645

    expected_return = avg_return * days
    expected_vol = vol * math.sqrt(days)

    upper = current * (1 + expected_return + z * expected_vol)
    lower = current * (1 + expected_return - z * expected_vol)
    expected = current * (1 + expected_return)

    return {
        "current": round(current, 6),
        "expected": round(expected, 6),
        "lower_bound": round(lower, 6),
        "upper_bound": round(upper, 6),
        "days": days,
        "confidence": confidence
    }


# =============================================================================
# CRYPTO-SPECIFIC
# =============================================================================

def mvrv_zscore(mvrv_values: List[float]) -> Dict:
    """Calculate MVRV Z-Score and interpretation."""
    if len(mvrv_values) < 30:
        return {"error": "Insufficient data"}

    current = mvrv_values[-1]
    avg = mean(mvrv_values)
    sigma = std(mvrv_values)

    zscore = (current - avg) / sigma if sigma != 0 else 0

    # Standard MVRV interpretation
    if current < 1:
        market_phase = "undervalued"
    elif current < 2:
        market_phase = "fair_value"
    elif current < 3:
        market_phase = "overvalued"
    else:
        market_phase = "extremely_overvalued"

    return {
        "mvrv": round(current, 4),
        "zscore": round(zscore, 4),
        "mean": round(avg, 4),
        "std": round(sigma, 4),
        "market_phase": market_phase,
        "interpretation": f"MVRV {current:.2f} ({market_phase.replace('_', ' ')}), Z-Score: {zscore:.2f}"
    }


def supply_distribution(lth_supply: List[float], sth_supply: List[float]) -> Dict:
    """Analyze LTH/STH supply distribution."""
    if not lth_supply or not sth_supply:
        return {"error": "Missing data"}

    n = min(len(lth_supply), len(sth_supply))
    current_lth = lth_supply[-1]
    current_sth = sth_supply[-1]
    total = current_lth + current_sth

    lth_pct = current_lth / total * 100 if total > 0 else 0
    sth_pct = current_sth / total * 100 if total > 0 else 0

    # Calculate ratio trend
    ratios = [lth_supply[i] / sth_supply[i] if sth_supply[i] > 0 else 0 for i in range(n)]
    ratio_trend = trend_direction(ratios, min(30, n // 2))

    return {
        "lth_supply": round(current_lth, 2),
        "sth_supply": round(current_sth, 2),
        "lth_pct": round(lth_pct, 2),
        "sth_pct": round(sth_pct, 2),
        "lth_sth_ratio": round(current_lth / current_sth if current_sth > 0 else 0, 4),
        "ratio_trend": ratio_trend["direction"],
        "interpretation": "accumulation" if ratio_trend["direction"] == "up" else "distribution" if ratio_trend["direction"] == "down" else "neutral"
    }


def funding_rate_signal(funding_rates: List[float]) -> Dict:
    """Analyze funding rate for market sentiment."""
    if len(funding_rates) < 7:
        return {"error": "Insufficient data"}

    current = funding_rates[-1]
    avg_7d = mean(funding_rates[-7:])
    avg_30d = mean(funding_rates[-30:]) if len(funding_rates) >= 30 else mean(funding_rates)

    # Annualized funding
    annualized = current * 3 * 365  # Assuming 8-hour funding

    if current > 0.05:
        signal = "extremely_bullish"
    elif current > 0.01:
        signal = "bullish"
    elif current > -0.01:
        signal = "neutral"
    elif current > -0.05:
        signal = "bearish"
    else:
        signal = "extremely_bearish"

    return {
        "current": round(current, 6),
        "avg_7d": round(avg_7d, 6),
        "avg_30d": round(avg_30d, 6),
        "annualized_pct": round(annualized, 2),
        "signal": signal,
        "interpretation": f"Funding {signal.replace('_', ' ')}: {current*100:.4f}% ({annualized:.1f}% annualized)"
    }


# =============================================================================
# META-ANALYSIS
# =============================================================================

def summarize_signals(metrics: Dict[str, Dict]) -> Dict:
    """Summarize multiple metrics into overall signal."""
    bullish = 0
    bearish = 0
    neutral = 0

    signal_keywords = {
        "bullish": ["bullish", "up", "accumulation", "undervalued", "oversold", "bottom"],
        "bearish": ["bearish", "down", "distribution", "overvalued", "overbought", "top"],
        "neutral": ["neutral", "sideways", "fair_value", "consolidation", "normal"]
    }

    for name, metric in metrics.items():
        metric_str = str(metric).lower()

        if any(kw in metric_str for kw in signal_keywords["bullish"]):
            bullish += 1
        elif any(kw in metric_str for kw in signal_keywords["bearish"]):
            bearish += 1
        else:
            neutral += 1

    total = bullish + bearish + neutral

    if bullish > bearish + neutral:
        consensus = "bullish"
    elif bearish > bullish + neutral:
        consensus = "bearish"
    else:
        consensus = "neutral"

    confidence = max(bullish, bearish, neutral) / total if total > 0 else 0

    return {
        "bullish_count": bullish,
        "bearish_count": bearish,
        "neutral_count": neutral,
        "total": total,
        "consensus": consensus,
        "confidence": round(confidence, 2),
        "summary": f"{consensus.capitalize()} ({bullish}B/{bearish}Be/{neutral}N), confidence: {confidence*100:.0f}%"
    }


def find_contradictions(metrics: Dict[str, Dict]) -> List[Dict]:
    """Find contradicting signals in metrics."""
    contradictions = []

    metric_signals = {}
    for name, metric in metrics.items():
        metric_str = str(metric).lower()
        if "bullish" in metric_str or "up" in metric_str:
            metric_signals[name] = "bullish"
        elif "bearish" in metric_str or "down" in metric_str:
            metric_signals[name] = "bearish"

    bullish_metrics = [k for k, v in metric_signals.items() if v == "bullish"]
    bearish_metrics = [k for k, v in metric_signals.items() if v == "bearish"]

    if bullish_metrics and bearish_metrics:
        contradictions.append({
            "bullish_signals": bullish_metrics,
            "bearish_signals": bearish_metrics,
            "note": "Mixed signals detected"
        })

    return contradictions


# =============================================================================
# CLI HELPERS
# =============================================================================

def load_series_file(filepath: str) -> Dict:
    """Load a series JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data


def full_analysis(values: List[float], dates: List[str] = None) -> Dict:
    """
    Complete metric analysis for aggregator.

    Returns structured analysis with:
    - Quantitative stats (mean, percentiles, current position)
    - Trend analysis (30d, 90d directions)
    - Volatility regime
    - Historical context (ATH distance, range position)
    - Anomalies and regime changes
    - Auto-generated interpretation
    """
    if not values or len(values) < 10:
        return {"error": "Insufficient data (need at least 10 points)"}

    # Core stats
    stats = basic_stats(values)
    pct = current_percentile(values)
    rng = calculate_range(values)

    # Trends
    trend_30 = trend_direction(values, min(30, len(values) // 2)) if len(values) >= 10 else {"direction": "unknown"}
    trend_90 = trend_direction(values, min(90, len(values) // 2)) if len(values) >= 20 else {"direction": "unknown"}

    # Volatility
    vol = volatility_regime(values) if len(values) >= 80 else {"regime": "unknown", "note": "Need 80+ points"}

    # Historical context
    ath = distance_from_ath(values, dates)
    atl = distance_from_atl(values, dates)

    # Anomalies and regime changes
    anomalies = detect_anomalies(values, dates=dates, z_threshold=2.0)[-5:]  # Last 5
    regime_changes = detect_regime_change(values, dates=dates)[-3:] if len(values) >= 60 else []

    # Breakout check
    breakout = detect_breakout(values, lookback=min(20, len(values) // 3), dates=dates)

    # Auto-interpretation
    interpretation = _generate_interpretation(stats, pct, trend_30, trend_90, rng, ath, vol, breakout)

    return {
        "data_points": len(values),
        "current_value": stats["current"],

        "quantitative": {
            "mean": stats["mean"],
            "std": stats["std"],
            "min": stats["min"],
            "max": stats["max"],
            "percentile_current": pct,
            "percentile_10": stats["p10"],
            "percentile_90": stats["p90"],
        },

        "position": {
            "in_range": rng["interpretation"],  # bottom/lower/middle/upper/top
            "range_position_pct": rng["position_pct"],
            "vs_mean": round((stats["current"] - stats["mean"]) / stats["mean"] * 100, 2) if stats["mean"] != 0 else 0,
            "vs_mean_text": "above" if stats["current"] > stats["mean"] else "below" if stats["current"] < stats["mean"] else "at",
        },

        "trends": {
            "trend_30d": trend_30.get("direction", "unknown"),
            "trend_30d_strength": trend_30.get("slope", 0),
            "trend_30d_confidence": trend_30.get("confidence", 0),
            "trend_90d": trend_90.get("direction", "unknown"),
            "trend_90d_strength": trend_90.get("slope", 0),
            "trend_alignment": "aligned" if trend_30.get("direction") == trend_90.get("direction") else "diverging",
        },

        "volatility": {
            "regime": vol.get("regime", "unknown"),
            "current_vol": vol.get("current_vol", 0),
            "z_score": vol.get("z_score", 0),
        },

        "historical": {
            "ath": ath.get("ath"),
            "ath_date": ath.get("ath_date"),
            "drawdown_pct": ath.get("drawdown_pct"),
            "atl": atl.get("atl"),
            "gain_from_atl_pct": atl.get("gain_from_atl_pct"),
        },

        "signals": {
            "breakout": breakout.get("breakout", False),
            "breakout_direction": breakout.get("direction"),
            "anomalies_count": len(anomalies),
            "recent_anomalies": anomalies,
            "regime_changes": regime_changes,
        },

        "interpretation": interpretation,
    }


def _generate_interpretation(stats, pct, trend_30, trend_90, rng, ath, vol, breakout) -> Dict:
    """Generate human-readable interpretation."""

    # Determine signal
    bullish_signals = 0
    bearish_signals = 0

    # Trend signals
    if trend_30.get("direction") == "up":
        bullish_signals += 1
    elif trend_30.get("direction") == "down":
        bearish_signals += 1

    if trend_90.get("direction") == "up":
        bullish_signals += 1
    elif trend_90.get("direction") == "down":
        bearish_signals += 1

    # Position signals
    if pct >= 80:
        bearish_signals += 1  # High percentile = potentially overextended
    elif pct <= 20:
        bullish_signals += 1  # Low percentile = potentially undervalued

    # Breakout signals
    if breakout.get("breakout"):
        if breakout.get("direction") == "up":
            bullish_signals += 1
        else:
            bearish_signals += 1

    # Determine overall signal
    if bullish_signals > bearish_signals + 1:
        signal = "bullish"
    elif bearish_signals > bullish_signals + 1:
        signal = "bearish"
    else:
        signal = "neutral"

    # Confidence
    total_signals = bullish_signals + bearish_signals
    if total_signals == 0:
        confidence = "low"
    else:
        max_signals = max(bullish_signals, bearish_signals)
        if max_signals >= 3:
            confidence = "high"
        elif max_signals >= 2:
            confidence = "medium"
        else:
            confidence = "low"

    # Generate text
    position_text = f"Current value is in {pct}th percentile ({rng['interpretation']} of historical range)"
    trend_text = f"30d trend: {trend_30.get('direction', 'unknown')}, 90d trend: {trend_90.get('direction', 'unknown')}"

    if ath.get("drawdown_pct", 0) < -10:
        ath_text = f"{abs(ath['drawdown_pct']):.1f}% below ATH"
    elif ath.get("drawdown_pct", 0) == 0:
        ath_text = "At ATH"
    else:
        ath_text = f"Near ATH ({ath['drawdown_pct']:.1f}%)"

    # Build key points list (filter out None)
    key_points = [
        position_text,
        trend_text,
        ath_text,
    ]
    if vol.get('regime') and vol.get('regime') != 'unknown':
        key_points.append(f"Volatility: {vol['regime']}")
    if breakout.get('breakout'):
        key_points.append(f"Breakout {breakout['direction']}!")

    return {
        "signal": signal,
        "confidence": confidence,
        "bullish_factors": bullish_signals,
        "bearish_factors": bearish_signals,
        "summary": f"{signal.upper()} ({confidence} confidence). {position_text}. {trend_text}. {ath_text}.",
        "key_points": key_points
    }


def analyze_series(filepath: str, analysis_type: str = "full") -> Dict:
    """Run comprehensive analysis on a series file."""
    data = load_series_file(filepath)

    values = data.get("values", [])
    dates = data.get("labels", [])

    if not values:
        return {"error": "No values in file"}

    if analysis_type == "basic":
        return basic_stats(values)

    # Full analysis using new function
    return full_analysis(values, dates)


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Test with sample data
    print("=== Series Analyzer Test ===\n")

    # Generate sample data
    import random
    random.seed(42)

    sample_values = [100]
    for _ in range(99):
        change = random.gauss(0, 2)
        sample_values.append(sample_values[-1] * (1 + change / 100))

    print("Basic Stats:", basic_stats(sample_values))
    print("\nTrend:", trend_direction(sample_values))
    print("\nVolatility:", volatility_regime(sample_values))
    print("\nRange:", calculate_range(sample_values))
    print("\nBreakout:", detect_breakout(sample_values))
