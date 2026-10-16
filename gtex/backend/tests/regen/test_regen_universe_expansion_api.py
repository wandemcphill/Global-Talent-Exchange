from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, select

from app.auth.service import AuthService
from app.ingestion.models import Club, Competition, InternalLeague, Match, Player, PlayerMatchStat, Season
from app.main import create_app
from app.models.club_profile import ClubProfile
from app.models.notification_record import NotificationRecord
from app.models.player_cards import PlayerCard, PlayerCardTier
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_lifecycle_event import PlayerLifecycleEvent
from app.models.player_story import PlayerStory
from app.models.regen import RegenOriginMetadata, RegenPersonalityProfile, RegenProfile
from app.models.story_feed import StoryFeedItem
from app.models.user import User, UserRole
from app.models.youth_tournament import YouthTournament
from app.regen_universe.expansion_service import RegenUniverseExpansionService


def _wait_for_startup(app) -> None:
    startup_thread = getattr(app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=5)


def _create_authenticated_headers(app, *, email: str, username: str, role: UserRole = UserRole.ADMIN) -> dict[str, str]:
    with app.state.session_factory() as session:
        service = AuthService()
        user = service.register_user(
            session,
            email=email,
            username=username,
            password="SuperSecret1",
            display_name=username,
            role=role,
        )
        token, _ = service.issue_access_token(user, session=session)
        session.commit()
    return {"Authorization": f"Bearer {token}"}


def _create_ingestion_club(session, *, club_id: str, competition_id: str, internal_league_id: str, name: str) -> Club:
    club = Club(
        id=club_id,
        source_provider="test",
        provider_external_id=club_id,
        current_competition_id=competition_id,
        internal_league_id=internal_league_id,
        name=name,
        slug=name.lower().replace(" ", "-"),
        short_name=name[:12],
    )
    session.add(club)
    return club


def _create_regen_player(
    session,
    *,
    prefix: str,
    suffix: str,
    name: str,
    birth_date: date,
    position: str,
    normalized_position: str,
    club_profile_id: str,
    tier_id: str,
) -> Player:
    player = Player(
        id=f"{prefix}-player-{suffix}",
        source_provider="gtex_regen",
        provider_external_id=f"{prefix}-player-{suffix}",
        full_name=name,
        position=position,
        normalized_position=normalized_position,
        date_of_birth=birth_date,
        current_club_profile_id=club_profile_id,
        market_value_eur=8_000_000,
        current_market_reference_value=8_000_000,
        is_real_player=False,
    )
    session.add(player)
    card = PlayerCard(
        id=f"{prefix}-card-{suffix}",
        player_id=player.id,
        tier_id=tier_id,
        edition_code="base",
        display_name=name,
        card_variant="base",
        supply_total=1,
        supply_available=1,
    )
    session.add(card)
    regen_profile = RegenProfile(
        id=f"{prefix}-regen-profile-{suffix}",
        regen_id=f"{prefix}-regen-{suffix}",
        player_id=player.id,
        linked_unique_card_id=card.id,
        generated_for_club_id=club_profile_id,
        birth_country_code="NG",
        birth_region="Lagos",
        birth_city="Lagos",
        primary_position=position,
        secondary_positions_json=[],
        current_gsi=72,
        current_ability_range_json={"minimum": 66, "maximum": 78},
        potential_range_json={"minimum": 80, "maximum": 92},
        scout_confidence="high",
        generation_source="academy",
        metadata_json={},
    )
    session.add(regen_profile)
    session.add(
        RegenPersonalityProfile(
            id=f"{prefix}-personality-{suffix}",
            regen_profile_id=regen_profile.id,
            temperament=56,
            leadership=61,
            ambition=74,
            loyalty=49,
            work_rate=68,
            flair=72 if normalized_position in {"forward", "midfielder"} else 48,
            resilience=66,
            personality_tags_json=["composed", "upside"],
        )
    )
    session.add(
        RegenOriginMetadata(
            id=f"{prefix}-origin-{suffix}",
            regen_profile_id=regen_profile.id,
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            hometown_club_affinity="Prestige FC",
            ethnolinguistic_profile="yoruba",
            religion_naming_pattern="mixed",
            urbanicity="urban",
            metadata_json={},
        )
    )
    return player


