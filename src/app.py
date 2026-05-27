from __future__ import annotations

from dataclasses import asdict
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.agent import answer_month_end_followup, run_month_end_agent, run_month_end_agent_with_trace
from src.case_matcher import format_matched_cases_markdown, match_root_cause_cases
from src.db import ensure_database_initialized
from src.evidence_chain import build_evidence_chain, format_evidence_chain_markdown
from src.export_validated_data import export_all, export_validation_summary
from src.llm_client import explain_llm_config_status, is_llm_available, load_llm_config
from src.severity import grade_all_exceptions, grade_exception
from src.ui import (
    format_wan,
    inject_global_css,
    render_info_card,
    render_kpi_card,
    render_page_header,
    render_section_title,
    severity_color,
)
from src.validation import (
    detect_reconciliation_exceptions,
    explain_exception_mock,
    export_root_cause_report,
    generate_root_cause_report,
    reconcile_allocation_result,
    reconcile_commission_to_gl,
)


st.set_page_config(page_title="证券公司月结差异归因 Agent", layout="wide")
inject_global_css()
render_page_header(
    "证券公司月结差异归因 Agent",
    "佣金收入勾稽、费用分摊校验、异常分级、证据链穿透、根因报告",
)

ensure_database_initialized(force_rebuild=False)
if st.sidebar.button("重新生成演示数据"):
    ensure_database_initialized(force_rebuild=True)
    st.sidebar.success("数据和 DuckDB 已重新生成。")
period = st.sidebar.selectbox("会计期间", [f"2025-{m:02d}" for m in range(1, 13)], index=2)
page = st.sidebar.radio(
    "功能",
    ["月结批次概览", "经纪佣金收入勾稽检查", "费用分摊准确性检查", "异常清单", "异常详情", "异常证据链", "可信数据导出", "AI / mock 归因报告", "Agent 工作台"],
)

exceptions = detect_reconciliation_exceptions(period)

AMOUNT_COLUMNS = {
    "commission_amount",
    "subledger_amount",
    "gl_amount",
    "commission_to_subledger_diff",
    "subledger_to_gl_diff",
    "amount",
    "allocated_amount",
    "diff_amount",
    "source_amount",
    "target_amount",
}


