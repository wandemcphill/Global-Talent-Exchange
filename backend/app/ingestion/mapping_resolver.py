from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Club, Country

from .mapping_registry import (
    CLUB_ALIAS_LOOKUP,
    CLUB_PLACEHOLDER_LABELS,
    COUNTRY_ALIAS_LOOKUP,
    normalize_registry_key,
)


FUZZY_MATCH_THRESHOLD = 0.94
FUZZY_MATCH_MARGIN = 0.03


def normalize_string(value: str | None) -> str | None:
    return normalize_registry_key(value)


@dataclass(frozen=True, slots=True)
class ClubResolutionContext:
    competition_name: str | None = None
    competition_id: str | None = None
    country_name: str | None = None
    country_id: str | None = None


@dataclass(frozen=True, slots=True)
class MappingResolution:
    entity_type: str
    status: str
    raw_name: str | None
    normalized_input: str | None
    resolution_method: str
    confidence_score: float
    reason_code: str | None = None
    canonical_name: str | None = None
    canonical_id: str | None = None

    def metadata(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "status": self.status,
            "raw_name": self.raw_name,
            "normalized_input": self.normalized_input,
            "resolution_method": self.resolution_method,
            "confidence_score": self.confidence_score,
            "reason_code": self.reason_code,
            "canonical_name": self.canonical_name,
            "canonical_id": self.canonical_id,
        }


@dataclass(frozen=True, slots=True)
class ResolvedCountryMapping(MappingResolution):
    entity: Country | None = None


@dataclass(frozen=True, slots=True)
class ResolvedClubMapping(MappingResolution):
    entity: Club | None = None


@dataclass(frozen=True, slots=True)
class _CountryEntry:
    entity_id: str
    canonical_name: str
    normalized_name: str
    codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ClubEntry:
    entity_id: str
    canonical_name: str
    normalized_names: tuple[str, ...]
    competition_id: str | None
    competition_name: str | None
    country_id: str | None
    country_name: str | None


