from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_session
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.competition_round import CompetitionRound
from app.models.national_team import NationalTeamCompetition
from app.models.regen_ecosystem import NationalRegenSeed
from app.regen_universe.router import router
from tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def _seed_national_award_match(
    session,
    *,
    owner_user_id: str,
    suffix: str,
    title: str,
    key: str,
    age_band: str,
    region_type: str,
    subject_key: str,
    when: date,
) -> None:
    competition = UserCompetition(
        id=f"user-competition-{suffix}",
        host_user_id=owner_user_id,
        name=title,
        format="cup",
        currency="COIN",
        source_type="national_team",
        source_id=f"national-{suffix}",
    )
    national_competition = NationalTeamCompetition(
        id=f"national-competition-{suffix}",
        key=key,
        title=title,
        season_label="2025/2026",
        region_type=region_type,
        age_band=age_band,
        format_type="cup",
        status="completed",
        linked_competition_id=competition.id,
        kickoff_at=datetime(when.year, when.month, when.day, 12, 0, tzinfo=timezone.utc),
        completed_at=datetime(when.year, when.month, when.day, 18, 0, tzinfo=timezone.utc),
        metadata_json={},
    )
    round_ = CompetitionRound(
        id=f"competition-round-{suffix}",
        competition_id=competition.id,
        round_number=1,
        stage="final",
        name="Final",
        status="completed",
    )
    match = CompetitionMatch(
        id=f"competition-match-{suffix}",
        competition_id=competition.id,
        round_id=round_.id,
        round_number=1,
        stage="final",
        home_club_id=f"home-{suffix}",
        away_club_id=f"away-{suffix}",
        status="completed",
        match_date=when,
        winner_club_id=f"home-{suffix}",
        completed_at=datetime(when.year, when.month, when.day, 18, 0, tzinfo=timezone.utc),
        metadata_json={
            "player_performances": [
                {
                    "subject_key": subject_key,
                    "appearances": 3,
                    "starts": 3,
                    "minutes": 270,
                    "goals": 3 if age_band != "senior" else 2,
                    "assists": 2,
                    "rating": 8.8 if age_band == "u17" else 8.6 if age_band == "u20" else 8.4,
                    "won_match": True,
                    "won_tournament": True,
                }
            ]
        },
    )
    session.add_all([competition, national_competition, round_, match])
    session.flush()


