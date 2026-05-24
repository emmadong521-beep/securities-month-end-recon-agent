from __future__ import annotations

import re
import json
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .agent_trace import ReasoningTrace, StepType
from .case_matcher import match_root_cause_cases
from .evidence_chain import build_evidence_chain
from .llm_client import call_llm, is_llm_available
from .severity import grade_exception
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
    reason_for_tool: str = ""
    confidence: float | None = None


@dataclass
class AgentResult:
    user_task: str
    plan: list[str]
    steps: list[AgentStep]
    final_answer: str
    evidence_chain: dict | None
    report_path: str | None
    llm_mode: str = "Mock Agent"
    llm_error: str | None = None
    severity: dict | None = None
    matched_cases: list[dict] | None = None


TOOL_REGISTRY = {
    "detect_reconciliation_exceptions": {"description": "查询指定期间月结异常清单", "scenario": "ALL"},
    "grade_exception": {"description": "按金额、链路和影响面评定异常严重等级", "scenario": "ALL"},
    "build_evidence_chain": {"description": "构建收入链路或费用分摊链路证据链", "scenario": "ALL"},
    "match_root_cause_cases": {"description": "匹配相似历史根因案例", "scenario": "ALL"},
    "generate_root_cause_report": {"description": "生成可复核的异常归因报告", "scenario": "ALL"},
    "export_root_cause_report": {"description": "导出 Markdown 归因报告", "scenario": "ALL"},
    "query_interface_batch_log": {"description": "接口批次日志查询扩展点", "scenario": "COMMISSION_TO_GL"},
    "query_allocation_rule": {"description": "分摊规则查询扩展点", "scenario": "ALLOCATION"},
    "query_allocation_driver": {"description": "分摊因子查询扩展点", "scenario": "ALLOCATION"},
    "query_gl_journal_summary": {"description": "总账凭证汇总查询扩展点", "scenario": "COMMISSION_TO_GL"},
}


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


def _intent_from_scenario(scenario: str, exception_id: str | None = None) -> str:
    if exception_id:
        return "exception_root_cause"
    if scenario == "ALLOCATION":
        return "allocation_reconciliation"
    return "commission_reconciliation"


def _scenario_from_intent(intent: str) -> str:
    if intent == "allocation_reconciliation":
        return "ALLOCATION"
    return "COMMISSION_TO_GL"


def _fallback_task_context(
    user_task: str,
    available_periods: list[str],
    available_exceptions: list[str],
    period: str | None = None,
    exception_id: str | None = None,
) -> dict:
    selected_exception_id = _extract_exception_id(user_task, exception_id)
    selected_period = _extract_period(user_task, period)
    if selected_period not in available_periods:
        selected_period = available_periods[0] if available_periods else "2025-03"
    if selected_exception_id and available_exceptions and selected_exception_id not in available_exceptions:
        selected_exception_id = None
    scenario = _scenario_from_task(user_task)
    return {
        "intent": _intent_from_scenario(scenario, selected_exception_id),
        "period": selected_period,
        "exception_id": selected_exception_id,
        "focus": "基于月结异常、证据链和归因报告定位根因",
    }


def parse_month_end_task_with_llm(
    user_task: str,
    available_periods: list[str],
    available_exceptions: list[str],
) -> dict:
    fallback = _fallback_task_context(user_task, available_periods, available_exceptions)
    if not is_llm_available():
        return fallback
    try:
        content = call_llm(
            [
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "user_task": user_task,
                            "available_periods": available_periods,
                            "available_exceptions": available_exceptions[:50],
                            "allowed_intents": [
                                "commission_reconciliation",
                                "allocation_reconciliation",
                                "exception_root_cause",
                                "unknown",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                }
            ],
            system_prompt=(
                "你只负责解析证券公司月结 Agent 任务意图，不做金额计算。"
                "必须只返回 JSON，对象字段为 intent, period, exception_id, focus。"
            ),
        )
        parsed = json.loads(content)
        intent = str(parsed.get("intent") or fallback["intent"])
        if intent not in {"commission_reconciliation", "allocation_reconciliation", "exception_root_cause", "unknown"}:
            intent = fallback["intent"]
        parsed_period = parsed.get("period") if parsed.get("period") in available_periods else fallback["period"]
        parsed_exception = parsed.get("exception_id")
        if available_exceptions and parsed_exception not in available_exceptions:
            parsed_exception = fallback["exception_id"]
        return {
            "intent": intent,
            "period": parsed_period,
            "exception_id": parsed_exception,
            "focus": str(parsed.get("focus") or fallback["focus"])[:120],
        }
    except Exception:
        return fallback


