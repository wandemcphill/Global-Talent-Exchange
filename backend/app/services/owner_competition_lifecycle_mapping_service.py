from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.competition import UserCompetition
from app.models.competition_match import CompetitionMatch
from app.models.owner_competition_lifecycle_mapping import (
    OwnerCompetitionLifecycleMapping,
    OwnerMatchLifecycleMapping,
)
from app.owner_console.models import OwnerCompetition, OwnerMatch


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
