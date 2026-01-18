# Excel Report Templates

This directory contains configuration for Excel report generation.

## Sheet Structure

The FileGenerator creates Excel workbooks with the following sheets:

### 1. Summary Sheet
- Research title and metadata
- Executive summary
- Key metrics overview
- Processing statistics (rounds, tasks, sources)

### 2. Key Insights Sheet
- Numbered list of insights
- Supporting data references
- Importance ratings

### 3. Section Sheets (one per scope item)
- Section title and summary
- Key points list
- Data highlights (metric cards)
- Sentiment indicator

### 4. Data Tables Sheet
- All data tables from sections
- Properly formatted headers
- Alternating row colors

### 5. Raw Data Sheet (optional)
- Full JSON dump of aggregated research
- Enabled via `include_raw_data: true` in config

## Styling

The generator applies consistent styling:
- Header row: Navy blue background (#1a365d), white text, bold
- Borders: Thin borders around all cells
- Column widths: Auto-sized based on content type
- Number formatting: Appropriate for each data type

## Configuration

Excel generation is configured via `ExcelConfig` in the report config:

```python
{
    "excel": {
        "sheets": ["summary", "insights", "sections", "data"],
        "include_raw_data": false,
        "include_charts": true
    }
}
```

## Note

Excel templates are generated programmatically using openpyxl.
Unlike PDF templates, there is no external template file - the structure
is defined in `src/tools/file_generator.py`.
