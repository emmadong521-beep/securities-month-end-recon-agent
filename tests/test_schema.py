from src.schema import CHART_OF_ACCOUNTS, TABLE_COLUMNS


def test_chart_of_accounts_has_required_fields():
    required = {"account_code", "account_name", "account_class", "normal_balance", "statement_type", "parent_account_code", "is_leaf", "description"}
    assert required.issubset(CHART_OF_ACCOUNTS[0])
    assert any(a["account_code"] == "6021" for a in CHART_OF_ACCOUNTS)


def test_required_tables_registered():
    for table in ["trade_flow", "commission_calc", "revenue_subledger", "gl_journal", "gl_balance", "allocation_result"]:
        assert table in TABLE_COLUMNS
