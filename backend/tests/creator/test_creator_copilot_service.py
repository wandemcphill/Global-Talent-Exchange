from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.copilot.copilot_service import CreatorCopilotService
from app.copilot.strategy_builder import CopilotStrategyBuilder
from app.media_engine.schemas import CreatorClipRevenueAttributionRequest
from app.models.base import Base
from app.models.clip_variant import ClipVariant
from app.models.highlight_share import HighlightShareExport
from app.models.user import User
from app.models.user_affinity_profile import UserAffinityProfile
from app.services.creator_clip_monetization_service import CreatorClipMonetizationService


class MemoryCacheBackend:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        _ = ttl_seconds
        self.values[key] = value

    def delete_many(self, keys: list[str]) -> None:
        for key in keys:
            self.values.pop(key, None)

    def ping(self) -> bool:
        return True


def _create_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    return SessionLocal()


def _create_user(session, *, user_id: str) -> User:
    user = User(
        id=user_id,
        email=f"{user_id}@example.com",
        username=user_id,
        password_hash="hashed",
        phone_number="1234567890",
    )
    session.add(user)
    session.flush()
    return user


def _create_export(session, *, user_id: str, export_id: str, title: str) -> HighlightShareExport:
    export = HighlightShareExport(
        id=export_id,
        user_id=user_id,
        match_key=f"match-{export_id}",
        source_storage_key=f"media/highlights/temp/{export_id}.mp4",
        export_storage_key=f"media/exports/{export_id}.zip",
        status="generated",
        aspect_ratio="9:16",
        watermark_label="GTEX",
        share_title=title,
        metadata_json={},
    )
    session.add(export)
    session.flush()
    return export


def _attribute_clip(
    session,
    *,
    export_id: str,
    views: int,
    source_reference: str,
    clip_format: str,
    duration_seconds: int,
    completion_rate: float,
    share_rate: float,
    loop_rate: float,
    hook_style: str,
    audience_cluster: str,
    force_viral_bonus: bool,
) -> None:
    CreatorClipMonetizationService(session).attribute_revenue(
        export_id=export_id,
        payload=CreatorClipRevenueAttributionRequest(
            views=views,
            source_reference=source_reference,
            force_viral_bonus=force_viral_bonus,
            metadata_json={
                "format": clip_format,
                "duration_seconds": duration_seconds,
                "completion_rate": completion_rate,
                "share_rate": share_rate,
                "loop_rate": loop_rate,
                "hook_style": hook_style,
                "audience_cluster": audience_cluster,
                "event_type": "analysis",
                "tags": ["breakdown", "final"],
            },
        ),
    )


def test_creator_copilot_service_generates_prediction_strategy_and_cached_profile() -> None:
    session = _create_session()
    try:
        creator = _create_user(session, user_id="creator-copilot")
        _create_export(session, user_id=creator.id, export_id="export-1", title="Debate clip one")
        _create_export(session, user_id=creator.id, export_id="export-2", title="Debate clip two")
        _create_export(session, user_id=creator.id, export_id="export-3", title="Meme clip")

        _attribute_clip(
            session,
            export_id="export-1",
            views=180000,
            source_reference="source-1",
            clip_format="debate",
            duration_seconds=18,
            completion_rate=0.91,
            share_rate=0.068,
            loop_rate=0.24,
            hook_style="fast-start",
            audience_cluster="debate-core",
            force_viral_bonus=True,
        )
        _attribute_clip(
            session,
            export_id="export-2",
            views=135000,
            source_reference="source-2",
            clip_format="debate",
            duration_seconds=20,
            completion_rate=0.87,
            share_rate=0.052,
            loop_rate=0.2,
            hook_style="fast-start",
            audience_cluster="debate-core",
            force_viral_bonus=True,
        )
        _attribute_clip(
            session,
            export_id="export-3",
            views=42000,
            source_reference="source-3",
            clip_format="meme",
            duration_seconds=30,
            completion_rate=0.58,
            share_rate=0.012,
            loop_rate=0.08,
            hook_style="slow-build",
            audience_cluster="casual-fans",
            force_viral_bonus=False,
        )

        session.add(
            UserAffinityProfile(
                user_id=creator.id,
                favorite_formats_json={"debate": 0.92, "tactical": 0.61},
                favorite_creators_json={},
                affinity_vector_json={"debate": 0.88},
                avg_watch_time=18.0,
                skip_rate=0.14,
                session_duration=540.0,
                engagement_score=0.79,
                state_json={"audience_cluster": "debate-core"},
            )
        )
        session.add_all(
            [
                ClipVariant(
                    variant_id="match-1::highlight-1::debate",
                    base_clip_id="match-1::highlight-1",
                    format_type="debate",
                    view_count=900,
                    watch_time=740.0,
                    loop_rate=0.22,
                    shares=62,
                    comments=40,
                    completion_rate=0.82,
                    share_rate=0.068,
                    comment_rate=0.044,
                    viral_score=86.0,
                    is_winner=True,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-2::highlight-2::debate",
                    base_clip_id="match-2::highlight-2",
                    format_type="debate",
                    view_count=820,
                    watch_time=690.0,
                    loop_rate=0.2,
                    shares=57,
                    comments=33,
                    completion_rate=0.78,
                    share_rate=0.061,
                    comment_rate=0.036,
                    viral_score=79.0,
                    is_winner=True,
                    metadata_json={},
                ),
                ClipVariant(
                    variant_id="match-3::highlight-3::instant",
                    base_clip_id="match-3::highlight-3",
                    format_type="instant",
                    view_count=780,
                    watch_time=610.0,
                    loop_rate=0.25,
                    shares=49,
                    comments=22,
                    completion_rate=0.71,
                    share_rate=0.05,
                    comment_rate=0.028,
                    viral_score=72.0,
                    is_winner=False,
                    metadata_json={},
                ),
            ]
        )
        session.commit()

        cache = MemoryCacheBackend()
        service = CreatorCopilotService(
            session=session,
            strategy_builder=CopilotStrategyBuilder(cache_backend=cache),
        )
        payload = service.analyze_draft(
            actor=creator,
            creator_id="creator-profile-copilot",
            draft={
                "title": "Final whistle breakdown",
                "duration_seconds": 19,
                "event_type": "analysis",
                "tags": ["breakdown", "final"],
                "preferred_format": "debate",
                "intro_seconds": 2.6,
                "visual_intensity": 0.64,
                "event_density": 0.58,
                "audience_cluster": "debate-core",
                "has_reaction_overlay": False,
            },
        )

        assert payload["prediction"]["best_format"] == "debate"
        assert payload["prediction"]["viral_probability"] > 0.6
        assert payload["variant_strategy"]["recommended_variants"][0]["type"] == "debate"
        assert payload["hook_analysis"]["suggestion"] == "start with goal moment, not buildup"
        assert payload["strategy_profile"]["profile_key"] == "creator:creator-profile-copilot:strategy_profile"
        assert payload["live_coaching"]["event_name"] == "copilot.alert.triggered"
        assert payload["action_plan"]
        assert "creator:creator-profile-copilot:strategy_profile" in cache.values
    finally:
        session.close()
