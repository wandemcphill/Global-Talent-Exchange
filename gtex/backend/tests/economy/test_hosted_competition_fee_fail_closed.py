from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.hosted_competition_engine.coin_aware_service import CoinAwareHostedCompetitionService
from app.hosted_competition_engine.service import HostedCompetitionError


def test_missing_competition_fee_policy_fails_closed() -> None:
    session = MagicMock()
    service = CoinAwareHostedCompetitionService(session=session, wallet_service=MagicMock())
    service_module = MagicMock()
    service_module.list_reward_rules.return_value = []
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            "app.hosted_competition_engine.coin_aware_service.AdminEngineService",
            lambda _session: service_module,
        )
        with pytest.raises(HostedCompetitionError, match="No active competition platform fee policy"):
            service._active_platform_fee_bps()
