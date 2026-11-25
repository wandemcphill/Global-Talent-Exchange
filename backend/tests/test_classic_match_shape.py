from math import hypot
from types import SimpleNamespace

from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.services.team_factory import SyntheticSquadFactory
from app.match_engine.simulation.models import PlayerRole
from app.schemas.match_viewer import (
    MatchViewerEventType,
    MatchViewerSide,
    MatchViewerTeamView,
)
from app.services.authoritative_spatial_simulation import _anchors, build_ball_payload, build_player_payloads
from app.services.match_timeline_service import MatchTimelineService, _TeamRuntime, _ViewerEventContext
from backend.tests.match_engine.helpers import build_request, build_team


def test_five_line_shape_is_not_rewritten_to_4_3_3() -> None:
    service = MatchTimelineService()
    assert service._normalize_formation("4-1-2-1-2") == "4-1-2-1-2"
    assert service._normalize_formation("5-3-2") == "5-3-2"
    assert service._normalize_formation("") == "4-3-3"
    runtime = SimpleNamespace(players_by_id={})
    assert service._line_sizes("4-1-2-1-2", [str(index) for index in range(10)], runtime) == [4, 1, 2, 1, 2]
    assert service._line_sizes("5-3-2", [str(index) for index in range(10)], runtime) == [5, 3, 2]


def test_posted_shape_changes_the_team_from_that_event() -> None:
    service = MatchTimelineService()
    home = _team_runtime(MatchViewerSide.HOME, "4-3-3")
    away = _team_runtime(MatchViewerSide.AWAY, "4-3-3")
    event = _ViewerEventContext(
        view=_event_view(MatchViewerEventType.NEUTRAL, "Shape change."),
        source_type="tactical_change",
        team_side=MatchViewerSide.HOME,
        home_formation="4-4-2",
    )
    service._apply_persistent_event(home, away, event)
    assert home.current_formation == "4-4-2"
    assert away.current_formation == "4-3-3"


def test_five_three_two_anchors_keep_five_defenders() -> None:
    home = _pitch_runtime("5-3-2")
    away = _pitch_runtime("4-4-2", side=MatchViewerSide.AWAY)
    players = build_player_payloads(
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=None,
        stage="pre",
        clock_minute=12,
        possession_side=MatchViewerSide.HOME,
        time_seconds=20,
    )
    defenders = [
        player
        for player in players
        if player["side"] is MatchViewerSide.HOME and player["role"] is PlayerRole.DEFENDER
    ]
    forwards = [
        player
        for player in players
        if player["side"] is MatchViewerSide.HOME and player["role"] is PlayerRole.FORWARD
    ]
    assert len(defenders) == 5
    assert len(forwards) == 2
    defender_x = [player["anchor_position"]["x"] for player in defenders]
    assert max(defender_x) - min(defender_x) < 8
    assert min(player["anchor_position"]["x"] for player in forwards) > max(defender_x)


def test_the_lineup_screen_reads_the_saved_sheet() -> None:
    from app.lineups.service import filed_sheet_view

    view = filed_sheet_view(
        "club-1",
        {
            "formation": "5-3-2",
            "starting_xi_ids": [f"squad-{index}" for index in range(11)],
            "bench_ids": ["squad-12"],
            "verdict_reason": "Filed in a back five.",
        },
        canonical_ids={"squad-0": "player-0", "squad-12": "player-12"},
    )
    assert view is not None
    assert view.formation == "5-3-2"
    assert view.starter_player_ids[0] == "player-0"
    assert view.starter_player_ids[1] == "squad-1"
    assert view.bench_player_ids == ["player-12"]
    assert filed_sheet_view("club-1", {"formation": "4-3-3", "starting_xi_ids": ["only-one"]}) is None


