from src.db import load_synthetic_data_to_duckdb
from src.seed_data import generate_synthetic_data
from src.severity import grade_all_exceptions, grade_exception
from src.validation import detect_reconciliation_exceptions


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_high_amount_revenue_exception_is_high():
    exceptions = detect_reconciliation_exceptions("2025-03")
    exception_id = exceptions[exceptions["scenario"] == "COMMISSION_TO_GL"].iloc[0]["exception_id"]
    grade = grade_exception(exception_id)
    assert grade["severity"] == "HIGH"
    assert grade["severity_reason"]


def test_allocation_rule_or_driver_exception_is_medium():
    exceptions = detect_reconciliation_exceptions("2025-07")
    exception_id = exceptions[exceptions["exception_type"] == "WRONG_RULE_VERSION"].iloc[0]["exception_id"]
    grade = grade_exception(exception_id)
    assert grade["severity"] == "MEDIUM"
    assert grade["severity_reason"]


def test_grade_all_exceptions_outputs_rows():
    grades = grade_all_exceptions("2025-06")
    assert not grades.empty
    assert {"exception_id", "severity", "severity_reason"}.issubset(grades.columns)
