import pandas as pd
import json
from datetime import datetime

# Config
STUDY_ID = "MAXIS-08"
src = "/Users/siddharth/Downloads/ETL/ETL/edc_data_temp/Maxis-08 RAW DATA_CSV/AEVENT.csv"
out = "/Users/siddharth/Downloads/ETL/ETL/sdtm_chat_output"

# Load
try:
    df = pd.read_csv(src, encoding='utf-8-sig')
except:
    df = pd.read_csv(src, encoding='latin1')

print(f"Loaded {len(df)} records")

# Transform
def dt(v):
    if pd.isna(v): return ''
    s = str(v).split('.')[0]
    if len(s)==8 and s.isdigit(): return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    if len(s)==6 and s.isdigit(): return f"{s[0:4]}-{s[4:6]}"
    return s

recs = []
for i, r in df.iterrows():
    sid = str(r.get('INVSITE','')).split('_')[1] if '_' in str(r.get('INVSITE','')) else str(i+1)
    aeserl = str(r.get('AESERL','')).upper()
    aeser = 'Y' if 'HOSPITALIZATION' in aeserl else 'N'
    
    recs.append({
        'STUDYID': STUDY_ID,
        'DOMAIN': 'AE',
        'USUBJID': f"{STUDY_ID}-{sid}",
        'AESEQ': int(r.get('AESEQ', i+1)),
        'AETERM': str(r.get('AEVERB','')),
        'AEDECOD': str(r.get('AEPTT', r.get('AEVERB',''))),
        'AELLT': str(r.get('AELTT','')),
        'AELLTCD': str(r.get('AELTC','')),
        'AEPTCD': str(r.get('AEPTC','')),
        'AEHLT': str(r.get('AEHTT','')),
        'AEHLTCD': str(r.get('AEHTC','')),
        'AEHLGT': str(r.get('AEHGT1','')),
        'AEHLGTCD': str(r.get('AEHGC','')),
        'AESOC': str(r.get('AESCT','')),
        'AESOCCD': str(r.get('AESCC','')),
        'AESTDTC': dt(r.get('AESTDT')),
        'AEENDTC': dt(r.get('AEENDT')),
        'AESEV': str(r.get('AESEV','')),
        'AESER': aeser,
        'AESDTH': 'Y' if 'DIED' in str(r.get('AEOUTCL','')).upper() else '',
        'AESHOSP': 'Y' if 'HOSPITALIZATION' in aeserl else '',
        'AESLIFE': '',
        'AESDISAB': '',
        'AESCONG': '',
        'AESMIE': '',
        'AEOUT': str(r.get('AEOUTCL','')),
        'AEACN': str(r.get('AEACTL','')),
        'AEREL': str(r.get('AERELL','')),
        'AECONTRT': str(r.get('AETRT',''))
    })

df_ae = pd.DataFrame(recs)
df_ae.to_csv(f"{out}/ae.csv", index=False)

spec = {"domain": "AE", "study": STUDY_ID, "records": len(df_ae), "date": str(datetime.now())}
with open(f"{out}/ae_mapping_specification.json", 'w') as f:
    json.dump(spec, f, indent=2)

print(f"✓ Created {len(df_ae)} AE records")
print(f"✓ Saved to {out}/ae.csv")
print(f"\nSummary:")
print(f"  Serious: {(df_ae['AESER']=='Y').sum()}")
print(f"  Deaths: {(df_ae['AESDTH']=='Y').sum()}")
print(f"  Hosp: {(df_ae['AESHOSP']=='Y').sum()}")
print("\nFirst 2 records:")
print(df_ae[['USUBJID','AESEQ','AETERM','AESTDTC','AESEV']].head(2))