def test_an_accepted_owner_eleven_is_relined_when_the_shape_changes() -> None:
    from app.owner_console.autonomous_staff_engine import (
        order_xi_for_shape,
        sheet_order_needs_reline,
        sheet_slot_lines,
    )
    from app.owner_console.service import _tactics_for_filed_sheet

    assert sheet_slot_lines("5-3-2") == ["GK", *["DEF"] * 5, *["MID"] * 3, *["FWD"] * 2]
    tactics = _tactics_for_filed_sheet({"formation": "4-3-3", "formations": ["4-3-3"]}, "5-3-2")
    assert tactics["formation"] == "5-3-2"
    assert tactics["formations"][0] == "5-3-2"

    hired = {"team_instructions_filed": True, "preferred_formation": "5-3-2", "preferred_formations": ["5-3-2"]}
    assert sheet_order_needs_reline(
        owner_formation="4-3-3",
        chosen_formation="5-3-2",
        shape_before_hire="4-3-3",
        hired_profile=hired,
    )
    assert not sheet_order_needs_reline(
        owner_formation="5-3-2",
        chosen_formation="5-3-2",
        shape_before_hire="4-3-3",
        hired_profile=hired,
    )
    assert not sheet_order_needs_reline(
        owner_formation="",
        chosen_formation="4-4-2",
        shape_before_hire="4-4-2",
        hired_profile=hired,
    )

    shirts = [
        SimpleNamespace(id="gk", line="GK"),
        SimpleNamespace(id="st", line="FWD"),
        SimpleNamespace(id="d1", line="DEF"),
        SimpleNamespace(id="lm", line="MID"),
        SimpleNamespace(id="d2", line="DEF"),
        SimpleNamespace(id="rw", line="FWD"),
        SimpleNamespace(id="d3", line="DEF"),
        SimpleNamespace(id="cm", line="MID"),
        SimpleNamespace(id="d4", line="DEF"),
        SimpleNamespace(id="lw", line="FWD"),
        SimpleNamespace(id="rm", line="MID"),
    ]
    ordered = order_xi_for_shape(shirts, "5-3-2", lambda player: player.line)
    assert [player.id for player in ordered] == [
        "gk",
        "d1",
        "d2",
        "d3",
        "d4",
        "lm",
        "cm",
        "rm",
        "st",
        "rw",
        "lw",
    ]
    factory = SyntheticSquadFactory.__new__(SyntheticSquadFactory)
    assert factory._resolve_player_role(SimpleNamespace(position="LM", normalized_position=None)) is PlayerRole.MIDFIELDER
    assert factory._resolve_player_role(SimpleNamespace(position="ST", normalized_position=None)) is PlayerRole.FORWARD


def test_a_saved_4_3_3_sheet_is_relined_into_the_hired_shape() -> None:
    from app.owner_console.autonomous_staff_engine import resolve_sheet_formation

    hired = {
        "team_instructions_filed": True,
        "preferred_formation": "5-3-2",
        "preferred_formations": ["5-3-2", "4-4-2"],
        "mentality": "attacking",
    }
    assert resolve_sheet_formation("4-3-3", hired) == "5-3-2"
    assert resolve_sheet_formation("4-4-2", hired) == "4-4-2"
    assert resolve_sheet_formation("4-3-3", None) == "4-3-3"

    def player(player_id: str, position: str) -> SimpleNamespace:
        return SimpleNamespace(id=player_id, position=position, normalized_position=None)

    sheet = [
        player("gk", "GK"),
        player("d1", "CB"),
        player("d2", "CB"),
        player("d3", "LB"),
        player("d4", "RB"),
        player("m1", "CM"),
        player("m2", "CM"),
        player("m3", "CM"),
        player("f1", "ST"),
        player("f2", "ST"),
        player("f3", "ST"),
    ]
    lined = SyntheticSquadFactory.__new__(SyntheticSquadFactory)._reslot_for_formation(sheet, "5-3-2")
    roles = [role for _player, role in lined]
    assert roles == (
        [PlayerRole.GOALKEEPER]
        + [PlayerRole.DEFENDER] * 5
        + [PlayerRole.MIDFIELDER] * 3
        + [PlayerRole.FORWARD] * 2
    )
    assert [item.id for item, _role in lined[:6]] == ["gk", "d1", "d2", "d3", "d4", "m1"]
    assert [item.id for item, _role in lined[-2:]] == ["f2", "f3"]


