from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.hosted_competition_engine.coin_aware_service import CoinAwareHostedCompetitionService
from app.models.hosted_competition import HostedCompetitionFundingMode


def test_frozen_coin_prize_fee_does_not_follow_later_admin_change() -> None:
    session = MagicMock()
    service = CoinAwareHostedCompetitionService(session=session, wallet_service=MagicMock())
    competition = SimpleNamespace(
        funding_mode=HostedCompetitionFundingMode.HOST_FUNDED_GTEX_COIN_PRIZE,
        metadata_json={"platform_fee_bps": 3000},
    )

    service._active_platform_fee_bps = MagicMock(return_value=1000)

    assert service._frozen_platform_fee_bps(competition) == 3000


def test_frozen_fee_produces_seventy_percent_net_at_thirty_percent_policy() -> None:
    gross = Decimal("1000.0000")
    fee_bps = 3000
    fee = (gross * Decimal(fee_bps) / Decimal("10000")).quantize(Decimal("0.0001"))
    net = (gross - fee).quantize(Decimal("0.0001"))

    assert fee == Decimal("300.0000")
    assert net == Decimal("700.0000")
