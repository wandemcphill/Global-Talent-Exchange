from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select

from app.awards.service import AwardsCultureService
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
from app.models.national_team import NationalTeamCompetition, NationalTeamEntry
from app.models.news_article import NewsArticle
from app.models.notification_record import NotificationRecord
from app.models.platform_experience_state import PlatformExperienceState
from app.models.player_fan_reaction import PlayerFanReaction
from app.models.prestige_rating import PrestigeRating
from app.models.regen_ecosystem import NationalRegenSeed, RegenAwardVote
from app.models.user import User
from app.platform_experience.service import PlatformExperienceService
from app.regen_universe.models import RegenAward, RegenSeason
from app.regen_universe.service import RegenUniverseService
from app.gtex_universe.fan_experience import GtexFanExperienceService
from tests.regen_universe_support import build_regen_universe_session, seed_two_season_universe


def _create_mega_pack_tables(session) -> None:
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
            NationalTeamCompetition.__table__,
            NationalTeamEntry.__table__,
            NewsArticle.__table__,
            NotificationRecord.__table__,
            PlayerFanReaction.__table__,
            PrestigeRating.__table__,
            RegenAwardVote.__table__,
            PlatformExperienceState.__table__,
        ],
    )


def _make_user(*, user_id: str, email: str, username: str, full_name: str) -> User:
    return User(
        id=user_id,
        email=email,
        username=username,
        password_hash="hashed",
        full_name=full_name,
    )


def _prepare_completed_awards_season(session, bundle: dict[str, object]) -> RegenSeason:
    service: RegenUniverseService = bundle["service"]
    first_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
    assert first_season is not None
    service.close_season(first_season.id, start_next_season=True)

    second_season = session.scalar(select(RegenSeason).where(RegenSeason.is_active.is_(True)))
    assert second_season is not None
    second_season.start_date = bundle["ingestion_season_two"].start_date
    second_season.end_date = bundle["ingestion_season_two"].end_date
    second_season.metadata_json = {"source_ingestion_season_ids": [bundle["ingestion_season_two"].id]}
    session.flush()

    service.close_season(second_season.id, start_next_season=False)
    return second_season


def test_match_ticket_purchase_and_reaction_create_sell_out_hype_and_atmosphere() -> None:
    session = build_regen_universe_session()
    try:
        _create_mega_pack_tables(session)
        home_user = _make_user(
            user_id="fan-home",
            email="home@example.com",
            username="fanhome",
            full_name="Home Fan",
        )
        away_user = _make_user(
            user_id="fan-away",
            email="away@example.com",
            username="fanaway",
            full_name="Away Fan",
        )
        league = GtexLeague(
            id="league-fan",
            code="fan-test",
            name="Fan Test League",
            league_type=GtexLeagueType.CASUAL,
            min_elo=0,
            max_elo=1600,
            default_entry_fee=Decimal("2.0000"),
            ai_backfill_enabled=True,
            leaderboard_key="leaderboard:fan-test",
            metadata_json={},
        )
        match = GtexMatch(
            id="match-fan-final",
            league_id=league.id,
            requested_by_user_id=home_user.id,
            status=GtexMatchStatus.QUEUED,
            home_participant_type=GtexParticipantType.HUMAN,
            home_user_id=home_user.id,
            away_participant_type=GtexParticipantType.HUMAN,
            away_user_id=away_user.id,
            entry_fee=Decimal("2.0000"),
            metadata_json={
                "home_label": "Alpha FC",
                "away_label": "Beta FC",
                "fan_experience": {
                    "is_final": True,
                    "capacity": 2,
                    "vip_capacity": 1,
                    "synthetic_ticket_sales": 1,
                },
            },
        )
        session.add_all([home_user, away_user, league, match])
        session.flush()

        service = GtexFanExperienceService(session)
        service.update_profile(actor=home_user, rival_club_ids=["club-rival"])
        service.purchase_match_ticket(actor=home_user, match=match, ticket_tier="vip")
        service.submit_match_reaction(actor=home_user, match=match, reaction_type="hype", supported_side="home")
        payload = service.match_experience(match=match, current_user=home_user)

        assert payload["sell_out_hype"]["triggered"] is True
        assert payload["atmosphere"]["priority_stream"] is True
        assert payload["atmosphere"]["crowd_intensity_boost"] > 0.0
        assert payload["current_user"]["dao_priority"] is True
        assert session.scalar(select(NewsArticle).where(NewsArticle.article_type == "sell_out_hype")) is not None
    finally:
        session.close()


