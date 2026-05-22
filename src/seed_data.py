from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from .config import COMPANY_CODE, RANDOM_SEED, SYNTHETIC_DIR
from .load_audit_report import load_audit_metrics
from .schema import CHART_OF_ACCOUNTS, TABLE_COLUMNS


PERIODS = [f"2025-{m:02d}" for m in range(1, 13)]
BRANCHES = [
    ("B001", "深圳营业部", "华南", "深圳", "2010-03-18"),
    ("B002", "上海营业部", "华东", "上海", "2008-06-12"),
    ("B003", "北京营业部", "华北", "北京", "2009-09-01"),
    ("B004", "广州营业部", "华南", "广州", "2011-04-20"),
    ("B005", "杭州营业部", "华东", "杭州", "2014-07-11"),
    ("B006", "成都营业部", "西南", "成都", "2012-10-08"),
    ("B007", "武汉营业部", "华中", "武汉", "2007-05-09"),
    ("B008", "南京营业部", "华东", "南京", "2015-11-22"),
]
BIZ_LINES = [
    ("BROKERAGE", "经纪业务", "代理买卖证券及交易单元收入"),
    ("IB", "投行业务", "承销保荐和财务顾问"),
    ("ASSET_MGMT", "资产管理", "集合资管和基金管理"),
    ("PROPRIETARY", "自营投资", "投资收益和公允价值变动"),
    ("MARGIN", "信用业务", "融资融券利息收入"),
    ("WEALTH", "财富管理", "代销金融产品和投顾"),
    ("HQ", "总部管理", "管理与共享服务"),
]
PRODUCTS = ["STOCK", "FUND", "BOND", "ETF"]
CUSTOMER_TYPES = ["RETAIL", "HNW", "INSTITUTION"]


def _money(value: float) -> float:
    return round(float(value), 2)


def _month_end_day(period: str, day: int = 28) -> str:
    return f"{period}-{day:02d}"


def _write_csv(output_dir: Path, name: str, rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=TABLE_COLUMNS.get(name))
    output_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_dir / f"{name}.csv", index=False)
    return df


