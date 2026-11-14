from app.match_engine.schemas import MatchTacticalAdjustmentInput
from app.match_engine.simulation.event_generator import MatchEventGenerator
from app.match_engine.simulation.models import MatchCompetitionType, MatchEventType, TacticalStyle

from tests.match_engine.helpers import build_request


def _identity(events, minute: int):
    return [
        (event.event_type, event.minute, event.home_score, event.away_score, event.primary_player_id)
        for event in events
        if event.minute < minute
    ]


def test_tail_resimulation_keeps_the_prefix_and_changes_the_rest() -> None:
    request = build_request(seed=17, match_id="tail-match")
    generator = MatchEventGenerator()
    baseline = generator.simulate(request)
    attacking = generator.simulate_tail(
        request,
        cursor_minute=60,
        revision=3,
        side="home",
        adjustment=MatchTacticalAdjustmentInput(
            mentality=TacticalStyle.ATTACKING,
            pressing=92,
            tempo=88,
            defensive_line=80,
        ),
    )
    defensive = generator.simulate_tail(
        request,
        cursor_minute=60,
        revision=3,
        side="home",
        adjustment=MatchTacticalAdjustmentInput(
            mentality=TacticalStyle.DEFENSIVE,
            pressing=18,
            tempo=28,
            defensive_line=22,
        ),
    )

    assert _identity(baseline.events, 60) == _identity(attacking.events, 60)
    assert _identity(baseline.events, 60) == _identity(defensive.events, 60)
    assert [
        (event.event_type, event.minute, event.home_score, event.away_score)
        for event in attacking.events
        if event.minute >= 60
    ] != [
        (event.event_type, event.minute, event.home_score, event.away_score)
        for event in defensive.events
        if event.minute >= 60
    ]


def test_league_draw_does_not_add_a_shootout() -> None:
    result = MatchEventGenerator().simulate(build_request(seed=4, match_id="league-draw-check"))
    assert result.decided_by_penalties is False
    assert not any(
        event.event_type in {MatchEventType.PENALTY_GOAL, MatchEventType.PENALTY_MISS} for event in result.events
    )


def test_extra_time_is_played_only_when_the_competition_asks_for_it() -> None:
    generator = MatchEventGenerator()
    found = None
    for seed in range(1, 48):
        request = build_request(
            seed=seed,
            match_id=f"extra-{seed}",
            competition_type=MatchCompetitionType.CUP,
            requires_winner=True,
        )
        request = request.model_copy(
            update={"competition": request.competition.model_copy(update={"extra_time": True})}
        )
        result = generator.simulate(request)
        full_time = next(event for event in result.events if event.event_type is MatchEventType.FULLTIME)
        if full_time.metadata.get("goes_to_extra_time"):
            found = result
            break
    assert found is not None
    assert any(event.metadata.get("match_phase") == "extra_time" for event in found.events)
    assert found.decided_by_penalties or found.home_score != found.away_score
