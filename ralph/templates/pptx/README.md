# PowerPoint Report Templates

This directory contains configuration for PowerPoint presentation generation.

## Slide Structure

The FileGenerator creates presentations with the following slides:

### 1. Title Slide
- Research title (goal from Brief)
- Generation date
- Optional company branding

### 2. Executive Summary Slide
- Full executive summary text
- Key takeaway bullet points

### 3. Key Insights Slides (1-2 slides)
- 4 insights per slide maximum
- Bullet point format
- Supporting data as sub-bullets

### 4. Section Slides (variable)
- One slide per scope item (configurable)
- Summary text
- Top 5 key points as bullets
- Data highlights if applicable

### 5. Recommendation Slide
- Verdict prominently displayed
- Confidence level
- Brief reasoning
- Key pros and cons

### 6. Thank You Slide
- Closing slide
- "Questions?" prompt

## Configuration

PowerPoint generation is configured via `PPTXConfig`:

```python
{
    "pptx": {
        "template": null,  # Use default layout
        "slides_per_section": 2,
        "include_speaker_notes": true,
        "aspect_ratio": "16:9"  # or "4:3"
    }
}
```

## Aspect Ratios

Supported aspect ratios:
- **16:9** (default): Modern widescreen format (13.333" x 7.5")
- **4:3**: Traditional format (10" x 7.5")

## Styling

The generator uses PowerPoint's built-in layouts:
- Layout 0: Title slide
- Layout 1: Title and content

Colors follow the primary_color from branding config when possible.

## Note

PowerPoint templates are generated programmatically using python-pptx.
The structure is defined in `src/tools/file_generator.py`.

For custom branded templates, you can provide a base PPTX file
via the `template` config option (future enhancement).
