import json

from src.agent import run_month_end_agent_with_trace
from src.agent_trace import ReasoningTrace, StepType
from src.db import load_synthetic_data_to_duckdb
from src.seed_data import generate_synthetic_data


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_month_end_agent_trace_contains_required_steps():
    trace = run_month_end_agent_with_trace("请分析 2025-03 经纪佣金收入差异最大的异常，并定位根因。")

    assert isinstance(trace, ReasoningTrace)
    assert trace.steps
    step_types = {step.step_type for step in trace.steps}
    assert StepType.INTENT_RECOGNITION in step_types
    assert StepType.PLAN_GENERATION in step_types
    assert StepType.TOOL_CALL in step_types
    assert StepType.OBSERVATION in step_types
    assert StepType.CONCLUSION in step_types
    assert trace.final_answer


def test_month_end_agent_trace_contains_evidence_chain_tool_and_serializes():
    trace = run_month_end_agent_with_trace("请分析异常 EXC_202503_001 的根因。")

    tool_names = {step.tool_name for step in trace.steps if step.tool_name}
    assert "build_evidence_chain" in tool_names
    assert "grade_exception" in tool_names
    assert "match_root_cause_cases" in tool_names
    assert "generate_root_cause_report" in tool_names
    json.dumps(trace.to_dict(), ensure_ascii=False, default=str)
