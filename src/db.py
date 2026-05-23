from __future__ import annotations

from pathlib import Path

import duckdb

from .config import DB_PATH, SYNTHETIC_DIR
from .schema import CORE_TABLES
from .seed_data import generate_synthetic_data


def database_exists_and_valid(db_path: str | Path = DB_PATH) -> bool:
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    required_tables = {
        "chart_of_accounts",
        "trade_flow",
        "commission_calc",
        "revenue_subledger",
        "gl_journal",
        "expense_pool",
        "allocation_result",
        "root_cause_case",
    }
    try:
        con = duckdb.connect(str(db_path), read_only=True)
        try:
            rows = con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
            ).fetchall()
            existing = {row[0] for row in rows}
            if not required_tables.issubset(existing):
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
    generate_synthetic_data()
    for suffix in ("", ".wal"):
        candidate = Path(f"{db_path}{suffix}") if suffix else db_path
        if candidate.exists():
            candidate.unlink()
    return init_duckdb(db_path)


def ensure_database_initialized(force_rebuild: bool = False, db_path: str | Path = DB_PATH) -> Path:
    db_path = Path(db_path)
    if force_rebuild:
        return rebuild_database(db_path)
    if not (SYNTHETIC_DIR / "trade_flow.csv").exists():
        generate_synthetic_data()
    if database_exists_and_valid(db_path):
        return db_path
    return init_duckdb(db_path)


def load_synthetic_data_to_duckdb(db_path: str | Path = DB_PATH) -> Path:
    return ensure_database_initialized(force_rebuild=False, db_path=db_path)


def get_connection(db_path: str | Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    ensure_database_initialized(force_rebuild=False, db_path=db_path)
    return duckdb.connect(str(db_path))


if __name__ == "__main__":
    print(load_synthetic_data_to_duckdb())
