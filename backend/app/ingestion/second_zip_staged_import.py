from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import hashlib
from pathlib import Path

from app.ingestion.second_zip_archive_intake import (
    SecondZipArchiveIntakeError,
    SecondZipArchiveIntakeService,
)
from app.ingestion.second_zip_base_eligibility import (
    SecondZipBaseEligibilityPolicy,
    evaluate_second_zip_players_csv_row,
)
from app.ingestion.transfermarkt_second_zip import (
    SECOND_ZIP_SOURCE_NAME,
    TransfermarktSecondZipError,
    TransfermarktSecondZipPlayerContract,
    TransfermarktSecondZipReferenceCatalog,
    TransfermarktSecondZipReader,
    map_player_contract_to_source_item,
    map_player_row_to_contract,
)
from app.schemas.real_player_ingestion import RealPlayerIngestionMode, RealPlayerIngestionRequest, RealPlayerSeedInput


SECOND_ZIP_SOURCE_TYPE = SECOND_ZIP_SOURCE_NAME
SECOND_ZIP_SOURCE_ANCHOR_FIELD = "external_player_id"


class SecondZipStagedImportError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SecondZipStagedImportBuildResult:
    archive_path: Path
    archive_sha256: str
    provider_name: str
    request: RealPlayerIngestionRequest
    metadata_json: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class SecondZipStagedImportBuilder:
    archive_intake_service: SecondZipArchiveIntakeService = field(default_factory=SecondZipArchiveIntakeService)
    reference_date: date | None = None

    def build_request(self, archive_path: str | Path) -> SecondZipStagedImportBuildResult:
        resolved_path = Path(archive_path).expanduser().resolve()
        try:
            inspection = self.archive_intake_service.validate_archive(resolved_path)
            reader = TransfermarktSecondZipReader(inspection.archive_path)
            reference_catalog = reader.build_reference_catalog()
            archive_sha256 = self._hash_file(inspection.archive_path)
            as_of = datetime.now(UTC)
            policy = SecondZipBaseEligibilityPolicy(
                reference_date=self.reference_date or as_of.date(),
            )
            seen_source_player_keys: set[str] = set()
            players: list[RealPlayerSeedInput] = []
            source_row_count = 0
            eligible_row_count = 0
            filtered_row_count = 0
            duplicate_skipped_count = 0

            for raw_row in reader.iter_players():
                source_row_count += 1
                eligibility = evaluate_second_zip_players_csv_row(raw_row, policy=policy)
                if not eligibility.eligible:
                    filtered_row_count += 1
                    continue

                eligible_row_count += 1
                contract = map_player_row_to_contract(raw_row)
                source_player_key = contract.external_player_id.strip()
                source_player_key_folded = source_player_key.casefold()
                if source_player_key_folded in seen_source_player_keys:
                    duplicate_skipped_count += 1
                    continue

                seen_source_player_keys.add(source_player_key_folded)
                players.append(
                    self._seed_input_from_contract(
                        contract,
                        reference_catalog=reference_catalog,
                        as_of=as_of,
                    )
                )
        except (OSError, SecondZipArchiveIntakeError, TransfermarktSecondZipError) as exc:
            raise SecondZipStagedImportError(str(exc)) from exc

        request = RealPlayerIngestionRequest(
            mode=RealPlayerIngestionMode.CURATED_SEED,
            players=players,
            ingestion_source_version=archive_sha256,
            as_of=as_of,
        )
        metadata = {
            "source_archive_sha256": archive_sha256,
            "source_archive_name": inspection.archive_path.name,
            "source_anchor_field": SECOND_ZIP_SOURCE_ANCHOR_FIELD,
            "source_row_count": source_row_count,
            "source_eligible_row_count": eligible_row_count,
            "source_filtered_row_count": filtered_row_count,
            "source_duplicate_skipped_count": duplicate_skipped_count,
        }
        return SecondZipStagedImportBuildResult(
            archive_path=inspection.archive_path,
            archive_sha256=archive_sha256,
            provider_name=SECOND_ZIP_SOURCE_NAME,
            request=request,
            metadata_json=metadata,
        )

    @staticmethod
    def _seed_input_from_contract(
        contract: TransfermarktSecondZipPlayerContract,
        *,
        reference_catalog: TransfermarktSecondZipReferenceCatalog,
        as_of: datetime,
    ) -> RealPlayerSeedInput:
        source_item = map_player_contract_to_source_item(
            contract,
            reference_catalog=reference_catalog,
        )
        return RealPlayerSeedInput.model_validate(
            {
                **source_item.raw_payload,
                "source_last_refreshed_at": as_of,
            }
        )

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()


__all__ = [
    "SECOND_ZIP_SOURCE_ANCHOR_FIELD",
    "SECOND_ZIP_SOURCE_TYPE",
    "SecondZipStagedImportBuildResult",
    "SecondZipStagedImportBuilder",
    "SecondZipStagedImportError",
]
