from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.ingestion.models import Club, Competition, Country
from app.ingestion.normalizers import (
    clean_name,
    normalize_club_name,
    normalize_competition_name,
    normalize_country_name,
    slugify,
)
from app.models.real_player_reference_mapping import (
    RealPlayerReferenceMapping,
    RealPlayerUnresolvedReference,
)


class CanonicalReferenceEntityType(StrEnum):
    COUNTRY = "country"
    COMPETITION = "competition"
    CLUB = "club"
    TEAM_IDENTITY = "team_identity"


class CanonicalReferenceStatus(StrEnum):
    RESOLVED = "resolved"
    AUTO_CREATED = "auto_created"
    UNRESOLVED = "unresolved"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class CanonicalReferenceInput:
    source_name: str
    entity_type: str
    provider_external_id: str | None = None
    display_name: str | None = None
    country_code: str | None = None
    country_name: str | None = None
    competition_external_id: str | None = None
    competition_display_name: str | None = None
    team_identity_kind: str | None = None
    metadata_json: dict[str, Any] = field(default_factory=dict)

    @property
    def normalized_display_name(self) -> str | None:
        if self.entity_type == CanonicalReferenceEntityType.COUNTRY.value:
            return normalize_country_name(self.display_name)
        if self.entity_type == CanonicalReferenceEntityType.COMPETITION.value:
            return normalize_competition_name(self.display_name)
        if self.entity_type == CanonicalReferenceEntityType.TEAM_IDENTITY.value and self.team_identity_kind == "national_team":
            return normalize_country_name(self.display_name)
        if self.entity_type in {
            CanonicalReferenceEntityType.CLUB.value,
            CanonicalReferenceEntityType.TEAM_IDENTITY.value,
        }:
            return normalize_club_name(self.display_name)
        return clean_name(self.display_name)

    @property
    def provider_reference_key(self) -> str:
        explicit_key = clean_name(self.provider_external_id)
        if explicit_key:
            return slugify(explicit_key)
        parts: list[str] = []
        if self.entity_type in {
            CanonicalReferenceEntityType.COMPETITION.value,
            CanonicalReferenceEntityType.CLUB.value,
            CanonicalReferenceEntityType.TEAM_IDENTITY.value,
        }:
            if self.country_code:
                parts.append(self.country_code)
            elif self.country_name:
                parts.append(self.country_name)
        if self.entity_type in {
            CanonicalReferenceEntityType.CLUB.value,
            CanonicalReferenceEntityType.TEAM_IDENTITY.value,
        }:
            if self.competition_external_id:
                parts.append(self.competition_external_id)
            elif self.competition_display_name:
                parts.append(self.competition_display_name)
        if self.display_name:
            parts.append(self.display_name)
        if not parts and self.country_name:
            parts.append(self.country_name)
        return slugify("::".join(parts))

    @property
    def has_reference(self) -> bool:
        return any(
            (
                clean_name(self.provider_external_id),
                clean_name(self.display_name),
                clean_name(self.country_code),
                clean_name(self.country_name),
            )
        )


@dataclass(frozen=True, slots=True)
class CanonicalReferenceResolution:
    entity_type: str
    status: str
    provider_reference_key: str | None
    provider_external_id: str | None
    provider_label: str | None
    normalized_label: str | None
    resolution_method: str
    confidence_score: float
    mapping_id: str | None = None
    unresolved_reference_id: str | None = None
    reason_code: str | None = None
    canonical_country_id: str | None = None
    canonical_competition_id: str | None = None
    canonical_club_id: str | None = None
    canonical_name: str | None = None
    team_identity_kind: str | None = None
    entity: Country | Competition | Club | None = None

    @property
    def canonical_id(self) -> str | None:
        return self.canonical_country_id or self.canonical_competition_id or self.canonical_club_id

    def metadata(self) -> dict[str, Any]:
        return {
            "entity_type": self.entity_type,
            "status": self.status,
            "provider_reference_key": self.provider_reference_key,
            "provider_external_id": self.provider_external_id,
            "provider_label": self.provider_label,
            "normalized_label": self.normalized_label,
            "resolution_method": self.resolution_method,
            "confidence_score": self.confidence_score,
            "mapping_id": self.mapping_id,
            "unresolved_reference_id": self.unresolved_reference_id,
            "reason_code": self.reason_code,
            "canonical_country_id": self.canonical_country_id,
            "canonical_competition_id": self.canonical_competition_id,
            "canonical_club_id": self.canonical_club_id,
            "canonical_name": self.canonical_name,
            "team_identity_kind": self.team_identity_kind,
        }


