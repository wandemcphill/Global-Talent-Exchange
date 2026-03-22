from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Player
from app.models.player_cards import PlayerMarketValueSnapshot
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink
from app.players.read_models import PlayerSummaryReadModel
from app.schemas.real_player_ingestion import RealPlayerSeedInput
from app.value_engine.read_models import PlayerValueSnapshotRecord

from .real_player_identity_normalizer import names_equivalent, normalize_identity_name


@dataclass(frozen=True, slots=True)
class RealPlayerAuditFinding:
    finding_type: str
    normalized_key: str
    gtex_player_ids: tuple[str, ...] = ()
    source_keys: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    resolution_status: str = "open"
    required_action: str | None = None
    details: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        payload = {
            "finding_type": self.finding_type,
            "normalized_key": self.normalized_key,
            "gtex_player_ids": list(self.gtex_player_ids),
            "source_keys": list(self.source_keys),
            "candidate_ids": list(self.candidate_ids),
            "resolution_status": self.resolution_status,
            "required_action": self.required_action,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(frozen=True, slots=True)
class SurfaceBaselineEntry:
    player_id: str
    is_real_player: bool
    source_provider: str
    provider_external_id: str
    canonical_display_name: str | None
    summary_last_snapshot_id: str | None
    summary_real_profile: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "player_id": self.player_id,
            "is_real_player": self.is_real_player,
            "source_provider": self.source_provider,
            "provider_external_id": self.provider_external_id,
            "canonical_display_name": self.canonical_display_name,
            "summary_last_snapshot_id": self.summary_last_snapshot_id,
            "summary_real_profile": self.summary_real_profile,
        }


@dataclass(frozen=True, slots=True)
class SurfaceBaseline:
    entries: tuple[SurfaceBaselineEntry, ...]

    def by_player_id(self) -> dict[str, SurfaceBaselineEntry]:
        return {entry.player_id: entry for entry in self.entries}


@dataclass(frozen=True, slots=True)
class AuditedRealPlayerRow:
    gtex_player_id: str
    source_name: str
    source_player_key: str
    canonical_name: str
    player_full_name: str
    canonical_display_name: str | None
    nationality: str | None
    current_club_name: str | None
    date_of_birth: date | None
    birth_year: int | None
    pricing_snapshot_id: str | None
    summary_last_snapshot_id: str | None
    summary_pricing_snapshot_id: str | None
    summary_real_profile: bool
    pricing_record_exists: bool
    market_snapshot_exists: bool
    is_real_player: bool

    @property
    def source_key(self) -> str:
        return f"{self.source_name}:{self.source_player_key}"

    @property
    def primary_name(self) -> str:
        return self.canonical_name or self.canonical_display_name or self.player_full_name


@dataclass(frozen=True, slots=True)
class RealPlayerIdentityAuditReport:
    ingestion_batch_id: str
    target_player_ids: tuple[str, ...]
    duplicate_findings: tuple[RealPlayerAuditFinding, ...] = ()
    ambiguous_findings: tuple[RealPlayerAuditFinding, ...] = ()
    pricing_findings: tuple[RealPlayerAuditFinding, ...] = ()
    stability_findings: tuple[RealPlayerAuditFinding, ...] = ()

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_findings)

    @property
    def ambiguous_count(self) -> int:
        return len(self.ambiguous_findings)

    @property
    def missing_pricing_count(self) -> int:
        return len(self.pricing_findings)

    @property
    def stability_count(self) -> int:
        return len(self.stability_findings)

    @property
    def hard_failure_count(self) -> int:
        return self.duplicate_count + self.ambiguous_count + self.missing_pricing_count + self.stability_count

    def is_clean(self) -> bool:
        return self.hard_failure_count == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "ingestion_batch_id": self.ingestion_batch_id,
            "target_player_ids": list(self.target_player_ids),
            "duplicate_count": self.duplicate_count,
            "ambiguous_count": self.ambiguous_count,
            "missing_pricing_count": self.missing_pricing_count,
            "stability_count": self.stability_count,
            "hard_failure_count": self.hard_failure_count,
            "duplicate_findings": [finding.to_dict() for finding in self.duplicate_findings],
            "ambiguous_findings": [finding.to_dict() for finding in self.ambiguous_findings],
            "pricing_findings": [finding.to_dict() for finding in self.pricing_findings],
            "stability_findings": [finding.to_dict() for finding in self.stability_findings],
        }


