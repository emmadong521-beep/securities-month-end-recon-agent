from src.case_matcher import match_root_cause_cases
from src.db import load_synthetic_data_to_duckdb
from src.seed_data import generate_synthetic_data
from src.validation import detect_reconciliation_exceptions


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_each_demo_exception_matches_case():
    sample_periods = ["2025-03", "2025-06", "2025-07", "2025-08"]
    for period in sample_periods:
        exception_id = detect_reconciliation_exceptions(period).iloc[0]["exception_id"]
        matches = match_root_cause_cases(exception_id)
        assert matches
        assert matches[0]["match_score"] > 0
        assert matches[0]["match_reason"]


def test_top_k_is_respected():
    exception_id = detect_reconciliation_exceptions("2025-03").iloc[0]["exception_id"]
    matches = match_root_cause_cases(exception_id, top_k=1)
    assert len(matches) == 1
