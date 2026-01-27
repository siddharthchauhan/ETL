#!/bin/bash
cd /Users/siddharth/Downloads/ETL/ETL/sdtm_workspace
python3 validate_dm_comprehensive.py > DM_VALIDATION_REPORT.txt 2>&1
echo "Validation report generated: DM_VALIDATION_REPORT.txt"
