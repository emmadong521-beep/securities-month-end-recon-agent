from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .evidence_chain import build_evidence_chain
from .validation import (
    detect_reconciliation_exceptions,
    export_root_cause_report,
    generate_root_cause_report,
)


@dataclass
class AgentStep:
    step_no: int
    thought: str
    tool_name: str
    tool_input: dict
    observation: str


@dataclass
class AgentResult:
    user_task: str
    plan: list[str]
    steps: list[AgentStep]
    final_answer: str
    evidence_chain: dict | None
    report_path: str | None


def _extract_period(user_task: str, period: str | None) -> str:
    if period:
        return period
    match = re.search(r"20\d{2}[-年](0[1-9]|1[0-2])", user_task)
    if match:
        return match.group(0).replace("年", "-")
    compact = re.search(r"(20\d{2})(0[1-9]|1[0-2])", user_task)
    if compact:
        return f"{compact.group(1)}-{compact.group(2)}"
    return "2025-03"


def _extract_exception_id(user_task: str, exception_id: str | None) -> str | None:
    if exception_id:
        return exception_id
    match = re.search(r"EXC_\d{6}_\d{3}", user_task, flags=re.IGNORECASE)
    return match.group(0).upper() if match else None


def _format_amount(value: float) -> str:
    return f"{value / 10000:,.2f} 万元"


def _select_exception(exceptions: pd.DataFrame, scenario: str) -> pd.Series | None:
    if exceptions.empty:
        return None
    if scenario == "ALLOCATION":
        candidates = exceptions[exceptions["scenario"] == "ALLOCATION"].copy()
    else:
        candidates = exceptions[exceptions["scenario"] == "COMMISSION_TO_GL"].copy()
    if candidates.empty:
        return None
    candidates["abs_diff"] = candidates["diff_amount"].astype(float).abs()
    return candidates.sort_values("abs_diff", ascending=False).iloc[0]


def _scenario_from_task(user_task: str) -> str:
    allocation_words = ["费用", "分摊", "allocation", "规则", "因子"]
    if any(word.lower() in user_task.lower() for word in allocation_words):
        return "ALLOCATION"
    return "COMMISSION_TO_GL"


def _final_answer(exception_id: str, chain: dict, report_path: str | None) -> str:
    report_note = f"报告已保存至 `{report_path}`。" if report_path else "报告未生成。"
    return (
        f"已定位异常 {exception_id}，期间为 {chain['period']}，差异金额 "
        f"{_format_amount(float(chain['diff_amount']))}。差异发生层级为 {chain['breakpoint']}。"
        f"根因为：{chain['root_cause']}。建议动作：{chain['recommended_action']}。{report_note}"
    )


