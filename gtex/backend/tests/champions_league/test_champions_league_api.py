from __future__ import annotations

def test_champions_league_api_surfaces_qualification_knockout_and_prize_views(
    api_client,
    build_candidates,
    build_league_clubs,
    build_standings_rows,
) -> None:
    qualification_response = api_client.post(
        "/champions-league/qualification-map",
        json={"clubs": [_candidate_payload(club) for club in build_candidates()]},
    )
    assert qualification_response.status_code == 200
    qualification_payload = qualification_response.json()
    assert len(qualification_payload["direct_qualifiers"]) == 24
    assert len(qualification_payload["playoff_qualifiers"]) == 24

    playoff_response = api_client.post(
        "/champions-league/playoff-bracket",
        json={"clubs": [_candidate_payload(club) for club in build_candidates()]},
    )
    assert playoff_response.status_code == 200
    playoff_payload = playoff_response.json()
    assert len(playoff_payload["ties"]) == 12
    assert len(playoff_payload["advancing_clubs"]) == 36

    league_response = api_client.post(
        "/champions-league/league-phase/table",
        json={
            "clubs": [_club_seed_payload(club) for club in build_league_clubs()],
            "matches": [],
        },
    )
    assert league_response.status_code == 200
    league_payload = league_response.json()
    assert len(league_payload["rows"]) == 36
    assert league_payload["rows"][0]["advancement_status"] == "round_of_16"

    knockout_response = api_client.post(
        "/champions-league/knockout-bracket",
        json={
            "standings": [_standing_payload(row) for row in build_standings_rows()],
        },
    )
    assert knockout_response.status_code == 200
    knockout_payload = knockout_response.json()
    assert len(knockout_payload["knockout_playoff"]) == 8
    assert knockout_payload["final"]["presentation_max_minutes"] == 10

    prize_response = api_client.post(
        "/champions-league/prize-pool/preview",
        json={
            "season_id": "ucl-2026",
            "league_leftover_allocation": "1000",
            "champion_club_id": "club-01",
            "champion_club_name": "Club 01",
            "currency": "credit",
        },
    )
    assert prize_response.status_code == 200
    prize_payload = prize_response.json()
    assert prize_payload["funded_pool"] == "350.0000"
    assert prize_payload["champion_share"] == "245.0000"
    assert prize_payload["platform_share"] == "105.0000"


def _candidate_payload(club) -> dict[str, object]:
    return {
        "club_id": club.club_id,
        "club_name": club.club_name,
        "region": club.region,
        "tier": club.tier,
        "ranking_points": club.ranking_points,
        "domestic_rank": club.domestic_rank,
    }


def _club_seed_payload(club) -> dict[str, object]:
    return {
        "club_id": club.club_id,
        "club_name": club.club_name,
        "seed": club.seed,
        "region": club.region,
        "tier": club.tier,
    }


def _standing_payload(row) -> dict[str, object]:
    return {
        "club_id": row.club_id,
        "club_name": row.club_name,
        "seed": row.seed,
        "played": row.played,
        "wins": row.wins,
        "draws": row.draws,
        "losses": row.losses,
        "goals_for": row.goals_for,
        "goals_against": row.goals_against,
        "goal_difference": row.goal_difference,
        "points": row.points,
        "rank": row.rank,
        "advancement_status": row.advancement_status.value,
    }