@dataclass(slots=True)
class RealPlayerCanonicalMappingService:
    settings: Settings = field(default_factory=get_settings)
    auto_create_missing_entities: bool | None = None

    def __post_init__(self) -> None:
        if self.auto_create_missing_entities is None:
            self.auto_create_missing_entities = self.settings.real_player_mapping_auto_create_missing_entities

    def resolve_country(
        self,
        session: Session,
        *,
        source_name: str,
        provider_external_id: str | None = None,
        name: str | None = None,
        as_of: datetime | None = None,
        sample_payload: dict[str, Any] | None = None,
    ) -> CanonicalReferenceResolution:
        reference = CanonicalReferenceInput(
            source_name=source_name,
            entity_type=CanonicalReferenceEntityType.COUNTRY.value,
            provider_external_id=provider_external_id,
            display_name=name,
            country_code=provider_external_id,
            country_name=name,
        )
        return self._resolve_country_reference(
            session,
            reference,
            as_of=as_of or datetime.now(UTC),
            sample_payload=sample_payload,
        )

    def resolve_competition(
        self,
        session: Session,
        *,
        source_name: str,
        provider_external_id: str | None = None,
        name: str | None = None,
        country: Country | None = None,
        country_code: str | None = None,
        country_name: str | None = None,
        as_of: datetime | None = None,
        sample_payload: dict[str, Any] | None = None,
        auto_create_values: dict[str, Any] | None = None,
    ) -> CanonicalReferenceResolution:
        reference = CanonicalReferenceInput(
            source_name=source_name,
            entity_type=CanonicalReferenceEntityType.COMPETITION.value,
            provider_external_id=provider_external_id,
            display_name=name,
            country_code=country_code,
            country_name=country_name,
        )
        return self._resolve_competition_reference(
            session,
            reference,
            country=country,
            as_of=as_of or datetime.now(UTC),
            sample_payload=sample_payload,
            auto_create_values=auto_create_values or {},
        )

    def resolve_club(
        self,
        session: Session,
        *,
        source_name: str,
        provider_external_id: str | None = None,
        name: str | None = None,
        country: Country | None = None,
        country_code: str | None = None,
        country_name: str | None = None,
        competition: Competition | None = None,
        competition_external_id: str | None = None,
        competition_name: str | None = None,
        as_of: datetime | None = None,
        sample_payload: dict[str, Any] | None = None,
        auto_create_values: dict[str, Any] | None = None,
    ) -> CanonicalReferenceResolution:
        reference = CanonicalReferenceInput(
            source_name=source_name,
            entity_type=CanonicalReferenceEntityType.CLUB.value,
            provider_external_id=provider_external_id,
            display_name=name,
            country_code=country_code,
            country_name=country_name,
            competition_external_id=competition_external_id,
            competition_display_name=competition_name,
        )
        return self._resolve_club_reference(
            session,
            reference,
            country=country,
            competition=competition,
            as_of=as_of or datetime.now(UTC),
            sample_payload=sample_payload,
            auto_create_values=auto_create_values or {},
        )

    def resolve_team_identity(
        self,
        session: Session,
        *,
        source_name: str,
        team_identity_kind: str,
        provider_external_id: str | None = None,
        name: str | None = None,
        country: Country | None = None,
        country_code: str | None = None,
        country_name: str | None = None,
        competition: Competition | None = None,
        competition_external_id: str | None = None,
        competition_name: str | None = None,
        as_of: datetime | None = None,
        sample_payload: dict[str, Any] | None = None,
    ) -> CanonicalReferenceResolution:
        as_of = as_of or datetime.now(UTC)
        reference = CanonicalReferenceInput(
            source_name=source_name,
            entity_type=CanonicalReferenceEntityType.TEAM_IDENTITY.value,
            provider_external_id=provider_external_id,
            display_name=name,
            country_code=country_code,
            country_name=country_name,
            competition_external_id=competition_external_id,
            competition_display_name=competition_name,
            team_identity_kind=team_identity_kind,
        )
        if team_identity_kind == "national_team":
            country_resolution = self._resolve_country_reference(
                session,
                CanonicalReferenceInput(
                    source_name=source_name,
                    entity_type=CanonicalReferenceEntityType.COUNTRY.value,
                    provider_external_id=country_code or provider_external_id,
                    display_name=name or country_name,
                    country_code=country_code or provider_external_id,
                    country_name=name or country_name,
                ),
                as_of=as_of,
                sample_payload=sample_payload,
            )
            return self._mirror_as_team_identity(session, reference, country_resolution, as_of=as_of, sample_payload=sample_payload)

        club_resolution = self._resolve_club_reference(
            session,
            CanonicalReferenceInput(
                source_name=source_name,
                entity_type=CanonicalReferenceEntityType.CLUB.value,
                provider_external_id=provider_external_id,
                display_name=name,
                country_code=country_code,
                country_name=country_name,
                competition_external_id=competition_external_id,
                competition_display_name=competition_name,
            ),
            country=country,
            competition=competition,
            as_of=as_of,
            sample_payload=sample_payload,
            auto_create_values={},
        )
        return self._mirror_as_team_identity(session, reference, club_resolution, as_of=as_of, sample_payload=sample_payload)

    def _resolve_country_reference(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        *,
        as_of: datetime,
        sample_payload: dict[str, Any] | None,
    ) -> CanonicalReferenceResolution:
        if not reference.has_reference:
            return self._skipped_resolution(reference, reason_code="missing_reference")

        mapping = self._lookup_mapping(session, reference)
        if mapping is not None:
            resolved = self._mapping_resolution(session, mapping, reference)
            if resolved is not None:
                return resolved

        exact_provider = self._match_country_by_provider(session, reference)
        if exact_provider is not None:
            return self._persist_mapping(
                session,
                reference,
                entity=exact_provider,
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="provider_exact",
                confidence_score=1.0,
                as_of=as_of,
            )

        country_code = (reference.provider_external_id or reference.country_code or "").upper()
        if country_code:
            by_code = list(
                session.scalars(
                    select(Country).where(
                        or_(
                            Country.alpha2_code == country_code,
                            Country.alpha3_code == country_code,
                            Country.fifa_code == country_code,
                        )
                    )
                )
            )
            if len(by_code) == 1:
                return self._persist_mapping(
                    session,
                    reference,
                    entity=by_code[0],
                    mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                    resolution_method="country_code_exact",
                    confidence_score=0.99,
                    as_of=as_of,
                )
            if len(by_code) > 1:
                return self._record_unresolved(
                    session,
                    reference,
                    reason_code="ambiguous_country_code_match",
                    as_of=as_of,
                    sample_payload=sample_payload,
                    notes=f"Multiple countries matched code '{country_code}'.",
                    metadata_json={"candidate_ids": [candidate.id for candidate in by_code]},
                )

        normalized_name = reference.normalized_display_name
        if normalized_name:
            by_name = list(
                session.scalars(
                    select(Country).where(func.lower(Country.name) == normalized_name.lower())
                )
            )
            if len(by_name) == 1:
                return self._persist_mapping(
                    session,
                    reference,
                    entity=by_name[0],
                    mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                    resolution_method="country_name_exact",
                    confidence_score=0.94,
                    as_of=as_of,
                )
            if len(by_name) > 1:
                return self._record_unresolved(
                    session,
                    reference,
                    reason_code="ambiguous_country_name_match",
                    as_of=as_of,
                    sample_payload=sample_payload,
                    notes=f"Multiple countries matched name '{normalized_name}'.",
                    metadata_json={"candidate_ids": [candidate.id for candidate in by_name]},
                )

        if self.auto_create_missing_entities:
            created = Country(
                source_provider=reference.source_name,
                provider_external_id=reference.provider_external_id or reference.provider_reference_key,
                name=normalized_name or reference.display_name or "Unknown",
                alpha2_code=country_code if len(country_code) == 2 else None,
                alpha3_code=country_code if len(country_code) == 3 else None,
                fifa_code=country_code if len(country_code) == 3 else None,
                last_synced_at=as_of,
            )
            session.add(created)
            session.flush()
            return self._persist_mapping(
                session,
                reference,
                entity=created,
                mapping_status=CanonicalReferenceStatus.AUTO_CREATED.value,
                resolution_method="auto_created",
                confidence_score=0.86,
                as_of=as_of,
            )

        return self._record_unresolved(
            session,
            reference,
            reason_code="country_not_found",
            as_of=as_of,
            sample_payload=sample_payload,
            notes="No canonical country matched the provider reference.",
        )

    def _resolve_competition_reference(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        *,
        country: Country | None,
        as_of: datetime,
        sample_payload: dict[str, Any] | None,
        auto_create_values: dict[str, Any],
    ) -> CanonicalReferenceResolution:
        if not reference.has_reference or not clean_name(reference.display_name):
            return self._skipped_resolution(reference, reason_code="missing_reference")

        mapping = self._lookup_mapping(session, reference)
        if mapping is not None:
            resolved = self._mapping_resolution(session, mapping, reference)
            if resolved is not None:
                return resolved

        exact_provider = self._match_competition_by_provider(session, reference)
        if exact_provider is not None:
            return self._persist_mapping(
                session,
                reference,
                entity=exact_provider,
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="provider_exact",
                confidence_score=1.0,
                as_of=as_of,
            )

        normalized_name = reference.normalized_display_name
        slug = slugify(normalized_name)
        candidates = list(
            session.scalars(
                select(Competition).where(
                    or_(
                        Competition.slug == slug,
                        func.lower(Competition.name) == normalized_name.lower(),
                    )
                )
            )
        )
        candidates = self._prefer_competitions_by_country(candidates, country=country)
        same_source = [candidate for candidate in candidates if candidate.source_provider == reference.source_name]
        if len(same_source) == 1:
            return self._persist_mapping(
                session,
                reference,
                entity=same_source[0],
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="same_source_name_match",
                confidence_score=0.95,
                as_of=as_of,
            )
        if len(candidates) == 1:
            return self._persist_mapping(
                session,
                reference,
                entity=candidates[0],
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="name_exact",
                confidence_score=0.91,
                as_of=as_of,
            )
        if len(candidates) > 1:
            return self._record_unresolved(
                session,
                reference,
                reason_code="ambiguous_competition_match",
                as_of=as_of,
                sample_payload=sample_payload,
                notes=f"Multiple canonical competitions matched '{normalized_name}'.",
                metadata_json={"candidate_ids": [candidate.id for candidate in candidates]},
            )

        if self.auto_create_missing_entities:
            created = Competition(
                source_provider=reference.source_name,
                provider_external_id=reference.provider_external_id or reference.provider_reference_key,
                country_id=country.id if country is not None else None,
                name=normalized_name or reference.display_name or "Unknown Competition",
                slug=slug,
                **auto_create_values,
            )
            session.add(created)
            session.flush()
            return self._persist_mapping(
                session,
                reference,
                entity=created,
                mapping_status=CanonicalReferenceStatus.AUTO_CREATED.value,
                resolution_method="auto_created",
                confidence_score=0.84,
                as_of=as_of,
            )

        return self._record_unresolved(
            session,
            reference,
            reason_code="competition_not_found",
            as_of=as_of,
            sample_payload=sample_payload,
            notes="No canonical competition matched the provider reference.",
        )

    def _resolve_club_reference(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        *,
        country: Country | None,
        competition: Competition | None,
        as_of: datetime,
        sample_payload: dict[str, Any] | None,
        auto_create_values: dict[str, Any],
    ) -> CanonicalReferenceResolution:
        if not reference.has_reference or not clean_name(reference.display_name):
            return self._skipped_resolution(reference, reason_code="missing_reference")

        mapping = self._lookup_mapping(session, reference)
        if mapping is not None:
            resolved = self._mapping_resolution(session, mapping, reference)
            if resolved is not None:
                return resolved

        exact_provider = self._match_club_by_provider(session, reference)
        if exact_provider is not None:
            return self._persist_mapping(
                session,
                reference,
                entity=exact_provider,
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="provider_exact",
                confidence_score=1.0,
                as_of=as_of,
            )

        normalized_name = reference.normalized_display_name
        slug = slugify(normalized_name)
        candidates = list(
            session.scalars(
                select(Club).where(
                    or_(
                        Club.slug == slug,
                        func.lower(Club.name) == normalized_name.lower(),
                        func.lower(func.coalesce(Club.short_name, "")) == normalized_name.lower(),
                    )
                )
            )
        )
        candidates = self._prefer_clubs_by_competition(candidates, competition=competition)
        candidates = self._prefer_clubs_by_country(candidates, country=country)
        same_source = [candidate for candidate in candidates if candidate.source_provider == reference.source_name]
        if len(same_source) == 1:
            return self._persist_mapping(
                session,
                reference,
                entity=same_source[0],
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="same_source_name_match",
                confidence_score=0.95,
                as_of=as_of,
            )
        if len(candidates) == 1:
            return self._persist_mapping(
                session,
                reference,
                entity=candidates[0],
                mapping_status=CanonicalReferenceStatus.RESOLVED.value,
                resolution_method="name_exact",
                confidence_score=0.9,
                as_of=as_of,
            )
        if len(candidates) > 1:
            return self._record_unresolved(
                session,
                reference,
                reason_code="ambiguous_club_match",
                as_of=as_of,
                sample_payload=sample_payload,
                notes=f"Multiple canonical clubs matched '{normalized_name}'.",
                metadata_json={"candidate_ids": [candidate.id for candidate in candidates]},
            )

        if self.auto_create_missing_entities:
            created = Club(
                source_provider=reference.source_name,
                provider_external_id=reference.provider_external_id or reference.provider_reference_key,
                country_id=country.id if country is not None else None,
                current_competition_id=competition.id if competition is not None else None,
                name=normalized_name or reference.display_name or "Unknown Club",
                slug=slug,
                **auto_create_values,
            )
            session.add(created)
            session.flush()
            return self._persist_mapping(
                session,
                reference,
                entity=created,
                mapping_status=CanonicalReferenceStatus.AUTO_CREATED.value,
                resolution_method="auto_created",
                confidence_score=0.82,
                as_of=as_of,
            )

        return self._record_unresolved(
            session,
            reference,
            reason_code="club_not_found",
            as_of=as_of,
            sample_payload=sample_payload,
            notes="No canonical club matched the provider reference.",
        )

    def _mirror_as_team_identity(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        resolution: CanonicalReferenceResolution,
        *,
        as_of: datetime,
        sample_payload: dict[str, Any] | None,
    ) -> CanonicalReferenceResolution:
        if resolution.status == CanonicalReferenceStatus.SKIPPED.value:
            return self._skipped_resolution(reference, reason_code=resolution.reason_code or "missing_reference")
        if resolution.status == CanonicalReferenceStatus.UNRESOLVED.value:
            return self._record_unresolved(
                session,
                reference,
                reason_code=resolution.reason_code or "team_identity_not_found",
                as_of=as_of,
                sample_payload=sample_payload,
                notes="Team identity could not be mapped to a canonical GTEX entity.",
                metadata_json=resolution.metadata(),
            )
        team_resolution = self._persist_mapping(
            session,
            reference,
            entity=resolution.entity,
            mapping_status=resolution.status,
            resolution_method=f"team_identity:{resolution.resolution_method}",
            confidence_score=resolution.confidence_score,
            as_of=as_of,
        )
        return CanonicalReferenceResolution(
            entity_type=team_resolution.entity_type,
            status=team_resolution.status,
            provider_reference_key=team_resolution.provider_reference_key,
            provider_external_id=team_resolution.provider_external_id,
            provider_label=team_resolution.provider_label,
            normalized_label=team_resolution.normalized_label,
            resolution_method=team_resolution.resolution_method,
            confidence_score=team_resolution.confidence_score,
            mapping_id=team_resolution.mapping_id,
            unresolved_reference_id=team_resolution.unresolved_reference_id,
            reason_code=team_resolution.reason_code,
            canonical_country_id=team_resolution.canonical_country_id,
            canonical_competition_id=team_resolution.canonical_competition_id,
            canonical_club_id=team_resolution.canonical_club_id,
            canonical_name=team_resolution.canonical_name,
            team_identity_kind=reference.team_identity_kind,
            entity=team_resolution.entity,
        )

    def _lookup_mapping(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
    ) -> RealPlayerReferenceMapping | None:
        mapping = session.scalar(
            select(RealPlayerReferenceMapping).where(
                RealPlayerReferenceMapping.source_name == reference.source_name,
                RealPlayerReferenceMapping.entity_type == reference.entity_type,
                RealPlayerReferenceMapping.provider_reference_key == reference.provider_reference_key,
                RealPlayerReferenceMapping.is_active.is_(True),
            )
        )
        if mapping is not None:
            return mapping
        if not reference.provider_external_id:
            return None
        return session.scalar(
            select(RealPlayerReferenceMapping).where(
                RealPlayerReferenceMapping.source_name == reference.source_name,
                RealPlayerReferenceMapping.entity_type == reference.entity_type,
                RealPlayerReferenceMapping.provider_external_id == reference.provider_external_id,
                RealPlayerReferenceMapping.is_active.is_(True),
            )
        )

    def _mapping_resolution(
        self,
        session: Session,
        mapping: RealPlayerReferenceMapping,
        reference: CanonicalReferenceInput,
    ) -> CanonicalReferenceResolution | None:
        entity = self._mapping_entity(session, mapping)
        if entity is None:
            return None
        return CanonicalReferenceResolution(
            entity_type=reference.entity_type,
            status=mapping.mapping_status,
            provider_reference_key=mapping.provider_reference_key,
            provider_external_id=mapping.provider_external_id,
            provider_label=mapping.provider_label,
            normalized_label=mapping.normalized_label,
            resolution_method=mapping.resolution_method,
            confidence_score=float(mapping.confidence_score or 0.0),
            mapping_id=mapping.id,
            canonical_country_id=mapping.canonical_country_id,
            canonical_competition_id=mapping.canonical_competition_id,
            canonical_club_id=mapping.canonical_club_id,
            canonical_name=getattr(entity, "name", None),
            team_identity_kind=mapping.team_identity_kind,
            entity=entity,
        )

    def _mapping_entity(
        self,
        session: Session,
        mapping: RealPlayerReferenceMapping,
    ) -> Country | Competition | Club | None:
        if mapping.canonical_country_id:
            return session.get(Country, mapping.canonical_country_id)
        if mapping.canonical_competition_id:
            return session.get(Competition, mapping.canonical_competition_id)
        if mapping.canonical_club_id:
            return session.get(Club, mapping.canonical_club_id)
        return None

    def _match_country_by_provider(self, session: Session, reference: CanonicalReferenceInput) -> Country | None:
        if not reference.provider_external_id:
            return None
        return session.scalar(
            select(Country).where(
                Country.source_provider == reference.source_name,
                Country.provider_external_id == reference.provider_external_id,
            )
        )

    def _match_competition_by_provider(self, session: Session, reference: CanonicalReferenceInput) -> Competition | None:
        if not reference.provider_external_id:
            return None
        return session.scalar(
            select(Competition).where(
                Competition.source_provider == reference.source_name,
                Competition.provider_external_id == reference.provider_external_id,
            )
        )

    def _match_club_by_provider(self, session: Session, reference: CanonicalReferenceInput) -> Club | None:
        if not reference.provider_external_id:
            return None
        return session.scalar(
            select(Club).where(
                Club.source_provider == reference.source_name,
                Club.provider_external_id == reference.provider_external_id,
            )
        )

    def _prefer_competitions_by_country(
        self,
        candidates: list[Competition],
        *,
        country: Country | None,
    ) -> list[Competition]:
        if country is None:
            return candidates
        matched = [candidate for candidate in candidates if candidate.country_id == country.id]
        return matched or candidates

    def _prefer_clubs_by_competition(
        self,
        candidates: list[Club],
        *,
        competition: Competition | None,
    ) -> list[Club]:
        if competition is None:
            return candidates
        matched = [candidate for candidate in candidates if candidate.current_competition_id == competition.id]
        return matched or candidates

    def _prefer_clubs_by_country(
        self,
        candidates: list[Club],
        *,
        country: Country | None,
    ) -> list[Club]:
        if country is None:
            return candidates
        matched = [candidate for candidate in candidates if candidate.country_id == country.id]
        return matched or candidates

    def _persist_mapping(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        *,
        entity: Country | Competition | Club | None,
        mapping_status: str,
        resolution_method: str,
        confidence_score: float,
        as_of: datetime,
    ) -> CanonicalReferenceResolution:
        mapping = self._lookup_mapping(session, reference)
        if mapping is None:
            mapping = RealPlayerReferenceMapping(
                source_name=reference.source_name,
                entity_type=reference.entity_type,
                provider_reference_key=reference.provider_reference_key,
            )
            session.add(mapping)
        mapping.provider_external_id = reference.provider_external_id
        mapping.provider_label = reference.display_name
        mapping.normalized_label = reference.normalized_display_name
        mapping.team_identity_kind = reference.team_identity_kind
        mapping.mapping_status = mapping_status
        mapping.resolution_method = resolution_method
        mapping.confidence_score = confidence_score
        mapping.is_active = True
        mapping.metadata_json = {
            "country_code": reference.country_code,
            "country_name": reference.country_name,
            "competition_external_id": reference.competition_external_id,
            "competition_display_name": reference.competition_display_name,
            **reference.metadata_json,
        }
        mapping.canonical_country_id = entity.id if isinstance(entity, Country) else None
        mapping.canonical_competition_id = entity.id if isinstance(entity, Competition) else None
        mapping.canonical_club_id = entity.id if isinstance(entity, Club) else None
        session.flush()
        self._mark_unresolved_reference_resolved(session, reference, mapping=mapping, as_of=as_of)
        return CanonicalReferenceResolution(
            entity_type=reference.entity_type,
            status=mapping.mapping_status,
            provider_reference_key=mapping.provider_reference_key,
            provider_external_id=mapping.provider_external_id,
            provider_label=mapping.provider_label,
            normalized_label=mapping.normalized_label,
            resolution_method=mapping.resolution_method,
            confidence_score=float(mapping.confidence_score or 0.0),
            mapping_id=mapping.id,
            canonical_country_id=mapping.canonical_country_id,
            canonical_competition_id=mapping.canonical_competition_id,
            canonical_club_id=mapping.canonical_club_id,
            canonical_name=getattr(entity, "name", None),
            team_identity_kind=mapping.team_identity_kind,
            entity=entity,
        )

    def _record_unresolved(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        *,
        reason_code: str,
        as_of: datetime,
        sample_payload: dict[str, Any] | None,
        notes: str | None,
        metadata_json: dict[str, Any] | None = None,
    ) -> CanonicalReferenceResolution:
        unresolved = session.scalar(
            select(RealPlayerUnresolvedReference).where(
                RealPlayerUnresolvedReference.source_name == reference.source_name,
                RealPlayerUnresolvedReference.entity_type == reference.entity_type,
                RealPlayerUnresolvedReference.provider_reference_key == reference.provider_reference_key,
            )
        )
        if unresolved is None:
            unresolved = RealPlayerUnresolvedReference(
                source_name=reference.source_name,
                entity_type=reference.entity_type,
                provider_reference_key=reference.provider_reference_key,
                first_seen_at=as_of,
                last_seen_at=as_of,
                reason_code=reason_code,
            )
            session.add(unresolved)
        else:
            unresolved.occurrence_count += 1
            unresolved.last_seen_at = as_of
        unresolved.provider_external_id = reference.provider_external_id
        unresolved.raw_label = reference.display_name
        unresolved.normalized_label = reference.normalized_display_name
        unresolved.team_identity_kind = reference.team_identity_kind
        unresolved.reason_code = reason_code
        unresolved.status = "open"
        unresolved.resolved_at = None
        unresolved.canonical_country_id = None
        unresolved.canonical_competition_id = None
        unresolved.canonical_club_id = None
        unresolved.sample_payload_json = sample_payload or {}
        unresolved.notes = notes
        unresolved.metadata_json = {
            "country_code": reference.country_code,
            "country_name": reference.country_name,
            "competition_external_id": reference.competition_external_id,
            "competition_display_name": reference.competition_display_name,
            **(metadata_json or {}),
            **reference.metadata_json,
        }
        session.flush()
        return CanonicalReferenceResolution(
            entity_type=reference.entity_type,
            status=CanonicalReferenceStatus.UNRESOLVED.value,
            provider_reference_key=reference.provider_reference_key,
            provider_external_id=reference.provider_external_id,
            provider_label=reference.display_name,
            normalized_label=reference.normalized_display_name,
            resolution_method="unresolved",
            confidence_score=0.0,
            unresolved_reference_id=unresolved.id,
            reason_code=reason_code,
            team_identity_kind=reference.team_identity_kind,
        )

    def _mark_unresolved_reference_resolved(
        self,
        session: Session,
        reference: CanonicalReferenceInput,
        *,
        mapping: RealPlayerReferenceMapping,
        as_of: datetime,
    ) -> None:
        unresolved = session.scalar(
            select(RealPlayerUnresolvedReference).where(
                RealPlayerUnresolvedReference.source_name == reference.source_name,
                RealPlayerUnresolvedReference.entity_type == reference.entity_type,
                RealPlayerUnresolvedReference.provider_reference_key == reference.provider_reference_key,
            )
        )
        if unresolved is None:
            return
        unresolved.status = "resolved"
        unresolved.resolved_at = as_of
        unresolved.canonical_country_id = mapping.canonical_country_id
        unresolved.canonical_competition_id = mapping.canonical_competition_id
        unresolved.canonical_club_id = mapping.canonical_club_id
        unresolved.metadata_json = {
            **(unresolved.metadata_json or {}),
            "resolved_mapping_id": mapping.id,
            "resolved_method": mapping.resolution_method,
        }
        session.flush()

    def _skipped_resolution(
        self,
        reference: CanonicalReferenceInput,
        *,
        reason_code: str,
    ) -> CanonicalReferenceResolution:
        return CanonicalReferenceResolution(
            entity_type=reference.entity_type,
            status=CanonicalReferenceStatus.SKIPPED.value,
            provider_reference_key=reference.provider_reference_key if reference.has_reference else None,
            provider_external_id=reference.provider_external_id,
            provider_label=reference.display_name,
            normalized_label=reference.normalized_display_name,
            resolution_method="skipped",
            confidence_score=0.0,
            reason_code=reason_code,
            team_identity_kind=reference.team_identity_kind,
        )


__all__ = [
    "CanonicalReferenceEntityType",
    "CanonicalReferenceInput",
    "CanonicalReferenceResolution",
    "CanonicalReferenceStatus",
    "RealPlayerCanonicalMappingService",
]
