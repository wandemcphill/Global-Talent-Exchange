from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.hosted_competition_engine.coin_aware_service import CoinAwareHostedCompetitionService
from app.models.wallet import LedgerUnit


def test_coin_funding_mode_creates_host_funded_withdrawable_contract() -> None:
    session = MagicMock()
    wallet = MagicMock()
    wallet.get_balance.return_value = Decimal("5000.0000")
    wallet.get_user_account.side_effect = lambda session, user, unit: SimpleNamespace(unit=unit, owner_user_id=user.id)
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
    postings = wallet.append_transaction.call_args.kwargs["postings"]
    assert all(posting.account.unit is LedgerUnit.COIN for posting in postings)
