from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.highlights.queue import FileHighlightRenderQueue, HighlightRenderJob


def _artifact_root(name: str) -> Path:
    root = Path(__file__).resolve().parents[3] / ".codex_tmp" / f"{name}_{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_highlight_queue_is_idempotent_and_tracks_terminal_state() -> None:
    queue = FileHighlightRenderQueue(_artifact_root("highlight_queue_test"))
    job = HighlightRenderJob(
        kind="clip",
        match_id="match-001",
        highlight_id="event-001",
        output_storage_key="media/highlights/temp/match-001/goal_12.mp4",
        title="Goal - 12'",
        duration_seconds=12,
        start_second=710,
        end_second=722,
    )

    first = queue.enqueue(job)
    second = queue.enqueue(job)

    assert first.job_id == second.job_id
    assert first.status == "queued"

    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.job_id == first.job_id
    assert claimed.status == "processing"
    assert claimed.attempts == 1

    failed = queue.mark_failed(claimed, error="ffmpeg missing")
    assert failed.status == "failed"
    assert failed.last_error == "ffmpeg missing"

    reloaded = queue.get_by_storage_key(job.output_storage_key)
    assert reloaded is not None
    assert reloaded.status == "failed"
    assert reloaded.job_id == first.job_id
