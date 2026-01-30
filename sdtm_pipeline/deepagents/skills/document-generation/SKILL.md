---
name: document-generation
description: This skill enables the agent to generate professional downloadable documents directly from conversation context.
---

# Document Generation Skill

## Overview

This skill enables the agent to generate professional downloadable documents
directly from conversation context. It supports nine file formats:

| Format | Tool | Library | Use Case |
|--------|------|---------|----------|
| PowerPoint (.pptx) | `generate_presentation` | python-pptx | Slide decks, reports, summaries |
| Excel (.xlsx) | `generate_excel` | openpyxl | Data tables, multi-sheet workbooks |
| Word (.docx) | `generate_word_document` | python-docx | Reports, protocols, documentation |
| CSV (.csv) | `generate_csv_file` | pandas | Raw data export, simple tables |
| PDF (.pdf) | `generate_pdf` | fpdf2 | Printable reports, formal documents |
| Markdown (.md) | `generate_markdown_file` | built-in | Technical docs, README files |
| Text (.txt) | `generate_text_file` | built-in | Plain text exports, logs |
| R Script (.r) | `generate_r_script` | built-in | Statistical analysis, data manipulation |
| SAS Program (.sas) | `generate_sas_program` | built-in | Clinical data processing, SDTM/ADaM |

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

### R Scripts
- "Generate an R script for the statistical analysis"
- "Create R code for the data visualization"
- "Export the analysis as an R file"
- "Write R code for the ADaM derivations"

### SAS Programs
- "Generate a SAS program for the SDTM mapping"
- "Create SAS code for the domain transformation"
- "Export the ETL logic as a SAS file"
- "Write SAS code for the define.xml generation"

## Tool Usage Patterns

### Generating a Presentation
````python
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
````

### Generating an Excel File
````python
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
````

### Generating a Word Document
````python
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
````

### Generating a CSV File
````python
generate_csv_file(
    title="validation_results",
    headers=["Rule ID", "Domain", "Severity", "Message"],
    rows=[
        ["SD0001", "DM", "Error", "Missing STUDYID"],
        ["SD0045", "AE", "Warning", "AEDECOD not in MedDRA"]
    ]
)
````

### Generating a PDF Document
````python
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
````

### Generating a Markdown File
````python
generate_markdown_file(
    title="Analysis Results",
    content="## Key Findings\n\n- 48 source files processed\n- 8 SDTM domains mapped\n\n## Recommendations\n\n1. Review unmapped files\n2. Run full validation"
)
````

### Generating a Text File
````python
generate_text_file(
    title="Processing Log",
    content="Processed DM domain: 100 records\nProcessed AE domain: 450 records\nAll domains complete."
)
````

### Generating an R Script
````python
generate_r_script(
    title="dm_analysis",
    description="Demographics analysis for Study XYZ-001",
    code='''
# Demographics Analysis Script
# Study: XYZ-001
# Author: Generated by Clinical Trial Agent
# Date: 2025-01-30

library(tidyverse)
library(haven)

# Load SDTM DM domain
dm <- read_xpt("sdtm/dm.xpt")

# Summary statistics
dm_summary <- dm %>%
  group_by(SEX, RACE) %>%
  summarise(
    n = n(),
    mean_age = mean(AGE, na.rm = TRUE),
    sd_age = sd(AGE, na.rm = TRUE),
    .groups = "drop"
  )

# Age distribution visualization
ggplot(dm, aes(x = AGE, fill = SEX)) +
  geom_histogram(binwidth = 5, alpha = 0.7, position = "dodge") +
  labs(title = "Age Distribution by Sex",
       x = "Age (years)",
       y = "Count") +
  theme_minimal()

# Export summary
write_csv(dm_summary, "output/dm_summary.csv")
''',
    packages=["tidyverse", "haven"]  # Optional: list required packages
)
````

