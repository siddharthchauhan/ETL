#!/usr/bin/env python3
"""Transform AE data for MAXIS-08 study"""

import pandas as pd
import numpy as np

# Load source
df = pd.read_csv('/tmp/s3_data/extracted/Maxis-08 RAW DATA_CSV/AEVENTC.csv', encoding='utf-8-sig')

print(f"Source records: {len(df)}")
print(f"Source columns: {list(df.columns)}")

# Helper functions
def format_date(d):
    if pd.isna(d) or str(d).strip() == '': return ''
    d = str(d).split('.')[0].strip()
    if len(d) == 8: return f"{d[0:4]}-{d[4:6]}-{d[6:8]}"
    if len(d) == 6: return f"{d[0:4]}-{d[4:6]}"
    return d

def map_sev(v):
    if pd.isna(v): return ''
    s = str(v).upper()
    return {'MILD': 'MILD', 'MODERATE': 'MODERATE', 'SEVERE': 'SEVERE'}.get(s, s)

def map_ser(v):
    if pd.isna(v): return ''
    s = str(v).upper()
    return 'Y' if 'SERIOUS' in s or s in ['Y', '1'] else 'N'

def map_rel(v):
    if pd.isna(v): return ''
    s = str(v).upper()
    m = {'POSSIBLE': 'POSSIBLY RELATED', 'PROBABLE': 'PROBABLY RELATED', 
         'UNLIKELY': 'UNLIKELY RELATED', 'UNRELATED': 'NOT RELATED',
         'NOT RELATED': 'NOT RELATED', 'RELATED': 'RELATED'}
    return m.get(s, s)

def map_out(v):
    if pd.isna(v): return ''
    s = str(v).upper()
    m = {'RESOLVED': 'RECOVERED/RESOLVED', 'CONTINUING': 'NOT RECOVERED/NOT RESOLVED',
         'RECOVERING': 'RECOVERING/RESOLVING', 'FATAL': 'FATAL'}
    return m.get(s, s)

def map_act(v):
    if pd.isna(v): return ''
    s = str(v).upper()
    m = {'NONE': 'DOSE NOT CHANGED', '1': 'DOSE NOT CHANGED'}
    return m.get(s, 'DOSE NOT CHANGED')

# Transform
ae = pd.DataFrame()
ae['STUDYID'] = df['STUDY']
ae['DOMAIN'] = 'AE'
ae['USUBJID'] = df.apply(lambda r: f"{r['STUDY']}-{r['INVSITE']}-{r['PT']}", axis=1)
ae['AESEQ'] = df['AESEQ']
ae['AESPID'] = ''
ae['AETERM'] = df['AEVERB'].fillna('')
ae['AEMODIFY'] = df['MODTERM'].fillna('')
ae['AEDECOD'] = df['PTTERM'].fillna('')
ae['AELLT'] = df['LLTTERM'].fillna('')
ae['AELLTCD'] = df['LLTCODE'].apply(lambda x: int(x) if pd.notna(x) else None)
ae['AEPTCD'] = df['PTCODE'].apply(lambda x: int(x) if pd.notna(x) else None)
ae['AEHLT'] = df['HLTTERM'].fillna('')
ae['AEHLTCD'] = df['HLTCODE'].apply(lambda x: int(x) if pd.notna(x) else None)
ae['AEHLGT'] = df['HLGTTERM'].fillna('')
ae['AEHLGTCD'] = df['HLGTCODE'].apply(lambda x: int(x) if pd.notna(x) else None)
ae['AEBODSYS'] = df['SOCTERM'].fillna('')
ae['AEBDSYCD'] = df['SOCCODE'].apply(lambda x: int(x) if pd.notna(x) else None)
ae['AESOC'] = df['SOCTERM'].fillna('')
ae['AESOCCD'] = df['SOCCODE'].apply(lambda x: int(x) if pd.notna(x) else None)
ae['AESEV'] = df['AESEV'].apply(map_sev)
ae['AESER'] = df['AESERL'].apply(map_ser)
ae['AEREL'] = df['AERELL'].apply(map_rel)
ae['AEACN'] = df['AEACTL'].apply(map_act)
ae['AEOUT'] = df['AEOUTCL'].apply(map_out)
ae['AESDTH'] = ''
ae['AESLIFE'] = ''
ae['AESHOSP'] = ''
ae['AESDISAB'] = ''
ae['AESCONG'] = ''
ae['AESMIE'] = ''
ae['AETOXGR'] = ''
ae['AECONTRT'] = ''
ae['AESTDTC'] = df['AESTDT'].apply(format_date)
ae['AEENDTC'] = df['AEENDT'].apply(format_date)
ae['AESTDY'] = None
ae['AEENDY'] = None
ae['EPOCH'] = ''
ae['VISITNUM'] = df['VISIT'].apply(lambda x: int(x) if pd.notna(x) and str(x).isdigit() else None)
ae['VISIT'] = df['CPEVENT'].fillna('')

# Save
ae.to_csv('/Users/siddharth/Downloads/ETL/ETL/sdtm_langgraph_output/ae.csv', index=False)

print(f"\nOutput records: {len(ae)}")
print(f"Output columns: {len(ae.columns)}")
print(f"Unique subjects: {ae['USUBJID'].nunique()}")
print(f"\nSample:\n{ae[['USUBJID', 'AESEQ', 'AETERM', 'AEDECOD', 'AESEV']].head()}")
print(f"\nSaved to: /Users/siddharth/Downloads/ETL/ETL/sdtm_langgraph_output/ae.csv")
