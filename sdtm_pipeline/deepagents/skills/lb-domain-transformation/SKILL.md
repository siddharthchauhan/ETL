---
name: lb-domain-transformation
description: Automatically detect and transform lab data from horizontal (wide) format to SDTM LB vertical (long) format using a MELT operation.
Core Problem Solved:

EDC systems often export lab data with each test as a separate column (e.g., HGB, WBC, GLUCOSE)
SDTM requires vertical format where each row = one test result with LBTESTCD, LBTEST, LBORRES
---

# LB Domain Transformation Skill

## Problem Statement

Lab data often comes from EDC systems in **horizontal format** where:
- Each row represents a subject at a visit
- Each column represents a different lab test (e.g., `HEMOGLOBIN`, `WBC`, `GLUCOSE`)
- Values in these columns are the test results

SDTM LB domain requires **vertical format** where:
- Each row represents a single test result
- LBTESTCD contains the test code (e.g., `HGB`)
- LBTEST contains the test name (e.g., `Hemoglobin`)
- LBORRES contains the test value

## Detection Logic

### Horizontal Format Indicators

The source data is likely horizontal if:
1. No column named `LBTESTCD`, `TESTCD`, or `LABTEST` exists
2. Multiple columns match known lab test patterns (HGB, WBC, ALT, etc.)
3. Only one row per subject per visit (instead of multiple rows per test)

```python
def detect_horizontal_format(df, domain="LB"):
    """
    Detect if source data is in horizontal format (needs MELT).

    Returns:
        tuple: (is_horizontal, test_columns, id_columns)
    """
    # Check for vertical format indicators
    vertical_indicators = [
        f"{domain}TESTCD", "TESTCD", "TEST", "LABTEST",
        "ANALYTE", "PARAMETER", "LPARM"
    ]

    for col in df.columns:
        if col.upper() in vertical_indicators:
            return (False, [], list(df.columns))

    # Check for horizontal format - find lab test columns
    test_columns = []
    id_columns = []

    for col in df.columns:
        col_upper = col.upper().strip()

        # Check if column is a known lab test
        if col_upper in LAB_TEST_CODE_MAP:
            test_columns.append(col)
        # Check if column matches lab test patterns
        elif any(pattern in col_upper for pattern in LAB_TEST_PATTERNS):
            test_columns.append(col)
        else:
            id_columns.append(col)

    # If we found multiple test columns, it's horizontal format
    is_horizontal = len(test_columns) >= 3

    return (is_horizontal, test_columns, id_columns)
```

## Lab Test Code Mapping Dictionary

This comprehensive mapping converts common EDC column names to SDTM LBTESTCD and LBTEST values:

```python
LAB_TEST_CODE_MAP = {
    # ============================================================
    # HEMATOLOGY
    # ============================================================
    # Red Blood Cells
    "HGB": {"LBTESTCD": "HGB", "LBTEST": "Hemoglobin", "LBCAT": "HEMATOLOGY", "LBSTRESU": "g/L"},
    "HEMOGLOBIN": {"LBTESTCD": "HGB", "LBTEST": "Hemoglobin", "LBCAT": "HEMATOLOGY", "LBSTRESU": "g/L"},
    "HB": {"LBTESTCD": "HGB", "LBTEST": "Hemoglobin", "LBCAT": "HEMATOLOGY", "LBSTRESU": "g/L"},
    "HCT": {"LBTESTCD": "HCT", "LBTEST": "Hematocrit", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},
    "HEMATOCRIT": {"LBTESTCD": "HCT", "LBTEST": "Hematocrit", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},
    "RBC": {"LBTESTCD": "RBC", "LBTEST": "Erythrocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^12/L"},
    "ERYTHROCYTES": {"LBTESTCD": "RBC", "LBTEST": "Erythrocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^12/L"},
    "MCV": {"LBTESTCD": "MCV", "LBTEST": "Ery. Mean Corpuscular Volume", "LBCAT": "HEMATOLOGY", "LBSTRESU": "fL"},
    "MCH": {"LBTESTCD": "MCH", "LBTEST": "Ery. Mean Corpuscular Hemoglobin", "LBCAT": "HEMATOLOGY", "LBSTRESU": "pg"},
    "MCHC": {"LBTESTCD": "MCHC", "LBTEST": "Ery. Mean Corpuscular HGB Concentration", "LBCAT": "HEMATOLOGY", "LBSTRESU": "g/L"},
    "RDW": {"LBTESTCD": "RDW", "LBTEST": "Erythrocyte Distribution Width", "LBCAT": "HEMATOLOGY", "LBSTRESU": "%"},

    # White Blood Cells
    "WBC": {"LBTESTCD": "WBC", "LBTEST": "Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "LEUKOCYTES": {"LBTESTCD": "WBC", "LBTEST": "Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "NEUT": {"LBTESTCD": "NEUT", "LBTEST": "Neutrophils", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "NEUTROPHILS": {"LBTESTCD": "NEUT", "LBTEST": "Neutrophils", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "NEUTLE": {"LBTESTCD": "NEUTLE", "LBTEST": "Neutrophils/Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},
    "LYMPH": {"LBTESTCD": "LYMPH", "LBTEST": "Lymphocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "LYMPHOCYTES": {"LBTESTCD": "LYMPH", "LBTEST": "Lymphocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "LYMPHLE": {"LBTESTCD": "LYMPHLE", "LBTEST": "Lymphocytes/Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},
    "MONO": {"LBTESTCD": "MONO", "LBTEST": "Monocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "MONOCYTES": {"LBTESTCD": "MONO", "LBTEST": "Monocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "MONOLE": {"LBTESTCD": "MONOLE", "LBTEST": "Monocytes/Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},
    "EOS": {"LBTESTCD": "EOS", "LBTEST": "Eosinophils", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "EOSINOPHILS": {"LBTESTCD": "EOS", "LBTEST": "Eosinophils", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "EOSLE": {"LBTESTCD": "EOSLE", "LBTEST": "Eosinophils/Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},
    "BASO": {"LBTESTCD": "BASO", "LBTEST": "Basophils", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "BASOPHILS": {"LBTESTCD": "BASO", "LBTEST": "Basophils", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "BASOLE": {"LBTESTCD": "BASOLE", "LBTEST": "Basophils/Leukocytes", "LBCAT": "HEMATOLOGY", "LBSTRESU": "FRACTION"},

    # Platelets
    "PLAT": {"LBTESTCD": "PLAT", "LBTEST": "Platelets", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "PLATELETS": {"LBTESTCD": "PLAT", "LBTEST": "Platelets", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "PLT": {"LBTESTCD": "PLAT", "LBTEST": "Platelets", "LBCAT": "HEMATOLOGY", "LBSTRESU": "10^9/L"},
    "MPV": {"LBTESTCD": "MPV", "LBTEST": "Mean Platelet Volume", "LBCAT": "HEMATOLOGY", "LBSTRESU": "fL"},

    # Coagulation
    "PT": {"LBTESTCD": "PT", "LBTEST": "Prothrombin Time", "LBCAT": "COAGULATION", "LBSTRESU": "sec"},
    "INR": {"LBTESTCD": "INR", "LBTEST": "International Normalized Ratio", "LBCAT": "COAGULATION", "LBSTRESU": "RATIO"},
    "APTT": {"LBTESTCD": "APTT", "LBTEST": "Activated Partial Thromboplastin Time", "LBCAT": "COAGULATION", "LBSTRESU": "sec"},
    "PTT": {"LBTESTCD": "APTT", "LBTEST": "Activated Partial Thromboplastin Time", "LBCAT": "COAGULATION", "LBSTRESU": "sec"},
    "FIBRINO": {"LBTESTCD": "FIBRINO", "LBTEST": "Fibrinogen", "LBCAT": "COAGULATION", "LBSTRESU": "g/L"},
    "FIBRINOGEN": {"LBTESTCD": "FIBRINO", "LBTEST": "Fibrinogen", "LBCAT": "COAGULATION", "LBSTRESU": "g/L"},

    # ============================================================
    # CHEMISTRY - Liver Function
    # ============================================================
    "ALT": {"LBTESTCD": "ALT", "LBTEST": "Alanine Aminotransferase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "SGPT": {"LBTESTCD": "ALT", "LBTEST": "Alanine Aminotransferase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "AST": {"LBTESTCD": "AST", "LBTEST": "Aspartate Aminotransferase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "SGOT": {"LBTESTCD": "AST", "LBTEST": "Aspartate Aminotransferase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "ALP": {"LBTESTCD": "ALP", "LBTEST": "Alkaline Phosphatase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "ALKPHOS": {"LBTESTCD": "ALP", "LBTEST": "Alkaline Phosphatase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "GGT": {"LBTESTCD": "GGT", "LBTEST": "Gamma Glutamyl Transferase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "BILI": {"LBTESTCD": "BILI", "LBTEST": "Bilirubin", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "BILIRUBIN": {"LBTESTCD": "BILI", "LBTEST": "Bilirubin", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "TBILI": {"LBTESTCD": "BILI", "LBTEST": "Bilirubin", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "DBILI": {"LBTESTCD": "DBILI", "LBTEST": "Direct Bilirubin", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "IBILI": {"LBTESTCD": "IBILI", "LBTEST": "Indirect Bilirubin", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "ALB": {"LBTESTCD": "ALB", "LBTEST": "Albumin", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},
    "ALBUMIN": {"LBTESTCD": "ALB", "LBTEST": "Albumin", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},
    "PROT": {"LBTESTCD": "PROT", "LBTEST": "Protein", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},
    "PROTEIN": {"LBTESTCD": "PROT", "LBTEST": "Protein", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},
    "TPROT": {"LBTESTCD": "PROT", "LBTEST": "Protein", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},
    "GLOBULIN": {"LBTESTCD": "GLOB", "LBTEST": "Globulin", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},

    # ============================================================
    # CHEMISTRY - Kidney Function
    # ============================================================
    "CREAT": {"LBTESTCD": "CREAT", "LBTEST": "Creatinine", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "CREATININE": {"LBTESTCD": "CREAT", "LBTEST": "Creatinine", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "BUN": {"LBTESTCD": "BUN", "LBTEST": "Blood Urea Nitrogen", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "UREA": {"LBTESTCD": "UREA", "LBTEST": "Urea", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "URIC": {"LBTESTCD": "URATE", "LBTEST": "Urate", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "URATE": {"LBTESTCD": "URATE", "LBTEST": "Urate", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "GFR": {"LBTESTCD": "GFR", "LBTEST": "Glomerular Filtration Rate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mL/min/1.73m2", "LBDRVFL": "Y"},
    "EGFR": {"LBTESTCD": "GFR", "LBTEST": "Glomerular Filtration Rate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mL/min/1.73m2", "LBDRVFL": "Y"},

    # ============================================================
    # CHEMISTRY - Electrolytes
    # ============================================================
    "SODIUM": {"LBTESTCD": "SODIUM", "LBTEST": "Sodium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "NA": {"LBTESTCD": "SODIUM", "LBTEST": "Sodium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "POTASSIUM": {"LBTESTCD": "K", "LBTEST": "Potassium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "K": {"LBTESTCD": "K", "LBTEST": "Potassium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "CHLORIDE": {"LBTESTCD": "CL", "LBTEST": "Chloride", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "CL": {"LBTESTCD": "CL", "LBTEST": "Chloride", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "BICARB": {"LBTESTCD": "BICARB", "LBTEST": "Bicarbonate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "CO2": {"LBTESTCD": "BICARB", "LBTEST": "Bicarbonate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "CA": {"LBTESTCD": "CA", "LBTEST": "Calcium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "CALCIUM": {"LBTESTCD": "CA", "LBTEST": "Calcium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "MG": {"LBTESTCD": "MG", "LBTEST": "Magnesium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "MAGNESIUM": {"LBTESTCD": "MG", "LBTEST": "Magnesium", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "PHOS": {"LBTESTCD": "PHOS", "LBTEST": "Phosphate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "PHOSPHATE": {"LBTESTCD": "PHOS", "LBTEST": "Phosphate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "PHOSPHORUS": {"LBTESTCD": "PHOS", "LBTEST": "Phosphate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},

    # ============================================================
    # CHEMISTRY - Glucose/Metabolic
    # ============================================================
    "GLUC": {"LBTESTCD": "GLUC", "LBTEST": "Glucose", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "GLUCOSE": {"LBTESTCD": "GLUC", "LBTEST": "Glucose", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "HBA1C": {"LBTESTCD": "HBA1C", "LBTEST": "Hemoglobin A1C", "LBCAT": "CHEMISTRY", "LBSTRESU": "%"},
    "A1C": {"LBTESTCD": "HBA1C", "LBTEST": "Hemoglobin A1C", "LBCAT": "CHEMISTRY", "LBSTRESU": "%"},
    "INSULIN": {"LBTESTCD": "INSULIN", "LBTEST": "Insulin", "LBCAT": "CHEMISTRY", "LBSTRESU": "pmol/L"},

    # ============================================================
    # CHEMISTRY - Lipids
    # ============================================================
    "CHOL": {"LBTESTCD": "CHOL", "LBTEST": "Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "CHOLESTEROL": {"LBTESTCD": "CHOL", "LBTEST": "Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "TCHOL": {"LBTESTCD": "CHOL", "LBTEST": "Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "HDL": {"LBTESTCD": "HDL", "LBTEST": "HDL Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "HDLC": {"LBTESTCD": "HDL", "LBTEST": "HDL Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "LDL": {"LBTESTCD": "LDL", "LBTEST": "LDL Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L", "LBDRVFL": "Y"},
    "LDLC": {"LBTESTCD": "LDL", "LBTEST": "LDL Cholesterol", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L", "LBDRVFL": "Y"},
    "TRIG": {"LBTESTCD": "TRIG", "LBTEST": "Triglycerides", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "TRIGLYCERIDES": {"LBTESTCD": "TRIG", "LBTEST": "Triglycerides", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},
    "TG": {"LBTESTCD": "TRIG", "LBTEST": "Triglycerides", "LBCAT": "CHEMISTRY", "LBSTRESU": "mmol/L"},

    # ============================================================
    # CHEMISTRY - Other
    # ============================================================
    "LDH": {"LBTESTCD": "LDH", "LBTEST": "Lactate Dehydrogenase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "CK": {"LBTESTCD": "CK", "LBTEST": "Creatine Kinase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "CPK": {"LBTESTCD": "CK", "LBTEST": "Creatine Kinase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "CKMB": {"LBTESTCD": "CKMB", "LBTEST": "Creatine Kinase MB", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "AMYLASE": {"LBTESTCD": "AMYLASE", "LBTEST": "Amylase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "LIPASE": {"LBTESTCD": "LIPASE", "LBTEST": "Lipase", "LBCAT": "CHEMISTRY", "LBSTRESU": "U/L"},
    "IRON": {"LBTESTCD": "IRON", "LBTEST": "Iron", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "FERRITIN": {"LBTESTCD": "FERRITN", "LBTEST": "Ferritin", "LBCAT": "CHEMISTRY", "LBSTRESU": "ug/L"},
    "TIBC": {"LBTESTCD": "TIBC", "LBTEST": "Iron Binding Capacity, Total", "LBCAT": "CHEMISTRY", "LBSTRESU": "umol/L"},
    "TRANSFERRIN": {"LBTESTCD": "TRANSFE", "LBTEST": "Transferrin", "LBCAT": "CHEMISTRY", "LBSTRESU": "g/L"},
    "FOLATE": {"LBTESTCD": "FOLATE", "LBTEST": "Folate", "LBCAT": "CHEMISTRY", "LBSTRESU": "nmol/L"},
    "B12": {"LBTESTCD": "B12", "LBTEST": "Vitamin B12", "LBCAT": "CHEMISTRY", "LBSTRESU": "pmol/L"},
    "VITB12": {"LBTESTCD": "B12", "LBTEST": "Vitamin B12", "LBCAT": "CHEMISTRY", "LBSTRESU": "pmol/L"},
    "VITD": {"LBTESTCD": "VITD", "LBTEST": "Vitamin D", "LBCAT": "CHEMISTRY", "LBSTRESU": "nmol/L"},
    "CRP": {"LBTESTCD": "CRP", "LBTEST": "C-Reactive Protein", "LBCAT": "CHEMISTRY", "LBSTRESU": "mg/L"},
    "ESR": {"LBTESTCD": "ESR", "LBTEST": "Erythrocyte Sedimentation Rate", "LBCAT": "CHEMISTRY", "LBSTRESU": "mm/h"},

    # ============================================================
    # CHEMISTRY - Thyroid
    # ============================================================
    "TSH": {"LBTESTCD": "TSH", "LBTEST": "Thyrotropin", "LBCAT": "CHEMISTRY", "LBSTRESU": "mIU/L"},
    "T3": {"LBTESTCD": "T3", "LBTEST": "Triiodothyronine", "LBCAT": "CHEMISTRY", "LBSTRESU": "nmol/L"},
    "T4": {"LBTESTCD": "T4", "LBTEST": "Thyroxine", "LBCAT": "CHEMISTRY", "LBSTRESU": "nmol/L"},
    "FT3": {"LBTESTCD": "FT3", "LBTEST": "Free Triiodothyronine", "LBCAT": "CHEMISTRY", "LBSTRESU": "pmol/L"},
    "FT4": {"LBTESTCD": "FT4", "LBTEST": "Free Thyroxine", "LBCAT": "CHEMISTRY", "LBSTRESU": "pmol/L"},

    # ============================================================
    # CHEMISTRY - Cardiac Markers
    # ============================================================
    "TROP": {"LBTESTCD": "TROP", "LBTEST": "Troponin", "LBCAT": "CHEMISTRY", "LBSTRESU": "ng/L"},
    "TROPONIN": {"LBTESTCD": "TROP", "LBTEST": "Troponin", "LBCAT": "CHEMISTRY", "LBSTRESU": "ng/L"},
    "TROPI": {"LBTESTCD": "TROPI", "LBTEST": "Troponin I", "LBCAT": "CHEMISTRY", "LBSTRESU": "ng/L"},
    "TROPT": {"LBTESTCD": "TROPT", "LBTEST": "Troponin T", "LBCAT": "CHEMISTRY", "LBSTRESU": "ng/L"},
    "BNP": {"LBTESTCD": "BNP", "LBTEST": "Brain Natriuretic Peptide", "LBCAT": "CHEMISTRY", "LBSTRESU": "pg/mL"},
    "PROBNP": {"LBTESTCD": "NTPBNP", "LBTEST": "N-terminal proBNP", "LBCAT": "CHEMISTRY", "LBSTRESU": "pg/mL"},

    # ============================================================
    # URINALYSIS
    # ============================================================
    "UPROT": {"LBTESTCD": "UPROT", "LBTEST": "Protein Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UGLUC": {"LBTESTCD": "UGLUC", "LBTEST": "Glucose Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UKET": {"LBTESTCD": "UKET", "LBTEST": "Ketones Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UBLOOD": {"LBTESTCD": "UBLOOD", "LBTEST": "Blood Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UPH": {"LBTESTCD": "UPH", "LBTEST": "pH Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "USPECGR": {"LBTESTCD": "USPECGR", "LBTEST": "Specific Gravity Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UROBILI": {"LBTESTCD": "UROBILI", "LBTEST": "Urobilinogen Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UBILI": {"LBTESTCD": "UBILI", "LBTEST": "Bilirubin Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UNITRA": {"LBTESTCD": "UNITRA", "LBTEST": "Nitrite Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "ULEUK": {"LBTESTCD": "ULEUK", "LBTEST": "Leukocyte Esterase Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UWBC": {"LBTESTCD": "UWBC", "LBTEST": "Leukocytes Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "URBC": {"LBTESTCD": "URBC", "LBTEST": "Erythrocytes Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UALB": {"LBTESTCD": "UALB", "LBTEST": "Albumin Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UMALB": {"LBTESTCD": "UMALB", "LBTEST": "Microalbumin Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "UCREAT": {"LBTESTCD": "UCREAT", "LBTEST": "Creatinine Urine", "LBCAT": "URINALYSIS", "LBSPEC": "URINE"},
    "ACR": {"LBTESTCD": "ACR", "LBTEST": "Albumin/Creatinine Ratio", "LBCAT": "URINALYSIS", "LBSPEC": "URINE", "LBDRVFL": "Y"},
}

# Common patterns for lab test detection (partial matches)
LAB_TEST_PATTERNS = [
    "HEMOGLOBIN", "HEMATOCRIT", "ERYTHRO", "LEUKO", "PLATELET",
    "NEUTRO", "LYMPHO", "MONO", "EOSINO", "BASO",
    "BILIRU", "CREATIN", "ALBUMIN", "PROTEIN", "GLUCOSE",
    "CHOLEST", "TRIGLYC", "SODIUM", "POTASSIUM", "CHLORIDE",
    "CALCIUM", "MAGNESIUM", "PHOSPH", "ALANINE", "ASPARTATE",
    "ALKALINE", "GAMMA", "UREA", "URIC", "IRON", "FERRITIN",
    "PROTHROMBIN", "FIBRINOGEN", "THYRO", "INSULIN",
    "TROPONIN", "AMYLASE", "LIPASE", "LACTATE",
]
```