def _fallback_plan(task_context: dict) -> list[str]:
    if task_context.get("exception_id"):
        return ["解析异常编号和场景", "构建证据链定位差异层级", "评定异常严重等级", "匹配历史根因案例", "生成归因报告和处理建议"]
    if task_context.get("intent") == "allocation_reconciliation":
        return ["查询期间异常清单", "筛选费用分摊异常", "构建分摊证据链", "评定管理会计影响等级", "匹配历史案例并生成建议动作"]
    return ["查询期间异常清单", "筛选经纪佣金收入异常", "构建收入链路证据链", "评定总账和报表影响等级", "匹配历史案例并生成建议动作"]


def generate_month_end_plan_with_llm(task_context: dict) -> list[str]:
    fallback = _fallback_plan(task_context)
    if not is_llm_available():
        return fallback
    try:
        content = call_llm(
            [{"role": "user", "content": json.dumps(task_context, ensure_ascii=False)}],
            system_prompt=(
                "你为证券公司月结差异归因 Agent 生成 4-6 步分析计划。"
                "计划只能围绕查询异常清单、筛选异常、构建证据链、查看接口日志或规则配置、生成结论。"
                "不要编造金额。每行输出一步计划，不要输出编号。"
            ),
        )
        plan = [line.strip("- 1234567890.、") for line in content.splitlines() if line.strip()]
        return plan[:6] or fallback
    except Exception:
        return fallback


def _final_answer(exception_id: str, chain: dict, report_path: str | None) -> str:
    report_note = f"报告已保存至 `{report_path}`。" if report_path else "报告未生成。"
    return (
        f"已定位异常 {exception_id}，期间为 {chain['period']}，差异金额 "
        f"{_format_amount(float(chain['diff_amount']))}。差异发生层级为 {chain['breakpoint']}。"
        f"根因为：{chain['root_cause']}。建议动作：{chain['recommended_action']}。{report_note}"
    )


def _enhanced_final_answer(
    exception_id: str,
    chain: dict,
    severity: dict | None,
    matched_cases: list[dict] | None,
    report_path: str | None,
) -> str:
    severity = severity or {}
    matched_cases = matched_cases or []
    top_case = matched_cases[0] if matched_cases else {}
    severity_text = str(severity.get("severity", "UNKNOWN"))
    manual = "需要人工复核" if severity.get("requires_manual_review") else "可按自动校验结果跟踪"
    case_text = (
        f"最相似历史案例为 {top_case.get('case_id')}，根因模式为：{top_case.get('root_cause')}，"
        f"建议动作：{top_case.get('recommended_action')}。"
        if top_case
        else "未匹配到相似历史案例。"
    )
    report_note = f"报告已保存至 `{report_path}`。" if report_path else "报告未生成。"
    return (
        f"异常 ID：{exception_id}；会计期间：{chain['period']}；异常类型：{chain['exception_type']}。"
        f"差异金额 {_format_amount(float(chain['diff_amount']))}，差异发生层级为 {chain['breakpoint']}。"
        f"严重等级：{severity_text}，原因：{severity.get('severity_reason', '未生成分级说明')}，"
        f"处理优先级：{severity.get('recommended_priority', '待评估')}，{manual}。"
        f"{case_text} 根因结论：{chain['root_cause']}。建议动作：{chain['recommended_action']}。{report_note}"
    )


def generate_month_end_final_answer_with_llm(
    user_task: str,
    plan: list[str],
    steps: list[AgentStep],
    evidence_chain: dict | None,
    mock_answer: str,
    severity: dict | None = None,
    matched_cases: list[dict] | None = None,
) -> str:
    if not is_llm_available():
        return mock_answer
    facts = {
        "user_task": user_task,
        "plan": plan,
        "steps": [step.__dict__ for step in steps],
        "evidence_chain": evidence_chain,
        "severity": severity,
        "matched_cases": matched_cases,
        "mock_answer": mock_answer,
    }
    content = call_llm(
        [{"role": "user", "content": json.dumps(facts, ensure_ascii=False, default=str)}],
        system_prompt=(
            "你是证券公司月结差异归因 Agent 的表达层。只能基于输入事实生成中文结论，"
            "不得编造金额、异常编号、期间、营业部、批次号或根因。"
            "如证据不足，必须说明当前数据不足以判断。金额单位保持万元。"
        ),
    )
    return content.strip() or mock_answer


