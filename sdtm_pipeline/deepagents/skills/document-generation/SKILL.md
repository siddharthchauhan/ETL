---
name: document-generation
description: Enables generating professional downloadable documents directly from conversation context.
---

# Document Generation Skill

## Overview

This skill enables the agent to generate professional downloadable documents
directly from conversation context. It supports seven file formats:

| Format | Tool | Library | Use Case |
|--------|------|---------|----------|
| PowerPoint (.pptx) | `generate_presentation` | python-pptx | Slide decks, reports, summaries |
| Excel (.xlsx) | `generate_excel` | openpyxl | Data tables, multi-sheet workbooks |
| Word (.docx) | `generate_word_document` | python-docx | Reports, protocols, documentation |
| CSV (.csv) | `generate_csv_file` | pandas | Raw data export, simple tables |
| PDF (.pdf) | `generate_pdf` | fpdf2 | Printable reports, formal documents |
| Markdown (.md) | `generate_markdown_file` | built-in | Technical docs, README files |
| Text (.txt) | `generate_text_file` | built-in | Plain text exports, logs |

## When to Use

### Presentations
- "Create a presentation about the SDTM conversion results"
- "Make slides summarizing the validation report"
- "Generate a PowerPoint for the clinical study review"

### Excel/Spreadsheets
- "Export the domain mapping as an Excel file"
- "Create a spreadsheet with the validation results"
- "Generate an Excel workbook with all domain summaries"

### Word Documents
- "Create a Word document with the transformation report"
- "Generate a document summarizing the pipeline results"
- "Write a report and export it as a Word file"

### CSV Files
- "Export the data as CSV"
- "Create a CSV file with the mapping specifications"
- "Download the results as a comma-separated file"

### PDF Documents
- "Create a PDF report of the validation results"
- "Generate a printable PDF summary"
- "Export the analysis as PDF"

### Markdown Files
- "Create a markdown document with the results"
- "Generate a README for this analysis"
- "Export as markdown"

### Text Files
- "Export the log as a text file"
- "Create a plain text summary"
- "Save the output to a text file"

## Tool Usage Patterns

### Generating a Presentation

```python
generate_presentation(
    title="SDTM Conversion Summary",
    subtitle="Study XYZ-001",
    slides=[
        {
            "title": "Overview",
            "content": "This presentation covers the SDTM conversion results...",
            "layout": "content"  # Options: title, content, two_column, blank
        },
        {
            "title": "Domain Results",
            "content": "- DM: 100 subjects converted\n- AE: 450 events mapped\n- VS: 2,300 records",
            "layout": "content"
        },
        {
            "title": "Validation Summary",
            "content": "All domains passed Pinnacle 21 validation with 0 errors.",
            "layout": "content"
        }
    ]
)
```

### Generating an Excel File

```python
generate_excel(
    title="Domain_Mapping_Report",
    sheets=[
        {
            "name": "DM Mapping",
            "headers": ["Source Column", "SDTM Variable", "Transformation", "Notes"],
            "rows": [
                ["SUBJID", "USUBJID", "CONCAT(STUDYID, '-', SUBJID)", "Derived"],
                ["SEX", "SEX", "MAP(M->M, F->F)", "Direct mapping"]
            ]
        },
        {
            "name": "Summary",
            "headers": ["Domain", "Records", "Status"],
            "rows": [
                ["DM", "100", "Complete"],
                ["AE", "450", "Complete"]
            ]
        }
    ]
)
```

### Generating a Word Document

```python
generate_word_document(
    title="SDTM Transformation Report",
    sections=[
        {
            "heading": "Executive Summary",
            "content": "This report details the SDTM transformation results for Study XYZ-001..."
        },
        {
            "heading": "Domain Results",
            "content": "The following domains were successfully converted...",
            "level": 2
        }
    ]
)
```

### Generating a CSV File

```python
generate_csv_file(
    title="validation_results",
    headers=["Rule ID", "Domain", "Severity", "Message"],
    rows=[
        ["SD0001", "DM", "Error", "Missing STUDYID"],
        ["SD0045", "AE", "Warning", "AEDECOD not in MedDRA"]
    ]
)
```

### Generating a PDF Document

```python
generate_pdf(
    title="Validation Report",
    sections=[
        {
            "heading": "Summary",
            "content": "All 8 domains passed validation with 0 critical errors.",
            "level": 1
        },
        {
            "heading": "Details",
            "content": "- DM: 100 subjects, 0 errors\n- AE: 450 events, 2 warnings",
            "level": 2
        }
    ]
)
```

### Generating a Markdown File

```python
generate_markdown_file(
    title="Analysis Results",
    content="## Key Findings\n\n- 48 source files processed\n- 8 SDTM domains mapped\n\n## Recommendations\n\n1. Review unmapped files\n2. Run full validation"
)
```

### Generating a Text File

```python
generate_text_file(
    title="Processing Log",
    content="Processed DM domain: 100 records\nProcessed AE domain: 450 records\nAll domains complete."
)
```

## Response Format

After generating a file, the tool returns metadata. The agent MUST include this
metadata in its response using the `generated-file` code block format so the
frontend can render a download card:

````markdown
I've generated the presentation for you:

```generated-file
{"filename": "SDTM_Conversion_Summary.pptx", "file_type": "pptx", "size_bytes": 245678, "description": "10-slide presentation covering SDTM conversion results", "download_url": "/download/SDTM_Conversion_Summary.pptx"}
```

The presentation includes 10 slides covering...
````

## CRITICAL Instructions for Agent

1. **ALWAYS** use the `generated-file` code block format when reporting generated files
2. **ALWAYS** include a meaningful description of the generated content
3. **Generate rich content** - don't create empty or placeholder documents
4. **Use proper structure** - presentations should have multiple slides, Excel should have formatted headers
5. **Match the request** - if user asks for a presentation, use `generate_presentation`, not Word
6. **Offer alternatives** - after generating, offer to export in a different format too
