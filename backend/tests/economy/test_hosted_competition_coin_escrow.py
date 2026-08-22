from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.economy.hosted_competition_coin_escrow import HostedCompetitionCoinEscrowService
from app.models.hosted_competition import UserHostedCompetition
from app.models.user import User
from app.models.wallet import LedgerUnit


def _service():
    session = MagicMock()
    session.scalar.return_value = None
    session.add = MagicMock()
    session.flush = MagicMock()
    wallet = MagicMock()
    wallet.get_balance.return_value = Decimal("5000.0000")
    wallet.get_user_account.side_effect = lambda session, user, unit: SimpleNamespace(unit=unit, owner_user_id=user.id)
    wallet.ensure_platform_account.side_effect = lambda session, unit: SimpleNamespace(unit=unit, code="platform")
    wallet.append_transaction.return_value = [SimpleNamespace(transaction_id="tx-1")]
    return HostedCompetitionCoinEscrowService(session=session, wallet_service=wallet), wallet, session


def _competition() -> UserHostedCompetition:
    return UserHostedCompetition(
        id="competition-1",
        template_id="template-1",
        host_user_id="host-1",
        title="Coin Cup",
        slug="coin-cup",
        status="open",
        funding_mode="host_funded_gtex_coin_prize",
        entry_fee_fancoin=Decimal("0.0000"),
        reward_pool_fancoin=Decimal("0.0000"),
        reward_pool_coin=Decimal("0.0000"),
        host_funding_required_coin=Decimal("0.0000"),
        host_funding_escrowed_coin=Decimal("0.0000"),
        metadata_json={},
    )


def _user(user_id: str) -> User:
    return SimpleNamespace(id=user_id)


def test_host_funding_uses_gtex_coin_and_records_escrow() -> None:
    service, wallet, _ = _service()
    competition = _competition()
    host = _user("host-1")

    transaction_id = service.fund_from_host(
        competition=competition,
        host=host,
        gross_prize=Decimal("1000.0000"),
    )

    assert transaction_id == "tx-1"
    assert competition.reward_pool_coin == Decimal("1000.0000")
    assert competition.host_funding_required_coin == Decimal("1000.0000")
    assert competition.host_funding_escrowed_coin == Decimal("1000.0000")

    postings = wallet.append_transaction.call_args.kwargs["postings"]
    assert all(posting.account.unit is LedgerUnit.COIN for posting in postings)
    assert postings[0].amount == Decimal("-1000.0000")
    assert postings[1].amount == Decimal("1000.0000")


def test_coin_settlement_pays_winner_and_platform_from_coin_escrow() -> None:
    service, wallet, _ = _service()
    competition = _competition()
    competition.host_funding_required_coin = Decimal("1000.0000")
    competition.host_funding_escrowed_coin = Decimal("1000.0000")
    competition.reward_pool_coin = Decimal("1000.0000")
    wallet.get_balance.return_value = Decimal("1000.0000")
    winner = _user("winner-1")
    actor = _user("admin-1")

    transaction_id = service.settle(
        competition=competition,
        winner=winner,
        net_prize=Decimal("700.0000"),
        platform_fee=Decimal("300.0000"),
        actor=actor,
    )

    assert transaction_id == "tx-1"
    assert competition.host_funding_escrowed_coin == Decimal("0.0000")

    postings = wallet.append_transaction.call_args.kwargs["postings"]
    assert all(posting.account.unit is LedgerUnit.COIN for posting in postings)
    amounts = [posting.amount for posting in postings]
    assert Decimal("700.0000") in amounts
    assert Decimal("-700.0000") in amounts
    assert Decimal("300.0000") in amounts
    assert Decimal("-300.0000") in amounts
