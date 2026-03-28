from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.highlights.queue import FileHighlightRenderQueue, HighlightRenderJob
from app.highlights.worker import HighlightRenderWorker
from app.storage import LocalObjectStorage


@dataclass(slots=True)
class StubRenderer:
    def render(self, _job, *, output_path: Path, storage_root: Path):
        output_path.write_bytes(b"fake-mp4")
        return {"renderer": "stub", "mode": "test"}


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
