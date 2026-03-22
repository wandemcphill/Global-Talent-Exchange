from __future__ import annotations

from app.common.enums.club_finance_account_type import ClubFinanceAccountType


def test_finance_service_tracks_opening_budget_and_cashflow(club_ops_services) -> None:
    finance = club_ops_services["finance"]

    overview = finance.get_finance_overview("club-finance")
    accounts = {account.account_type: account for account in overview.accounts}

    assert accounts[ClubFinanceAccountType.OPERATING_BALANCE].balance_minor == 1_500_000
    assert overview.budget.available_budget_minor == 1_500_000
    assert overview.cashflow.total_income_minor == 1_500_000


def test_finance_service_posts_auditable_dual_entries(club_ops_services) -> None:
    finance = club_ops_services["finance"]

    finance.get_finance_overview("club-audit")
    finance.record_competition_reward("club-audit", amount_minor=250_000, reference_id="competition-7")
    finance.record_academy_program_debit("club-audit", amount_minor=80_000, reference_id="academy-7")

    ledger = finance.get_ledger("club-audit").entries
    cashflow = finance.get_cashflow_summary("club-audit")
    account_balances = {
        account.account_type: account.balance_minor
        for account in finance.get_finance_overview("club-audit").accounts
    }

    assert len(ledger) == 5
    assert cashflow.total_income_minor == 1_750_000
    assert cashflow.total_expense_minor == 80_000
    assert cashflow.competition_income_minor == 250_000
    assert cashflow.academy_spend_minor == 80_000
    assert account_balances[ClubFinanceAccountType.OPERATING_BALANCE] == 1_670_000
    assert account_balances[ClubFinanceAccountType.COMPETITION_INCOME] == 250_000
    assert account_balances[ClubFinanceAccountType.ACADEMY_SPEND] == -80_000
