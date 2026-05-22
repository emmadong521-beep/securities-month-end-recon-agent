from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .config import DB_PATH, OUTPUT_DIR
from .db import load_synthetic_data_to_duckdb
from .load_audit_report import load_audit_metrics
from .schema import CORE_TABLES
from .validation import detect_all_reconciliation_exceptions, reconcile_allocation_result, reconcile_commission_to_gl


PRIMARY_KEYS = {
    "chart_of_accounts": ["account_code"],
    "branch_master": ["branch_id"],
    "biz_line_master": ["biz_line_id"],
    "customer_master": ["customer_id"],
    "trade_flow": ["trade_id"],
    "commission_calc": ["commission_id"],
    "revenue_subledger": ["subledger_id"],
    "gl_journal": ["journal_line_id"],
    "expense_pool": ["pool_id"],
    "allocation_rule": ["rule_id"],
    "allocation_driver": ["driver_id"],
    "allocation_result": ["allocation_id"],
    "interface_batch_log": ["batch_id"],
    "root_cause_case": ["case_id"],
}

AMOUNT_FIELDS = {
    "trade_flow": ["trade_amount", "calculated_commission"],
    "commission_calc": ["gross_commission", "net_commission", "revenue_amount"],
    "revenue_subledger": ["amount"],
    "gl_journal": ["amount"],
    "gl_balance": ["debit_amount", "credit_amount", "ending_balance"],
    "expense_pool": ["amount"],
    "allocation_driver": ["driver_value", "driver_weight"],
    "allocation_result": ["allocated_amount", "allocation_ratio"],
}

EXPECTED_EXCEPTIONS = {
    "UPSTREAM_SUBLEDGER_DIFF",
    "SUBLEDGER_GL_SHORT_POSTING",
    "SUBLEDGER_GL_DUPLICATE_POSTING",
    "ACCOUNT_MAPPING_ERROR",
    "ALLOCATION_NOT_FULLY_DISTRIBUTED",
    "WRONG_RULE_VERSION",
    "MISSING_ALLOCATION_DRIVER",
}


def _table(con: duckdb.DuckDBPyConnection, table: str) -> pd.DataFrame:
    return con.execute(f"SELECT * FROM {table}").fetchdf()


def _status_from_checks(checks: list[dict[str, Any]]) -> str:
    if any(c["status"] == "FAIL" for c in checks):
        return "FAIL"
    if any(c["status"] == "WARNING" for c in checks):
        return "WARNING"
    return "PASS"


def _write_report(report: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "data_quality_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 数据质量自检报告",
        "",
        f"结论：{report['status']}",
        "",
        "## 表行数",
    ]
    for table, count in report["row_counts"].items():
        lines.append(f"- {table}: {count}")
    lines.extend(["", "## 检查项"])
    for check in report["checks"]:
        lines.append(f"- [{check['status']}] {check['name']}: {check['detail']}")
    lines.extend(["", "## 校准说明", report["calibration_note"], ""])
    (OUTPUT_DIR / "data_quality_report.md").write_text("\n".join(lines), encoding="utf-8")


