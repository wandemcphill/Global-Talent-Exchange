from __future__ import annotations

from backend.app.club_identity.models.dynasty_models import EraLabel


def test_dynasty_api_exposes_profile_history_eras_and_leaderboard(api_client) -> None:
    profile_response = api_client.get("/api/clubs/club-global/dynasty")
    assert profile_response.status_code == 200
    profile_payload = profile_response.json()
    assert profile_payload["current_era_label"] == EraLabel.GLOBAL_DYNASTY
    assert profile_payload["active_dynasty_flag"] is True
    assert len(profile_payload["last_four_season_summary"]) == 4

    history_response = api_client.get("/api/clubs/club-fall/dynasty/history")
    assert history_response.status_code == 200
    history_payload = history_response.json()
    assert any(snapshot["era_label"] == EraLabel.FALLEN_GIANT for snapshot in history_payload["dynasty_timeline"])
    assert history_payload["events"]

    eras_response = api_client.get("/api/clubs/club-cont/eras")
    assert eras_response.status_code == 200
    eras_payload = eras_response.json()
    assert any(era["era_label"] == EraLabel.CONTINENTAL_DYNASTY for era in eras_payload)

    leaderboard_response = api_client.get("/api/leaderboards/dynasties?limit=3")
    assert leaderboard_response.status_code == 200
    leaderboard_payload = leaderboard_response.json()
    assert leaderboard_payload[0]["club_id"] == "club-global"
    assert leaderboard_payload[0]["current_era_label"] == EraLabel.GLOBAL_DYNASTY
    assert any(entry["current_era_label"] == EraLabel.FALLEN_GIANT for entry in leaderboard_payload)
