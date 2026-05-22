from src.db import load_synthetic_data_to_duckdb
from src.seed_data import generate_synthetic_data
from src.validation import (
    detect_reconciliation_exceptions,
    generate_root_cause_report,
    reconcile_allocation_result,
    reconcile_commission_to_gl,
)


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_normal_batch_reconciles():
    rec = reconcile_commission_to_gl("2025-01")
    normal = rec[(rec["branch_id"] == "B001") & (rec["batch_id"].str.contains("COMM_202501_B001"))].iloc[0]
    assert abs(normal["commission_to_subledger_diff"]) < 1
    assert abs(normal["subledger_to_gl_diff"]) < 1


def test_seeded_commission_exceptions_detected():
    mar = detect_reconciliation_exceptions("2025-03")
    apr = detect_reconciliation_exceptions("2025-04")
    may = detect_reconciliation_exceptions("2025-05")
    sep = detect_reconciliation_exceptions("2025-09")
    types = set(mar["exception_type"]) | set(apr["exception_type"]) | set(may["exception_type"]) | set(sep["exception_type"])
    assert "UPSTREAM_SUBLEDGER_DIFF" in types
    assert "SUBLEDGER_GL_SHORT_POSTING" in types
    assert "SUBLEDGER_GL_DUPLICATE_POSTING" in types
    assert "ACCOUNT_MAPPING_ERROR" in types


def test_allocation_ratio_and_amount_exceptions_detected():
    june = detect_reconciliation_exceptions("2025-06")
    assert "ALLOCATION_NOT_FULLY_DISTRIBUTED" in set(june["exception_type"])
    alloc = reconcile_allocation_result("2025-06")
    assert (alloc["allocation_ratio"] < 0.999).any()


def test_rule_version_and_driver_missing_detected():
    july = detect_reconciliation_exceptions("2025-07")
    aug = detect_reconciliation_exceptions("2025-08")
    assert "WRONG_RULE_VERSION" in set(july["exception_type"])
    assert "MISSING_ALLOCATION_DRIVER" in set(aug["exception_type"])


def test_root_cause_report_contains_required_sections():
    exceptions = detect_reconciliation_exceptions("2025-03")
    report = generate_root_cause_report(exceptions.iloc[0]["exception_id"])
    assert "异常金额" in report
    assert "差异原因" in report
    assert "证据链" in report
    assert "建议动作" in report
