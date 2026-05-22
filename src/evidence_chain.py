from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from .config import DB_PATH
from .db import load_synthetic_data_to_duckdb
from .validation import detect_all_reconciliation_exceptions


def _table(table: str) -> pd.DataFrame:
    if not Path(DB_PATH).exists():
        load_synthetic_data_to_duckdb()
    con = duckdb.connect(str(DB_PATH))
    try:
        return con.execute(f"SELECT * FROM {table}").fetchdf()
    finally:
        con.close()


def _exception(exception_id: str) -> pd.Series:
    exceptions = detect_all_reconciliation_exceptions()
    match = exceptions[exceptions["exception_id"] == exception_id]
    if match.empty:
        raise ValueError(f"Unknown exception_id: {exception_id}")
    return match.iloc[0]


def _case(exception_type: str) -> tuple[str, str]:
    cases = _table("root_cause_case")
    match = cases[cases["exception_type"] == exception_type]
    if match.empty:
        return "需复核源系统、子账、总账或分摊链路的批次日志。", "复核批次日志，修正数据后重新执行月结检查。"
    row = match.iloc[0]
    return str(row["root_cause"]), str(row["recommended_action"])


def _amount_sum(df: pd.DataFrame, column: str) -> float:
    if df.empty or column not in df:
        return 0.0
    return round(float(df[column].fillna(0).sum()), 2)


def _ids(df: pd.DataFrame, column: str, limit: int = 5) -> list[str]:
    if df.empty or column not in df:
        return []
    return [str(v) for v in df[column].dropna().astype(str).head(limit).tolist()]


def _parse_batch(text: str) -> str | None:
    match = re.search(r"(COMM_\d{6}_B\d{3}|WEALTH_\d{6})", text)
    return match.group(1) if match else None


def _parse_pool(text: str) -> str | None:
    match = re.search(r"(POOL\d+)", text)
    return match.group(1) if match else None


def build_commission_evidence_chain(exception_id: str) -> dict[str, Any]:
    exc = _exception(exception_id)
    period = str(exc["period"])
    batch_id = _parse_batch(str(exc["suspected_reason"]))
    subledger = _table("revenue_subledger")
    gl = _table("gl_journal")
    trades = _table("trade_flow")
    commission = _table("commission_calc")
    gl["account_code"] = gl["account_code"].astype(str)
    subledger["account_code"] = subledger["account_code"].astype(str)

    if not batch_id and str(exc["exception_type"]) == "ACCOUNT_MAPPING_ERROR":
        candidates = subledger[
            (subledger["period"] == period)
            & (subledger["biz_line_id"] == "WEALTH")
            & (subledger["account_code"] == "6021")
        ]
        batch_id = str(candidates["recognition_batch_id"].iloc[0]) if not candidates.empty else None

    trade_rows = trades[trades["clearing_batch_id"] == batch_id] if batch_id else trades.iloc[0:0]
    commission_rows = commission[commission["calc_batch_id"] == batch_id] if batch_id else commission.iloc[0:0]
    sub_rows = subledger[subledger["recognition_batch_id"] == batch_id] if batch_id else subledger.iloc[0:0]
    gl_rows = gl[
        (gl["batch_id"] == batch_id)
        & (gl["dr_cr"] == "CR")
        & (gl["account_code"].isin(["6021", "6022"]))
    ] if batch_id else gl.iloc[0:0]

    root_cause, action = _case(str(exc["exception_type"]))
    breakpoint = {
        "UPSTREAM_SUBLEDGER_DIFF": "commission_calc -> revenue_subledger",
        "SUBLEDGER_GL_SHORT_POSTING": "revenue_subledger -> gl_journal",
        "SUBLEDGER_GL_DUPLICATE_POSTING": "revenue_subledger -> gl_journal",
        "ACCOUNT_MAPPING_ERROR": "revenue_subledger -> chart_of_accounts",
    }.get(str(exc["exception_type"]), "commission_to_gl")

    return {
        "exception_id": str(exc["exception_id"]),
        "scenario": str(exc["scenario"]),
        "exception_type": str(exc["exception_type"]),
        "period": period,
        "diff_amount": round(float(exc["diff_amount"]), 2),
        "trace_key": batch_id or "",
        "trace_steps": [
            {
                "step": 1,
                "layer": "trade_flow",
                "description": "交易流水汇总",
                "record_count": int(len(trade_rows)),
                "amount": _amount_sum(trade_rows, "calculated_commission"),
                "key_ids": _ids(trade_rows, "trade_id"),
            },
            {
                "step": 2,
                "layer": "commission_calc",
                "description": "佣金计算结果",
                "record_count": int(len(commission_rows)),
                "amount": _amount_sum(commission_rows, "revenue_amount"),
                "key_ids": _ids(commission_rows, "commission_id"),
            },
            {
                "step": 3,
                "layer": "revenue_subledger",
                "description": "收入子账确认",
                "record_count": int(len(sub_rows)),
                "amount": _amount_sum(sub_rows, "amount"),
                "key_ids": _ids(sub_rows, "subledger_id"),
            },
            {
                "step": 4,
                "layer": "gl_journal",
                "description": "总账凭证入账",
                "record_count": int(len(gl_rows)),
                "amount": _amount_sum(gl_rows, "amount"),
                "key_ids": _ids(gl_rows, "journal_id"),
            },
        ],
        "breakpoint": breakpoint,
        "root_cause": root_cause,
        "recommended_action": action,
    }


