#!/usr/bin/env python3
"""
Comprehensive Source Data Profiling Script
Profiles all 48 CSV files in the SDTM workspace source_data directory
"""

import pandas as pd
import numpy as np
import json
import os
from pathlib import Path
from datetime import datetime
import re

def infer_dtype(series):
    """
    Infer the data type of a pandas Series.
    Returns: 'integer', 'float', 'date', 'boolean', 'string'
    """
    # Drop nulls for type inference
    non_null = series.dropna()
    
    if len(non_null) == 0:
        return 'string'  # Default for empty columns
    
    # Check if boolean
    unique_vals = non_null.unique()
    if len(unique_vals) <= 2:
        # Check for common boolean patterns
        str_vals = set([str(v).upper() for v in unique_vals])
        bool_patterns = [
            {'Y', 'N'}, {'YES', 'NO'}, {'TRUE', 'FALSE'}, 
            {'T', 'F'}, {'1', '0'}, {1, 0}, {True, False}
        ]
        if any(str_vals <= pattern or set(unique_vals) <= pattern for pattern in bool_patterns):
            return 'boolean'
    
    # Check numeric types
    if pd.api.types.is_integer_dtype(series):
        return 'integer'
    
    if pd.api.types.is_float_dtype(series):
        return 'float'
    
    # Check for date patterns in strings
    if pd.api.types.is_object_dtype(series):
        # Sample some values to check for dates
        sample = non_null.head(100)
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY or DD/MM/YYYY
            r'^\d{2}-[A-Z]{3}-\d{4}',  # DD-MON-YYYY
        ]
        
        date_matches = 0
        for val in sample:
            val_str = str(val)
            for pattern in date_patterns:
                if re.match(pattern, val_str):
                    date_matches += 1
                    break
        
        if date_matches / len(sample) > 0.5:  # If >50% match date patterns
            return 'date'
    
    return 'string'

def get_sample_values(series, n=5):
    """
    Get first n unique non-null sample values from a series.
    """
    non_null = series.dropna()
    if len(non_null) == 0:
        return []
    
    unique_vals = non_null.unique()[:n]
    
    # Convert to native Python types for JSON serialization
    samples = []
    for val in unique_vals:
        if pd.isna(val):
            continue
        if isinstance(val, (np.integer, np.floating)):
            samples.append(float(val) if isinstance(val, np.floating) else int(val))
        elif isinstance(val, (np.bool_)):
            samples.append(bool(val))
        else:
            samples.append(str(val))
    
    return samples

def profile_csv_file(file_path):
    """
    Profile a single CSV file and return detailed metadata.
    """
    try:
        # Read CSV
        df = pd.read_csv(file_path, low_memory=False)
        
        # Basic file info
        row_count = len(df)
        column_count = len(df.columns)
        
        # Profile each column
        columns_profile = []
        
        for col in df.columns:
            series = df[col]
            
            # Calculate statistics
            non_null_count = series.notna().sum()
            null_count = series.isna().sum()
            null_pct = round((null_count / row_count) * 100, 2) if row_count > 0 else 0.0
            unique_count = series.nunique()
            
            # Infer data type
            dtype = infer_dtype(series)
            
            # Get sample values
            sample_values = get_sample_values(series, n=5)
            
            col_profile = {
                "name": col,
                "dtype": dtype,
                "non_null": int(non_null_count),
                "null_count": int(null_count),
                "null_pct": float(null_pct),
                "unique_count": int(unique_count),
                "sample_values": sample_values
            }
            
            columns_profile.append(col_profile)
        
        file_profile = {
            "row_count": int(row_count),
            "column_count": int(column_count),
            "columns": columns_profile
        }
        
        return file_profile, None
        
    except Exception as e:
        return None, str(e)

def profile_all_files(source_dir):
    """
    Profile all CSV files in the source directory.
    """
    source_path = Path(source_dir)
    csv_files = list(source_path.glob("**/*.csv"))
    
    print(f"Found {len(csv_files)} CSV files to profile")
    print("="*80)
    
    all_profiles = {}
    errors = {}
    
    for idx, csv_file in enumerate(csv_files, 1):
        filename = csv_file.name
        print(f"[{idx}/{len(csv_files)}] Profiling: {filename}...", end=" ")
        
        profile, error = profile_csv_file(csv_file)
        
        if error:
            print(f"ERROR: {error}")
            errors[filename] = error
        else:
            print(f"✓ ({profile['row_count']} rows, {profile['column_count']} columns)")
            all_profiles[filename] = profile
    
    print("="*80)
    print(f"Successfully profiled: {len(all_profiles)} files")
    if errors:
        print(f"Errors encountered: {len(errors)} files")
    
    return all_profiles, errors

def main():
    """Main execution function."""
    source_dir = "./sdtm_workspace/source_data/Maxis-08 RAW DATA_CSV"
    output_file = "./sdtm_workspace/source_data_profile.json"
    
    print("="*80)
    print("SOURCE DATA PROFILING")
    print("="*80)
    print(f"Source Directory: {source_dir}")
    print(f"Output File: {output_file}")
    print()
    
    # Profile all files
    profiles, errors = profile_all_files(source_dir)
    
    # Create output structure
    output = {
        "metadata": {
            "profile_date": datetime.now().isoformat(),
            "total_files": len(profiles),
            "source_directory": source_dir,
            "errors": errors if errors else {}
        },
        "profiles": profiles
    }
    
    # Save to JSON
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print()
    print(f"Profile saved to: {output_file}")
    print()
    
    # Print summary statistics
    print("="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    total_rows = sum(p['row_count'] for p in profiles.values())
    total_columns = sum(p['column_count'] for p in profiles.values())
    
    print(f"Total Files: {len(profiles)}")
    print(f"Total Rows: {total_rows:,}")
    print(f"Total Columns: {total_columns:,}")
    print()
    
    # Top 10 files by row count
    print("Top 10 Files by Row Count:")
    sorted_by_rows = sorted(profiles.items(), key=lambda x: x[1]['row_count'], reverse=True)[:10]
    for filename, profile in sorted_by_rows:
        print(f"  {filename:30s} - {profile['row_count']:6,} rows, {profile['column_count']:3} columns")
    
    print("="*80)
    
    return output

if __name__ == "__main__":
    result = main()
    
    # Also print the JSON output for immediate viewing
    print("\n\nJSON OUTPUT (first 3 files preview):")
    print("="*80)
    
    # Show preview of first 3 files
    preview = {}
    for i, (filename, profile) in enumerate(result['profiles'].items()):
        if i >= 3:
            break
        preview[filename] = profile
    
    print(json.dumps(preview, indent=2))
