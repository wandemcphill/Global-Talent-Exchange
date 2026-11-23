from __future__ import annotations

from types import SimpleNamespace

from app.match_engine.services.match_report import build_simulated_match_report_from_payload
from app.owner_console import competitions, engine
from app.routes.match_viewer import _attach_match_report_metadata
from app.schemas.match_viewer import (
    MatchViewerEventType,
    MatchViewerEventView,
    MatchViewerSide,
    MatchViewerTeamView,
    MatchViewStateView,
)


def _side(name: str, strength: float, prefix: str) -> dict[str, object]:
    roles = ["GK", "DF", "DF", "DF", "DF", "MF", "MF", "MF", "FW", "FW", "FW"]
    return {
        "name": name,
        "strength": strength,
        "mentality": "balanced",
        "formation": "4-3-3",
        "avg_morale": 75,
        "xi_players": [
            {
                "id": f"{prefix}-p{idx + 1}",
                "name": f"{name} {role} {idx + 1}",
                "rating": int(strength),
                "morale": 75,
                "fitness": 90,
            }
            for idx, role in enumerate(roles)
        ],
    }


def test_owner_console_simulate_match_includes_full_stats_scorers_and_assists() -> None:
    sim = engine.simulate_match(
        "sim-report-seed-42",
        _side("Lagos Lions", 79.0, "home"),
        _side("Abuja Eagles", 74.0, "away"),
    )

    stats = sim["stats"]
    assert stats["home_possession"] + stats["away_possession"] == 100
    assert stats["home_shots"] >= sim["home_goals"]
    assert stats["away_shots"] >= sim["away_goals"]
    assert stats["home_expected_goals"] is not None
    assert stats["away_expected_goals"] is not None
    assert stats["home_saves"] >= 0
    assert stats["away_saves"] >= 0

    goals = sim["goals"]
    assert len(goals) == sim["home_goals"] + sim["away_goals"]
    for goal in goals:
        assert goal["scorer_name"]
        if goal["is_penalty"]:
            assert goal["assist_name"] is None
        elif goal["assist_name"]:
            assert goal["assist_name"] != goal["scorer_name"]

    report = sim["match_report"]
    assert report["is_simulated"] is True
    assert report["home_score"] == sim["home_goals"]
    assert report["away_score"] == sim["away_goals"]
    assert report["motm"]["available"] is True
    assert report["motm"]["player_name"]
    assert len(report["player_stats"]) >= 11


def test_match_dict_reconstructs_report_for_legacy_played_owner_match() -> None:
    legacy_match = SimpleNamespace(
        id="legacy-m-1",
        competition_id="comp-1",
        round_number=2,
        home_club_id="club-h",
        away_club_id="club-a",
        home_name="Lagos Lions",
        away_name="Abuja Eagles",
        status="played",
        home_goals=2,
        away_goals=1,
        played_at=None,
        events_json=[
            {
                "minute": 18,
                "type": "goal",
                "team": "home",
                "scorer": "Victor Osimhen",
                "assist": "Ademola Lookman",
                "text": "Victor Osimhen scores!",
            },
            {
                "minute": 44,
                "type": "yellow_card",
                "team": "away",
                "player": "Musa Bello",
                "text": "Yellow card for Musa Bello.",
            },
            {
                "minute": 62,
                "type": "goal",
                "team": "away",
                "scorer": "Ahmed Musa",
                "text": "Ahmed Musa levels it!",
            },
            {
                "minute": 84,
                "type": "goal",
                "team": "home",
                "scorer": "Alex Iwobi",
                "assist": "Wilfred Ndidi",
                "text": "Alex Iwobi wins it late!",
            },
        ],
        narrative_json={
            "momentum": [56, 58, 54, 60],
            "expected_goals": [1.85, 0.91],
        },
    )

    payload = competitions.match_dict(legacy_match, full=True)
    assert payload["is_simulated"] is True
    assert payload["stats"]["home_possession"] + payload["stats"]["away_possession"] == 100
    assert payload["stats"]["home_expected_goals"] == 1.85
    assert payload["stats"]["away_expected_goals"] == 0.91
    assert payload["stats"]["home_assists"] == 2
    assert payload["stats"]["away_yellow_cards"] == 1
    assert len(payload["goals"]) == 3
    assert payload["goals"][0]["scorer_name"] == "Victor Osimhen"
    assert payload["goals"][0]["assist_name"] == "Ademola Lookman"


def test_match_viewer_attaches_simulated_metadata_and_report() -> None:
    view_state = MatchViewStateView(
        match_id="match_fast_1",
        source="match_engine",
        duration_seconds=300,
        home_team=MatchViewerTeamView(
            team_id="home-1",
            team_name="Lagos United",
            short_name="LAG",
            side=MatchViewerSide.HOME,
            formation="4-3-3",
            primary_color="#00aa55",
            secondary_color="#ffffff",
            accent_color="#ffcc00",
            goalkeeper_color="#222222",
        ),
        away_team=MatchViewerTeamView(
            team_id="away-1",
            team_name="Accra Sparks",
            short_name="ACC",
            side=MatchViewerSide.AWAY,
            formation="4-2-3-1",
            primary_color="#cc2222",
            secondary_color="#ffffff",
            accent_color="#000000",
            goalkeeper_color="#111111",
        ),
        events=[
            MatchViewerEventView(
                event_id="e1",
                sequence=1,
                event_type=MatchViewerEventType.GOAL,
                minute=31,
                clock_label="31'",
                time_seconds=90.0,
                team_id="home-1",
                team_name="Lagos United",
                primary_player_id="hp1",
                primary_player_name="Victor Osimhen",
                secondary_player_id="hp2",
                secondary_player_name="Ademola Lookman",
                home_score=1,
                away_score=0,
                banner_text="GOAL",
                commentary="Osimhen finishes Lookman's through ball.",
            )
        ],
        frames=[],
    )

    enriched = _attach_match_report_metadata(
        view_state,
        metadata_json={
            "is_simulated": True,
            "match_status": "completed",
            "home_score": 1,
            "away_score": 0,
            "fast_match": {"match_id": "match_fast_1", "result": "win"},
        },
        match=None,
    )

    assert enriched.is_simulated is True
    assert enriched.match_status == "completed"
    assert enriched.match_report is not None
    assert enriched.match_report["home_score"] == 1
    assert enriched.match_report["away_score"] == 0
    assert enriched.match_report["goals"][0]["scorer_name"] == "Victor Osimhen"
    assert enriched.match_report["goals"][0]["assist_name"] == "Ademola Lookman"
    assert enriched.stats is not None
    assert enriched.stats["home_assists"] == 1


def test_build_simulated_match_report_from_payload_excludes_penalty_keeper_as_assist() -> None:
    report = build_simulated_match_report_from_payload(
        match_id="pen-1",
        home_team_id="h",
        away_team_id="a",
        home_team_name="Home FC",
        away_team_name="Away FC",
        home_score=1,
        away_score=0,
        events=[
            {
                "minute": 70,
                "event_type": "penalty_scored",
                "team_id": "h",
                "primary_player_name": "Striker 9",
                "secondary_player_name": "Away Keeper 1",
                "home_score": 1,
                "away_score": 0,
            }
        ],
    )
    assert len(report["goals"]) == 1
    assert report["goals"][0]["is_penalty"] is True
    assert report["goals"][0]["scorer_name"] == "Striker 9"
    assert report["goals"][0]["assist_name"] is None
    assert report["stats"]["home_assists"] == 0