def _seed_regen_universe(session, *, prefix: str) -> dict[str, object]:
    owner = User(
        id=f"{prefix}-owner",
        email=f"{prefix}-owner@example.com",
        username=f"{prefix}_owner",
        password_hash="hash",
        full_name="Owner User",
    )
    session.add(owner)
    club_profile = ClubProfile(
        id=f"{prefix}-club-profile-1",
        owner_user_id=owner.id,
        club_name="Prestige FC",
        short_name="PFC",
        slug=f"{prefix}-prestige-fc",
        primary_color="#003366",
        secondary_color="#ffffff",
        accent_color="#ffcc00",
        country_code="NG",
        region_name="Lagos",
        city_name="Lagos",
        visibility="public",
    )
    session.add(club_profile)
    tier = PlayerCardTier(
        id=f"{prefix}-tier",
        code=f"{prefix.upper()}_RARE",
        name=f"{prefix.title()} Rare",
        rarity_rank=900 if prefix == "story" else 901,
    )
    session.add(tier)
    league = InternalLeague(
        id=f"{prefix}-league",
        code=f"{prefix[:8].upper()}L",
        name=f"{prefix.title()} League",
        rank=900 if prefix == "story" else 901,
        competition_multiplier=1.2,
        visibility_weight=1.1,
    )
    competition = Competition(
        id=f"{prefix}-competition",
        source_provider="test",
        provider_external_id=f"{prefix}-competition",
        internal_league_id=league.id,
        name=f"{prefix.title()} Premier League",
        slug=f"{prefix}-premier-league",
        code=f"{prefix[:3].upper()}PL",
        is_major=False,
        competition_strength=82.0,
    )
    season_one = Season(
        id=f"{prefix}-season-1",
        source_provider="test",
        provider_external_id=f"{prefix}-season-1",
        competition_id=competition.id,
        label="2025/2026",
        start_date=date(2025, 8, 1),
        end_date=date(2026, 5, 31),
        is_current=False,
    )
    season_two = Season(
        id=f"{prefix}-season-2",
        source_provider="test",
        provider_external_id=f"{prefix}-season-2",
        competition_id=competition.id,
        label="2026/2027",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 5, 31),
        is_current=True,
    )
    session.add_all([league, competition, season_one, season_two])

    players = {
        "veteran": _create_regen_player(
            session,
            prefix=prefix,
            suffix="veteran",
            name="Victor Veteran",
            birth_date=date(1998, 3, 14),
            position="ST",
            normalized_position="forward",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "wonderkid": _create_regen_player(
            session,
            prefix=prefix,
            suffix="wonderkid",
            name="Kelechi Wonderkid",
            birth_date=date(2006, 4, 10),
            position="ST",
            normalized_position="forward",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "playmaker": _create_regen_player(
            session,
            prefix=prefix,
            suffix="playmaker",
            name="Musa Playmaker",
            birth_date=date(2002, 9, 5),
            position="CM",
            normalized_position="midfielder",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "defender": _create_regen_player(
            session,
            prefix=prefix,
            suffix="defender",
            name="David Defender",
            birth_date=date(2000, 6, 7),
            position="CB",
            normalized_position="defender",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "keeper": _create_regen_player(
            session,
            prefix=prefix,
            suffix="keeper",
            name="Gabriel Gloves",
            birth_date=date(1999, 1, 22),
            position="GK",
            normalized_position="goalkeeper",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
        "breakout": _create_regen_player(
            session,
            prefix=prefix,
            suffix="breakout",
            name="Tunde Breakout",
            birth_date=date(2005, 12, 2),
            position="RW",
            normalized_position="forward",
            club_profile_id=club_profile.id,
            tier_id=tier.id,
        ),
    }
    session.flush()
    return {
        "players": players,
        "owner": owner,
        "club_profile": club_profile,
        "tier": tier,
        "league": league,
        "competition": competition,
        "season_one": season_one,
        "season_two": season_two,
    }


def _seed_rivalry_matches(
    session,
    *,
    competition_id: str,
    season_id: str,
    wonderkid: Player,
    breakout: Player,
    home_club: Club,
    away_club: Club,
) -> None:
    match_rows = [
        {
            "match_id": "match-rivalry-1",
            "kickoff_at": datetime(2026, 2, 1, 15, 0, tzinfo=timezone.utc),
            "home_club_id": home_club.id,
            "away_club_id": away_club.id,
            "home_score": 2,
            "away_score": 1,
            "wonderkid_rating": 8.4,
            "breakout_rating": 8.1,
            "wonderkid_goals": 1,
            "breakout_goals": 1,
        },
        {
            "match_id": "match-rivalry-2",
            "kickoff_at": datetime(2026, 2, 18, 18, 0, tzinfo=timezone.utc),
            "home_club_id": away_club.id,
            "away_club_id": home_club.id,
            "home_score": 2,
            "away_score": 2,
            "wonderkid_rating": 8.0,
            "breakout_rating": 8.3,
            "wonderkid_goals": 1,
            "breakout_goals": 1,
        },
        {
            "match_id": "match-rivalry-3",
            "kickoff_at": datetime(2026, 3, 3, 20, 0, tzinfo=timezone.utc),
            "home_club_id": home_club.id,
            "away_club_id": away_club.id,
            "home_score": 3,
            "away_score": 2,
            "wonderkid_rating": 8.7,
            "breakout_rating": 8.2,
            "wonderkid_goals": 2,
            "breakout_goals": 1,
        },
    ]
    for row in match_rows:
        session.add(
            Match(
                id=row["match_id"],
                source_provider="test",
                provider_external_id=row["match_id"],
                competition_id=competition_id,
                season_id=season_id,
                home_club_id=row["home_club_id"],
                away_club_id=row["away_club_id"],
                kickoff_at=row["kickoff_at"],
                status="completed",
                stage="league",
                home_score=row["home_score"],
                away_score=row["away_score"],
            )
        )
        session.add(
            PlayerMatchStat(
                id=f"stat-{row['match_id']}-wonderkid",
                source_provider="test",
                provider_external_id=f"{row['match_id']}-wonderkid",
                player_id=wonderkid.id,
                match_id=row["match_id"],
                club_id=home_club.id,
                competition_id=competition_id,
                season_id=season_id,
                appearances=1,
                starts=1,
                minutes=90,
                goals=row["wonderkid_goals"],
                assists=1,
                rating=row["wonderkid_rating"],
                raw_position="ST",
            )
        )
        session.add(
            PlayerMatchStat(
                id=f"stat-{row['match_id']}-breakout",
                source_provider="test",
                provider_external_id=f"{row['match_id']}-breakout",
                player_id=breakout.id,
                match_id=row["match_id"],
                club_id=away_club.id,
                competition_id=competition_id,
                season_id=season_id,
                appearances=1,
                starts=1,
                minutes=90,
                goals=row["breakout_goals"],
                assists=0,
                rating=row["breakout_rating"],
                raw_position="RW",
            )
        )


@pytest.fixture()
def app_client(tmp_path):
    database_url = f"sqlite+pysqlite:///{(tmp_path / 'regen_universe_expansion.db').as_posix()}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    app = create_app(engine=engine, run_migration_check=True)
    with TestClient(app) as client:
        _wait_for_startup(app)
        yield app, client


def test_player_story_dna_and_rivalries_routes(app_client) -> None:
    app, client = app_client

    with app.state.session_factory() as session:
        bundle = _seed_regen_universe(session, prefix="story")
        club_profile = bundle["club_profile"]
        competition = bundle["competition"]
        season = bundle["season_two"]
        wonderkid = bundle["players"]["wonderkid"]
        breakout = bundle["players"]["breakout"]

        rival_club_profile = ClubProfile(
            id="story-club-profile-rival",
            owner_user_id=bundle["owner"].id,
            club_name="Harbor Rovers",
            short_name="HRV",
            slug="story-harbor-rovers",
            primary_color="#5a1f1f",
            secondary_color="#f7f0e4",
            accent_color="#e9a53b",
            country_code="GH",
            region_name="Accra",
            city_name="Accra",
            visibility="public",
        )
        session.add(rival_club_profile)

        home_club = _create_ingestion_club(
            session,
            club_id="ingestion-prestige",
            competition_id=competition.id,
            internal_league_id=competition.internal_league_id,
            name="Prestige FC",
        )
        away_club = _create_ingestion_club(
            session,
            club_id="ingestion-harbor",
            competition_id=competition.id,
            internal_league_id=competition.internal_league_id,
            name="Harbor Rovers",
        )

        wonderkid.current_club_profile_id = club_profile.id
        wonderkid.current_club_id = home_club.id
        wonderkid.market_value_eur = 24_000_000
        wonderkid.current_market_reference_value = 24_000_000
        breakout.current_club_profile_id = rival_club_profile.id
        breakout.current_club_id = away_club.id
        breakout.market_value_eur = 18_000_000
        breakout.current_market_reference_value = 18_000_000

        session.add_all(
            [
                PlayerCareerEntry(
                    id="career-wonderkid-1",
                    player_id=wonderkid.id,
                    club_id=club_profile.id,
                    club_name=club_profile.club_name,
                    season_label="2025/2026",
                    squad_role="rotation",
                    appearances=25,
                    goals=17,
                    assists=8,
                    average_rating=7,
                    honours_json=[],
                    start_on=date(2025, 8, 1),
                    end_on=date(2026, 5, 31),
                ),
                PlayerCareerEntry(
                    id="career-wonderkid-2",
                    player_id=wonderkid.id,
                    club_id=club_profile.id,
                    club_name=club_profile.club_name,
                    season_label="2026/2027",
                    squad_role="star",
                    appearances=31,
                    goals=24,
                    assists=13,
                    average_rating=8,
                    honours_json=[{"name": "Continental Shield"}],
                    start_on=date(2026, 8, 1),
                    end_on=date(2027, 5, 31),
                ),
                PlayerLifecycleEvent(
                    id="lifecycle-wonderkid-1",
                    player_id=wonderkid.id,
                    club_id=club_profile.id,
                    event_type="starter_bootstrap",
                    occurred_on=date(2025, 8, 5),
                    summary="Won a first-team role during the opening bootstrap phase.",
                    details_json={"source": "test"},
                ),
                PlayerLifecycleEvent(
                    id="lifecycle-wonderkid-2",
                    player_id=wonderkid.id,
                    club_id=club_profile.id,
                    event_type="transfer_completed",
                    occurred_on=date(2026, 1, 15),
                    summary="A January move reframed the arc and raised expectations immediately.",
                    details_json={"source": "test"},
                ),
            ]
        )
        _seed_rivalry_matches(
            session,
            competition_id=competition.id,
            season_id=season.id,
            wonderkid=wonderkid,
            breakout=breakout,
            home_club=home_club,
            away_club=away_club,
        )

        session.flush()
        service = RegenUniverseExpansionService(session)
        rivalry_result = service.detect_rivalries(player_id=wonderkid.id)
        session.commit()

    assert rivalry_result["rivalries_updated"] >= 1

    story_response = client.get(f"/players/{wonderkid.id}/story")
    assert story_response.status_code == 200, story_response.text
    story_payload = story_response.json()
    assert {chapter["title"] for chapter in story_payload["chapters"]} >= {
        "Origin Story",
        "Breakout Moment",
        "Career Turning Point",
        "Peak Era",
        "Legacy Reflection",
        "Defining Rivalry Chapter",
    }
    assert story_payload["narrative_score"] >= 70
    assert len(story_payload["key_matches"]) >= 3
    assert any(moment["event_type"] == "rivalry_peak" for moment in story_payload["timeline_narrative"])

    dna_response = client.get(f"/players/{wonderkid.id}/dna")
    assert dna_response.status_code == 200, dna_response.text
    dna_payload = dna_response.json()
    assert dna_payload["archetype"] in {"playmaker", "poacher", "engine", "destroyer"}
    assert set(dna_payload["traits"]) == {"tempo", "risk_taking", "creativity", "discipline"}

    rivalries_response = client.get(f"/players/{wonderkid.id}/rivalries")
    assert rivalries_response.status_code == 200, rivalries_response.text
    rivalries_payload = rivalries_response.json()
    assert rivalries_payload[0]["intensity_score"] >= 70
    assert {player["player_name"] for player in rivalries_payload[0]["players"]} == {
        "Kelechi Wonderkid",
        "Tunde Breakout",
    }

    avatar_response = client.get(f"/players/{wonderkid.id}/avatar")
    assert avatar_response.status_code == 200, avatar_response.text
    avatar_payload = avatar_response.json()
    assert avatar_payload["player_id"] == wonderkid.id
    assert avatar_payload["render_format"] == "json"
    assert avatar_payload["portrait_url"].startswith("http://127.0.0.1:8000/generated-media/")
    assert "/regen_newgen_faces/script_skin_hair/" in avatar_payload["portrait_url"]
    assert avatar_payload["portrait_source_provider"] == "gtex_regen_newgen_face_bank"
    assert avatar_payload["portrait_source_collection"] == "script_skin_tone_hair_colour"
    assert avatar_payload["portrait_status"] == "ready_newgen_face_bank"
    assert avatar_payload["face"] is None
    assert avatar_payload["legacy_avatar"] is None
    assert avatar_payload["layered_svg"] is None
    assert avatar_payload["static_image_data_uri"] is None
    assert avatar_payload["capabilities"] == ["newgen_face_bank_image"]

    avatar_svg_response = client.get(
        f"/players/{wonderkid.id}/avatar",
        params={"format": "svg"},
        follow_redirects=False,
    )
    assert avatar_svg_response.status_code == 307, avatar_svg_response.text
    assert "/regen_newgen_faces/script_skin_hair/" in avatar_svg_response.headers["location"]

    missing_story_response = client.get("/players/nonexistent/story")
    missing_dna_response = client.get("/players/nonexistent/dna")
    missing_rivalries_response = client.get("/players/nonexistent/rivalries")
    missing_avatar_response = client.get("/players/nonexistent/avatar")
    assert missing_story_response.status_code == 404
    assert missing_dna_response.status_code == 404
    assert missing_rivalries_response.status_code == 404
    assert missing_avatar_response.status_code == 404

    with app.state.session_factory() as session:
        story_row = session.scalar(select(PlayerStory).where(PlayerStory.player_id == wonderkid.id))
        wonderkid_row = session.get(Player, wonderkid.id)
        notifications = session.execute(select(NotificationRecord.template_key)).scalars().all()
        feed_items = session.execute(select(StoryFeedItem.story_type)).scalars().all()

    assert story_row is not None
    assert wonderkid_row is not None
    assert wonderkid_row.dna_profile["archetype"] == dna_payload["archetype"]
    assert "RIVALRY_HEATING_UP" in notifications
    assert "documentary" in feed_items


def test_youth_tournament_routes_and_jobs(app_client) -> None:
    app, client = app_client
    admin_headers = _create_authenticated_headers(
        app,
        email="regen-admin@example.com",
        username="regenadmin",
        role=UserRole.SUPER_ADMIN,
    )

    with app.state.session_factory() as session:
        bundle = _seed_regen_universe(session, prefix="tourney")
        players = bundle["players"]
        base_club = bundle["club_profile"]
        competition = bundle["competition"]
        season = bundle["season_two"]

        participant_clubs = [
            base_club,
            ClubProfile(
                id="tourney-club-profile-2",
                owner_user_id=bundle["owner"].id,
                club_name="Coastal Athletic",
                short_name="CAT",
                slug="tourney-coastal-athletic",
                primary_color="#1f4f66",
                secondary_color="#f3f6f8",
                accent_color="#f08a24",
                country_code="SN",
                region_name="Dakar",
                city_name="Dakar",
                visibility="public",
            ),
            ClubProfile(
                id="tourney-club-profile-3",
                owner_user_id=bundle["owner"].id,
                club_name="Savanna Sporting",
                short_name="SVS",
                slug="tourney-savanna-sporting",
                primary_color="#284b2d",
                secondary_color="#faf5ea",
                accent_color="#d6a23a",
                country_code="CI",
                region_name="Abidjan",
                city_name="Abidjan",
                visibility="public",
            ),
            ClubProfile(
                id="tourney-club-profile-4",
                owner_user_id=bundle["owner"].id,
                club_name="Atlas Juniors",
                short_name="ATJ",
                slug="tourney-atlas-juniors",
                primary_color="#3b2a5d",
                secondary_color="#ffffff",
                accent_color="#d84f38",
                country_code="MA",
                region_name="Casablanca",
                city_name="Casablanca",
                visibility="public",
            ),
        ]
        session.add_all(participant_clubs[1:])

        participant_players = [
            players["wonderkid"],
            players["breakout"],
            players["playmaker"],
            players["defender"],
        ]
        for player in players.values():
            player.market_value_eur = float(player.market_value_eur or 8_000_000)
            player.current_market_reference_value = player.market_value_eur
        for index, player in enumerate(participant_players):
            player.current_club_profile_id = participant_clubs[index].id
            player.date_of_birth = date.today() - timedelta(days=(16 + index) * 365)
            player.market_value_eur = float(18_000_000 + (index * 3_000_000))
            player.current_market_reference_value = player.market_value_eur

        home_club = _create_ingestion_club(
            session,
            club_id="ingestion-tourney-home",
            competition_id=competition.id,
            internal_league_id=competition.internal_league_id,
            name="Youth Derby Home",
        )
        away_club = _create_ingestion_club(
            session,
            club_id="ingestion-tourney-away",
            competition_id=competition.id,
            internal_league_id=competition.internal_league_id,
            name="Youth Derby Away",
        )
        players["wonderkid"].current_club_id = home_club.id
        players["breakout"].current_club_id = away_club.id
        _seed_rivalry_matches(
            session,
            competition_id=competition.id,
            season_id=season.id,
            wonderkid=players["wonderkid"],
            breakout=players["breakout"],
            home_club=home_club,
            away_club=away_club,
        )
        session.commit()

    future_start = date.today() + timedelta(days=40)
    create_response = client.post(
        "/admin/regen-universe/youth-tournaments",
        headers=admin_headers,
        json={
            "name": "Global Future Stars Invitational",
            "age_limit": "U19",
            "rewards": {"winner": "exposure", "awards": ["Best Young Player", "Top Scorer", "Breakout Talent"]},
            "start_date": future_start.isoformat(),
            "end_date": (future_start + timedelta(days=3)).isoformat(),
            "participant_limit": 4,
            "simulate_immediately": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    tournament_payload = create_response.json()
    assert tournament_payload["status"] == "completed"
    assert len(tournament_payload["fixtures"]) == 3
    assert len(tournament_payload["standings"]) == 4
    assert any(player["award"] for player in tournament_payload["top_players"])

    list_response = client.get("/regen-universe/youth-tournaments")
    detail_response = client.get(f"/regen-universe/youth-tournaments/{tournament_payload['id']}")
    assert list_response.status_code == 200, list_response.text
    assert detail_response.status_code == 200, detail_response.text
    assert any(item["id"] == tournament_payload["id"] for item in list_response.json())
    assert detail_response.json()["id"] == tournament_payload["id"]

    story_job_response = client.post("/admin/regen-universe/jobs/story-regeneration", headers=admin_headers)
    rivalry_job_response = client.post("/admin/regen-universe/jobs/rivalry-detection", headers=admin_headers)
    dna_job_response = client.post("/admin/regen-universe/jobs/dna-evolution", headers=admin_headers)
    schedule_job_response = client.post(
        "/admin/regen-universe/jobs/tournament-scheduling",
        headers=admin_headers,
        params={"days_ahead": 21},
    )

    assert story_job_response.status_code == 200, story_job_response.text
    assert rivalry_job_response.status_code == 200, rivalry_job_response.text
    assert dna_job_response.status_code == 200, dna_job_response.text
    assert schedule_job_response.status_code == 200, schedule_job_response.text

    story_job_payload = story_job_response.json()
    rivalry_job_payload = rivalry_job_response.json()
    dna_job_payload = dna_job_response.json()
    schedule_job_payload = schedule_job_response.json()
    assert story_job_payload["status"] == "success"
    assert story_job_payload["result"]["stories_regenerated"] == len(players)
    assert rivalry_job_payload["status"] == "success"
    assert rivalry_job_payload["result"]["rivalries_updated"] >= 1
    assert dna_job_payload["status"] == "success"
    assert dna_job_payload["result"]["players_scanned"] == len(players)
    assert schedule_job_payload["status"] == "success"
    assert schedule_job_payload["result"]["created"] == 1

    with app.state.session_factory() as session:
        notification_keys = session.execute(select(NotificationRecord.template_key)).scalars().all()
        tournaments = session.scalars(select(YouthTournament).order_by(YouthTournament.start_date.asc())).all()

    assert "YOUTH_TOURNAMENT_START" in notification_keys
    assert "YOUTH_TOURNAMENT_STAR" in notification_keys
    assert len(tournaments) == 2
