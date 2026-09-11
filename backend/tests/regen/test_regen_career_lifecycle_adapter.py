from __future__ import annotations

from datetime import date

from app.services.regen_career_lifecycle_adapter import _subtract_months


def test_subtract_months_preserves_calendar_boundaries() -> None:
    assert _subtract_months(date(2027, 3, 31), 1) == date(2027, 2, 28)
    assert _subtract_months(date(2028, 3, 31), 1) == date(2028, 2, 29)
    assert _subtract_months(date(2027, 1, 31), 12) == date(2026, 1, 31)


def test_service_package_installs_phase6_adapter() -> None:
    from app.services.player_lifecycle_service import PlayerLifecycleService

    assert getattr(PlayerLifecycleService._sync_regen_state, "__name__", "") == "_policy_sync"
