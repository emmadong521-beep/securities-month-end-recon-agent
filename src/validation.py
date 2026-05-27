from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .config import DB_PATH, OUTPUT_DIR
from .db import EXPECTED_TABLE_COLUMNS, database_exists_and_valid, ensure_database_initialized, get_connection


def _table(table: str) -> pd.DataFrame:
    if not database_exists_and_valid(DB_PATH):
        ensure_database_initialized(force_rebuild=True)
    con = get_connection(DB_PATH)
    try:
        df = con.execute(f"SELECT * FROM {table}").fetchdf()
    finally:
        con.close()
    expected_columns = EXPECTED_TABLE_COLUMNS.get(table)
    if expected_columns:
        missing_columns = sorted(expected_columns.difference(df.columns))
        if missing_columns:
            raise RuntimeError(
                f"DuckDB table '{table}' is missing required columns: {missing_columns}. "
                "Run ensure_database_initialized(force_rebuild=True) to rebuild the demo database."
            )
    return df


def reconcile_commission_to_gl(period: str) -> pd.DataFrame:
    commission = _table("commission_calc")
    trades = _table("trade_flow")[["trade_id", "branch_id"]]
    sub = _table("revenue_subledger")
    gl = _table("gl_journal")
    sub["account_code"] = sub["account_code"].astype(str)
    gl["account_code"] = gl["account_code"].astype(str)
    commission = commission.merge(trades, on="trade_id", how="left")
    commission["period"] = commission["calc_batch_id"].str.extract(r"COMM_(\d{6})_")[0].str.replace(r"(\d{4})(\d{2})", r"\1-\2", regex=True)
    c = commission[(commission["period"] == period) & (commission["status"] == "POSTED")]
    c = c.groupby(["period", "branch_id", "calc_batch_id"], as_index=False)["revenue_amount"].sum().rename(columns={"calc_batch_id": "batch_id", "revenue_amount": "commission_amount"})
    s = sub[(sub["period"] == period) & (sub["source_system"] == "COMMISSION_SYSTEM") & (sub["status"] == "RECOGNIZED")]
    s = s.groupby(["period", "branch_id", "recognition_batch_id"], as_index=False)["amount"].sum().rename(columns={"recognition_batch_id": "batch_id", "amount": "subledger_amount"})
    g = gl[(gl["period"] == period) & (gl["source_system"] == "REVENUE_SUBLEDGER") & (gl["account_code"] == "6021") & (gl["dr_cr"] == "CR") & (gl["biz_line_id"] == "BROKERAGE")]
    g = g.groupby(["period", "branch_id", "batch_id"], as_index=False)["amount"].sum().rename(columns={"amount": "gl_amount"})
    out = c.merge(s, on=["period", "branch_id", "batch_id"], how="outer").merge(g, on=["period", "branch_id", "batch_id"], how="outer")
    for col in ["commission_amount", "subledger_amount", "gl_amount"]:
        out[col] = out[col].fillna(0.0).astype(float)
    out["commission_to_subledger_diff"] = out["commission_amount"] - out["subledger_amount"]
    out["subledger_to_gl_diff"] = out["subledger_amount"] - out["gl_amount"]
    out["status"] = np.where((out["commission_to_subledger_diff"].abs() < 1) & (out["subledger_to_gl_diff"].abs() < 1), "MATCHED", "EXCEPTION")
    return out.sort_values(["period", "branch_id", "batch_id"]).reset_index(drop=True)


def reconcile_allocation_result(period: str) -> pd.DataFrame:
    pool = _table("expense_pool")
    alloc = _table("allocation_result")
    driver = _table("allocation_driver")
    rules = _table("allocation_rule")
    pool_p = pool[pool["period"] == period]
    alloc_p = alloc[alloc["period"] == period]
    by_pool = alloc_p.groupby("pool_id", as_index=False).agg(allocated_amount=("allocated_amount", "sum"), allocation_ratio=("allocation_ratio", "sum"), driver_count=("target_id", "nunique"))
    out = pool_p.merge(by_pool, on="pool_id", how="left")
    out[["allocated_amount", "allocation_ratio", "driver_count"]] = out[["allocated_amount", "allocation_ratio", "driver_count"]].fillna(0)
    out["diff_amount"] = out["amount"] - out["allocated_amount"]
    used_rules = alloc_p[["pool_id", "rule_id"]].drop_duplicates().merge(rules[["rule_id", "is_active", "rule_version"]], on="rule_id", how="left")
    out = out.merge(used_rules, on="pool_id", how="left")
    expected_targets = _table("branch_master").query("status == 'ACTIVE'")["branch_id"].nunique()
    out["expected_driver_count"] = expected_targets
    out["driver_missing_count"] = expected_targets - out["driver_count"]
    out["status"] = np.where((out["diff_amount"].abs() < 1) & (out["allocation_ratio"].sub(1).abs() < 0.0001) & (out["is_active"].fillna(True)) & (out["driver_missing_count"] <= 0), "MATCHED", "EXCEPTION")
    return out.sort_values("pool_id").reset_index(drop=True)


