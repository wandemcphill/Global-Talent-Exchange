from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.analytics_event import AnalyticsEvent
from app.models.base import Base
from app.models.creator_profile import CreatorProfile
from app.models.user_affinity_profile import UserAffinityProfile
from app.viral.cold_start import ColdStartManager


def _build_session_factory() -> sessionmaker[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            AnalyticsEvent.__table__,
            CreatorProfile.__table__,
            UserAffinityProfile.__table__,
        ],
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def test_cold_start_manager_applies_new_user_and_new_creator_rules() -> None:
    session_factory = _build_session_factory()
    with session_factory() as session:
        session.add(
            CreatorProfile(
                id="creator-new",
                user_id="creator-user-new",
                handle="creator-new",
                display_name="Creator New",
                payout_config_json={},
            )
        )
        session.add(
            CreatorProfile(
                id="creator-established",
                user_id="creator-user-established",
                handle="creator-established",
                display_name="Creator Established",
                payout_config_json={
                    "feedback_engine": {
                        "published_campaign_clips": 4,
                        "future_distribution_weight": 1.25,
                    }
                },
            )
        )
        session.add(
            UserAffinityProfile(
                user_id="viewer-established",
                state_json={"event_counts": {"clip.view": 5}},
            )
        )
        session.add_all(
            [
                AnalyticsEvent(name="clip.view", user_id="viewer-established", metadata_json={"clip_id": "clip-a"}),
                AnalyticsEvent(name="clip.view", user_id="viewer-established", metadata_json={"clip_id": "clip-b"}),
                AnalyticsEvent(name="clip.view", user_id="viewer-established", metadata_json={"clip_id": "clip-c"}),
                AnalyticsEvent(name="clip.view", user_id="viewer-established", metadata_json={"clip_id": "clip-d"}),
                AnalyticsEvent(name="clip.view", user_id="viewer-established", metadata_json={"clip_id": "clip-e"}),
            ]
        )
        session.commit()

        manager = ColdStartManager(session=session)

        assert manager.is_new_user("viewer-new") is True
        assert manager.is_new_user("viewer-established") is False
        assert manager.exploration_rate(is_new_user=True) == 0.5
        assert manager.exploration_rate(is_new_user=False) == 0.0

        initial_floor = manager.initial_impression_floor(clip_id="clip-cold", observed_views=0)
        assert 200 <= initial_floor <= 500
        assert manager.initial_impression_floor(clip_id="clip-cold", observed_views=500) == 0

        assert manager.creator_boost("creator-new") == 0.15
        assert manager.creator_boost("creator-established") == 0.0
