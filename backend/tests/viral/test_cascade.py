from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.db import get_session
from app.viral.cascade import InMemoryViralCascadeStore, ViralCascadeEngine
from app.viral.router import router as viral_router
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralScoreBreakdownView,
)


def _build_clip(
    *,
    clip_id: str = "clip-cascade",
    ranking_score: float = 52.0,
    completion_rate: float = 0.83,
    share_rate: float = 0.16,
    views_last_10min: int = 360,
    views_last_60min: int = 120,
    view_count: int = 1000,
) -> ViralClipView:
    shares = int(round(view_count * share_rate))
    completions = int(round(view_count * completion_rate))
    return ViralClipView(
        clip_id=clip_id,
        match_id="match-1",
        highlight_id="highlight-1",
        title="Late winner",
        event_type="goal",
        minute=89,
        viral_score=96,
        engagement=82.0,
        freshness=90.0,
        ranking_score=ranking_score,
        tags=["goal"],
        breakdown=ViralScoreBreakdownView(total=96, base_event=50, late_drama_bonus=30, go_ahead_bonus=16),
        caption=ViralCaptionView(hook="Late winner", caption="The match flipped late."),
        distribution_accounts=[],
        editor=ViralEditPlanView(crop_filter="scale=1080:1920", overlay_text="Late winner"),
        formats=[],
        analytics=ViralClipAnalyticsView(
            clip_id=clip_id,
            view_count=view_count,
            completions=completions,
            watch_time=12.4,
            total_watch_time=12.4 * view_count,
            loops=220,
            loop_rate=0.22,
            shares=shares,
            comments=18,
            skips=max(view_count - completions, 0),
            completion_rate=completion_rate,
            share_rate=share_rate,
            comment_rate=0.018,
            views_last_10min=views_last_10min,
            views_last_60min=views_last_60min,
        ),
        feedback=ViralFeedbackLoopView(
            performance_tier="high_retention",
            recommendation="Increase similar clips.",
            increase_similar_clips=True,
            actions=["increase_distribution"],
            viral_analysis="The clip held retention and sharing momentum.",
        ),
        metadata={},
    )


def test_cascade_engine_triggers_then_cools_down_without_reboosting_static_metrics() -> None:
    engine = ViralCascadeEngine(store=InMemoryViralCascadeStore())
    clip = _build_clip()
    now = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)

    boosted = engine.apply_to_clip(clip, now=now)

    assert boosted.ranking_score == 82.0
    assert boosted.tags[-1] == "cascade"
    assert boosted.metadata["cascade"]["cascade"] is True
    assert boosted.metadata["cascade"]["status"] == "active"
    assert boosted.metadata["cascade"]["actions"]["distribution_cap_multiplier"] == 3
    assert boosted.metadata["cascade"]["actions"]["pinned_in_trending"] is True
    assert engine.list_cascades(now=now)[0]["clip_id"] == clip.clip_id

    cooling = engine.apply_to_clip(clip, now=now + timedelta(minutes=20))

    assert cooling.ranking_score == clip.ranking_score
    assert cooling.metadata["cascade"]["cascade"] is False
    assert cooling.metadata["cascade"]["status"] == "cooldown"

    expired = engine.apply_to_clip(clip, now=now + timedelta(hours=2))

    assert expired.ranking_score == clip.ranking_score
    assert expired.metadata["cascade"]["status"] == "expired"
    assert engine.list_cascades(now=now + timedelta(hours=2)) == []


def test_cascades_router_lists_active_cascade_records() -> None:
    app = FastAPI()
    app.include_router(viral_router)

    def _override_session():
        yield MagicMock()

    app.dependency_overrides[get_session] = _override_session
    engine = ViralCascadeEngine(store=InMemoryViralCascadeStore())
    app.state.viral_cascade_engine = engine
    app.state.viral_cascade_store = engine.store

    engine.apply_to_clip(
        _build_clip(clip_id="clip-router"),
        now=datetime.now(UTC),
    )

    with TestClient(app) as client:
        response = client.get("/viral/cascades")

    assert response.status_code == 200
    body = response.json()
    assert body["cascades"]
    assert body["cascades"][0]["clip_id"] == "clip-router"
    assert body["cascades"][0]["cascade"] is True
    assert body["cascades"][0]["actions"]["distribution_cap_multiplier"] == 3
