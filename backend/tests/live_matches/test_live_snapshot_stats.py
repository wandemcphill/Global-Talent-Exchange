from types import SimpleNamespace

from app.live_matches.router import _possession_from_frames, _v2_stats_payload


def _event(event_type: str, team_id: str, minute: int, xg: float = 0.1):
    return SimpleNamespace(event_type=event_type, team_id=team_id, minute=minute, metadata={"xg": xg})


def test_shots_and_cards_stay_cumulative_after_the_commentary_window() -> None:
    frame = SimpleNamespace(
        players=[SimpleNamespace(side="home", team_id="home")],
        home_score=2,
        away_score=1,
    )
    events = [_event("shot", "home" if index % 2 == 0 else "away", index) for index in range(45)]
    events.append(_event("yellow_card", "home", 12, xg=0))
    events.append(_event("red_card", "away", 44, xg=0))
    stats = _v2_stats_payload(frame, events, frames=[])
    assert stats["home_shots"] == 23
    assert stats["away_shots"] == 22
    assert stats["home_shots"] + stats["away_shots"] > 40
    assert stats["home_yellow_cards"] == 1
    assert stats["away_red_cards"] == 1
    assert stats["home_pass_accuracy"] is None
    assert stats["home_expected_threat"] is None
    assert stats["home_ppda"] is None


def test_possession_matches_the_share_of_frame_sides() -> None:
    frames = [SimpleNamespace(possession_side="home")] * 3 + [SimpleNamespace(possession_side="away")]
    assert _possession_from_frames(frames) == (75, 25)
