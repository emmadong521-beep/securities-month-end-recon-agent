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

if page == "月结批次概览":
    rec = reconcile_commission_to_gl(period)
    alloc = reconcile_allocation_result(period)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("佣金批次", len(rec))
    c2.metric("异常批次", int((rec["status"] == "EXCEPTION").sum()))
    c3.metric("费用池", len(alloc))
    c4.metric("异常费用池", int((alloc["status"] == "EXCEPTION").sum()))
    chart_df = pd.DataFrame({"类别": ["佣金异常", "分摊异常"], "数量": [(rec["status"] == "EXCEPTION").sum(), (alloc["status"] == "EXCEPTION").sum()]})
    st.plotly_chart(px.bar(chart_df, x="类别", y="数量", text_auto=True), width="stretch")

elif page == "经纪佣金收入勾稽检查":
    rec = reconcile_commission_to_gl(period)
    st.dataframe(rec, width="stretch")
    st.plotly_chart(px.bar(rec, x="branch_id", y=["commission_amount", "subledger_amount", "gl_amount"], barmode="group"), width="stretch")

elif page == "费用分摊准确性检查":
    alloc = reconcile_allocation_result(period)
    st.dataframe(alloc, width="stretch")
    st.plotly_chart(px.bar(alloc, x="pool_id", y=["amount", "allocated_amount"], barmode="group"), width="stretch")

elif page == "异常清单":
    st.dataframe(exceptions, width="stretch")

elif page == "异常详情":
    if exceptions.empty:
        st.info("本期间未检测到异常。")
    else:
        exception_id = st.selectbox("异常编号", exceptions["exception_id"].tolist())
        st.dataframe(exceptions[exceptions["exception_id"] == exception_id], width="stretch")
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
        st.subheader("异常基本信息")
        st.json({k: chain[k] for k in ["exception_id", "scenario", "exception_type", "period", "diff_amount", "trace_key"]})
        st.subheader("逐层穿透")
        st.dataframe(pd.DataFrame(chain["trace_steps"]), width="stretch")
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
        st.markdown(generate_root_cause_report(exception_id))