@dataclass(slots=True)
class MappingResolver:
    fuzzy_threshold: float = FUZZY_MATCH_THRESHOLD
    fuzzy_margin: float = FUZZY_MATCH_MARGIN
    _country_entries: tuple[_CountryEntry, ...] = field(default_factory=tuple, init=False)
    _country_by_name: dict[str, tuple[_CountryEntry, ...]] = field(default_factory=dict, init=False)
    _country_by_code: dict[str, tuple[_CountryEntry, ...]] = field(default_factory=dict, init=False)
    _club_entries: tuple[_ClubEntry, ...] = field(default_factory=tuple, init=False)
    _club_by_name: dict[str, tuple[_ClubEntry, ...]] = field(default_factory=dict, init=False)

    def resolve_country(
        self,
        session: Session,
        *,
        raw_name: str | None,
        raw_code: str | None = None,
    ) -> ResolvedCountryMapping:
        self._ensure_country_index(session)
        normalized_input = normalize_registry_key(raw_name, strip_suffixes=False)
        normalized_code = (raw_code or "").strip().upper() or None
        if normalized_code:
            code_matches = self._country_by_code.get(normalized_code, ())
            if len(code_matches) == 1:
                return self._resolved_country(
                    session,
                    code_matches[0],
                    raw_name=raw_name,
                    normalized_input=normalized_input,
                    method="code_exact",
                    confidence=1.0,
                )
            if len(code_matches) > 1:
                return self._unresolved_country(
                    raw_name=raw_name,
                    normalized_input=normalized_input,
                    reason_code="ambiguous_country_code_match",
                )
        if not normalized_input:
            return self._skipped_country(raw_name=raw_name, reason_code="missing_reference")

        exact_matches = self._country_by_name.get(normalized_input, ())
        if len(exact_matches) == 1:
            return self._resolved_country(
                session,
                exact_matches[0],
                raw_name=raw_name,
                normalized_input=normalized_input,
                method="exact",
                confidence=1.0,
            )
        if len(exact_matches) > 1:
            return self._unresolved_country(
                raw_name=raw_name,
                normalized_input=normalized_input,
                reason_code="ambiguous_country_match",
            )

        alias_target = COUNTRY_ALIAS_LOOKUP.get(normalized_input)
        if alias_target:
            alias_matches = self._country_by_name.get(alias_target, ())
            if len(alias_matches) == 1:
                return self._resolved_country(
                    session,
                    alias_matches[0],
                    raw_name=raw_name,
                    normalized_input=normalized_input,
                    method="alias",
                    confidence=0.99,
                )
            if len(alias_matches) > 1:
                return self._unresolved_country(
                    raw_name=raw_name,
                    normalized_input=normalized_input,
                    reason_code="ambiguous_country_alias_match",
                )

        fuzzy_match = self._best_fuzzy_country_match(normalized_input)
        if fuzzy_match is not None:
            entry, score = fuzzy_match
            return self._resolved_country(
                session,
                entry,
                raw_name=raw_name,
                normalized_input=normalized_input,
                method="fuzzy",
                confidence=score,
            )
        return self._unresolved_country(
            raw_name=raw_name,
            normalized_input=normalized_input,
            reason_code="country_not_found",
        )

    def resolve_club(
        self,
        session: Session,
        *,
        raw_name: str | None,
        context: ClubResolutionContext | None = None,
    ) -> ResolvedClubMapping:
        self._ensure_club_index(session)
        normalized_input = normalize_string(raw_name)
        if not normalized_input:
            return self._skipped_club(raw_name=raw_name, reason_code="missing_reference")
        if normalized_input in CLUB_PLACEHOLDER_LABELS:
            return self._skipped_club(raw_name=raw_name, normalized_input=normalized_input, reason_code="club_placeholder")

        exact_resolution = self._select_club_from_candidates(
            session,
            candidates=self._club_by_name.get(normalized_input, ()),
            raw_name=raw_name,
            normalized_input=normalized_input,
            method="exact",
            ambiguous_reason="ambiguous_club_match",
        )
        if exact_resolution is not None and (exact_resolution.status == "resolved" or context is None):
            return exact_resolution

        alias_target = CLUB_ALIAS_LOOKUP.get(normalized_input)
        if alias_target:
            alias_resolution = self._select_club_from_candidates(
                session,
                candidates=self._club_by_name.get(alias_target, ()),
                raw_name=raw_name,
                normalized_input=normalized_input,
                method="alias",
                ambiguous_reason="ambiguous_club_alias_match",
                confidence=0.99,
            )
            if alias_resolution is not None and (alias_resolution.status == "resolved" or context is None):
                return alias_resolution

        fuzzy_resolution = self._fuzzy_club_candidates(
            session,
            candidates=self._club_entries,
            raw_name=raw_name,
            normalized_input=normalized_input,
            method="fuzzy",
        )
        if fuzzy_resolution is not None:
            return fuzzy_resolution

        if context is not None:
            context_candidates = self._filter_clubs_by_context(self._club_entries, context=context)
            if context_candidates:
                context_exact = self._select_club_from_candidates(
                    session,
                    candidates=tuple(entry for entry in context_candidates if normalized_input in entry.normalized_names),
                    raw_name=raw_name,
                    normalized_input=normalized_input,
                    method="context_exact",
                    ambiguous_reason="ambiguous_context_club_match",
                )
                if context_exact is not None:
                    return context_exact
                if alias_target:
                    context_alias = self._select_club_from_candidates(
                        session,
                        candidates=tuple(entry for entry in context_candidates if alias_target in entry.normalized_names),
                        raw_name=raw_name,
                        normalized_input=normalized_input,
                        method="context_alias",
                        ambiguous_reason="ambiguous_context_club_alias_match",
                        confidence=0.99,
                    )
                    if context_alias is not None:
                        return context_alias
                context_fuzzy = self._fuzzy_club_candidates(
                    session,
                    candidates=context_candidates,
                    raw_name=raw_name,
                    normalized_input=normalized_input,
                    method="context_fuzzy",
                )
                if context_fuzzy is not None:
                    return context_fuzzy

        return self._unresolved_club(
            raw_name=raw_name,
            normalized_input=normalized_input,
            reason_code="club_not_found",
        )

    def _ensure_country_index(self, session: Session) -> None:
        if self._country_entries:
            return
        entries: list[_CountryEntry] = []
        by_name: dict[str, list[_CountryEntry]] = {}
        by_code: dict[str, list[_CountryEntry]] = {}
        for country in session.scalars(select(Country)):
            normalized_name = normalize_registry_key(country.name, strip_suffixes=False)
            if normalized_name is None:
                continue
            codes = tuple(
                sorted(
                    {
                        value.strip().upper()
                        for value in (
                            country.alpha2_code,
                            country.alpha3_code,
                            country.fifa_code,
                            country.provider_external_id,
                        )
                        if value and value.strip()
                    }
                )
            )
            entry = _CountryEntry(
                entity_id=country.id,
                canonical_name=country.name,
                normalized_name=normalized_name,
                codes=codes,
            )
            entries.append(entry)
            by_name.setdefault(normalized_name, []).append(entry)
            for code in codes:
                by_code.setdefault(code, []).append(entry)
        self._country_entries = tuple(entries)
        self._country_by_name = {key: tuple(value) for key, value in by_name.items()}
        self._country_by_code = {key: tuple(value) for key, value in by_code.items()}

    def _ensure_club_index(self, session: Session) -> None:
        if self._club_entries:
            return
        entries: list[_ClubEntry] = []
        by_name: dict[str, list[_ClubEntry]] = {}
        clubs = list(
            session.scalars(
                select(Club).options(
                    selectinload(Club.current_competition),
                    selectinload(Club.country),
                )
            )
        )
        for club in clubs:
            normalized_names = tuple(
                sorted(
                    {
                        normalized
                        for normalized in (
                            normalize_string(club.name),
                            normalize_string(club.short_name),
                            normalize_string(club.code),
                            normalize_string(club.slug.replace("-", " ") if club.slug else None),
                        )
                        if normalized
                    }
                )
            )
            if not normalized_names:
                continue
            competition_name = (
                normalize_registry_key(club.current_competition.name, strip_suffixes=False)
                if club.current_competition is not None
                else None
            )
            country_name = (
                normalize_registry_key(club.country.name, strip_suffixes=False)
                if club.country is not None
                else None
            )
            entry = _ClubEntry(
                entity_id=club.id,
                canonical_name=club.name,
                normalized_names=normalized_names,
                competition_id=club.current_competition_id,
                competition_name=competition_name,
                country_id=club.country_id,
                country_name=country_name,
            )
            entries.append(entry)
            for name in normalized_names:
                by_name.setdefault(name, []).append(entry)
        self._club_entries = tuple(entries)
        self._club_by_name = {key: tuple(value) for key, value in by_name.items()}

    def _best_fuzzy_country_match(self, normalized_input: str) -> tuple[_CountryEntry, float] | None:
        scored = [
            (SequenceMatcher(None, normalized_input, entry.normalized_name).ratio(), entry)
            for entry in self._country_entries
        ]
        return self._best_scored_match(scored)

    def _fuzzy_club_candidates(
        self,
        session: Session,
        *,
        candidates: tuple[_ClubEntry, ...],
        raw_name: str | None,
        normalized_input: str,
        method: str,
    ) -> ResolvedClubMapping | None:
        scored = [
            (
                max(SequenceMatcher(None, normalized_input, candidate_name).ratio() for candidate_name in entry.normalized_names),
                entry,
            )
            for entry in candidates
        ]
        best = self._best_scored_match(scored)
        if best is None:
            return None
        entry, score = best
        return self._resolved_club(
            session,
            entry,
            raw_name=raw_name,
            normalized_input=normalized_input,
            method=method,
            confidence=score,
        )

    def _best_scored_match(self, scored_matches):
        filtered = [
            (score, entry)
            for score, entry in scored_matches
            if score >= self.fuzzy_threshold
        ]
        if not filtered:
            return None
        ordered = sorted(
            filtered,
            key=lambda item: (
                -item[0],
                item[1].canonical_name.casefold(),
                item[1].entity_id,
            ),
        )
        best_score, best_entry = ordered[0]
        second_score = ordered[1][0] if len(ordered) > 1 else None
        if second_score is not None and (best_score - second_score) < self.fuzzy_margin:
            return None
        return best_entry, best_score

    def _filter_clubs_by_context(
        self,
        candidates: tuple[_ClubEntry, ...],
        *,
        context: ClubResolutionContext,
    ) -> tuple[_ClubEntry, ...]:
        competition_name = normalize_registry_key(context.competition_name, strip_suffixes=False)
        country_name = normalize_registry_key(context.country_name, strip_suffixes=False)
        competition_id = (context.competition_id or "").strip() or None
        country_id = (context.country_id or "").strip() or None
        return tuple(
            entry
            for entry in candidates
            if (
                (competition_id and entry.competition_id == competition_id)
                or (competition_name and entry.competition_name == competition_name)
                or (country_id and entry.country_id == country_id)
                or (country_name and entry.country_name == country_name)
            )
        )

    def _select_club_from_candidates(
        self,
        session: Session,
        *,
        candidates: tuple[_ClubEntry, ...],
        raw_name: str | None,
        normalized_input: str,
        method: str,
        ambiguous_reason: str,
        confidence: float = 1.0,
    ) -> ResolvedClubMapping | None:
        if len(candidates) == 1:
            return self._resolved_club(
                session,
                candidates[0],
                raw_name=raw_name,
                normalized_input=normalized_input,
                method=method,
                confidence=confidence,
            )
        if len(candidates) > 1:
            return self._unresolved_club(
                raw_name=raw_name,
                normalized_input=normalized_input,
                reason_code=ambiguous_reason,
            )
        return None

    def _resolved_country(
        self,
        session: Session,
        entry: _CountryEntry,
        *,
        raw_name: str | None,
        normalized_input: str | None,
        method: str,
        confidence: float,
    ) -> ResolvedCountryMapping:
        return ResolvedCountryMapping(
            entity_type="country",
            status="resolved",
            raw_name=raw_name,
            normalized_input=normalized_input,
            resolution_method=method,
            confidence_score=confidence,
            canonical_name=entry.canonical_name,
            canonical_id=entry.entity_id,
            entity=session.get(Country, entry.entity_id),
        )

    def _resolved_club(
        self,
        session: Session,
        entry: _ClubEntry,
        *,
        raw_name: str | None,
        normalized_input: str | None,
        method: str,
        confidence: float,
    ) -> ResolvedClubMapping:
        return ResolvedClubMapping(
            entity_type="club",
            status="resolved",
            raw_name=raw_name,
            normalized_input=normalized_input,
            resolution_method=method,
            confidence_score=confidence,
            canonical_name=entry.canonical_name,
            canonical_id=entry.entity_id,
            entity=session.get(Club, entry.entity_id),
        )

    def _unresolved_country(
        self,
        *,
        raw_name: str | None,
        normalized_input: str | None,
        reason_code: str,
    ) -> ResolvedCountryMapping:
        return ResolvedCountryMapping(
            entity_type="country",
            status="unresolved",
            raw_name=raw_name,
            normalized_input=normalized_input,
            resolution_method="unresolved",
            confidence_score=0.0,
            reason_code=reason_code,
        )

    def _skipped_country(
        self,
        *,
        raw_name: str | None,
        reason_code: str,
    ) -> ResolvedCountryMapping:
        return ResolvedCountryMapping(
            entity_type="country",
            status="skipped",
            raw_name=raw_name,
            normalized_input=normalize_registry_key(raw_name, strip_suffixes=False),
            resolution_method="skipped",
            confidence_score=0.0,
            reason_code=reason_code,
        )

    def _unresolved_club(
        self,
        *,
        raw_name: str | None,
        normalized_input: str | None,
        reason_code: str,
    ) -> ResolvedClubMapping:
        return ResolvedClubMapping(
            entity_type="club",
            status="unresolved",
            raw_name=raw_name,
            normalized_input=normalized_input,
            resolution_method="unresolved",
            confidence_score=0.0,
            reason_code=reason_code,
        )

    def _skipped_club(
        self,
        *,
        raw_name: str | None,
        normalized_input: str | None = None,
        reason_code: str,
    ) -> ResolvedClubMapping:
        return ResolvedClubMapping(
            entity_type="club",
            status="skipped",
            raw_name=raw_name,
            normalized_input=normalized_input or normalize_string(raw_name),
            resolution_method="skipped",
            confidence_score=0.0,
            reason_code=reason_code,
        )


__all__ = [
    "ClubResolutionContext",
    "FUZZY_MATCH_MARGIN",
    "FUZZY_MATCH_THRESHOLD",
    "MappingResolution",
    "MappingResolver",
    "ResolvedClubMapping",
    "ResolvedCountryMapping",
    "normalize_string",
]
