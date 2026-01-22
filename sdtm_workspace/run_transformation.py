#!/usr/bin/env python3
"""Execute the AE transformation"""
import sys
sys.path.insert(0, '/Users/siddharth/Downloads/ETL/ETL/sdtm_workspace')

from transform_ae_comprehensive import transform_aevent_to_sdtm

if __name__ == "__main__":
    ae_df, suppae_df, stats = transform_aevent_to_sdtm()
