import pandas as pd

from src.db import load_synthetic_data_to_duckdb
from src.export_validated_data import export_all, export_validation_summary
from src.seed_data import generate_synthetic_data


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_validated_exports_exist_and_are_non_empty():
    paths = export_all("2025-03")
    for path in paths:
        assert path.exists()
        df = pd.read_csv(path)
        assert not df.empty


def test_validated_exports_contain_status_and_summary_counts():
    revenue_path, expense_path, _ = export_all("2025-06")
    assert "validation_status" in pd.read_csv(revenue_path).columns
    assert "validation_status" in pd.read_csv(expense_path).columns
    summary = pd.read_csv(export_validation_summary("2025-06"))
    assert "exception_count" in summary.columns
    assert summary["exception_count"].sum() > 0
