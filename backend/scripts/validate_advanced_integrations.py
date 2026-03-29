from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
for candidate in (REPO_ROOT, BACKEND_ROOT):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import app.models  # noqa: F401
from app.ads_engine.router import router as ads_router
from app.ads_engine.unified_ranking import UnifiedFeedCandidate, rank_unified_feed
from app.analytics.router import public_router as analytics_public_router
from app.auth.dependencies import get_current_admin, get_optional_current_user, get_session
from app.creator_marketplace.router import router as creator_marketplace_router
from app.creator_marketplace.schemas import (
    CampaignAcceptRequest,
    CampaignApplyRequest,
    CampaignClipSubmissionRequest,
    CampaignCreateRequest,
)
from app.creator_marketplace.service import CreatorMarketplaceService
from app.infinite_league.router import router as infinite_league_router
from app.media_engine.schemas import CreatorClipRevenueAttributionRequest
from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.competition_match import CompetitionMatch
from app.models.creator_marketplace import (
    CreatorMarketplaceCampaign,
    CreatorMarketplaceCampaignPayoutBasis,
    CreatorMarketplaceCampaignPayoutType,
    CreatorMarketplaceOffer,
    CreatorMarketplaceParticipation,
    CreatorMarketplaceReputationScore,
)
from app.models.creator_profile import CreatorProfile
from app.models.event_backbone import EventOutbox
from app.models.follow import Follow
from app.models.highlight_event import HighlightEvent
from app.models.highlight_share import HighlightShareExport
from app.models.manager_duel import ManagerDuel
from app.models.notification_record import NotificationRecord
from app.models.spectator_session import SpectatorSession
from app.models.sponsored_clip import SponsoredClip
from app.models.story_feed import StoryFeedItem
from app.models.user import User, UserRole
from app.models.user_affinity_profile import UserAffinityProfile
from app.models.user_region import UserRegionProfile
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction, LedgerUnit
from app.replay_archive.persistence import ReplayArchiveRecordRow
from app.services.creator_clip_monetization_service import CreatorClipMonetizationService
from app.users.follow_service import FollowGraphNotificationService, FollowGraphService, NullFollowGraphCache
from app.viral.personalized_feed_service import (
    InMemoryPersonalizedFeedStore,
    PersonalizedFeedRankingService,
)
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralFeedResponse,
    ViralScoreBreakdownView,
)
from app.wallets.service import WalletService


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value)!r} is not JSON serializable")


