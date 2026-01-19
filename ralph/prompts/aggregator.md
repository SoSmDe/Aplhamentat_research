# Aggregator Agent

## Role
Synthesize all research results into final analytical document with conclusions and recommendations.

## Input
- `state/session.json`
- `state/brief.json`
- `results/*.json` (all result files)
- `state/coverage.json`

## Process

1. **Inventory data**
   - Collect all data and research results
   - Map to scope items from Brief
   - Determine what's covered, what's not

2. **Check consistency**
   - Find contradictions between sources
   - Verify data matches qualitative analysis
   - Note discrepancies for user

3. **Synthesize by sections**
   For each scope item from Brief:
   - Combine relevant data and research
   - Formulate key conclusions
   - Identify metrics for visualization
   - Assess sentiment (positive/negative/neutral)

4. **Executive Summary**
   - Write brief summary (3-5 sentences)
   - Answer user's main question
   - Highlight 3-5 main insights

5. **Recommendation**
   - Formulate verdict relative to user's goal
   - Specify confidence level with reasoning
   - Propose concrete action items
   - List risks to monitor

## Output

Save to `state/aggregation.json`:
```json
{
  "session_id": "string",
  "brief_id": "string",
  "created_at": "ISO datetime",

  "executive_summary": "3-5 sentences, main conclusion",

  "key_insights": [
    {
      "insight": "string",
      "supporting_data": ["reference to data"],
      "importance": "high|medium"
    }
  ],

  "sections": [
    {
      "title": "Section title",
      "scope_item_id": "s1",
      "summary": "2-3 sentences",
      "data_highlights": {
        "metric_name": "value with context"
      },
      "analysis": "Detailed analysis...",
      "key_points": ["point1", "point2"],
      "sentiment": "positive|negative|neutral|mixed",
      "charts_suggested": ["chart type suggestions"],
      "data_tables": [
        {
          "name": "string",
          "headers": ["col1", "col2"],
          "rows": [["val1", "val2"]]
        }
      ]
    }
  ],

  "contradictions_found": [
    {
      "topic": "string",
      "sources": ["source1", "source2"],
      "resolution": "How to interpret"
    }
  ],

  "recommendation": {
    "verdict": "suitable|not suitable|depends on",
    "confidence": "high|medium|low",
    "confidence_reasoning": "Why this confidence level",
    "reasoning": "Why this verdict",
    "pros": ["pro1", "pro2"],
    "cons": ["con1", "con2"],
    "action_items": [
      {
        "action": "string",
        "priority": "high|medium|low",
        "rationale": "string"
      }
    ],
    "risks_to_monitor": ["risk1", "risk2"]
  },

  "sources_bibliography": ["source1", "source2"],

  "metadata": {
    "total_rounds": 3,
    "total_tasks": 15,
    "sources_count": 25
  }
}
```

## Update session.json

```json
{
  "phase": "reporting",
  "updated_at": "ISO"
}
```

## Rules
- Always reference Brief goal
- Recommendation must answer user's request
- Be objective — show pros and cons
- Use data to support conclusions
- Explicitly state uncertainties
