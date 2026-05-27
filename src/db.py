from __future__ import annotations

from pathlib import Path

import duckdb

from .config import DB_PATH, SYNTHETIC_DIR
from .schema import CORE_TABLES
from .seed_data import generate_synthetic_data


EXPECTED_TABLE_COLUMNS = {
    "trade_flow": {"trade_id", "branch_id", "trade_date", "trade_amount", "calculated_commission"},
    "commission_calc": {"commission_id", "trade_id", "net_commission", "revenue_amount"},
    "revenue_subledger": {"subledger_id", "source_doc_id", "period", "branch_id", "biz_line_id", "amount"},
    "gl_journal": {"journal_id", "journal_line_id", "period", "source_doc_id", "account_code", "amount"},
    "expense_pool": {"pool_id", "period", "cost_type", "amount"},
    "allocation_rule": {"rule_id", "period", "cost_type", "allocation_basis"},
    "allocation_driver": {"driver_id", "period", "rule_id", "target_id", "driver_value"},
    "allocation_result": {"allocation_id", "period", "pool_id", "rule_id", "allocated_amount"},
}


def table_exists(con: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    result = con.execute(
        """
        SELECT count(*)
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = ?
        """,
        [table_name],
    ).fetchone()
    return bool(result and result[0] > 0)


def get_table_columns(con: duckdb.DuckDBPyConnection, table_name: str) -> set[str]:
    if not table_exists(con, table_name):
        return set()
    rows = con.execute(f"PRAGMA table_info('{table_name}')").fetchall()
    return {str(row[1]) for row in rows}


def database_exists_and_valid(db_path: str | Path = DB_PATH) -> bool:
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            for table_name, expected_columns in EXPECTED_TABLE_COLUMNS.items():
                if not table_exists(con, table_name):
                    return False
                existing_columns = get_table_columns(con, table_name)
                if not expected_columns.issubset(existing_columns):
                    return False
            counts = con.execute(
                "SELECT (SELECT count(*) FROM trade_flow), (SELECT count(*) FROM gl_journal)"
            ).fetchone()
            return bool(counts and counts[0] > 0 and counts[1] > 0)
        finally:
            con.close()
    except Exception:
        return False


def init_duckdb(db_path: str | Path = DB_PATH) -> Path:
    db_path = Path(db_path)
    generate_synthetic_data()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        for table in CORE_TABLES:
            csv_path = SYNTHETIC_DIR / f"{table}.csv"
            if csv_path.exists():
                con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=True)", [str(csv_path)])
    finally:
        con.close()
    from .validation import detect_all_reconciliation_exceptions

    detect_all_reconciliation_exceptions(write_to_db=True)
    return db_path


def rebuild_database(db_path: str | Path = DB_PATH) -> Path:
    db_path = Path(db_path)
    for candidate in (db_path, Path(f"{db_path}.wal")):
        if candidate.exists():
            candidate.unlink()
    return init_duckdb(db_path)


def ensure_database_initialized(force_rebuild: bool = False, db_path: str | Path = DB_PATH) -> Path:
    db_path = Path(db_path)
    if force_rebuild:
        return rebuild_database(db_path)
    if database_exists_and_valid(db_path):
        return db_path
    return rebuild_database(db_path)


def load_synthetic_data_to_duckdb(db_path: str | Path = DB_PATH) -> Path:
    return ensure_database_initialized(force_rebuild=False, db_path=db_path)


def get_connection(db_path: str | Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    ensure_database_initialized(force_rebuild=False, db_path=db_path)
    return duckdb.connect(str(db_path))


if __name__ == "__main__":
    print(load_synthetic_data_to_duckdb())