def run_month_end_agent(
    user_task: str,
    period: str | None = None,
    exception_id: str | None = None,
    use_llm: bool | None = None,
) -> AgentResult:
    available_periods = [f"2025-{m:02d}" for m in range(1, 13)]
    available_exceptions: list[str] = []
    if period:
        available_exceptions = detect_reconciliation_exceptions(period)["exception_id"].astype(str).tolist()
    requested_llm = is_llm_available() if use_llm is None else bool(use_llm)
    llm_error = None
    llm_mode = "Mock Agent"
    if requested_llm and is_llm_available():
        llm_mode = "Volcengine Ark LLM Agent"
    elif requested_llm:
        llm_error = "LLM 配置不完整，已回退 Mock Agent。"

    task_context = _fallback_task_context(user_task, available_periods, available_exceptions, period, exception_id)
    if requested_llm and is_llm_available():
        try:
            task_context = parse_month_end_task_with_llm(user_task, available_periods, available_exceptions)
            if period:
                task_context["period"] = period
            if exception_id:
                task_context["exception_id"] = exception_id
                task_context["intent"] = "exception_root_cause"
        except Exception as exc:
            llm_error = f"LLM 任务解析失败，已回退 Mock Agent：{exc}"
            llm_mode = "Mock Agent"

    selected_period = str(task_context.get("period") or _extract_period(user_task, period))
    selected_exception_id = task_context.get("exception_id") or _extract_exception_id(user_task, exception_id)
    scenario = _scenario_from_intent(str(task_context.get("intent") or "commission_reconciliation"))
    plan = _fallback_plan(task_context)
    if requested_llm and is_llm_available():
        try:
            plan = generate_month_end_plan_with_llm(task_context)
        except Exception as exc:
            llm_error = f"LLM 计划生成失败，已使用 Mock 计划：{exc}"

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
                reason_for_tool="先获取候选异常，确定本次排查对象。",
                confidence=0.95,
            )
        )
        selected = _select_exception(exceptions, scenario)
        if selected is None:
            final = f"{selected_period} 未检测到符合任务类型的异常。"
            return AgentResult(user_task, plan, steps, final, None, None, llm_mode, llm_error)
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
                reason_for_tool="按任务场景和差异绝对值选择最高优先级异常。",
                confidence=0.9,
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
            reason_for_tool="逐层穿透源系统、子账、总账或分摊链路，确认断点。",
            confidence=0.92,
        )
    )

    severity = grade_exception(selected_exception_id)
    steps.append(
        AgentStep(
            step_no=len(steps) + 1,
            thought="结合差异金额、影响链路和异常类型评估处理优先级。",
            tool_name="grade_exception",
            tool_input={"exception_id": selected_exception_id},
            observation=(
                f"严重等级 {severity['severity']}；影响层级 {severity['affected_layer']}；"
                f"优先级 {severity['recommended_priority']}。"
            ),
            reason_for_tool="月结排查需要区分总账/报表风险和管理会计口径风险。",
            confidence=0.88,
        )
    )

    matched_cases = match_root_cause_cases(selected_exception_id, top_k=3)
    top_case = matched_cases[0] if matched_cases else None
    steps.append(
        AgentStep(
            step_no=len(steps) + 1,
            thought="用当前异常症状、断点和异常类型匹配历史根因模式。",
            tool_name="match_root_cause_cases",
            tool_input={"exception_id": selected_exception_id, "top_k": 3},
            observation=(
                f"匹配到 {len(matched_cases)} 条相似案例。"
                + (
                    f"最高匹配案例 {top_case['case_id']}，分数 {top_case['match_score']}，根因 {top_case['root_cause']}。"
                    if top_case
                    else ""
                )
            ),
            reason_for_tool="历史案例用于校验根因判断并给出可执行处理动作。",
            confidence=0.86,
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
            reason_for_tool="将证据链、分级和建议动作整理成可留痕报告。",
            confidence=0.9,
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
            reason_for_tool="导出 Markdown 文件，便于月结复核和跨团队流转。",
            confidence=0.95,
        )
    )

    mock_final = _enhanced_final_answer(selected_exception_id, evidence_chain, severity, matched_cases, report_path)
    final = mock_final
    if requested_llm and is_llm_available():
        try:
            final = generate_month_end_final_answer_with_llm(user_task, plan, steps, evidence_chain, mock_final, severity, matched_cases)
        except Exception as exc:
            llm_error = f"LLM 结论生成失败，已展示 Mock 结果：{exc}"
            llm_mode = "Mock Agent"
            final = mock_final
    return AgentResult(user_task, plan, steps, final, evidence_chain, report_path, llm_mode, llm_error, severity, matched_cases)


