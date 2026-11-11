from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.economy.competition_funding_policy import CompetitionFundingMode
from app.hosted_competition_engine.coin_aware_service import CoinAwareHostedCompetitionService
from app.hosted_competition_engine.service import HostedCompetitionError, HostedCompetitionService
from app.models.hosted_competition import HostedCompetitionFundingMode, HostedCompetitionStatus
from app.models.wallet import LedgerUnit


def test_coin_funding_mode_creates_host_funded_withdrawable_contract() -> None:
    session = MagicMock()
    session.scalar.return_value = None
    wallet = MagicMock()
    wallet.get_balance.return_value = Decimal("5000.0000")
    wallet.get_user_account.side_effect = lambda session, user, unit: SimpleNamespace(unit=unit, owner_user_id=user.id)
    wallet.ensure_platform_account.side_effect = lambda session, unit: SimpleNamespace(unit=unit, code="platform")
    wallet.append_transaction.return_value = [SimpleNamespace(transaction_id="fund-tx")]
    service = CoinAwareHostedCompetitionService(session=session, wallet_service=wallet)
    service.get_template_by_key = MagicMock(
        return_value=SimpleNamespace(id="template-1", is_user_hostable=True, participants=8)
    )
    service._metadata_with_join_rules = MagicMock(return_value={})
    service._create_entry_participant = MagicMock(
        return_value=SimpleNamespace(entry_fee_fancoin=Decimal("0.0000"), metadata_json={})
    )
    service._active_platform_fee_bps = MagicMock(return_value=3000)
    service._policy_provenance = MagicMock(return_value=("host-funded-test-policy", "test-v1"))
    host = SimpleNamespace(id="host-1")
    payload = SimpleNamespace(
        funding_mode="host_funded_gtex_coin_prize",
        template_key="user-hosted-cup-8",
        title="Coin Cup",
        description="",
        slug="coin-cup",
        visibility="public",
        starts_at=None,
        lock_at=None,
        max_participants=8,
        entry_fee_fancoin=Decimal("0.0000"),
        reward_pool_coin=Decimal("1000.0000"),
        metadata_json={},
        join_passcode=None,
    )

    competition, _, host_participation_created = service.create_competition(host=host, payload=payload)

    assert host_participation_created is True
    assert competition.funding_mode.value == "host_funded_gtex_coin_prize"
    assert competition.reward_pool_coin == Decimal("1000.0000")
    assert competition.platform_fee_amount == Decimal("300.0000")
    assert competition.host_funding_required_coin == Decimal("1000.0000")
    assert competition.host_funding_escrowed_coin == Decimal("1000.0000")
    assert competition.entry_fee_fancoin == Decimal("0.0000")
    assert competition.metadata_json["fee_policy_rule_key"] == "host-funded-test-policy"
    assert competition.metadata_json["fee_policy_version"] == "test-v1"
    postings = wallet.append_transaction.call_args.kwargs["postings"]
    assert all(posting.account.unit is LedgerUnit.COIN for posting in postings)
    assert competition.reward_pool_coin != Decimal("250.0000") * Decimal(payload.max_participants)


@pytest.mark.parametrize(
    "funding_mode",
    ["fancoin_entry_pool", "entry_funded", "participant_funded", "pool", "dynamic"],
)
def test_participant_funded_create_is_rejected(funding_mode: str) -> None:
    service = CoinAwareHostedCompetitionService(session=MagicMock(), wallet_service=MagicMock())
    payload = SimpleNamespace(funding_mode=funding_mode, template_key="user-hosted-cup-8", title="Cup")

    with pytest.raises(HostedCompetitionError, match="FanCoin entry-pool competitions are prohibited"):
        service.create_competition(host=SimpleNamespace(id="host-1"), payload=payload)

    service.wallet_service.append_transaction.assert_not_called()


def test_template_entry_fee_is_not_charged() -> None:
    session = MagicMock()
    session.scalar.return_value = None
    wallet = MagicMock()
    wallet.get_balance.return_value = Decimal("5000.0000")
    wallet.get_user_account.side_effect = lambda session, user, unit: SimpleNamespace(unit=unit, owner_user_id=user.id)
    wallet.ensure_platform_account.side_effect = lambda session, unit: SimpleNamespace(unit=unit, code="platform")
    wallet.append_transaction.return_value = [SimpleNamespace(transaction_id="fund-tx")]
    service = CoinAwareHostedCompetitionService(session=session, wallet_service=wallet)
    service.get_template_by_key = MagicMock(
        return_value=SimpleNamespace(
            id="template-1",
            is_user_hostable=True,
            participants=8,
            entry_fee_fancoin=Decimal("250.0000"),
        )
    )
    service._metadata_with_join_rules = MagicMock(return_value={})
    service._create_entry_participant = MagicMock(
        return_value=SimpleNamespace(entry_fee_fancoin=Decimal("250.0000"), metadata_json={})
    )
    service._active_platform_fee_bps = MagicMock(return_value=1000)
    service._policy_provenance = MagicMock(return_value=("policy", "v1"))
    payload = SimpleNamespace(
        funding_mode=None,
        template_key="user-hosted-cup-8",
        title="Free Cup",
        description="",
        slug="free-cup",
        visibility="public",
        starts_at=None,
        lock_at=None,
        max_participants=8,
        entry_fee_fancoin=None,
        reward_pool_coin=Decimal("1000.0000"),
        metadata_json={},
        join_passcode=None,
    )

    competition, _, _ = service.create_competition(host=SimpleNamespace(id="host-1"), payload=payload)

    assert competition.funding_mode is CompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE
    assert competition.entry_fee_fancoin == Decimal("0.0000")
    assert competition.reward_pool_fancoin == Decimal("0.0000")
    assert competition.reward_pool_coin == Decimal("1000.0000")
    debited_units = [posting.account.unit for posting in wallet.append_transaction.call_args.kwargs["postings"]]
    assert LedgerUnit.CREDIT not in debited_units


def test_collect_entry_fee_never_debits_entrant() -> None:
    wallet = MagicMock()
    service = HostedCompetitionService(session=MagicMock(), wallet_service=wallet)
    participant = SimpleNamespace(entry_fee_fancoin=Decimal("100.0000"), metadata_json={})

    service._collect_entry_fee(
        competition=SimpleNamespace(id="c1", title="Cup", entry_fee_fancoin=Decimal("100.0000")),
        participant=participant,
        user=SimpleNamespace(id="entrant"),
    )

    wallet.append_transaction.assert_not_called()
    wallet.get_user_account.assert_not_called()
    assert participant.entry_fee_fancoin == Decimal("0.0000")
    assert participant.metadata_json["payment_status"] == "free"


def test_join_rejects_fancoin_entry_pool_without_debit() -> None:
    wallet = MagicMock()
    session = MagicMock()
    session.scalar.return_value = SimpleNamespace(
        id="c1",
        status=HostedCompetitionStatus.OPEN,
        funding_mode=HostedCompetitionFundingMode.FANCOIN_ENTRY_POOL,
        entry_fee_fancoin=Decimal("100.0000"),
    )
    service = HostedCompetitionService(session=session, wallet_service=wallet)

    with pytest.raises(HostedCompetitionError, match="FanCoin entry-pool competitions are prohibited"):
        service.join_competition(user=SimpleNamespace(id="entrant"), competition_id="c1")

    wallet.append_transaction.assert_not_called()
