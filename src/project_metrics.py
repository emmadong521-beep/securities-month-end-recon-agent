from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd

from .agent import run_month_end_agent
from .config import OUTPUT_DIR, SYNTHETIC_DIR
from .data_quality import run_data_quality_checks
from .export_validated_data import export_all
from .validation import detect_all_reconciliation_exceptions


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _csv_count(name: str) -> int:
    path = SYNTHETIC_DIR / f"{name}.csv"
    return int(len(pd.read_csv(path))) if path.exists() else 0


def _pytest_summary() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        timeout=240,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}"
    match = re.search(r"(\d+) passed", output)
    if match and result.returncode == 0:
        return f"{match.group(1)} passed"
    return "not available"


def _agent_step_range() -> str:
    tasks = [
        ("请分析 2025-03 经纪佣金收入差异最大的异常，并定位根因。", "2025-03", None),
        ("请检查 2025-06 费用分摊异常，说明差异发生在哪个环节。", "2025-06", None),
        ("请分析异常 EXC_202503_001 的根因。", "2025-03", "EXC_202503_001"),
    ]
    counts = [len(run_month_end_agent(task, period, exception_id, use_llm=False).steps) for task, period, exception_id in tasks]
    return f"{min(counts)}-{max(counts)}"


def collect_project_metrics() -> dict[str, Any]:
    quality = run_data_quality_checks()
    exceptions = detect_all_reconciliation_exceptions(write_to_db=False)
    cases = pd.read_csv(SYNTHETIC_DIR / "root_cause_case.csv")
    expected_types = set(cases["exception_type"].astype(str))
    detected_types = set(exceptions["exception_type"].astype(str))
    exported_files = [path.name for path in export_all()]
    metrics = {
        "Synthetic trading records": _csv_count("trade_flow"),
        "Commission calculation rows": _csv_count("commission_calc"),
        "Revenue subledger rows": _csv_count("revenue_subledger"),
        "GL journal lines": _csv_count("gl_journal"),
        "Allocation result rows": _csv_count("allocation_result"),
        "Embedded reconciliation exception scenarios": int(len(expected_types)),
        "Detected reconciliation exceptions": int(len(exceptions)),
        "Predefined seeded demo exceptions detected": f"{len(expected_types & detected_types)} / {len(expected_types)}",
        "Supported reconciliation scenarios": 2,
        "Agent tool-call steps per demo task": _agent_step_range(),
        "Unit tests": _pytest_summary(),
        "Data quality status": str(quality["status"]),
        "Exported validated data files": int(len(exported_files)),
    }
    return metrics


def _write_outputs(metrics: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "project_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["| Metric | Value |", "|---|---:|"]
    for key, value in metrics.items():
        lines.append(f"| {key} | {value} |")
    (OUTPUT_DIR / "project_metrics.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    project_metrics = collect_project_metrics()
    _write_outputs(project_metrics)
    print(json.dumps(project_metrics, ensure_ascii=False, indent=2))
