from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.match_engine.simulation.models import PlayerRole
from app.schemas.match_viewer import MatchViewerEventType, MatchViewerPlayerState, MatchViewerSide
from app.services.authoritative_spatial_simulation import (
    _line_sizes,
    build_ball_payload,
    build_player_payloads,
)


def _runtime(side: MatchViewerSide, team_id: str) -> SimpleNamespace:
    players = {}
    roles = [
        PlayerRole.GOALKEEPER,
        PlayerRole.DEFENDER,
        PlayerRole.DEFENDER,
        PlayerRole.DEFENDER,
        PlayerRole.DEFENDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.MIDFIELDER,
        PlayerRole.FORWARD,
        PlayerRole.FORWARD,
        PlayerRole.FORWARD,
    ]
    lineup = []
    for index, role in enumerate(roles, start=1):
        player_id = f"{side.value}-{index}"
        lineup.append(player_id)
        players[player_id] = SimpleNamespace(
            player_id=player_id,
            team_id=team_id,
            side=side,
            label=str(index),
            shirt_number=index,
            role=role,
            base_stamina_pct=100.0,
        )
    return SimpleNamespace(
        view=SimpleNamespace(side=side),
        players_by_id=players,
        lineup=lineup,
        current_formation="4-3-3",
    )


def _event() -> SimpleNamespace:
    view = SimpleNamespace(
        event_id="spatial-goal",
        event_type=MatchViewerEventType.GOAL,
        time_seconds=2.0,
        duration_ms=650,
        highlighted_player_ids=["home-10"],
        primary_player_id="home-10",
        secondary_player_id="away-1",
    )
    return SimpleNamespace(
        view=view,
        team_side=MatchViewerSide.HOME,
        render_contract={
            "origin": {"x": 67.0, "y": 34.0},
            "target": {"x": 96.0, "y": 36.0},
        },
    )


def _pass_event() -> SimpleNamespace:
    view = SimpleNamespace(
        event_id="spatial-pass",
        event_type=MatchViewerEventType.PASS,
        time_seconds=2.0,
        duration_ms=500,
        highlighted_player_ids=["home-9", "home-10"],
        primary_player_id="home-9",
        secondary_player_id="home-10",
    )
    return SimpleNamespace(
        view=view,
        team_side=MatchViewerSide.HOME,
        render_contract={
            "origin": {"x": 49.0, "y": 50.0},
            "target": {"x": 67.0, "y": 52.0},
            "ball": {
                "motion": "pass",
                "spin": {"x": 0.1, "y": 0.8, "z": 1.2},
                "trajectory": [
                    {"t": 0.0, "x": 49.0, "y": 50.0, "z": 0.02},
                    {"t": 0.2, "x": 55.0, "y": 50.5, "z": 0.07},
                    {"t": 0.4, "x": 61.0, "y": 51.2, "z": 0.05},
                    {"t": 0.6, "x": 67.0, "y": 52.0, "z": 0.01},
                ],
            },
        },
    )


def test_idle_player_has_no_artificial_clock_drift() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")
    positions = []
    velocities = []
    for time_seconds in (0.0, 5.0, 15.0, 30.0):
        players = build_player_payloads(
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=None,
            stage="open_play",
            clock_minute=time_seconds / 60.0,
            possession_side=MatchViewerSide.HOME,
            time_seconds=time_seconds,
        )
        player = next(item for item in players if item["player_id"] == "home-2")
        positions.append((player["position"]["x"], player["position"]["y"]))
        velocities.append((player["velocity"]["x"], player["velocity"]["y"]))

    assert positions == [positions[0]] * len(positions)
    assert velocities == [(0.0, 0.0)] * len(velocities)


def test_player_motion_has_no_large_frame_to_frame_jump() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")
    event = _event()
    previous = None
    maximum_step = 0.0

    for index in range(121):
        time_seconds = index * 0.05
        players = build_player_payloads(
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=event,
            stage="event",
            clock_minute=time_seconds / 60.0,
            possession_side=MatchViewerSide.HOME,
            time_seconds=time_seconds,
        )
        current = {item["player_id"]: item["position"] for item in players}
        if previous is not None:
            for player_id, point in current.items():
                old = previous[player_id]
                step = ((point["x"] - old["x"]) ** 2 + (point["y"] - old["y"]) ** 2) ** 0.5
                maximum_step = max(maximum_step, step)
        previous = current

    assert maximum_step < 2.0


