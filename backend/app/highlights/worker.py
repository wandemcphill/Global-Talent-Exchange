from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import shutil
from threading import Event, Thread
from time import sleep
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from fastapi import FastAPI

from app.highlights.ffmpeg_builder import FFmpegHighlightRenderer, HighlightRenderer
from app.highlights.queue import FileHighlightRenderQueue
from app.highlights.service import HighlightGenerationService
from app.storage import LocalObjectStorage

if TYPE_CHECKING:
    from app.core.container import ApplicationContext

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HighlightRenderWorker:
    queue: FileHighlightRenderQueue
    storage: LocalObjectStorage
    renderer: HighlightRenderer = field(default_factory=FFmpegHighlightRenderer)
    poll_interval_seconds: float = 5.0
    _stop_event: Event = field(default_factory=Event)
    _thread: Thread | None = None

    @property
    def storage_root(self) -> Path:
        return self.storage.root

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run_loop, name="gtex-highlight-render", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def process_next(self) -> dict[str, Any] | None:
        record = self.queue.claim_next()
        if record is None:
            return None

        temp_dir: Path | None = None
        try:
            temp_root = self.storage_root / "_tmp_render"
            temp_root.mkdir(parents=True, exist_ok=True)
            temp_dir = temp_root / f"{record.job_id}_{uuid4().hex[:8]}"
            temp_dir.mkdir(parents=True, exist_ok=True)
            output_path = temp_dir / f"{record.job_id}.mp4"
            render_result = self.renderer.render(
                record.payload,
                output_path=output_path,
                storage_root=self.storage_root,
            )
            content = output_path.read_bytes()
            stored = self.storage.put_bytes(
                key=record.payload.output_storage_key,
                content=content,
                content_type="video/mp4",
                metadata={
                    "queue_job_id": record.job_id,
                    "queue_name": record.queue_name,
                    "render_kind": record.payload.kind,
                    "match_id": record.payload.match_id,
                    "highlight_id": record.payload.highlight_id,
                    "title": record.payload.title,
                    "subtitle": record.payload.subtitle,
                    "duration_seconds": record.payload.duration_seconds,
                    "render_mode": render_result.get("mode"),
                },
            )
            completed = self.queue.mark_succeeded(
                record,
                result={
                    "output_storage_key": stored.key,
                    "size_bytes": stored.size_bytes,
                    **render_result,
                },
            )
            return {
                "job_id": completed.job_id,
                "status": "succeeded",
                "output_storage_key": stored.key,
                "size_bytes": stored.size_bytes,
                "mode": render_result.get("mode"),
            }
        except Exception as exc:
            failed = self.queue.mark_failed(record, error=str(exc))
            logger.exception(
                "highlights.render.failed",
                extra={
                    "job_id": failed.job_id,
                    "storage_key": failed.payload.output_storage_key,
                    "kind": failed.payload.kind,
                },
            )
            return {
                "job_id": failed.job_id,
                "status": "failed",
                "error": failed.last_error,
                "output_storage_key": failed.payload.output_storage_key,
            }
        finally:
            if temp_dir is not None:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            outcome = self.process_next()
            if outcome is None:
                sleep(self.poll_interval_seconds)


def bind_highlight_render_worker(app: FastAPI, context: ApplicationContext) -> None:
    queue = FileHighlightRenderQueue(context.settings.media_storage.storage_root)
    storage = LocalObjectStorage(context.settings.media_storage.storage_root)
    worker = HighlightRenderWorker(
        queue=queue,
        storage=storage,
        renderer=FFmpegHighlightRenderer(binary=os.getenv("GTE_HIGHLIGHT_RENDER_FFMPEG_BINARY", "ffmpeg")),
        poll_interval_seconds=max(
            0.5,
            float(os.getenv("GTE_HIGHLIGHT_RENDER_WORKER_INTERVAL_SECONDS", "5")),
        ),
    )
    app.state.highlight_render_queue = queue
    app.state.highlight_generation_service = HighlightGenerationService(
        settings=context.settings,
        queue=queue,
        storage=storage,
    )
    app.state.highlight_render_worker = worker
    enabled = os.getenv("GTE_HIGHLIGHT_RENDER_WORKER_ENABLED", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    if enabled:
        worker.start()


def shutdown_highlight_render_worker(app: FastAPI, _context: ApplicationContext) -> None:
    worker = getattr(app.state, "highlight_render_worker", None)
    if worker is not None:
        worker.stop()


__all__ = [
    "HighlightRenderWorker",
    "bind_highlight_render_worker",
    "shutdown_highlight_render_worker",
]
