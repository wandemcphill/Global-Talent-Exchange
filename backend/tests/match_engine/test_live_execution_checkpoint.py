from __future__ import annotations

from app.match_engine.schemas import (
    MatchCompetitionContextInput,
    MatchSimulationRequest,
    MatchSubstitutionRequestInput,
    MatchTacticalAdjustmentInput,
)
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.match_engine.simulation.event_generator import MatchEventGenerator
from app.match_engine.simulation.live_execution import (
    MatchExecutionCheckpoint,
    advance_checkpoint,
    apply_live_tactical_revision,
    finalize_checkpoint,
    initialize_execution,
    resume_from_halftime,
)
from app.match_engine.simulation.models import MatchCompetitionType, TacticalStyle


def _build_request(
    *,
    match_id: str = "checkpoint-match-1",
    seed: int = 4242,
    extra_time: bool = False,
    requires_winner: bool = False,
    is_final: bool = False,
):
    factory = SyntheticSquadFactory()
    home = factory.build_team(
        team_id="club-home",
        team_name="Home FC",
        base_overall=79,
    )
    away = factory.build_team(
        team_id="club-away",
        team_name="Away FC",
        base_overall=78,
    )
    competition = MatchCompetitionContextInput(
        competition_type=MatchCompetitionType.CUP if is_final or requires_winner else MatchCompetitionType.LEAGUE,
        stage="final" if is_final else "league",
        is_final=is_final,
        requires_winner=requires_winner,
        extra_time=extra_time,
    )
    return MatchSimulationRequest(
        match_id=match_id,
        seed=seed,
        home_team=home,
        away_team=away,
        competition=competition,
    )


def test_progressive_checkpoint_roundtrip_matches_full_simulation_exactly() -> None:
    generator = MatchEventGenerator()
    request = _build_request(match_id="parity-league", seed=90125)
    baseline = generator.simulate(request)

    checkpoint = initialize_execution(generator, request, revision=1)
    assert checkpoint.current_minute == 0
    assert checkpoint.committed_events[0].event_type.value == "kickoff"

    for step_target in (15, 30, 45):
        payload = checkpoint.to_dict()
        checkpoint = MatchExecutionCheckpoint.from_dict(payload, generator=generator, request=request)
        checkpoint, _ = advance_checkpoint(
            generator,
            request,
            checkpoint,
            until_minute=step_target,
            stop_at_halftime=True,
        )

    assert checkpoint.current_minute == 45
    assert checkpoint.clock_phase == "halftime"
    assert checkpoint.halftime_processed is True

    checkpoint = resume_from_halftime(
        MatchExecutionCheckpoint.from_dict(checkpoint.to_dict(), generator=generator, request=request)
    )
    for step_target in (60, 75, 90):
        payload = checkpoint.to_dict()
        checkpoint = MatchExecutionCheckpoint.from_dict(payload, generator=generator, request=request)
        checkpoint, _ = advance_checkpoint(
            generator,
            request,
            checkpoint,
            until_minute=step_target,
            stop_at_halftime=True,
        )

    stepped_result = finalize_checkpoint(generator, request, checkpoint)
    assert stepped_result.home_score == baseline.home_score
    assert stepped_result.away_score == baseline.away_score
    assert stepped_result.winner_team_id == baseline.winner_team_id
    assert [(e.sequence, e.event_type, e.minute) for e in stepped_result.events] == [
        (e.sequence, e.event_type, e.minute) for e in baseline.events
    ]
    assert [
        (p.player_id, p.minutes_played, p.goals, p.assists, p.yellow_cards)
        for p in stepped_result.player_stats
    ] == [
        (p.player_id, p.minutes_played, p.goals, p.assists, p.yellow_cards)
        for p in baseline.player_stats
    ]


