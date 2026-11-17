from __future__ import annotations

from unittest.mock import MagicMock

from app.hosted_competition_engine.coin_aware_service import CoinAwareHostedCompetitionService


def test_competition_prize_has_no_platform_cut_without_a_fee_policy() -> None:
    service = CoinAwareHostedCompetitionService(session=MagicMock(), wallet_service=MagicMock())

    assert service._active_platform_fee_bps() == 0