def test_regen_hype_board_publishes_required_shortlist_articles() -> None:
    session = build_regen_universe_session()
    try:
        _create_mega_pack_tables(session)
        bundle = seed_two_season_universe(session)
        completed_season = _prepare_completed_awards_season(session, bundle)
        country_rows = [
            ("NG", "Nigeria"),
            ("GH", "Ghana"),
            ("SN", "Senegal"),
            ("CM", "Cameroon"),
            ("CI", "Ivory Coast"),
        ]
        for index in range(15):
            country_code, country_name = country_rows[index % len(country_rows)]
            session.add(
                NationalRegenSeed(
                    seed_key=f"seed-{index}",
                    display_name=f"Wonderkid {index}",
                    country_code=country_code,
                    country_name=country_name,
                    confederation_code="CAF",
                    primary_position="ST" if index % 2 == 0 else "CM",
                    current_rating=70 + index,
                    potential_rating=85 + (15 - index),
                    growth_curve=0.55 + (index * 0.01),
                    rarity_tier="elite" if index < 5 else "rare",
                    metadata_json={"headline_score": 100 - index},
                )
            )
        session.flush()

        payload = GtexFanExperienceService(session).regen_hype_board(season_id=completed_season.id)
        article_titles = {
            title
            for title in session.scalars(select(NewsArticle.title)).all()
        }

        assert len(payload["wonderkids"]) == 10
        assert len(payload["rising_stars"]) == 5
        assert "Top 10 Wonderkids" in article_titles
        assert "Top 5 Rising Stars" in article_titles
        assert any(item["award_name"] == "GTEX Ballon d'Or" for item in payload["award_nominee_headlines"])
    finally:
        session.close()


def test_awards_ceremony_contains_ticket_and_vote_metadata() -> None:
    session = build_regen_universe_session()
    try:
        _create_mega_pack_tables(session)
        bundle = seed_two_season_universe(session)
        completed_season = _prepare_completed_awards_season(session, bundle)
        service = AwardsCultureService(session)
        ceremony = service.get_ceremony(season_id=completed_season.id)
        assert ceremony is not None

        first_segment = ceremony["segments"][0]
        finalist = first_segment["finalists"][0]
        award = session.scalar(select(RegenAward).where(RegenAward.code == first_segment["award_code"]))
        assert award is not None

        voter = _make_user(
            user_id="ceremony-fan",
            email="ceremony@example.com",
            username="ceremonyfan",
            full_name="Ceremony Fan",
        )
        session.add(voter)
        session.flush()

        profile = FanProfile(
            user_id=voter.id,
            loyalty_score=92.0,
            reputation_score=40.0,
            fan_tier="Legend",
            attendance_count=0,
            attendance_history_json=[],
            badges_json=["legend-crest"],
            metadata_json={"fan_tier": "Legend"},
        )
        session.add(profile)
        session.flush()

        session.add(
            FanExperienceTicket(
                user_id=voter.id,
                fan_profile_id=profile.id,
                event_type="ceremony",
                event_key=f"ceremony:{completed_season.id}",
                match_id=None,
                ticket_tier="vip",
                access_level="tv_mode_only",
                status="purchased",
                seat_label="VIP-1",
                price_coin=Decimal("32.0000"),
                discount_bps=0,
                priority_stream=True,
                exclusive_commentary_lines_json=["VIP podium feed"],
                loyalty_bonus=12.0,
                reputation_bonus=14.0,
                metadata_json={},
            )
        )
        session.add(
            RegenAwardVote(
                user_id=voter.id,
                award_id=award.id,
                player_id=finalist["entity_id"],
                season_id=completed_season.id,
                metadata_json={},
            )
        )
        session.flush()

        ceremony = service.get_ceremony(season_id=completed_season.id)
        assert ceremony is not None
        assert ceremony["ticketed_access"] is True
        assert ceremony["tv_mode_only"] is True
        assert ceremony["live_vote_enabled"] is True
        assert ceremony["ceremony_flow"] == ["Nominees", "Top 3", "Live Reveal", "Winner", "Reaction Explosion"]
        assert ceremony["tickets_sold"] == 1
        assert ceremony["vip_tickets_sold"] == 1
        assert ceremony["live_vote_snapshot"][first_segment["award_code"]][0]["vote_count"] == 1
        assert ceremony["reaction_explosion"]["legend_attendees"] == 1
    finally:
        session.close()


def test_platform_mode_exposes_ticket_feature_flags() -> None:
    session = build_regen_universe_session()
    try:
        _create_mega_pack_tables(session)
        user = _make_user(
            user_id="platform-fan",
            email="platform@example.com",
            username="platformfan",
            full_name="Platform Fan",
        )
        profile = FanProfile(
            user_id=user.id,
            loyalty_score=48.0,
            reputation_score=18.0,
            fan_tier="Ultra",
            attendance_count=1,
            attendance_history_json=[],
            badges_json=["ultra-voice"],
            metadata_json={"fan_tier": "Ultra"},
        )
        ticket = FanExperienceTicket(
            user_id=user.id,
            fan_profile_id=profile.id,
            event_type="ceremony",
            event_key="ceremony:test-season",
            match_id=None,
            ticket_tier="vip",
            access_level="tv_mode_only",
            status="purchased",
            seat_label="VIP-9",
            price_coin=Decimal("32.0000"),
            discount_bps=700,
            priority_stream=True,
            exclusive_commentary_lines_json=["Podium isolation feed"],
            loyalty_bonus=12.0,
            reputation_bonus=14.0,
            metadata_json={},
        )
        session.add_all([user, profile, ticket])
        session.flush()

        payload = PlatformExperienceService(session).get_mode(current_user=user, device_id="living-room-tv")

        assert payload["features"]["priority_stream_access"] is True
        assert payload["features"]["exclusive_commentary_lane"] is True
        assert payload["features"]["ceremony_tv_access"] is True
    finally:
        session.close()
