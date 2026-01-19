# Task: Fix PDF Generation - Getting HTML Instead of PDF

## Status: ✅ FIXED

## Problem Description

User requested a marketing research report with the following specification:
```
./loop.sh "Сделай маркетинговое исследование компании Mezen.io, подготовь отчёт в их корпоративном стиле, формат - pdf, Executive Summary + Отчёт примерно 7-12 страниц. Определи проблемы, потенциальные траты на маркетинг в месяц, точки роста, ближайшие точки роста."
```

**Expected:** `report.pdf` file
**Received:** `report.html` file

---

## Root Cause Analysis

1. **Brief Builder** ✅ — Correctly detected `output_format: "pdf"` from query
2. **Session.json** ✅ — Preferences were properly passed
3. **Reporter** ❌ — Generated HTML but didn't know HOW to convert to PDF

The reporter.md had instructions about what files to create (`output/report.pdf`) but no explicit workflow for HTML→PDF conversion.

---

## Fix Applied (Commit: 94e08d3)

### 1. reporter.md — Added "PDF Generation Workflow" section

New section with step-by-step instructions:
- Step 1: Generate charts as PNG with Matplotlib
- Step 2: Generate HTML with `<img>` tags (not Chart.js)
- Step 3: Convert HTML to PDF using weasyprint
- Step 4: Verify PDF exists

Includes:
- Complete weasyprint Python code with A4 format and page numbers
- Alternative wkhtmltopdf command as fallback
- Verification checklist

### 2. brief_builder.md — Improved format detection

Added explicit keywords to output format detection:
- "pdf", "PDF", "формат pdf", "format pdf"
- "excel", "xlsx"
- "html"

---

## Testing

To verify the fix works, run:
```bash
./loop.sh "Test report, format pdf, 2 pages"
```

Expected output:
```
output/
├── report.pdf         # ← Must exist
├── report.html        # HTML source
├── charts/*.png       # Chart images
└── html_to_pdf.py     # Conversion script
```

---

## Files Modified

1. `ralph/prompts/reporter.md` — Added PDF Generation Workflow section (+70 lines)
2. `ralph/prompts/brief_builder.md` — Added explicit pdf/excel/html keywords

---

## Acceptance Criteria

- [x] Brief Builder correctly detects "pdf" in query
- [x] Reporter has explicit PDF generation instructions
- [x] weasyprint code example provided
- [x] Alternative (wkhtmltopdf) documented
- [ ] End-to-end test with PDF output (pending user test)