## MELT Transformation Logic

```python
def melt_horizontal_to_vertical(df, test_columns, id_columns, study_id):
    """
    Transform horizontal lab data to SDTM LB vertical format.

    Args:
        df: Source DataFrame in horizontal format
        test_columns: List of columns containing test results
        id_columns: List of identifier columns to keep
        study_id: Study identifier

    Returns:
        DataFrame in vertical SDTM LB format
    """
    import pandas as pd

    lb_records = []

    for idx, row in df.iterrows():
        # Get subject identifier
        usubjid = None
        for col in ["USUBJID", "SUBJID", "PT", "SUBJECT_ID", "PATIENT_ID"]:
            if col in row and pd.notna(row[col]):
                usubjid = str(row[col])
                break

        if not usubjid:
            continue

        # Get visit info
        visitnum = None
        visit = ""
        for col in ["VISITNUM", "VISNUM", "VISIT_NUMBER"]:
            if col in row and pd.notna(row[col]):
                try:
                    visitnum = int(float(row[col]))
                except:
                    visitnum = row[col]
                break

        for col in ["VISIT", "VISNAME", "VISIT_NAME"]:
            if col in row and pd.notna(row[col]):
                visit = str(row[col])
                break

        # Get date info
        lbdtc = ""
        for col in ["LBDTC", "DATE", "VISITDT", "COLLDT", "SPECDT", "LABDT"]:
            if col in row and pd.notna(row[col]):
                lbdtc = _convert_date_to_iso(row[col])
                break

        # Get epoch
        epoch = ""
        for col in ["EPOCH", "PHASE", "PERIOD"]:
            if col in row and pd.notna(row[col]):
                epoch = str(row[col]).upper()
                break

        seq = 0

        # Create one record per test
        for test_col in test_columns:
            if test_col not in row or pd.isna(row[test_col]):
                continue

            seq += 1
            result = row[test_col]

            # Get test mapping
            test_col_upper = test_col.upper().strip()
            test_info = LAB_TEST_CODE_MAP.get(test_col_upper, {})

            # If not found by exact match, try partial match
            if not test_info:
                for pattern, info in LAB_TEST_CODE_MAP.items():
                    if pattern in test_col_upper or test_col_upper in pattern:
                        test_info = info
                        break

            # Default mapping if not found
            if not test_info:
                # Create LBTESTCD from column name (max 8 chars)
                test_info = {
                    "LBTESTCD": test_col_upper[:8],
                    "LBTEST": test_col.replace("_", " ").title(),
                    "LBCAT": "UNKNOWN",
                    "LBSTRESU": ""
                }

            lb_record = {
                "STUDYID": study_id,
                "DOMAIN": "LB",
                "USUBJID": f"{study_id}-{usubjid}" if not usubjid.startswith(study_id) else usubjid,
                "LBSEQ": seq,
                "LBTESTCD": test_info.get("LBTESTCD", test_col_upper[:8]),
                "LBTEST": test_info.get("LBTEST", test_col),
                "LBCAT": test_info.get("LBCAT", ""),
                "LBORRES": str(result),
                "LBORRESU": test_info.get("LBSTRESU", ""),
                "LBSTRESC": str(result),
                "LBSTRESN": None,
                "LBSTRESU": test_info.get("LBSTRESU", ""),
                "LBSPEC": test_info.get("LBSPEC", "BLOOD"),
                "LBDRVFL": test_info.get("LBDRVFL", ""),
                "VISITNUM": visitnum,
                "VISIT": visit,
                "EPOCH": epoch,
                "LBDTC": lbdtc,
            }

            # Try to parse numeric result
            try:
                lb_record["LBSTRESN"] = float(result)
            except (ValueError, TypeError):
                pass

            lb_records.append(lb_record)

    return pd.DataFrame(lb_records)


def _convert_date_to_iso(date_value):
    """Convert various date formats to ISO 8601."""
    import pandas as pd
    from datetime import datetime

    if pd.isna(date_value):
        return ""

    date_str = str(date_value)

    # Already ISO format
    if len(date_str) >= 10 and date_str[4] == '-' and date_str[7] == '-':
        return date_str[:10]

    # Try various formats
    formats = [
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y%m%d",
        "%d-%b-%Y", "%d %b %Y", "%b %d, %Y"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except:
            continue

    return date_str
```

