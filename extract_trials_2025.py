#!/usr/bin/env python3
"""
Extract clinical trials data from ClinicalTrials.gov for year 2025
Uses the ClinicalTrials.gov API to fetch trials with start dates in 2025
"""

import requests
import json
import time
from datetime import datetime
from collections import defaultdict
import re

# API endpoint for ClinicalTrials.gov
API_BASE = "https://clinicaltrials.gov/api/v2/studies"

def fetch_trials_batch(page_token=None):
    """Fetch a batch of trials from the API"""
    params = {
        "filter.advanced": "AREA[StartDate]RANGE[2025-01-01,2025-12-31]",
        "format": "json",
        "pageSize": 1000,
        "countTotal": "true",
    }
    
    # Add pagination token if provided
    if page_token:
        params["pageToken"] = page_token
    
    try:
        response = requests.get(API_BASE, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching batch: {e}")
        return None

def categorize_therapeutic_area(conditions):
    """Categorize trials by therapeutic area based on conditions"""
    if not conditions:
        return "Unknown"
    
    # Convert conditions to lowercase for matching
    conditions_lower = [c.lower() if c else "" for c in conditions]
    conditions_text = " ".join(conditions_lower)
    
    # Define therapeutic area keywords (order matters - check specific before general)
    categories = {
        "Oncology": ["cancer", "carcinoma", "tumor", "tumour", "malignancy", "neoplasm", "lymphoma", 
                     "leukemia", "leukaemia", "melanoma", "sarcoma", "oncology", "metastatic", "myeloma"],
        "Cardiovascular": ["cardiovascular", "cardiac", "heart", "hypertension", "myocardial", 
                          "coronary", "atherosclerosis", "stroke", "arrhythmia", "vascular", "angina"],
        "Neurological": ["neurological", "alzheimer", "parkinson", "epilepsy", "multiple sclerosis", 
                        "dementia", "neuropathy", "seizure", "brain", "cerebral", "neural", "migraine"],
        "Diabetes/Metabolic": ["diabetes", "diabetic", "metabolic", "obesity", "glucose", "insulin",
                              "hyperglycemia", "hypoglycemia", "metabolic syndrome"],
        "Infectious Disease": ["infectious", "infection", "covid", "coronavirus", "hiv", "aids", 
                              "hepatitis", "tuberculosis", "malaria", "viral", "bacterial", "sepsis"],
        "Respiratory": ["respiratory", "asthma", "copd", "pulmonary", "pneumonia", "lung", 
                       "bronchial", "breathing"],
        "Immunology/Rheumatology": ["immunology", "autoimmune", "immune", "rheumatoid", "lupus", "psoriasis",
                      "inflammatory", "arthritis", "crohn"],
        "Ophthalmology": ["ophthalmology", "eye", "ocular", "vision", "retina", "glaucoma", 
                         "macular", "cataract"],
        "Dermatology": ["dermatology", "skin", "dermatitis", "eczema", "acne", "rash"],
        "Gastroenterology": ["gastroenterology", "gastrointestinal", "liver", "hepatic", "bowel",
                            "colitis", "gastric", "intestinal", "digestive"],
        "Nephrology": ["nephrology", "kidney", "renal", "dialysis"],
        "Endocrinology": ["endocrine", "thyroid", "hormone", "pituitary", "adrenal"],
        "Psychiatry/Mental Health": ["psychiatry", "psychiatric", "depression", "anxiety", "schizophrenia",
                      "bipolar", "mental health", "psychological"],
        "Pain Management": ["pain", "chronic pain", "neuropathic pain", "analgesia"],
        "Women's Health": ["pregnancy", "pregnant", "maternal", "obstetric", "gynecologic", 
                          "menopause", "endometriosis"],
        "Pediatrics": ["pediatric", "child", "infant", "neonatal", "adolescent"],
        "Hematology": ["hematology", "blood", "anemia", "hemophilia", "thrombosis", "coagulation"],
        "Rare Diseases": ["rare disease", "orphan"],
        "Surgery": ["surgery", "surgical", "operative", "postoperative"],
        "Emergency Medicine": ["emergency", "trauma", "critical care", "intensive care"],
        "Orthopedics": ["orthopedic", "bone", "fracture", "joint", "musculoskeletal"],
        "Dental": ["dental", "tooth", "oral", "periodontal"],
    }
    
    # Check each category (first match wins)
    for category, keywords in categories.items():
        for keyword in keywords:
            if keyword in conditions_text:
                return category
    
    return "Other"

def extract_month(start_date_str):
    """Extract month name from start date"""
    if not start_date_str:
        return "Unknown"
    
    try:
        # Handle different date formats
        if len(start_date_str) >= 7:  # YYYY-MM or YYYY-MM-DD
            date_obj = datetime.strptime(start_date_str[:7], "%Y-%m")
            return date_obj.strftime("%B")  # Full month name
        elif len(start_date_str) == 4:  # YYYY only
            return "Unknown"
    except:
        pass
    
    return "Unknown"

def main():
    print("Starting extraction of clinical trials for 2025...")
    print("=" * 80)
    
    # Initialize data structures
    all_trials = []
    monthly_therapeutic_summary = defaultdict(lambda: defaultdict(int))
    therapeutic_areas_set = set()
    
    # Fetch trials in batches
    page_token = None
    batch_num = 0
    total_trials = 0
    
    while True:
        batch_num += 1
        print(f"Fetching batch {batch_num}...")
        
        batch_data = fetch_trials_batch(page_token)
        
        if not batch_data:
            print(f"  Warning: Failed to fetch batch {batch_num}")
            break
        
        # Get total count from first batch
        if batch_num == 1:
            total_trials = batch_data.get("totalCount", 0)
            print(f"Total trials to fetch: {total_trials}")
            print()
        
        studies = batch_data.get("studies", [])
        if not studies:
            print("  No more trials to fetch")
            break
        
        print(f"  Retrieved {len(studies)} trials")
        
        # Process each trial
        for study in studies:
            protocol_section = study.get("protocolSection", {})
            identification_module = protocol_section.get("identificationModule", {})
            conditions_module = protocol_section.get("conditionsModule", {})
            status_module = protocol_section.get("statusModule", {})
            
            # Extract data
            nct_id = identification_module.get("nctId", "")
            conditions = conditions_module.get("conditions", [])
            start_date_struct = status_module.get("startDateStruct", {})
            start_date = start_date_struct.get("date", "")
            
            # Categorize
            therapeutic_area = categorize_therapeutic_area(conditions)
            month = extract_month(start_date)
            
            # Store trial data
            trial_data = {
                "nct_id": nct_id,
                "conditions": conditions,
                "start_date": start_date,
                "therapeutic_area": therapeutic_area,
                "month": month
            }
            all_trials.append(trial_data)
            
            # Update summary
            if month != "Unknown":
                monthly_therapeutic_summary[month][therapeutic_area] += 1
                therapeutic_areas_set.add(therapeutic_area)
        
        # Check for next page
        next_page_token = batch_data.get("nextPageToken")
        if not next_page_token:
            print("  No more pages")
            break
        
        page_token = next_page_token
        print(f"  Progress: {len(all_trials)}/{total_trials} trials processed")
        
        # Rate limiting
        time.sleep(0.5)
    
    print()
    print("=" * 80)
    print(f"Extraction complete! Processed {len(all_trials)} trials")
    print()
    
    # Sort months in calendar order
    month_order = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    # Create final summary structure
    summary_by_month = {}
    for month in month_order:
        if month in monthly_therapeutic_summary:
            summary_by_month[month] = dict(monthly_therapeutic_summary[month])
    
    # Add unknown if exists
    if "Unknown" in monthly_therapeutic_summary:
        summary_by_month["Unknown"] = dict(monthly_therapeutic_summary["Unknown"])
    
    # Create final output structure
    output = {
        "extraction_date": datetime.now().isoformat(),
        "total_trials": len(all_trials),
        "summary_by_month": summary_by_month,
        "therapeutic_areas": sorted(list(therapeutic_areas_set)),
        "file_path": "/Users/siddharth/Downloads/ETL/ETL/clinical_trials_2025.json"
    }
    
    # Save to file
    output_file = "/Users/siddharth/Downloads/ETL/ETL/clinical_trials_2025.json"
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Data saved to: {output_file}")
    print()
    
    # Print summary statistics
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Total Trials: {len(all_trials)}")
    print(f"Therapeutic Areas Identified: {len(therapeutic_areas_set)}")
    print()
    
    print("Therapeutic Areas:")
    area_counts = {}
    for area in therapeutic_areas_set:
        count = sum(monthly_therapeutic_summary[month].get(area, 0) 
                   for month in monthly_therapeutic_summary)
        area_counts[area] = count
    
    for area in sorted(area_counts.keys(), key=lambda x: area_counts[x], reverse=True):
        print(f"  - {area}: {area_counts[area]} trials")
    print()
    
    print("Monthly Distribution:")
    for month in month_order:
        if month in monthly_therapeutic_summary:
            total = sum(monthly_therapeutic_summary[month].values())
            print(f"  - {month}: {total} trials")
    
    if "Unknown" in monthly_therapeutic_summary:
        total = sum(monthly_therapeutic_summary["Unknown"].values())
        print(f"  - Unknown: {total} trials")
    
    print()
    print("=" * 80)
    print("Output structure includes:")
    print("  - extraction_date: ISO timestamp of extraction")
    print("  - total_trials: Total number of trials processed")
    print("  - summary_by_month: Monthly breakdown by therapeutic area")
    print("  - therapeutic_areas: List of all therapeutic areas found")
    print("  - file_path: Path to the JSON output file")
    print()
    print("Done!")
    
    return output

if __name__ == "__main__":
    result = main()
    
    # Print the final summary in the requested format
    if result:
        print()
        print("=" * 80)
        print("FINAL OUTPUT SUMMARY")
        print("=" * 80)
        print(json.dumps({
            "total_trials": result["total_trials"],
            "summary_by_month": result["summary_by_month"],
            "therapeutic_areas": result["therapeutic_areas"],
            "file_path": result["file_path"]
        }, indent=2))
