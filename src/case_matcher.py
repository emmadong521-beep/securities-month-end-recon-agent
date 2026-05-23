from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .config import DB_PATH
from .evidence_chain import build_evidence_chain
from .validation import detect_all_reconciliation_exceptions


def _table(table: str) -> pd.DataFrame:
    con = duckdb.connect(str(DB_PATH))
    try:
        return con.execute(f"SELECT * FROM {table}").fetchdf()
    finally:
        con.close()


def _token_score(text: str, pattern: str) -> tuple[int, list[str]]:
    tokens = [token for token in str(pattern).replace("，", " ").replace("；", " ").replace(",", " ").split() if len(token) >= 2]
    hits = [token for token in tokens if token in str(text)]
    return len(hits) * 10, hits


def match_root_cause_cases(exception_id: str, top_k: int = 3) -> list[dict]:
    if not Path(DB_PATH).exists():
        from .db import ensure_database_initialized

        ensure_database_initialized()
    exceptions = detect_all_reconciliation_exceptions(write_to_db=False)
    match = exceptions[exceptions["exception_id"].astype(str) == exception_id]
    if match.empty:
        raise ValueError(f"Unknown exception_id: {exception_id}")
    exc = match.iloc[0]
    chain = build_evidence_chain(exception_id)
    cases = _table("root_cause_case")
    rows: list[dict] = []
    for _, case in cases.iterrows():
        score = 0
        reasons = []
        if str(case["scenario"]) == str(exc["scenario"]):
            score += 40
            reasons.append("场景一致")
        if str(case["exception_type"]) == str(exc["exception_type"]):
            score += 50
            reasons.append("异常类型一致")
        keyword_score, hits = _token_score(str(exc["suspected_reason"]), str(case["symptom"]))
        if keyword_score:
            score += keyword_score
            reasons.append(f"症状关键词匹配：{', '.join(hits[:3])}")
        pattern_score, pattern_hits = _token_score(str(chain.get("breakpoint", "")), str(case["evidence_pattern"]))
        if pattern_score:
            score += pattern_score
            reasons.append(f"证据模式匹配：{', '.join(pattern_hits[:3])}")
        if str(case["evidence_pattern"]).split()[0:1] and str(case["evidence_pattern"]).split()[0] in str(chain.get("breakpoint", "")):
            score += 10
        if score <= 0:
            continue
        rows.append(
            {
                "case_id": str(case["case_id"]),
                "match_score": int(score),
                "scenario": str(case["scenario"]),
                "exception_type": str(case["exception_type"]),
                "symptom": str(case["symptom"]),
                "root_cause": str(case["root_cause"]),
                "evidence_pattern": str(case["evidence_pattern"]),
                "recommended_action": str(case["recommended_action"]),
                "match_reason": "；".join(reasons) if reasons else "与当前异常存在规则维度相似性",
            }
        )
    rows.sort(key=lambda item: item["match_score"], reverse=True)
    return rows[: max(int(top_k), 1)]


def format_matched_cases_markdown(exception_id: str) -> str:
    cases = match_root_cause_cases(exception_id)
    if not cases:
        return "未匹配到相似历史案例。"
    lines = ["| 案例 | 分数 | 异常类型 | 根因 | 建议动作 | 匹配理由 |", "|---|---:|---|---|---|---|"]
    for case in cases:
        lines.append(
            f"| {case['case_id']} | {case['match_score']} | {case['exception_type']} | "
            f"{case['root_cause']} | {case['recommended_action']} | {case['match_reason']} |"
        )
    return "\n".join(lines)