def test_named_passes_join_the_commentary_before_the_chance() -> None:
    from app.live_matches.router import _timeline_with_passes

    view = SimpleNamespace(
        home_team=SimpleNamespace(team_id="home", team_name="Ekiti FC", short_name="EKI"),
        away_team=SimpleNamespace(team_id="away", team_name="Lagos Titans", short_name="LAG"),
    )
    frames = [
        SimpleNamespace(
            frame_id="pass-a",
            overlay_text="Ekiti play it out from the back. Adeyemi finds the pivot.",
            time_seconds=10.0,
            clock_minute=12.0,
            possession_side=MatchViewerSide.HOME,
            home_score=0,
            away_score=0,
        ),
        SimpleNamespace(
            frame_id="pass-a-repeat",
            overlay_text="Ekiti play it out from the back. Adeyemi finds the pivot.",
            time_seconds=11.0,
            clock_minute=12.0,
            possession_side=MatchViewerSide.HOME,
            home_score=0,
            away_score=0,
        ),
        SimpleNamespace(
            frame_id="pass-b",
            overlay_text="Ekiti move it through the lines. The pivot finds the striker.",
            time_seconds=14.0,
            clock_minute=14.0,
            possession_side=MatchViewerSide.HOME,
            home_score=0,
            away_score=0,
        ),
    ]
    chance = SimpleNamespace(
        time_seconds=20.0,
        event_id="shot-1",
        event_type=MatchViewerEventType.ATTACK,
        minute=16,
        banner_text="Shot",
        commentary="Adeyemi shoots from the edge of the box.",
        team_id="home",
        team_name="Ekiti FC",
        primary_player_name="Adeyemi",
        secondary_player_name=None,
        home_score=0,
        away_score=0,
        flags=[],
    )
    timeline = _timeline_with_passes(view, frames, [chance])
    assert [item["type"] for item in timeline] == ["pass", "pass", "attack"]
    assert timeline[0]["team_name"] == "EKI"
    assert "finds the pivot" in str(timeline[0]["description"])
    assert "finds the striker" in str(timeline[1]["description"])
    assert timeline[-1]["description"] == "Adeyemi shoots from the edge of the box."


def test_named_passes_follow_the_shape_and_stay_one_step_apart() -> None:
    service = MatchTimelineService()
    back_five = _pitch_runtime("5-3-2")
    defenders = {f"home-{index}" for index in range(2, 7)}
    for beat in range(1, 8):
        pair = service._pass_pair(back_five, beat)
        assert pair is not None
        for player_id in pair:
            if player_id in defenders:
                assert player_id == "home-4"

    wide = _pitch_runtime("4-3-3")
    wide.width = 78
    anchors = _anchors(wide, True)
    previous = None
    flank_ids = set()
    for beat in range(1, 9):
        pair = service._pass_pair(wide, beat)
        assert pair is not None
        if previous is not None:
            assert pair[0] == previous
            start = anchors[previous]
            end = anchors[pair[1]]
            assert hypot(start["x"] - end["x"], start["y"] - end["y"]) < 34
        previous = pair[1]
        flank_ids.update(pair)
    assert "home-2" in flank_ids or "home-5" in flank_ids

    pair_strikers = _pitch_runtime("4-4-2")
    seen = set()
    for beat in range(1, 10):
        pair = service._pass_pair(pair_strikers, beat)
        assert pair is not None
        seen.update(player_id for player_id in pair if player_id in {"home-10", "home-11"})
    assert seen == {"home-10", "home-11"}


def test_goalkeeper_stands_in_goal_when_the_sheet_lists_them_last() -> None:
    home = _pitch_runtime("4-4-2")
    keeper_id = home.lineup.pop(0)
    home.lineup.append(keeper_id)
    players = build_player_payloads(
        home_runtime=home,
        away_runtime=_pitch_runtime("4-3-3", side=MatchViewerSide.AWAY),
        home_attacks_right=True,
        active_event=None,
        stage="pre",
        clock_minute=8,
        possession_side=MatchViewerSide.HOME,
        time_seconds=12,
    )
    keeper = next(player for player in players if player["player_id"] == keeper_id)
    outfield = [
        player
        for player in players
        if player["side"] is MatchViewerSide.HOME and player["player_id"] != keeper_id
    ]
    assert keeper["role"] is PlayerRole.GOALKEEPER
    assert keeper["anchor_position"]["x"] < min(player["anchor_position"]["x"] for player in outfield)


