from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ingestion.real_player_canonical_mapping_service import CanonicalReferenceEntityType, CanonicalReferenceInput
from app.models.real_player_import_batch import RealPlayerImportBatch, RealPlayerImportRow
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_reference_mapping import (
    RealPlayerReferenceMapping,
    RealPlayerUnresolvedReference,
)
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.read_models import PlayerValueSnapshotRecord


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _payload_value(payload: dict[str, object], *keys: str) -> object | None:
    for key in keys:
        value = payload.get(key)
        if value is not None and _normalize_text(value):
            return value
    return None


def _payload_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def _reference_lookup_keys(
    row: RealPlayerImportRow,
    *,
    entity_type: str,
) -> tuple[str, ...]:
    keys: list[str] = []
    if entity_type == "club":
        direct_key = _normalize_text(row.club_reference_key)
        if direct_key:
            keys.append(direct_key)
        raw_payload = _payload_dict(row.raw_payload_json)
        derived_reference = CanonicalReferenceInput(
            source_name=row.source_name,
            entity_type=CanonicalReferenceEntityType.CLUB.value,
            provider_external_id=_normalize_text(_payload_value(raw_payload, "current_real_world_club_key")) or None,
            display_name=_normalize_text(_payload_value(raw_payload, "current_real_world_club")) or None,
            competition_external_id=_normalize_text(_payload_value(raw_payload, "current_real_world_league_key")) or None,
            competition_display_name=_normalize_text(_payload_value(raw_payload, "current_real_world_league")) or None,
        )
    else:
        direct_key = _normalize_text(row.league_reference_key)
        if direct_key:
            keys.append(direct_key)
        raw_payload = _payload_dict(row.raw_payload_json)
        derived_reference = CanonicalReferenceInput(
            source_name=row.source_name,
            entity_type=CanonicalReferenceEntityType.COMPETITION.value,
            provider_external_id=_normalize_text(_payload_value(raw_payload, "current_real_world_league_key")) or None,
            display_name=_normalize_text(_payload_value(raw_payload, "current_real_world_league")) or None,
        )

    derived_key = _normalize_text(derived_reference.provider_reference_key)
    if derived_reference.has_reference and derived_key:
        keys.append(derived_key)
    return tuple(dict.fromkeys(key for key in keys if key))


def _render_list(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "(none)"


def _render_counts(values: dict[str, int]) -> str:
    if not values:
        return "(none)"
    return ", ".join(
        f"{key}={count}"
        for key, count in sorted(values.items())
    )


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGroup:
    key_type: str
    identity_key: str
    row_count: int
    distinct_player_count: int
    source_keys: tuple[str, ...]
    player_ids: tuple[str, ...]
    canonical_names: tuple[str, ...]

    def render(self) -> str:
        return (
            f"{self.key_type}={self.identity_key} rows={self.row_count} "
            f"players={self.distinct_player_count} "
            f"sources={_render_list(self.source_keys)}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "key_type": self.key_type,
            "identity_key": self.identity_key,
            "row_count": self.row_count,
            "distinct_player_count": self.distinct_player_count,
            "source_keys": list(self.source_keys),
            "player_ids": list(self.player_ids),
            "canonical_names": list(self.canonical_names),
        }


@dataclass(frozen=True, slots=True)
class MissingRequiredFieldRow:
    row_number: int
    source_name: str
    source_player_key: str
    canonical_name: str
    status: str
    missing_fields: tuple[str, ...]

    def render(self) -> str:
        return (
            f"row={self.row_number} source={self.source_name}:{self.source_player_key} "
            f"status={self.status} missing={_render_list(self.missing_fields)}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "row_number": self.row_number,
            "source_name": self.source_name,
            "source_player_key": self.source_player_key,
            "canonical_name": self.canonical_name,
            "status": self.status,
            "missing_fields": list(self.missing_fields),
        }


@dataclass(frozen=True, slots=True)
class UnresolvedReferenceItem:
    entity_type: str
    provider_reference_key: str
    reason_code: str | None
    source_name: str
    raw_label: str | None
    state: str

    def render(self) -> str:
        reason = self.reason_code or self.state
        label = self.raw_label or self.provider_reference_key
        return f"{self.entity_type}={label} source={self.source_name} reason={reason}"

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "provider_reference_key": self.provider_reference_key,
            "reason_code": self.reason_code,
            "source_name": self.source_name,
            "raw_label": self.raw_label,
            "state": self.state,
        }


