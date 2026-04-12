from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.highlights.ffmpeg_builder import HighlightSourcePendingError, HighlightSourceUnavailableError
from app.highlights.queue import FileHighlightRenderQueue, HighlightRenderJob
from app.highlights.worker import HighlightRenderWorker
from app.storage import LocalObjectStorage


@dataclass(slots=True)
class StubRenderer:
    def render(self, _job, *, output_path: Path, storage_root: Path):
        output_path.write_bytes(b"fake-mp4")
        return {"renderer": "stub", "mode": "test"}


@dataclass(slots=True)
class PendingSourceRenderer:
    def render(self, _job, *, output_path: Path, storage_root: Path):
        raise HighlightSourcePendingError("source_footage_pending")


@dataclass(slots=True)
class UnavailableSourceRenderer:
    def render(self, _job, *, output_path: Path, storage_root: Path):
        raise HighlightSourceUnavailableError("source_footage_unavailable")


def _artifact_root(name: str) -> Path:
    root = Path(__file__).resolve().parents[3] / ".codex_tmp" / f"{name}_{uuid4().hex[:8]}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def test_highlight_worker_processes_queued_job_and_stores_asset() -> None:
    root = _artifact_root("highlight_worker_test")
    storage = LocalObjectStorage(root)
    queue = FileHighlightRenderQueue(root)
    job = HighlightRenderJob(
        kind="clip",
        match_id="match-002",
        highlight_id="event-002",
        output_storage_key="media/highlights/temp/match-002/goal_90.mp4",
        title="Last-minute goal",
        duration_seconds=8,
        start_second=5400,
        end_second=5408,
    )
    queued = queue.enqueue(job)
    worker = HighlightRenderWorker(queue=queue, storage=storage, renderer=StubRenderer())

    outcome = worker.process_next()

    assert outcome is not None
    assert outcome["status"] == "succeeded"
    assert storage.exists(key=job.output_storage_key) is True

    metadata = storage.read_metadata(key=job.output_storage_key)
    assert metadata["queue_job_id"] == queued.job_id
    assert metadata["render_kind"] == "clip"
    assert metadata["render_mode"] == "test"

    record = queue.get_by_storage_key(job.output_storage_key)
    assert record is not None
    assert record.status == "succeeded"


def test_highlight_worker_requeues_pending_source_jobs_without_storing_placeholder() -> None:
    root = _artifact_root("highlight_worker_pending_source")
    storage = LocalObjectStorage(root)
    queue = FileHighlightRenderQueue(root)
    job = HighlightRenderJob(
        kind="clip",
        match_id="match-003",
        highlight_id="event-003",
        output_storage_key="media/highlights/temp/match-003/goal_71.mp4",
        title="Late goal",
        duration_seconds=8,
        source_storage_key="media/replays/match-003/full_match.mp4",
    )
    queue.enqueue(job)
    worker = HighlightRenderWorker(queue=queue, storage=storage, renderer=PendingSourceRenderer())

    outcome = worker.process_next()

    assert outcome is not None
    assert outcome["status"] == "pending"
    assert storage.exists(key=job.output_storage_key) is False

    record = queue.get_by_storage_key(job.output_storage_key)
    assert record is not None
    assert record.status == "queued"
    assert record.last_error == "source_footage_pending"
    assert record.result["render_status"] == "pending"


def test_highlight_worker_marks_missing_source_as_unavailable_without_storing_asset() -> None:
    root = _artifact_root("highlight_worker_unavailable_source")
    storage = LocalObjectStorage(root)
    queue = FileHighlightRenderQueue(root)
    job = HighlightRenderJob(
        kind="clip",
        match_id="match-004",
        highlight_id="event-004",
        output_storage_key="media/highlights/temp/match-004/goal_88.mp4",
        title="Winner",
        duration_seconds=8,
    )
    queue.enqueue(job)
    worker = HighlightRenderWorker(queue=queue, storage=storage, renderer=UnavailableSourceRenderer())

    outcome = worker.process_next()

    assert outcome is not None
    assert outcome["status"] == "unavailable"
    assert storage.exists(key=job.output_storage_key) is False

    record = queue.get_by_storage_key(job.output_storage_key)
    assert record is not None
    assert record.status == "failed"
    assert record.last_error == "source_footage_unavailable"
    assert record.result["render_status"] == "unavailable"