def test_close_season_computes_requested_awards_and_seed_timelines() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        service = bundle["service"]
        active_season = service.list_seasons(active_only=True)[0]

        u17_seed = NationalRegenSeed(
            seed_key="seed:phase6:u17",
            display_name="Ifeanyi Okoro",
            age=16,
            age_band="u17",
            country_code="NG",
            country_name="Nigeria",
            seed_type="preseeded_national_pool",
            primary_position="ST",
            current_rating=76,
            potential_rating=90,
            growth_curve=0.84,
            rarity_tier="elite",
            status="active",
            metadata_json={"age": 16},
        )
        u20_seed = NationalRegenSeed(
            seed_key="seed:phase6:u20",
            display_name="Tari Mensah",
            age=19,
            age_band="u20",
            country_code="GH",
            country_name="Ghana",
            seed_type="preseeded_national_pool",
            primary_position="AM",
            current_rating=78,
            potential_rating=91,
            growth_curve=0.81,
            rarity_tier="elite",
            status="active",
            metadata_json={"age": 19},
        )
        senior_seed = NationalRegenSeed(
            seed_key="seed:phase6:afcon",
            display_name="Cheikh Ndao",
            age=24,
            age_band="senior",
            country_code="SN",
            country_name="Senegal",
            seed_type="preseeded_national_pool",
            primary_position="LW",
            current_rating=80,
            potential_rating=90,
            growth_curve=0.76,
            rarity_tier="elite",
            status="active",
            metadata_json={"age": 24},
        )
        session.add_all([u17_seed, u20_seed, senior_seed])
        session.flush()

        _seed_national_award_match(
            session,
            owner_user_id="user-owner",
            suffix="u17",
            title="GTEX U17 World Cup",
            key="gtex-u17-world-cup",
            age_band="u17",
            region_type="global",
            subject_key=f"seed:{u17_seed.id}",
            when=date(2026, 5, 8),
        )
        _seed_national_award_match(
            session,
            owner_user_id="user-owner",
            suffix="u20",
            title="GTEX U20 World Cup",
            key="gtex-u20-world-cup",
            age_band="u20",
            region_type="global",
            subject_key=f"seed:{u20_seed.id}",
            when=date(2026, 5, 12),
        )
        _seed_national_award_match(
            session,
            owner_user_id="user-owner",
            suffix="afcon",
            title="GTEX AFCON",
            key="gtex-afcon",
            age_band="senior",
            region_type="africa",
            subject_key=f"seed:{senior_seed.id}",
            when=date(2026, 5, 15),
        )

        session.flush()
        service.close_season(active_season.id, start_next_season=False)

        awards = {item["award"]["code"]: item for item in service.list_awards(season_id=active_season.id)}
        assert awards["BALLON_DOR"]["award"]["name"] == "GTEX World Player of the Year"
        assert awards["GOLDEN_BOY"]["award"]["name"] == "GTEX Young Player of the Year"
        assert awards["BEST_GOALKEEPER"]["award"]["name"] == "GTEX Golden Glove"
        assert awards["BREAKOUT_STAR"]["award"]["name"] == "GTEX Breakout Regen"
        assert awards["TEAM_OF_THE_YEAR"]["award"]["name"] == "GTEX Team of the Year"
        assert awards["U17_WORLD_CUP_GOLDEN_BALL"]["winners"][0]["player_id"] == f"seed:{u17_seed.id}"
        assert awards["U20_WORLD_CUP_GOLDEN_BALL"]["winners"][0]["player_id"] == f"seed:{u20_seed.id}"
        assert awards["AFCON_PLAYER_OF_THE_TOURNAMENT"]["winners"][0]["player_id"] == f"seed:{senior_seed.id}"

        seed_lookup = service.get_player_lookup(f"seed:{u17_seed.id}")
        assert seed_lookup is not None
        assert any(item["event_type"] == "national_team_callup" for item in seed_lookup["timeline"])
        assert any(item["event_type"] == "award_won" for item in seed_lookup["timeline"])
        assert any(item["achievement_type"] == "tournament_winner" for item in seed_lookup["achievements"])
    finally:
        session.close()


def test_public_regen_endpoints_surface_timeline_achievements_and_award_feed() -> None:
    session = build_regen_universe_session()
    try:
        bundle = seed_two_season_universe(session)
        service = bundle["service"]
        active_season = service.list_seasons(active_only=True)[0]
        service.close_season(active_season.id, start_next_season=False)

        world_player = next(
            item["winners"][0]["player_id"]
            for item in service.list_awards(season_id=active_season.id)
            if item["award"]["code"] == "BALLON_DOR" and item["winners"]
        )

        showcase = service.get_player_showcase(world_player)
        feed = service.list_scouting_feed(limit=40)

        assert showcase is not None
        assert showcase["prestige"] is not None
        assert showcase["prestige"]["recent_awards"]
        assert any(item["event_type"] == "award_won" for item in showcase["timeline"])
        assert any(item["achievement_type"] == "award_won" for item in showcase["achievements"])
        assert any(item["feed_type"] == "award_won" and item["player_id"] == world_player for item in feed["items"])

        app = FastAPI()
        app.include_router(router)

        def _session_override():
            yield session

        app.dependency_overrides[get_session] = _session_override

        with TestClient(app) as client:
            timeline_response = client.get(f"/regen-universe/players/{world_player}/timeline")
            achievements_response = client.get("/regen-universe/achievements", params={"player_id": world_player})
            awards_response = client.get("/regen-universe/awards", params={"season_id": active_season.id})

        assert timeline_response.status_code == 200, timeline_response.text
        assert achievements_response.status_code == 200, achievements_response.text
        assert awards_response.status_code == 200, awards_response.text
        assert any(item["event_type"] == "award_won" for item in timeline_response.json()["items"])
        assert any(item["achievement_type"] == "award_won" for item in achievements_response.json()["items"])
        assert any(item["award"]["name"] == "GTEX World Player of the Year" for item in awards_response.json()["items"])
    finally:
        session.close()
