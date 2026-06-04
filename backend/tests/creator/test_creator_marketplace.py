from __future__ import annotations

from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth.dependencies import get_current_user, get_session
from app.core.trust_middleware import SharedTrustMiddleware
from app.creator_marketplace.router import router as creator_marketplace_router
from app.creator_marketplace.schemas import (
    CampaignAcceptRequest,
    CampaignApplyRequest,
    CampaignClipSubmissionRequest,
    CampaignCreateRequest,
)
from app.creator_marketplace.service import CreatorMarketplaceService
from app.models.base import Base
from app.models.creator_marketplace import (
    CreatorMarketplaceCampaign,
    CreatorMarketplaceCampaignPayoutBasis,
    CreatorMarketplaceCampaignPayoutType,
    CreatorMarketplaceOffer,
    CreatorMarketplaceParticipation,
    CreatorMarketplaceReputationScore,
)
from app.models.event_backbone import EventOutbox
from app.models.creator_profile import CreatorProfile
from app.models.notification_record import NotificationRecord
from app.models.risk_ops import AuditLog
from app.models.user import User, UserRole
from app.models.wallet import LedgerAccount, LedgerBalanceProjection, LedgerEntry, LedgerTransaction, LedgerUnit
from app.viral.trust import InMemoryTrustStateStore, TrustFactorBreakdown, TrustScoreService, TrustState
from app.wallets.service import WalletService


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            CreatorProfile.__table__,
            NotificationRecord.__table__,
            EventOutbox.__table__,
            LedgerAccount.__table__,
            LedgerTransaction.__table__,
            LedgerEntry.__table__,
            LedgerBalanceProjection.__table__,
            AuditLog.__table__,
            CreatorMarketplaceCampaign.__table__,
            CreatorMarketplaceOffer.__table__,
            CreatorMarketplaceParticipation.__table__,
            CreatorMarketplaceReputationScore.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _make_user(*, user_id: str, username: str, display_name: str) -> User:
    return User(
        id=user_id,
        email=f"{username}@example.com",
        username=username,
        display_name=display_name,
        password_hash="not-used",
        role=UserRole.USER,
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


def test_creator_marketplace_service_settles_payouts_and_updates_reputation() -> None:
    session_factory = _build_session_factory()
    with session_factory() as session:
        brand = _make_user(user_id="brand-1", username="brand1", display_name="Peak Cola")
        creator_user = _make_user(user_id="creator-user-1", username="creator1", display_name="Ada Plays")
        creator_profile = _make_creator_profile(creator_id="creator-1", user=creator_user)
        session.add_all([brand, creator_user, creator_profile])
        session.commit()

        service = CreatorMarketplaceService(session=session)
        created_campaign = service.create_campaign(
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

        marketplace = service.list_creator_marketplace(actor=creator_user)
        assert marketplace
        assert marketplace[0]["campaign"]["id"] == created_campaign["id"]
        assert marketplace[0]["match_score"] > 70

        offer = service.apply_to_campaign(
            actor=creator_user,
            campaign_id=created_campaign["id"],
            payload=CampaignApplyRequest(
                proposed_price=Decimal("150"),
                message="I can deliver a short-form sponsored clip this week.",
            ),
        )
        session.commit()

        participation = service.accept_offer(
            actor=brand,
            campaign_id=created_campaign["id"],
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

        wallet_service = WalletService()
        creator_account = wallet_service.get_user_account(session, creator_user, LedgerUnit.CREDIT)
        treasury_account = wallet_service.ensure_treasury_account(session, LedgerUnit.CREDIT)
        revenue_account = wallet_service.ensure_creator_clip_revenue_account(session, LedgerUnit.CREDIT)

        assert wallet_service.get_balance(session, creator_account) == Decimal("72.0000")
        assert wallet_service.get_balance(session, treasury_account) == Decimal("8.0000")
        assert wallet_service.get_balance(session, revenue_account) == Decimal("-80.0000")

        assert participation["performance_metrics"]["views"] == 800
        assert participation["performance_metrics"]["engagement"] == 120
        assert participation["performance_metrics"]["conversions"] == 12
        assert participation["clips_submitted"][0]["is_sponsored"] is True
        assert participation["clips_submitted"][0]["ads_engine"]["placement_type"] == "sponsored_highlight"
        assert Decimal(str(participation["gross_payout"])) == Decimal("80.0000")
        assert Decimal(str(participation["payout_earned"])) == Decimal("72.0000")
        assert Decimal(str(participation["platform_fee_amount"])) == Decimal("8.0000")

        reputation = service.get_creator_reputation_view(actor=creator_user)
        assert reputation["creator_reputation_score"] > 70
        assert reputation["completed_campaigns"] == 1

        performance = service.get_campaign_performance(actor=brand, campaign_id=created_campaign["id"])
        assert performance["totals"]["views"] == 800
        assert performance["totals"]["engagement"] == 120
        assert performance["totals"]["conversions"] == 12
        assert performance["totals"]["sponsored_clips_injected"] == 1
        assert Decimal(str(performance["totals"]["payout_earned"])) == Decimal("72.0000")

        notifications = session.scalars(select(NotificationRecord).order_by(NotificationRecord.created_at.asc())).all()
        template_keys = {item.template_key for item in notifications}
        assert "creator_marketplace.campaign_match" in template_keys
        assert "creator_marketplace.offer_accepted" in template_keys
        assert "creator_marketplace.payout_completed" in template_keys
        assert offer["match_score"] > 70


def test_creator_marketplace_zeroes_payouts_for_low_trust_creators() -> None:
    session_factory = _build_session_factory()
    with session_factory() as session:
        brand = _make_user(user_id="brand-low-trust", username="brand-low-trust", display_name="Peak Cola")
        creator_user = _make_user(
            user_id="creator-user-low-trust", username="creator-low-trust", display_name="Ada Plays"
        )
        creator_profile = _make_creator_profile(creator_id="creator-low-trust", user=creator_user)
        session.add_all([brand, creator_user, creator_profile])
        session.commit()

        trust_store = InMemoryTrustStateStore()
        trust_store.save_trust_state(
            TrustState(
                user_id=creator_user.id,
                trust_score=0.1,
                suspicious_event_count=4,
                healthy_event_count=0,
                shadow_banned=False,
                monetization_eligible=False,
                ranking_eligible=False,
                suspicious_flags=("creator_marketplace_gate",),
                factors=TrustFactorBreakdown(
                    account_age=0.2,
                    session_consistency=0.2,
                    device_fingerprint_stability=0.2,
                    engagement_authenticity=0.2,
                    anomaly_detection=0.2,
                ),
                updated_at=creator_user.updated_at,
            )
        )
        service = CreatorMarketplaceService(
            session=session,
            trust_middleware=SharedTrustMiddleware(
                session=session,
                trust_service=TrustScoreService(store=trust_store),
            ),
        )
        created_campaign = service.create_campaign(
            actor=brand,
            payload=CampaignCreateRequest(
                title="Trust Gate Campaign",
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

        service.apply_to_campaign(
            actor=creator_user,
            campaign_id=created_campaign["id"],
            payload=CampaignApplyRequest(
                proposed_price=Decimal("150"),
                message="I can deliver a short-form sponsored clip this week.",
            ),
        )
        session.commit()

        participation = service.accept_offer(
            actor=brand,
            campaign_id=created_campaign["id"],
            payload=CampaignAcceptRequest(
                creator_id=creator_profile.id,
                clip_submissions=[
                    CampaignClipSubmissionRequest(
                        clip_id="clip-low-trust",
                        title="Trust Gated Clip",
                        clip_url="https://cdn.example.com/clip-low-trust.mp4",
                        views=800,
                        engagement=120,
                        conversions=12,
                    )
                ],
                brand_feedback_score=4.5,
            ),
        )
        session.commit()

        assert Decimal(str(participation["gross_payout"])) == Decimal("0.0000")
        assert Decimal(str(participation["payout_earned"])) == Decimal("0.0000")
        assert Decimal(str(participation["platform_fee_amount"])) == Decimal("0.0000")
        assert participation["wallet_transaction_id"] is None
        assert participation["performance_metrics"]["trust_blocked"] is True


def test_creator_marketplace_router_supports_end_to_end_flow() -> None:
    session_factory = _build_session_factory()
    with session_factory() as seed_session:
        brand = _make_user(user_id="brand-2", username="brand2", display_name="Spark Drink")
        creator_user = _make_user(user_id="creator-user-2", username="creator2", display_name="Bola Streams")
        creator_profile = _make_creator_profile(creator_id="creator-2", user=creator_user)
        seed_session.add_all([brand, creator_user, creator_profile])
        seed_session.commit()

    app = FastAPI()
    app.include_router(creator_marketplace_router)
    app.include_router(creator_marketplace_router, prefix="/api")
    current_actor = {"user": brand}

    def override_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = lambda: current_actor["user"]

    with TestClient(app) as client:
        create_response = client.post(
            "/api/campaigns/create",
            json={
                "title": "Creator Router Launch",
                "budget": "500",
                "target_formats": ["short_video"],
                "target_audience": {"tags": ["sports", "lagos"]},
                "payout_type": "fixed",
                "payout_rate": "0",
                "payout_basis": "views",
                "platform_fee_bps": 1000,
                "status": "open",
            },
        )

        assert create_response.status_code == 201
        campaign_id = create_response.json()["id"]

        current_actor["user"] = creator_user
        marketplace_response = client.get("/api/creators/marketplace")
        assert marketplace_response.status_code == 200
        assert marketplace_response.json()[0]["campaign"]["id"] == campaign_id

        apply_response = client.post(
            f"/api/campaigns/{campaign_id}/apply",
            json={
                "proposed_price": "120",
                "message": "Ready to publish a sponsored launch clip.",
            },
        )
        assert apply_response.status_code == 201

        current_actor["user"] = brand
        accept_response = client.post(
            f"/api/campaigns/{campaign_id}/accept",
            json={
                "creator_id": creator_profile.id,
                "agreed_price": "120",
                "clip_submissions": [
                    {
                        "clip_id": "clip-router-1",
                        "title": "Sponsored Router Clip",
                        "views": 400,
                        "engagement": 60,
                        "conversions": 4,
                    }
                ],
                "brand_feedback_score": 4.0,
            },
        )
        assert accept_response.status_code == 200
        assert Decimal(accept_response.json()["payout_earned"]) == Decimal("108.0000")

        performance_response = client.get(f"/api/campaigns/{campaign_id}/performance")
        assert performance_response.status_code == 200
        assert performance_response.json()["totals"]["views"] == 400

        current_actor["user"] = creator_user
        reputation_response = client.get("/api/creators/me/reputation")
        assert reputation_response.status_code == 200
        assert reputation_response.json()["completed_campaigns"] == 1
