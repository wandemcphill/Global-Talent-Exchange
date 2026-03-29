from __future__ import annotations

import app.models  # noqa: F401
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.commentary.schemas import CommentarySelectionRequest
from app.commentary.service import CommentaryService
from app.global_memory.models import PlayerHistory
from app.ingestion.models import Player
from app.live_matches.schemas import LiveMatchStreamEventView
from app.models.base import Base
from app.models.club_ownership import ClubGovernanceState, ClubToken, ClubTreasury
from app.models.club_profile import ClubProfile
from app.models.club_social import RivalryProfile
from app.models.player_rivalry import PlayerRivalry
from app.models.player_story import PlayerStory
from app.models.user import User


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, SessionLocal()


def test_commentary_service_renders_dual_profiles_with_memory_and_governance_hooks() -> None:
    engine, session = _session()
    try:
        user = User(email="fan@example.com", username="fan", password_hash="hash")
        owner = User(email="owner@example.com", username="owner", password_hash="hash")
        session.add_all([user, owner])
        session.flush()

        home_club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Lagos Meteors",
            slug="lagos-meteors",
            primary_color="#111111",
            secondary_color="#ffffff",
            accent_color="#ff5500",
        )
        away_club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Abuja Sparks",
            slug="abuja-sparks",
            primary_color="#004488",
            secondary_color="#ffee00",
            accent_color="#00cc88",
        )
        session.add_all([home_club, away_club])
        session.flush()

        hero = Player(
            source_provider="test",
            provider_external_id="hero-1",
            full_name="Ayo Striker",
            current_club_profile_id=home_club.id,
        )
        rival = Player(
            source_provider="test",
            provider_external_id="rival-1",
            full_name="Tariq Marker",
            current_club_profile_id=away_club.id,
        )
        session.add_all([hero, rival])
        session.flush()

        session.add_all(
            [
                PlayerHistory(
                    player_id=hero.id,
                    global_player_id=f"global-{hero.id}",
                    event="Won the coastal derby last season.",
                    competition="Premier Cup",
                ),
                PlayerStory(
                    player_id=hero.id,
                    chapters={"current_arc": "He is chasing another late winner."},
                ),
                PlayerRivalry(
                    player_a_id=hero.id,
                    player_b_id=rival.id,
                    intensity_score=84.0,
                ),
                RivalryProfile(
                    club_a_id=home_club.id,
                    club_b_id=away_club.id,
                    label="The Southwest Firestorm",
                    intensity_score=91,
                ),
                ClubToken(
                    club_id=home_club.id,
                    price=1.2,
                    performance_score=0.8,
                    win_rate=0.65,
                    fan_demand_score=0.45,
                    treasury_balance_snapshot=24.0,
                ),
                ClubTreasury(
                    club_id=home_club.id,
                    balance_coin=24.0,
                ),
                ClubGovernanceState(
                    club_id=home_club.id,
                    formation="3-4-3",
                    playstyle="vertical press",
                    fan_mandate_summary="Fans demanded 3-4-3 and relentless pressure.",
                ),
            ]
        )
        session.commit()

        service = CommentaryService(session)
        service.seed_defaults()
        profiles = {item.name: item for item in service.list_profiles()}
        selection = service.save_selection(
            user=user,
            payload=CommentarySelectionRequest(
                match_id="match-1",
                primary_profile_id=profiles["The Hype Beast"].id,
                secondary_profile_id=profiles["The General"].id,
                dual_mode=True,
                voice_enabled=False,
            ),
        )
        session.commit()

        response = service.render_stream(
            match_id="match-1",
            status="live",
            user_id=user.id,
            cursor=1,
            include_audio=False,
            events=[
                LiveMatchStreamEventView(
                    match_id="match-1",
                    event_id="evt-1",
                    minute=89,
                    event_type="goal",
                    source_event_type="goal",
                    team_id=home_club.id,
                    team="Lagos Meteors",
                    team_side="home",
                    player_id=hero.id,
                    player="Ayo Striker",
                    secondary_player_id=rival.id,
                    secondary_player="Tariq Marker",
                    commentary="Ayo Striker scores late for Lagos Meteors.",
                    home_score=2,
                    away_score=1,
                    highlight_eligible=True,
                    meta={"importance": 5},
                    metadata={
                        "commentary_context": {
                            "event_family": "goal",
                            "importance": 5,
                            "late_drama": True,
                            "team_name": "Lagos Meteors",
                            "opponent_team_name": "Abuja Sparks",
                            "player_name": "Ayo Striker",
                        }
                    },
                )
            ],
        )

        assert selection.dual_mode is True
        assert response.selection.primary_profile.name == "The Hype Beast"
        assert response.events[0].secondary is not None
        assert response.events[0].secondary.profile_name == "The General"
        assert response.events[0].context["governance_formation"] == "3-4-3"
        assert "Fans demanded" in response.events[0].context["governance_story_hook"]
        assert response.events[0].context["player_history_hook"] == "Won the coastal derby last season."
        assert response.events[0].context["rivalry_label"] == "The Southwest Firestorm"
        assert response.events[0].line != response.events[0].base_line
    finally:
        session.close()
        engine.dispose()