def test_pass_hands_possession_to_receiver_after_authoritative_flight() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")
    event = _pass_event()
    owner_states = []
    positions = []

    for time_seconds in (2.0, 2.2, 2.4, 2.6, 2.8):
        players = build_player_payloads(
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=event,
            stage="event",
            clock_minute=time_seconds / 60.0,
            possession_side=MatchViewerSide.HOME,
            time_seconds=time_seconds,
        )
        ball = build_ball_payload(
            player_payloads=players,
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=event,
            stage="event",
            possession_side=MatchViewerSide.HOME,
            time_seconds=time_seconds,
        )
        owner_states.append((time_seconds, ball["owner_player_id"], ball["state"]))
        positions.append(ball["position"])

    assert owner_states[0][1] is None
    assert owner_states[0][2] == "in_flight"
    assert any(owner == "home-10" and state == "controlled" for _, owner, state in owner_states[2:])
    assert positions[1]["x"] > positions[0]["x"]
    assert positions[2]["x"] > positions[1]["x"]
    assert positions[-1]["x"] >= 66.9


def test_goal_produces_continuous_ball_flight_and_velocity() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")
    event = _event()
    previous = None
    maximum_step = 0.0
    saw_flight = False
    saw_height = False

    for index in range(80):
        time_seconds = index * 0.05
        players = build_player_payloads(
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=event,
            stage="event",
            clock_minute=time_seconds / 60.0,
            possession_side=MatchViewerSide.HOME,
            time_seconds=time_seconds,
        )
        ball = build_ball_payload(
            player_payloads=players,
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=event,
            stage="event",
            possession_side=MatchViewerSide.HOME,
            time_seconds=time_seconds,
        )
        if ball["state"] == "in_flight":
            saw_flight = True
            saw_height |= ball["height"] > 0.05
        point = ball["position"]
        if previous is not None:
            step = ((point["x"] - previous["x"]) ** 2 + (point["y"] - previous["y"]) ** 2) ** 0.5
            maximum_step = max(maximum_step, step)
        previous = point

    assert saw_flight
    assert saw_height
    assert maximum_step < 4.0


def _reduced_runtime(
    side: MatchViewerSide,
    team_id: str,
    *,
    outfield: int,
    roles: list[PlayerRole] | None = None,
    formation: str = "4-4-1",
) -> SimpleNamespace:
    """A lineup reduced by dismissals, still carrying its nominal formation.

    ``roles`` defaults to a shape that leaves one of the three lines empty,
    which is what a real dismissal-reduced side looks like once its forwards
    (or its whole midfield) have been sacrificed. That matters: the role
    branch of _line_sizes only fires when defenders, midfielders and forwards
    are all non-empty, so a balanced remainder never reaches the fallback that
    actually broke.
    """
    runtime = _runtime(side, team_id)
    assert outfield <= len(runtime.lineup) - 1, "base fixture cannot field that many outfield players"
    runtime.lineup = runtime.lineup[: outfield + 1]
    runtime.current_formation = formation
    if roles is None:
        roles = [PlayerRole.DEFENDER] * outfield
    assert len(roles) == outfield
    for player_id, role in zip(runtime.lineup[1:], roles):
        runtime.players_by_id[player_id].role = role
    return runtime


# 10 outfield is a full XI; 0 is a side reduced to its goalkeeper. Both ends
# and everything between are reachable through dismissals.
@pytest.mark.parametrize("outfield", list(range(0, 11)))
def test_line_sizes_always_cover_exactly_the_players_on_the_pitch(outfield: int) -> None:
    # _anchors indexes the outfield list by these sizes, so covering exactly the
    # players present is an invariant, not a preference.
    runtime = _reduced_runtime(MatchViewerSide.HOME, "home", outfield=outfield)

    sizes = _line_sizes(runtime)

    assert sum(sizes) == outfield, f"{outfield} outfield players mapped to {sizes}"
    assert all(size > 0 for size in sizes), f"empty line group in {sizes}"


def _payloads_for(home: SimpleNamespace, away: SimpleNamespace) -> list[dict]:
    return build_player_payloads(
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=None,
        stage="open_play",
        clock_minute=1.0,
        possession_side=MatchViewerSide.HOME,
        time_seconds=60.0,
    )


def test_player_payloads_survive_a_lineup_reduced_by_red_cards() -> None:
    # The exact production failure: a 9-man side (8 outfield) still advertising
    # "4-4-1" (9 outfield), whose remaining players do not split into three
    # non-empty lines. Anchoring used to fall back to a fixed [4, 4, 1] and
    # index a ninth outfield player that no longer existed.
    home = _reduced_runtime(
        MatchViewerSide.HOME,
        "home",
        outfield=8,
        roles=[PlayerRole.DEFENDER] * 4 + [PlayerRole.MIDFIELDER] * 4,
    )
    away = _runtime(MatchViewerSide.AWAY, "away")

    payloads = _payloads_for(home, away)

    assert len(payloads) == len(home.lineup) + len(away.lineup)
    home_ids = {item["player_id"] for item in payloads if item["side"] is MatchViewerSide.HOME}
    assert home_ids == set(home.lineup)
    for item in payloads:
        anchor = item["anchor_position"]
        assert 0.0 <= float(anchor["x"]) <= 100.0
        assert 0.0 <= float(anchor["y"]) <= 100.0


