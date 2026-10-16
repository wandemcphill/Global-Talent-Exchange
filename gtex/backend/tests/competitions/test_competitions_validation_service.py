from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.competition import Competition
from app.schemas.competition_core import CompetitionCreateRequest, CompetitionUpdateRequest
from app.services.competition_validation_service import (
    CompetitionValidationError,
    CompetitionValidationService,
)


def _league_request(
    *,
    entry_fee_minor: int = 1000,
    platform_fee_bps: int = 1000,
    host_creation_fee_minor: int = 500,
    min_participants: int = 4,
    max_participants: int = 8,
    payout_mode: str = "winner_take_all",
    top_n: int | None = None,
    payout_percentages: list[int] | None = None,
) -> CompetitionCreateRequest:
    payload: dict[str, object] = {
        "core": {
            "host_user_id": "host-1",
            "name": "Verified Skill League",
            "description": "Transparent player-vs-player contest.",
            "format": "league",
            "visibility": "public",
            "start_mode": "scheduled",
            "scheduled_start_at": datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
            "status": "draft",
        },
        "rules": {
            "format": "league",
            "league_rules": {
                "win_points": 3,
                "draw_points": 1,
                "loss_points": 0,
                "tie_break_order": ["points", "goal_diff", "goals_for"],
                "home_away": True,
                "min_participants": min_participants,
                "max_participants": max_participants,
            },
        },
        "financials": {
            "entry_fee_minor": entry_fee_minor,
            "currency": "USD",
            "platform_fee_bps": platform_fee_bps,
            "host_creation_fee_minor": host_creation_fee_minor,
            "payout_mode": payout_mode,
        },
    }
    if top_n is not None:
        payload["financials"]["top_n"] = top_n
    if payout_percentages is not None:
        payload["financials"]["payout_percentages"] = payout_percentages
    return CompetitionCreateRequest.model_validate(payload)


def _competition(status: str = "draft") -> Competition:
    return Competition(
        host_user_id="host-1",
        name="Editable Contest",
        description="Skill contest.",
        format="league",
        visibility="public",
        status=status,
        start_mode="scheduled",
        scheduled_start_at=datetime(2026, 5, 1, 12, 0, tzinfo=timezone.utc),
        currency="USD",
        entry_fee_minor=1000,
        platform_fee_bps=500,
        host_creation_fee_minor=100,
        gross_pool_minor=8000,
        net_prize_pool_minor=7500,
    )


def test_validate_creation_returns_auditable_fee_summary() -> None:
    service = CompetitionValidationService()

    result = service.validate_creation(_league_request())

    assert result.payout_percentages == [100]
    assert result.min_participants == 4
    assert result.max_participants == 8
    assert result.fee_summary.gross_pool_minor == 8_000
    assert result.fee_summary.platform_fee_minor == 800
    assert result.fee_summary.net_prize_pool_minor == 6_700


def test_validate_creation_rejects_payout_config_above_capacity() -> None:
    service = CompetitionValidationService()

    with pytest.raises(CompetitionValidationError, match="cannot exceed the competition capacity"):
        service.validate_creation(_league_request(max_participants=8, payout_mode="top_n", top_n=9))


def test_validate_creation_rejects_fee_stacks_without_a_prize_pool() -> None:
    service = CompetitionValidationService()

    with pytest.raises(CompetitionValidationError, match="positive net prize pool"):
        service.validate_creation(
            _league_request(
                entry_fee_minor=1000,
                platform_fee_bps=1500,
                host_creation_fee_minor=1700,
                min_participants=2,
                max_participants=2,
            )
        )


def test_validate_update_rejects_critical_changes_after_first_paid_join() -> None:
    service = CompetitionValidationService()
    competition = _competition()
    update = CompetitionUpdateRequest.model_validate(
        {
            "financials": {
                "entry_fee_minor": 2000,
                "currency": "USD",
                "platform_fee_bps": 500,
                "host_creation_fee_minor": 100,
                "payout_mode": "winner_take_all",
            }
        }
    )

    with pytest.raises(CompetitionValidationError, match="first paid join"):
        service.validate_update(competition=competition, update=update, has_paid_participants=True)


def test_validate_update_rejects_critical_changes_after_lock() -> None:
    service = CompetitionValidationService()
    competition = _competition(status="locked")
    update = CompetitionUpdateRequest.model_validate(
        {
            "rules": {
                "format": "league",
                "league_rules": {
                    "win_points": 3,
                    "draw_points": 1,
                    "loss_points": 0,
                    "tie_break_order": ["points", "goal_diff", "goals_for"],
                    "home_away": False,
                    "min_participants": 4,
                    "max_participants": 8,
                },
            }
        }
    )

    with pytest.raises(CompetitionValidationError, match="locked competitions"):
        service.validate_update(competition=competition, update=update, has_paid_participants=False)


def test_validate_update_allows_non_critical_changes_after_paid_join() -> None:
    service = CompetitionValidationService()
    competition = _competition()
    update = CompetitionUpdateRequest.model_validate({"name": "Renamed Contest"})

    service.validate_update(competition=competition, update=update, has_paid_participants=True)
