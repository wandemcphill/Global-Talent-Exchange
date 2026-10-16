from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from typing import Iterable, Mapping

from app.ingestion.normalizers import clean_name, slugify
from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord
from app.ingestion.second_zip_base_eligibility import (
    SecondZipBaseEligibilityPolicy,
    SecondZipBaseEligibilityResult,
    evaluate_second_zip_players_csv_row,
)


DEFAULT_SECOND_ZIP_FALLBACK_MARKET_VALUE_EUR = 500_000
SECOND_ZIP_FREE_AGENT_CLUB_KEY = "free-agent"
SECOND_ZIP_FREE_AGENT_CLUB_NAME = "Free Agent"

_NULLISH_TEXT_VALUES = frozenset({"", "null", "none", "n/a", "na", "unknown"})
_DEDUPE_PASS_STATUSES = frozenset({"passed", "clear", "unique", "resolved"})
_DEDUPE_FAIL_STATUSES = frozenset({"failed", "duplicate", "blocked", "review_required", "open"})
_RESOLVED_MAPPING_STATUSES = frozenset({"resolved", "auto_created"})
_FREE_AGENT_LABELS = frozenset({"free agent", "without club", "no club", "unattached"})


class SecondZipPublishTier(StrEnum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3 = "tier_3"


class SecondZipValuationSource(StrEnum):
    SOURCE_MARKET_VALUE = "source_market_value"
    FALLBACK_MARKET_VALUE = "fallback_market_value"


class SecondZipClubAssignmentType(StrEnum):
    RESOLVED_CLUB = "resolved_club"
    CLUB_PLACEHOLDER = "club_placeholder"
    FREE_AGENT_FALLBACK = "free_agent_fallback"


@dataclass(frozen=True, slots=True)
class SecondZipResolvedValuation:
    market_value_eur: int
    source: SecondZipValuationSource
    is_fallback: bool
    reason_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "market_value_eur": self.market_value_eur,
            "source": self.source.value,
            "is_fallback": self.is_fallback,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class SecondZipClubAssignment:
    assignment_type: SecondZipClubAssignmentType
    club_name: str
    club_key: str
    competition_name: str | None
    competition_key: str | None
    is_fallback: bool
    reason_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "assignment_type": self.assignment_type.value,
            "club_name": self.club_name,
            "club_key": self.club_key,
            "competition_name": self.competition_name,
            "competition_key": self.competition_key,
            "is_fallback": self.is_fallback,
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True, slots=True)
class SecondZipPublishReadinessResult:
    provider_player_id: str
    full_name: str
    publish_ready: bool
    publish_tier: SecondZipPublishTier
    dedupe_passed: bool
    hard_validation_blockers: tuple[str, ...]
    base_eligibility: SecondZipBaseEligibilityResult
    valuation: SecondZipResolvedValuation
    club_assignment: SecondZipClubAssignment
    publish_blockers: tuple[str, ...]
    fallback_count: int
    freshness_at: datetime | None

    def to_dict(self) -> dict[str, object]:
        return {
            "provider_player_id": self.provider_player_id,
            "full_name": self.full_name,
            "publish_ready": self.publish_ready,
            "publish_tier": self.publish_tier.value,
            "dedupe_passed": self.dedupe_passed,
            "hard_validation_blockers": list(self.hard_validation_blockers),
            "base_eligibility": self.base_eligibility.to_dict(),
            "valuation": self.valuation.to_dict(),
            "club_assignment": self.club_assignment.to_dict(),
            "publish_blockers": list(self.publish_blockers),
            "fallback_count": self.fallback_count,
            "freshness_at": self.freshness_at.isoformat() if self.freshness_at is not None else None,
        }