def run_month_end_agent_with_trace(
    user_task: str,
    period: str | None = None,
    exception_id: str | None = None,
) -> ReasoningTrace:
    started = time.perf_counter()
    available_periods = [f"2025-{m:02d}" for m in range(1, 13)]
    selected_period = _extract_period(user_task, period)
    if selected_period not in available_periods:
        selected_period = "2025-03"
    selected_exception_id = _extract_exception_id(user_task, exception_id)
    scenario = _scenario_from_task(user_task)
    intent = _intent_from_scenario(scenario, selected_exception_id)
    task_context = {
        "intent": intent,
        "period": selected_period,
        "exception_id": selected_exception_id,
        "scenario": scenario,
        "focus": "定位月结异常断点、严重等级、历史案例和建议动作",
    }
    trace = ReasoningTrace(user_task=user_task, intent=intent, period=selected_period)
    trace.add_step(
        StepType.INTENT_RECOGNITION,
        "识别任务意图",
        "解析用户输入中的期间、异常编号和排查场景。",
        result=task_context,
    )

    plan = _fallback_plan(task_context)
    trace.add_step(
        StepType.PLAN_GENERATION,
        "制定排查计划",
        "根据任务类型选择先查异常清单、再做证据链、分级、案例匹配和报告生成的路径。",
        result={"plan": plan, "expected_tools": [item for item in TOOL_REGISTRY]},
    )

    exceptions = detect_reconciliation_exceptions(selected_period)
    trace.add_step(
        StepType.TOOL_CALL,
        "查询期间异常清单",
        "获取候选异常，作为后续选择和下钻对象。",
        tool_name="detect_reconciliation_exceptions",
        tool_input={"period": selected_period},
        result=exceptions,
    )
    trace.add_step(
        StepType.OBSERVATION,
        "观察异常分布",
        f"期间 {selected_period} 检测到 {len(exceptions)} 条异常。",
        result=exceptions,
    )

    if not selected_exception_id:
        selected = _select_exception(exceptions, scenario)
        if selected is None:
            trace.final_answer = f"{selected_period} 未检测到符合任务类型的异常。"
            trace.add_step(
                StepType.CONCLUSION,
                "综合结论",
                trace.final_answer,
                result={"final_answer": trace.final_answer},
            )
            trace.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            return trace
        selected_exception_id = str(selected["exception_id"])
        trace.add_step(
            StepType.ANALYSIS_DECISION,
            "选择下钻异常",
            (
                f"按场景 {scenario} 和差异绝对值选择异常 {selected_exception_id}，"
                f"差异金额 {_format_amount(float(selected['diff_amount']))}。"
            ),
            result=selected.to_dict(),
        )

    evidence_chain = build_evidence_chain(selected_exception_id)
    trace.add_step(
        StepType.TOOL_CALL,
        "构建证据链",
        "逐层穿透源系统、子账、总账或费用分摊链路。",
        tool_name="build_evidence_chain",
        tool_input={"exception_id": selected_exception_id},
        result=evidence_chain,
    )
    trace.add_step(
        StepType.OBSERVATION,
        "定位差异发生层级",
        (
            f"证据链包含 {len(evidence_chain['trace_steps'])} 个层级，"
            f"差异发生在 {evidence_chain['breakpoint']}。"
        ),
        result=evidence_chain,
    )

    severity = grade_exception(selected_exception_id)
    trace.add_step(
        StepType.TOOL_CALL,
        "评定异常严重等级",
        "按差异金额、影响链路和异常类型评估优先级。",
        tool_name="grade_exception",
        tool_input={"exception_id": selected_exception_id},
        result=severity,
    )
    trace.add_step(
        StepType.ANALYSIS_DECISION,
        "形成风险判断",
        (
            f"异常被评为 {severity['severity']}，影响层级为 {severity['affected_layer']}，"
            f"人工复核要求为 {severity['requires_manual_review']}。"
        ),
        result=severity,
    )

    matched_cases = match_root_cause_cases(selected_exception_id, top_k=3)
    trace.add_step(
        StepType.TOOL_CALL,
        "匹配历史案例",
        "用异常类型、症状和断点匹配 root_cause_case 中的相似案例。",
        tool_name="match_root_cause_cases",
        tool_input={"exception_id": selected_exception_id, "top_k": 3},
        result=matched_cases,
    )
    trace.add_step(
        StepType.OBSERVATION,
        "观察案例匹配结果",
        f"匹配到 {len(matched_cases)} 条相似案例。",
        result=matched_cases,
    )

    report = generate_root_cause_report(selected_exception_id)
    trace.add_step(
        StepType.TOOL_CALL,
        "生成归因报告",
        "将证据链、异常分级和案例匹配结果组织成可复核报告。",
        tool_name="generate_root_cause_report",
        tool_input={"exception_id": selected_exception_id},
        result={"report_length": len(report), "report_preview": report[:500]},
    )

    final_answer = _enhanced_final_answer(selected_exception_id, evidence_chain, severity, matched_cases, None)
    trace.final_answer = final_answer
    trace.metadata = {
        "exception_id": selected_exception_id,
        "evidence_chain": evidence_chain,
        "severity": severity,
        "matched_cases": matched_cases,
    }
    trace.add_step(
        StepType.CONCLUSION,
        "综合结论",
        final_answer,
        result={
            "exception_id": selected_exception_id,
            "period": evidence_chain["period"],
            "diff_amount": evidence_chain["diff_amount"],
            "breakpoint": evidence_chain["breakpoint"],
            "severity": severity.get("severity"),
            "matched_case_count": len(matched_cases),
            "root_cause": evidence_chain["root_cause"],
            "recommended_action": evidence_chain["recommended_action"],
        },
    )
    trace.elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    return trace


