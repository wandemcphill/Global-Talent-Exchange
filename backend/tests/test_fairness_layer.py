from __future__ import annotations

from datetime import date

import pytest

from app.common.enums.competition_type import CompetitionType
from app.common.enums.fixture_window import FixtureWindow
from app.competition_engine.queue_contracts import MatchSimulationJob
from app.fairness.fairness_guard import FairnessGuard, FairnessViolation
from app.fairness.match_integrity_service import MatchIntegrityService, MatchIntegrityViolation
from app.fairness.spend_balance_controller import SpendBalanceController
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.services.match_timeline_service import MatchTimelineService
from backend.tests.match_engine.helpers import build_request


def _build_job() -> MatchSimulationJob:
    return MatchSimulationJob(
        fixture_id="fairness-match",
        competition_id="competition-1",
        competition_type=CompetitionType.LEAGUE,
        match_date=date(2026, 3, 24),
        window=FixtureWindow.SENIOR_1,
        home_club_id="club-home",
        away_club_id="club-away",
        home_club_name="Home Club",
        away_club_name="Away Club",
    )


def test_fairness_guard_rejects_monetization_injection() -> None:
    request = build_request(seed=12)
    home_team = request.home_team.model_copy(
        update={
            "tactics": request.home_team.tactics.model_copy(
                update={"player_instructions": {"premium_camera_boost": True}}
            )
        }
    )
    injected_request = request.model_copy(update={"home_team": home_team})

    with pytest.raises(FairnessViolation, match="Monetization cannot affect match logic"):
        FairnessGuard().validate_public_request(injected_request)


def test_locked_inputs_ignore_client_seed_and_produce_identical_results() -> None:
    base_request = build_request(seed=12)
    alternate_seed_request = build_request(seed=99)

    locked_a = FairnessGuard().lock_official_request(base_request)
    locked_b = FairnessGuard().lock_official_request(alternate_seed_request)

    assert locked_a.match_hash == locked_b.match_hash
    assert locked_a.match_seed == locked_b.match_seed

    service = MatchSimulationService()
    replay_a = service.build_replay_payload(locked_a.request)
    replay_b = service.build_replay_payload(locked_b.request)

    assert replay_a.seed == replay_b.seed
    assert replay_a.summary.home_score == replay_b.summary.home_score
    assert replay_a.summary.away_score == replay_b.summary.away_score
    assert [event.event_type for event in replay_a.timeline.events] == [
        event.event_type for event in replay_b.timeline.events
    ]


def test_spend_balance_controller_blocks_squads_over_the_s_plus_cap() -> None:
    request = build_request(seed=13)
    boosted_starters = [
        player.model_copy(update={"overall": 92}) if index < 6 else player
        for index, player in enumerate(request.home_team.starters)
    ]
    boosted_home = request.home_team.model_copy(update={"starters": boosted_starters})
    boosted_request = request.model_copy(update={"home_team": boosted_home})

    with pytest.raises(FairnessViolation, match="S\\+ player cap"):
        SpendBalanceController().apply_balance_controls(
            request=boosted_request,
            job=_build_job(),
            match_seed=101,
            competition_metadata_json={},
        )


def test_match_integrity_service_rejects_tampered_timeline_payloads() -> None:
    request = build_request(seed=14)
    locked = FairnessGuard().lock_official_request(request)
    replay_payload = MatchSimulationService().build_replay_payload(locked.request)
    view_state = MatchTimelineService().build_from_replay_payload(replay_payload)
    integrity = MatchIntegrityService()
    fairness = integrity.build_fairness_envelope(
        locked_context=locked,
        view_state=view_state,
        balance_metadata={},
        competition_metadata_json={},
    )
    tampered_view = view_state.model_copy(update={"events": view_state.events[:-1]})

    with pytest.raises(MatchIntegrityViolation, match="timeline proof"):
        integrity.validate_view_state(view_state=tampered_view, fairness_metadata=fairness)


def test_match_integrity_service_builds_32_bit_visible_hashes() -> None:
    request = build_request(seed=15)
    locked = FairnessGuard().lock_official_request(request)
    replay_payload = MatchSimulationService().build_replay_payload(locked.request)
    view_state = MatchTimelineService().build_from_replay_payload(replay_payload)
    integrity = MatchIntegrityService()

    fairness = integrity.build_fairness_envelope(
        locked_context=locked,
        view_state=view_state,
        balance_metadata={},
        competition_metadata_json={},
    )

    visible_hash = fairness["visible_timeline_hash"]
    assert visible_hash == integrity._visible_hash_view_state(view_state)
    assert len(visible_hash) == 8
    assert all(char in "0123456789abcdef" for char in visible_hash)
