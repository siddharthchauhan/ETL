#!/bin/bash
#
# MAXIS-08 Raw Data Validation Execution Script
# ==============================================
# 
# This script runs comprehensive raw data validation on all MAXIS-08 source files
# before SDTM transformation.
#
# Author: SDTM Pipeline - Validation Agent
# Date: 2025-02-02
# Study: MAXIS-08

set -e  # Exit on error

echo ""
echo "================================================================================"
echo "MAXIS-08 RAW DATA VALIDATION"
echo "================================================================================"
echo ""
echo "This script will validate all source data files for:"
echo "  • Required identifiers (STUDY, INVSITE, PT)"
echo "  • Date format consistency"
echo "  • Duplicate records"
echo "  • Missing critical data elements"
echo "  • Overall data quality"
echo ""
echo "================================================================================"
echo ""

# Configuration
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DATA_PATH="${DATA_PATH:-/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV}"
STUDY_ID="${STUDY_ID:-MAXIS-08}"
OUTPUT_DIR="${OUTPUT_DIR:-$SCRIPT_DIR}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Output files
REPORT_FILE="$OUTPUT_DIR/MAXIS-08_RAW_DATA_VALIDATION_REPORT.md"
JSON_FILE="$OUTPUT_DIR/MAXIS-08_RAW_DATA_VALIDATION_RESULTS_${TIMESTAMP}.json"
LOG_FILE="$OUTPUT_DIR/raw_data_validation_${TIMESTAMP}.log"

echo "Configuration:"
echo "  Data Path: $DATA_PATH"
echo "  Study ID: $STUDY_ID"
echo "  Report Output: $REPORT_FILE"
echo "  JSON Output: $JSON_FILE"
echo "  Log File: $LOG_FILE"
echo ""

# Check if data path exists
if [ ! -d "$DATA_PATH" ]; then
    echo "❌ ERROR: Data path does not exist: $DATA_PATH"
    echo ""
    echo "Please ensure data has been loaded from S3 or specify correct path:"
    echo "  export DATA_PATH=/path/to/your/data"
    echo "  ./run_raw_data_validation.sh"
    echo ""
    echo "Expected data structure:"
    echo "  $DATA_PATH/"
    echo "    ├── DEMO.csv"
    echo "    ├── AEVENT.csv"
    echo "    ├── AEVENTC.csv"
    echo "    ├── CONMEDS.csv"
    echo "    ├── CONMEDSC.csv"
    echo "    ├── VITALS.csv"
    echo "    ├── HEMLAB.csv"
    echo "    ├── CHEMLAB.csv"
    echo "    ├── DOSE.csv"
    echo "    ├── ECG.csv"
    echo "    └── PHYSEXAM.csv"
    echo ""
    exit 1
fi

echo "✅ Data path exists: $DATA_PATH"
echo ""

# Check Python environment
if ! command -v python3 &> /dev/null; then
    echo "❌ ERROR: python3 not found. Please install Python 3.8+"
    exit 1
fi

echo "Python version:"
python3 --version
echo ""

# Check required packages
echo "Checking required Python packages..."
python3 -c "import pandas, numpy" 2>/dev/null || {
    echo "❌ ERROR: Required packages not found (pandas, numpy)"
    echo "Please install: pip install pandas numpy"
    exit 1
}
echo "✅ Required packages found"
echo ""

echo "================================================================================"
echo "STARTING VALIDATION"
echo "================================================================================"
echo ""

# Run validation
python3 "$SCRIPT_DIR/raw_data_validation.py" \
    --data-path "$DATA_PATH" \
    --study-id "$STUDY_ID" \
    --output "$REPORT_FILE" \
    --json-output "$JSON_FILE" \
    2>&1 | tee "$LOG_FILE"

EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "================================================================================"
echo "VALIDATION COMPLETE"
echo "================================================================================"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ SUCCESS: Validation completed without critical errors"
    echo ""
    echo "📄 Generated Files:"
    echo "  • Validation Report: $REPORT_FILE"
    echo "  • JSON Results: $JSON_FILE"
    echo "  • Execution Log: $LOG_FILE"
    echo ""
    echo "Next Steps:"
    echo "  1. Review the validation report: $REPORT_FILE"
    echo "  2. Address any warnings before SDTM transformation"
    echo "  3. Proceed with Phase 3: Mapping Specification"
    echo ""
else
    echo "❌ FAILURE: Critical errors found"
    echo ""
    echo "📄 Generated Files:"
    echo "  • Validation Report: $REPORT_FILE"
    echo "  • JSON Results: $JSON_FILE"
    echo "  • Execution Log: $LOG_FILE"
    echo ""
    echo "Required Actions:"
    echo "  1. Review critical errors in: $REPORT_FILE"
    echo "  2. Fix data quality issues in source files"
    echo "  3. Re-run validation after fixes"
    echo "  4. DO NOT proceed with SDTM transformation until errors are resolved"
    echo ""
fi

echo "================================================================================"

exit $EXIT_CODE
