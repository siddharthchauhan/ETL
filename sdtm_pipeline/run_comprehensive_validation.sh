#!/bin/bash
################################################################################
# MAXIS-08 Comprehensive Raw Data Validation - Execution Script
################################################################################
#
# Purpose: Execute complete raw source data validation before SDTM transformation
#
# Prerequisites:
#   - Python 3.8+ with pandas, numpy installed
#   - Source data files available (extracted from S3)
#   - Sufficient disk space for results (~ 50MB)
#
# Usage:
#   ./run_comprehensive_validation.sh
#
# Or with custom data path:
#   ./run_comprehensive_validation.sh /path/to/data
#
# Author: SDTM Pipeline - Validation Agent
# Date: 2025-02-02
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
STUDY_ID="MAXIS-08"
DEFAULT_DATA_PATH="/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV"
OUTPUT_DIR="./validation_results"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Use provided data path or default
DATA_PATH="${1:-$DEFAULT_DATA_PATH}"

################################################################################
# Functions
################################################################################

print_header() {
    echo -e "${BLUE}"
    echo "================================================================================"
    echo "$1"
    echo "================================================================================"
    echo -e "${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

check_prerequisites() {
    print_header "CHECKING PREREQUISITES"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
    print_success "Python 3 found: $(python3 --version)"
    
    # Check required Python packages
    print_info "Checking Python packages..."
    python3 -c "import pandas; import numpy" 2>/dev/null
    if [ $? -eq 0 ]; then
        print_success "Required Python packages installed"
    else
        print_error "Missing required packages. Install with: pip install pandas numpy"
        exit 1
    fi
    
    # Check data path
    if [ ! -d "$DATA_PATH" ]; then
        print_warning "Data path not found: $DATA_PATH"
        print_info "You may need to download data from S3 first:"
        echo ""
        echo "  aws s3 cp s3://s3dcri/Clinical_Studies/MAXIS-08/RAW_DATA/Maxis-08\ RAW\ DATA.zip /tmp/"
        echo "  unzip '/tmp/Maxis-08 RAW DATA.zip' -d /tmp/s3_data/extracted/"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "Data path found: $DATA_PATH"
        FILE_COUNT=$(ls -1 "$DATA_PATH"/*.csv 2>/dev/null | wc -l)
        print_info "Found $FILE_COUNT CSV files"
    fi
    
    # Create output directory
    mkdir -p "$OUTPUT_DIR"
    print_success "Output directory: $OUTPUT_DIR"
    
    echo ""
}

run_structural_validation() {
    print_header "PHASE 1: STRUCTURAL VALIDATION"
    
    OUTPUT_FILE="$OUTPUT_DIR/structural_validation_${TIMESTAMP}.json"
    
    print_info "Running structural validation..."
    print_info "This checks: file structure, required columns, data types, duplicates"
    echo ""
    
    python3 raw_data_validation.py \
        --data-path "$DATA_PATH" \
        --study-id "$STUDY_ID" \
        --output "$OUTPUT_FILE"
    
    if [ $? -eq 0 ]; then
        print_success "Structural validation completed"
        print_info "Results saved to: $OUTPUT_FILE"
    else
        print_error "Structural validation failed"
        return 1
    fi
    
    echo ""
}

run_enhanced_validation() {
    print_header "PHASE 2: BUSINESS RULES & CROSS-DOMAIN VALIDATION"
    
    OUTPUT_FILE="$OUTPUT_DIR/enhanced_validation_${TIMESTAMP}.json"
    
    print_info "Running enhanced validation with business rules..."
    print_info "This checks: business rules, CT preview, cross-domain consistency"
    echo ""
    
    python3 enhanced_raw_data_validation.py \
        --data-path "$DATA_PATH" \
        --study-id "$STUDY_ID" \
        --output "$OUTPUT_FILE"
    
    if [ $? -eq 0 ]; then
        print_success "Enhanced validation completed"
        print_info "Results saved to: $OUTPUT_FILE"
    else
        print_warning "Enhanced validation completed with findings"
        print_info "Results saved to: $OUTPUT_FILE"
    fi
    
    echo ""
}

generate_summary_report() {
    print_header "PHASE 3: GENERATING SUMMARY REPORT"
    
    print_info "Consolidating validation results..."
    
    # Find the latest result files
    STRUCTURAL_FILE=$(ls -t $OUTPUT_DIR/structural_validation_*.json 2>/dev/null | head -1)
    ENHANCED_FILE=$(ls -t $OUTPUT_DIR/enhanced_validation_*.json 2>/dev/null | head -1)
    
    if [ -n "$STRUCTURAL_FILE" ] && [ -n "$ENHANCED_FILE" ]; then
        print_success "Found validation results:"
        print_info "  Structural: $STRUCTURAL_FILE"
        print_info "  Enhanced:   $ENHANCED_FILE"
        
        # Extract key metrics using Python
        python3 << EOF
import json
import sys

try:
    with open('$ENHANCED_FILE', 'r') as f:
        results = json.load(f)
    
    print("\n" + "="*80)
    print("VALIDATION SUMMARY - $STUDY_ID")
    print("="*80)
    print(f"\nFiles Validated: {results.get('files_validated', 0)}")
    print(f"Total Records: {results.get('total_records', 0):,}")
    print(f"Quality Score: {results.get('overall_quality_score', 0):.1f}/100")
    print("\nIssues by Severity:")
    print(f"  Critical Errors:  {results.get('critical_errors', 0):3d}  ❌ MUST FIX")
    print(f"  Errors:           {results.get('errors', 0):3d}  ⚠️  SHOULD FIX")
    print(f"  Warnings:         {results.get('warnings', 0):3d}  ⚠️  REVIEW")
    print(f"  Info:             {results.get('info', 0):3d}  ℹ️  INFORMATIONAL")
    print("\nTransformation Readiness:")
    print(f"  {results.get('transformation_readiness', 'UNKNOWN')}")
    print("\n" + "="*80 + "\n")
    
except Exception as e:
    print(f"Error reading results: {e}", file=sys.stderr)
    sys.exit(1)
EOF
        
    else
        print_warning "Validation result files not found"
    fi
    
    echo ""
}

show_next_steps() {
    print_header "NEXT STEPS"
    
    cat << EOF
Based on the validation results:

1. ✅ REVIEW VALIDATION RESULTS
   - Open: $OUTPUT_DIR/enhanced_validation_${TIMESTAMP}.json
   - Review all CRITICAL and ERROR findings
   - Document findings in validation package

2. 🔧 ADDRESS CRITICAL BLOCKERS (if any)
   - Query sites for missing required data
   - Correct data entry errors
   - Remove duplicate records
   - Re-run validation after corrections

3. 📋 DOCUMENT QUALITY ISSUES
   - Create data quality report for sponsor
   - Document known issues in SDRG
   - Obtain medical review for clinical outliers

4. ✅ PROCEED TO SDTM TRANSFORMATION (if ready)
   - Begin mapping specification development
   - Execute SDTM transformation
   - Perform post-transformation validation

5. 📊 GENERATE REPORTS
   - Review comprehensive validation report:
     MAXIS-08_COMPREHENSIVE_RAW_DATA_VALIDATION_REPORT.md

For detailed validation framework and business rules, see:
  - MAXIS-08_COMPREHENSIVE_RAW_DATA_VALIDATION_REPORT.md
  - RAW_DATA_VALIDATION_GUIDE.md
  - RAW_DATA_VALIDATION_INDEX.md

EOF
}

################################################################################
# Main Execution
################################################################################

main() {
    print_header "MAXIS-08 COMPREHENSIVE RAW DATA VALIDATION"
    
    echo "Study ID: $STUDY_ID"
    echo "Data Path: $DATA_PATH"
    echo "Output Directory: $OUTPUT_DIR"
    echo "Timestamp: $TIMESTAMP"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Run validations
    run_structural_validation
    
    run_enhanced_validation
    
    # Generate summary
    generate_summary_report
    
    # Show next steps
    show_next_steps
    
    print_header "VALIDATION COMPLETE"
    print_success "All validation phases completed successfully!"
    print_info "Review results in: $OUTPUT_DIR"
    echo ""
}

# Execute main function
main "$@"
