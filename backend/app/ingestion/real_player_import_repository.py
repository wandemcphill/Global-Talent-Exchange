from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ingestion.constants import REAL_PLAYER_IMPORT_ENTITY_TYPE
from app.ingestion.models import ProviderSyncCursor, ProviderSyncRun
from app.ingestion.repository import MutationStats
from app.models.base import utcnow
from app.providers.import_models import RealPlayerSourceItem

from .real_player_import_models import RealPlayerImportStagingRecord


def _payload_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


class RealPlayerImportRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_staging_records(
        self,
        *,
        provider_name: str,
        items: Sequence[RealPlayerSourceItem],
        source_version: str | None,
        last_import_run_id: str,
        last_import_cursor: str | None,
    ) -> MutationStats:
        stats = MutationStats(records_seen=len(items))
        if not items:
            return stats

        player_ids = [item.provider_player_id for item in items]
        existing_records = self.session.scalars(
            select(RealPlayerImportStagingRecord).where(
                RealPlayerImportStagingRecord.provider_name == provider_name,
                RealPlayerImportStagingRecord.provider_player_id.in_(player_ids),
            )
        )
        existing_by_provider_id = {
            record.provider_player_id: record
            for record in existing_records
        }
        observed_at = utcnow()

        for item in items:
            payload_hash = _payload_hash(item.raw_payload)
            record = existing_by_provider_id.get(item.provider_player_id)
            if record is None:
                record = RealPlayerImportStagingRecord(
                    provider_name=provider_name,
                    provider_player_id=item.provider_player_id,
                    provider_club_id=item.current_club_id,
                    provider_club_name=item.current_club_name,
                    provider_competition_id=item.current_competition_id,
                    provider_competition_name=item.current_competition_name,
                    provider_season_id=item.current_season_id,
                    full_name=item.full_name,
                    first_name=item.first_name,
                    last_name=item.last_name,
                    short_name=item.short_name,
                    display_position=item.display_position,
                    nationality_name=item.nationality_name,
                    nationality_code=item.nationality_code,
                    date_of_birth=item.date_of_birth,
                    provider_last_updated_at=item.provider_last_updated_at,
                    source_version=source_version,
                    last_import_cursor=last_import_cursor,
                    source_payload_hash=payload_hash,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    last_import_run_id=last_import_run_id,
                    latest_payload_json=item.raw_payload,
                    metadata_json=dict(item.metadata_json),
                )
                self.session.add(record)
                existing_by_provider_id[item.provider_player_id] = record
                stats.inserted_count += 1
                continue

            if record.source_payload_hash == payload_hash:
                stats.skipped_count += 1
                continue

            record.provider_club_id = item.current_club_id
            record.provider_club_name = item.current_club_name
            record.provider_competition_id = item.current_competition_id
            record.provider_competition_name = item.current_competition_name
            record.provider_season_id = item.current_season_id
            record.full_name = item.full_name
            record.first_name = item.first_name
            record.last_name = item.last_name
            record.short_name = item.short_name
            record.display_position = item.display_position
            record.nationality_name = item.nationality_name
            record.nationality_code = item.nationality_code
            record.date_of_birth = item.date_of_birth
            record.provider_last_updated_at = item.provider_last_updated_at
            record.source_version = source_version
            record.last_import_cursor = last_import_cursor
            record.source_payload_hash = payload_hash
            record.last_seen_at = observed_at
            record.last_import_run_id = last_import_run_id
            record.latest_payload_json = item.raw_payload
            record.metadata_json = dict(item.metadata_json)
            stats.updated_count += 1

        self.session.flush()
        return stats

    def list_recent_runs(self, *, provider_name: str, limit: int = 10) -> list[ProviderSyncRun]:
        statement = (
            select(ProviderSyncRun)
            .where(
                ProviderSyncRun.provider_name == provider_name,
                ProviderSyncRun.entity_type == REAL_PLAYER_IMPORT_ENTITY_TYPE,
            )
            .order_by(ProviderSyncRun.started_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def get_latest_run(self, *, provider_name: str) -> ProviderSyncRun | None:
        statement = (
            select(ProviderSyncRun)
            .where(
                ProviderSyncRun.provider_name == provider_name,
                ProviderSyncRun.entity_type == REAL_PLAYER_IMPORT_ENTITY_TYPE,
            )
            .order_by(ProviderSyncRun.started_at.desc())
            .limit(1)
        )
        return self.session.scalar(statement)

    def get_cursor(self, *, provider_name: str, cursor_key: str) -> ProviderSyncCursor | None:
        return self.session.scalar(
            select(ProviderSyncCursor).where(
                ProviderSyncCursor.provider_name == provider_name,
                ProviderSyncCursor.entity_type == REAL_PLAYER_IMPORT_ENTITY_TYPE,
                ProviderSyncCursor.cursor_key == cursor_key,
            )
        )

    def count_staged_records(self, *, provider_name: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(RealPlayerImportStagingRecord).where(
                    RealPlayerImportStagingRecord.provider_name == provider_name
                )
            )
            or 0
        )

    def latest_seen_at(self, *, provider_name: str) -> datetime | None:
        return self.session.scalar(
            select(func.max(RealPlayerImportStagingRecord.last_seen_at)).where(
                RealPlayerImportStagingRecord.provider_name == provider_name
            )
        )
