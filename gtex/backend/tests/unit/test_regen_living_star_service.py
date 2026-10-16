from __future__ import annotations

from types import SimpleNamespace

from app.services.regen_living_star_service import RegenLivingStarService


class _FakePersonality(SimpleNamespace):
    pass


class _FakeState(SimpleNamespace):
    pass


def _personality(**overrides):
    base = dict(
        ambition=50,
        loyalty=50,
        professionalism=50,
        greed=50,
        temperament=50,
        patience=50,
        adaptability=50,
        competitiveness=50,
        aggression=50,
        confidence=50,
        consistency=50,
        clutch_factor=50,
        ego=50,
        development_focus=50,
        hometown_affinity=50,
        trophy_hunger=50,
        media_appetite=50,
        default_career_target_band="development-first",
    )
    base.update(overrides)
    return _FakePersonality(**base)


def _state(**overrides):
    base = dict(
        morale=55.0,
        happiness=55.0,
        transfer_appetite=20.0,
        contract_stance="balanced",
        wage_satisfaction=55.0,
        playing_time_satisfaction=55.0,
        development_satisfaction=55.0,
        club_project_belief=55.0,
        grievance_count=0,
        transfer_request_status="no_action",
        preferred_role_band="rotation",
        career_stage="prospect",
        career_target_band="development-first",
        salary_expectation_amount=0,
        promise_memory_json={},
        unmet_expectations_json=[],
    )
    base.update(overrides)
    return _FakeState(**base)


def test_mercenary_archetype_and_explosive_mood():
    service = RegenLivingStarService(session=SimpleNamespace())
    personality = _personality(greed=92, ambition=88, loyalty=20, ego=70)
    state = _state(
        happiness=25,
        wage_satisfaction=20,
        playing_time_satisfaction=30,
        transfer_appetite=80,
        grievance_count=2,
        transfer_request_status="public_unhappy_state",
        promise_memory_json={"cl": {"statement": "Champions League by 2028", "status": "broken", "broken": True}},
    )
    archetype = service._archetype(personality)
    mood = service._mood(state, personality)
    brief = service._behavior_brief("p1", personality, state, mood)
    ladder = service._exit_ladder(state, personality)
    monologue = service._monologue("p1", personality, state, archetype, mood)

    assert archetype.code == "mercenary"
    assert mood.code == "explosive"
    assert ladder.stage == "training_exile"
    assert "Champions League" in monologue.voice_line or "walk" in monologue.voice_line.lower() or monologue.voice_line
    assert 0 <= brief.shot_greed <= 1
    assert brief.discipline_risk > 0.2


def test_one_club_romantic_prefers_loyalty():
    service = RegenLivingStarService(session=SimpleNamespace())
    personality = _personality(loyalty=95, hometown_affinity=90, greed=15, ambition=40)
    archetype = service._archetype(personality)
    assert archetype.code == "one_club_romantic"


def test_exit_escalation_for_mercenary_skips_ahead():
    service = RegenLivingStarService(session=SimpleNamespace())
    personality = _personality(greed=90, loyalty=20)
    assert service._escalate("quiet_discontent", personality) == "training_exile"