## Integration with LBTransformer

The LBTransformer should be enhanced to:

1. **Detect format before transformation**
2. **Apply MELT if horizontal format detected**
3. **Use test code mapping dictionary**

```python
class EnhancedLBTransformer(BaseDomainTransformer):
    """Enhanced LB transformer with horizontal format detection."""

    def transform(self, source_df: pd.DataFrame) -> pd.DataFrame:
        """Transform lab data with automatic format detection."""

        # Step 1: Detect format
        is_horizontal, test_cols, id_cols = detect_horizontal_format(source_df, "LB")

        if is_horizontal:
            self.log(f"Detected HORIZONTAL format with {len(test_cols)} test columns")
            self.log(f"Test columns: {', '.join(test_cols[:10])}...")

            # Step 2: MELT to vertical format
            vertical_df = melt_horizontal_to_vertical(
                source_df, test_cols, id_cols, self.study_id
            )

            self.log(f"MELT transformation: {len(source_df)} rows -> {len(vertical_df)} test records")

            # Step 3: Continue with standard transformation
            return self._finalize_lb_dataset(vertical_df)
        else:
            self.log("Detected VERTICAL format - using standard transformation")
            return self._transform_vertical(source_df)
```

## Unit Conversion Factors

For standardizing units:

```python
UNIT_CONVERSIONS = {
    # Hemoglobin: g/dL -> g/L
    ("g/dL", "g/L"): 10.0,
    ("g/dl", "g/L"): 10.0,

    # Glucose: mg/dL -> mmol/L
    ("mg/dL", "mmol/L", "GLUC"): 0.0555,

    # Creatinine: mg/dL -> umol/L
    ("mg/dL", "umol/L", "CREAT"): 88.4,

    # Bilirubin: mg/dL -> umol/L
    ("mg/dL", "umol/L", "BILI"): 17.1,

    # Cholesterol: mg/dL -> mmol/L
    ("mg/dL", "mmol/L", "CHOL"): 0.0259,
    ("mg/dL", "mmol/L", "HDL"): 0.0259,
    ("mg/dL", "mmol/L", "LDL"): 0.0259,

    # Triglycerides: mg/dL -> mmol/L
    ("mg/dL", "mmol/L", "TRIG"): 0.0113,

    # Calcium: mg/dL -> mmol/L
    ("mg/dL", "mmol/L", "CA"): 0.25,

    # Albumin: g/dL -> g/L
    ("g/dL", "g/L", "ALB"): 10.0,
}
```

