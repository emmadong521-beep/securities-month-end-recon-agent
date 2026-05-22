# 表结构

- chart_of_accounts：总账科目表，采用 1xxx 资产、2xxx 负债、3xxx 共同、4xxx 权益、5xxx 成本、6xxx 损益编码体系。
- branch_master：营业部主数据。
- biz_line_master：经纪、投行、资管、自营、信用、财富管理、总部管理业务线。
- customer_master：客户主数据，含 RETAIL、HNW、INSTITUTION。
- trade_flow：证券交易流水，含交易金额、佣金率、清算批次。
- commission_calc：佣金计算结果，含毛佣金、折扣、税额、收入金额。
- revenue_subledger：收入子账，保留来源单据和确认批次。
- gl_journal：总账凭证行，保留来源系统、来源单据、批次和科目。
- gl_balance：按期间、营业部、业务线、科目汇总的余额。
- expense_pool：费用池。
- allocation_rule：分摊规则及版本。
- allocation_driver：分摊因子。
- allocation_result：分摊结果。
- interface_batch_log：接口批次日志。
- reconciliation_exception：差异异常清单。
- root_cause_case：历史异常案例库。

## 输出报告

- data_quality_report：由 `python -m src.data_quality` 生成，包含行数、主键、外键、金额空值、金额勾稽、异常埋入与检测、公开指标校准和检查结论。
- evidence_chain：由 `src/evidence_chain.py` 动态生成，按异常编号展示收入链路或费用分摊链路的逐层证据。
