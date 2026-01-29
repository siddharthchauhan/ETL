"""
Runner script for AE domain fix
"""
import asyncio
import sys
from pathlib import Path

# Add to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sdtm_pipeline.fix_ae_domain import main

if __name__ == "__main__":
    print("Starting AE domain fix...")
    asyncio.run(main())
