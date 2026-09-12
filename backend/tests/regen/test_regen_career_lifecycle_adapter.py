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
    from app.models.base import Base
    from app.models.regen import RegenProfile
    from app.services.player_lifecycle_service import PlayerLifecycleService
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
            metadata_json={
                "career_state": {
                    "virtual_age_months": 144,
                    "lifecycle_age_months": 144,
                    "career_stage": "late_career",
                    "retirement_pressure": True,
                    "retirement_pressure_band": "high",
                    "expected_longevity_months": 12,
                    "retirement_watch": True,
                    "retirement_decision_eligible": True,
                    "eligible_for_retirement_decision": True,
                    "policy_drivers": ["stale-driver"],
                    "retirement_drivers": ["stale-driver"],
                    "retirement_policy_status": "assessed",
                    "retirement_policy": "phase6_dynamic",
                    "lifecycle_phase": "retirement_watch",
                    "retired": False,
                }
            },
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
        assert "lifecycle_age_months" not in career_state
        assert career_state.get("career_stage") == "age_unknown"
        assert career_state.get("retirement_pressure") is False
        assert career_state.get("retirement_pressure_band") == "unknown"
        assert career_state.get("expected_longevity_months") is None
        assert career_state.get("retirement_watch") is False
        assert career_state.get("retirement_decision_eligible") is False
        assert career_state.get("eligible_for_retirement_decision") is False
        assert career_state.get("policy_drivers") == []
        assert career_state.get("retirement_drivers") == []
        assert career_state.get("retirement_policy_status") == "age_unknown"
        assert career_state.get("retirement_policy") == "phase6_dynamic"
        assert career_state.get("retired") is False

        # Also test already-retired regen with unknown age.
        regen.metadata_json["career_state"]["retired"] = True
        regen.metadata_json["career_state"]["retired_on"] = "2025-01-01"
        session.flush()

        summary_retired = service.get_regen_summary(player.id, on_date=date(2025, 6, 1))
        assert summary_retired is not None
        assert summary_retired.retired is True
        assert summary_retired.lifecycle_phase == "retired"
        assert regen.metadata_json["career_state"].get("retirement_decision_eligible") is False
    finally:
        session.close()


def test_already_retired_player_preserves_retired_state_and_legacy_plan_on_resync() -> None:
    from datetime import datetime, timezone

    from app.ingestion.models import Player
    from app.models.base import Base
    from app.models.regen import RegenProfile
    from app.services.player_lifecycle_service import PlayerLifecycleService
    from tests.regen_universe_support import build_regen_universe_session

    session = build_regen_universe_session()
    Base.metadata.create_all(session.get_bind())
    try:
        player = Player(
            id="test-retired-player",
            source_provider="manual",
            provider_external_id="ext-retired-player",
            first_name="Retired",
            last_name="Legend",
            full_name="Retired Legend Player",
            position="CB",
            date_of_birth=date(1990, 1, 1),
            is_tradable=False,
        )
        regen = RegenProfile(
            id="regen-retired-legend",
            regen_id="RGN-RETIRED-LEGEND",
            player_id=player.id,
            linked_unique_card_id="card-retired-legend",
            generated_for_club_id="club-1",
            birth_country_code="NG",
            primary_position="CB",
            secondary_positions_json=[],
            generated_at=datetime(2020, 1, 1, 12, 0, tzinfo=timezone.utc),
            current_gsi=88,
            scout_confidence="high",
            generation_source="academy",
            status="retired",
            metadata_json={
                "career_state": {
                    "virtual_age_months": 420,
                    "lifecycle_age_months": 420,
                    "career_stage": "late_career",
                    "retirement_pressure": False,
                    "retirement_pressure_band": "decision",
                    "expected_longevity_months": 0,
                    "retirement_watch": True,
                    "retirement_decision_eligible": True,
                    "eligible_for_retirement_decision": True,
                    "policy_drivers": ["virtual_age"],
                    "retirement_drivers": ["virtual_age"],
                    "retirement_policy_status": "assessed",
                    "retirement_policy": "phase6_dynamic",
                    "lifecycle_phase": "retired",
                    "retired": True,
                    "retired_on": "2025-01-01",
                    "previous_club_id": "club-1",
                }
            },
        )
        session.add_all([player, regen])
        session.flush()

        service = PlayerLifecycleService(session)
        summary = service.get_regen_summary(player.id, on_date=date(2025, 6, 1))

        assert summary is not None
        assert summary.retired is True
        assert summary.lifecycle_phase == "retired"

        career_state = regen.metadata_json.get("career_state", {})
        assert career_state.get("retired") is True
        assert career_state.get("lifecycle_phase") == "retired"
        assert career_state.get("retired_on") == "2025-01-01"
    finally:
        session.close()