@dataclass(slots=True)
class SecondZipPublishReadinessService:
    reference_date: date
    fallback_market_value_eur: int = DEFAULT_SECOND_ZIP_FALLBACK_MARKET_VALUE_EUR
    free_agent_club_name: str = SECOND_ZIP_FREE_AGENT_CLUB_NAME
    free_agent_club_key: str = SECOND_ZIP_FREE_AGENT_CLUB_KEY

    def evaluate_record(
        self,
        record: RealPlayerImportStagingRecord,
    ) -> SecondZipPublishReadinessResult:
        payload = _merged_payload(record)
        metadata = _mapping_dict(record.metadata_json)
        base_eligibility = evaluate_second_zip_players_csv_row(
            payload,
            policy=SecondZipBaseEligibilityPolicy(reference_date=self.reference_date),
        )
        dedupe_passed = _dedupe_passed(metadata)
        hard_validation_blockers = _hard_validation_blockers(metadata)
        valuation = self._resolve_valuation(payload)
        club_assignment = self._resolve_club_assignment(record, payload=payload, metadata=metadata)

        publish_blockers: list[str] = []
        if not base_eligibility.eligible:
            publish_blockers.extend(
                f"base_import_filter:{reason_code}"
                for reason_code in base_eligibility.exclusion_reason_codes
            )
        if not dedupe_passed:
            publish_blockers.append("dedupe_failed")
        publish_blockers.extend(
            f"hard_validation_blocker:{blocker}"
            for blocker in hard_validation_blockers
        )

        publish_ready = not publish_blockers
        fallback_count = int(valuation.is_fallback) + int(club_assignment.is_fallback)
        publish_tier = self._publish_tier(
            publish_ready=publish_ready,
            valuation=valuation,
            club_assignment=club_assignment,
        )
        return SecondZipPublishReadinessResult(
            provider_player_id=record.provider_player_id,
            full_name=record.full_name,
            publish_ready=publish_ready,
            publish_tier=publish_tier,
            dedupe_passed=dedupe_passed,
            hard_validation_blockers=hard_validation_blockers,
            base_eligibility=base_eligibility,
            valuation=valuation,
            club_assignment=club_assignment,
            publish_blockers=tuple(dict.fromkeys(publish_blockers)),
            fallback_count=fallback_count,
            freshness_at=_freshness_at(record),
        )

    def evaluate_records(
        self,
        records: Iterable[RealPlayerImportStagingRecord],
    ) -> tuple[SecondZipPublishReadinessResult, ...]:
        evaluations = [self.evaluate_record(record) for record in records]
        return tuple(sorted(evaluations, key=_publish_sort_key))

    def select_publish_ready(
        self,
        records: Iterable[RealPlayerImportStagingRecord],
        *,
        allowed_tiers: tuple[SecondZipPublishTier, ...] = (
            SecondZipPublishTier.TIER_1,
            SecondZipPublishTier.TIER_2,
        ),
    ) -> tuple[SecondZipPublishReadinessResult, ...]:
        return tuple(
            evaluation
            for evaluation in self.evaluate_records(records)
            if evaluation.publish_ready and evaluation.publish_tier in allowed_tiers
        )

    def _resolve_valuation(
        self,
        payload: Mapping[str, object],
    ) -> SecondZipResolvedValuation:
        source_market_value = _coerce_positive_int(payload.get("market_value_in_eur"))
        if source_market_value is not None:
            return SecondZipResolvedValuation(
                market_value_eur=source_market_value,
                source=SecondZipValuationSource.SOURCE_MARKET_VALUE,
                is_fallback=False,
            )
        return SecondZipResolvedValuation(
            market_value_eur=self.fallback_market_value_eur,
            source=SecondZipValuationSource.FALLBACK_MARKET_VALUE,
            is_fallback=True,
            reason_code="missing_market_value_in_eur",
        )

    def _resolve_club_assignment(
        self,
        record: RealPlayerImportStagingRecord,
        *,
        payload: Mapping[str, object],
        metadata: Mapping[str, object],
    ) -> SecondZipClubAssignment:
        mapping_root = _reference_mapping_root(metadata)
        club_mapping = _mapping_dict(mapping_root.get("club"))
        competition_mapping = _mapping_dict(mapping_root.get("competition"))

        source_club_name = _first_text(
            record.provider_club_name,
            payload.get("current_club_name"),
            payload.get("current_real_world_club"),
        )
        source_club_key = _first_text(
            record.provider_club_id,
            payload.get("current_club_id"),
            payload.get("current_real_world_club_key"),
        )
        competition_name = _first_text(
            record.provider_competition_name,
            payload.get("current_club_domestic_competition_name"),
            payload.get("current_real_world_league"),
        )
        competition_key = _first_text(
            record.provider_competition_id,
            payload.get("current_club_domestic_competition_id"),
            payload.get("current_real_world_league_key"),
        )
        club_status = _status_value(club_mapping.get("status"))
        competition_name = _first_text(
            competition_name,
            competition_mapping.get("display_name"),
            competition_mapping.get("canonical_name"),
        )
        competition_key = _first_text(
            competition_key,
            competition_mapping.get("provider_reference_key"),
            competition_mapping.get("canonical_competition_id"),
        )

        if club_status in _RESOLVED_MAPPING_STATUSES or _first_text(
            club_mapping.get("canonical_club_id"),
            club_mapping.get("canonical_id"),
        ):
            resolved_name = _first_text(
                source_club_name,
                club_mapping.get("display_name"),
                club_mapping.get("canonical_name"),
            ) or self.free_agent_club_name
            resolved_key = _first_text(
                source_club_key,
                club_mapping.get("provider_reference_key"),
                club_mapping.get("canonical_club_id"),
            ) or self.free_agent_club_key
            return SecondZipClubAssignment(
                assignment_type=SecondZipClubAssignmentType.RESOLVED_CLUB,
                club_name=resolved_name,
                club_key=resolved_key,
                competition_name=competition_name,
                competition_key=competition_key,
                is_fallback=False,
            )

        if _is_free_agent_label(source_club_name) or (
            source_club_name is None and source_club_key is None
        ):
            return SecondZipClubAssignment(
                assignment_type=SecondZipClubAssignmentType.FREE_AGENT_FALLBACK,
                club_name=self.free_agent_club_name,
                club_key=self.free_agent_club_key,
                competition_name=competition_name,
                competition_key=competition_key,
                is_fallback=True,
                reason_code="missing_or_free_agent_club",
            )

        placeholder_name = source_club_name or self.free_agent_club_name
        placeholder_key = f"placeholder:{source_club_key or slugify(placeholder_name)}"
        return SecondZipClubAssignment(
            assignment_type=SecondZipClubAssignmentType.CLUB_PLACEHOLDER,
            club_name=placeholder_name,
            club_key=placeholder_key,
            competition_name=competition_name,
            competition_key=competition_key,
            is_fallback=True,
            reason_code="unresolved_club_mapping",
        )

    @staticmethod
    def _publish_tier(
        *,
        publish_ready: bool,
        valuation: SecondZipResolvedValuation,
        club_assignment: SecondZipClubAssignment,
    ) -> SecondZipPublishTier:
        if not publish_ready:
            return SecondZipPublishTier.TIER_3
        if not valuation.is_fallback and not club_assignment.is_fallback:
            return SecondZipPublishTier.TIER_1
        return SecondZipPublishTier.TIER_2


