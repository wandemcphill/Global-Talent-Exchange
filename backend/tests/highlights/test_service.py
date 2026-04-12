from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from app.core.config import get_settings, reset_settings_cache
from app.highlights.service import HighlightGenerationService
from app.match_engine.schemas import MatchHighlightItemView, MatchHighlightListView, MatchHighlightPipelineView, MatchHighlightReelView


def _artifact_root(name: str) -> Path:
    root = Path(__file__).resolve().parents[3] / ".codex_tmp" / f"{name}_{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _service(storage_root: Path) -> HighlightGenerationService:
    reset_settings_cache()
    settings = get_settings()
    settings = replace(settings, media_storage=replace(settings.media_storage, storage_root=storage_root))
    return HighlightGenerationService(settings=settings)


def _manifest() -> MatchHighlightListView:
    return MatchHighlightListView(
        match_id="match-highlight-001",
        highlights=[
            MatchHighlightItemView(
                highlight_id="event-1",
                title="Goal",
                minute=12,
                event_type="goals",
                duration_seconds=8,
                storage_key="media/highlights/temp/match-highlight-001/goal_12.mp4",
            )
        ],
        pipeline=MatchHighlightPipelineView(object_storage_prefix="media/highlights/temp"),
        reel=MatchHighlightReelView(
            title="Recap",
            clip_count=1,
            runtime_seconds=8,
            storage_key="media/highlights/temp/match-highlight-001/recap.mp4",
        ),
    )


def test_prepare_manifest_returns_unavailable_when_no_source_footage_is_configured() -> None:
    service = _service(_artifact_root("highlight_service_unavailable"))

    manifest = service.prepare_manifest(_manifest())

    assert manifest.highlights[0].render_status == "unavailable"
    assert manifest.highlights[0].metadata["queue_status"] == "source_unavailable"
    assert manifest.reel is not None
    assert manifest.reel.render_status == "unavailable"
    assert service.queue.get_by_storage_key(manifest.highlights[0].storage_key) is None


def test_prepare_manifest_returns_pending_when_source_footage_is_not_ready() -> None:
    service = _service(_artifact_root("highlight_service_pending"))

    manifest = service.prepare_manifest(
        _manifest(),
        source_storage_key="media/replays/match-highlight-001/full_match.mp4",
    )

    assert manifest.highlights[0].render_status == "pending"
    assert manifest.highlights[0].metadata["queue_status"] == "pending"
    assert manifest.highlights[0].metadata["queue_reason"] == "source_footage_pending"
    assert manifest.reel is not None
    assert manifest.reel.render_status == "pending"
    record = service.queue.get_by_storage_key(manifest.highlights[0].storage_key)
    assert record is not None
    assert record.status == "queued"
