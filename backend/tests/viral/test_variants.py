from __future__ import annotations

import random

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.clip_variant import ClipVariant
from app.viral.comparator import ViralVariantScoringComparator
from app.viral.promotion import ViralClipPromotionService


def _session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[ClipVariant.__table__])
    return sessionmaker(bind=engine, expire_on_commit=False)


def test_promotion_service_uses_epsilon_greedy_delivery_before_winner_lock() -> None:
    session_factory = _session_factory()
    comparator = ViralVariantScoringComparator()

    with session_factory() as session:
        session.add_all(
            [
                ClipVariant(
                    variant_id="clip::instant",
                    base_clip_id="clip",
                    format_type="instant",
                    view_count=900,
                    watch_time=14.0,
                    loop_rate=0.24,
                    shares=72,
                    comments=18,
                    completion_rate=0.84,
                    share_rate=0.08,
                    comment_rate=0.02,
                ),
                ClipVariant(
                    variant_id="clip::cinematic",
                    base_clip_id="clip",
                    format_type="cinematic",
                    view_count=620,
                    watch_time=13.5,
                    loop_rate=0.14,
                    shares=20,
                    comments=9,
                    completion_rate=0.71,
                    share_rate=0.0323,
                    comment_rate=0.0145,
                ),
                ClipVariant(
                    variant_id="clip::meme",
                    base_clip_id="clip",
                    format_type="meme",
                    view_count=580,
                    watch_time=11.0,
                    loop_rate=0.18,
                    shares=26,
                    comments=8,
                    completion_rate=0.68,
                    share_rate=0.0448,
                    comment_rate=0.0137,
                ),
            ]
        )
        session.commit()

        service = ViralClipPromotionService(session=session, comparator=comparator)
        decision = service.refresh("clip")

        assert decision.resolved is False
        leading_variant = session.get(ClipVariant, decision.leading_variant_id)
        assert leading_variant is not None
        assert leading_variant.distribution_weight == 0.8

        exploratory_choice = service.select_delivery_variant("clip", random_source=random.Random(0))
        exploit_choice = service.select_delivery_variant("clip", random_source=random.Random(1))

        assert exploratory_choice is not None
        assert exploratory_choice.variant_id != decision.leading_variant_id
        assert exploit_choice is not None
        assert exploit_choice.variant_id == decision.leading_variant_id
