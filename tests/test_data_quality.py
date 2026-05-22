from pathlib import Path

from src.config import OUTPUT_DIR
from src.data_quality import run_data_quality_checks


def test_data_quality_report_outputs():
    report = run_data_quality_checks()
    assert report["status"] in {"PASS", "WARNING"}
    assert report["row_counts"]["trade_flow"] > 0
    assert Path(OUTPUT_DIR / "data_quality_report.md").exists()
    assert Path(OUTPUT_DIR / "data_quality_report.json").exists()
