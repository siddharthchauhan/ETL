"""Copy AE transformation files to requested locations"""
import shutil
import pandas as pd
import json
from datetime import datetime

# Copy the complete AE dataset
source_ae = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_sdtm_complete_transform.csv"
dest_ae = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_domain.csv"
shutil.copy2(source_ae, dest_ae)
print(f"✓ Copied AE dataset to: {dest_ae}")

# Copy the mapping specification
source_mapping = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_mapping_specification.json"
dest_mapping = "/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace/ae_mapping_spec.json"
shutil.copy2(source_mapping, dest_mapping)
print(f"✓ Copied mapping spec to: {dest_mapping}")

# Load the datasets for statistics
df = pd.read_csv(dest_ae)
print(f"\n📊 AE Dataset Statistics:")
print(f"  Total Records: {len(df)}")
print(f"  Unique Subjects: {df['USUBJID'].nunique()}")
print(f"  Variables: {len(df.columns)}")
print(f"\n✅ Files copied successfully!")