def _amount_view(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    rename = {}
    for col in AMOUNT_COLUMNS.intersection(out.columns):
        out[col] = out[col].astype(float) / 10000
        rename[col] = f"{col}（万元）"
    return out.rename(columns=rename)


def _trace_steps_view(trace_steps: list[dict]) -> pd.DataFrame:
    out = pd.DataFrame(trace_steps)
    if "amount" in out.columns:
        out["amount"] = out["amount"].astype(float) / 10000
        out = out.rename(columns={"amount": "amount（万元）"})
    return out


def _agent_steps_view(result) -> pd.DataFrame:
    rows = []
    for step in result.steps:
        row = asdict(step)
        row["tool_input"] = str(row["tool_input"])
        rows.append(row)
    return pd.DataFrame(rows)


def _data_quality_status() -> str:
    report_path = Path(__file__).resolve().parents[1] / "data" / "output" / "data_quality_report.json"
    if not report_path.exists():
        return "WARNING"
    try:
        return json.loads(report_path.read_text(encoding="utf-8")).get("status", "WARNING")
    except json.JSONDecodeError:
        return "WARNING"


def _render_trace_timeline(chain: dict) -> None:
    breakpoint_text = str(chain.get("breakpoint", ""))
    for step in chain["trace_steps"]:
        layer = str(step.get("layer", ""))
        is_breakpoint = layer in breakpoint_text or breakpoint_text in layer
        render_info_card(
            f"{step.get('step')} · {layer}",
            (
                f"{step.get('description')}。记录数：{step.get('record_count')}；"
                f"金额：{format_wan(step.get('amount'))}；状态：{'BREAKPOINT' if is_breakpoint else 'OK'}。"
            ),
            icon="🔎" if is_breakpoint else "✓",
            border_color=severity_color("HIGH") if is_breakpoint else "#1F4E79",
        )


TRACE_ICONS = {
    "意图识别": "🎯",
    "制定计划": "📝",
    "工具调用": "🔧",
    "观察结果": "👁️",
    "分析判断": "🧠",
    "综合结论": "✅",
}


def _render_trace_payload(payload) -> None:
    if isinstance(payload, dict) and payload.get("type") == "DataFrame":
        st.json({key: value for key, value in payload.items() if key != "preview"})
        if payload.get("preview"):
            st.dataframe(pd.DataFrame(payload["preview"]), width="stretch")
    elif isinstance(payload, dict) and payload.get("type") == "list":
        st.json({key: value for key, value in payload.items() if key != "preview"})
        if payload.get("preview"):
            st.json(payload["preview"])
    elif payload is not None:
        st.json(payload)


def _render_explainable_trace(trace) -> None:
    trace_dict = trace.to_dict()
    render_section_title("可解释分析轨迹", "🧭")
    st.caption("展示任务理解、分析计划、工具调用轨迹、观察结果、分析判断和综合结论。")
    c1, c2, c3 = st.columns(3)
    with c1:
        render_kpi_card("分析步骤数", str(len(trace.steps)), status="PASS")
    with c2:
        render_kpi_card("工具调用次数", str(sum(1 for step in trace.steps if step.tool_name)), status="PASS")
    with c3:
        render_kpi_card("总耗时", f"{(trace.elapsed_ms or 0) / 1000:.2f}s", status="PASS")
    render_info_card("最终结论", trace.final_answer, icon="✅", border_color="#059669")
    st.markdown("**任务输入**")
    st.write(trace.user_task)
    for step in trace.steps:
        step_type = step.step_type.value
        icon = TRACE_ICONS.get(step_type, "•")
        with st.expander(f"{icon} 步骤 {step.step_no}｜{step_type}｜{step.title}", expanded=step.step_type.value == "综合结论"):
            render_info_card(step.title, step.detail, icon=icon, border_color="#1F4E79")
            if step.tool_name:
                st.markdown("**工具调用轨迹**")
                st.json({"tool_name": step.tool_name, "tool_input": step.tool_input or {}})
            if step.result_summary is not None:
                st.markdown("**观察结果**")
                _render_trace_payload(step.result_summary)
            if step.key_numbers:
                st.markdown("**关键数字**")
                st.json(step.key_numbers)
    st.download_button(
        "下载 trace JSON",
        data=json.dumps(trace_dict, ensure_ascii=False, indent=2, default=str),
        file_name="month_end_agent_trace.json",
        mime="application/json",
    )


def _recommended_demo_path() -> None:
    with st.container(border=True):
        render_section_title("推荐演示路径", "🧭")
        st.markdown(
            """
1. 在侧边栏选择 `2025-03`，先看“月结批次概览”确认本月异常数量。
2. 进入“经纪佣金收入勾稽检查”，定位佣金计算、收入子账、总账之间的金额差异。
3. 切换到 `2025-06` 至 `2025-08`，查看费用分摊比例、规则版本和分摊因子异常。
4. 打开“异常清单”，选择一条异常进入“异常证据链”。
5. 查看“差异定位结论”和逐层穿透表，再导出 Markdown 归因报告。
            """
        )


def _llm_status_text(use_llm: bool) -> str:
    status = explain_llm_config_status()
    if use_llm and status["available"]:
        return "当前模式：Volcengine Ark LLM Agent"
    if use_llm and not status["available"]:
        return "当前模式：LLM 配置不完整，已回退 Mock Agent"
    return "当前模式：Mock Agent"


def _show_llm_config_status() -> None:
    status = explain_llm_config_status()
    display_status = {
        "mode": status["mode"],
        "provider": status["provider"],
        "base_url": status["base_url"],
        "model": status["model"],
        "missing_fields": status["missing_fields"],
        "message": status["message"],
        "api_key": "已配置" if status.get("api_key_configured") else "未配置",
    }
    with st.expander("LLM 配置状态"):
        st.json(display_status)

if page == "月结批次概览":
    _recommended_demo_path()
    rec = reconcile_commission_to_gl(period)
    alloc = reconcile_allocation_result(period)
    grades = grade_all_exceptions(period)
    high_count = int((grades["severity"] == "HIGH").sum()) if not grades.empty and "severity" in grades else 0
    medium_count = int((grades["severity"] == "MEDIUM").sum()) if not grades.empty and "severity" in grades else 0
    quality_status = _data_quality_status()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("检测异常数", str(len(exceptions)), status="HIGH" if len(exceptions) else "PASS", help_text=period)
    with c2:
        render_kpi_card("HIGH 异常数", str(high_count), status="HIGH" if high_count else "PASS", help_text="收入确认和总账优先")
    with c3:
        render_kpi_card("MEDIUM 异常数", str(medium_count), status="MEDIUM" if medium_count else "PASS", help_text="分摊和管理会计影响")
    with c4:
        render_kpi_card("数据质量状态", quality_status, status=quality_status, help_text="data_quality_report.json")
    chart_df = pd.DataFrame({"类别": ["佣金异常", "分摊异常"], "数量": [(rec["status"] == "EXCEPTION").sum(), (alloc["status"] == "EXCEPTION").sum()]})
    fig = px.bar(chart_df, x="类别", y="数量", text_auto=True, title="月结异常数量概览")
    fig.update_yaxes(title="数量")
    st.plotly_chart(fig, width="stretch")
    st.caption("先用异常数量判断本月月结风险，再进入明细页面定位具体批次。")

elif page == "经纪佣金收入勾稽检查":
    rec = reconcile_commission_to_gl(period)
    st.dataframe(_amount_view(rec), width="stretch")
    plot_df = rec.assign(
        **{
            "佣金计算金额（万元）": rec["commission_amount"] / 10000,
            "收入子账金额（万元）": rec["subledger_amount"] / 10000,
            "总账凭证金额（万元）": rec["gl_amount"] / 10000,
        }
    )
    fig = px.bar(
        plot_df,
        x="branch_id",
        y=["佣金计算金额（万元）", "收入子账金额（万元）", "总账凭证金额（万元）"],
        barmode="group",
        title="经纪佣金收入链路勾稽（万元）",
    )
    fig.update_yaxes(title="金额（万元）")
    st.plotly_chart(fig, width="stretch")
    st.caption("三组金额应逐层一致；任一营业部柱形不齐即提示收入确认或入账链路需要复核。")

elif page == "费用分摊准确性检查":
    alloc = reconcile_allocation_result(period)
    st.dataframe(_amount_view(alloc), width="stretch")
    plot_df = alloc.assign(**{"费用池金额（万元）": alloc["amount"] / 10000, "已分摊金额（万元）": alloc["allocated_amount"] / 10000})
    fig = px.bar(plot_df, x="pool_id", y=["费用池金额（万元）", "已分摊金额（万元）"], barmode="group", title="费用池与分摊结果比对（万元）")
    fig.update_yaxes(title="金额（万元）")
    st.plotly_chart(fig, width="stretch")
    st.caption("费用池金额应被完整分摊；缺口通常来自比例不满、规则版本错误或分摊因子缺失。")

elif page == "异常清单":
    grades = grade_all_exceptions(period)
    view = exceptions.merge(grades, on=["exception_id", "period"], how="left", suffixes=("", "_graded"))
    severity_options = ["ALL"] + sorted(view["severity_graded"].dropna().unique().tolist())
    selected_severity = st.selectbox("严重等级", severity_options)
    if selected_severity != "ALL":
        view = view[view["severity_graded"] == selected_severity]
    if not view.empty:
        view = view.copy()
        view["severity_badge"] = view["severity_graded"].fillna("UNKNOWN")
        render_section_title("异常分布", "⚠️")
        cols = st.columns(3)
        for idx, severity in enumerate(["HIGH", "MEDIUM", "LOW"]):
            with cols[idx]:
                render_kpi_card(f"{severity} 异常", str(int((view["severity_badge"] == severity).sum())), status=severity)
    st.dataframe(_amount_view(view), width="stretch")
    if not view.empty:
        high_view = view[view["severity_badge"] == "HIGH"].head(3)
        if not high_view.empty:
            render_section_title("高风险异常", "🚨")
            for row in high_view.itertuples():
                render_info_card(
                    str(row.exception_id),
                    f"类型：{row.exception_type}；差异金额：{format_wan(row.diff_amount)}；疑似原因：{row.suspected_reason}",
                    icon="⚠️",
                    border_color=severity_color("HIGH"),
                )
    st.caption("严重等级按影响链路、差异金额和处理优先级生成，用于区分总账风险和管理会计口径风险。")

elif page == "异常详情":
    if exceptions.empty:
        st.info("本期间未检测到异常。")
    else:
        exception_id = st.selectbox("异常编号", exceptions["exception_id"].tolist())
        st.dataframe(_amount_view(exceptions[exceptions["exception_id"] == exception_id]), width="stretch")
        with st.container(border=True):
            grade = grade_exception(exception_id)
            st.subheader("异常分级")
            c1, c2 = st.columns(2)
            c1.metric("严重等级", grade["severity"])
            c2.metric("处理优先级", grade["recommended_priority"])
            st.write(grade["severity_reason"])
        st.subheader("相似历史案例")
        st.markdown(format_matched_cases_markdown(exception_id))
        st.write(explain_exception_mock(exception_id))
        question = st.text_input("追问")
        if question:
            st.write("模板回答：该问题需要基于异常金额、批次日志、源表到目标表链路逐项核验。当前 PoC 已固定金额证据，不由模型重新计算金额。")

elif page == "异常证据链":
    if exceptions.empty:
        st.info("本期间未检测到异常。")
    else:
        exception_id = st.selectbox("异常编号", exceptions["exception_id"].tolist())
        chain = build_evidence_chain(exception_id)
        with st.container(border=True):
            render_section_title("差异定位结论", "✅")
            grade = grade_exception(exception_id)
            c1, c2 = st.columns(2)
            with c1:
                render_kpi_card("差异金额", format_wan(chain["diff_amount"]), status=grade["severity"])
            with c2:
                render_kpi_card("严重等级", grade["severity"], status=grade["severity"], help_text=grade["recommended_priority"])
            st.markdown(f"**差异发生层级：** {chain['breakpoint']}")
            st.markdown(f"**根因：** {chain['root_cause']}")
            st.markdown(f"**建议动作：** {chain['recommended_action']}")
        st.subheader("异常基本信息")
        st.json({
            "exception_id": chain["exception_id"],
            "scenario": chain["scenario"],
            "exception_type": chain["exception_type"],
            "period": chain["period"],
            "diff_amount（万元）": round(chain["diff_amount"] / 10000, 2),
            "trace_key": chain["trace_key"],
        })
        render_section_title("逐层穿透 Timeline", "🧩")
        _render_trace_timeline(chain)
        st.subheader("逐层穿透明细")
        st.dataframe(_trace_steps_view(chain["trace_steps"]), width="stretch")
        st.subheader("差异发生点")
        st.info(chain["breakpoint"])
        st.subheader("mock Agent 归因说明")
        st.write(explain_exception_mock(exception_id))
        st.subheader("处理建议")
        st.write(chain["recommended_action"])
        with st.expander("Markdown 证据链"):
            st.markdown(format_evidence_chain_markdown(exception_id))

elif page == "可信数据导出":
    st.subheader("可信数据导出")
    st.caption("导出经过月结校验标记的收入、费用分摊和校验汇总数据，供管理会计分析使用。")
    if st.button("生成导出文件", type="primary"):
        paths = export_all()
        st.session_state["validated_export_paths"] = [str(path) for path in paths]
    paths = st.session_state.get("validated_export_paths")
    if paths:
        for path in paths:
            st.success(path)
    summary_path = export_validation_summary(period)
    if summary_path.exists():
        st.dataframe(_amount_view(pd.read_csv(summary_path)), width="stretch")

elif page == "AI / mock 归因报告":
    if exceptions.empty:
        st.info("本期间未检测到异常。")
    else:
        exception_id = st.selectbox("选择异常", exceptions["exception_id"].tolist())
        report = generate_root_cause_report(exception_id)
        st.markdown(report)
        if st.button("导出 Markdown 归因报告", type="primary"):
            output_path = export_root_cause_report(exception_id)
            st.success(f"已导出：{output_path}")

else:
    render_section_title("Agent 工作台", "🤖")
    st.caption("输入自然语言任务，Agent 会自动规划分析步骤、调用现有校验与证据链工具，并展示可追溯的观察结果。")
    llm_config = load_llm_config()
    use_llm = st.checkbox("使用 LLM 增强回答", value=llm_config.enabled)
    st.info(_llm_status_text(use_llm))
    _show_llm_config_status()
    if use_llm and is_llm_available():
        st.caption(f"当前模型：{llm_config.model}")
    elif use_llm and llm_config.enabled:
        st.warning("LLM 配置不完整，页面将自动使用 Mock Agent。")
    default_task = f"请分析 {period} 经纪佣金收入差异最大的异常，并定位根因。"
    user_task = st.text_area("自然语言任务", value=default_task, height=100)
    col1, col2 = st.columns(2)
    agent_period = col1.selectbox("Agent 分析期间", [f"2025-{m:02d}" for m in range(1, 13)], index=int(period[-2:]) - 1)
    exception_options = ["自动识别"]
    if not exceptions.empty:
        exception_options.extend(exceptions["exception_id"].tolist())
    selected_exception = col2.selectbox("异常编号（可选）", exception_options)
    exception_arg = None if selected_exception == "自动识别" else selected_exception

    if st.button("运行 Agent", type="primary"):
        st.session_state["month_end_agent_use_llm"] = use_llm
        st.session_state["month_end_agent_result"] = run_month_end_agent(user_task, agent_period, exception_arg, use_llm=use_llm)
        st.session_state["month_end_agent_trace"] = run_month_end_agent_with_trace(user_task, agent_period, exception_arg)

    result = st.session_state.get("month_end_agent_result")
    if result:
        if result.llm_error:
            st.warning(result.llm_error)
        trace = st.session_state.get("month_end_agent_trace")
        if trace:
            _render_explainable_trace(trace)
        st.subheader("Agent 分析计划")
        for idx, item in enumerate(result.plan, start=1):
            st.markdown(f"{idx}. {item}")

        st.subheader("工具调用轨迹")
        st.dataframe(_agent_steps_view(result), width="stretch")

        st.subheader("每一步观察结果")
        for step in result.steps:
            with st.expander(f"步骤 {step.step_no}：{step.tool_name}"):
                st.markdown(f"**规划意图：** {step.thought}")
                st.json(step.tool_input)
                st.write(step.observation)

        with st.container(border=True):
            render_section_title("最终分析结论", "✅")
            if result.severity:
                c1, c2 = st.columns(2)
                with c1:
                    render_kpi_card("严重等级", result.severity.get("severity", "UNKNOWN"), status=result.severity.get("severity", "UNKNOWN"))
                with c2:
                    render_kpi_card("处理优先级", result.severity.get("recommended_priority", "待评估"), status=result.severity.get("severity", "UNKNOWN"))
            if result.matched_cases:
                top_case = result.matched_cases[0]
                st.caption(f"最高匹配历史案例：{top_case['case_id']}，匹配分数 {top_case['match_score']}。")
            render_info_card("归因结论", result.final_answer, icon="✅", border_color="#059669")

        if result.evidence_chain:
            st.subheader("证据链")
            st.dataframe(_trace_steps_view(result.evidence_chain["trace_steps"]), width="stretch")
            st.info(f"差异发生点：{result.evidence_chain['breakpoint']}")

        followup = st.text_input("追问", placeholder="例如：影响金额是多少？建议动作是什么？")
        if followup:
            st.write(answer_month_end_followup(followup, result, use_llm=st.session_state.get("month_end_agent_use_llm", use_llm)))
