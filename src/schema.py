CHART_OF_ACCOUNTS = [
    {"account_code": "1001", "account_name": "库存现金", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "现金"},
    {"account_code": "1002", "account_name": "银行存款", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "自有及客户银行存款"},
    {"account_code": "1012", "account_name": "其他货币资金", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "其他货币资金"},
    {"account_code": "1021", "account_name": "结算备付金", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "证券结算备付金"},
    {"account_code": "1031", "account_name": "存出保证金", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "交易及信用保证金"},
    {"account_code": "1101", "account_name": "交易性金融资产", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "以公允价值计量且其变动计入当期损益的金融资产"},
    {"account_code": "1111", "account_name": "买入返售金融资产", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "买入返售金融资产"},
    {"account_code": "1122", "account_name": "应收账款", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应收手续费及清算款"},
    {"account_code": "1131", "account_name": "应收股利", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应收股利"},
    {"account_code": "1132", "account_name": "应收利息", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应收利息"},
    {"account_code": "1201", "account_name": "融出资金", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "融资融券融出资金"},
    {"account_code": "1221", "account_name": "其他应收款", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "其他应收款"},
    {"account_code": "1231", "account_name": "坏账准备", "account_class": "资产类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "1122", "is_leaf": True, "description": "应收款减值准备"},
    {"account_code": "1501", "account_name": "持有至到期投资", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "持有至到期投资"},
    {"account_code": "1511", "account_name": "长期股权投资", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "长期股权投资"},
    {"account_code": "1601", "account_name": "固定资产", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "固定资产"},
    {"account_code": "1602", "account_name": "累计折旧", "account_class": "资产类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "1601", "is_leaf": True, "description": "累计折旧"},
    {"account_code": "1701", "account_name": "无形资产", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "无形资产"},
    {"account_code": "1811", "account_name": "递延所得税资产", "account_class": "资产类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "递延所得税资产"},
    {"account_code": "2001", "account_name": "短期借款", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "短期借款"},
    {"account_code": "2101", "account_name": "交易性金融负债", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "交易性金融负债"},
    {"account_code": "2111", "account_name": "卖出回购金融资产款", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "卖出回购业务融资"},
    {"account_code": "2201", "account_name": "应付票据", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应付票据"},
    {"account_code": "2202", "account_name": "应付账款", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应付款项"},
    {"account_code": "2211", "account_name": "应付职工薪酬", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应付职工薪酬"},
    {"account_code": "2221", "account_name": "应交税费", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应交税费"},
    {"account_code": "2231", "account_name": "应付利息", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "应付利息"},
    {"account_code": "2241", "account_name": "其他应付款", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "其他应付款"},
    {"account_code": "2311", "account_name": "代理买卖证券款", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "客户交易结算资金"},
    {"account_code": "2501", "account_name": "长期借款", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "长期借款"},
    {"account_code": "2801", "account_name": "预计负债", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "预计负债"},
    {"account_code": "2901", "account_name": "递延所得税负债", "account_class": "负债类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "递延所得税负债"},
    {"account_code": "4001", "account_name": "实收资本或股本", "account_class": "所有者权益类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "股本"},
    {"account_code": "4002", "account_name": "资本公积", "account_class": "所有者权益类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "资本公积"},
    {"account_code": "4101", "account_name": "盈余公积", "account_class": "所有者权益类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "法定盈余公积"},
    {"account_code": "4103", "account_name": "本年利润", "account_class": "所有者权益类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "本年利润"},
    {"account_code": "4104", "account_name": "利润分配", "account_class": "所有者权益类", "normal_balance": "CR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "未分配利润"},
    {"account_code": "4201", "account_name": "库存股", "account_class": "所有者权益类", "normal_balance": "DR", "statement_type": "BS", "parent_account_code": "", "is_leaf": True, "description": "库存股"},
    {"account_code": "5001", "account_name": "业务成本归集", "account_class": "成本类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "成本归集"},
    {"account_code": "6001", "account_name": "主营业务收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "营业收入"},
    {"account_code": "6011", "account_name": "利息收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6001", "is_leaf": True, "description": "利息收入"},
    {"account_code": "6021", "account_name": "手续费及佣金收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6001", "is_leaf": True, "description": "经纪及其他手续费佣金收入"},
    {"account_code": "6022", "account_name": "财富管理代销收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6021", "is_leaf": True, "description": "代销金融产品收入"},
    {"account_code": "6023", "account_name": "投资银行业务收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6021", "is_leaf": True, "description": "承销保荐及财务顾问收入"},
    {"account_code": "6024", "account_name": "资产管理业务收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6021", "is_leaf": True, "description": "资管及基金管理费"},
    {"account_code": "6031", "account_name": "投资收益", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6001", "is_leaf": True, "description": "金融工具投资收益"},
    {"account_code": "6041", "account_name": "公允价值变动损益", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6001", "is_leaf": True, "description": "公允价值变动收益"},
    {"account_code": "6051", "account_name": "其他业务收入", "account_class": "损益类", "normal_balance": "CR", "statement_type": "PL", "parent_account_code": "6001", "is_leaf": True, "description": "其他业务收入"},
    {"account_code": "6111", "account_name": "手续费及佣金支出", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "手续费及佣金支出"},
    {"account_code": "6401", "account_name": "主营业务成本", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "主营业务成本"},
    {"account_code": "6402", "account_name": "其他业务成本", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "其他业务成本"},
    {"account_code": "6411", "account_name": "利息支出", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "利息支出"},
    {"account_code": "6601", "account_name": "销售费用", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "销售费用"},
    {"account_code": "6602", "account_name": "管理费用", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "业务及管理费"},
    {"account_code": "6603", "account_name": "财务费用", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "财务费用"},
    {"account_code": "6701", "account_name": "资产减值损失", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "资产减值损失"},
    {"account_code": "6711", "account_name": "信用减值损失", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "信用减值损失"},
    {"account_code": "6801", "account_name": "所得税费用", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "所得税费用"},
    {"account_code": "6901", "account_name": "以前年度损益调整", "account_class": "损益类", "normal_balance": "DR", "statement_type": "PL", "parent_account_code": "", "is_leaf": True, "description": "以前年度损益调整"},
]

from pydantic import BaseModel, Field


TABLE_COLUMNS = {
    "chart_of_accounts": ["account_code", "account_name", "account_class", "normal_balance", "statement_type", "parent_account_code", "is_leaf", "description"],
    "branch_master": ["branch_id", "branch_name", "region", "city", "open_date", "status"],
    "biz_line_master": ["biz_line_id", "biz_line_name", "description"],
    "customer_master": ["customer_id", "customer_type", "branch_id", "risk_level", "open_date", "status"],
    "trade_flow": ["trade_id", "trade_date", "settle_date", "customer_id", "branch_id", "product_type", "market", "buy_sell", "trade_amount", "commission_rate", "calculated_commission", "clearing_batch_id"],
    "commission_calc": ["commission_id", "trade_id", "calc_date", "commission_rate", "gross_commission", "discount_amount", "net_commission", "tax_amount", "revenue_amount", "calc_batch_id", "status"],
    "revenue_subledger": ["subledger_id", "source_system", "source_doc_id", "period", "biz_line_id", "branch_id", "customer_type", "account_code", "amount", "dr_cr", "accounting_standard", "recognition_batch_id", "status"],
    "gl_journal": ["journal_id", "journal_line_id", "period", "posting_date", "source_system", "source_doc_id", "batch_id", "company_code", "branch_id", "biz_line_id", "account_code", "account_name", "dr_cr", "amount", "currency", "description", "posting_status"],
    "gl_balance": ["period", "company_code", "branch_id", "biz_line_id", "account_code", "opening_balance", "debit_amount", "credit_amount", "ending_balance"],
    "expense_pool": ["pool_id", "period", "cost_type", "cost_name", "amount", "source_account_code", "allocation_basis", "owner_dept"],
    "allocation_rule": ["rule_id", "rule_version", "period", "cost_type", "allocation_basis", "target_dimension", "effective_start", "effective_end", "is_active", "description"],
    "allocation_driver": ["driver_id", "period", "rule_id", "target_id", "target_type", "driver_value", "driver_weight"],
    "allocation_result": ["allocation_id", "period", "pool_id", "rule_id", "target_id", "target_type", "allocated_amount", "allocation_ratio", "posting_status", "management_account_code"],
    "interface_batch_log": ["batch_id", "source_system", "target_system", "period", "start_time", "end_time", "record_count", "total_amount", "status", "error_message"],
    "reconciliation_exception": ["exception_id", "period", "scenario", "exception_type", "severity", "source_table", "target_table", "source_amount", "target_amount", "diff_amount", "diff_rate", "suspected_reason", "status"],
    "root_cause_case": ["case_id", "scenario", "exception_type", "symptom", "root_cause", "evidence_pattern", "recommended_action"],
}

CORE_TABLES = list(TABLE_COLUMNS.keys())


class ReconciliationException(BaseModel):
    exception_id: str
    period: str
    scenario: str
    exception_type: str
    severity: str = Field(pattern="^(LOW|MEDIUM|HIGH)$")
    source_table: str
    target_table: str
    source_amount: float
    target_amount: float
    diff_amount: float
    diff_rate: float
    suspected_reason: str
    status: str = "OPEN"
