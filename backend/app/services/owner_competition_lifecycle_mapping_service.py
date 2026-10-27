from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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
from app.owner_console.models import OwnerCompetition, OwnerMatch
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
            select(CompetitionMatch)
            .where(CompetitionMatch.id == canonical_match_id)
            .with_for_update()
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
            select(OwnerMatchLifecycleMapping).where(
                OwnerMatchLifecycleMapping.legacy_match_id == legacy_match_id
            )
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
                select(OwnerMatchLifecycleMapping).where(
                    OwnerMatchLifecycleMapping.legacy_match_id == legacy_match_id
                )
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
            select(CompetitionMatch)
            .where(CompetitionMatch.id == fixture_mapping.canonical_match_id)
            .with_for_update()
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
                FixtureWindow.SENIOR_1
                if format_enum is CompetitionFormat.LEAGUE
                else FixtureWindow.FAST_CUP_OPEN
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
