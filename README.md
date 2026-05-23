# securities-month-end-recon-agent

中文名：证券公司月结差异归因 Agent

本项目是证券行业财务 AI 应用 PoC，模拟证券公司月结期间经纪业务佣金收入、收入子账、总账凭证、总账余额和费用分摊结果之间的差异识别、证据链穿透和根因归因。项目一用于保证月结数据准确、可追溯；项目二可基于可信月结数据开展管理会计分析和经营决策支持。

## 数据来源说明

审计报告路径通过 `.env` 的 `AUDIT_REPORT_PATH` 配置：

```bash
cp .env.example .env
# 在 .env 中配置 AUDIT_REPORT_PATH=/path/to/your/audit_report.pdf
```

PDF 不会提交到仓库。`src/load_audit_report.py` 会尝试解析公开披露汇总指标，解析失败时使用 `data/raw/audit_report_metrics_template.yaml` 和代码内置 fallback。客户、交易、凭证、营业部、费用池和分摊结果均为合成数据。

本项目仅用于个人研究型 PoC。项目使用公开披露数据进行规模校准，明细数据均为合成数据，不代表长江证券真实客户、交易、凭证、营业部或内部经营数据，不包含任何未公开重大信息、客户隐私数据或商业秘密，不构成投资建议。

## 业务场景

1. 经纪业务佣金收入上游系统与总账差异归因：`trade_flow -> commission_calc -> revenue_subledger -> gl_journal -> gl_balance`
2. 营业部 / 业务线费用分摊结果准确性比对：`expense_pool -> allocation_rule -> allocation_driver -> allocation_result`
3. 异常证据链：按异常编号穿透交易、佣金、子账、总账或费用池、规则、因子、分摊结果。

## 运行方式

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m src.seed_data
.venv/bin/python -m src.db
.venv/bin/python -m pytest
.venv/bin/streamlit run src/app.py
```

一键启动本地 Demo：

```bash
./scripts/run_demo.sh
```

## Quick Demo Path

1. 打开首页“月结批次概览”，选择 `2025-03`，查看本月异常批次数量。
2. 进入“经纪佣金收入勾稽检查”，对比佣金计算、收入子账和总账凭证金额（万元）。
3. 切换 `2025-06`、`2025-07`、`2025-08`，在“费用分摊准确性检查”查看比例、规则版本和分摊因子异常。
4. 打开“异常清单”，选择需要穿透的异常编号。
5. 进入“异常证据链”，查看差异定位结论、逐层证据和处理建议。
6. 进入“Agent 工作台”，输入自然语言任务，查看分析计划、工具调用轨迹、观察结果和追问回答。
7. 在“AI / mock 归因报告”中导出 Markdown 报告到 `data/output/`。

## Agent 工作台

`src/agent.py` 提供 deterministic mock Agent 层，不强制依赖外部 LLM。它会根据自然语言任务识别期间、异常编号和任务类型，真实调用现有函数：

- `detect_reconciliation_exceptions`
- `build_evidence_chain`
- `generate_root_cause_report`
- `export_root_cause_report`

Streamlit 的“Agent 工作台”会展示用户任务、自动分析计划、工具调用轨迹、每一步观察结果、最终结论、证据链和追问回答。第一版支持经纪佣金收入差异、费用分摊异常和指定异常编号三类任务。

## 数据质量检查

```bash
.venv/bin/python -m src.data_quality
```

输出文件：

- `data/output/data_quality_report.md`
- `data/output/data_quality_report.json`

检查内容包括核心表行数、主键唯一性、外键完整性、关键金额空值、金额勾稽、异常案例埋入与检测、公开汇总指标规模校准和 PASS / WARNING / FAIL 结论。

## 主要表

`chart_of_accounts`, `branch_master`, `biz_line_master`, `customer_master`, `trade_flow`, `commission_calc`, `revenue_subledger`, `gl_journal`, `gl_balance`, `expense_pool`, `allocation_rule`, `allocation_driver`, `allocation_result`, `interface_batch_log`, `reconciliation_exception`, `root_cause_case`

## 内置异常演示入口

- 2025-03：广州营业部经纪佣金批次未进入收入确认
- 2025-04：北京营业部部分收入子账未生成总账凭证
- 2025-05：上海营业部总账凭证重复推送
- 2025-09 / 2025-10：财富管理代销收入误入经纪佣金科目
- 2025-06：费用池分摊比例合计小于 100%
- 2025-07：本月应使用 V2 分摊规则但结果使用 V1
- 2025-08：成都营业部缺失分摊因子

## Demo 截图占位

可在启动 Streamlit 后截取：月结批次概览、经纪佣金勾稽、费用分摊检查、异常清单、异常证据链和 mock 归因报告页面。

## 后续扩展方向

- 接入脱敏后的企业数据样例或数据质量平台
- 增加凭证冲销、重跑批次、审批流模拟
- 接入 LLM API，但保持金额由规则和 SQL 计算，模型只负责表达