def run_data_quality_checks() -> dict[str, Any]:
    load_synthetic_data_to_duckdb()
    con = duckdb.connect(str(DB_PATH))
    try:
        tables = {table: _table(con, table) for table in CORE_TABLES}
    finally:
        con.close()

    checks: list[dict[str, Any]] = []
    row_counts = {table: int(len(df)) for table, df in tables.items()}
    for table, count in row_counts.items():
        if table == "reconciliation_exception":
            continue
        checks.append({"name": f"{table} 非空", "status": "PASS" if count > 0 else "FAIL", "detail": f"{count} rows"})

    for table, keys in PRIMARY_KEYS.items():
        df = tables[table]
        duplicate_count = int(df.duplicated(keys).sum()) if all(k in df for k in keys) else len(df)
        checks.append({
            "name": f"{table} 主键唯一",
            "status": "PASS" if duplicate_count == 0 else "FAIL",
            "detail": f"duplicate_count={duplicate_count}, keys={keys}",
        })

    fk_checks = [
        ("commission_calc.trade_id", tables["commission_calc"]["trade_id"], tables["trade_flow"]["trade_id"]),
        ("trade_flow.customer_id", tables["trade_flow"]["customer_id"], tables["customer_master"]["customer_id"]),
        ("revenue_subledger.branch_id", tables["revenue_subledger"]["branch_id"], tables["branch_master"]["branch_id"]),
        ("gl_journal.source_doc_id", tables["gl_journal"]["source_doc_id"], tables["revenue_subledger"]["subledger_id"]),
        ("allocation_result.pool_id", tables["allocation_result"]["pool_id"], tables["expense_pool"]["pool_id"]),
        ("allocation_result.rule_id", tables["allocation_result"]["rule_id"], tables["allocation_rule"]["rule_id"]),
    ]
    for name, child, parent in fk_checks:
        missing = int((~child.dropna().isin(parent.dropna())).sum())
        checks.append({"name": f"{name} 外键完整", "status": "PASS" if missing == 0 else "FAIL", "detail": f"missing={missing}"})

    for table, fields in AMOUNT_FIELDS.items():
        df = tables[table]
        for field in fields:
            nulls = int(df[field].isna().sum())
            checks.append({"name": f"{table}.{field} 空值", "status": "PASS" if nulls == 0 else "FAIL", "detail": f"nulls={nulls}"})

    normal = reconcile_commission_to_gl("2025-01")
    normal_diff = float((normal["commission_to_subledger_diff"].abs() + normal["subledger_to_gl_diff"].abs()).max())
    checks.append({
        "name": "正常经纪佣金批次勾稽",
        "status": "PASS" if normal_diff < 1 else "FAIL",
        "detail": f"max_diff={normal_diff:.2f}",
    })
    alloc = reconcile_allocation_result("2025-01")
    alloc_diff = float(alloc["diff_amount"].abs().max())
    checks.append({
        "name": "正常费用分摊勾稽",
        "status": "PASS" if alloc_diff < 1 else "FAIL",
        "detail": f"max_diff={alloc_diff:.2f}",
    })

    exceptions = detect_all_reconciliation_exceptions()
    detected = set(exceptions["exception_type"].dropna().astype(str))
    missing_expected = sorted(EXPECTED_EXCEPTIONS - detected)
    checks.append({
        "name": "异常案例埋入与检测",
        "status": "PASS" if not missing_expected else "FAIL",
        "detail": f"detected={sorted(detected)}, missing={missing_expected}",
    })

    metrics = load_audit_metrics()
    synthetic_brokerage = float(tables["commission_calc"]["revenue_amount"].sum())
    public_brokerage = float(metrics["business_structure"]["代理买卖证券业务收入"])
    ratio = synthetic_brokerage / public_brokerage if public_brokerage else 0.0
    checks.append({
        "name": "公开指标规模校准",
        "status": "PASS" if 0.95 <= ratio <= 1.05 else "WARNING",
        "detail": f"synthetic_brokerage={synthetic_brokerage:,.2f}, public_metric={public_brokerage:,.2f}, ratio={ratio:.2%}",
    })

    report = {
        "status": _status_from_checks(checks),
        "row_counts": row_counts,
        "checks": checks,
        "calibration_note": "审计报告公开披露指标仅用于营业收入、手续费及佣金净收入、业务及管理费等汇总规模校准；客户、交易、凭证、分摊明细均为合成数据。",
    }
    _write_report(report)
    return report


if __name__ == "__main__":
    result = run_data_quality_checks()
    print(json.dumps({"status": result["status"], "output": str(OUTPUT_DIR / "data_quality_report.md")}, ensure_ascii=False, indent=2))