def _merged_payload(record: RealPlayerImportStagingRecord) -> dict[str, object]:
    payload = dict(record.latest_payload_json) if isinstance(record.latest_payload_json, dict) else {}
    payload.setdefault("player_id", record.provider_player_id)
    payload.setdefault("name", record.full_name)
    payload.setdefault("position", record.display_position)
    payload.setdefault("current_club_id", record.provider_club_id)
    payload.setdefault("current_club_name", record.provider_club_name)
    payload.setdefault("current_club_domestic_competition_id", record.provider_competition_id)
    payload.setdefault("current_club_domestic_competition_name", record.provider_competition_name)
    payload.setdefault("country_of_citizenship", record.nationality_name)
    payload.setdefault("nationality_code", record.nationality_code)
    if record.date_of_birth is not None:
        payload.setdefault("date_of_birth", record.date_of_birth.isoformat())
    return payload


def _mapping_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _reference_mapping_root(metadata: Mapping[str, object]) -> dict[str, object]:
    for key in ("canonical_mapping", "reference_mapping"):
        section = _mapping_dict(metadata.get(key))
        if section:
            return section
    return {}


def _status_value(value: object) -> str | None:
    normalized = _normalized_text(value)
    return normalized.casefold() if normalized is not None else None


def _first_text(*values: object) -> str | None:
    for value in values:
        normalized = _normalized_text(value)
        if normalized is not None:
            return normalized
    return None


