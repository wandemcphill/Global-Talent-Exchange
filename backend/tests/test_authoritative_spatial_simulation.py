from __future__ import annotations

from types import SimpleNamespace

from app.match_engine.simulation.models import PlayerRole
from app.schemas.match_viewer import MatchViewerEventType, MatchViewerSide
from app.services.authoritative_spatial_simulation import build_ball_payload, build_player_payloads


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
