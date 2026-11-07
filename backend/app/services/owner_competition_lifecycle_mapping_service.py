from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.fixture_window import FixtureWindow
from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.owner_competition_lifecycle_mapping import (
    OwnerCompetitionLifecycleMapping,
    OwnerMatchLifecycleMapping,
)
from app.owner_console.models import OwnerClubState, OwnerCompetition, OwnerCompetitionEntry, OwnerMatch
from app.services.world_clock_service import WorldClockService


class OwnerCompetitionLifecycleMappingError(ValueError):
    """A legacy-to-canonical mapping cannot be safely created or reused."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(detail)


@dataclass(slots=True)
class OwnerCompetitionLifecycleMappingService:
    """Bind legacy owner-console records to existing canonical records without replaying history.

    This service intentionally does not create canonical competitions or fixtures,
    copy old scores/events, or settle money. Canonical rows must already exist.
    """

    session: Session

    def reconciliation_report(self) -> dict[str, object]:
        """Return a read-only inventory of global legacy competitions and canonical mappings.

        This deliberately does not create mappings, synthesize canonical competitions,
        copy results, replay fixtures, or touch ledger/reward records. It gives an
        operator the evidence needed to make explicit, reversible mapping decisions.
        """
        legacy_competitions = list(
            self.session.scalars(
                select(OwnerCompetition)
                .where(OwnerCompetition.host_type == "gtex")
                .order_by(OwnerCompetition.created_at.asc(), OwnerCompetition.id.asc())
            ).all()
        )
        if not legacy_competitions:
            return {
                "mode": "read_only",
                "automatic_reconciliation": False,
                "summary": {
                    "global_competitions": 0,
                    "active_competition_mappings": 0,
                    "unmapped_competitions": 0,
                    "missing_canonical_competitions": 0,
                    "legacy_fixtures": 0,
                    "legacy_historical_results": 0,
                    "active_fixture_mappings": 0,
                    "unmapped_legacy_fixtures": 0,
                    "unmapped_canonical_fixtures": 0,
                    "dangling_fixture_mappings": 0,
                },
                "competitions": [],
            }

        legacy_ids = [competition.id for competition in legacy_competitions]
        legacy_matches = list(
            self.session.scalars(
                select(OwnerMatch)
                .where(OwnerMatch.competition_id.in_(legacy_ids))
                .order_by(OwnerMatch.round_number.asc(), OwnerMatch.id.asc())
            ).all()
        )
        legacy_matches_by_competition: dict[str, list[OwnerMatch]] = {
            competition_id: [] for competition_id in legacy_ids
        }
        for legacy_match in legacy_matches:
            legacy_matches_by_competition.setdefault(legacy_match.competition_id, []).append(legacy_match)

        legacy_entries = list(
            self.session.scalars(
                select(OwnerCompetitionEntry).where(OwnerCompetitionEntry.competition_id.in_(legacy_ids))
            ).all()
        )
        entrant_counts: dict[str, int] = {competition_id: 0 for competition_id in legacy_ids}
        for entry in legacy_entries:
            entrant_counts[entry.competition_id] = entrant_counts.get(entry.competition_id, 0) + 1

        competition_mappings = list(
            self.session.scalars(
                select(OwnerCompetitionLifecycleMapping).where(
                    OwnerCompetitionLifecycleMapping.legacy_competition_id.in_(legacy_ids)
                )
            ).all()
        )
        mappings_by_legacy = {
            mapping.legacy_competition_id: mapping for mapping in competition_mappings
        }
        active_mapping_ids = [
            mapping.id for mapping in competition_mappings if mapping.mapping_status == "active"
        ]
        fixture_mappings = (
            list(
                self.session.scalars(
                    select(OwnerMatchLifecycleMapping).where(
                        OwnerMatchLifecycleMapping.competition_mapping_id.in_(active_mapping_ids)
                    )
                ).all()
            )
            if active_mapping_ids
            else []
        )
        active_fixture_mappings_by_competition: dict[str, list[OwnerMatchLifecycleMapping]] = {
            competition_id: [] for competition_id in legacy_ids
        }
        for fixture_mapping in fixture_mappings:
            if fixture_mapping.mapping_status == "active":
                active_fixture_mappings_by_competition.setdefault(
                    fixture_mapping.legacy_competition_id, []
                ).append(fixture_mapping)

        rows: list[dict[str, object]] = []
        active_competition_mapping_count = 0
        unmapped_competition_count = 0
        missing_canonical_count = 0
        historical_result_count = 0
        active_fixture_mapping_count = 0
        unmapped_legacy_fixture_count = 0

        for legacy in legacy_competitions:
            mapping = mappings_by_legacy.get(legacy.id)
            is_active_mapping = mapping is not None and mapping.mapping_status == "active"
            if is_active_mapping:
                active_competition_mapping_count += 1
            else:
                unmapped_competition_count += 1

            canonical = (
                self.session.get(UserCompetition, mapping.canonical_competition_id)
                if is_active_mapping and mapping is not None
                else None
            )
            canonical_missing = bool(is_active_mapping and canonical is None)
            if canonical_missing:
                missing_canonical_count += 1

            competition_legacy_matches = legacy_matches_by_competition.get(legacy.id, [])
            historical_matches = [
                match
                for match in competition_legacy_matches
                if (
                    match.played_at is not None
                    or match.home_goals is not None
                    or match.away_goals is not None
                    or bool(match.events_json)
                    or match.status not in {"scheduled", "pending"}
                )
            ]
            unplayed_matches = [
                match
                for match in competition_legacy_matches
                if (
                    match.status == "scheduled"
                    and match.played_at is None
                    and match.home_goals is None
                    and match.away_goals is None
                    and not match.events_json
                )
            ]
            historical_result_count += len(historical_matches)

            active_fixture_links = active_fixture_mappings_by_competition.get(legacy.id, [])
            mapped_legacy_match_ids = {link.legacy_match_id for link in active_fixture_links}
            unmapped_fixtures = [
                match for match in competition_legacy_matches if match.id not in mapped_legacy_match_ids
            ]
            active_fixture_mapping_count += len(active_fixture_links)
            unmapped_legacy_fixture_count += len(unmapped_fixtures)

            canonical_matches = (
                list(
                    self.session.scalars(
                        select(CompetitionMatch).where(CompetitionMatch.competition_id == canonical.id)
                    ).all()
                )
                if canonical is not None
                else []
            )
            canonical_fixture_ids = {match.id for match in canonical_matches}
            mapped_canonical_fixture_ids = {
                link.canonical_match_id for link in active_fixture_links
            }
            dangling_fixture_mapping_count = len(
                mapped_canonical_fixture_ids - canonical_fixture_ids
            )
            unmapped_canonical_fixture_count = len(
                canonical_fixture_ids - mapped_canonical_fixture_ids
            )
            canonical_fixture_count = len(canonical_matches)

            reasons: list[str] = []
            if not is_active_mapping:
                reasons.append("competition_mapping_required")
            if canonical_missing:
                reasons.append("mapped_canonical_competition_missing")
            if historical_matches:
                reasons.append("legacy_historical_results_must_be_preserved")
            if unmapped_fixtures:
                reasons.append("legacy_fixtures_require_explicit_review")
            if dangling_fixture_mapping_count:
                reasons.append("fixture_mapping_references_missing_canonical_fixtures")
            if unmapped_canonical_fixture_count:
                reasons.append("canonical_fixtures_without_legacy_owner_records_need_review")

            rows.append(
                {
                    "legacy_competition_id": legacy.id,
                    "name": legacy.name,
                    "format": legacy.format,
                    "legacy_status": legacy.status,
                    "legacy_current_round": legacy.current_round,
                    "legacy_entrant_count": entrant_counts.get(legacy.id, 0),
                    "legacy_fixture_count": len(competition_legacy_matches),
                    "legacy_unplayed_fixture_count": len(unplayed_matches),
                    "legacy_historical_result_count": len(historical_matches),
                    "legacy_fixture_ids": [match.id for match in competition_legacy_matches],
                    "mapping_status": mapping.mapping_status if mapping is not None else "unmapped",
                    "canonical_competition_id": (
                        mapping.canonical_competition_id if mapping is not None else None
                    ),
                    "canonical_competition_exists": canonical is not None,
                    "canonical_status": str(canonical.status) if canonical is not None else None,
                    "canonical_fixture_count": canonical_fixture_count,
                    "active_fixture_mapping_count": len(active_fixture_links),
                    "unmapped_canonical_fixture_count": unmapped_canonical_fixture_count,
                    "dangling_fixture_mapping_count": dangling_fixture_mapping_count,
                    "unmapped_legacy_fixture_ids": [match.id for match in unmapped_fixtures],
                    "operator_review_reasons": reasons,
                    "automatic_reconciliation": False,
                    "historical_rows_mutated": False,
                    "ledger_or_reward_rows_mutated": False,
                }
            )

        return {
            "mode": "read_only",
            "automatic_reconciliation": False,
            "summary": {
                "global_competitions": len(legacy_competitions),
                "active_competition_mappings": active_competition_mapping_count,
                "unmapped_competitions": unmapped_competition_count,
                "missing_canonical_competitions": missing_canonical_count,
                "legacy_fixtures": len(legacy_matches),
                "legacy_historical_results": historical_result_count,
                "active_fixture_mappings": active_fixture_mapping_count,
                "unmapped_legacy_fixtures": unmapped_legacy_fixture_count,
                "unmapped_canonical_fixtures": sum(
                    int(row["unmapped_canonical_fixture_count"]) for row in rows
                ),
                "dangling_fixture_mappings": sum(
                    int(row["dangling_fixture_mapping_count"]) for row in rows
                ),
            },
            "competitions": rows,
        }

    def bind_competition(
        self,
        legacy_competition_id: str,
        canonical_competition_id: str,
    ) -> OwnerCompetitionLifecycleMapping:
        legacy = self.session.get(OwnerCompetition, legacy_competition_id)
        if legacy is None:
            raise OwnerCompetitionLifecycleMappingError(
                "legacy_competition_not_found", "The owner-console competition does not exist."
            )
        if legacy.host_type != "gtex":
            raise OwnerCompetitionLifecycleMappingError(
                "user_hosted_competition_uses_separate_lifecycle",
                "User-hosted tournaments remain on their separately defined execution rail.",
            )

        canonical = self.session.get(UserCompetition, canonical_competition_id)
        if canonical is None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_competition_not_found", "The canonical GTEX competition does not exist."
            )
        if not self._is_platform_competition(canonical.source_type):
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_competition_not_global",
                "Only explicitly platform-hosted canonical competitions can be linked to global GTEX tournaments.",
            )
        expected_format = {"league": "league", "knockout": "cup"}.get(legacy.format)
        if expected_format is None or canonical.format != expected_format:
            raise OwnerCompetitionLifecycleMappingError(
                "competition_format_mismatch",
                "Legacy and canonical competitions must use compatible league/cup formats before they can be linked.",
            )

        by_legacy = self.session.scalar(
            select(OwnerCompetitionLifecycleMapping).where(
                OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy_competition_id
            )
        )
        if by_legacy is not None:
            if by_legacy.canonical_competition_id == canonical_competition_id:
                return by_legacy
            raise OwnerCompetitionLifecycleMappingError(
                "legacy_competition_already_mapped",
                "This legacy competition is already mapped to a different canonical competition.",
            )

        by_canonical = self.session.scalar(
            select(OwnerCompetitionLifecycleMapping).where(
                OwnerCompetitionLifecycleMapping.canonical_competition_id == canonical_competition_id
            )
        )
        if by_canonical is not None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_competition_already_mapped",
                "This canonical competition is already linked to a different legacy competition.",
            )

        mapping = OwnerCompetitionLifecycleMapping(
            legacy_competition_id=legacy_competition_id,
            canonical_competition_id=canonical_competition_id,
            mapping_status="active",
            metadata_json={"mapping_contract": "owner-console-to-canonical-v1"},
        )
        try:
            # Unique constraints are the final concurrency guard. A retry that
            # races with an identical insert resolves to that existing mapping.
            with self.session.begin_nested():
                self.session.add(mapping)
                self.session.flush()
            return mapping
        except IntegrityError as exc:
            existing = self.session.scalar(
                select(OwnerCompetitionLifecycleMapping).where(
                    OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy_competition_id
                )
            )
            if existing is not None and existing.canonical_competition_id == canonical_competition_id:
                return existing
            raise OwnerCompetitionLifecycleMappingError(
                "competition_mapping_conflict",
                "A concurrent mapping claimed one of these competition identities.",
            ) from exc

    def bind_scheduled_match(
        self,
        legacy_match_id: str,
        canonical_match_id: str,
    ) -> OwnerMatchLifecycleMapping:
        legacy_match = self.session.get(OwnerMatch, legacy_match_id)
        if legacy_match is None:
            raise OwnerCompetitionLifecycleMappingError(
                "legacy_match_not_found", "The legacy owner-console fixture does not exist."
            )

        competition_mapping = self.session.scalar(
            select(OwnerCompetitionLifecycleMapping).where(
                OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy_match.competition_id
            )
        )
        if competition_mapping is None or competition_mapping.mapping_status != "active":
            raise OwnerCompetitionLifecycleMappingError(
                "competition_mapping_required",
                "An active competition mapping is required before a fixture can be linked.",
            )

        legacy_competition = self.session.get(OwnerCompetition, legacy_match.competition_id)
        if legacy_competition is None or legacy_competition.host_type != "gtex":
            raise OwnerCompetitionLifecycleMappingError(
                "user_hosted_competition_uses_separate_lifecycle",
                "Only global GTEX fixtures can be linked to the canonical lifecycle.",
            )

        # Lock the canonical row when the DB supports row locks so the mapping
        # cannot silently target an already-claimed fixture.
        canonical_match = self.session.scalar(
            select(CompetitionMatch).where(CompetitionMatch.id == canonical_match_id).with_for_update()
        )
        if canonical_match is None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_match_not_found", "The canonical fixture does not exist."
            )
        if canonical_match.competition_id != competition_mapping.canonical_competition_id:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_match_competition_mismatch",
                "The canonical fixture belongs to a different canonical competition.",
            )
        if (
            legacy_match.status != "scheduled"
            or legacy_match.played_at is not None
            or canonical_match.status != "scheduled"
            or canonical_match.completed_at is not None
        ):
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_is_not_unplayed",
                "Only fixtures that are still scheduled and have no recorded result can be linked.",
            )
        if legacy_match.round_number != canonical_match.round_number:
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_round_mismatch",
                "Legacy and canonical fixtures must belong to the same round before they can be linked.",
            )
        if (
            legacy_match.home_club_id != canonical_match.home_club_id
            or legacy_match.away_club_id != canonical_match.away_club_id
        ):
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_club_identity_mismatch",
                "Home and away club identities must match exactly before a fixture can be linked.",
            )

        by_legacy = self.session.scalar(
            select(OwnerMatchLifecycleMapping).where(OwnerMatchLifecycleMapping.legacy_match_id == legacy_match_id)
        )
        if by_legacy is not None:
            if (
                by_legacy.canonical_match_id == canonical_match_id
                and by_legacy.competition_mapping_id == competition_mapping.id
            ):
                return by_legacy
            raise OwnerCompetitionLifecycleMappingError(
                "legacy_match_already_mapped",
                "This legacy fixture is already linked to a different canonical fixture.",
            )

        by_canonical = self.session.scalar(
            select(OwnerMatchLifecycleMapping).where(
                OwnerMatchLifecycleMapping.canonical_match_id == canonical_match_id
            )
        )
        if by_canonical is not None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_match_already_mapped",
                "This canonical fixture is already linked to a different legacy fixture.",
            )

        mapping = OwnerMatchLifecycleMapping(
            legacy_match_id=legacy_match_id,
            competition_mapping_id=competition_mapping.id,
            legacy_competition_id=legacy_match.competition_id,
            canonical_match_id=canonical_match_id,
            mapping_status="active",
            metadata_json={"mapping_contract": "owner-console-to-canonical-v1"},
        )
        try:
            with self.session.begin_nested():
                self.session.add(mapping)
                self.session.flush()
            return mapping
        except IntegrityError as exc:
            existing = self.session.scalar(
                select(OwnerMatchLifecycleMapping).where(OwnerMatchLifecycleMapping.legacy_match_id == legacy_match_id)
            )
            if (
                existing is not None
                and existing.canonical_match_id == canonical_match_id
                and existing.competition_mapping_id == competition_mapping.id
            ):
                return existing
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_mapping_conflict",
                "A concurrent mapping claimed one of these fixture identities.",
            ) from exc

    def save_pre_match_tactics(
        self,
        *,
        legacy_match_id: str,
        club_id: str,
        user_id: str,
        mentality: str,
        lineup_mode: str,
    ) -> CompetitionMatch:
        """Persist owner instructions on the mapped canonical fixture, never simulate it."""
        if mentality not in {"defensive", "balanced", "attacking"}:
            raise OwnerCompetitionLifecycleMappingError(
                "invalid_mentality", "Choose defensive, balanced, or attacking mentality."
            )
        if lineup_mode not in {"strongest", "rotate"}:
            raise OwnerCompetitionLifecycleMappingError(
                "invalid_lineup_mode", "Choose strongest or rotate lineup mode."
            )

        legacy_match = self.session.get(OwnerMatch, legacy_match_id)
        if legacy_match is None:
            raise OwnerCompetitionLifecycleMappingError(
                "legacy_match_not_found", "The owner-console fixture does not exist."
            )
        legacy_competition = self.session.get(OwnerCompetition, legacy_match.competition_id)
        if legacy_competition is None or legacy_competition.host_type != "gtex":
            raise OwnerCompetitionLifecycleMappingError(
                "user_hosted_competition_uses_separate_lifecycle",
                "Only global GTEX fixtures accept canonical pre-match instructions.",
            )
        if legacy_match.status != "scheduled" or legacy_match.played_at is not None:
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_is_not_unplayed", "Instructions can only be changed for an unplayed fixture."
            )
        if club_id not in {legacy_match.home_club_id, legacy_match.away_club_id}:
            raise OwnerCompetitionLifecycleMappingError(
                "club_not_in_fixture", "The selected club is not one of the clubs in this fixture."
            )

        owner_state = self.session.scalar(
            select(OwnerClubState).where(OwnerClubState.club_id == club_id)
        )
        if owner_state is None or owner_state.owner_user_id != user_id:
            raise OwnerCompetitionLifecycleMappingError(
                "not_club_owner",
                "Only the authenticated owner of this club may submit pre-match instructions.",
            )

        legacy_entry = self.session.scalar(
            select(OwnerCompetitionLifecycleMapping).where(
                OwnerCompetitionLifecycleMapping.legacy_competition_id == legacy_competition.id,
                OwnerCompetitionLifecycleMapping.mapping_status == "active",
            )
        )
        if legacy_entry is None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_fixture_mapping_required",
                "This global competition has not been reconciled with a canonical GTEX competition yet.",
            )
        fixture_mapping = self.session.scalar(
            select(OwnerMatchLifecycleMapping).where(
                OwnerMatchLifecycleMapping.legacy_match_id == legacy_match_id,
                OwnerMatchLifecycleMapping.competition_mapping_id == legacy_entry.id,
                OwnerMatchLifecycleMapping.mapping_status == "active",
            )
        )
        if fixture_mapping is None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_fixture_mapping_required",
                "This fixture has not been linked to its canonical GTEX fixture yet.",
            )

        canonical_match = self.session.scalar(
            select(CompetitionMatch).where(CompetitionMatch.id == fixture_mapping.canonical_match_id).with_for_update()
        )
        if canonical_match is None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_match_not_found", "The canonical fixture no longer exists."
            )
        if canonical_match.status != "scheduled" or canonical_match.completed_at is not None:
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_is_not_unplayed", "Instructions can only be changed before the canonical fixture starts."
            )

        canonical_competition = self.session.get(UserCompetition, canonical_match.competition_id)
        if canonical_competition is None:
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_competition_not_found", "The canonical GTEX competition does not exist."
            )
        if not self._is_platform_competition(canonical_competition.source_type):
            raise OwnerCompetitionLifecycleMappingError(
                "canonical_competition_not_global",
                "The mapped fixture no longer belongs to a platform-hosted global competition.",
            )
        if (
            legacy_match.home_club_id != canonical_match.home_club_id
            or legacy_match.away_club_id != canonical_match.away_club_id
            or club_id not in {canonical_match.home_club_id, canonical_match.away_club_id}
        ):
            raise OwnerCompetitionLifecycleMappingError(
                "fixture_club_identity_mismatch",
                "The mapped canonical fixture no longer matches the legacy home/away club identities.",
            )
        kickoff_at = canonical_match.scheduled_at
        if kickoff_at is not None and kickoff_at.tzinfo is None:
            kickoff_at = kickoff_at.replace(tzinfo=timezone.utc)
        if kickoff_at is None:
            match_date = canonical_match.match_date
            if match_date is None and canonical_competition.scheduled_start_at is not None:
                scheduled_start = canonical_competition.scheduled_start_at
                if scheduled_start.tzinfo is None:
                    scheduled_start = scheduled_start.replace(tzinfo=timezone.utc)
                match_date = scheduled_start.date()
            if match_date is None:
                raise OwnerCompetitionLifecycleMappingError(
                    "canonical_kickoff_unresolved",
                    "The canonical fixture has no authoritative kickoff date; instructions cannot be accepted.",
                )
            format_enum = CompetitionFormat(canonical_competition.format)
            default_window = (
                FixtureWindow.SENIOR_1 if format_enum is CompetitionFormat.LEAGUE else FixtureWindow.FAST_CUP_OPEN
            )
            window = FixtureWindow(canonical_match.window) if canonical_match.window else default_window
            kickoff_at = window.kickoff_at(match_date)

        now_virtual = WorldClockService(self.session).now_virtual()
        if kickoff_at <= now_virtual:
            raise OwnerCompetitionLifecycleMappingError(
                "kickoff_already_due", "Pre-match instructions must be saved before the scheduled virtual kickoff."
            )

        metadata = dict(canonical_match.metadata_json or {})
        owner_tactics = dict(metadata.get("owner_pre_match_tactics") or {})
        owner_tactics[club_id] = {
            "mentality": mentality,
            "lineup_mode": lineup_mode,
            "saved_by_user_id": user_id,
            "saved_at_virtual_time": now_virtual.isoformat(),
        }
        metadata["owner_pre_match_tactics"] = owner_tactics
        canonical_match.metadata_json = metadata
        self.session.flush()
        return canonical_match

    @staticmethod
    def _is_platform_competition(source_type: str | None) -> bool:
        return (source_type or "").strip().lower() in {
            "gtex",
            "platform",
            "gtex_platform",
            "gtex_competition",
            "gtex_hosted",
        }

    def canonical_match_for_legacy_match(self, legacy_match_id: str) -> CompetitionMatch | None:
        mapping = self.session.scalar(
            select(OwnerMatchLifecycleMapping).where(
                OwnerMatchLifecycleMapping.legacy_match_id == legacy_match_id,
                OwnerMatchLifecycleMapping.mapping_status == "active",
            )
        )
        if mapping is None:
            return None
        return self.session.get(CompetitionMatch, mapping.canonical_match_id)


__all__ = [
    "OwnerCompetitionLifecycleMappingError",
    "OwnerCompetitionLifecycleMappingService",
]