@dataclass(frozen=True, slots=True)
class CanonicalMappingValidationSummary:
    referenced_canonical_mapping_count: int
    resolved_canonical_mapping_count: int
    unresolved_count: int
    tracked_count: int
    missing_mapping_record_count: int
    resolved_by_entity_type: dict[str, int]
    unresolved_by_entity_type: dict[str, int]
    unresolved_reference_categories: dict[str, int]

    def render_lines(self) -> tuple[str, ...]:
        return (
            f"referenced_canonical_mapping_count={self.referenced_canonical_mapping_count}",
            f"resolved_canonical_mapping_count={self.resolved_canonical_mapping_count}",
            f"unresolved_count={self.unresolved_count}",
            f"tracked_count={self.tracked_count}",
            f"missing_mapping_record_count={self.missing_mapping_record_count}",
            f"resolved_by_entity_type={_render_counts(self.resolved_by_entity_type)}",
            f"unresolved_by_entity_type={_render_counts(self.unresolved_by_entity_type)}",
            f"unresolved_reference_categories={_render_counts(self.unresolved_reference_categories)}",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "referenced_canonical_mapping_count": self.referenced_canonical_mapping_count,
            "resolved_canonical_mapping_count": self.resolved_canonical_mapping_count,
            "unresolved_count": self.unresolved_count,
            "tracked_count": self.tracked_count,
            "missing_mapping_record_count": self.missing_mapping_record_count,
            "resolved_by_entity_type": dict(self.resolved_by_entity_type),
            "unresolved_by_entity_type": dict(self.unresolved_by_entity_type),
            "unresolved_reference_categories": dict(self.unresolved_reference_categories),
        }


@dataclass(frozen=True, slots=True)
class _CanonicalMappingAnalysis:
    unresolved_references: tuple[UnresolvedReferenceItem, ...]
    summary: CanonicalMappingValidationSummary


@dataclass(frozen=True, slots=True)
class ValuationCoverageSummary:
    imported_row_count: int
    unique_player_count: int
    rows_with_snapshot_id: int
    rows_with_persisted_snapshot: int
    profiles_with_snapshot_id: int
    profiles_with_matching_snapshot: int
    summaries_with_current_value: int
    rows_missing_valuation: tuple[str, ...]

    @property
    def rows_missing_persisted_snapshot(self) -> int:
        return max(self.imported_row_count - self.rows_with_persisted_snapshot, 0)

    def render_lines(self) -> tuple[str, ...]:
        lines = (
            f"imported_rows={self.imported_row_count}",
            f"unique_players={self.unique_player_count}",
            f"rows_with_snapshot_id={self.rows_with_snapshot_id}",
            f"rows_with_persisted_snapshot={self.rows_with_persisted_snapshot}",
            f"profiles_with_snapshot_id={self.profiles_with_snapshot_id}",
            f"profiles_with_matching_snapshot={self.profiles_with_matching_snapshot}",
            f"summaries_with_current_value={self.summaries_with_current_value}",
        )
        if not self.rows_missing_valuation:
            return lines
        return lines + (f"rows_missing_valuation={_render_list(self.rows_missing_valuation)}",)

    def to_dict(self) -> dict[str, object]:
        return {
            "imported_row_count": self.imported_row_count,
            "unique_player_count": self.unique_player_count,
            "rows_with_snapshot_id": self.rows_with_snapshot_id,
            "rows_with_persisted_snapshot": self.rows_with_persisted_snapshot,
            "rows_missing_persisted_snapshot": self.rows_missing_persisted_snapshot,
            "profiles_with_snapshot_id": self.profiles_with_snapshot_id,
            "profiles_with_matching_snapshot": self.profiles_with_matching_snapshot,
            "summaries_with_current_value": self.summaries_with_current_value,
            "rows_missing_valuation": list(self.rows_missing_valuation),
        }


