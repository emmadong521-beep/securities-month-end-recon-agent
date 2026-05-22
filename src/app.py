from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
import pandas as pd
import plotly.express as px

from src.db import load_synthetic_data_to_duckdb
from src.evidence_chain import build_evidence_chain, format_evidence_chain_markdown
from src.validation import (
    detect_reconciliation_exceptions,
    explain_exception_mock,
    export_root_cause_report,
    generate_root_cause_report,
    reconcile_allocation_result,
    reconcile_commission_to_gl,
)


st.set_page_config(page_title="证券公司月结差异归因 Agent", layout="wide")
st.title("证券公司月结差异归因 Agent")

load_synthetic_data_to_duckdb()
period = st.sidebar.selectbox("会计期间", [f"2025-{m:02d}" for m in range(1, 13)], index=2)
page = st.sidebar.radio(
    "功能",
    ["月结批次概览", "经纪佣金收入勾稽检查", "费用分摊准确性检查", "异常清单", "异常详情", "异常证据链", "AI / mock 归因报告"],
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


def _recommended_demo_path() -> None:
    with st.container(border=True):
        st.subheader("推荐演示路径")
        st.markdown(
            """
1. 在侧边栏选择 `2025-03`，先看“月结批次概览”确认本月异常数量。
2. 进入“经纪佣金收入勾稽检查”，定位佣金计算、收入子账、总账之间的金额差异。
3. 切换到 `2025-06` 至 `2025-08`，查看费用分摊比例、规则版本和分摊因子异常。
4. 打开“异常清单”，选择一条异常进入“异常证据链”。
5. 查看“差异定位结论”和逐层穿透表，再导出 Markdown 归因报告。
            """
        )

if page == "月结批次概览":
    _recommended_demo_path()
    rec = reconcile_commission_to_gl(period)
    alloc = reconcile_allocation_result(period)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("佣金批次", len(rec))
    c2.metric("异常批次", int((rec["status"] == "EXCEPTION").sum()))
    c3.metric("费用池", len(alloc))
    c4.metric("异常费用池", int((alloc["status"] == "EXCEPTION").sum()))
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
    st.dataframe(_amount_view(exceptions), width="stretch")

elif page == "异常详情":
    if exceptions.empty:
        st.info("本期间未检测到异常。")
    else:
        exception_id = st.selectbox("异常编号", exceptions["exception_id"].tolist())
        st.dataframe(_amount_view(exceptions[exceptions["exception_id"] == exception_id]), width="stretch")
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
            st.subheader("差异定位结论")
            c1, c2 = st.columns(2)
            c1.metric("差异金额", f"{chain['diff_amount'] / 10000:,.2f} 万元")
            c2.metric("差异发生层级", chain["breakpoint"])
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
        st.subheader("逐层穿透")
        st.dataframe(_trace_steps_view(chain["trace_steps"]), width="stretch")
        st.subheader("差异发生点")
        st.info(chain["breakpoint"])
        st.subheader("mock Agent 归因说明")
        st.write(explain_exception_mock(exception_id))
        st.subheader("处理建议")
        st.write(chain["recommended_action"])
        with st.expander("Markdown 证据链"):
            st.markdown(format_evidence_chain_markdown(exception_id))

else:
    if exceptions.empty:
        st.info("本期间未检测到异常。")
    else:
        exception_id = st.selectbox("选择异常", exceptions["exception_id"].tolist())
        report = generate_root_cause_report(exception_id)
        st.markdown(report)
        if st.button("导出 Markdown 归因报告"):
            output_path = export_root_cause_report(exception_id)
            st.success(f"已导出：{output_path}")