### Generating a SAS Program
````python
generate_sas_program(
    title="dm_sdtm",
    description="SDTM DM domain creation for Study XYZ-001",
    code='''
/*****************************************************************************
* Program:    dm_sdtm.sas
* Study:      XYZ-001
* Purpose:    Create SDTM DM (Demographics) domain
* Author:     Generated by Clinical Trial Agent
* Date:       2025-01-30
*****************************************************************************/

%let studyid = XYZ-001;
%let domain = DM;

libname raw "data/raw";
libname sdtm "data/sdtm";

/* Import source demographics data */
proc import datafile="data/source/demographics.csv"
    out=work.source_dm
    dbms=csv replace;
    guessingrows=max;
run;

/* Create SDTM DM domain */
data sdtm.dm(label="Demographics");
    attrib
        STUDYID  length=$20  label="Study Identifier"
        DOMAIN   length=$2   label="Domain Abbreviation"
        USUBJID  length=$40  label="Unique Subject Identifier"
        SUBJID   length=$20  label="Subject Identifier for the Study"
        RFSTDTC  length=$20  label="Subject Reference Start Date/Time"
        RFENDTC  length=$20  label="Subject Reference End Date/Time"
        SITEID   length=$10  label="Study Site Identifier"
        BRTHDTC  length=$20  label="Date/Time of Birth"
        AGE      length=8    label="Age"
        AGEU     length=$10  label="Age Units"
        SEX      length=$2   label="Sex"
        RACE     length=$50  label="Race"
        ETHNIC   length=$50  label="Ethnicity"
        ARMCD    length=$20  label="Planned Arm Code"
        ARM      length=$200 label="Description of Planned Arm"
        COUNTRY  length=$3   label="Country"
    ;
    
    set work.source_dm;
    
    STUDYID = "&studyid";
    DOMAIN = "&domain";
    USUBJID = catx("-", STUDYID, SUBJID);
    AGEU = "YEARS";
    
    /* Apply controlled terminology mappings */
    if upcase(sex_raw) = "MALE" then SEX = "M";
    else if upcase(sex_raw) = "FEMALE" then SEX = "F";
    else SEX = "U";
    
run;

/* Validation checks */
proc freq data=sdtm.dm;
    tables SEX RACE ETHNIC ARM / missing;
    title "DM Domain - Frequency Distributions";
run;

proc means data=sdtm.dm n mean std min max;
    var AGE;
    title "DM Domain - Age Statistics";
run;

/* Export to XPT */
proc cport library=sdtm file="data/sdtm/dm.xpt" memtype=data;
    select dm;
run;

%put NOTE: DM domain creation complete;
''',
    macros=[]  # Optional: list any macro dependencies
)
````

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

### Code File Response Examples

For R scripts:
````markdown
I've generated the R analysis script:
```generated-file
{"filename": "dm_analysis.r", "file_type": "r", "size_bytes": 1245, "description": "R script for demographics analysis with tidyverse", "download_url": "/download/dm_analysis.r"}
```

The script includes data loading, summary statistics, and visualization code...
````

For SAS programs:
````markdown
I've generated the SAS program:
```generated-file
{"filename": "dm_sdtm.sas", "file_type": "sas", "size_bytes": 3567, "description": "SAS program for SDTM DM domain creation", "download_url": "/download/dm_sdtm.sas"}
```

The program creates a compliant DM domain with proper attributes and controlled terminology...
````

## CRITICAL Instructions for Agent

1. **ALWAYS** use the `generated-file` code block format when reporting generated files
2. **ALWAYS** include a meaningful description of the generated content
3. **Generate rich content** - don't create empty or placeholder documents
4. **Use proper structure** - presentations should have multiple slides, Excel should have formatted headers
5. **Match the request** - if user asks for a presentation, use `generate_presentation`, not Word
6. **Offer alternatives** - after generating, offer to export in a different format too
7. **For code files** - include proper headers, comments, and follow language-specific conventions
8. **SAS programs** - follow CDISC/SDTM naming conventions and include proper ATTRIB statements
9. **R scripts** - include library() calls and follow tidyverse style guide where appropriate
10. **Clinical context** - when generating code for clinical trials, ensure CDISC compliance