def test_progressive_knockout_extra_time_and_penalties_match_full_simulation() -> None:
    generator = MatchEventGenerator()
    # Find a seed that reaches extra time (drawn at 90) so ET + penalty stepping is exercised too.
    request = None
    baseline = None
    for candidate_seed in range(100, 140):
        candidate = _build_request(
            match_id=f"ko-{candidate_seed}",
            seed=candidate_seed,
            extra_time=True,
            requires_winner=True,
            is_final=True,
        )
        res = generator.simulate(candidate)
        if any((e.metadata or {}).get("match_phase") == "extra_time" for e in res.events):
            request = candidate
            baseline = res
            break
    assert request is not None and baseline is not None

    checkpoint = initialize_execution(generator, request, revision=1)
    for target in (25, 45):
        checkpoint = MatchExecutionCheckpoint.from_dict(checkpoint.to_dict(), generator=generator, request=request)
        checkpoint, _ = advance_checkpoint(generator, request, checkpoint, until_minute=target, stop_at_halftime=True)
    checkpoint = resume_from_halftime(checkpoint)
    for target in (70, 90):
        checkpoint = MatchExecutionCheckpoint.from_dict(checkpoint.to_dict(), generator=generator, request=request)
        checkpoint, _ = advance_checkpoint(generator, request, checkpoint, until_minute=target, stop_at_halftime=True)

    assert checkpoint.extra_time_active is True
    assert checkpoint.target_end_minute == 120
    assert checkpoint.clock_phase == "extra_time"

    for target in (105, 120):
        checkpoint = MatchExecutionCheckpoint.from_dict(checkpoint.to_dict(), generator=generator, request=request)
        checkpoint, _ = advance_checkpoint(generator, request, checkpoint, until_minute=target, stop_at_halftime=False)

    stepped_result = finalize_checkpoint(generator, request, checkpoint)
    assert stepped_result.home_score == baseline.home_score
    assert stepped_result.away_score == baseline.away_score
    assert stepped_result.decided_by_penalties == baseline.decided_by_penalties
    assert stepped_result.home_penalty_score == baseline.home_penalty_score
    assert stepped_result.away_penalty_score == baseline.away_penalty_score
    assert stepped_result.winner_team_id == baseline.winner_team_id
    assert [(e.sequence, e.event_type, e.minute) for e in stepped_result.events] == [
        (e.sequence, e.event_type, e.minute) for e in baseline.events
    ]


def test_live_tactical_revision_preserves_prefix_and_changes_future_execution() -> None:
    generator = MatchEventGenerator()
    request = _build_request(match_id="resim-live-1", seed=7771)

    baseline_cp = initialize_execution(generator, request, revision=1)
    baseline_cp, _ = advance_checkpoint(generator, request, baseline_cp, until_minute=45, stop_at_halftime=True)
    baseline_cp = resume_from_halftime(baseline_cp)
    baseline_cp, _ = advance_checkpoint(generator, request, baseline_cp, until_minute=90, stop_at_halftime=True)
    baseline_result = finalize_checkpoint(generator, request, baseline_cp)

    live_cp = initialize_execution(generator, request, revision=1)
    live_cp, _ = advance_checkpoint(generator, request, live_cp, until_minute=45, stop_at_halftime=True)
    prefix_snapshot = [
        (e.sequence, e.event_type.value, e.minute, e.home_score, e.away_score, e.primary_player_id)
        for e in live_cp.committed_events
    ]

    outgoing_id = live_cp.home_state.active_player_ids[-1]
    incoming_id = live_cp.home_state.bench_player_ids[0]
    live_cp, emitted = apply_live_tactical_revision(
        generator,
        request,
        live_cp,
        side="home",
        command_id="cmd-ht-1",
        effective_minute=45,
        new_revision=2,
        adjustment=MatchTacticalAdjustmentInput(
            formation="3-4-3",
            mentality=TacticalStyle.ATTACKING,
            pressing=88,
            tempo=86,
            defensive_line=72,
        ),
        substitutions=[
            MatchSubstitutionRequestInput(
                outgoing_player_id=outgoing_id,
                incoming_player_id=incoming_id,
                urgency="urgent",
                reason="tactical_push",
            )
        ],
    )
    assert len(emitted) >= 2
    assert live_cp.execution_revision == 2
    # Committed prefix up through sequence len(prefix_snapshot) must remain immutable!
    assert [
        (e.sequence, e.event_type.value, e.minute, e.home_score, e.away_score, e.primary_player_id)
        for e in live_cp.committed_events[: len(prefix_snapshot)]
    ] == prefix_snapshot

    live_cp = resume_from_halftime(live_cp)
    live_cp, _ = advance_checkpoint(generator, request, live_cp, until_minute=90, stop_at_halftime=True)
    revised_result = finalize_checkpoint(generator, request, live_cp)

    assert revised_result.home_stats.current_formation == "3-4-3"
    assert revised_result.home_stats.substitutions >= 1
    assert any(
        e.event_type.value == "tactical_change" and (e.metadata or {}).get("change_id") == "cmd-ht-1"
        for e in revised_result.events
    )
    assert any(
        e.event_type.value == "substitution" and e.primary_player_id == incoming_id and e.secondary_player_id == outgoing_id
        for e in revised_result.events
    )
    # Regenerated second half produces a distinct revised second-half event stream from unmodified baseline.
    baseline_second_half = [(e.event_type.value, e.minute) for e in baseline_result.events if e.minute > 45]
    revised_second_half = [(e.event_type.value, e.minute) for e in revised_result.events if e.minute > 45]
    assert revised_second_half != baseline_second_half
