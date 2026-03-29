from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select

from app.ingestion.models import Competition, Club, Country, InternalLeague, Match, Player, Season, TeamStanding
from app.models.manager_marketplace import ManagerProfile
from app.models.national_team import NationalTeamCompetition, NationalTeamEntry
from app.models.user import User
from app.regen_universe.models import RegenPerformanceRecord, RegenSeason
from app.regen_universe.service import RegenUniverseService


def _seed_awards_storyline(session_factory) -> str:
    with session_factory() as session:
        for item in session.scalars(select(RegenSeason).where(RegenSeason.is_active.is_(True))).all():
            item.is_active = False

        service = RegenUniverseService(session)
        service.seed_defaults()

        country = Country(
            id="awards-country-ng",
            source_provider="test",
            provider_external_id="awards-country-ng",
            name="Nigeria",
            alpha2_code="NG",
            alpha3_code="NGA",
            fifa_code="NGA",
            confederation_code="CAF",
            market_region="africa",
            is_enabled_for_universe=True,
        )
        league = InternalLeague(
            id="awards-league-top",
            code="AGT",
            name="Awards League",
            rank=91,
            competition_multiplier=1.25,
            visibility_weight=1.15,
        )
        competition = Competition(
            id="awards-competition-top",
            source_provider="test",
            provider_external_id="awards-competition-top",
            country_id=country.id,
            internal_league_id=league.id,
            name="Awards Premier",
            slug="awards-premier",
            code="APR",
            competition_strength=88.0,
        )
        source_season = Season(
            id="awards-source-season",
            source_provider="test",
            provider_external_id="awards-source-season",
            competition_id=competition.id,
            label="2026/2027",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 5, 31),
            is_current=True,
        )
        club_winner = Club(
            id="awards-club-winner",
            source_provider="test",
            provider_external_id="awards-club-winner",
            country_id=country.id,
            current_competition_id=competition.id,
            internal_league_id=league.id,
            name="Lagos Crown",
            slug="lagos-crown",
            short_name="LCR",
            code="LCR",
        )
        club_runner_up = Club(
            id="awards-club-runner-up",
            source_provider="test",
            provider_external_id="awards-club-runner-up",
            country_id=country.id,
            current_competition_id=competition.id,
            internal_league_id=league.id,
            name="Abuja Comets",
            slug="abuja-comets",
            short_name="ABC",
            code="ABC",
        )
        manager_user = User(
            id="awards-manager-user",
            email="awards-manager@example.com",
            username="awards-manager",
            password_hash="hashed",
            full_name="Nia Solace",
        )
        manager_profile = ManagerProfile(
            id="awards-manager-profile",
            manager_id=manager_user.id,
            name="Nia Solace",
            matches_managed=38,
            wins=29,
            losses=4,
            reputation_score=1480,
            current_losing_streak=0,
            formation_preferences_json=["4-3-3"],
        )
        national_competition = NationalTeamCompetition(
            id="awards-national-competition",
            key="awards-cup-2027",
            title="Awards Nations Cup",
            season_label="2027",
            status="completed",
            active=True,
        )
        national_entry = NationalTeamEntry(
            id="awards-national-entry-ng",
            competition_id=national_competition.id,
            country_code="NG",
            country_name="Nigeria",
            squad_size=26,
            metadata_json={
                "wins": 6,
                "trophies": 1,
                "win_ratio": 0.857,
                "big_match_impact": 2.5,
                "performance_score": 42.0,
            },
        )
        regen_season = RegenSeason(
            id="awards-regen-season",
            season_number=9201,
            start_date=date(2026, 8, 1),
            end_date=date(2027, 5, 31),
            is_active=True,
            metadata_json={"source_ingestion_season_ids": [source_season.id]},
        )

        session.add_all(
            [
                country,
                league,
                competition,
                source_season,
                club_winner,
                club_runner_up,
                manager_user,
                manager_profile,
                national_competition,
                national_entry,
                regen_season,
            ]
        )
        session.add(
            Match(
                id="awards-final-match",
                source_provider="test",
                provider_external_id="awards-final-match",
                competition_id=competition.id,
                season_id=source_season.id,
                home_club_id=club_winner.id,
                away_club_id=club_runner_up.id,
                winner_club_id=club_winner.id,
                kickoff_at=datetime(2027, 5, 28, 19, 0, tzinfo=timezone.utc),
                status="completed",
                stage="final",
                home_score=3,
                away_score=1,
            )
        )
        session.add(
            TeamStanding(
                id="awards-standing-winner",
                source_provider="test",
                provider_external_id="awards-standing-winner",
                competition_id=competition.id,
                season_id=source_season.id,
                club_id=club_winner.id,
                standing_type="total",
                position=1,
                played=38,
                won=29,
                drawn=5,
                lost=4,
                goals_for=86,
                goals_against=29,
                goal_difference=57,
                points=92,
            )
        )

        profiles = [
            ("Ayo Star", "forward", 95.0, 92.0, 36, 18, 0.92, 33, 23),
            ("Kemi Blaze", "forward", 90.0, 84.0, 34, 14, 0.86, 21, 21),
            ("Musa Orbit", "midfielder", 88.0, 90.0, 35, 16, 0.88, 10, 24),
            ("Tariq Pulse", "midfielder", 84.0, 82.0, 33, 11, 0.84, 8, 18),
            ("Ife Shield", "defender", 83.0, 74.0, 36, 5, 0.89, 2, 4),
            ("Dara Wall", "defender", 81.0, 72.0, 34, 4, 0.84, 1, 3),
            ("Sade Reflex", "goalkeeper", 80.0, 58.0, 35, 2, 0.85, 0, 1),
            ("Lami Echo", "forward", 79.0, 77.0, 31, 8, 0.78, 18, 12),
            ("Tobi Current", "midfielder", 78.0, 76.0, 30, 9, 0.8, 7, 14),
            ("Mina Crest", "forward", 77.0, 75.0, 29, 6, 0.76, 15, 9),
            ("Uche Axis", "defender", 76.0, 68.0, 31, 3, 0.77, 1, 2),
            ("Zuri Tide", "midfielder", 75.0, 74.0, 28, 7, 0.74, 5, 12),
        ]
        for index, (name, position_group, overall, specialist, consistency, trophies, win_ratio, goals, assists) in enumerate(
            profiles,
            start=1,
        ):
            player = Player(
                id=f"awards-player-{index}",
                source_provider="test",
                provider_external_id=f"awards-player-{index}",
                full_name=name,
                normalized_position=position_group,
                position={
                    "forward": "ST",
                    "midfielder": "CM",
                    "defender": "CB",
                    "goalkeeper": "GK",
                }[position_group],
                date_of_birth=date(2007, 1, 1) if index == 2 else date(2001, 1, 1),
                is_real_player=False,
                country_id=country.id,
                current_club_id=club_winner.id if index % 2 else club_runner_up.id,
                current_competition_id=competition.id,
                internal_league_id=league.id,
            )
            session.add(player)
            session.add(
                RegenPerformanceRecord(
                    id=f"awards-record-{index}",
                    season_id=regen_season.id,
                    player_id=player.id,
                    player_name=name,
                    age=19 if index == 2 else 24 + (index % 5),
                    position_group=position_group,
                    appearances=34,
                    starts=32,
                    minutes_played=2800,
                    goals=goals,
                    assists=assists,
                    clean_sheets=16 if position_group in {"defender", "goalkeeper"} else 0,
                    saves=84 if position_group == "goalkeeper" else 0,
                    average_rating=7.6 + (index * 0.03),
                    matches_won=25,
                    win_ratio=win_ratio,
                    competition_importance=1.2,
                    consistency_score=consistency / 100.0,
                    overall_score=overall,
                    midfielder_score=specialist if position_group == "midfielder" else 0.0,
                    defender_score=specialist if position_group == "defender" else 0.0,
                    goalkeeper_score=specialist if position_group == "goalkeeper" else 0.0,
                    scorer_score=specialist if position_group == "forward" else 0.0,
                    forward_score=specialist if position_group == "forward" else 0.0,
                    playmaker_score=assists * 2.2,
                    improvement_score=6.0 + index,
                    metadata_json={
                        "trophy_points": trophies / 10.0,
                        "big_match_impact": 1.4 if index <= 4 else 0.5,
                    },
                )
            )

        session.commit()
        return regen_season.id


