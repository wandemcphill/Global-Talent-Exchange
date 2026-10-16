from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.gtex_universe.fan_experience import GtexFanExperienceService
from app.gtex_universe.social_warfare import GtexSocialWarfareService
from app.models.base import Base
from app.models.fan_experience import (
    FanExperienceTicket,
    FanProfile,
    FanReaction,
    FanTribe,
    LegacySnapshot,
    MarketShockEvent,
    MatchChatMessage,
    MatchChatRoom,
    MegaEvent,
    NarrativeConflict,
)
from app.models.gtex_economy import GtexLeague, GtexLeagueType, GtexMatch, GtexMatchStatus, GtexParticipantType
from app.models.manager_marketplace import ManagerProfile
from app.models.news_article import NewsArticle
from app.models.prestige_rating import PrestigeRating
from app.models.user import User
from tests.regen_universe_support import build_regen_universe_session


def _create_social_warfare_tables(session) -> None:
    bind = session.get_bind()
    assert bind is not None
    Base.metadata.create_all(
        bind,
        tables=[
            GtexLeague.__table__,
            GtexMatch.__table__,
            FanProfile.__table__,
            FanExperienceTicket.__table__,
            FanReaction.__table__,
            FanTribe.__table__,
            MatchChatRoom.__table__,
            MatchChatMessage.__table__,
            NarrativeConflict.__table__,
            MarketShockEvent.__table__,
            MegaEvent.__table__,
            LegacySnapshot.__table__,
            ManagerProfile.__table__,
            NewsArticle.__table__,
            PrestigeRating.__table__,
        ],
    )


def _make_user(*, user_id: str, full_name: str) -> User:
    return User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        full_name=full_name,
    )


def _make_match(*, league_id: str, home_user_id: str, away_user_id: str, metadata: dict[str, object]) -> GtexMatch:
    return GtexMatch(
        id="match-social-war",
        league_id=league_id,
        requested_by_user_id=home_user_id,
        status=GtexMatchStatus.RUNNING,
        home_participant_type=GtexParticipantType.HUMAN,
        home_user_id=home_user_id,
        away_participant_type=GtexParticipantType.HUMAN,
        away_user_id=away_user_id,
        entry_fee=Decimal("3.0000"),
        metadata_json=metadata,
    )


def test_match_experience_embeds_social_warfare_state() -> None:
    session = build_regen_universe_session()
    try:
        _create_social_warfare_tables(session)
        home_user = _make_user(user_id="fan-home", full_name="Home Fan")
        away_user = _make_user(user_id="fan-away", full_name="Away Fan")
        league = GtexLeague(
            id="league-social-war",
            code="social-war",
            name="Social War League",
            league_type=GtexLeagueType.CASUAL,
            min_elo=0,
            max_elo=1600,
            default_entry_fee=Decimal("3.0000"),
            ai_backfill_enabled=True,
            leaderboard_key="leaderboard:social-war",
            metadata_json={},
        )
        match = _make_match(
            league_id=league.id,
            home_user_id=home_user.id,
            away_user_id=away_user.id,
            metadata={
                "home_label": "Alpha FC",
                "away_label": "Beta FC",
                "fan_experience": {
                    "is_final": True,
                    "capacity": 120,
                    "vip_capacity": 12,
                    "synthetic_ticket_sales": 18,
                },
            },
        )
        session.add_all([home_user, away_user, league, match])
        session.flush()

        fan_service = GtexFanExperienceService(session)
        fan_service.update_profile(actor=home_user, favorite_club_id=f"user:{home_user.id}", rival_club_ids=[])
        fan_service.update_profile(actor=away_user, favorite_club_id=f"user:{away_user.id}", rival_club_ids=[])

        social_service = GtexSocialWarfareService(session)
        home_tribe = social_service.join_tribe(actor=home_user, match=match, club_id=f"user:{home_user.id}")
        social_service.join_tribe(actor=away_user, match=match, club_id=f"user:{away_user.id}")
        social_service.post_chat_message(
            actor=home_user,
            match=match,
            message="vamos legend",
            emoji="fire",
            intensity=2.4,
        )

        payload = fan_service.match_experience(match=match, current_user=home_user)

        assert payload["social_warfare"]["current_user_tribe"]["id"] == home_tribe.id
        assert len(payload["social_warfare"]["fan_tribes"]) == 2
        assert payload["social_warfare"]["live_chat"]["total_messages"] == 1
        assert payload["social_warfare"]["fan_war"]["rivalry_heat"] > 0.0
        assert payload["atmosphere"]["fan_war_pressure"] > 0.0
        assert payload["atmosphere"]["live_chat_pressure"] > 0.0
        assert payload["social_ticket_demand_multiplier"] >= 1.0
    finally:
        session.close()


