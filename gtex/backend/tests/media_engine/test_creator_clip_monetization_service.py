from __future__ import annotations

from decimal import Decimal

import app.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.media_engine.schemas import CreatorClipRevenueAttributionRequest
from app.models.base import Base
from app.models.highlight_share import HighlightShareExport
from app.models.user import User, UserRole
from app.models.wallet import LedgerUnit
from app.services.creator_clip_monetization_service import CreatorClipMonetizationService
from app.viral.trust import InMemoryTrustStateStore, TrustFactorBreakdown, TrustScoreService, TrustState
from app.wallets.service import WalletService


def _session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return engine, SessionLocal


def _create_user(session, *, user_id: str, role: UserRole = UserRole.USER) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        role=role,
    )
    session.add(user)
    session.flush()
    return user


def test_creator_clip_revenue_attribution_credits_wallets_and_is_idempotent() -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        creator = _create_user(session, user_id="creator-clip-user")
        admin = _create_user(session, user_id="admin-clip-user", role=UserRole.ADMIN)
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
        session.add(export)
        session.flush()

        service = CreatorClipMonetizationService(session=session)
        payload = CreatorClipRevenueAttributionRequest(
            views=120000,
            in_app_ad_revenue_credit=Decimal("60.0000"),
            sponsored_clip_revenue_credit=Decimal("20.0000"),
            referral_boost_bps=1000,
            weekly_top_creator_bonus_credit=Decimal("3.0000"),
            source_reference="youtube-batch-clip-101",
            metadata_json={"channel": "youtube"},
        )

        attribution = service.attribute_revenue(export_id=export.id, payload=payload, actor=admin)
        duplicate = service.attribute_revenue(export_id=export.id, payload=payload, actor=admin)
        wallet_service = WalletService()
        creator_account = wallet_service.get_user_account(session, creator, LedgerUnit.CREDIT)
        treasury_account = wallet_service.ensure_treasury_account(session, LedgerUnit.CREDIT)
        rewards_account = wallet_service.ensure_rewards_pool_account(session, LedgerUnit.CREDIT)
        summary = service.build_creator_summary(actor=creator)

        assert duplicate.id == attribution.id
        assert attribution.gross_revenue_credit == Decimal("80.0000")
        assert attribution.creator_base_share_credit == Decimal("40.0000")
        assert attribution.platform_share_credit == Decimal("24.0000")
        assert attribution.growth_pool_share_credit == Decimal("16.0000")
        assert attribution.viral_bonus_credit == Decimal("4.0000")
        assert attribution.referral_bonus_credit == Decimal("1.6000")
        assert attribution.weekly_top_creator_bonus_credit == Decimal("3.0000")
        assert attribution.creator_payout_credit == Decimal("48.6000")
        assert attribution.growth_pool_retained_credit == Decimal("7.4000")
        assert attribution.is_viral is True
        assert wallet_service.get_balance(session, creator_account) == Decimal("48.6000")
        assert wallet_service.get_balance(session, treasury_account) == Decimal("24.0000")
        assert wallet_service.get_balance(session, rewards_account) == Decimal("7.4000")
        assert summary.generated_clip_count == 1
        assert summary.monetized_clip_count == 1
        assert summary.total_views == 120000
        assert summary.total_creator_payout_credit == Decimal("48.6000")
        assert summary.total_viral_bonus_credit == Decimal("4.0000")

    engine.dispose()


def test_creator_clip_revenue_attribution_blocks_shadow_banned_creators() -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        creator = _create_user(session, user_id="creator-shadow-banned")
        admin = _create_user(session, user_id="admin-shadow-banned", role=UserRole.ADMIN)
        export = HighlightShareExport(
            user_id=creator.id,
            match_key="friendly-clip-shadow",
            source_storage_key="media/highlights/temp/friendly-clip-shadow.mp4",
            export_storage_key="media/exports/friendly-clip-shadow.zip",
            status="generated",
            aspect_ratio="9:16",
            watermark_label="GTEX",
            share_title="Shadow banned clip",
            metadata_json={},
        )
        session.add(export)
        session.flush()

        trust_store = InMemoryTrustStateStore()
        trust_store.save_trust_state(
            TrustState(
                user_id=creator.id,
                trust_score=0.1,
                suspicious_event_count=5,
                healthy_event_count=0,
                shadow_banned=True,
                monetization_eligible=False,
                ranking_eligible=False,
                suspicious_flags=("abnormal_device_ip_cluster_spike",),
                factors=TrustFactorBreakdown(
                    account_age=0.2,
                    session_consistency=0.1,
                    device_fingerprint_stability=0.1,
                    engagement_authenticity=0.1,
                    anomaly_detection=0.1,
                ),
                updated_at=creator.updated_at,
            )
        )
        service = CreatorClipMonetizationService(
            session=session,
            trust_service=TrustScoreService(store=trust_store),
        )
        payload = CreatorClipRevenueAttributionRequest(
            views=1200,
            in_app_ad_revenue_credit=Decimal("5.0000"),
        )

        with pytest.raises(Exception) as exc_info:
            service.attribute_revenue(export_id=export.id, payload=payload, actor=admin)

        assert "trust score is too low" in str(exc_info.value).lower()

    engine.dispose()


def test_creator_clip_revenue_attribution_rejects_low_clip_trust_payout() -> None:
    engine, SessionLocal = _session()
    with SessionLocal() as session:
        creator = _create_user(session, user_id="creator-low-clip-trust")
        admin = _create_user(session, user_id="admin-low-clip-trust", role=UserRole.ADMIN)
        export = HighlightShareExport(
            user_id=creator.id,
            match_key="friendly-clip-low-trust",
            source_storage_key="media/highlights/temp/friendly-clip-low-trust.mp4",
            export_storage_key="media/exports/friendly-clip-low-trust.zip",
            status="generated",
            aspect_ratio="9:16",
            watermark_label="GTEX",
            share_title="Low trust clip",
            metadata_json={},
        )
        session.add(export)
        session.flush()

        service = CreatorClipMonetizationService(session=session)
        payload = CreatorClipRevenueAttributionRequest(
            clip_id="clip-low-trust-1",
            views=50000,
            in_app_ad_revenue_credit=Decimal("40.0000"),
            avg_trust_score=0.5,
            clip_trust_score=0.25,
            metadata_json={"channel": "youtube"},
        )

        attribution = service.attribute_revenue(export_id=export.id, payload=payload, actor=admin)
        wallet_service = WalletService()
        creator_account = wallet_service.get_user_account(session, creator, LedgerUnit.CREDIT)

        assert attribution.gross_revenue_credit == Decimal("0.0000")
        assert attribution.creator_payout_credit == Decimal("0.0000")
        assert attribution.is_viral is False
        assert attribution.metadata_json["trust_rejected"] is True
        assert attribution.metadata_json["clip_trust_score"] == "0.2500"
        assert attribution.metadata_json["avg_trust_score"] == "0.5000"
        assert wallet_service.get_balance(session, creator_account) == Decimal("0.0000")

    engine.dispose()
