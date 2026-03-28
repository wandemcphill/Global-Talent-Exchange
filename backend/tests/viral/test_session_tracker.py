from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.viral.ingestion_schemas import ClipEvent, ClipEventMetadata, ClipEventType
from app.viral.schemas import (
    ViralCaptionView,
    ViralClipAnalyticsView,
    ViralClipView,
    ViralEditPlanView,
    ViralFeedbackLoopView,
    ViralFeedResponse,
    ViralScoreBreakdownView,
)
from app.viral.session_tracker import ViralSessionTracker


def _clip(
    *,
    clip_id: str,
    team_name: str,
    event_type: str,
    content_type: str,
    format_key: str = "instant_clip",
    viral_score: int,
    engagement: float,
    freshness: float,
    minute: int,
) -> ViralClipView:
    return ViralClipView(
        clip_id=clip_id,
        match_id="match-1",
        highlight_id=clip_id.split("::")[-1],
        title=f"Clip {clip_id}",
        team_name=team_name,
        player_name="Player One",
        event_type=event_type,
        minute=minute,
        viral_score=viral_score,
        engagement=engagement,
        freshness=freshness,
        ranking_score=0.0,
        tags=["tactical"] if content_type == "tactical" else ["chaos"] if content_type == "meme" else ["highlight"],
        breakdown=ViralScoreBreakdownView(total=viral_score),
        caption=ViralCaptionView(hook="Hook", caption="Caption"),
        editor=ViralEditPlanView(format_key=format_key, crop_filter="center_crop", overlay_text="Hook"),
        analytics=ViralClipAnalyticsView(clip_id=clip_id),
        feedback=ViralFeedbackLoopView(
            performance_tier="stable",
            recommendation="keep testing",
            viral_analysis="Solid baseline",
        ),
        metadata={"content_type": content_type, "format_key": format_key},
    )


def _feed(*clips: ViralClipView) -> ViralFeedResponse:
    return ViralFeedResponse(
        clips=list(clips),
        generated_at=datetime.now(UTC),
        personalization={},
    )


def _event(
    *,
    clip_id: str,
    session_id: str,
    event_type: ClipEventType,
    watch_time_ms: int,
    video_length_ms: int,
    content_type: str | None = None,
    format_key: str | None = None,
    clip_event_type: str | None = None,
    team_name: str | None = None,
    tags: list[str] | None = None,
) -> ClipEvent:
    return ClipEvent(
        event_id=uuid4(),
        clip_id=clip_id,
        user_id=None,
        session_id=session_id,
        timestamp=datetime.now(UTC),
        event_type=event_type,
        watch_time_ms=watch_time_ms,
        video_length_ms=video_length_ms,
        metadata=ClipEventMetadata(
            device="ios",
            country="NG",
            referrer="feed",
            content_type=content_type,
            format_key=format_key,
            clip_event_type=clip_event_type,
            team_name=team_name,
            tags=tags or [],
        ),
    )


def test_session_tracker_applies_meme_skip_and_tactical_completion_adjustments() -> None:
    tracker = ViralSessionTracker()

    tracker.observe_many(
        [
            _event(
                clip_id="match::meme-1",
                session_id="session-1",
                event_type=ClipEventType.SCROLL,
                watch_time_ms=300,
                video_length_ms=10000,
                content_type="meme",
                format_key="meme_cut",
                clip_event_type="red_card",
                team_name="Chaos FC",
                tags=["chaos"],
            ),
            _event(
                clip_id="match::meme-2",
                session_id="session-1",
                event_type=ClipEventType.SCROLL,
                watch_time_ms=400,
                video_length_ms=10000,
                content_type="meme",
                format_key="meme_cut",
                clip_event_type="missed_big_chance",
                team_name="Chaos FC",
                tags=["chaos"],
            ),
            _event(
                clip_id="match::meme-3",
                session_id="session-1",
                event_type=ClipEventType.SCROLL,
                watch_time_ms=500,
                video_length_ms=10000,
                content_type="meme",
                format_key="meme_cut",
                clip_event_type="woodwork",
                team_name="Chaos FC",
                tags=["chaos"],
            ),
            _event(
                clip_id="match::tactical-1",
                session_id="session-1",
                event_type=ClipEventType.COMPLETE,
                watch_time_ms=12000,
                video_length_ms=12000,
                content_type="tactical",
                format_key="breakdown",
                clip_event_type="tactical_swing",
                team_name="Thinkers FC",
                tags=["tactical"],
            ),
        ]
    )

    state = tracker.get_state("session-1")

    assert state.clips_seen == 4
    assert state.watch_time_ms == 13200
    assert state.skips == 3
    assert state.interactions == 1
    assert state.affinity.content_types["meme"] < 0
    assert state.affinity.content_types["tactical"] > 0
    assert state.affinity.formats["breakdown"] > 0
    assert state.affinity.formats["meme_cut"] < 0
    assert "content_types" in state.affinity.override_dimensions
    assert state.affinity.teams["thinkers fc"] > 0


def test_session_tracker_personalization_overrides_global_affinity() -> None:
    tracker = ViralSessionTracker()
    global_clip = _clip(
        clip_id="match::global-goal",
        team_name="Global FC",
        event_type="goal",
        content_type="highlight",
        format_key="instant_clip",
        viral_score=72,
        engagement=48,
        freshness=35,
        minute=18,
    )
    session_clip = _clip(
        clip_id="match::session-tactical",
        team_name="Session FC",
        event_type="tactical_swing",
        content_type="tactical",
        format_key="breakdown",
        viral_score=68,
        engagement=46,
        freshness=35,
        minute=51,
    )
    feed = _feed(global_clip, session_clip)

    baseline = tracker.personalize_feed(
        session_id="session-2",
        feed=feed,
        favorite_team="Global FC",
        favorite_event_types=["goal"],
    )

    assert baseline.clips[0].clip_id == global_clip.clip_id

    tracker.observe_many(
        [
            _event(
                clip_id=session_clip.clip_id,
                session_id="session-2",
                event_type=ClipEventType.COMPLETE,
                watch_time_ms=12000,
                video_length_ms=12000,
            )
        ]
    )

    personalized = tracker.personalize_feed(
        session_id="session-2",
        feed=feed,
        favorite_team="Global FC",
        favorite_event_types=["goal"],
    )

    assert personalized.session is not None
    assert personalized.session.override_global_affinity is True
    assert personalized.clips[0].clip_id == session_clip.clip_id
    assert personalized.clips[0].metadata["base_score"] > 0
    assert personalized.clips[0].metadata["session_affinity"] > personalized.clips[0].metadata["base_score"]
    assert personalized.clips[0].metadata["session_score_adjustment"] > 0