@dataclass(slots=True)
class RealPlayerIdentityAuditService:
    def capture_surface_baseline(self, session: Session) -> SurfaceBaseline:
        summaries = {
            summary.player_id: summary
            for summary in session.scalars(select(PlayerSummaryReadModel))
        }
        players = list(session.scalars(select(Player).order_by(Player.id.asc())))
        return SurfaceBaseline(
            entries=tuple(
                SurfaceBaselineEntry(
                    player_id=player.id,
                    is_real_player=bool(player.is_real_player),
                    source_provider=player.source_provider,
                    provider_external_id=player.provider_external_id,
                    canonical_display_name=player.canonical_display_name,
                    summary_last_snapshot_id=summaries.get(player.id).last_snapshot_id if summaries.get(player.id) is not None else None,
                    summary_real_profile=_summary_real_profile_flag(summaries.get(player.id)),
                )
                for player in players
            )
        )

    def detect_payload_collisions(self, players: Sequence[RealPlayerSeedInput]) -> tuple[RealPlayerAuditFinding, ...]:
        findings: list[RealPlayerAuditFinding] = []
        rows = [
            _PayloadAuditRow(
                source_name=player.source_name,
                source_player_key=player.source_player_key,
                canonical_name=player.canonical_name,
                nationality=player.nationality or player.nationality_code,
                current_club_name=player.current_real_world_club,
                date_of_birth=player.date_of_birth,
                birth_year=player.birth_year,
            )
            for player in players
        ]
        findings.extend(self._duplicate_name_dob_findings(rows))
        findings.extend(self._duplicate_name_nat_club_findings(rows))
        findings.extend(self._normalization_collision_findings(rows))
        return tuple(findings)

    def audit_batch(
        self,
        session: Session,
        *,
        ingestion_batch_id: str,
        baseline: SurfaceBaseline | None = None,
    ) -> RealPlayerIdentityAuditReport:
        target_rows = self._load_audit_rows(session, ingestion_batch_id=ingestion_batch_id)
        all_rows = self._load_audit_rows(session)
        target_player_ids = tuple(sorted({row.gtex_player_id for row in target_rows}))
        all_player_ids = tuple(sorted({row.gtex_player_id for row in all_rows}))

        duplicate_findings = [
            *self._duplicate_external_id_findings(all_rows),
            *self._duplicate_name_dob_findings(all_rows),
            *self._duplicate_name_nat_club_findings(all_rows),
            *self._normalization_collision_findings(all_rows),
            *self._orphaned_mapping_findings(all_rows),
            *self._multiple_external_identity_findings(session, all_player_ids),
        ]
        pricing_findings = self._pricing_findings(target_rows)
        stability_findings = self._stability_findings(session, baseline=baseline, target_player_ids=target_player_ids)

        return RealPlayerIdentityAuditReport(
            ingestion_batch_id=ingestion_batch_id,
            target_player_ids=target_player_ids,
            duplicate_findings=tuple(duplicate_findings),
            ambiguous_findings=(),
            pricing_findings=tuple(pricing_findings),
            stability_findings=tuple(stability_findings),
        )

    def _load_audit_rows(self, session: Session, *, ingestion_batch_id: str | None = None) -> list[AuditedRealPlayerRow]:
        profile_statement = select(RealPlayerProfile)
        if ingestion_batch_id is not None:
            profile_statement = profile_statement.where(RealPlayerProfile.ingestion_batch_id == ingestion_batch_id)
        profiles = list(session.scalars(profile_statement))
        if not profiles:
            return []

        player_ids = tuple(sorted({profile.gtex_player_id for profile in profiles}))
        source_link_ids = tuple(sorted({profile.source_link_id for profile in profiles}))

        players = {
            player.id: player
            for player in session.scalars(
                select(Player)
                .options(
                    selectinload(Player.country),
                    selectinload(Player.current_club),
                )
                .where(Player.id.in_(player_ids))
            )
        }
        source_links = {
            source_link.id: source_link
            for source_link in session.scalars(
                select(RealPlayerSourceLink).where(RealPlayerSourceLink.id.in_(source_link_ids))
            )
        }
        summaries = {
            summary.player_id: summary
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(player_ids))
            )
        }
        pricing_records = {
            record.id: record
            for record in session.scalars(
                select(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.player_id.in_(player_ids))
            )
        }
        market_snapshots_by_player: dict[str, list[PlayerMarketValueSnapshot]] = defaultdict(list)
        for snapshot in session.scalars(
            select(PlayerMarketValueSnapshot).where(PlayerMarketValueSnapshot.player_id.in_(player_ids))
        ):
            market_snapshots_by_player[snapshot.player_id].append(snapshot)

        rows: list[AuditedRealPlayerRow] = []
        for profile in profiles:
            player = players.get(profile.gtex_player_id)
            source_link = source_links.get(profile.source_link_id)
            summary = summaries.get(profile.gtex_player_id)
            if player is None or source_link is None:
                rows.append(
                    AuditedRealPlayerRow(
                        gtex_player_id=profile.gtex_player_id,
                        source_name=profile.source_name,
                        source_player_key=profile.source_player_key,
                        canonical_name=profile.canonical_name,
                        player_full_name=profile.canonical_name,
                        canonical_display_name=None,
                        nationality=profile.nationality,
                        current_club_name=profile.current_club_name,
                        date_of_birth=profile.date_of_birth,
                        birth_year=profile.birth_year,
                        pricing_snapshot_id=profile.pricing_snapshot_id,
                        summary_last_snapshot_id=None,
                        summary_pricing_snapshot_id=None,
                        summary_real_profile=False,
                        pricing_record_exists=bool(profile.pricing_snapshot_id and pricing_records.get(profile.pricing_snapshot_id)),
                        market_snapshot_exists=False,
                        is_real_player=False,
                    )
                )
                continue

            summary_pricing_snapshot_id = _summary_pricing_snapshot_id(summary)
            market_snapshot_exists = any(
                isinstance(snapshot.metadata_json, dict)
                and snapshot.metadata_json.get("authoritative_snapshot_id") == profile.pricing_snapshot_id
                for snapshot in market_snapshots_by_player.get(player.id, ())
            )
            rows.append(
                AuditedRealPlayerRow(
                    gtex_player_id=player.id,
                    source_name=source_link.source_name,
                    source_player_key=source_link.source_player_key,
                    canonical_name=profile.canonical_name,
                    player_full_name=player.full_name,
                    canonical_display_name=player.canonical_display_name,
                    nationality=profile.nationality or getattr(player.country, "name", None),
                    current_club_name=profile.current_club_name or player.real_world_club_name or getattr(player.current_club, "name", None),
                    date_of_birth=profile.date_of_birth or player.date_of_birth,
                    birth_year=profile.birth_year or (player.date_of_birth.year if player.date_of_birth is not None else None),
                    pricing_snapshot_id=profile.pricing_snapshot_id,
                    summary_last_snapshot_id=summary.last_snapshot_id if summary is not None else None,
                    summary_pricing_snapshot_id=summary_pricing_snapshot_id,
                    summary_real_profile=_summary_real_profile_flag(summary),
                    pricing_record_exists=bool(profile.pricing_snapshot_id and pricing_records.get(profile.pricing_snapshot_id)),
                    market_snapshot_exists=market_snapshot_exists,
                    is_real_player=bool(player.is_real_player),
                )
            )
        return rows

    def _duplicate_external_id_findings(self, rows: Sequence[AuditedRealPlayerRow | _PayloadAuditRow]) -> list[RealPlayerAuditFinding]:
        groups: dict[tuple[str, str], list[AuditedRealPlayerRow | _PayloadAuditRow]] = defaultdict(list)
        for row in rows:
            groups[(row.source_name, row.source_player_key)].append(row)
        return [
            _build_finding(
                finding_type="duplicate_authoritative_external_id",
                normalized_key=f"{source_name}:{source_player_key}",
                rows=group_rows,
                required_action="Keep exactly one GTEX canonical identity per authoritative external id.",
            )
            for (source_name, source_player_key), group_rows in groups.items()
            if len(group_rows) > 1
        ]

    def _duplicate_name_dob_findings(self, rows: Sequence[AuditedRealPlayerRow | _PayloadAuditRow]) -> list[RealPlayerAuditFinding]:
        groups: dict[tuple[str, str], list[AuditedRealPlayerRow | _PayloadAuditRow]] = defaultdict(list)
        for row in rows:
            if row.date_of_birth is None:
                continue
            groups[(normalize_identity_name(row.canonical_name).normalized, row.date_of_birth.isoformat())].append(row)
        return [
            _build_finding(
                finding_type="duplicate_normalized_name_dob",
                normalized_key=f"{name_key}|{dob}",
                rows=group_rows,
                required_action="Merge or relink duplicate canonical identities sharing the same normalized name and DOB.",
            )
            for (name_key, dob), group_rows in groups.items()
            if len(group_rows) > 1
        ]

    def _duplicate_name_nat_club_findings(self, rows: Sequence[AuditedRealPlayerRow | _PayloadAuditRow]) -> list[RealPlayerAuditFinding]:
        groups: dict[tuple[str, str, str, str], list[AuditedRealPlayerRow | _PayloadAuditRow]] = defaultdict(list)
        for row in rows:
            if row.date_of_birth is not None or row.birth_year is None:
                continue
            club_key = normalize_identity_name(row.current_club_name).normalized
            nationality_key = normalize_identity_name(row.nationality).normalized
            if not club_key or not nationality_key:
                continue
            groups[(normalize_identity_name(row.canonical_name).normalized, str(row.birth_year), nationality_key, club_key)].append(row)
        return [
            _build_finding(
                finding_type="duplicate_normalized_name_nationality_club",
                normalized_key="|".join(group_key),
                rows=group_rows,
                required_action="Resolve duplicate canonical identities sharing the same normalized fallback identity key.",
            )
            for group_key, group_rows in groups.items()
            if len(group_rows) > 1
        ]

    def _normalization_collision_findings(self, rows: Sequence[AuditedRealPlayerRow | _PayloadAuditRow]) -> list[RealPlayerAuditFinding]:
        findings: list[RealPlayerAuditFinding] = []
        name_groups: dict[str, list[AuditedRealPlayerRow | _PayloadAuditRow]] = defaultdict(list)
        for row in rows:
            normalized_name = normalize_identity_name(row.canonical_name).normalized
            if normalized_name:
                name_groups[normalized_name].append(row)
        for normalized_name, group_rows in name_groups.items():
            if len(group_rows) < 2:
                continue
            if not _has_related_name_pair(group_rows):
                continue
            if not _has_collision_identity_pair(group_rows):
                continue
            findings.append(
                _build_finding(
                    finding_type="normalization_collision",
                    normalized_key=normalized_name,
                    rows=group_rows,
                    required_action="Review accent, spacing, punctuation, and shortened-name normalization before allowing multiple GTEX identities.",
                )
            )
        return findings

    def _orphaned_mapping_findings(self, rows: Sequence[AuditedRealPlayerRow]) -> list[RealPlayerAuditFinding]:
        findings: list[RealPlayerAuditFinding] = []
        for row in rows:
            if row.is_real_player and row.summary_real_profile:
                continue
            findings.append(
                RealPlayerAuditFinding(
                    finding_type="orphaned_mapping",
                    normalized_key=row.source_key,
                    gtex_player_ids=(row.gtex_player_id,),
                    source_keys=(row.source_key,),
                    required_action="Ensure each ingested real player has a real-player flag, source link, profile, and summary projection.",
                    details={
                        "is_real_player": row.is_real_player,
                        "summary_real_profile": row.summary_real_profile,
                    },
                )
            )
        return findings

    def _multiple_external_identity_findings(
        self,
        session: Session,
        target_player_ids: Sequence[str],
    ) -> list[RealPlayerAuditFinding]:
        if not target_player_ids:
            return []
        groups: dict[str, list[RealPlayerSourceLink]] = defaultdict(list)
        for source_link in session.scalars(
            select(RealPlayerSourceLink).where(RealPlayerSourceLink.gtex_player_id.in_(tuple(target_player_ids)))
        ):
            groups[source_link.gtex_player_id].append(source_link)
        findings: list[RealPlayerAuditFinding] = []
        for player_id, source_links in groups.items():
            if len(source_links) <= 1:
                continue
            findings.append(
                RealPlayerAuditFinding(
                    finding_type="multiple_external_identities_per_gtex_identity",
                    normalized_key=player_id,
                    gtex_player_ids=(player_id,),
                    source_keys=tuple(sorted(f"{source_link.source_name}:{source_link.source_player_key}" for source_link in source_links)),
                    required_action="Review whether multiple external identities were linked to one GTEX player incorrectly.",
                )
            )
        return findings

    def _pricing_findings(self, rows: Sequence[AuditedRealPlayerRow]) -> list[RealPlayerAuditFinding]:
        findings: list[RealPlayerAuditFinding] = []
        for row in rows:
            if row.pricing_snapshot_id and row.pricing_record_exists and row.market_snapshot_exists and row.summary_pricing_snapshot_id == row.pricing_snapshot_id:
                continue
            findings.append(
                RealPlayerAuditFinding(
                    finding_type="missing_authoritative_pricing",
                    normalized_key=row.source_key,
                    gtex_player_ids=(row.gtex_player_id,),
                    source_keys=(row.source_key,),
                    required_action="Ensure every ingested player has a persisted authoritative pricing snapshot and market surface record.",
                    details={
                        "pricing_snapshot_id": row.pricing_snapshot_id,
                        "pricing_record_exists": row.pricing_record_exists,
                        "market_snapshot_exists": row.market_snapshot_exists,
                        "summary_pricing_snapshot_id": row.summary_pricing_snapshot_id,
                    },
                )
            )
        return findings

    def _stability_findings(
        self,
        session: Session,
        *,
        baseline: SurfaceBaseline | None,
        target_player_ids: Sequence[str],
    ) -> list[RealPlayerAuditFinding]:
        if baseline is None:
            return []
        target_player_id_set = set(target_player_ids)
        baseline_entries = {
            player_id: entry
            for player_id, entry in baseline.by_player_id().items()
            if player_id not in target_player_id_set
        }
        if not baseline_entries:
            return []

        players = {
            player.id: player
            for player in session.scalars(
                select(Player).where(Player.id.in_(tuple(baseline_entries.keys())))
            )
        }
        summaries = {
            summary.player_id: summary
            for summary in session.scalars(
                select(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(tuple(baseline_entries.keys())))
            )
        }
        findings: list[RealPlayerAuditFinding] = []
        for player_id, entry in baseline_entries.items():
            player = players.get(player_id)
            summary = summaries.get(player_id)
            if player is None:
                findings.append(
                    RealPlayerAuditFinding(
                        finding_type="mixed_surface_player_removed",
                        normalized_key=player_id,
                        candidate_ids=(player_id,),
                        required_action="Non-target players should not disappear during real-player ingestion.",
                    )
                )
                continue
            summary_real_profile = _summary_real_profile_flag(summary)
            summary_last_snapshot_id = summary.last_snapshot_id if summary is not None else None
            if (
                bool(player.is_real_player) == entry.is_real_player
                and player.canonical_display_name == entry.canonical_display_name
                and summary_real_profile == entry.summary_real_profile
                and summary_last_snapshot_id == entry.summary_last_snapshot_id
            ):
                continue
            findings.append(
                RealPlayerAuditFinding(
                    finding_type="mixed_real_regen_surface_regression",
                    normalized_key=player_id,
                    candidate_ids=(player_id,),
                    required_action="Non-target player identity and summary surfaces must remain unchanged.",
                    details={
                        "baseline": entry.to_dict(),
                        "current": {
                            "is_real_player": bool(player.is_real_player),
                            "canonical_display_name": player.canonical_display_name,
                            "summary_last_snapshot_id": summary_last_snapshot_id,
                            "summary_real_profile": summary_real_profile,
                        },
                    },
                )
            )
        return findings


