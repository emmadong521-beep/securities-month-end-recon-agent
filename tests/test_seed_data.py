import pandas as pd

from src.config import SYNTHETIC_DIR
from src.db import load_synthetic_data_to_duckdb
from src.seed_data import generate_synthetic_data
from src.schema import CORE_TABLES


def test_core_tables_non_empty():
    counts = generate_synthetic_data()
    load_synthetic_data_to_duckdb()
    for table in CORE_TABLES:
        if table == "reconciliation_exception":
            continue
        assert counts[table] > 0, table


def test_traceable_ids_exist():
    generate_synthetic_data()
    trades = pd.read_csv(SYNTHETIC_DIR / "trade_flow.csv")
    commissions = pd.read_csv(SYNTHETIC_DIR / "commission_calc.csv")
    sub = pd.read_csv(SYNTHETIC_DIR / "revenue_subledger.csv")
    gl = pd.read_csv(SYNTHETIC_DIR / "gl_journal.csv")
    assert commissions["trade_id"].isin(trades["trade_id"]).all()
    commission_sub = sub[sub["source_system"] == "COMMISSION_SYSTEM"]
    assert commission_sub["source_doc_id"].isin(commissions["commission_id"]).all()
    assert gl[gl["source_system"] == "REVENUE_SUBLEDGER"]["source_doc_id"].isin(sub["subledger_id"]).all()
