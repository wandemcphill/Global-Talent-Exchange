from __future__ import annotations

import json

import pytest

import app.models  # noqa: F401
from app.media_engine.schemas import CreatorClipRevenueAttributionRequest
from app.models.highlight_share import HighlightShareExport
from app.models.user import User
from app.services.creator_clip_monetization_service import CreatorClipMonetizationService
from app.services.creator_insights_service import CreatorInsightsService


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


@pytest.fixture()
def session(gtex_db_session):
    # Shared full-schema engine with per-test rollback; avoids rebuilding 567 tables.
    yield gtex_db_session


def _create_user(session, *, user_id: str, email: str, username: str) -> User:
    user = User(id=user_id, email=email, username=username, password_hash="hashed", phone_number="1234567890")
    session.add(user)
    session.flush()
    return user


def _create_export(session, *, user_id: str, export_id: str, match_key: str, share_title: str) -> HighlightShareExport:
    export = HighlightShareExport(
        id=export_id,
        user_id=user_id,
        match_key=match_key,
        source_storage_key=f"media/highlights/temp/{export_id}.mp4",
        export_storage_key=f"media/exports/{export_id}.zip",
        status="generated",
        aspect_ratio="9:16",
        watermark_label="GTEX",
        share_title=share_title,
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
            },
        ),
    )


def test_creator_insights_service_builds_profile_recommendations_and_cache_entry(session) -> None:
    creator = _create_user(session, user_id="creator-insights-1", email="creator1@example.com", username="creator1")

    debate_one = _create_export(
        session,
        user_id=creator.id,
        export_id="export-debate-1",
        match_key="match-debate-1",
        share_title="Debate clip one",
    )
    debate_two = _create_export(
        session,
        user_id=creator.id,
        export_id="export-debate-2",
        match_key="match-debate-2",
        share_title="Debate clip two",
    )
    meme_one = _create_export(
        session,
        user_id=creator.id,
        export_id="export-meme-1",
        match_key="match-meme-1",
        share_title="Meme clip one",
    )
    meme_two = _create_export(
        session,
        user_id=creator.id,
        export_id="export-meme-2",
        match_key="match-meme-2",
        share_title="Meme clip two",
    )

    _attribute_clip(
        session,
        export_id=debate_one.id,
        views=180000,
        source_reference="debate-source-1",
        clip_format="debate",
        duration_seconds=18,
        completion_rate=0.91,
        share_rate=0.07,
        loop_rate=0.26,
        hook_style="fast-start",
        audience_cluster="debate-core",
        force_viral_bonus=True,
    )
    _attribute_clip(
        session,
        export_id=debate_two.id,
        views=145000,
        source_reference="debate-source-2",
        clip_format="debate",
        duration_seconds=19,
        completion_rate=0.87,
        share_rate=0.055,
        loop_rate=0.2,
        hook_style="fast-start",
        audience_cluster="debate-core",
        force_viral_bonus=True,
    )
    _attribute_clip(
        session,
        export_id=meme_one.id,
        views=42000,
        source_reference="meme-source-1",
        clip_format="meme",
        duration_seconds=28,
        completion_rate=0.58,
        share_rate=0.012,
        loop_rate=0.08,
        hook_style="slow-build",
        audience_cluster="casual-fans",
        force_viral_bonus=False,
    )
    _attribute_clip(
        session,
        export_id=meme_two.id,
        views=38000,
        source_reference="meme-source-2",
        clip_format="meme",
        duration_seconds=32,
        completion_rate=0.52,
        share_rate=0.01,
        loop_rate=0.05,
        hook_style="slow-build",
        audience_cluster="debate-core",
        force_viral_bonus=False,
    )
    session.commit()

    cache = MemoryCacheBackend()
    payload = CreatorInsightsService(session=session, cache_backend=cache).build_creator_insights(
        actor=creator,
        creator_id="creator-profile-1",
    )

    assert payload["profile_key"] == "creator:creator-profile-1:profile"
    assert payload["creator_metrics"]["best_format"] == "debate"
    assert payload["creator_metrics"]["worst_format"] == "meme"
    assert payload["creator_metrics"]["optimal_duration"] == "15-20s"
    assert payload["creator_metrics"]["audience_cluster"] == "debate-core"
    assert payload["analyzer"]["strongest_format"] == "debate"
    assert payload["analyzer"]["patterns"][0].startswith("debate clips outperform meme by +")
    assert "Videos 15-20s perform best" in payload["analyzer"]["patterns"]
    assert payload["recommendations"] == {
        "best_format": "debate",
        "optimal_length": "18s",
        "hook_style": "fast-start",
        "posting_strategy": "high frequency",
    }
    assert payload["viral_feedback_loop"]["high_retention_clips"] == 2
    assert payload["viral_feedback_loop"]["increase_similar_signals"] == 2
    assert json.loads(cache.values["creator:creator-profile-1:profile"])["profile_key"] == "creator:creator-profile-1:profile"