def _normalized_text(value: object) -> str | None:
    if value is None or isinstance(value, bool):
        return None
    normalized = clean_name(str(value))
    if normalized is None or normalized.casefold() in _NULLISH_TEXT_VALUES:
        return None
    return normalized


def _coerce_positive_int(value: object) -> int | None:
    normalized = _normalized_text(value)
    if normalized is None:
        return None
    try:
        parsed = int(normalized)
    except ValueError:
        try:
            parsed = int(float(normalized))
        except ValueError:
            return None
    return parsed if parsed > 0 else None


def _dedupe_passed(metadata: Mapping[str, object]) -> bool:
    explicit_flag = metadata.get("dedupe_passed")
    if isinstance(explicit_flag, bool):
        return explicit_flag

    dedupe_metadata = _mapping_dict(metadata.get("dedupe"))
    status = _status_value(dedupe_metadata.get("status") or metadata.get("dedupe_status"))
    if status in _DEDUPE_PASS_STATUSES:
        return True
    if status in _DEDUPE_FAIL_STATUSES:
        return False

    findings = metadata.get("duplicate_findings") or metadata.get("dedupe_findings") or ()
    if isinstance(findings, (list, tuple)) and findings:
        return False
    return True


def _hard_validation_blockers(metadata: Mapping[str, object]) -> tuple[str, ...]:
    blockers: list[str] = []
    validation_metadata = _mapping_dict(metadata.get("validation"))
    for candidate in (
        metadata.get("hard_validation_blockers"),
        validation_metadata.get("hard_blockers"),
        metadata.get("validation_blockers"),
    ):
        if isinstance(candidate, (list, tuple)):
            blockers.extend(
                normalized
                for normalized in (_normalized_text(item) for item in candidate)
                if normalized is not None
            )
    explicit_flag = validation_metadata.get("has_hard_blocker")
    if explicit_flag is True and not blockers:
        blockers.append("unspecified")
    return tuple(dict.fromkeys(blocker.casefold().replace(" ", "_") for blocker in blockers))


def _is_free_agent_label(value: str | None) -> bool:
    if value is None:
        return False
    return value.casefold() in _FREE_AGENT_LABELS


def _freshness_at(record: RealPlayerImportStagingRecord) -> datetime | None:
    for candidate in (record.provider_last_updated_at, record.last_seen_at, record.first_seen_at):
        if isinstance(candidate, datetime):
            return candidate
    return None


def _publish_sort_key(result: SecondZipPublishReadinessResult) -> tuple[object, ...]:
    tier_rank = {
        SecondZipPublishTier.TIER_1: 0,
        SecondZipPublishTier.TIER_2: 1,
        SecondZipPublishTier.TIER_3: 2,
    }[result.publish_tier]
    freshness_rank = 0
    freshness_value = float("-inf")
    if result.freshness_at is not None:
        freshness_rank = -1
        freshness_value = result.freshness_at.timestamp()
    return (
        tier_rank,
        result.fallback_count,
        freshness_rank,
        -freshness_value,
        result.full_name.casefold(),
        result.provider_player_id.casefold(),
    )


__all__ = [
    "DEFAULT_SECOND_ZIP_FALLBACK_MARKET_VALUE_EUR",
    "SECOND_ZIP_FREE_AGENT_CLUB_KEY",
    "SECOND_ZIP_FREE_AGENT_CLUB_NAME",
    "SecondZipClubAssignment",
    "SecondZipClubAssignmentType",
    "SecondZipPublishReadinessResult",
    "SecondZipPublishReadinessService",
    "SecondZipPublishTier",
    "SecondZipResolvedValuation",
    "SecondZipValuationSource",
]
