from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_admin, get_current_user, get_session
from app.history_engagement.router import admin_router, router
from app.ingestion.models import Club as IngestionClub
from app.ingestion.models import Competition as IngestionCompetition
from app.ingestion.models import Country, InternalLeague, LiquidityBand, Player, SupplyTier
from app.models.base import Base
from app.models.club_profile import ClubProfile
from app.models.club_social import RivalryProfile
from app.models.club_trophy import ClubTrophy
from app.models.competition import UserCompetition
from app.models.competition_round import CompetitionRound
from app.models.competition_match import CompetitionMatch
from app.models.broadcast_rights import ViewSession
from app.models.history_engagement import (
    Achievement,
    DailyTask,
    HistoricalLeaderboardEntry,
    HistoricalRecord,
    MilestoneProgress,
    SeasonPassMission,
    SeasonPassReward,
    SeasonPassSeason,
    SocialActivity,
    UserAchievement,
    UserFollow,
    UserObjectiveProgress,
    UserProfile,
    UserSeasonMissionProgress,
    UserSeasonProgress,
    UserSeasonRewardClaim,
    UserStreak,
    WeeklyTask,
)
from app.models.media_engine import MatchRevenueSnapshot
from app.models.national_team import NationalTeamCompetition, NationalTeamEntry
from app.models.notification_record import NotificationRecord
from app.models.player_cards import PlayerCard, PlayerCardTier
from app.models.player_contract import PlayerContract
from app.models.regen import (
    RegenAward,
    RegenDiscoveryBadge,
    RegenGenerationEvent,
    RegenLegacyRecord,
    RegenProfile,
)
from app.models.reward_settlement import RewardSettlement
from app.models.story_feed import StoryFeedItem
from app.models.transfer_bid import TransferBid
from app.models.transfer_market import MarketWatchlistEntry, TransferListing, TransferListingBid, TransferNegotiation
from app.models.transfer_window import TransferWindow
from app.models.user import KycStatus, User, UserRole
from app.predictions.models import Prediction, PredictionOutcome


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            ClubProfile.__table__,
            UserCompetition.__table__,
            CompetitionRound.__table__,
            CompetitionMatch.__table__,
            Country.__table__,
            InternalLeague.__table__,
            SupplyTier.__table__,
            LiquidityBand.__table__,
            IngestionCompetition.__table__,
            IngestionClub.__table__,
            Player.__table__,
            PlayerCardTier.__table__,
            PlayerCard.__table__,
            PlayerContract.__table__,
            TransferWindow.__table__,
            TransferListing.__table__,
            TransferListingBid.__table__,
            TransferBid.__table__,
            TransferNegotiation.__table__,
            MatchRevenueSnapshot.__table__,
            ClubTrophy.__table__,
            NotificationRecord.__table__,
            RewardSettlement.__table__,
            Achievement.__table__,
            UserAchievement.__table__,
            MilestoneProgress.__table__,
            UserProfile.__table__,
            UserFollow.__table__,
            SocialActivity.__table__,
            DailyTask.__table__,
            WeeklyTask.__table__,
            UserObjectiveProgress.__table__,
            SeasonPassSeason.__table__,
            SeasonPassReward.__table__,
            SeasonPassMission.__table__,
            UserSeasonProgress.__table__,
            UserSeasonRewardClaim.__table__,
            UserSeasonMissionProgress.__table__,
            UserStreak.__table__,
            HistoricalRecord.__table__,
            HistoricalLeaderboardEntry.__table__,
            RegenProfile.__table__,
            RegenGenerationEvent.__table__,
            RegenAward.__table__,
            RegenDiscoveryBadge.__table__,
            RegenLegacyRecord.__table__,
            Prediction.__table__,
            RivalryProfile.__table__,
            NationalTeamCompetition.__table__,
            NationalTeamEntry.__table__,
            StoryFeedItem.__table__,
            MarketWatchlistEntry.__table__,
            ViewSession.__table__,
        ],
    )
    session_local = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with session_local() as db_session:
        today = datetime.now(UTC).date()
        db_session.add_all(
            [
                User(id="manager-1", email="manager1@example.com", username="manager-1", display_name="Manager One", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="manager-2", email="manager2@example.com", username="manager-2", display_name="Manager Two", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                User(id="fan-1", email="fan1@example.com", username="fan-1", display_name="Fan One", password_hash="x", role=UserRole.USER, kyc_status=KycStatus.FULLY_VERIFIED),
                ClubProfile(id="club-1", owner_user_id="manager-1", club_name="Lagos Meteors", short_name="LAG", slug="lagos-meteors", primary_color="#111111", secondary_color="#ffffff", accent_color="#009966", visibility="public"),
                ClubProfile(id="club-2", owner_user_id="manager-2", club_name="Abuja Comets", short_name="ABJ", slug="abuja-comets", primary_color="#222222", secondary_color="#eeeeee", accent_color="#ff5500", visibility="public"),
                UserCompetition(id="comp-1", host_user_id="manager-1", name="Premier Test Cup", format="cup", visibility="public", status="completed", currency="coin"),
                CompetitionRound(id="round-1", competition_id="comp-1", round_number=1, stage="final", status="completed", metadata_json={}),
                Player(id="player-1", source_provider="test", provider_external_id="player-1", full_name="Ayo Ade", current_club_profile_id="club-1"),
                PlayerCardTier(id="tier-1", code="legend", name="Legend", rarity_rank=1, metadata_json={}),
                PlayerCard(id="card-1", player_id="player-1", tier_id="tier-1", display_name="Ayo Ade", edition_code="base", metadata_json={}),
                TransferWindow(id="window-1", territory_code="NG", label="Summer Window", status="open", opens_on=today - timedelta(days=1), closes_on=today + timedelta(days=30)),
                TransferBid(id="legacy-bid-1", window_id="window-1", player_id="player-1", selling_club_id="club-1", buying_club_id="club-2", status="completed", bid_amount=100, structured_terms_json={}),
                PlayerContract(id="contract-1", player_id="player-1", club_id="club-2", status="active", wage_amount=100, signed_on=today, starts_on=today, ends_on=today + timedelta(days=365)),
                TransferListing(id="listing-1", window_id="window-1", player_id="player-1", selling_club_id="club-1", base_price=100, current_highest_bid=150, highest_bidder_id="club-2", status="closed", expires_at=datetime.now(UTC), metadata_json={}),
                TransferListing(id="listing-2", window_id="window-1", player_id="player-1", selling_club_id="club-1", base_price=120, current_highest_bid=180, highest_bidder_id="club-2", status="closed", expires_at=datetime.now(UTC), metadata_json={}),
                TransferListingBid(id="listing-bid-1", listing_id="listing-1", bidder_club_id="club-2", amount=150, metadata_json={}),
                TransferListingBid(id="listing-bid-2", listing_id="listing-2", bidder_club_id="club-2", amount=180, metadata_json={}),
                TransferNegotiation(id="neg-1", listing_id="listing-1", winning_bid_id="listing-bid-1", player_id="player-1", selling_club_id="club-1", bidder_club_id="club-2", status="completed", contract_years=4, player_contract_id="contract-1", lifecycle_transfer_bid_id="legacy-bid-1", resolved_at=datetime.now(UTC), metadata_json={}),
                TransferNegotiation(id="neg-2", listing_id="listing-2", winning_bid_id="listing-bid-2", player_id="player-1", selling_club_id="club-1", bidder_club_id="club-2", status="completed", contract_years=5, resolved_at=datetime.now(UTC), metadata_json={}),
                CompetitionMatch(id="match-1", competition_id="comp-1", round_id="round-1", round_number=1, stage="final", home_club_id="club-1", away_club_id="club-2", match_date=today, status="completed", home_score=4, away_score=2, winner_club_id="club-1", completed_at=datetime.now(UTC), metadata_json={}),
                MatchRevenueSnapshot(id="revenue-1", match_key="match-1", competition_key="comp-1", home_club_id="club-1", away_club_id="club-2", total_views=500, premium_purchases=40, total_revenue_coin=200, home_club_share_coin=100, away_club_share_coin=100, metadata_json={}),
                ClubTrophy(id="trophy-1", club_id="club-1", trophy_type="cup", trophy_name="Premier Test Cup", competition_source="competition", competition_id="comp-1", season_label="2026", prestige_weight=120, metadata_json={}),
                RegenProfile(id="regen-profile-1", regen_id="regen-1", player_id="player-1", linked_unique_card_id="card-1", generated_for_club_id="club-1", birth_country_code="NG", primary_position="ST", secondary_positions_json=[], generated_at=datetime.now(UTC), current_gsi=92, current_ability_range_json={"min": 90, "max": 92}, potential_range_json={"min": 93, "max": 97}, scout_confidence="elite", generation_source="academy", metadata_json={}),
                RegenGenerationEvent(id="regen-gen-1", regen_profile_id="regen-profile-1", club_id="club-1", generation_source="academy", season_label="2026", metadata_json={}),
                RegenAward(id="regen-award-1", regen_id="regen-profile-1", club_id="club-1", award_code="golden-boy", award_name="Golden Boy", award_category="individual", season_label="2026", impact_score=9.5, metadata_json={}),
                RegenDiscoveryBadge(id="regen-badge-1", regen_id="regen-profile-1", club_id="club-1", badge_code="generational-talent", badge_name="Generational Talent", metadata_json={}),
                RegenLegacyRecord(id="regen-legacy-1", regen_id="regen-profile-1", player_id="player-1", club_id="club-1", appearances_total=120, goals_total=88, assists_total=30, awards_total=3, seasons_total=5, legacy_score=55, legacy_tier="legend", is_legend=True, narrative_summary="Ayo Ade dominated the era.", metadata_json={}),
                Prediction(id="prediction-1", user_id="manager-1", match_id="match-1", predicted_outcome=PredictionOutcome.HOME_WIN, confidence_level=0.8, metadata_json={}),
                RivalryProfile(id="rivalry-1", club_a_id="club-1", club_b_id="club-2", label="Meteors vs Comets", intensity_score=77, streak_holder_club_id="club-1", streak_length=3, metadata_json={}, notable_moments_json=["Cup final thriller"], narrative_tags_json=[]),
                NationalTeamCompetition(id="nat-comp-1", key="nations-1", title="Federation Nations Cup", season_label="2026", status="completed", metadata_json={"winner_manager_user_id": "manager-1"}),
                NationalTeamEntry(id="nat-entry-1", competition_id="nat-comp-1", country_code="NG", country_name="Nigeria", manager_user_id="manager-1", metadata_json={}),
                StoryFeedItem(id="story-1", story_type="club_story", audience="public", title="Meteors dominated the final", body="A statement performance under the lights.", subject_type="club", subject_id="club-1", metadata_json={}, featured=True),
                MarketWatchlistEntry(id="watch-1", club_id="club-1", player_id="player-1", source="scouting", discovery_score=88, metadata_json={}),
            ]
        )
        for idx in range(2, 11):
            db_session.add(
                CompetitionRound(
                    id=f"round-{idx}",
                    competition_id="comp-1",
                    round_number=idx,
                    stage="league",
                    status="completed",
                    metadata_json={},
                )
            )
            db_session.add(
                CompetitionMatch(
                    id=f"match-{idx}",
                    competition_id="comp-1",
                    round_id=f"round-{idx}",
                    round_number=idx,
                    stage="league",
                    home_club_id="club-1",
                    away_club_id="club-2",
                    match_date=today,
                    status="completed",
                    home_score=2 + (idx % 2),
                    away_score=1,
                    winner_club_id="club-1",
                    completed_at=datetime.now(UTC) - timedelta(hours=idx),
                    metadata_json={},
                )
            )
        for idx in range(1, 11):
            db_session.add(
                ViewSession(
                    id=f"view-{idx}",
                    user_id="manager-1",
                    match_id=f"match-{idx}",
                    competition_id="comp-1",
                    timestamp=datetime.now(UTC) - timedelta(minutes=idx),
                    metadata_json={},
                )
            )
        for idx in range(2, 27):
            db_session.add(
                UserFollow(
                    id=f"seed-follow-{idx}",
                    follower_user_id="fan-1" if idx == 2 else "manager-2",
                    target_key=f"manager:manager-1:{idx}",
                    target_type="manager",
                    target_user_id="manager-1",
                    metadata_json={},
                )
            )
        db_session.commit()
        yield db_session
    engine.dispose()


@pytest.fixture()
def user_state(session: Session) -> dict[str, User]:
    return {
        "current_user": session.get(User, "fan-1"),
        "admin_user": session.get(User, "manager-1"),
    }


@pytest.fixture()
def app(session: Session, user_state: dict[str, User]) -> FastAPI:
    application = FastAPI()
    application.include_router(router)
    application.include_router(admin_router)

    def override_session() -> Iterator[Session]:
        yield session

    def override_user() -> User:
        return user_state["current_user"]

    def override_admin() -> User:
        return user_state["admin_user"]

    application.dependency_overrides[get_session] = override_session
    application.dependency_overrides[get_current_user] = override_user
    application.dependency_overrides[get_current_admin] = override_admin
    return application


@pytest.fixture()
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_history_endpoints_publish_leaderboards_and_timeline(client: TestClient) -> None:
    leaderboard_response = client.get("/history/leaderboards")
    assert leaderboard_response.status_code == 200, leaderboard_response.text
    leaderboard_body = leaderboard_response.json()
    assert leaderboard_body["top_clubs_ever"][0]["entity_id"] == "club-1"
    assert leaderboard_body["top_players_ever"][0]["entity_id"] == "player-1"
    assert leaderboard_body["top_managers"][0]["entity_id"] == "manager-1"

    goat_response = client.get("/history/goat-rankings", params={"entity_type": "player"})
    assert goat_response.status_code == 200, goat_response.text
    assert goat_response.json()["entries"][0]["entity_id"] == "player-1"

    timeline_response = client.get("/history/timeline/player/player-1")
    assert timeline_response.status_code == 200, timeline_response.text
    timeline_body = timeline_response.json()
    assert timeline_body["historical_ranking"]["entity_id"] == "player-1"
    assert any(item["event_type"] == "award" for item in timeline_body["career_timeline"])

    records_response = client.get("/history/records")
    assert records_response.status_code == 200, records_response.text
    assert any(item["headline"] == "Highest scoring match" for item in records_response.json())


def test_social_follow_feed_and_community_routes(client: TestClient, user_state: dict[str, User]) -> None:
    follow_response = client.post("/social/follows", json={"target_type": "manager", "target_id": "manager-1"})
    assert follow_response.status_code == 201, follow_response.text
    assert follow_response.json()["target_user_id"] == "manager-1"

    club_follow_response = client.post("/social/follows", json={"target_type": "club", "target_id": "club-1"})
    assert club_follow_response.status_code == 201, club_follow_response.text

    feed_response = client.get("/social/feed")
    assert feed_response.status_code == 200, feed_response.text
    activity_types = {item["activity_type"] for item in feed_response.json()}
    assert {"transfer", "match_win", "story_event"} <= activity_types

    community_response = client.get("/social/clubs/club-1/community")
    assert community_response.status_code == 200, community_response.text
    assert community_response.json()["club_id"] == "club-1"

    message_response = client.post("/social/clubs/club-1/community/messages", json={"body": "Big win."})
    assert message_response.status_code == 201, message_response.text
    assert message_response.json()["activity_type"] == "fan_chat"

    rivalry_response = client.post("/social/rivalries/club-1/club-2/banter", json={"body": "Comets got cooked."})
    assert rivalry_response.status_code == 201, rivalry_response.text
    assert rivalry_response.json()["activity_type"] == "banter"

    rivalry_page_response = client.get("/social/rivalries/club-1/club-2")
    assert rivalry_page_response.status_code == 200, rivalry_page_response.text
    assert rivalry_page_response.json()["intensity_score"] == 77


def test_engagement_sync_and_objectives_complete_for_manager(
    client: TestClient,
    user_state: dict[str, User],
) -> None:
    user_state["current_user"] = user_state["admin_user"]

    sync_response = client.post("/engagement/sync")
    assert sync_response.status_code == 200, sync_response.text
    sync_body = sync_response.json()
    unlocked = {item["metadata_json"]["achievement_key"] for item in sync_body["unlocked_achievements"]}
    assert "develop-regen-90" in unlocked
    assert "discover-generational-talent" in unlocked
    assert sync_body["streak"]["streak_days"] == 1
    assert sync_body["season_pass"]["season_id"] == "S1"
    assert sync_body["season_pass"]["current_level"] >= 5
    assert len(sync_body["season_pass"]["daily_missions"]) == 3

    objectives_response = client.get("/objectives/me")
    assert objectives_response.status_code == 200, objectives_response.text
    objectives_body = objectives_response.json()
    assert all(item["completed"] for item in objectives_body["daily_tasks"])
    assert all(item["completed"] for item in objectives_body["weekly_tasks"])

    achievements_response = client.get("/engagement/achievements/me")
    assert achievements_response.status_code == 200, achievements_response.text
    assert len(achievements_response.json()) >= 2

    admin_response = client.post("/admin/history-engagement/run-workers")
    assert admin_response.status_code == 200, admin_response.text
    assert admin_response.json()["reconciled_users"] >= 1


def test_season_pass_route_exposes_rewards_and_supports_claims(
    client: TestClient,
    user_state: dict[str, User],
) -> None:
    user_state["current_user"] = user_state["admin_user"]

    season_response = client.get("/season-pass/me")
    assert season_response.status_code == 200, season_response.text
    season_body = season_response.json()
    assert season_body["season_id"] == "S1"
    assert season_body["current_level"] >= 5
    assert any(item["completed"] for item in season_body["daily_missions"])

    reward = next(item for item in season_body["rewards"] if item["level"] == 5)
    assert reward["claimable"] is True
    assert reward["claimed"] is False

    claim_response = client.post(f"/season-pass/rewards/{reward['id']}/claim")
    assert claim_response.status_code == 201, claim_response.text
    claim_body = claim_response.json()
    assert claim_body["reward_id"] == reward["id"]
    assert claim_body["granted_payload_json"]["gtex"] == 5

    refreshed_response = client.get("/season-pass/me")
    assert refreshed_response.status_code == 200, refreshed_response.text
    refreshed_reward = next(item for item in refreshed_response.json()["rewards"] if item["id"] == reward["id"])
    assert refreshed_reward["claimed"] is True
    assert refreshed_reward["claimable"] is False
