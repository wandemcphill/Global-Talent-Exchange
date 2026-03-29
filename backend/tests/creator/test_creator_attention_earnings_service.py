from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.creator_attention_earnings import ClipEarningsLog, CreatorWallet
from app.models.user import User, UserRole
from app.services.creator_attention_earnings_service import CreatorAttentionEarningsService


class _FakeCache:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_delta(self, **payload) -> None:
        self.events.append(payload)


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine)
    CreatorWallet.__table__.create(bind=engine)
    ClipEarningsLog.__table__.create(bind=engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_creator_attention_earnings_updates_wallet_and_defers_cache_until_commit() -> None:
    session_factory = _build_session_factory()
    cache = _FakeCache()

    with session_factory() as session:
        creator = User(
            id="creator-earnings-1",
            email="creator-earnings-1@example.com",
            username="creator_earnings_1",
            password_hash="hashed",
            role=UserRole.USER,
        )
        viewer = User(
            id="viewer-earnings-1",
            email="viewer-earnings-1@example.com",
            username="viewer_earnings_1",
            password_hash="hashed",
            role=UserRole.USER,
        )
        session.add_all([creator, viewer])
        session.commit()

    with session_factory() as session:
        service = CreatorAttentionEarningsService(session=session, cache=cache)
        clip = SimpleNamespace(
            clip_id="clip-earn-1",
            match_id="match-earn-1",
            metadata={"creator_user_id": "creator-earnings-1"},
        )

        impression = service.track_impression(
            clip=clip,
            viewer_user_id="viewer-earnings-1",
            feed_source="personalized_feed",
            reference_key="creator-attention:test-impression",
        )
        duplicate_impression = service.track_impression(
            clip=clip,
            viewer_user_id="viewer-earnings-1",
            feed_source="personalized_feed",
            reference_key="creator-attention:test-impression",
        )
        like = service.track_engagement_event(
            name="clip.like",
            clip_id="clip-earn-1",
            viewer_user_id="viewer-earnings-1",
            metadata={"creator_id": "creator-earnings-1"},
            reference_key="creator-attention:test-like",
        )
        share = service.track_engagement_event(
            name="clip.share",
            clip_id="clip-earn-1",
            viewer_user_id="viewer-earnings-1",
            metadata={"creator_id": "creator-earnings-1"},
            reference_key="creator-attention:test-share",
        )

        assert impression is not None
        assert duplicate_impression is not None
        assert duplicate_impression.id == impression.id
        assert like is not None
        assert share is not None
        assert cache.events == []

        wallet = session.scalar(
            select(CreatorWallet).where(CreatorWallet.creator_user_id == "creator-earnings-1")
        )
        logs = list(session.scalars(select(ClipEarningsLog).order_by(ClipEarningsLog.created_at)).all())

        assert wallet is not None
        assert wallet.total_impressions == 1
        assert wallet.total_likes == 1
        assert wallet.total_shares == 1
        assert wallet.total_earnings_credit == Decimal("0.0370")
        assert wallet.available_balance_credit == Decimal("0.0370")
        assert len(logs) == 3
        assert sum(log.impression_delta for log in logs) == 1
        assert sum(log.like_delta for log in logs) == 1
        assert sum(log.share_delta for log in logs) == 1

        session.commit()

    assert len(cache.events) == 3
    assert sum(int(event["impression_delta"]) for event in cache.events) == 1
    assert sum(int(event["like_delta"]) for event in cache.events) == 1
    assert sum(int(event["share_delta"]) for event in cache.events) == 1
