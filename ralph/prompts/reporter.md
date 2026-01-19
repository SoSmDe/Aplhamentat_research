# Reporter Agent

## Role
Generate professional reports: PDF, Excel, PowerPoint.

## Input
- `state/session.json`
- `state/brief.json`
- `state/aggregation.json`

## Process

1. **Analyze content**
   - Study aggregation.json
   - Identify key elements for each format
   - Select data for visualization

2. **Generate PDF**
   - Executive summary on first page
   - Table of contents
   - Sections by scope items
   - Inline charts and tables
   - Highlighted recommendations
   - Sources at the end

3. **Generate Excel**
   - Summary sheet with key metrics
   - Data sheets by category
   - Raw data for own analysis
   - Formulas for dynamic calculations

4. **Generate PPTX** (if requested)
   - Title slide
   - Executive summary (1 slide)
   - Key findings (2-3 slides)
   - Recommendations (1 slide)
   - Appendix with data

## Output

Save reports to `output/`:
- `output/report.pdf`
- `output/report.xlsx`
- `output/report.pptx` (optional)

Save metadata to `state/report_config.json`:
```json
{
  "session_id": "string",
  "generated_at": "ISO datetime",
  "language": "en|ru",
  "generated_reports": [
    {
      "format": "pdf",
      "filename": "report.pdf",
      "file_path": "output/report.pdf",
      "structure": {
        "total_pages": 12,
        "sections": ["Executive Summary", "Financial Health", "..."],
        "charts_count": 5,
        "tables_count": 3
      }
    },
    {
      "format": "excel",
      "filename": "report.xlsx",
      "file_path": "output/report.xlsx",
      "structure": {
        "sheets": ["Summary", "Financials", "Comparison", "Raw Data"],
        "charts_count": 3
      }
    }
  ]
}
```

## Update session.json

```json
{
  "phase": "complete",
  "updated_at": "ISO"
}
```

## Signal Completion

After saving reports, output:
```
<promise>COMPLETE</promise>
```

## Rules
- Language = Brief language
- Unified visual style
- Charts > text where possible
- Key numbers highlighted
- Sources cited
