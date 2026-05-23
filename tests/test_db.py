from src.config import DB_PATH
from src.db import database_exists_and_valid, ensure_database_initialized
from src.seed_data import generate_synthetic_data


def test_database_reuse_and_force_rebuild():
    generate_synthetic_data()
    path = ensure_database_initialized(force_rebuild=True)
    assert path == DB_PATH
    assert database_exists_and_valid()
    first_mtime = DB_PATH.stat().st_mtime
    ensure_database_initialized(force_rebuild=False)
    assert DB_PATH.stat().st_mtime == first_mtime
    ensure_database_initialized(force_rebuild=True)
    assert database_exists_and_valid()