@dataclass(frozen=True, slots=True)
class _PayloadAuditRow:
    source_name: str
    source_player_key: str
    canonical_name: str
    nationality: str | None
    current_club_name: str | None
    date_of_birth: date | None
    birth_year: int | None

    @property
    def source_key(self) -> str:
        return f"{self.source_name}:{self.source_player_key}"


def _summary_real_profile_flag(summary: PlayerSummaryReadModel | None) -> bool:
    if summary is None or not isinstance(summary.summary_json, dict):
        return False
    real_player_profile = summary.summary_json.get("real_player_profile")
    return bool(isinstance(real_player_profile, dict) and real_player_profile.get("is_real_player"))


def _summary_pricing_snapshot_id(summary: PlayerSummaryReadModel | None) -> str | None:
    if summary is None or not isinstance(summary.summary_json, dict):
        return None
    real_player_profile = summary.summary_json.get("real_player_profile")
    if not isinstance(real_player_profile, dict):
        return None
    value = real_player_profile.get("pricing_snapshot_id")
    return str(value) if value else None


def _has_related_name_pair(rows: Sequence[AuditedRealPlayerRow | _PayloadAuditRow]) -> bool:
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if names_equivalent(left.canonical_name, right.canonical_name):
                return True
    return False


def _has_collision_identity_pair(rows: Sequence[AuditedRealPlayerRow | _PayloadAuditRow]) -> bool:
    for index, left in enumerate(rows):
        for right in rows[index + 1:]:
            if _rows_share_collision_identity(left, right):
                return True
    return False


