#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ralph Chart Renderer CLI

Renders Plotly charts from series data and outputs analysis summary.
Solves the problem of Claude losing data when copying large arrays.

Usage:
    python render_charts.py --chart-data state/chart_data.json --series-dir results/series/ --output-dir output/charts/

Arguments:
    --chart-data    Path to chart specifications JSON
    --series-dir    Directory with series JSON files
    --output-dir    Directory to save rendered HTML charts

Output:
    - HTML files in output-dir (one per chart)
    - JSON summary to stdout with analysis results
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    print(json.dumps({"error": "plotly not installed. Run: pip install plotly"}))
    sys.exit(1)

try:
    import numpy as np
except ImportError:
    np = None  # Will use pure Python for calculations


def load_json(path: str) -> Optional[Dict]:
    """Load JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None


def calculate_trend(values: List[float], days: int) -> Dict[str, Any]:
    """Calculate trend over specified number of days."""
    if not values or len(values) < 2:
        return {"direction": "unknown", "change": 0, "percent": 0}

    # Take last N values
    period_values = values[-days:] if len(values) >= days else values

    if len(period_values) < 2:
        return {"direction": "flat", "change": 0, "percent": 0}

    start_val = period_values[0]
    end_val = period_values[-1]

    change = end_val - start_val
    percent = (change / start_val * 100) if start_val != 0 else 0

    if abs(percent) < 1:
        direction = "flat"
    elif change > 0:
        direction = "up"
    else:
        direction = "down"

    return {
        "direction": direction,
        "change": round(change, 2),
        "percent": round(percent, 2)
    }


def detect_pattern(values: List[float]) -> Dict[str, str]:
    """Detect pattern in time series."""
    if not values or len(values) < 10:
        return {"pattern": "insufficient_data", "description": "Not enough data points"}

    # Calculate simple metrics
    first_half = values[:len(values)//2]
    second_half = values[len(values)//2:]

    avg_first = sum(first_half) / len(first_half)
    avg_second = sum(second_half) / len(second_half)

    # Check for volatility
    if np:
        std_dev = np.std(values)
        mean_val = np.mean(values)
        cv = std_dev / mean_val if mean_val != 0 else 0
    else:
        mean_val = sum(values) / len(values)
        variance = sum((x - mean_val) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        cv = std_dev / mean_val if mean_val != 0 else 0

    # Pattern detection
    change_pct = (avg_second - avg_first) / avg_first * 100 if avg_first != 0 else 0

    if cv > 0.3:
        # High volatility
        if change_pct > 10:
            return {"pattern": "volatile_up", "description": "High volatility with upward trend"}
        elif change_pct < -10:
            return {"pattern": "volatile_down", "description": "High volatility with downward trend"}
        else:
            return {"pattern": "consolidation", "description": "High volatility sideways movement"}
    else:
        # Low volatility
        if change_pct > 5:
            return {"pattern": "accumulation", "description": "Steady upward movement"}
        elif change_pct < -5:
            return {"pattern": "distribution", "description": "Steady downward movement"}
        else:
            return {"pattern": "plateau", "description": "Stable with minimal change"}


def analyze_series(series_data: Dict) -> Dict[str, Any]:
    """Analyze a single series."""
    values = series_data.get("values", [])
    # Support both "timestamps" and "labels" field names (data.md uses labels)
    timestamps = series_data.get("timestamps", series_data.get("labels", []))

    if not values:
        return {"error": "No values in series"}

    # Extract just the values if they're in object format
    if values and isinstance(values[0], dict):
        values = [v.get("value", v.get("y", 0)) for v in values]

    # Convert to float
    values = [float(v) if v is not None else 0 for v in values]

    current = values[-1] if values else 0

    # Key statistics
    analysis = {
        "data_points": len(values),
        "current_value": round(current, 4),
        "trends": {
            "trend_90d": calculate_trend(values, 90),
            "trend_30d": calculate_trend(values, 30),
            "trend_7d": calculate_trend(values, 7)
        },
        "key_levels": {
            "min_90d": round(min(values[-90:]) if len(values) >= 90 else min(values), 4),
            "max_90d": round(max(values[-90:]) if len(values) >= 90 else max(values), 4),
            "avg_90d": round(sum(values[-90:]) / len(values[-90:]) if len(values) >= 90 else sum(values) / len(values), 4)
        }
    }

    # Add pattern detection
    pattern_info = detect_pattern(values)
    analysis["pattern"] = pattern_info["pattern"]
    analysis["pattern_description"] = pattern_info["description"]

    # Add period info if timestamps available
    if timestamps:
        analysis["period"] = {
            "start": timestamps[0] if timestamps else None,
            "end": timestamps[-1] if timestamps else None
        }

    return analysis


def create_narrative_options(analysis: Dict, chart_title: str) -> Dict[str, str]:
    """Generate narrative options for the chart."""
    pattern = analysis.get("pattern", "unknown")
    trend_30d = analysis.get("trends", {}).get("trend_30d", {})
    direction = trend_30d.get("direction", "flat")
    percent = trend_30d.get("percent", 0)

    # Generate interpretations
    if pattern in ["accumulation", "volatile_up"] or direction == "up":
        bullish = f"Strong upward momentum ({percent:+.1f}% за 30d), pattern confirms {pattern}"
        bearish = f"Rally may be overextended, watch for reversal signals"
        neutral = f"Uptrend active ({percent:+.1f}% за 30d), {pattern} pattern detected"
    elif pattern in ["distribution", "volatile_down"] or direction == "down":
        bullish = f"Potential bottoming formation, oversold conditions emerging"
        bearish = f"Downtrend continues ({percent:+.1f}% за 30d), {pattern} pattern indicates further weakness"
        neutral = f"Correction underway ({percent:+.1f}% за 30d), monitoring for stabilization"
    else:
        bullish = f"Consolidation building base for potential breakout"
        bearish = f"Sideways action may resolve lower, watch support levels"
        neutral = f"Range-bound movement, {pattern} pattern, awaiting directional catalyst"

    return {
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral
    }


def render_chart(chart_spec: Dict, series_data: Dict[str, Dict], output_dir: str) -> Dict[str, Any]:
    """Render a single chart and return analysis."""
    # Support both "id" and "chart_id" field names (aggregator uses chart_id)
    chart_id = chart_spec.get("chart_id", chart_spec.get("id", "unknown"))
    title = chart_spec.get("title", f"Chart {chart_id}")
    # Support both "type" and "chart_type" field names
    chart_type = chart_spec.get("chart_type", chart_spec.get("type", "line"))

    # Support multiple formats for series references:
    # 1. "series": [{file, label, secondary_y}] - direct format
    # 2. "source_files": ["series/file.json"] - aggregator format
    # 3. "data.datasets": [{label, data}] - Chart.js format from aggregator
    series_refs = chart_spec.get("series", [])

    # Convert aggregator's source_files format to series format
    if not series_refs and "source_files" in chart_spec:
        for sf in chart_spec["source_files"]:
            # Extract filename from path like "series/BTC_price.json"
            filename = sf.split("/")[-1] if "/" in sf else sf
            series_refs.append({"file": filename, "label": filename.replace(".json", "").replace("_", " ")})

    # Handle Chart.js inline data format (data.datasets)
    inline_data = chart_spec.get("data", {})
    has_inline_data = "datasets" in inline_data and "labels" in inline_data

    # Create figure
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    series_analyses = []
    colors = ["#3366CC", "#DC3912", "#FF9900", "#109618", "#990099", "#0099C6"]

    for i, series_ref in enumerate(series_refs):
        series_name = series_ref.get("name", series_ref.get("file", f"series_{i}"))
        series_file = series_ref.get("file", series_name)

        # Find series data
        if series_file not in series_data:
            continue

        data = series_data[series_file]
        values = data.get("values", [])
        # Support both "timestamps" and "labels" field names (data.md uses labels)
        timestamps = data.get("timestamps", data.get("labels", []))

        # Handle object format
        if values and isinstance(values[0], dict):
            timestamps = [v.get("timestamp", v.get("date", v.get("x"))) for v in values]
            values = [v.get("value", v.get("y", 0)) for v in values]

        if not values:
            continue

        # Add trace
        secondary_y = series_ref.get("secondary_y", False)
        color = colors[i % len(colors)]

        fig.add_trace(
            go.Scatter(
                x=timestamps if timestamps else list(range(len(values))),
                y=values,
                name=series_ref.get("label", series_name),
                line=dict(color=color, width=2),
                hovertemplate="%{y:.2f}<extra>%{fullData.name}</extra>"
            ),
            secondary_y=secondary_y
        )

        # Analyze series
        analysis = analyze_series(data)
        analysis["series"] = series_name
        analysis["file"] = series_file
        series_analyses.append(analysis)

    # Handle Chart.js inline data format (bar charts with inline data)
    # Use inline data if: 1) no series_refs at all, OR 2) series_refs existed but no traces were added
    if has_inline_data and (not series_refs or not fig.data):
        labels = inline_data.get("labels", [])
        for i, dataset in enumerate(inline_data.get("datasets", [])):
            values = dataset.get("data", [])
            label = dataset.get("label", f"Dataset {i}")
            bg_colors = dataset.get("backgroundColor", colors[:len(values)])

            # Determine trace type based on chart_type
            if chart_type in ["bar", "horizontalBar"]:
                fig.add_trace(
                    go.Bar(
                        x=labels,
                        y=values,
                        name=label,
                        marker=dict(color=bg_colors),
                        hovertemplate="%{x}: %{y}<extra></extra>"
                    )
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=labels,
                        y=values,
                        name=label,
                        mode="lines+markers",
                        line=dict(color=bg_colors[0] if isinstance(bg_colors, list) else bg_colors, width=2),
                        hovertemplate="%{y:.2f}<extra>%{fullData.name}</extra>"
                    )
                )

            # Create simple analysis for inline data
            series_analyses.append({
                "series": label,
                "file": "inline",
                "count": len(values),
                "min": min(values) if values else 0,
                "max": max(values) if values else 0,
                "pattern": "inline_data"
            })

    # Check if chart has any data
    if not fig.data:
        raise ValueError(f"Chart {chart_id} has no data to render. Check source_files or data.datasets.")

    # Update layout
    fig.update_layout(
        title=dict(text=title, font=dict(size=16)),
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=60, t=80, b=60)
    )

    # Set axis labels
    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text=chart_spec.get("y_axis_label", "Value"), secondary_y=False)
    if any(s.get("secondary_y") for s in series_refs):
        fig.update_yaxes(title_text=chart_spec.get("y_axis_secondary_label", ""), secondary_y=True)

    # Save chart - sanitize filename for Windows compatibility
    safe_title = title.lower().replace(' ', '_')
    # Remove Windows-invalid characters: : ? * < > | " / \
    for char in ':?*<>|"\\/':
        safe_title = safe_title.replace(char, '')
    output_path = os.path.join(output_dir, f"{chart_id}_{safe_title[:30]}.html")
    fig.write_html(output_path, include_plotlyjs="cdn")

    # Generate visual summary
    if series_analyses:
        main_analysis = series_analyses[0]
        trend = main_analysis.get("trends", {}).get("trend_30d", {})
        pattern = main_analysis.get("pattern", "unknown")
        visual_summary = f"{pattern.replace('_', ' ').title()} pattern. 30d trend: {trend.get('direction', 'unknown')} ({trend.get('percent', 0):+.1f}%)"
    else:
        visual_summary = "No series data available"

    # Build result
    result = {
        "chart_id": chart_id,
        "title": title,
        "rendered_file": output_path,
        "series_analysis": series_analyses,
        "visual_summary": visual_summary,
        "narrative_options": create_narrative_options(
            series_analyses[0] if series_analyses else {},
            title
        )
    }

    return result


def main():
    parser = argparse.ArgumentParser(description="Render charts from series data")
    parser.add_argument("--chart-data", required=True, help="Path to chart specifications JSON")
    parser.add_argument("--series-dir", required=True, help="Directory with series JSON files")
    parser.add_argument("--output-dir", required=True, help="Output directory for HTML charts")

    args = parser.parse_args()

    # Load chart specifications
    chart_data = load_json(args.chart_data)
    if not chart_data:
        print(json.dumps({"error": f"Failed to load chart data from {args.chart_data}"}))
        sys.exit(1)

    charts = chart_data.get("charts", [])
    if not charts:
        print(json.dumps({"error": "No charts defined in chart_data"}))
        sys.exit(1)

    # Load all series files
    series_dir = Path(args.series_dir)
    if not series_dir.exists():
        print(json.dumps({"error": f"Series directory not found: {args.series_dir}"}))
        sys.exit(1)

    series_data = {}
    for series_file in series_dir.glob("*.json"):
        data = load_json(str(series_file))
        if data:
            series_data[series_file.name] = data
            # Also store without extension for flexible matching
            series_data[series_file.stem] = data

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Render each chart
    results = []
    for chart_spec in charts:
        try:
            result = render_chart(chart_spec, series_data, str(output_dir))
            results.append(result)
        except Exception as e:
            results.append({
                "chart_id": chart_spec.get("chart_id", chart_spec.get("id", "unknown")),
                "error": str(e)
            })

    # Build output summary
    output = {
        "generated_at": datetime.now().isoformat(),
        "series_files_processed": len(series_data) // 2,  # Divide by 2 because we store with and without extension
        "charts_rendered": len([r for r in results if "error" not in r]),
        "charts": results
    }

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