def _write_exceptions_to_db(df: pd.DataFrame) -> None:
    if Path(DB_PATH).exists():
        con = duckdb.connect(str(DB_PATH))
        try:
            con.execute("CREATE OR REPLACE TABLE reconciliation_exception AS SELECT * FROM df")
        finally:
            con.close()


def detect_reconciliation_exceptions(period: str, write_to_db: bool = False) -> pd.DataFrame:
    rows = []
    idx = 1
    rec = reconcile_commission_to_gl(period)
    for _, r in rec.iterrows():
        if abs(r["commission_to_subledger_diff"]) >= 1:
            diff = float(r["commission_to_subledger_diff"])
            rows.append({
                "exception_id": f"EXC_{period.replace('-', '')}_{idx:03d}",
                "period": period,
                "scenario": "COMMISSION_TO_GL",
                "exception_type": "UPSTREAM_SUBLEDGER_DIFF",
                "severity": "HIGH",
                "source_table": "commission_calc",
                "target_table": "revenue_subledger",
                "source_amount": float(r["commission_amount"]),
                "target_amount": float(r["subledger_amount"]),
                "diff_amount": diff,
                "diff_rate": diff / max(float(r["commission_amount"]), 1.0),
                "suspected_reason": f"批次 {r['batch_id']} 佣金计算已完成但收入子账缺失或少确认",
                "status": "OPEN",
            })
            idx += 1
        if abs(r["subledger_to_gl_diff"]) >= 1:
            diff = float(r["subledger_to_gl_diff"])
            etype = "SUBLEDGER_GL_SHORT_POSTING" if diff > 0 else "SUBLEDGER_GL_DUPLICATE_POSTING"
            reason = "总账凭证少入账，疑似凭证生成或接口失败" if diff > 0 else "总账金额高于子账，疑似重复推送凭证批次"
            rows.append({
                "exception_id": f"EXC_{period.replace('-', '')}_{idx:03d}",
                "period": period,
                "scenario": "COMMISSION_TO_GL",
                "exception_type": etype,
                "severity": "HIGH",
                "source_table": "revenue_subledger",
                "target_table": "gl_journal",
                "source_amount": float(r["subledger_amount"]),
                "target_amount": float(r["gl_amount"]),
                "diff_amount": diff,
                "diff_rate": diff / max(float(r["subledger_amount"]), 1.0),
                "suspected_reason": f"批次 {r['batch_id']} {reason}",
                "status": "OPEN",
            })
            idx += 1

    sub = _table("revenue_subledger")
    sub["account_code"] = sub["account_code"].astype(str)
    mapping = sub[(sub["period"] == period) & (sub["biz_line_id"] == "WEALTH") & (sub["account_code"] == "6021")]
    for _, r in mapping.iterrows():
        rows.append({
            "exception_id": f"EXC_{period.replace('-', '')}_{idx:03d}",
            "period": period,
            "scenario": "COMMISSION_TO_GL",
            "exception_type": "ACCOUNT_MAPPING_ERROR",
            "severity": "MEDIUM",
            "source_table": "revenue_subledger",
            "target_table": "chart_of_accounts",
            "source_amount": float(r["amount"]),
            "target_amount": 0.0,
            "diff_amount": float(r["amount"]),
            "diff_rate": 1.0,
            "suspected_reason": f"财富管理单据 {r['source_doc_id']} 误入经纪佣金科目6021，应映射至6022",
            "status": "OPEN",
        })
        idx += 1

    alloc = reconcile_allocation_result(period)
    for _, r in alloc.iterrows():
        if abs(float(r["diff_amount"])) >= 1 or abs(float(r["allocation_ratio"]) - 1) > 0.0001:
            rows.append({
                "exception_id": f"EXC_{period.replace('-', '')}_{idx:03d}",
                "period": period,
                "scenario": "ALLOCATION",
                "exception_type": "ALLOCATION_NOT_FULLY_DISTRIBUTED",
                "severity": "HIGH",
                "source_table": "expense_pool",
                "target_table": "allocation_result",
                "source_amount": float(r["amount"]),
                "target_amount": float(r["allocated_amount"]),
                "diff_amount": float(r["diff_amount"]),
                "diff_rate": float(r["diff_amount"]) / max(float(r["amount"]), 1.0),
                "suspected_reason": f"费用池 {r['pool_id']} 分摊比例合计为 {float(r['allocation_ratio']):.2%}",
                "status": "OPEN",
            })
            idx += 1
        if not bool(r.get("is_active", True)):
            rows.append({
                "exception_id": f"EXC_{period.replace('-', '')}_{idx:03d}",
                "period": period,
                "scenario": "ALLOCATION",
                "exception_type": "WRONG_RULE_VERSION",
                "severity": "MEDIUM",
                "source_table": "allocation_rule",
                "target_table": "allocation_result",
                "source_amount": float(r["amount"]),
                "target_amount": float(r["allocated_amount"]),
                "diff_amount": 0.0,
                "diff_rate": 0.0,
                "suspected_reason": f"费用池 {r['pool_id']} 使用了非激活规则 {r['rule_id']}",
                "status": "OPEN",
            })
            idx += 1
        if int(r.get("driver_missing_count", 0)) > 0:
            rows.append({
                "exception_id": f"EXC_{period.replace('-', '')}_{idx:03d}",
                "period": period,
                "scenario": "ALLOCATION",
                "exception_type": "MISSING_ALLOCATION_DRIVER",
                "severity": "MEDIUM",
                "source_table": "allocation_driver",
                "target_table": "allocation_result",
                "source_amount": float(r["amount"]),
                "target_amount": float(r["allocated_amount"]),
                "diff_amount": float(r["diff_amount"]),
                "diff_rate": float(r["diff_amount"]) / max(float(r["amount"]), 1.0),
                "suspected_reason": f"费用池 {r['pool_id']} 缺少 {int(r['driver_missing_count'])} 个目标分摊因子",
                "status": "OPEN",
            })
            idx += 1

    df = pd.DataFrame(rows)
    if df.empty:
        df = pd.DataFrame(columns=["exception_id", "period", "scenario", "exception_type", "severity", "source_table", "target_table", "source_amount", "target_amount", "diff_amount", "diff_rate", "suspected_reason", "status"])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / f"reconciliation_exceptions_{period}.csv", index=False)
    if write_to_db:
        _write_exceptions_to_db(df)
    return df