def _rows_share_collision_identity(left: AuditedRealPlayerRow | _PayloadAuditRow, right: AuditedRealPlayerRow | _PayloadAuditRow) -> bool:
    if not names_equivalent(left.canonical_name, right.canonical_name):
        return False
    left_nationality = normalize_identity_name(left.nationality).normalized
    right_nationality = normalize_identity_name(right.nationality).normalized
    if left.date_of_birth is not None and right.date_of_birth is not None:
        if left.date_of_birth == right.date_of_birth:
            return True
    if left.birth_year is None or right.birth_year is None:
        return False
    if left.birth_year != right.birth_year:
        return False
    if left_nationality and right_nationality and left_nationality == right_nationality:
        return True
    left_club = normalize_identity_name(left.current_club_name).normalized
    right_club = normalize_identity_name(right.current_club_name).normalized
    return bool(left_club and right_club and left_club == right_club)


def _build_finding(
    *,
    finding_type: str,
    normalized_key: str,
    rows: Iterable[AuditedRealPlayerRow | _PayloadAuditRow],
    required_action: str,
) -> RealPlayerAuditFinding:
    row_list = list(rows)
    gtex_player_ids = tuple(sorted({row.gtex_player_id for row in row_list if isinstance(row, AuditedRealPlayerRow)}))
    source_keys = tuple(sorted({row.source_key for row in row_list}))
    return RealPlayerAuditFinding(
        finding_type=finding_type,
        normalized_key=normalized_key,
        gtex_player_ids=gtex_player_ids,
        source_keys=source_keys,
        required_action=required_action,
    )


__all__ = [
    "RealPlayerAuditFinding",
    "RealPlayerIdentityAuditReport",
    "RealPlayerIdentityAuditService",
    "SurfaceBaseline",
    "SurfaceBaselineEntry",
]
