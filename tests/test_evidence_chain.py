from src.db import load_synthetic_data_to_duckdb
from src.evidence_chain import build_evidence_chain
from src.seed_data import generate_synthetic_data
from src.validation import detect_all_reconciliation_exceptions


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_each_exception_has_evidence_chain():
    exceptions = detect_all_reconciliation_exceptions()
    assert not exceptions.empty
    for exception_id in exceptions["exception_id"]:
        chain = build_evidence_chain(exception_id)
        assert chain["trace_steps"]
        assert "diff_amount" in chain
        assert chain["root_cause"]
        assert chain["recommended_action"]


def test_commission_chain_contains_required_layers():
    exceptions = detect_all_reconciliation_exceptions()
    exception_id = exceptions[exceptions["scenario"] == "COMMISSION_TO_GL"].iloc[0]["exception_id"]
    layers = {step["layer"] for step in build_evidence_chain(exception_id)["trace_steps"]}
    assert {"trade_flow", "commission_calc", "revenue_subledger", "gl_journal"}.issubset(layers)


def test_allocation_chain_contains_required_layers():
    exceptions = detect_all_reconciliation_exceptions()
    exception_id = exceptions[exceptions["scenario"] == "ALLOCATION"].iloc[0]["exception_id"]
    layers = {step["layer"] for step in build_evidence_chain(exception_id)["trace_steps"]}
    assert {"expense_pool", "allocation_rule", "allocation_driver", "allocation_result"}.issubset(layers)