def test_shot_frame_ball_belongs_to_the_shooter_named_in_commentary() -> None:
    home = _pitch_runtime("4-4-2")
    away = _pitch_runtime("5-3-2", side=MatchViewerSide.AWAY)
    home.players_by_id["home-9"].player_name = "Shooting Forward"
    commentary = "Shooting Forward shoots from the edge of the box."
    event = SimpleNamespace(
        view=SimpleNamespace(
            event_id="shot-1",
            event_type=MatchViewerEventType.GOAL,
            time_seconds=2.0,
            duration_ms=650,
            highlighted_player_ids=["home-9"],
            primary_player_id="home-9",
            primary_player_name="Shooting Forward",
            secondary_player_id=None,
            commentary=commentary,
        ),
        team_side=MatchViewerSide.HOME,
        render_contract={
            "origin": {"x": 78.0, "y": 48.0},
            "target": {"x": 96.0, "y": 50.0},
        },
    )
    players = build_player_payloads(
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=event,
        stage="event",
        clock_minute=40,
        possession_side=MatchViewerSide.HOME,
        time_seconds=6.0,
    )
    ball = build_ball_payload(
        player_payloads=players,
        home_runtime=home,
        away_runtime=away,
        home_attacks_right=True,
        active_event=event,
        stage="event",
        possession_side=MatchViewerSide.HOME,
        time_seconds=6.0,
    )
    assert "Shooting Forward" in commentary
    assert ball["owner_player_id"] == "home-9"
    assert ball["state"] == "controlled"


def test_chance_frame_slows_before_the_outcome_and_keeps_the_hired_shape() -> None:
    request = build_request(
        seed=33,
        home_team=build_team("home", "North City", 84, formation="5-3-2"),
        away_team=build_team("away", "South Town", 78, formation="4-4-2"),
    )
    view = MatchTimelineService().build_from_replay_payload(
        MatchSimulationService().build_replay_payload(request)
    )
    assert view.home_team.formation == "5-3-2"
    assert view.away_team.formation == "4-4-2"
    chance = next(
        event
        for event in view.events
        if event.event_type
        in {
            MatchViewerEventType.GOAL,
            MatchViewerEventType.SAVE,
            MatchViewerEventType.MISS,
            MatchViewerEventType.ATTACK,
        }
    )
    held = [
        frame
        for frame in view.frames
        if frame.active_event_id == chance.event_id and frame.playback_rate < 1
    ]
    assert held
    assert any(frame.playback_rate <= 0.5 for frame in held)
    named = [
        frame
        for frame in view.frames
        if frame.active_event_id is None and frame.overlay_text and " finds " in frame.overlay_text
    ]
    assert named
    sample = named[0]
    receiver_name = sample.overlay_text.split(" finds ", 1)[1].split(".")[0].strip()
    owner = next(player for player in sample.players if player.player_id == sample.ball.owner_player_id)
    assert receiver_name == (owner.player_name or owner.label)


def _team_runtime(side: MatchViewerSide, formation: str) -> _TeamRuntime:
    view = MatchViewerTeamView(
        team_id=side.value,
        team_name=side.value,
        short_name=side.value[:3].upper(),
        side=side,
        formation=formation,
        primary_color="#112233",
        secondary_color="#ffffff",
        accent_color="#00aaff",
        goalkeeper_color="#eeeeee",
    )
    return _TeamRuntime(
        view=view,
        players_by_id={},
        lineup=[],
        bench=[],
        current_formation=formation,
    )


def _event_view(event_type: MatchViewerEventType, commentary: str):
    from app.schemas.match_viewer import MatchViewerEventView

    return MatchViewerEventView(
        event_id="shape-1",
        sequence=1,
        event_type=event_type,
        minute=30,
        clock_label="30'",
        time_seconds=30,
        home_score=0,
        away_score=0,
        banner_text=commentary,
        commentary=commentary,
    )


def _pitch_runtime(formation: str, side: MatchViewerSide = MatchViewerSide.HOME) -> SimpleNamespace:
    lines = [int(part) for part in formation.split("-")]
    roles = (
        [PlayerRole.GOALKEEPER]
        + [PlayerRole.DEFENDER] * lines[0]
        + [PlayerRole.MIDFIELDER] * sum(lines[1:-1])
        + [PlayerRole.FORWARD] * lines[-1]
    )
    players = {}
    lineup = []
    prefix = side.value
    for index, role in enumerate(roles, start=1):
        player_id = f"{prefix}-{index}"
        lineup.append(player_id)
        players[player_id] = SimpleNamespace(
            player_id=player_id,
            team_id=prefix,
            side=side,
            label=str(index),
            shirt_number=index,
            role=role,
            player_name=f"{prefix} {index}",
            base_stamina_pct=100.0,
        )
    return SimpleNamespace(
        view=SimpleNamespace(side=side),
        players_by_id=players,
        lineup=lineup,
        current_formation=formation,
        defensive_line=50.0,
        press_intensity=50.0,
        width=50.0,
    )