## Specimen Type Inference

When LBSPEC is not provided in source data:

```python
SPECIMEN_BY_CATEGORY = {
    "HEMATOLOGY": "WHOLE BLOOD",
    "COAGULATION": "PLASMA",
    "CHEMISTRY": "SERUM",
    "URINALYSIS": "URINE",
}

def infer_specimen(lbcat, lbtestcd):
    """Infer specimen type from category or test."""
    if lbcat in SPECIMEN_BY_CATEGORY:
        return SPECIMEN_BY_CATEGORY[lbcat]

    # Urine tests
    if lbtestcd.startswith("U") or lbtestcd in ["ACR", "UMALB"]:
        return "URINE"

    # Default to blood
    return "BLOOD"
```

## Instructions for Agent

When transforming LB domain data:

1. **FIRST**: Check if source data is horizontal format (test values as columns)
2. **IF HORIZONTAL**: Apply MELT transformation using test code mapping
3. **ALWAYS**: Use LAB_TEST_CODE_MAP for LBTESTCD and LBTEST values
4. **DERIVE**: LBCAT from test code mapping or file name (CHEMLAB -> CHEMISTRY)
5. **INFER**: LBSPEC from category if not provided
6. **CONVERT**: Units to SI standard using conversion factors
7. **CALCULATE**: LBNRIND from reference ranges if available

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Empty LBTESTCD | Horizontal format not detected | Apply MELT transformation |
| Empty LBORRES | Test values in columns, not RESULT column | Extract from test columns |
| Empty LBCAT | No category mapping | Use LAB_TEST_CODE_MAP |
| Wrong LBSPEC | Not inferred from category | Use SPECIMEN_BY_CATEGORY |
| Empty LBTEST | Only test code provided | Look up in LAB_TEST_CODE_MAP |
