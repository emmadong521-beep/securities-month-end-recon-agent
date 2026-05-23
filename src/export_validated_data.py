from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .config import DB_PATH, OUTPUT_DIR
from .db import ensure_database_initialized
from .severity import grade_all_exceptions
from .validation import detect_all_reconciliation_exceptions


def _table(table: str) -> pd.DataFrame:
    ensure_database_initialized()
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(f"SELECT * FROM {table}").fetchdf()
    finally:
        con.close()


def _exception_counts(period: str | None = None, scenario: str | None = None) -> pd.DataFrame:
    exceptions = detect_all_reconciliation_exceptions(write_to_db=False)
    if period:
        exceptions = exceptions[exceptions["period"] == period]
    if scenario:
        exceptions = exceptions[exceptions["scenario"] == scenario]
    if exceptions.empty:
        return pd.DataFrame(columns=["period", "exception_count"])
    return exceptions.groupby("period", as_index=False).agg(exception_count=("exception_id", "count"))


def export_validated_actual_revenue(period: str | None = None) -> Path:
    subledger = _table("revenue_subledger")
    if period:
        subledger = subledger[subledger["period"] == period].copy()
    df = (
        subledger[subledger["status"] == "RECOGNIZED"]
        .groupby(["period", "branch_id", "biz_line_id", "customer_type"], as_index=False)
        .agg(revenue_amount=("amount", "sum"))
    )
    df["product_type"] = "MIXED"
    counts = _exception_counts(period, "COMMISSION_TO_GL")
    df = df.merge(counts, on="period", how="left")
    df["exception_count"] = df["exception_count"].fillna(0).astype(int)
    df["validation_status"] = df["exception_count"].map(lambda value: "WARNING" if value else "PASS")
    df["source"] = "month_end_recon_agent.revenue_subledger"
    df = df[
        [
            "period",
            "branch_id",
            "biz_line_id",
            "customer_type",
            "product_type",
            "revenue_amount",
            "validation_status",
            "exception_count",
            "source",
        ]
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "validated_actual_revenue.csv"
    df.to_csv(path, index=False)
    return path


def export_validated_allocated_expense(period: str | None = None) -> Path:
    allocation = _table("allocation_result")
    pools = _table("expense_pool")[["pool_id", "cost_type"]]
    if period:
        allocation = allocation[allocation["period"] == period].copy()
    df = allocation.merge(pools, on="pool_id", how="left")
    df = (
        df.groupby(["period", "target_id", "cost_type"], as_index=False)
        .agg(allocated_amount=("allocated_amount", "sum"))
        .rename(columns={"target_id": "branch_id"})
    )
    df["biz_line_id"] = "ALLOCATED"
    counts = _exception_counts(period, "ALLOCATION")
    df = df.merge(counts, on="period", how="left")
    df["exception_count"] = df["exception_count"].fillna(0).astype(int)
    df["validation_status"] = df["exception_count"].map(lambda value: "WARNING" if value else "PASS")
    df["source"] = "month_end_recon_agent.allocation_result"
    df = df[
        [
            "period",
            "branch_id",
            "biz_line_id",
            "cost_type",
            "allocated_amount",
            "validation_status",
            "exception_count",
            "source",
        ]
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "validated_allocated_expense.csv"
    df.to_csv(path, index=False)
    return path


def export_validation_summary(period: str | None = None) -> Path:
    exceptions = detect_all_reconciliation_exceptions(write_to_db=False)
    grades = grade_all_exceptions(period, write_to_db=False)
    if period:
        exceptions = exceptions[exceptions["period"] == period].copy()
    merged = exceptions.merge(grades[["exception_id", "severity"]], on="exception_id", how="left", suffixes=("", "_graded"))
    if merged.empty:
        summary = pd.DataFrame(
            columns=[
                "period",
                "scenario",
                "total_amount",
                "exception_amount",
                "exception_count",
                "high_severity_count",
                "medium_severity_count",
                "low_severity_count",
            ]
        )
    else:
        summary = merged.groupby(["period", "scenario"], as_index=False).agg(
            total_amount=("source_amount", "sum"),
            exception_amount=("diff_amount", lambda s: s.abs().sum()),
            exception_count=("exception_id", "count"),
            high_severity_count=("severity_graded", lambda s: int((s == "HIGH").sum())),
            medium_severity_count=("severity_graded", lambda s: int((s == "MEDIUM").sum())),
            low_severity_count=("severity_graded", lambda s: int((s == "LOW").sum())),
        )
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "validation_summary.csv"
    summary.to_csv(path, index=False)
    return path


def export_all(period: str | None = None) -> list[Path]:
    return [
        export_validated_actual_revenue(period),
        export_validated_allocated_expense(period),
        export_validation_summary(period),
    ]


if __name__ == "__main__":
    for output_path in export_all():
        print(output_path)