def test_awards_routes_return_shortlists_winners_and_tv_ceremony(client, app_session_factory) -> None:
    season_id = _seed_awards_storyline(app_session_factory)

    categories_response = client.get("/awards/categories")
    nominees_response = client.get("/awards/nominees", params={"season_id": season_id})
    winners_response = client.get("/awards/winners", params={"season_id": season_id})
    ceremony_response = client.get("/awards/ceremony", params={"season_id": season_id})

    assert categories_response.status_code == 200
    assert nominees_response.status_code == 200
    assert winners_response.status_code == 200
    assert ceremony_response.status_code == 200

    categories = categories_response.json()
    nominees = nominees_response.json()
    winners = winners_response.json()
    ceremony = ceremony_response.json()

    assert any(item["award_name"] == "GTEX Ballon d'Or" for item in categories)
    assert any(bucket["award_code"] == "BEST_MANAGER" for bucket in nominees)
    ballon_bucket = next(item for item in nominees if item["award_code"] == "BALLON_DOR")
    assert [stage["stage_label"] for stage in ballon_bucket["stages"]] == ["Top 30", "Top 10", "Final 3"]
    assert ballon_bucket["stages"][-1]["nominees"][0]["display_name"] == "Ayo Star"

    club_bucket = next(item for item in winners if item["award_code"] == "CLUB_OF_THE_YEAR")
    assert club_bucket["winners"][0]["display_name"] == "Lagos Crown"

    assert ceremony["broadcast_mode"] == "tv"
    assert ceremony["validation"]["ranking_consistency"] is True
    assert ceremony["segments"]
    assert ceremony["segments"][0]["winners"]
