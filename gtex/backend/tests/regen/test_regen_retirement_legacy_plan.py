from app.regen_career.retirement_legacy_plan import build_retirement_legacy_plan


def test_standard_retirement_creates_one_successor_plan() -> None:
    plan = build_retirement_legacy_plan(
        retiring_regen_id="regen-1",
        retiring_player_id="player-1",
        club_id="club-1",
        current_gsi=84,
        potential_floor_gsi=88,
    )

    assert plan.successor_count == 1
    assert plan.successor_quality_floor_gsi == 84
    assert not plan.exceptional_successor_candidate
    assert plan.trigger_key == "regen-retirement:regen-1:club-1"


def test_exceptional_retirement_allows_two_successor_candidates() -> None:
    plan = build_retirement_legacy_plan(
        retiring_regen_id="regen-2",
        retiring_player_id="player-2",
        club_id="club-2",
        current_gsi=92,
        potential_floor_gsi=94,
    )

    assert plan.successor_count == 2
    assert plan.successor_quality_floor_gsi == 94
    assert plan.exceptional_successor_candidate