def test_player_payloads_handle_a_goalkeeper_only_lineup() -> None:
    home = _reduced_runtime(MatchViewerSide.HOME, "home", outfield=0)
    away = _runtime(MatchViewerSide.AWAY, "away")

    payloads = _payloads_for(home, away)

    home_ids = [item["player_id"] for item in payloads if item["side"] is MatchViewerSide.HOME]
    assert home_ids == home.lineup


def test_line_sizes_ignore_a_formation_that_no_longer_matches_the_pitch() -> None:
    # A dismissal does not rewrite current_formation, so the stale string must
    # lose to the players actually available.
    runtime = _reduced_runtime(MatchViewerSide.HOME, "home", outfield=7, formation="4-4-2")

    sizes = _line_sizes(runtime)

    assert sum(sizes) == 7


def test_lineup_referencing_an_unknown_player_fails_loudly() -> None:
    """Documents the module-wide contract: lineup is a subset of players_by_id.

    Every access in this module indexes players_by_id directly, including the
    payload loop, so a lineup entry with no player record is a data-integrity
    fault upstream rather than a state playback should absorb. Pinning the
    KeyError keeps a future "fix" from silently dropping the player and
    rendering a match with ten men when eleven were selected.
    """
    runtime = _reduced_runtime(MatchViewerSide.HOME, "home", outfield=8)
    runtime.players_by_id.pop(runtime.lineup[-1])

    with pytest.raises(KeyError):
        _line_sizes(runtime)


def test_resting_shape_keeps_attack_ahead_of_defense() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")

    payloads = _payloads_for(home, away)
    home_defense = next(item for item in payloads if item["player_id"] == "home-2")
    home_attack = next(item for item in payloads if item["player_id"] == "home-9")
    away_defense = next(item for item in payloads if item["player_id"] == "away-2")
    away_attack = next(item for item in payloads if item["player_id"] == "away-9")

    assert home_attack["position"]["x"] > home_defense["position"]["x"] + 8.0
    assert away_defense["position"]["x"] > away_attack["position"]["x"] + 8.0


def test_open_play_depth_moves_the_block_and_hands_the_ball_to_one_carrier() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")

    def midfield_x(depth: float) -> float:
        players = build_player_payloads(
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=None,
            stage="pre",
            clock_minute=12.0,
            possession_side=MatchViewerSide.HOME,
            time_seconds=40.0,
            phase_depth=depth,
        )
        return next(item["position"]["x"] for item in players if item["player_id"] == "home-6")

    assert midfield_x(0.8) > midfield_x(0.2) + 12.0

    players = build_player_payloads(
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=None,
        stage="pre",
        clock_minute=12.0,
        possession_side=MatchViewerSide.HOME,
        time_seconds=40.0,
        phase_depth=0.55,
    )
    carriers = [item for item in players if item["has_possession"]]
    assert len(carriers) == 1
    assert carriers[0]["side"] is MatchViewerSide.HOME
    defenders = [item for item in players if item["player_id"] in {"away-2", "away-3", "away-4", "away-5"}]
    line = [item["position"]["x"] for item in defenders]
    assert max(line) - min(line) < 8.0

    ball = build_ball_payload(
        player_payloads=players,
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=None,
        stage="pre",
        possession_side=MatchViewerSide.HOME,
        time_seconds=40.0,
    )
    assert ball["state"] == "controlled"
    assert ball["owner_player_id"] == carriers[0]["player_id"]
    assert abs(ball["position"]["x"] - carriers[0]["position"]["x"]) < 1.5


def _open_play(home: SimpleNamespace, away: SimpleNamespace, **overrides: object) -> list[dict]:
    payload = {
        "home_runtime": home,
        "away_runtime": away,
        "home_attacks_right": True,
        "active_event": None,
        "stage": "pre",
        "clock_minute": 12.0,
        "possession_side": MatchViewerSide.HOME,
        "time_seconds": 40.0,
        "phase_depth": 0.55,
    }
    payload.update(overrides)
    return build_player_payloads(**payload)