def build_allocation_evidence_chain(exception_id: str) -> dict[str, Any]:
    exc = _exception(exception_id)
    period = str(exc["period"])
    pool_id = _parse_pool(str(exc["suspected_reason"]))
    pools = _table("expense_pool")
    rules = _table("allocation_rule")
    drivers = _table("allocation_driver")
    results = _table("allocation_result")

    pool_rows = pools[pools["pool_id"] == pool_id] if pool_id else pools.iloc[0:0]
    result_rows = results[results["pool_id"] == pool_id] if pool_id else results.iloc[0:0]
    rule_ids = result_rows["rule_id"].dropna().astype(str).unique().tolist() if not result_rows.empty else []
    rule_rows = rules[rules["rule_id"].astype(str).isin(rule_ids)] if rule_ids else rules.iloc[0:0]
    driver_rows = drivers[drivers["rule_id"].astype(str).isin(rule_ids)] if rule_ids else drivers.iloc[0:0]

    root_cause, action = _case(str(exc["exception_type"]))
    breakpoint = {
        "ALLOCATION_NOT_FULLY_DISTRIBUTED": "expense_pool -> allocation_result",
        "WRONG_RULE_VERSION": "allocation_rule -> allocation_result",
        "MISSING_ALLOCATION_DRIVER": "allocation_driver -> allocation_result",
    }.get(str(exc["exception_type"]), "allocation")

    return {
        "exception_id": str(exc["exception_id"]),
        "scenario": str(exc["scenario"]),
        "exception_type": str(exc["exception_type"]),
        "period": period,
        "diff_amount": round(float(exc["diff_amount"]), 2),
        "trace_key": pool_id or "",
        "trace_steps": [
            {
                "step": 1,
                "layer": "expense_pool",
                "description": "费用池金额",
                "record_count": int(len(pool_rows)),
                "amount": _amount_sum(pool_rows, "amount"),
                "key_ids": _ids(pool_rows, "pool_id"),
            },
            {
                "step": 2,
                "layer": "allocation_rule",
                "description": "分摊规则版本",
                "record_count": int(len(rule_rows)),
                "amount": 0.0,
                "key_ids": _ids(rule_rows, "rule_id"),
            },
            {
                "step": 3,
                "layer": "allocation_driver",
                "description": "分摊因子",
                "record_count": int(len(driver_rows)),
                "amount": _amount_sum(driver_rows, "driver_value"),
                "key_ids": _ids(driver_rows, "driver_id"),
            },
            {
                "step": 4,
                "layer": "allocation_result",
                "description": "分摊结果",
                "record_count": int(len(result_rows)),
                "amount": _amount_sum(result_rows, "allocated_amount"),
                "key_ids": _ids(result_rows, "allocation_id"),
            },
        ],
        "breakpoint": breakpoint,
        "root_cause": root_cause,
        "recommended_action": action,
    }


def build_evidence_chain(exception_id: str) -> dict[str, Any]:
    exc = _exception(exception_id)
    if str(exc["scenario"]) == "ALLOCATION":
        return build_allocation_evidence_chain(exception_id)
    return build_commission_evidence_chain(exception_id)


def format_evidence_chain_markdown(exception_id: str) -> str:
    chain = build_evidence_chain(exception_id)
    rows = "\n".join(
        f"| {s['step']} | {s['layer']} | {s['description']} | {s['record_count']} | {s['amount']:,.2f} | {', '.join(s['key_ids'])} |"
        for s in chain["trace_steps"]
    )
    return f"""# 异常证据链

异常编号：{chain['exception_id']}

期间：{chain['period']}

场景：{chain['scenario']}

异常类型：{chain['exception_type']}

差异金额：{chain['diff_amount']:,.2f} 元

追踪键：{chain['trace_key']}

| 步骤 | 层级 | 说明 | 记录数 | 金额 | 关键ID |
|---:|---|---|---:|---:|---|
{rows}

差异发生点：{chain['breakpoint']}

根因：{chain['root_cause']}

建议动作：{chain['recommended_action']}
"""
