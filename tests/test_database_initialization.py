from pathlib import Path

import duckdb

from src.config import DB_PATH
from src.db import (
    EXPECTED_TABLE_COLUMNS,
    database_exists_and_valid,
    ensure_database_initialized,
    get_connection,
    get_table_columns,
    table_exists,
)
from src.validation import detect_all_reconciliation_exceptions


def test_database_exists_and_valid_for_normal_database():
    ensure_database_initialized(force_rebuild=True)

    assert database_exists_and_valid()


def test_ensure_database_initialized_rebuilds_when_duckdb_deleted():
    ensure_database_initialized(force_rebuild=True)
    DB_PATH.unlink()
    wal_path = Path(f"{DB_PATH}.wal")
    if wal_path.exists():
        wal_path.unlink()

    path = ensure_database_initialized()

    assert path.exists()
    assert database_exists_and_valid()


def test_database_exists_and_valid_rejects_missing_required_column(tmp_path):
    old_db = tmp_path / "old_schema.duckdb"
    con = duckdb.connect(str(old_db))
    try:
        for table_name, columns in EXPECTED_TABLE_COLUMNS.items():
            if table_name == "trade_flow":
                con.execute("CREATE TABLE trade_flow(trade_id VARCHAR)")
            else:
                column_sql = ", ".join(f"{column} VARCHAR" for column in sorted(columns))
                con.execute(f"CREATE TABLE {table_name}({column_sql})")
    finally:
        con.close()

    assert not database_exists_and_valid(old_db)


def test_force_rebuild_restores_trade_flow_required_columns():
    ensure_database_initialized(force_rebuild=True)
    con = get_connection()
    try:
        columns = get_table_columns(con, "trade_flow")
    finally:
        con.close()

    assert {"trade_id", "branch_id"}.issubset(columns)


def test_detect_all_reconciliation_exceptions_without_write_does_not_create_table():
    ensure_database_initialized(force_rebuild=True)
    con = get_connection()
    try:
        con.execute("DROP TABLE IF EXISTS reconciliation_exception")
    finally:
        con.close()

    df = detect_all_reconciliation_exceptions(write_to_db=False)

    con = get_connection()
    try:
        exists = table_exists(con, "reconciliation_exception")
    finally:
        con.close()
    assert not df.empty
    assert not exists


def test_detect_all_reconciliation_exceptions_with_write_creates_table():
    df = detect_all_reconciliation_exceptions(write_to_db=True)

    con = get_connection()
    try:
        exists = table_exists(con, "reconciliation_exception")
        count = con.execute("SELECT count(*) FROM reconciliation_exception").fetchone()[0]
    finally:
        con.close()
    assert exists
    assert count == len(df)
