from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings
from app.highlights.queue import FileHighlightRenderQueue, HighlightRenderJob, HighlightRenderJobRecord
from app.match_engine.schemas import MatchHighlightItemView, MatchHighlightListView, MatchHighlightReelView
from app.storage import LocalObjectStorage


@dataclass(slots=True)
class HighlightGenerationService:
    settings: Settings
    queue: FileHighlightRenderQueue | None = None
    storage: LocalObjectStorage | None = None

    def __post_init__(self) -> None:
        if self.queue is None:
            self.queue = FileHighlightRenderQueue(self.settings.media_storage.storage_root)
        if self.storage is None:
            self.storage = LocalObjectStorage(self.settings.media_storage.storage_root)

    def prepare_manifest(
        self,
        manifest: MatchHighlightListView,
        *,
        source_path: str | None = None,
        source_storage_key: str | None = None,
    ) -> MatchHighlightListView:
        clip_storage_keys: list[str] = []
        clip_render_statuses: list[str] = []
        items: list[MatchHighlightItemView] = []
        for item in manifest.highlights:
            updated_item = self._prepare_item(
                match_id=manifest.match_id,
                item=item,
                source_path=source_path,
                source_storage_key=source_storage_key,
            )
            items.append(updated_item)
            if updated_item.storage_key:
                clip_storage_keys.append(updated_item.storage_key)
                clip_render_statuses.append(updated_item.render_status)

        reel = self._prepare_reel(
            match_id=manifest.match_id,
            reel=manifest.reel,
            clip_storage_keys=tuple(clip_storage_keys),
            clip_render_statuses=tuple(clip_render_statuses),
            source_path=source_path,
            source_storage_key=source_storage_key,
        )
        pipeline = (
            manifest.pipeline.model_copy(update={"queue_name": self.queue.queue_name})
            if manifest.pipeline is not None
            else None
        )
        return manifest.model_copy(update={"highlights": items, "reel": reel, "pipeline": pipeline})

    def _prepare_item(
        self,
        *,
        match_id: str,
        item: MatchHighlightItemView,
        source_path: str | None,
        source_storage_key: str | None,
    ) -> MatchHighlightItemView:
        if not item.storage_key:
            return item
        if self.storage.exists(key=item.storage_key):
            metadata = dict(item.metadata)
            metadata["queue_status"] = "ready"
            return item.model_copy(update={"render_status": "ready", "metadata": metadata})
        source_status = self.resolve_clip_source_status(
            source_path=source_path,
            source_storage_key=source_storage_key,
        )
        if source_status == "unavailable":
            metadata = dict(item.metadata)
            metadata["queue_status"] = "source_unavailable"
            metadata["queue_reason"] = "source_footage_unavailable"
            return item.model_copy(update={"render_status": "unavailable", "metadata": metadata})

        job = HighlightRenderJob(
            kind="clip",
            match_id=match_id,
            highlight_id=item.highlight_id,
            output_storage_key=item.storage_key,
            title=item.overlay_title or item.title,
            subtitle=item.overlay_subtitle or item.scoreline_label or item.label,
            duration_seconds=max(1, int(item.duration_seconds or 1)),
            start_second=item.match_clock_start_second,
            end_second=item.match_clock_end_second,
            playback_speed=item.replay_speed,
            source_path=source_path,
            source_storage_key=source_storage_key,
            metadata={
                "event_type": item.event_type,
                "minute": item.minute,
                "camera_sequence": list(item.camera_sequence),
                "crowd_spike": item.crowd_spike,
                "importance": item.importance,
            },
        )
        record = self.queue.enqueue(job, replace_terminal=self._should_replace_terminal(item.storage_key))
        metadata = dict(item.metadata)
        metadata["queue_job_id"] = record.job_id
        render_status = self.render_status_for_record(record)
        if source_status == "pending":
            render_status = "pending"
        metadata["queue_status"] = render_status
        if source_status == "pending":
            metadata["queue_reason"] = "source_footage_pending"
        return item.model_copy(update={"render_status": render_status, "metadata": metadata})

    def _prepare_reel(
        self,
        *,
        match_id: str,
        reel: MatchHighlightReelView | None,
        clip_storage_keys: tuple[str, ...],
        clip_render_statuses: tuple[str, ...],
        source_path: str | None,
        source_storage_key: str | None,
    ) -> MatchHighlightReelView | None:
        if reel is None or not reel.storage_key or reel.runtime_seconds <= 0:
            return reel
        if self.storage.exists(key=reel.storage_key):
            return reel.model_copy(update={"render_status": "ready"})
        reel_source_status = self._resolve_reel_source_status(
            clip_storage_keys=clip_storage_keys,
            clip_render_statuses=clip_render_statuses,
            source_path=source_path,
            source_storage_key=source_storage_key,
        )
        if reel_source_status != "ready":
            return reel.model_copy(update={"render_status": reel_source_status})

        job = HighlightRenderJob(
            kind="reel",
            match_id=match_id,
            output_storage_key=reel.storage_key,
            title=reel.title,
            duration_seconds=max(1, int(reel.runtime_seconds)),
            subtitle=f"{reel.clip_count} clips",
            source_path=source_path,
            source_storage_key=source_storage_key,
            source_clip_storage_keys=clip_storage_keys,
            metadata={"clip_count": reel.clip_count},
        )
        record = self.queue.enqueue(job, replace_terminal=self._should_replace_terminal(reel.storage_key))
        return reel.model_copy(update={"render_status": self.render_status_for_record(record)})

    def _should_replace_terminal(self, storage_key: str) -> bool:
        existing = self.queue.get_by_storage_key(storage_key)
        return existing is not None and existing.status == "succeeded" and not self.storage.exists(key=storage_key)

    def resolve_clip_source_status(
        self,
        *,
        source_path: str | None,
        source_storage_key: str | None,
    ) -> str:
        if source_path:
            return "ready" if Path(source_path).exists() else "pending"
        if source_storage_key:
            return "ready" if self.storage.exists(key=source_storage_key) else "pending"
        return "unavailable"

    def _resolve_reel_source_status(
        self,
        *,
        clip_storage_keys: tuple[str, ...],
        clip_render_statuses: tuple[str, ...],
        source_path: str | None,
        source_storage_key: str | None,
    ) -> str:
        if clip_storage_keys:
            ready_clip_count = sum(1 for storage_key in clip_storage_keys if self.storage.exists(key=storage_key))
            if ready_clip_count == len(clip_storage_keys):
                return "ready"
            if any(status == "unavailable" for status in clip_render_statuses):
                return "unavailable"
            return "pending"
        return self.resolve_clip_source_status(source_path=source_path, source_storage_key=source_storage_key)

    @staticmethod
    def render_status_for_record(record: HighlightRenderJobRecord) -> str:
        return HighlightGenerationService._render_status(record)

    @staticmethod
    def _render_status(record: HighlightRenderJobRecord) -> str:
        if record.status == "succeeded":
            return "ready"
        result_status = str(record.result.get("render_status") or "").strip()
        if result_status:
            return result_status
        return record.status


__all__ = ["HighlightGenerationService"]