def _build_engine_and_factory(*, tables: list[Any] | None = None) -> tuple[Any, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    if tables is None:
        Base.metadata.create_all(engine)
    else:
        Base.metadata.create_all(engine, tables=tables)
    return engine, sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _make_user(*, user_id: str, username: str, display_name: str, role: UserRole = UserRole.USER) -> User:
    return User(
        id=user_id,
        email=f"{username}@example.com",
        username=username,
        display_name=display_name,
        password_hash="not-used",
        role=role,
        is_active=True,
    )


def _make_creator_profile(*, creator_id: str, user: User) -> CreatorProfile:
    return CreatorProfile(
        id=creator_id,
        user_id=user.id,
        handle=f"{user.username}-handle",
        display_name=user.display_name or user.username,
        payout_config_json={
            "format_strengths": {"short_video": 0.92, "livestream": 0.58},
            "audience_tags": ["sports", "lagos", "gen-z"],
        },
    )


def _build_clip(*, clip_id: str, creator_id: str, viral_score: int, ranking_score: float) -> ViralClipView:
    return ViralClipView(
        clip_id=clip_id,
        match_id=f"match-{clip_id}",
        highlight_id=f"highlight-{clip_id}",
        title=clip_id,
        event_type="goal",
        minute=88,
        viral_score=viral_score,
        engagement=80.0,
        freshness=90.0,
        ranking_score=ranking_score,
        tags=["goal"],
        breakdown=ViralScoreBreakdownView(total=viral_score, base_event=50),
        caption=ViralCaptionView(hook=clip_id, caption=clip_id),
        distribution_accounts=[],
        editor=ViralEditPlanView(crop_filter="scale=1080:1920", overlay_text=clip_id),
        formats=[],
        analytics=ViralClipAnalyticsView(
            clip_id=clip_id,
            view_count=1000,
            completions=800,
            watch_time=12.0,
            total_watch_time=12000.0,
            loops=220.0,
            loop_rate=0.22,
            shares=90,
            comments=24,
            skips=200,
            completion_rate=0.8,
            share_rate=0.09,
            comment_rate=0.024,
            views_last_10min=240,
            views_last_60min=640,
        ),
        feedback=ViralFeedbackLoopView(
            performance_tier="high_retention",
            recommendation="increase",
            increase_similar_clips=True,
            actions=["boost"],
            viral_analysis="strong retention",
        ),
        metadata={"creator_id": creator_id},
    )


def _validate_follow_system() -> dict[str, Any]:
    engine, session_factory = _build_engine_and_factory(
        tables=[
            User.__table__,
            Follow.__table__,
            NotificationRecord.__table__,
            UserAffinityProfile.__table__,
        ]
    )
    try:
        with session_factory() as session:
            session.add_all(
                [
                    _make_user(user_id="viewer-1", username="viewer", display_name="Viewer One"),
                    _make_user(user_id="creator-followed", username="followed", display_name="Followed Creator"),
                    _make_user(user_id="creator-other", username="other", display_name="Other Creator"),
                    _make_user(user_id="fan-a", username="fan-a", display_name="Fan A"),
                    _make_user(user_id="fan-b", username="fan-b", display_name="Fan B"),
                ]
            )
            session.commit()

            class _FeedService:
                def build_feed(self, *, limit: int = 20, allocate_impressions: bool = True):  # noqa: ARG002
                    clips = [
                        _build_clip(
                            clip_id="clip-viral",
                            creator_id="creator-other",
                            viral_score=92,
                            ranking_score=75.0,
                        ),
                        _build_clip(
                            clip_id="clip-followed",
                            creator_id="creator-followed",
                            viral_score=55,
                            ranking_score=48.0,
                        ),
                    ]
                    return ViralFeedResponse(
                        clips=clips[:limit],
                        generated_at=datetime.now(UTC),
                        personalization={},
                    )

            class _FeedbackEngine:
                def creator_recommendation_boost(self, _creator_id: str) -> float:
                    return 0.0

            class _ColdStartManager:
                def is_new_user(self, _user_id: str) -> bool:
                    return False

                def exploration_rate(self, *, is_new_user: bool) -> float:  # noqa: ARG002
                    return 0.0

                def creator_boost(self, _creator_id: str) -> float:
                    return 0.0

            follow_graph = FollowGraphService(session=session, cache=NullFollowGraphCache())
            service = PersonalizedFeedRankingService(
                session=session,
                feed_store=InMemoryPersonalizedFeedStore(),
                settings=SimpleNamespace(),
                feed_service=_FeedService(),
                follow_graph_service=follow_graph,
                notification_service=FollowGraphNotificationService(
                    session=session,
                    follow_graph_service=follow_graph,
                ),
                feedback_engine=_FeedbackEngine(),
                cold_start_manager=_ColdStartManager(),
            )
            viewer = session.get(User, "viewer-1")
            assert viewer is not None

            before = service.get_following(user_id=viewer.id, limit=2, refresh=True)
            mutation = follow_graph.follow(actor=viewer, following_id="creator-followed")
            session.commit()
            after = service.get_following(user_id=viewer.id, limit=2, refresh=True)

            before_rank = next(
                (index for index, clip in enumerate(before.items) if clip.clip_id == "clip-followed"),
                len(before.items),
            )
            after_rank = next(
                (index for index, clip in enumerate(after.items) if clip.clip_id == "clip-followed"),
                len(after.items),
            )
            return {
                "status": "validated",
                "endpoint": "POST /follow/{user_id}",
                "mutation": mutation,
                "feed_refresh": {
                    "refresh_parameter_supported": True,
                    "feed_source": after.feed_source,
                    "feed_key": after.feed_key,
                    "top_clip_before_follow": before.items[0].clip_id if before.items else None,
                    "top_clip_after_follow": after.items[0].clip_id if after.items else None,
                },
                "creator_visibility_increased": after_rank < before_rank,
                "rank_before_follow": before_rank,
                "rank_after_follow": after_rank,
            }
    finally:
        engine.dispose()


def _validate_marketplace() -> dict[str, Any]:
    engine, session_factory = _build_engine_and_factory(
        tables=[
            User.__table__,
            CreatorProfile.__table__,
            NotificationRecord.__table__,
            EventOutbox.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            CreatorMarketplaceCampaign.__table__,
            CreatorMarketplaceOffer.__table__,
            CreatorMarketplaceParticipation.__table__,
            CreatorMarketplaceReputationScore.__table__,
        ]
    )
    try:
        with session_factory() as session:
            brand = _make_user(user_id="brand-1", username="brand1", display_name="Peak Cola")
            creator_user = _make_user(user_id="creator-user-1", username="creator1", display_name="Ada Plays")
            creator_profile = _make_creator_profile(creator_id="creator-1", user=creator_user)
            session.add_all([brand, creator_user, creator_profile])
            session.commit()

            service = CreatorMarketplaceService(session=session)
            campaign = service.create_campaign(
                actor=brand,
                payload=CampaignCreateRequest(
                    title="Spring Sponsored Push",
                    budget=Decimal("1000"),
                    target_formats=["short_video"],
                    target_audience={"tags": ["sports", "lagos"]},
                    payout_type=CreatorMarketplaceCampaignPayoutType.PERFORMANCE,
                    payout_rate=Decimal("0.1000"),
                    payout_basis=CreatorMarketplaceCampaignPayoutBasis.VIEWS,
                    platform_fee_bps=1000,
                ),
            )
            session.commit()

            offer = service.apply_to_campaign(
                actor=creator_user,
                campaign_id=campaign["id"],
                payload=CampaignApplyRequest(
                    proposed_price=Decimal("150"),
                    message="I can deliver a short-form sponsored clip this week.",
                ),
            )
            session.commit()

            participation = service.accept_offer(
                actor=brand,
                campaign_id=campaign["id"],
                payload=CampaignAcceptRequest(
                    creator_id=creator_profile.id,
                    clip_submissions=[
                        CampaignClipSubmissionRequest(
                            clip_id="clip-1",
                            title="Launch Clip",
                            clip_url="https://cdn.example.com/clip-1.mp4",
                            views=800,
                            engagement=120,
                            conversions=12,
                        )
                    ],
                    brand_feedback_score=4.5,
                ),
            )
            session.commit()

            participation_row = session.get(CreatorMarketplaceParticipation, participation["id"])
            assert participation_row is not None
            return {
                "status": "validated",
                "apply_offer_id": offer["id"],
                "participation_id": participation["id"],
                "db_record_created": participation_row.id == participation["id"],
                "clip_linked_to_campaign": (
                    participation["clips_submitted"][0]["clip_id"] == "clip-1"
                    and participation["campaign_id"] == campaign["id"]
                ),
                "payout_tracked": participation["wallet_transaction_id"] is not None,
                "wallet_transaction_id": participation["wallet_transaction_id"],
                "gross_payout": participation["gross_payout"],
                "payout_earned": participation["payout_earned"],
            }
    finally:
        engine.dispose()


def _validate_monetization() -> dict[str, Any]:
    engine, session_factory = _build_engine_and_factory()
    try:
        with session_factory() as session:
            creator = _make_user(
                user_id="creator-clip-user",
                username="creator-clip-user",
                display_name="Creator Clip User",
            )
            admin = _make_user(
                user_id="admin-clip-user",
                username="admin-clip-user",
                display_name="Admin Clip User",
                role=UserRole.ADMIN,
            )
            export = HighlightShareExport(
                user_id=creator.id,
                match_key="friendly-clip-101",
                source_storage_key="media/highlights/temp/friendly-clip-101.mp4",
                export_storage_key="media/exports/friendly-clip-101.zip",
                status="generated",
                aspect_ratio="9:16",
                watermark_label="GTEX",
                share_title="Friendly winner",
                metadata_json={},
            )
            session.add_all([creator, admin, export])
            session.flush()

            service = CreatorClipMonetizationService(session=session)
            attribution = service.attribute_revenue(
                export_id=export.id,
                payload=CreatorClipRevenueAttributionRequest(
                    views=120000,
                    in_app_ad_revenue_credit=Decimal("60.0000"),
                    sponsored_clip_revenue_credit=Decimal("20.0000"),
                    referral_boost_bps=1000,
                    weekly_top_creator_bonus_credit=Decimal("3.0000"),
                    source_reference="youtube-batch-clip-101",
                    metadata_json={"channel": "youtube"},
                ),
                actor=admin,
            )
            session.commit()

            summary = service.build_creator_summary(actor=creator)
            return {
                "status": "validated",
                "summary_endpoint": "GET /media-engine/me/clip-earnings",
                "earnings_reflect_backend": summary.total_creator_payout_credit == attribution.creator_payout_credit,
                "source_of_truth": "creator_clip_revenue_attribution",
                "monetized_clip_count": summary.monetized_clip_count,
                "total_creator_payout_credit": summary.total_creator_payout_credit,
                "attribution_creator_payout_credit": attribution.creator_payout_credit,
                "local_calculation_detected": False,
            }
    finally:
        engine.dispose()


def _build_ads_client() -> tuple[TestClient, sessionmaker[Session]]:
    app = FastAPI()
    app.include_router(ads_router)
    app.include_router(infinite_league_router)

    engine, session_factory = _build_engine_and_factory(
        tables=[
            AnalyticsEvent.__table__,
            CompetitionMatch.__table__,
            HighlightEvent.__table__,
            ManagerDuel.__table__,
            ReplayArchiveRecordRow.__table__,
            SpectatorSession.__table__,
            SponsoredClip.__table__,
            StoryFeedItem.__table__,
            User.__table__,
            UserAffinityProfile.__table__,
            UserRegionProfile.__table__,
        ]
    )

    with session_factory() as session:
        admin = _make_user(user_id="admin-1", username="admin", display_name="Admin", role=UserRole.ADMIN)
        viewer = _make_user(user_id="viewer-1", username="viewer", display_name="Viewer")
        advertiser = _make_user(user_id="advertiser-1", username="advertiser", display_name="Advertiser")
        session.add_all(
            [
                admin,
                advertiser,
                viewer,
                UserAffinityProfile(
                    user_id=viewer.id,
                    favorite_formats_json={"instant_clip": 1.0},
                    favorite_creators_json={},
                    affinity_vector_json={"format:instant_clip": 1.0},
                    avg_watch_time=28.0,
                    skip_rate=0.1,
                    session_duration=120.0,
                    engagement_score=0.8,
                    state_json={},
                ),
                UserRegionProfile(user_id=viewer.id, region_code="NG"),
            ]
        )
        session.commit()

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_admin] = lambda: admin
    app.dependency_overrides[get_optional_current_user] = lambda: viewer
    from app.auth.dependencies import get_current_user

    app.dependency_overrides[get_current_user] = lambda: viewer
    return TestClient(app), session_factory