def test_finalize_social_warfare_persists_conflicts_shocks_and_legacy() -> None:
    session = build_regen_universe_session()
    try:
        _create_social_warfare_tables(session)
        home_user = _make_user(user_id="manager-home", full_name="Home Boss")
        away_user = _make_user(user_id="manager-away", full_name="Away Boss")
        league = GtexLeague(
            id="league-social-final",
            code="social-final",
            name="Social Final League",
            league_type=GtexLeagueType.CASUAL,
            min_elo=0,
            max_elo=1600,
            default_entry_fee=Decimal("4.0000"),
            ai_backfill_enabled=True,
            leaderboard_key="leaderboard:social-final",
            metadata_json={},
        )
        match = _make_match(
            league_id=league.id,
            home_user_id=home_user.id,
            away_user_id=away_user.id,
            metadata={
                "home_label": "Atlas FC",
                "away_label": "Mirage United",
                "transfer_story": "Star captain crosses the divide and sparks betrayal talk.",
                "dao_vote_result": {"resolution": "corruption_probe"},
                "scandal": True,
                "fan_experience": {
                    "is_final": True,
                    "capacity": 180,
                    "vip_capacity": 18,
                    "synthetic_ticket_sales": 120,
                },
            },
        )
        match.home_score = 4
        match.away_score = 1
        home_manager = ManagerProfile(manager_id=home_user.id, name="Home Boss", current_losing_streak=0)
        away_manager = ManagerProfile(manager_id=away_user.id, name="Away Boss", current_losing_streak=3)
        session.add_all([home_user, away_user, league, match, home_manager, away_manager])
        session.flush()

        fan_service = GtexFanExperienceService(session)
        fan_service.update_profile(actor=home_user, favorite_club_id=f"user:{home_user.id}", rival_club_ids=[])
        fan_service.update_profile(actor=away_user, favorite_club_id=f"user:{away_user.id}", rival_club_ids=[])

        social_service = GtexSocialWarfareService(session)
        social_service.join_tribe(actor=home_user, match=match, club_id=f"user:{home_user.id}")
        social_service.join_tribe(actor=away_user, match=match, club_id=f"user:{away_user.id}")
        social_service.post_chat_message(actor=home_user, match=match, message="legend win", emoji="fire", intensity=2.6)
        social_service.post_chat_message(actor=away_user, match=match, message="fraud sack", emoji="thumbs_down", intensity=2.2)

        payload = social_service.finalize_match_social_warfare(
            match=match,
            fan_context={
                "winner_side": "home",
                "sell_out_triggered": True,
                "commentary_tone": "hostile",
                "tickets_sold": 170,
                "home_manager_id": home_manager.id,
                "away_manager_id": away_manager.id,
            },
        )

        conflict_types = {item["conflict_type"] for item in payload["narrative_conflicts"]}
        shock_types = {item["shock_type"] for item in payload["market_shocks"]}

        assert "manager_under_pressure" in conflict_types
        assert "fan_backlash" in conflict_types
        assert "dao_corruption_vote" in shock_types
        assert "breakout_star" in shock_types
        assert session.scalar(select(LegacySnapshot).where(LegacySnapshot.category == "greatest_matches")) is not None
        assert session.scalar(select(MegaEvent).where(MegaEvent.match_id == match.id)) is not None
        assert session.scalar(select(NewsArticle).where(NewsArticle.article_type == "market_shock")) is not None
    finally:
        session.close()
