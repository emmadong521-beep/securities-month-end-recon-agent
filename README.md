# securities-month-end-recon-agent

中文名：证券公司月结差异归因 Agent

本项目模拟证券公司月结期间，经纪业务佣金收入、收入子账、总账凭证、费用分摊结果之间的差异识别与根因归因。项目一的定位是“先保证月结数据准确、可追溯”，项目二再基于可信月结数据做管理会计分析。

## 数据来源说明

审计报告路径通过 `.env` 的 `AUDIT_REPORT_PATH` 配置，默认指向：

`/Users/dongkaixin/Downloads/财务agent项目/管理会计多维盈利分析/长江证券2025年审计财报.pdf`

PDF 不会提交到仓库。`src/load_audit_report.py` 会尝试解析公开披露汇总指标，解析失败时使用 `data/raw/audit_report_metrics_template.yaml` 和代码内置的公开汇总口径 fallback。明细交易、客户、凭证、营业部、费用分摊数据全部为合成测试数据。

本项目仅用于个人学习和求职作品集。项目使用公开披露数据进行规模校准，明细数据均为合成数据，不代表长江证券真实客户、交易、凭证、营业部或内部经营数据，不包含任何未公开重大信息、客户隐私数据或商业秘密，不构成投资建议。

## 业务场景

1. 经纪业务佣金收入上游系统与总账差异归因：`trade_flow -> commission_calc -> revenue_subledger -> gl_journal -> gl_balance`
2. 营业部 / 业务线费用分摊结果准确性比对：`expense_pool -> allocation_rule -> allocation_driver -> allocation_result`

## 审计报告校准口径

造数使用审计报告公开披露的 2025 年营业总收入、手续费及佣金净收入、代理买卖证券业务收入、业务及管理费等汇总金额做规模校准。所有明细行均为按证券公司业务逻辑构造的合成数据。

## 运行方式

```bash
cd /Users/dongkaixin/Downloads/财务agent项目/securities-month-end-recon-agent
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m src.seed_data
.venv/bin/python -m src.db
.venv/bin/python -m pytest
.venv/bin/streamlit run src/app.py
```

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

面试展示时可在启动 Streamlit 后截取：月结批次概览、经纪佣金勾稽、费用分摊检查、异常详情、mock 归因报告五张图。

## 简历写法建议

- 构建证券公司月结差异归因 Agent PoC，基于公开审计报告汇总口径校准合成数据，打通交易流水、佣金计算、收入子账、总账凭证和费用分摊链路。
- 设计 DuckDB + pandas 的可追溯勾稽引擎，内置缺批次、少入账、重复凭证、科目映射错误、分摊比例不平等异常，并生成证据链归因报告。

## 后续扩展方向

- 接入真实企业数据脱敏样例或数据质量平台
- 增加凭证冲销、重跑批次、审批流模拟
- 接入 LLM API，但保持金额由规则和 SQL 计算，模型只负责表达