def generate_synthetic_data(output_dir: str | Path = SYNTHETIC_DIR) -> dict[str, int]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(RANDOM_SEED)
    metrics = load_audit_metrics()
    brokerage_target = metrics["business_structure"]["代理买卖证券业务收入"]
    expense_target = metrics["income_statement"]["业务及管理费"] * 0.18

    branch_rows = [
        {"branch_id": bid, "branch_name": name, "region": region, "city": city, "open_date": open_date, "status": "ACTIVE"}
        for bid, name, region, city, open_date in BRANCHES
    ]
    biz_rows = [{"biz_line_id": bid, "biz_line_name": name, "description": desc} for bid, name, desc in BIZ_LINES]
    account_rows = CHART_OF_ACCOUNTS

    customer_rows = []
    branch_prob = np.array([0.16, 0.20, 0.13, 0.11, 0.09, 0.08, 0.14, 0.09])
    for i in range(1, 321):
        branch_id = rng.choice([b[0] for b in BRANCHES], p=branch_prob)
        ctype = rng.choice(CUSTOMER_TYPES, p=[0.72, 0.18, 0.10])
        customer_rows.append({
            "customer_id": f"C{i:05d}",
            "customer_type": ctype,
            "branch_id": branch_id,
            "risk_level": rng.choice(["C2", "C3", "C4", "C5"], p=[0.25, 0.45, 0.22, 0.08]),
            "open_date": f"{rng.integers(2015, 2025)}-{rng.integers(1, 13):02d}-{rng.integers(1, 28):02d}",
            "status": "ACTIVE" if rng.random() > 0.04 else "DORMANT",
        })
    customers = pd.DataFrame(customer_rows)

    season = np.array([0.073, 0.065, 0.082, 0.078, 0.085, 0.081, 0.076, 0.079, 0.091, 0.086, 0.098, 0.106])
    season = season / season.sum()
    branch_weight = dict(zip([b[0] for b in BRANCHES], branch_prob / branch_prob.sum()))

    trade_rows, commission_rows, subledger_rows, journal_rows = [], [], [], []
    interface_rows = []
    subledger_seq = 1
    journal_seq = 1
    trade_seq = 1
    for month_idx, period in enumerate(PERIODS):
        month_target = brokerage_target * season[month_idx]
        for branch_id, bw in branch_weight.items():
            branch_target = month_target * bw
            trade_weights = rng.dirichlet(np.ones(4))
            batch_id = f"COMM_{period.replace('-', '')}_{branch_id}"
            branch_customers = customers[customers["branch_id"] == branch_id]["customer_id"].to_numpy()
            for local_idx in range(4):
                customer_id = str(rng.choice(branch_customers))
                customer_type = customers.loc[customers["customer_id"] == customer_id, "customer_type"].iloc[0]
                product = rng.choice(PRODUCTS, p=[0.58, 0.17, 0.08, 0.17])
                rate_base = {"RETAIL": 0.00042, "HNW": 0.00034, "INSTITUTION": 0.00024}[customer_type]
                commission_rate = float(rate_base * rng.uniform(0.88, 1.08))
                revenue_amount = branch_target * trade_weights[local_idx]
                tax_amount = revenue_amount * 0.06
                net_commission = revenue_amount + tax_amount
                discount_amount = net_commission * rng.uniform(0.01, 0.035)
                gross_commission = net_commission + discount_amount
                trade_amount = gross_commission / commission_rate
                trade_id = f"T{trade_seq:07d}"
                commission_id = f"CM{trade_seq:07d}"
                trade_rows.append({
                    "trade_id": trade_id,
                    "trade_date": f"{period}-{rng.integers(1, 24):02d}",
                    "settle_date": f"{period}-{rng.integers(2, 27):02d}",
                    "customer_id": customer_id,
                    "branch_id": branch_id,
                    "product_type": product,
                    "market": rng.choice(["SSE", "SZSE", "BSE"], p=[0.48, 0.48, 0.04]),
                    "buy_sell": rng.choice(["BUY", "SELL"]),
                    "trade_amount": _money(trade_amount),
                    "commission_rate": round(commission_rate, 8),
                    "calculated_commission": _money(gross_commission),
                    "clearing_batch_id": batch_id,
                })
                commission_rows.append({
                    "commission_id": commission_id,
                    "trade_id": trade_id,
                    "calc_date": _month_end_day(period, 25),
                    "commission_rate": round(commission_rate, 8),
                    "gross_commission": _money(gross_commission),
                    "discount_amount": _money(discount_amount),
                    "net_commission": _money(net_commission),
                    "tax_amount": _money(tax_amount),
                    "revenue_amount": _money(revenue_amount),
                    "calc_batch_id": batch_id,
                    "status": "POSTED",
                })
                omit_subledger = period == "2025-03" and branch_id == "B004"
                if not omit_subledger:
                    subledger_id = f"SL{subledger_seq:07d}"
                    subledger_rows.append({
                        "subledger_id": subledger_id,
                        "source_system": "COMMISSION_SYSTEM",
                        "source_doc_id": commission_id,
                        "period": period,
                        "biz_line_id": "BROKERAGE",
                        "branch_id": branch_id,
                        "customer_type": customer_type,
                        "account_code": "6021",
                        "amount": _money(revenue_amount),
                        "dr_cr": "CR",
                        "accounting_standard": "CAS",
                        "recognition_batch_id": batch_id,
                        "status": "RECOGNIZED",
                    })
                    omit_gl = period == "2025-04" and branch_id == "B003" and local_idx in (0, 1)
                    if not omit_gl:
                        account_name = "手续费及佣金收入"
                        duplicate_times = 2 if (period == "2025-05" and branch_id == "B002" and local_idx == 0) else 1
                        for dup in range(duplicate_times):
                            jid = f"JV{journal_seq:07d}"
                            journal_rows.append({
                                "journal_id": jid,
                                "journal_line_id": f"{jid}-001",
                                "period": period,
                                "posting_date": _month_end_day(period),
                                "source_system": "REVENUE_SUBLEDGER",
                                "source_doc_id": subledger_id,
                                "batch_id": batch_id,
                                "company_code": COMPANY_CODE,
                                "branch_id": branch_id,
                                "biz_line_id": "BROKERAGE",
                                "account_code": "1122",
                                "account_name": "应收账款",
                                "dr_cr": "DR",
                                "amount": _money(revenue_amount),
                                "currency": "CNY",
                                "description": "经纪佣金收入应收确认",
                                "posting_status": "POSTED",
                            })
                            journal_rows.append({
                                "journal_id": jid,
                                "journal_line_id": f"{jid}-002",
                                "period": period,
                                "posting_date": _month_end_day(period),
                                "source_system": "REVENUE_SUBLEDGER",
                                "source_doc_id": subledger_id,
                                "batch_id": batch_id,
                                "company_code": COMPANY_CODE,
                                "branch_id": branch_id,
                                "biz_line_id": "BROKERAGE",
                                "account_code": "6021",
                                "account_name": account_name,
                                "dr_cr": "CR",
                                "amount": _money(revenue_amount),
                                "currency": "CNY",
                                "description": "经纪佣金收入入账" + ("-重复批次" if duplicate_times == 2 and dup == 1 else ""),
                                "posting_status": "POSTED",
                            })
                            journal_seq += 1
                    subledger_seq += 1
                trade_seq += 1
            interface_rows.append({
                "batch_id": batch_id,
                "source_system": "COMMISSION_SYSTEM",
                "target_system": "REVENUE_SUBLEDGER",
                "period": period,
                "start_time": f"{period}-28 21:00:00",
                "end_time": f"{period}-28 21:08:00",
                "record_count": 4,
                "total_amount": _money(branch_target),
                "status": "FAILED" if period == "2025-03" and branch_id == "B004" else "SUCCESS",
                "error_message": "营业部批次未进入收入确认" if period == "2025-03" and branch_id == "B004" else "",
            })

        wealth_amount = metrics["business_structure"]["代销金融产品业务收入"] * season[month_idx] * 0.18
        branch_id = "B005" if month_idx % 2 == 0 else "B002"
        subledger_id = f"SL{subledger_seq:07d}"
        subledger_rows.append({
            "subledger_id": subledger_id,
            "source_system": "WEALTH_SYSTEM",
            "source_doc_id": f"WL{period.replace('-', '')}",
            "period": period,
            "biz_line_id": "WEALTH",
            "branch_id": branch_id,
            "customer_type": "HNW",
            "account_code": "6021" if period in ("2025-09", "2025-10") else "6022",
            "amount": _money(wealth_amount),
            "dr_cr": "CR",
            "accounting_standard": "CAS",
            "recognition_batch_id": f"WEALTH_{period.replace('-', '')}",
            "status": "RECOGNIZED",
        })
        jid = f"JV{journal_seq:07d}"
        account_code = "6021" if period in ("2025-09", "2025-10") else "6022"
        account_name = "手续费及佣金收入" if account_code == "6021" else "财富管理代销收入"
        for line_no, dr_cr, code, name in [("001", "DR", "1122", "应收账款"), ("002", "CR", account_code, account_name)]:
            journal_rows.append({
                "journal_id": jid,
                "journal_line_id": f"{jid}-{line_no}",
                "period": period,
                "posting_date": _month_end_day(period),
                "source_system": "REVENUE_SUBLEDGER",
                "source_doc_id": subledger_id,
                "batch_id": f"WEALTH_{period.replace('-', '')}",
                "company_code": COMPANY_CODE,
                "branch_id": branch_id,
                "biz_line_id": "WEALTH",
                "account_code": code,
                "account_name": name,
                "dr_cr": dr_cr,
                "amount": _money(wealth_amount),
                "currency": "CNY",
                "description": "财富管理代销收入入账",
                "posting_status": "POSTED",
            })
        journal_seq += 1
        subledger_seq += 1

    pool_rows, rule_rows, driver_rows, allocation_rows = [], [], [], []
    cost_types = [
        ("IT_SYSTEM_COST", "IT系统成本", "TRADE_COUNT"),
        ("MARKET_DATA_COST", "行情资讯成本", "ACTIVE_CUSTOMER"),
        ("HQ_MANAGEMENT_COST", "总部管理成本", "HEADCOUNT"),
        ("RESEARCH_SUPPORT_COST", "研究支持成本", "REVENUE"),
        ("BRANCH_OPERATION_COST", "营业部运营成本", "AREA"),
    ]
    active_branch_ids = [b[0] for b in BRANCHES]
    pool_seq = 1
    for month_idx, period in enumerate(PERIODS):
        monthly_expense = expense_target * season[month_idx]
        weights = rng.dirichlet(np.ones(10))
        for j in range(10):
            ctype, cname, basis = cost_types[j % len(cost_types)]
            pool_id = f"POOL{pool_seq:05d}"
            rule_id = f"RULE_{period.replace('-', '')}_{j + 1:02d}_V2"
            amount = monthly_expense * weights[j]
            pool_rows.append({
                "pool_id": pool_id,
                "period": period,
                "cost_type": ctype,
                "cost_name": f"{cname}-{j // len(cost_types) + 1}",
                "amount": _money(amount),
                "source_account_code": "6602",
                "allocation_basis": basis,
                "owner_dept": "FINANCE_COE",
            })
            if period == "2025-07" and j == 0:
                old_rule_id = rule_id.replace("_V2", "_V1")
                rule_rows.append({"rule_id": old_rule_id, "rule_version": "V1", "period": period, "cost_type": ctype, "allocation_basis": basis, "target_dimension": "BRANCH", "effective_start": "2025-01-01", "effective_end": "2025-06-30", "is_active": False, "description": "旧版分摊规则，7月不应继续使用"})
            rule_rows.append({"rule_id": rule_id, "rule_version": "V2", "period": period, "cost_type": ctype, "allocation_basis": basis, "target_dimension": "BRANCH", "effective_start": "2025-07-01" if period >= "2025-07" else "2025-01-01", "effective_end": "2025-12-31", "is_active": True, "description": f"{cname}按{basis}分摊到营业部"})
            raw_driver = rng.uniform(30, 300, size=len(active_branch_ids))
            if ctype == "IT_SYSTEM_COST":
                raw_driver[1] *= 2.4
            if ctype == "HQ_MANAGEMENT_COST":
                raw_driver[[0, 1, 2]] *= 1.6
            used_rule_id = rule_id.replace("_V2", "_V1") if (period == "2025-07" and j == 0) else rule_id
            missing_branch = "B006" if (period == "2025-08" and j == 1) else None
            valid_indices = [i for i, b in enumerate(active_branch_ids) if b != missing_branch]
            denominator = raw_driver[valid_indices].sum()
            ratio_scale = 0.92 if (period == "2025-06" and j == 2) else 1.0
            for i, branch_id in enumerate(active_branch_ids):
                if branch_id == missing_branch:
                    continue
                weight = float(raw_driver[i] / denominator)
                driver_rows.append({
                    "driver_id": f"DRV{pool_seq:05d}_{branch_id}",
                    "period": period,
                    "rule_id": used_rule_id,
                    "target_id": branch_id,
                    "target_type": "BRANCH",
                    "driver_value": _money(raw_driver[i]),
                    "driver_weight": round(weight, 8),
                })
                allocation_rows.append({
                    "allocation_id": f"ALLOC{pool_seq:05d}_{branch_id}",
                    "period": period,
                    "pool_id": pool_id,
                    "rule_id": used_rule_id,
                    "target_id": branch_id,
                    "target_type": "BRANCH",
                    "allocated_amount": _money(amount * weight * ratio_scale),
                    "allocation_ratio": round(weight * ratio_scale, 8),
                    "posting_status": "POSTED",
                    "management_account_code": "6602",
                })
            interface_rows.append({
                "batch_id": f"ALLOC_{period.replace('-', '')}_{j + 1:02d}",
                "source_system": "ALLOCATION_ENGINE",
                "target_system": "MANAGEMENT_LEDGER",
                "period": period,
                "start_time": f"{period}-28 22:00:00",
                "end_time": f"{period}-28 22:05:00",
                "record_count": len(valid_indices),
                "total_amount": _money(amount * ratio_scale),
                "status": "WARNING" if ratio_scale < 1 or missing_branch else "SUCCESS",
                "error_message": "分摊比例不为100%或分摊因子缺失" if ratio_scale < 1 or missing_branch else "",
            })
            pool_seq += 1

    gl = pd.DataFrame(journal_rows)
    account_meta = pd.DataFrame(CHART_OF_ACCOUNTS)[["account_code", "normal_balance"]]
    gl_balance = (
        gl.groupby(["period", "company_code", "branch_id", "biz_line_id", "account_code", "dr_cr"], as_index=False)["amount"].sum()
        .pivot_table(index=["period", "company_code", "branch_id", "biz_line_id", "account_code"], columns="dr_cr", values="amount", fill_value=0)
        .reset_index()
        .rename(columns={"DR": "debit_amount", "CR": "credit_amount"})
    )
    if "debit_amount" not in gl_balance:
        gl_balance["debit_amount"] = 0.0
    if "credit_amount" not in gl_balance:
        gl_balance["credit_amount"] = 0.0
    gl_balance = gl_balance.merge(account_meta, on="account_code", how="left")
    gl_balance["opening_balance"] = 0.0
    gl_balance["ending_balance"] = np.where(
        gl_balance["normal_balance"].eq("DR"),
        gl_balance["debit_amount"] - gl_balance["credit_amount"],
        gl_balance["credit_amount"] - gl_balance["debit_amount"],
    )
    gl_balance_rows = gl_balance[["period", "company_code", "branch_id", "biz_line_id", "account_code", "opening_balance", "debit_amount", "credit_amount", "ending_balance"]].round(2).to_dict("records")

    root_cause_rows = [
        {"case_id": "RC001", "scenario": "COMMISSION_TO_GL", "exception_type": "UPSTREAM_SUBLEDGER_DIFF", "symptom": "交易流水佣金汇总大于收入子账", "root_cause": "营业部或接口批次未进入收入确认", "evidence_pattern": "commission_calc 有金额，revenue_subledger 无对应 recognition_batch_id", "recommended_action": "重跑收入确认批次并锁定批次幂等键"},
        {"case_id": "RC002", "scenario": "COMMISSION_TO_GL", "exception_type": "SUBLEDGER_GL_SHORT_POSTING", "symptom": "收入子账金额等于业务系统金额但总账少入账", "root_cause": "凭证生成失败或接口批次失败", "evidence_pattern": "subledger 有金额，gl_journal 对应 batch_id 少于子账", "recommended_action": "补生成凭证并核对接口日志失败原因"},
        {"case_id": "RC003", "scenario": "COMMISSION_TO_GL", "exception_type": "SUBLEDGER_GL_DUPLICATE_POSTING", "symptom": "总账金额高于收入子账", "root_cause": "重复推送凭证批次", "evidence_pattern": "gl_journal 同 batch_id 金额大于子账且存在重复描述", "recommended_action": "冲销重复凭证并增加批次幂等校验"},
        {"case_id": "RC004", "scenario": "COMMISSION_TO_GL", "exception_type": "ACCOUNT_MAPPING_ERROR", "symptom": "财富管理收入误入经纪佣金科目", "root_cause": "科目映射配置错误", "evidence_pattern": "biz_line_id=WEALTH 但 account_code=6021", "recommended_action": "修正映射到6022并重分类凭证"},
        {"case_id": "RC005", "scenario": "ALLOCATION", "exception_type": "ALLOCATION_NOT_FULLY_DISTRIBUTED", "symptom": "费用池分摊结果小于费用池金额", "root_cause": "分摊比例合计小于100%", "evidence_pattern": "allocation_ratio sum < 1", "recommended_action": "补足分摊因子后重跑分摊"},
        {"case_id": "RC006", "scenario": "ALLOCATION", "exception_type": "WRONG_RULE_VERSION", "symptom": "本月使用过期分摊规则", "root_cause": "规则版本切换失败", "evidence_pattern": "allocation_result.rule_id 指向 is_active=False", "recommended_action": "切换到V2规则并重算分摊结果"},
        {"case_id": "RC007", "scenario": "ALLOCATION", "exception_type": "MISSING_ALLOCATION_DRIVER", "symptom": "部分营业部缺少分摊因子", "root_cause": "交易笔数或客户数等驱动数据缺失", "evidence_pattern": "driver target 数小于活跃营业部数", "recommended_action": "补齐驱动数据并设置缺失值预警"},
    ]

    empty_exception_rows = []
    outputs = {
        "chart_of_accounts": account_rows,
        "branch_master": branch_rows,
        "biz_line_master": biz_rows,
        "customer_master": customer_rows,
        "trade_flow": trade_rows,
        "commission_calc": commission_rows,
        "revenue_subledger": subledger_rows,
        "gl_journal": journal_rows,
        "gl_balance": gl_balance_rows,
        "expense_pool": pool_rows,
        "allocation_rule": rule_rows,
        "allocation_driver": driver_rows,
        "allocation_result": allocation_rows,
        "interface_batch_log": interface_rows,
        "reconciliation_exception": empty_exception_rows,
        "root_cause_case": root_cause_rows,
    }
    counts = {}
    for table, rows in outputs.items():
        counts[table] = len(_write_csv(output_dir, table, rows))
    return counts


if __name__ == "__main__":
    for table, count in generate_synthetic_data().items():
        print(f"{table}: {count}")