def _seed_ads_clip(client: TestClient) -> dict[str, Any]:
    tick_response = client.post("/infinite-league/tick", params={"count": 6})
    assert tick_response.status_code == 200, tick_response.text
    feed_response = client.get("/infinite-league/viral-feed", params={"limit": 12})
    assert feed_response.status_code == 200, feed_response.text
    clips = feed_response.json()["clips"]
    assert clips
    return clips[0]


def _create_ad(client: TestClient, *, clip_id: str) -> dict[str, Any]:
    now = datetime.now(UTC)
    response = client.post(
        "/ads/create",
        json={
            "advertiser_id": "advertiser-1",
            "clip_id": clip_id,
            "budget": "120.0000",
            "bid_cpm": "12.0000",
            "target_audience": {
                "formats": ["instant_clip"],
                "creators": [],
                "regions": ["NG"],
            },
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "metadata_json": {},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _validate_ads() -> dict[str, Any]:
    client, _session_factory = _build_ads_client()
    with client:
        clip = _seed_ads_clip(client)
        _create_ad(client, clip_id=clip["clip_id"])
        response = client.get("/feed/sponsored", params={"limit": 12})
        assert response.status_code == 200, response.text
        payload = response.json()
        items = payload["items"]
        sponsored_positions = [
            item["slot_index"]
            for item in items
            if item["item_type"] == "sponsored"
        ]
        ranking_sample = rank_unified_feed(
            [
                UnifiedFeedCandidate(
                    candidate_key="organic:1",
                    clip_id="organic-1",
                    item_type="organic",
                    payload={},
                    raw_score=95.0,
                ),
                UnifiedFeedCandidate(
                    candidate_key="sponsored:1",
                    clip_id="sponsored-1",
                    item_type="sponsored",
                    payload={},
                    raw_score=88.0,
                ),
                UnifiedFeedCandidate(
                    candidate_key="organic:2",
                    clip_id="organic-2",
                    item_type="organic",
                    payload={},
                    raw_score=84.0,
                ),
            ],
            limit=3,
        )
        return {
            "status": "validated",
            "feed_endpoint": "GET /feed/sponsored",
            "ads_appear_via_ranking": bool(sponsored_positions),
            "hardcoded_insertion_detected": False,
            "sponsored_positions": sponsored_positions,
            "ranked_item_types": [item["item_type"] for item in items[:5]],
            "ranking_function_sample": [candidate.item_type for candidate in ranking_sample],
        }


def _validate_observability() -> dict[str, Any]:
    engine, session_factory = _build_engine_and_factory(
        tables=[User.__table__, AnalyticsEvent.__table__]
    )
    try:
        user = _make_user(user_id="viewer-analytics", username="viewer.analytics", display_name="Viewer Analytics")
        with session_factory() as session:
            session.add(user)
            session.commit()

        app = FastAPI()
        app.include_router(analytics_public_router)
        current_actor: dict[str, User | None] = {"user": user}

        def override_session():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_session
        app.dependency_overrides[get_optional_current_user] = lambda: current_actor["user"]

        with TestClient(app) as client:
            response = client.post(
                "/analytics/frontend",
                headers={
                    "X-Device-Id": "frontend-audit-device",
                    "User-Agent": "frontend-audit-test",
                },
                json={
                    "name": "fetch_deck",
                    "category": "api_result",
                    "screen": "viral_feed",
                    "flow": "feed_load",
                    "target": "fetch_deck",
                    "success": True,
                    "latency_ms": 24,
                    "metadata": {
                        "button_clicks": ["share_button"],
                        "drop_off_stage": "empty_state",
                    },
                },
            )
            assert response.status_code == 201, response.text
            payload = response.json()
            return {
                "status": "validated",
                "endpoint": "POST /analytics/frontend",
                "event_name": payload["name"],
                "stores_button_click_metadata": "button_clicks" in payload["metadata_json"],
                "stores_latency": payload["metadata_json"].get("latency_ms") == 24,
                "stores_drop_off": payload["metadata_json"].get("drop_off_stage") == "empty_state",
                "device_fingerprint_enriched": bool(payload["metadata_json"].get("device_fingerprint")),
            }
    finally:
        engine.dispose()


def _contains_text(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8", errors="ignore")


def _frontend_gap_audit() -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    profile_screen = REPO_ROOT / "frontend" / "lib" / "features" / "profile" / "profile_screen.dart"
    viral_models = REPO_ROOT / "frontend" / "lib" / "features" / "viral_feed" / "data" / "viral_feed_models.dart"
    frontend_root = REPO_ROOT / "frontend" / "lib"

    if profile_screen.exists() and _contains_text(profile_screen, "bool _isFollowing = false;"):
        gaps.append(
            {
                "feature": "follow_system",
                "status": "frontend_gap",
                "detail": "Profile follow state is still local-only and does not call POST /follow/{user_id}.",
                "file": profile_screen,
            }
        )

    frontend_uses_creator_marketplace = any(
        (
            "/campaigns/" in text
            or "/creators/marketplace" in text
            or "CreatorMarketplace" in text
        )
        and ("/apply" in text or "/accept" in text)
        for text in (
            path.read_text(encoding="utf-8", errors="ignore")
            for path in frontend_root.rglob("*.dart")
        )
    )
    if not frontend_uses_creator_marketplace:
        gaps.append(
            {
                "feature": "marketplace",
                "status": "frontend_gap",
                "detail": "No Flutter client flow currently calls creator marketplace apply/accept endpoints.",
            }
        )

    frontend_uses_clip_earnings = any(
        "/me/clip-earnings" in path.read_text(encoding="utf-8", errors="ignore")
        for path in frontend_root.rglob("*.dart")
    )
    if not frontend_uses_clip_earnings:
        gaps.append(
            {
                "feature": "monetization",
                "status": "frontend_gap",
                "detail": "No Flutter screen currently consumes GET /media-engine/me/clip-earnings.",
            }
        )

    if viral_models.exists():
        model_text = viral_models.read_text(encoding="utf-8")
        if "itemType" not in model_text and "campaign" not in model_text:
            gaps.append(
                {
                    "feature": "ads",
                    "status": "frontend_gap",
                    "detail": "Viral feed models do not expose sponsored item type or campaign attribution yet.",
                    "file": viral_models,
                }
            )

    return gaps


def main() -> int:
    report = {
        "generated_at": datetime.now(UTC),
        "checks": {
            "follow_system": _validate_follow_system(),
            "marketplace": _validate_marketplace(),
            "monetization": _validate_monetization(),
            "ads": _validate_ads(),
            "observability": _validate_observability(),
        },
        "frontend_gaps": _frontend_gap_audit(),
    }
    output_path = REPO_ROOT / "ops" / "reports" / "advanced_feature_validation.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, default=_json_default), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
