"""The match eleven is the filed first-team sheet, with a goalkeeper and a reserve bench."""

from app.owner_console.engine import club_strength


def _player(pid: str, position: str, rating: int, sheet: str) -> dict:
    return {
        "id": pid,
        "position": position,
        "rating": rating,
        "morale": 70,
        "fitness": 90,
        "age": 17 if sheet == "academy" else 26,
        "injured_days": 0,
        "minutes": 0 if sheet == "academy" else 100,
        "is_regen": sheet == "academy",
        "squad_status": sheet,
    }


def test_match_xi_comes_from_the_first_team_sheet_and_keeps_a_goalkeeper():
    players = [
        _player("gk", "goalkeeper", 70, "first_team"),
        *[_player(f"ft-{index}", "midfielder", 80 - index, "first_team") for index in range(10)],
        _player("wonder", "forward", 99, "academy"),
        _player("res-1", "defender", 60, "reserve"),
    ]
    result = club_strength(players, {}, {})
    assert "gk" in result["xi"]
    assert "wonder" not in result["xi"]
    assert "wonder" not in result["bench"]
    assert result["bench"][0] == "res-1"
    assert len(result["xi"]) == 11


def test_a_promised_academy_player_stays_in_the_matchday_squad():
    players = [
        _player("gk", "goalkeeper", 70, "first_team"),
        *[_player(f"ft-{index}", "midfielder", 80 - index, "first_team") for index in range(10)],
        _player("wonder", "forward", 99, "academy"),
    ]
    facilities = {
        "_last_manager_matchday_selection": {"starting_xi_ids": ["wonder"]},
        "_manager_matchday_commitments": {"wonder": {"matchday_role": "starting_xi"}},
    }
    starting = club_strength(players, {}, facilities)
    assert "wonder" in starting["xi"]

    benched = club_strength(
        players,
        {},
        {"_manager_matchday_commitments": {"wonder": {"matchday_role": "matchday_squad_bench"}}},
    )
    assert "wonder" not in benched["xi"]
    assert "wonder" in benched["bench"]


def test_filed_eleven_is_the_eleven_that_plays():
    players = [
        _player("gk", "goalkeeper", 70, "first_team"),
        *[_player(f"ft-{index}", "midfielder", 80, "first_team") for index in range(12)],
    ]
    filed = ["gk", *[f"ft-{index}" for index in range(10)]]
    result = club_strength(players, {}, {"_last_manager_matchday_selection": {"starting_xi_ids": filed}})
    assert result["xi"] == filed