def answer_month_end_followup(question: str, context: AgentResult, use_llm: bool | None = None) -> str:
    question_norm = question.strip().lower()
    chain = context.evidence_chain or {}
    if not chain:
        return "当前上下文没有可用证据链，请先运行一次 Agent 分析。"
    severity = context.severity or {}
    matched_cases = context.matched_cases or []
    requested_llm = is_llm_available() if use_llm is None else bool(use_llm)
    if requested_llm and is_llm_available():
        try:
            content = call_llm(
                [
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question,
                                "final_answer": context.final_answer,
                                "steps": [step.__dict__ for step in context.steps],
                                "evidence_chain": context.evidence_chain,
                                "severity": context.severity,
                                "matched_cases": context.matched_cases,
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                ],
                system_prompt=(
                    "你回答证券公司月结 Agent 的追问。只能引用上下文已有事实，"
                    "不得新增金额、异常编号、期间、批次或根因。金额单位保持万元。"
                ),
            )
            if content.strip():
                return content.strip()
        except Exception:
            pass

    if "高风险" in question or "高等级" in question or "为什么判断" in question:
        return (
            f"当前严重等级为 {severity.get('severity', 'UNKNOWN')}。"
            f"判断依据：{severity.get('severity_reason', '未生成分级说明')}；"
            f"影响层级：{severity.get('affected_layer', chain.get('breakpoint', '未知'))}；"
            f"处理优先级：{severity.get('recommended_priority', '待评估')}。"
        )
    if "历史案例" in question or "相似" in question:
        if not matched_cases:
            return "当前上下文未匹配到相似历史案例。"
        case_text = "；".join(
            f"{case['case_id']}（分数 {case['match_score']}，根因：{case['root_cause']}）"
            for case in matched_cases[:3]
        )
        return f"相似历史案例：{case_text}。"
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
    if "谁处理" in question or "责任" in question or "下一步" in question:
        if str(chain.get("scenario")) == "ALLOCATION":
            return "建议由财务管理会计或费用分摊规则负责人牵头，系统数据团队补充规则版本、分摊因子和批次重跑证据。"
        return "建议由财务核算人员牵头，收入子账或总账接口负责人配合核对批次日志、凭证生成和幂等控制。"
    if "财务经理" in question or "经理" in question or "说明" in question:
        return (
            f"给财务经理的说明：{chain['period']} 发现 {chain['exception_type']} 异常，"
            f"差异金额 {_format_amount(float(chain['diff_amount']))}，断点位于 {chain['breakpoint']}。"
            f"当前评级为 {severity.get('severity', 'UNKNOWN')}，建议按 {severity.get('recommended_priority', '既定优先级')} 处理，"
            f"核心动作是：{chain['recommended_action']}"
        )
    return "可以继续围绕严重等级、历史案例、差异层级、影响金额、总账影响、管理会计影响或建议动作追问。"