def _all_exceptions() -> pd.DataFrame:
    return detect_all_reconciliation_exceptions(write_to_db=False)


def detect_all_reconciliation_exceptions(write_to_db: bool = True) -> pd.DataFrame:
    frames = [detect_reconciliation_exceptions(f"2025-{m:02d}", write_to_db=False) for m in range(1, 13)]
    df = pd.concat(frames, ignore_index=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_DIR / "reconciliation_exceptions_all.csv", index=False)
    if write_to_db:
        _write_exceptions_to_db(df)
    return df


def explain_exception_mock(exception_id: str) -> str:
    exceptions = _all_exceptions()
    match = exceptions[exceptions["exception_id"] == exception_id]
    if match.empty:
        return f"未找到异常 {exception_id}。"
    r = match.iloc[0]
    return (
        f"异常 {r['exception_id']} 属于 {r['scenario']} / {r['exception_type']}。"
        f"源表金额 {float(r['source_amount']) / 10000:,.2f} 万元，目标表金额 {float(r['target_amount']) / 10000:,.2f} 万元，"
        f"差异 {float(r['diff_amount']) / 10000:,.2f} 万元。初步原因：{r['suspected_reason']}。"
    )


def generate_root_cause_report(exception_id: str) -> str:
    exceptions = _all_exceptions()
    cases = _table("root_cause_case")
    match = exceptions[exceptions["exception_id"] == exception_id]
    if match.empty:
        return f"# 异常归因报告\n\n未找到异常 {exception_id}。"
    r = match.iloc[0]
    case = cases[cases["exception_type"] == r["exception_type"]]
    if case.empty:
        root_cause = r["suspected_reason"]
        evidence = f"{r['source_table']} -> {r['target_table']}"
        action = "请财务运营人员复核数据链路和接口日志。"
    else:
        c = case.iloc[0]
        root_cause = c["root_cause"]
        evidence = c["evidence_pattern"]
        action = c["recommended_action"]
    return f"""# 异常归因报告

## 异常金额
期间：{r['period']}

源表金额：{float(r['source_amount']) / 10000:,.2f} 万元

目标表金额：{float(r['target_amount']) / 10000:,.2f} 万元

差异金额：{float(r['diff_amount']) / 10000:,.2f} 万元

## 差异原因
{root_cause}

## 证据链
{r['source_table']} -> {r['target_table']}；{evidence}；系统提示：{r['suspected_reason']}

## 建议动作
{action}
"""


def export_root_cause_report(exception_id: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"root_cause_report_{exception_id}.md"
    output_path.write_text(generate_root_cause_report(exception_id), encoding="utf-8")
    return output_path