@dataclass(frozen=True, slots=True)
class RealPlayerImportValidationReport:
    batch_key: str
    provider_name: str
    mode: str
    status: str
    submitted_row_count: int
    normalized_row_count: int
    imported_row_count: int
    unique_player_count: int
    rows_by_status: dict[str, int]
    duplicate_candidates: tuple[DuplicateCandidateGroup, ...]
    canonical_mapping_summary: CanonicalMappingValidationSummary
    unresolved_references: tuple[UnresolvedReferenceItem, ...]
    missing_required_fields: tuple[MissingRequiredFieldRow, ...]
    valuation_coverage: ValuationCoverageSummary

    @property
    def resolved_canonical_mapping_count(self) -> int:
        return self.canonical_mapping_summary.resolved_canonical_mapping_count

    @property
    def unresolved_count(self) -> int:
        return self.canonical_mapping_summary.unresolved_count

    @property
    def tracked_count(self) -> int:
        return self.canonical_mapping_summary.tracked_count

    @property
    def missing_mapping_record_count(self) -> int:
        return self.canonical_mapping_summary.missing_mapping_record_count

    @property
    def unresolved_reference_categories(self) -> dict[str, int]:
        return self.canonical_mapping_summary.unresolved_reference_categories

    @property
    def verdict(self) -> str:
        if self.duplicate_candidates:
            return "fail"
        if self.unresolved_count:
            return "fail"
        if self.missing_required_fields:
            return "fail"
        if self.valuation_coverage.rows_missing_persisted_snapshot:
            return "fail"
        return "pass"

    def render_text(self) -> str:
        status_summary = ", ".join(
            f"{status}={count}"
            for status, count in sorted(self.rows_by_status.items())
        ) or "(none)"
        sections = [
            (
                "1. Batch summary",
                (
                    f"batch_key={self.batch_key}",
                    f"provider_name={self.provider_name}",
                    f"mode={self.mode}",
                    f"status={self.status}",
                    f"submitted_row_count={self.submitted_row_count}",
                    f"normalized_row_count={self.normalized_row_count}",
                    f"imported_row_count={self.imported_row_count}",
                    f"unique_player_count={self.unique_player_count}",
                    f"rows_by_status={status_summary}",
                ),
            ),
            (
                "2. Duplicate candidates",
                tuple(item.render() for item in self.duplicate_candidates) or ("none",),
            ),
            (
                "3. Canonical mapping fence",
                self.canonical_mapping_summary.render_lines(),
            ),
            (
                "4. Unresolved mappings",
                tuple(item.render() for item in self.unresolved_references) or ("none",),
            ),
            (
                "5. Players missing required fields",
                tuple(item.render() for item in self.missing_required_fields) or ("none",),
            ),
            (
                "6. Valuation coverage",
                self.valuation_coverage.render_lines(),
            ),
            (
                "7. Verdict",
                (self.verdict,),
            ),
        ]
        rendered: list[str] = []
        for title, lines in sections:
            rendered.append(title)
            rendered.extend(f"- {line}" for line in lines)
            rendered.append("")
        return "\n".join(rendered).rstrip()

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_key": self.batch_key,
            "provider_name": self.provider_name,
            "mode": self.mode,
            "status": self.status,
            "submitted_row_count": self.submitted_row_count,
            "normalized_row_count": self.normalized_row_count,
            "imported_row_count": self.imported_row_count,
            "unique_player_count": self.unique_player_count,
            "rows_by_status": dict(self.rows_by_status),
            "duplicate_candidates": [item.to_dict() for item in self.duplicate_candidates],
            "canonical_mapping_summary": self.canonical_mapping_summary.to_dict(),
            "resolved_canonical_mapping_count": self.resolved_canonical_mapping_count,
            "unresolved_count": self.unresolved_count,
            "tracked_count": self.tracked_count,
            "missing_mapping_record_count": self.missing_mapping_record_count,
            "unresolved_reference_categories": dict(self.unresolved_reference_categories),
            "unresolved_references": [item.to_dict() for item in self.unresolved_references],
            "missing_required_fields": [item.to_dict() for item in self.missing_required_fields],
            "valuation_coverage": self.valuation_coverage.to_dict(),
            "verdict": self.verdict,
        }