def test_high_line_and_press_change_the_block() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")

    def home_defense(line: float) -> float:
        home.defensive_line = line
        players = _open_play(home, away, phase_depth=0.45)
        return next(item["position"]["x"] for item in players if item["player_id"] == "home-2")

    assert home_defense(80) > home_defense(20) + 6.0

    def away_gap(press: float) -> float:
        away.press_intensity = press
        players = _open_play(home, away, phase_depth=0.75)
        ball = build_ball_payload(
            player_payloads=players,
            home_runtime=home,
            away_runtime=away,
            home_attacks_right=True,
            active_event=None,
            stage="pre",
            possession_side=MatchViewerSide.HOME,
            time_seconds=40.0,
        )
        line = [item["position"]["x"] for item in players if item["player_id"] in {"away-2", "away-3", "away-4", "away-5"}]
        return abs((sum(line) / len(line)) - ball["position"]["x"])

    assert away_gap(85) < away_gap(20) - 2.0


def test_corner_packs_the_box_and_a_goal_does_not() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")
    corner = SimpleNamespace(
        view=SimpleNamespace(
            event_id="spatial-corner",
            event_type=MatchViewerEventType.SET_PIECE,
            time_seconds=8.0,
            duration_ms=900,
            highlighted_player_ids=["home-9"],
            primary_player_id="home-9",
            secondary_player_id=None,
        ),
        team_side=MatchViewerSide.HOME,
        metadata={"set_piece_kind": "corner"},
        render_contract={"origin": {"x": 92.0, "y": 12.0}, "target": {"x": 88.0, "y": 48.0}},
    )
    packed = _open_play(home, away, active_event=corner, stage="event", phase_depth=None, time_seconds=8.0, clock_minute=20.0)
    open_play = _open_play(home, away, phase_depth=None, time_seconds=8.0, clock_minute=20.0)
    taker = next(item for item in packed if item["player_id"] == "home-9")
    resting = next(item for item in open_play if item["player_id"] == "home-9")
    assert taker["position"]["y"] < resting["position"]["y"] - 8.0
    packed_line = [item["position"]["x"] for item in packed if item["player_id"] in {"away-2", "away-3", "away-4", "away-5"}]
    open_line = [item["position"]["x"] for item in open_play if item["player_id"] in {"away-2", "away-3", "away-4", "away-5"}]
    assert sum(packed_line) / len(packed_line) > (sum(open_line) / len(open_line)) + 4.0

    goal = _event()
    during_goal = _open_play(home, away, active_event=goal, stage="event", phase_depth=None, time_seconds=2.0, clock_minute=12.0)
    goal_line = [item["position"]["x"] for item in during_goal if item["player_id"] in {"away-2", "away-3", "away-4", "away-5"}]
    assert sum(goal_line) / len(goal_line) < sum(packed_line) / len(packed_line)


def test_late_minutes_drop_the_attack_deeper() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")

    def attacker(clock: float) -> float:
        players = _open_play(home, away, phase_depth=None, clock_minute=clock, time_seconds=clock * 60.0)
        return next(item["position"]["x"] for item in players if item["player_id"] == "home-9")

    early = attacker(10.0)
    late = attacker(82.0)
    assert late < early - 1.0
    assert abs(attacker(20.0) - attacker(40.0)) < 0.05


def test_open_play_puts_a_runner_on_the_ball_and_a_presser_on_the_carrier() -> None:
    home = _runtime(MatchViewerSide.HOME, "home")
    away = _runtime(MatchViewerSide.AWAY, "away")
    players = _open_play(home, away, phase_depth=0.55)
    carriers = [item for item in players if item["has_possession"]]
    assert len(carriers) == 1
    carrier = carriers[0]
    ball = build_ball_payload(
        player_payloads=players,
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=None,
        stage="pre",
        possession_side=MatchViewerSide.HOME,
        time_seconds=40.0,
    )
    assert ball["position"]["x"] > carrier["position"]["x"] + 0.4
    assert abs(ball["position"]["x"] - carrier["position"]["x"]) < 1.5

    attackers = [
        item
        for item in players
        if item["player_id"] in {"home-9", "home-10", "home-11"} and not item["has_possession"]
    ]
    assert max(item["position"]["x"] for item in attackers) > carrier["position"]["x"] + 3.0

    mids = [item for item in players if item["player_id"] in {"away-6", "away-7", "away-8"}]
    pressing = [item for item in mids if item["state"] is MatchViewerPlayerState.PRESSING]
    assert len(pressing) == 1

    def gap(item: dict) -> float:
        return abs(item["position"]["x"] - ball["position"]["x"]) + abs(item["position"]["y"] - ball["position"]["y"])

    assert gap(pressing[0]) + 1.0 < min(gap(item) for item in mids if item is not pressing[0])
    line = [item["position"]["x"] for item in players if item["player_id"] in {"away-2", "away-3", "away-4", "away-5"}]
    assert max(line) - min(line) < 8.0