def run_month_end_agent(
    user_task: str,
    period: str | None = None,
    exception_id: str | None = None,
) -> AgentResult:
    selected_period = _extract_period(user_task, period)
    selected_exception_id = _extract_exception_id(user_task, exception_id)
    scenario = _scenario_from_task(user_task)
    if selected_exception_id:
        plan = [
            "解析自然语言任务中的异常编号",
            "按异常编号构建证据链",
            "生成归因报告并输出结论",
        ]
    elif scenario == "ALLOCATION":
        plan = [
            "查询当前期间异常清单",
            "筛选费用分摊相关异常并定位最大差异",
            "构建费用池、规则、因子和分摊结果证据链",
            "生成归因报告并输出建议动作",
        ]
    else:
        plan = [
            "查询当前期间异常清单",
            "筛选经纪佣金收入相关异常并定位最大差异",
            "构建交易、佣金、子账和总账证据链",
            "生成归因报告并输出建议动作",
        ]

    steps: list[AgentStep] = []
    evidence_chain: dict | None = None
    report_path: str | None = None

    if not selected_exception_id:
        exceptions = detect_reconciliation_exceptions(selected_period)
        steps.append(
            AgentStep(
                step_no=1,
                thought="先获取期间异常清单，确认可分析对象。",
                tool_name="detect_reconciliation_exceptions",
                tool_input={"period": selected_period},
                observation=f"检测到 {len(exceptions)} 条异常。",
            )
        )
        selected = _select_exception(exceptions, scenario)
        if selected is None:
            final = f"{selected_period} 未检测到符合任务类型的异常。"
            return AgentResult(user_task, plan, steps, final, None, None)
        selected_exception_id = str(selected["exception_id"])
        steps.append(
            AgentStep(
                step_no=2,
                thought="按任务意图选择差异金额绝对值最大的异常。",
                tool_name="select_exception_by_abs_diff",
                tool_input={"scenario": scenario, "period": selected_period},
                observation=(
                    f"选中 {selected_exception_id}，类型 {selected['exception_type']}，"
                    f"差异金额 {_format_amount(float(selected['diff_amount']))}。"
                ),
            )
        )

    evidence_chain = build_evidence_chain(selected_exception_id)
    steps.append(
        AgentStep(
            step_no=len(steps) + 1,
            thought="对选中异常执行逐层穿透，定位差异发生层级。",
            tool_name="build_evidence_chain",
            tool_input={"exception_id": selected_exception_id},
            observation=(
                f"证据链包含 {len(evidence_chain['trace_steps'])} 个层级，"
                f"差异发生点为 {evidence_chain['breakpoint']}。"
            ),
        )
    )

    report = generate_root_cause_report(selected_exception_id)
    steps.append(
        AgentStep(
            step_no=len(steps) + 1,
            thought="基于规则结果和证据链生成可复核的归因报告。",
            tool_name="generate_root_cause_report",
            tool_input={"exception_id": selected_exception_id},
            observation=f"已生成归因报告正文，共 {len(report)} 个字符。",
        )
    )

    path = export_root_cause_report(selected_exception_id)
    report_path = str(Path(path))
    steps.append(
        AgentStep(
            step_no=len(steps) + 1,
            thought="将报告保存为 Markdown 文件，便于月结复核留痕。",
            tool_name="export_root_cause_report",
            tool_input={"exception_id": selected_exception_id},
            observation=f"报告路径：{report_path}",
        )
    )

    final = _final_answer(selected_exception_id, evidence_chain, report_path)
    return AgentResult(user_task, plan, steps, final, evidence_chain, report_path)


def answer_month_end_followup(question: str, context: AgentResult) -> str:
    question_norm = question.strip().lower()
    chain = context.evidence_chain or {}
    if not chain:
        return "当前上下文没有可用证据链，请先运行一次 Agent 分析。"

    if "哪一层" in question or "哪个环节" in question or "发生在哪" in question:
        return f"差异发生层级为 {chain['breakpoint']}。"
    if "金额" in question or "影响" in question:
        return f"本次差异金额为 {_format_amount(float(chain['diff_amount']))}。"
    if "建议" in question or "动作" in question or "处理" in question:
        return f"建议动作：{chain['recommended_action']}"
    if "总账" in question:
        breakpoint = str(chain.get("breakpoint", ""))
        scenario = str(chain.get("scenario", ""))
        if "gl_journal" in breakpoint:
            return "该异常已定位到总账凭证入账层级，会直接影响总账金额或凭证完整性。"
        if scenario == "COMMISSION_TO_GL":
            return "该异常处于收入链路，若不修复，会影响后续总账确认或总账与子账勾稽。"
        return "该异常主要位于费用分摊链路，需结合管理会计分摊入账规则判断是否同步影响总账。"
    if "管理会计" in question:
        if str(chain.get("scenario")) == "ALLOCATION":
            return "会影响管理会计分析，因为费用分摊金额、规则或因子异常会改变营业部和业务线利润。"
        return "会影响管理会计分析，因为收入确认差异会传导到实际收入、利润贡献和经营分析口径。"
    return "可以继续围绕差异层级、影响金额、总账影响、管理会计影响或建议动作追问。"
