from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
OUTPUT_DIR = DATA_DIR / "output"
DB_PATH = OUTPUT_DIR / "month_end_recon.duckdb"
AUDIT_REPORT_PATH = os.getenv("AUDIT_REPORT_PATH", "/Users/dongkaixin/Downloads/财务agent项目/管理会计多维盈利分析/长江证券2025年审计财报.pdf")
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "20250522"))
COMPANY_CODE = "CJSC_SYNTH"
