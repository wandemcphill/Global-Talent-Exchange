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


def test_virtual_age_unavailable_prevents_retirement() -> None:
    from datetime import datetime, timezone
    from app.ingestion.models import Player
    from app.models.regen import RegenProfile
    from app.services.player_lifecycle_service import PlayerLifecycleService
    from app.models.base import Base
    from tests.regen_universe_support import build_regen_universe_session

    session = build_regen_universe_session()
    Base.metadata.create_all(session.get_bind())
    try:
        player = Player(
            id="test-player-unknown-age",
            source_provider="manual",
            provider_external_id="ext-unknown-age",
            first_name="Unknown",
            last_name="Age",
            full_name="Unknown Age Player",
            position="ST",
            date_of_birth=date(2005, 1, 1),
            is_tradable=True,
        )
        regen = RegenProfile(
            id="regen-profile-unknown-age",
            regen_id="RGN-UNKNOWN-AGE",
            player_id=player.id,
            linked_unique_card_id="card-unknown-age",
            generated_for_club_id="club-1",
            birth_country_code="NG",
            primary_position="ST",
            secondary_positions_json=[],
            generated_at=datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc),
            current_gsi=70,
            scout_confidence="high",
            generation_source="academy",
            status="active",
            metadata_json={},
        )
        session.add_all([player, regen])
        session.flush()

        service = PlayerLifecycleService(session)
        summary = service.get_regen_summary(player.id, on_date=date(2025, 6, 1))

        assert summary is not None
        assert summary.lifecycle_age_months is None
        assert summary.lifecycle_phase == "age_unknown"

        career_state = regen.metadata_json.get("career_state", {})
        assert career_state.get("virtual_age_months") is None
        assert career_state.get("career_stage") == "age_unknown"
        assert career_state.get("retirement_pressure") is False
        assert career_state.get("retirement_pressure_band") == "unknown"
        assert career_state.get("expected_longevity_months") is None
        assert career_state.get("retirement_watch") is False
        assert career_state.get("eligible_for_retirement_decision") is False
        assert career_state.get("policy_drivers") == []

        # Also test already-retired regen with unknown age
        regen.metadata_json["career_state"]["retired"] = True
        regen.metadata_json["career_state"]["retired_on"] = "2025-01-01"
        session.flush()

        summary_retired = service.get_regen_summary(player.id, on_date=date(2025, 6, 1))
        assert summary_retired is not None
        assert summary_retired.retired is True
        assert summary_retired.lifecycle_phase == "retired"
    finally:
        session.close()
