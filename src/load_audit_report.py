from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

from .config import AUDIT_REPORT_PATH, RAW_DIR


DEFAULT_AUDIT_METRICS: dict[str, Any] = {
    "company": "长江证券股份有限公司",
    "report_year": 2025,
    "currency": "CNY",
    "unit": "yuan",
    "source_note": "公开披露审计报告汇总口径；明细数据为合成数据。",
    "balance_sheet": {
        "货币资金": 64057872717.75,
        "结算备付金": 9385225435.88,
        "融出资金": 46040912990.02,
        "交易性金融资产": 28914935215.43,
        "买入返售金融资产": 3422849566.32,
        "应收款项": 1896644148.54,
        "其他资产": 240246258.99,
        "短期借款": 19803661.66,
        "卖出回购金融资产款": 33832166929.82,
        "代理买卖证券款": 69211469584.41,
        "应付款项": 1853737573.02,
        "应付职工薪酬": 3962780558.18,
        "应交税费": 459971261.08,
        "实收资本或股本": 5530072948.00,
        "资本公积": 11288357670.64,
        "盈余公积": 2860312606.69,
        "未分配利润": 8663899733.85,
    },
    "income_statement": {
        "营业总收入": 10547734279.96,
        "手续费及佣金净收入": 4781644467.38,
        "利息净收入": 2375082213.13,
        "投资收益": 2914359066.24,
        "公允价值变动收益": 373532245.10,
        "其他业务收入": 103116288.11,
        "营业总支出": 5781958875.06,
        "业务及管理费": 5675720868.42,
        "信用减值损失": 8211420.13,
        "所得税费用": 911901865.48,
        "净利润": 3700780682.54,
    },
    "business_structure": {
        "证券经纪业务净收入": 3627526411.74,
        "证券经纪业务收入": 4408236704.92,
        "代理买卖证券业务收入": 3400948125.37,
        "代销金融产品业务收入": 228445201.46,
        "投资银行业务净收入": 398556443.91,
        "投资银行业务收入": 409750331.67,
        "资产管理业务净收入": 113542333.53,
        "基金管理业务净收入": 180235592.45,
        "经纪及证券金融分部收入": 6418878352.60,
        "证券自营业务分部收入": 2177175949.42,
        "资产管理业务分部收入": 440873250.93,
        "融资融券业务利息收入": 2034295400.84,
    },
}


METRIC_PATTERNS = {
    "货币资金": r"货币资金合计\s+([0-9,]+\.\d{2})",
    "结算备付金": r"结算备付金\s+([0-9,]+\.\d{2})",
    "融出资金": r"融出资金\s+([0-9,]+\.\d{2})",
    "交易性金融资产": r"交易性金融资产\s+([0-9,]+\.\d{2})",
    "手续费及佣金净收入": r"手续费及佣金净收入.*?([0-9,]+\.\d{2})",
    "业务及管理费": r"业务及管理费.*?合计\s+([0-9,]+\.\d{2})",
}


def _number(value: str) -> float:
    return float(value.replace(",", ""))


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    path = Path(pdf_path)
    if not path.exists():
        return ""
    if PdfReader is not None:
        try:
            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            pass
    try:
        completed = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode == 0:
            return completed.stdout
    except Exception:
        return ""
    return ""


def parse_public_metrics(text: str) -> dict[str, Any]:
    metrics = DEFAULT_AUDIT_METRICS.copy()
    metrics["parse_status"] = "fallback_defaults"
    if not text:
        return metrics
    parsed = {}
    for key, pattern in METRIC_PATTERNS.items():
        match = re.search(pattern, text, flags=re.S)
        if match:
            parsed[key] = _number(match.group(1))
    if parsed:
        metrics = yaml.safe_load(yaml.safe_dump(DEFAULT_AUDIT_METRICS, allow_unicode=True))
        metrics["parse_status"] = "partial_pdf_parse"
        for key, value in parsed.items():
            if key in metrics["balance_sheet"]:
                metrics["balance_sheet"][key] = value
            elif key in metrics["income_statement"]:
                metrics["income_statement"][key] = value
    return metrics


def load_audit_metrics(pdf_path: str | Path | None = None) -> dict[str, Any]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manual_path = RAW_DIR / "audit_report_metrics.yaml"
    if manual_path.exists():
        with manual_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if data:
            data.setdefault("parse_status", "manual_yaml")
            return data
    path = pdf_path or os.getenv("AUDIT_REPORT_PATH") or AUDIT_REPORT_PATH
    metrics = parse_public_metrics(extract_text_from_pdf(path))
    output_path = RAW_DIR / "audit_report_metrics_extracted.yaml"
    with output_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(metrics, f, allow_unicode=True, sort_keys=False)
    return metrics


if __name__ == "__main__":
    loaded = load_audit_metrics()
    print(yaml.safe_dump(loaded, allow_unicode=True, sort_keys=False))