@dataclass(slots=True)
class RealPlayerImportValidationService:
    session_factory: sessionmaker[Session]

    def run(
        self,
        *,
        batch_key: str | None = None,
        provider_name: str | None = None,
    ) -> RealPlayerImportValidationReport:
        with self.session_factory() as session:
            batch = self._select_batch(
                session=session,
                batch_key=batch_key,
                provider_name=provider_name,
            )
            rows = list(
                session.scalars(
                    select(RealPlayerImportRow)
                    .where(RealPlayerImportRow.batch_id == batch.id)
                    .order_by(RealPlayerImportRow.row_number.asc(), RealPlayerImportRow.id.asc())
                )
            )
            imported_rows = [row for row in rows if row.status == "imported"]
            rows_by_status = dict(Counter(row.status for row in rows))
            valuation_coverage = self._build_valuation_coverage(session=session, rows=imported_rows)
            canonical_mapping_analysis = self._analyze_canonical_mappings(session=session, rows=rows)
            return RealPlayerImportValidationReport(
                batch_key=batch.batch_key,
                provider_name=batch.provider_name,
                mode=batch.mode,
                status=batch.status,
                submitted_row_count=batch.submitted_row_count,
                normalized_row_count=batch.normalized_row_count,
                imported_row_count=len(imported_rows),
                unique_player_count=valuation_coverage.unique_player_count,
                rows_by_status=rows_by_status,
                duplicate_candidates=self._build_duplicate_candidates(rows),
                canonical_mapping_summary=canonical_mapping_analysis.summary,
                unresolved_references=canonical_mapping_analysis.unresolved_references,
                missing_required_fields=self._build_missing_required_fields(rows),
                valuation_coverage=valuation_coverage,
            )

    def _select_batch(
        self,
        *,
        session: Session,
        batch_key: str | None,
        provider_name: str | None,
    ) -> RealPlayerImportBatch:
        statement = select(RealPlayerImportBatch)
        if batch_key is not None:
            statement = statement.where(RealPlayerImportBatch.batch_key == batch_key)
        if provider_name is not None:
            statement = statement.where(RealPlayerImportBatch.provider_name == provider_name)
        statement = statement.order_by(
            RealPlayerImportBatch.requested_at.desc(),
            RealPlayerImportBatch.created_at.desc(),
            RealPlayerImportBatch.id.desc(),
        )
        batch = session.scalar(statement.limit(1))
        if batch is None:
            filters: list[str] = []
            if batch_key is not None:
                filters.append(f"batch_key={batch_key}")
            if provider_name is not None:
                filters.append(f"provider_name={provider_name}")
            qualifier = " ".join(filters).strip() or "latest batch"
            raise ValueError(f"Real-player import batch was not found for {qualifier}.")
        return batch

    def _build_duplicate_candidates(
        self,
        rows: list[RealPlayerImportRow],
    ) -> tuple[DuplicateCandidateGroup, ...]:
        groups: list[DuplicateCandidateGroup] = []
        for key_type, attribute in (
            ("exact_identity_key", "exact_identity_key"),
            ("name_birthyear_club_key", "name_birthyear_club_key"),
            ("name_birthyear_nationality_key", "name_birthyear_nationality_key"),
        ):
            grouped: dict[str, list[RealPlayerImportRow]] = defaultdict(list)
            for row in rows:
                value = _normalize_text(getattr(row, attribute))
                if not value:
                    continue
                grouped[value].append(row)
            for identity_key, items in grouped.items():
                if len(items) < 2:
                    continue
                player_ids = tuple(sorted({_normalize_text(item.gtex_player_id) for item in items if item.gtex_player_id}))
                groups.append(
                    DuplicateCandidateGroup(
                        key_type=key_type,
                        identity_key=identity_key,
                        row_count=len(items),
                        distinct_player_count=len(player_ids),
                        source_keys=tuple(
                            sorted(
                                f"{item.source_name}:{item.source_player_key}"
                                for item in items
                            )
                        ),
                        player_ids=player_ids,
                        canonical_names=tuple(
                            sorted({_normalize_text(item.canonical_name) for item in items if _normalize_text(item.canonical_name)})
                        ),
                    )
                )
        return tuple(
            sorted(
                groups,
                key=lambda item: (-item.distinct_player_count, -item.row_count, item.key_type, item.identity_key),
            )
        )

    def _analyze_canonical_mappings(
        self,
        *,
        session: Session,
        rows: list[RealPlayerImportRow],
    ) -> _CanonicalMappingAnalysis:
        referenced_keys: dict[str, dict[tuple[str, str], tuple[str, ...]]] = {
            "club": {},
            "competition": {},
        }
        for row in rows:
            for entity_type, lookup_keys in (
                ("club", _reference_lookup_keys(row, entity_type="club")),
                ("competition", _reference_lookup_keys(row, entity_type="competition")),
            ):
                if not lookup_keys:
                    continue
                direct_key = _normalize_text(row.club_reference_key if entity_type == "club" else row.league_reference_key)
                reference_key = direct_key or lookup_keys[0]
                lookup = (row.source_name, reference_key)
                existing = referenced_keys[entity_type].get(lookup, ())
                referenced_keys[entity_type][lookup] = tuple(
                    dict.fromkeys([*existing, *lookup_keys])
                )
        if not referenced_keys["club"] and not referenced_keys["competition"]:
            return _CanonicalMappingAnalysis(
                unresolved_references=(),
                summary=CanonicalMappingValidationSummary(
                    referenced_canonical_mapping_count=0,
                    resolved_canonical_mapping_count=0,
                    unresolved_count=0,
                    tracked_count=0,
                    missing_mapping_record_count=0,
                    resolved_by_entity_type={},
                    unresolved_by_entity_type={},
                    unresolved_reference_categories={},
                ),
            )

        source_names = sorted(
            {
                source_name
                for values in referenced_keys.values()
                for source_name, _ in values
            }
        )
        provider_reference_keys = sorted(
            {
                candidate_key
                for values in referenced_keys.values()
                for lookup_keys in values.values()
                for candidate_key in lookup_keys
            }
        )
        mapping_rows = list(
            session.scalars(
                select(RealPlayerReferenceMapping).where(
                    RealPlayerReferenceMapping.source_name.in_(source_names),
                    RealPlayerReferenceMapping.provider_reference_key.in_(provider_reference_keys),
                    RealPlayerReferenceMapping.entity_type.in_(("club", "competition")),
                )
            )
        )
        resolved_keys = {
            (mapping.entity_type, mapping.source_name, mapping.provider_reference_key)
            for mapping in mapping_rows
            if (
                mapping.is_active
                and mapping.mapping_status in {"resolved", "auto_created"}
                and any(
                    (
                        mapping.canonical_country_id,
                        mapping.canonical_competition_id,
                        mapping.canonical_club_id,
                    )
                )
            )
        }
        unresolved_rows = list(
            session.scalars(
                select(RealPlayerUnresolvedReference).where(
                    RealPlayerUnresolvedReference.source_name.in_(source_names),
                    RealPlayerUnresolvedReference.provider_reference_key.in_(provider_reference_keys),
                    RealPlayerUnresolvedReference.entity_type.in_(("club", "competition")),
                    RealPlayerUnresolvedReference.status != "resolved",
                )
            )
        )
        unresolved_lookup = {
            (row.entity_type, row.source_name, row.provider_reference_key): row
            for row in unresolved_rows
        }

        findings: list[UnresolvedReferenceItem] = []
        resolved_by_entity_type: Counter[str] = Counter()
        for entity_type in ("club", "competition"):
            for source_name, provider_reference_key in sorted(referenced_keys[entity_type]):
                lookup_keys = referenced_keys[entity_type][(source_name, provider_reference_key)]
                if any((entity_type, source_name, candidate_key) in resolved_keys for candidate_key in lookup_keys):
                    resolved_by_entity_type[entity_type] += 1
                    continue
                unresolved = next(
                    (
                        unresolved_lookup.get((entity_type, source_name, candidate_key))
                        for candidate_key in lookup_keys
                        if unresolved_lookup.get((entity_type, source_name, candidate_key)) is not None
                    ),
                    None,
                )
                findings.append(
                    UnresolvedReferenceItem(
                        entity_type=entity_type,
                        provider_reference_key=provider_reference_key,
                        reason_code=unresolved.reason_code if unresolved is not None else None,
                        source_name=source_name,
                        raw_label=unresolved.raw_label if unresolved is not None else None,
                        state="tracked" if unresolved is not None else "missing_mapping_record",
                    )
                )
        unresolved_by_entity_type = Counter(item.entity_type for item in findings)
        unresolved_reference_categories = Counter(
            (
                f"{item.entity_type}:{item.state}:{item.reason_code or item.state}"
                if item.state == "tracked"
                else f"{item.entity_type}:{item.state}"
            )
            for item in findings
        )
        summary = CanonicalMappingValidationSummary(
            referenced_canonical_mapping_count=sum(len(values) for values in referenced_keys.values()),
            resolved_canonical_mapping_count=sum(resolved_by_entity_type.values()),
            unresolved_count=len(findings),
            tracked_count=sum(1 for item in findings if item.state == "tracked"),
            missing_mapping_record_count=sum(1 for item in findings if item.state == "missing_mapping_record"),
            resolved_by_entity_type=dict(sorted(resolved_by_entity_type.items())),
            unresolved_by_entity_type=dict(sorted(unresolved_by_entity_type.items())),
            unresolved_reference_categories=dict(sorted(unresolved_reference_categories.items())),
        )
        return _CanonicalMappingAnalysis(
            unresolved_references=tuple(findings),
            summary=summary,
        )

    def _build_missing_required_fields(
        self,
        rows: list[RealPlayerImportRow],
    ) -> tuple[MissingRequiredFieldRow, ...]:
        findings: list[MissingRequiredFieldRow] = []
        for row in rows:
            raw_payload = row.raw_payload_json if isinstance(row.raw_payload_json, dict) else {}
            normalized_payload = row.normalized_payload_json if isinstance(row.normalized_payload_json, dict) else {}
            missing_fields: list[str] = []
            if not _normalize_text(row.canonical_name):
                missing_fields.append("canonical_name")
            if not (_normalize_text(row.normalized_full_name) or _normalize_text(row.normalized_display_name)):
                missing_fields.append("normalized_name")
            if not (
                _normalize_text(_payload_value(raw_payload, "date_of_birth", "birth_year"))
                or _normalize_text(_payload_value(normalized_payload, "date_of_birth", "birth_year"))
            ):
                missing_fields.append("birth_reference")
            if not (
                _normalize_text(row.nationality_code)
                or _normalize_text(row.normalized_nationality)
                or _normalize_text(_payload_value(raw_payload, "nationality", "nationality_code"))
            ):
                missing_fields.append("nationality")
            if not (
                _normalize_text(row.primary_position_key)
                or _normalize_text(_payload_value(raw_payload, "primary_position"))
            ):
                missing_fields.append("primary_position")
            if row.status == "imported" and not _normalize_text(row.gtex_player_id):
                missing_fields.append("gtex_player_id")
            if not missing_fields:
                continue
            findings.append(
                MissingRequiredFieldRow(
                    row_number=row.row_number,
                    source_name=row.source_name,
                    source_player_key=row.source_player_key,
                    canonical_name=row.canonical_name,
                    status=row.status,
                    missing_fields=tuple(missing_fields),
                )
            )
        return tuple(findings)

    def _build_valuation_coverage(
        self,
        *,
        session: Session,
        rows: list[RealPlayerImportRow],
    ) -> ValuationCoverageSummary:
        player_ids = sorted({_normalize_text(row.gtex_player_id) for row in rows if row.gtex_player_id})
        snapshot_ids = sorted({_normalize_text(row.authoritative_snapshot_id) for row in rows if row.authoritative_snapshot_id})
        profile_lookup = {
            profile.gtex_player_id: profile
            for profile in session.scalars(
                select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id.in_(player_ids))
            )
        } if player_ids else {}
        summary_lookup = {
            summary.player_id: summary
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(player_ids))
            )
        } if player_ids else {}
        snapshot_lookup = {
            snapshot.id: snapshot
            for snapshot in session.scalars(
                select(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.id.in_(snapshot_ids))
            )
        } if snapshot_ids else {}

        missing_rows: list[str] = []
        rows_with_snapshot_id = 0
        rows_with_persisted_snapshot = 0
        profiles_with_snapshot_id = 0
        profiles_with_matching_snapshot = 0
        summaries_with_current_value = 0
        for row in rows:
            source_key = f"{row.source_name}:{row.source_player_key}"
            row_has_gap = False
            if _normalize_text(row.authoritative_snapshot_id):
                rows_with_snapshot_id += 1
            else:
                row_has_gap = True
            if row.authoritative_snapshot_id in snapshot_lookup:
                rows_with_persisted_snapshot += 1
            else:
                row_has_gap = True
            profile = profile_lookup.get(_normalize_text(row.gtex_player_id))
            if profile is not None and _normalize_text(profile.pricing_snapshot_id):
                profiles_with_snapshot_id += 1
                if profile.pricing_snapshot_id == row.authoritative_snapshot_id and profile.pricing_snapshot_id in snapshot_lookup:
                    profiles_with_matching_snapshot += 1
            else:
                row_has_gap = True
            summary = summary_lookup.get(_normalize_text(row.gtex_player_id))
            if summary is not None and summary.current_value_credits is not None:
                summaries_with_current_value += 1
            else:
                row_has_gap = True
            if row_has_gap:
                missing_rows.append(source_key)
        return ValuationCoverageSummary(
            imported_row_count=len(rows),
            unique_player_count=len(player_ids),
            rows_with_snapshot_id=rows_with_snapshot_id,
            rows_with_persisted_snapshot=rows_with_persisted_snapshot,
            profiles_with_snapshot_id=profiles_with_snapshot_id,
            profiles_with_matching_snapshot=profiles_with_matching_snapshot,
            summaries_with_current_value=summaries_with_current_value,
            rows_missing_valuation=tuple(sorted(missing_rows)),
        )
