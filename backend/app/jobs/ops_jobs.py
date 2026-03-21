from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.market.service import MarketEngine
from app.services.storage_media_service import MediaStorageService
from app.storage import LocalObjectStorage
from app.workers.integrity_scan_worker import IntegrityScanWorker
from app.workers.media_retention_worker import MediaRetentionWorker


@dataclass(slots=True)
class OpsJobRunner:
    session_factory: sessionmaker
    settings: Settings
    market_engine: MarketEngine | None = None

    def run_media_retention(self) -> dict[str, Any]:
        storage_service = MediaStorageService(
            storage=LocalObjectStorage(self.settings.media_storage.storage_root),
            config=self.settings.media_storage,
        )
        with self.session_factory() as session:
            worker = MediaRetentionWorker(session=session, storage_service=storage_service)
            archived = worker.archive_expired_highlights()
            purged = worker.purge_expired_archives()
            session.commit()
        return {"archive": archived, "purge": purged}

    def run_integrity_scan(self) -> dict[str, Any]:
        with self.session_factory() as session:
            worker = IntegrityScanWorker(session=session, settings=self.settings, market_engine=self.market_engine)
            results = {
                "integrity_scan": worker.run_integrity_scan(),
                "cluster_scan": worker.run_suspicious_cluster_scan(),
            }
            session.commit()
        return results


__all__ = ["OpsJobRunner"]
