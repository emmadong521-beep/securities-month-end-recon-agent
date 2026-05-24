from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import pandas as pd


class StepType(str, Enum):
    INTENT_RECOGNITION = "意图识别"
    PLAN_GENERATION = "制定计划"
    TOOL_CALL = "工具调用"
    OBSERVATION = "观察结果"
    ANALYSIS_DECISION = "分析判断"
    CONCLUSION = "综合结论"


def summarize_result(result: Any) -> Any:
    if result is None:
        return None
    if isinstance(result, pd.DataFrame):
        return {
            "type": "DataFrame",
            "rows": int(len(result)),
            "columns": [str(col) for col in result.columns],
            "preview": result.head(5).to_dict(orient="records"),
        }
    if isinstance(result, pd.Series):
        return {
            "type": "Series",
            "index": [str(item) for item in result.index.tolist()],
            "values": result.to_dict(),
        }
    if isinstance(result, dict):
        return {
            str(key): summarize_result(value) if isinstance(value, (pd.DataFrame, pd.Series, dict, list, tuple)) else value
            for key, value in result.items()
        }
    if isinstance(result, (list, tuple)):
        return {
            "type": "list",
            "count": int(len(result)),
            "preview": [
                summarize_result(item) if isinstance(item, (pd.DataFrame, pd.Series, dict, list, tuple)) else item
                for item in list(result)[:5]
            ],
        }
    return result if isinstance(result, (str, int, float, bool)) else str(result)


def extract_key_numbers(result: Any) -> dict[str, float]:
    keywords = (
        "amount",
        "diff",
        "variance",
        "revenue",
        "profit",
        "expense",
        "effect",
        "rate",
        "count",
        "score",
        "rank",
    )
    numbers: dict[str, float] = {}

    def visit(value: Any, prefix: str = "") -> None:
        if isinstance(value, pd.DataFrame):
            for col in value.columns:
                col_name = str(col)
                if any(word in col_name.lower() for word in keywords) and pd.api.types.is_numeric_dtype(value[col]):
                    numbers[f"{prefix}{col_name}_sum"] = float(value[col].sum())
            numbers[f"{prefix}row_count"] = float(len(value))
            return
        if isinstance(value, pd.Series):
            visit(value.to_dict(), prefix)
            return
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                full_key = f"{prefix}{key_text}"
                if isinstance(item, (int, float)) and not isinstance(item, bool):
                    if any(word in key_text.lower() for word in keywords):
                        numbers[full_key] = float(item)
                elif isinstance(item, (dict, list, tuple, pd.DataFrame, pd.Series)):
                    visit(item, f"{full_key}.")
            return
        if isinstance(value, (list, tuple)):
            for index, item in enumerate(value[:5]):
                visit(item, f"{prefix}{index}.")

    visit(result)
    return numbers


@dataclass
class ReasoningStep:
    step_no: int
    step_type: StepType
    title: str
    detail: str
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    result_summary: Any = None
    key_numbers: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_no": self.step_no,
            "step_type": self.step_type.value,
            "title": self.title,
            "detail": self.detail,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input or {},
            "result_summary": self.result_summary,
            "key_numbers": self.key_numbers,
        }


@dataclass
class ReasoningTrace:
    user_task: str
    intent: str
    period: str | None = None
    final_answer: str = ""
    elapsed_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    steps: list[ReasoningStep] = field(default_factory=list)

    def add_step(
        self,
        step_type: StepType,
        title: str,
        detail: str,
        tool_name: str | None = None,
        tool_input: dict[str, Any] | None = None,
        result: Any = None,
        key_numbers: dict[str, float] | None = None,
    ) -> ReasoningStep:
        step = ReasoningStep(
            step_no=len(self.steps) + 1,
            step_type=step_type,
            title=title,
            detail=detail,
            tool_name=tool_name,
            tool_input=tool_input or {},
            result_summary=summarize_result(result),
            key_numbers=key_numbers or extract_key_numbers(result),
        )
        self.steps.append(step)
        return step

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_task": self.user_task,
            "intent": self.intent,
            "period": self.period,
            "final_answer": self.final_answer,
            "elapsed_ms": self.elapsed_ms,
            "metadata": summarize_result(self.metadata),
            "steps": [step.to_dict() for step in self.steps],
        }
