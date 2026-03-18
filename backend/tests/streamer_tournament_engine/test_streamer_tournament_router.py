from __future__ import annotations


def _create_fan_qualifier(api_client, *, methods: list[str], top_gifter_rank_limit: int | None = None, playoff_source_competition_id: str | None = None):
    response = api_client.post(
        "/streamer-tournaments",
        json={
            "title": "Fan Gauntlet",
            "tournament_type": "fan_qualifier",
            "season_id": "season-1",
            "playoff_source_competition_id": playoff_source_competition_id,
            "qualification_methods": methods,
            "top_gifter_rank_limit": top_gifter_rank_limit,
            "max_participants": 16,
            "rewards": [
                {
                    "title": "Qualifier Reward",
                    "reward_type": "fan_coin",
                    "placement_start": 1,
                    "placement_end": 1,
                    "amount": "50.0000",
                }
            ],
        },
    )
    assert response.status_code == 201, response.text
    tournament = response.json()
    publish = api_client.post(
        f"/streamer-tournaments/{tournament['id']}/publish",
        json={"submission_notes": "publish"},
    )
    assert publish.status_code == 200, publish.text
    return publish.json()


def test_fan_can_join_via_season_pass(api_client) -> None:
    api_client.app.state.current_user_id = "creator-user"
    tournament = _create_fan_qualifier(api_client, methods=["season_pass"])

    api_client.app.state.current_user_id = "season-fan"
    response = api_client.post(
        f"/streamer-tournaments/{tournament['id']}/join",
        json={},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    entry = next(item for item in payload["entries"] if item["user_id"] == "season-fan")
    assert entry["qualification_source"] == "season_pass"


def test_fans_can_join_via_top_gifter_and_playoffs(api_client) -> None:
    api_client.app.state.current_user_id = "creator-user"
    tournament = _create_fan_qualifier(
        api_client,
        methods=["top_gifter", "playoffs"],
        top_gifter_rank_limit=1,
        playoff_source_competition_id="competition-1",
    )

    api_client.app.state.current_user_id = "gifter-fan"
    gifter_join = api_client.post(
        f"/streamer-tournaments/{tournament['id']}/join",
        json={"qualification_source_hint": "top_gifter"},
    )
    assert gifter_join.status_code == 200, gifter_join.text
    gifter_entry = next(item for item in gifter_join.json()["entries"] if item["user_id"] == "gifter-fan")
    assert gifter_entry["qualification_source"] == "top_gifter"

    api_client.app.state.current_user_id = "playoff-fan"
    playoff_join = api_client.post(
        f"/streamer-tournaments/{tournament['id']}/join",
        json={"qualification_source_hint": "playoffs"},
    )
    assert playoff_join.status_code == 200, playoff_join.text
    playoff_entry = next(item for item in playoff_join.json()["entries"] if item["user_id"] == "playoff-fan")
    assert playoff_entry["qualification_source"] == "playoffs"

