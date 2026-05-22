from __future__ import annotations

from pathlib import Path

import duckdb

from .config import DB_PATH, SYNTHETIC_DIR
from .schema import CORE_TABLES
from .seed_data import generate_synthetic_data


def init_duckdb(db_path: str | Path = DB_PATH) -> Path:
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        for table in CORE_TABLES:
            csv_path = SYNTHETIC_DIR / f"{table}.csv"
            if csv_path.exists():
                con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto(?, header=True)", [str(csv_path)])
        return db_path
    finally:
        con.close()


def load_synthetic_data_to_duckdb(db_path: str | Path = DB_PATH) -> Path:
    if not SYNTHETIC_DIR.exists() or not (SYNTHETIC_DIR / "trade_flow.csv").exists():
        generate_synthetic_data()
    return init_duckdb(db_path)


def get_connection(db_path: str | Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    if not Path(db_path).exists():
        load_synthetic_data_to_duckdb(db_path)
    return duckdb.connect(str(db_path))


if __name__ == "__main__":
    print(load_synthetic_data_to_duckdb())
