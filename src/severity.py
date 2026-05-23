from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .config import DB_PATH, OUTPUT_DIR
from .validation import detect_all_reconciliation_exceptions


HIGH_RISK_TYPES = {
    "UPSTREAM_SUBLEDGER_DIFF",
    "SUBLEDGER_GL_SHORT_POSTING",
    "SUBLEDGER_GL_DUPLICATE_POSTING",
}

MEDIUM_RISK_TYPES = {
    "ALLOCATION_NOT_FULLY_DISTRIBUTED",
    "WRONG_RULE_VERSION",
    "MISSING_ALLOCATION_DRIVER",
}


def _exceptions(period: str | None = None) -> pd.DataFrame:
    df = detect_all_reconciliation_exceptions(write_to_db=False)
    if period:
        df = df[df["period"] == period].copy()
    return df.reset_index(drop=True)


def _grade_row(row: pd.Series) -> dict:
    exception_type = str(row["exception_type"])
    scenario = str(row["scenario"])
    diff_amount = abs(float(row["diff_amount"]))
    source_table = str(row["source_table"])
    target_table = str(row["target_table"])
    affected_layer = f"{source_table} -> {target_table}"

    if exception_type in HIGH_RISK_TYPES or diff_amount >= 1_000_000:
        severity = "HIGH"
        financial_impact_level = "可能影响收入确认、总账凭证或财务报表金额"
        priority = "T+0 优先处理"
        manual = True
        reason = "差异影响收入确认或总账链路，且金额超过 100 万元阈值。"
    elif scenario == "ALLOCATION" or exception_type in MEDIUM_RISK_TYPES:
        severity = "MEDIUM"
        financial_impact_level = "影响费用分摊、营业部盈利和管理会计分析"
        priority = "本月关账前处理"
        manual = True
        reason = "差异主要影响管理会计分摊口径，对总账直接影响有限但会影响经营分析。"
    else:
        severity = "LOW"
        financial_impact_level = "主要影响维度映射或展示口径"
        priority = "纳入月结问题清单跟踪"
        manual = diff_amount >= 100_000
        reason = "差异偏向维度或科目映射问题，可按影响金额和批次重要性排期处理。"

    return {
        "exception_id": str(row["exception_id"]),
        "period": str(row["period"]),
        "severity": severity,
        "severity_reason": reason,
        "financial_impact_level": financial_impact_level,
        "affected_layer": affected_layer,
        "recommended_priority": priority,
        "requires_manual_review": bool(manual),
    }


def grade_exception(exception_id: str) -> dict:
    df = _exceptions()
    match = df[df["exception_id"].astype(str) == exception_id]
    if match.empty:
        raise ValueError(f"Unknown exception_id: {exception_id}")
    return _grade_row(match.iloc[0])


def grade_all_exceptions(period: str | None = None, write_to_db: bool = True) -> pd.DataFrame:
    df = _exceptions(period)
    rows = [_grade_row(row) for _, row in df.iterrows()]
    out = pd.DataFrame(rows)
    if out.empty:
        out = pd.DataFrame(
            columns=[
                "exception_id",
                "period",
                "severity",
                "severity_reason",
                "financial_impact_level",
                "affected_layer",
                "recommended_priority",
                "requires_manual_review",
            ]
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_DIR / "exception_severity.csv", index=False)
    if write_to_db and Path(DB_PATH).exists():
        con = duckdb.connect(str(DB_PATH))
        try:
            con.execute("CREATE OR REPLACE TABLE reconciliation_exception_severity AS SELECT * FROM out")
        finally:
            con.close()
    return out
