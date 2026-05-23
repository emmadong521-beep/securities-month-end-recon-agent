from src.agent import AgentResult, answer_month_end_followup, run_month_end_agent
from src.db import load_synthetic_data_to_duckdb
from src.seed_data import generate_synthetic_data


def setup_module():
    generate_synthetic_data()
    load_synthetic_data_to_duckdb()


def test_run_month_end_agent_returns_result():
    result = run_month_end_agent("请分析 2025-03 经纪佣金收入差异最大的异常，并定位根因。", use_llm=False)
    assert isinstance(result, AgentResult)
    assert result.plan
    assert result.steps
    assert result.final_answer


def test_agent_steps_include_core_tools():
    result = run_month_end_agent("请分析异常 EXC_202503_001 的根因。", use_llm=False)
    tool_names = {step.tool_name for step in result.steps}
    assert "build_evidence_chain" in tool_names
    assert "grade_exception" in tool_names
    assert "match_root_cause_cases" in tool_names
    assert "generate_root_cause_report" in tool_names
    assert "严重等级" in result.final_answer


def test_agent_followup_answers_amount_and_action():
    result = run_month_end_agent("请检查 2025-06 费用分摊异常，说明差异发生在哪个环节。", use_llm=False)
    amount_answer = answer_month_end_followup("影响金额是多少？", result, use_llm=False)
    action_answer = answer_month_end_followup("建议动作是什么？", result, use_llm=False)
    risk_answer = answer_month_end_followup("为什么判断为高风险？", result, use_llm=False)
    case_answer = answer_month_end_followup("这个异常和哪些历史案例相似？", result, use_llm=False)
    assert "万元" in amount_answer
    assert "建议动作" in action_answer
    assert "严重等级" in risk_answer
    assert "相似历史案例" in case_answer


def test_agent_falls_back_when_llm_unavailable(monkeypatch):
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "volcengine")
    monkeypatch.setenv("ARK_API_KEY", "your_ark_api_key_here")
    result = run_month_end_agent("请分析 2025-03 经纪佣金收入差异最大的异常，并定位根因。", use_llm=True)
    tool_names = {step.tool_name for step in result.steps}
    assert result.final_answer
    assert result.llm_mode == "Mock Agent"
    assert result.llm_error
    assert "build_evidence_chain" in tool_names
