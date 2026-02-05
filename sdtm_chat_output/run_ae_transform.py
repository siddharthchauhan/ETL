#!/usr/bin/env python3
"""
Execute AE Transformation
"""
import sys
import os
sys.path.insert(0, '/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output')

# Import and run
from transform_ae import transform_ae_data

if __name__ == "__main__":
    result = transform_ae_data()
    sys.exit(0 if result is not None else 1)
