from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.risk_ops_engine.service import RiskOpsService
from app.services.storage_media_service import MediaStorageService


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class MediaRetentionWorker:
    session: Session
    storage_service: MediaStorageService

    def archive_expired_highlights(self) -> dict[str, Any]:
        expired = self.storage_service.list_expired_temporary_highlights()
        archived: list[str] = []
        for key in expired:
            archived_asset = self.storage_service.archive_highlight(storage_key=key)
            archived.append(archived_asset.storage_key)
            RiskOpsService(self.session).log_audit(
                actor_user_id=None,
                action_key="media.highlight.archived",
                resource_type="media_asset",
                resource_id=archived_asset.storage_key,
                detail="Expired highlight moved to archive storage.",
                metadata_json={"source_key": key},
            )
        self.session.flush()
        return {"expired_count": len(expired), "archived_count": len(archived)}

    def purge_expired_archives(self) -> dict[str, Any]:
        cutoff = _utcnow() - timedelta(days=self.storage_service.config.highlight_archive_ttl_days)
        deleted: list[str] = []
        for key in self.storage_service.storage.list_prefix(prefix=self.storage_service.config.highlight_archive_prefix):
            metadata = self.storage_service.storage.read_metadata(key=key)
            archived_at_raw = metadata.get("archived_at")
            if not archived_at_raw:
                continue
            try:
                archived_at = datetime.fromisoformat(str(archived_at_raw))
            except ValueError:
                continue
            if archived_at.tzinfo is None:
                archived_at = archived_at.replace(tzinfo=timezone.utc)
            if archived_at <= cutoff:
                self.storage_service.storage.delete(key=key)
                deleted.append(key)
                RiskOpsService(self.session).log_audit(
                    actor_user_id=None,
                    action_key="media.highlight.purged",
                    resource_type="media_asset",
                    resource_id=key,
                    detail="Archived highlight purged after retention window.",
                    metadata_json={},
                )
        self.session.flush()
        return {"purged_count": len(deleted)}


__all__ = ["MediaRetentionWorker"]
