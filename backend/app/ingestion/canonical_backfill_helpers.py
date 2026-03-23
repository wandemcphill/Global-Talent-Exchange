from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.ingestion.models import Club, Competition, Country
from app.ingestion.normalizers import (
    clean_name,
    normalize_club_name,
    normalize_competition_name,
    normalize_country_name,
    slugify,
)

FOOTBALLSQUADS_PROVIDER = "footballsquads"
_FOOTBALLSQUADS_KEY_SEPARATOR_RE = re.compile(r"[:/|]+")


def _clean_source_name(value: str | None) -> str | None:
    cleaned = clean_name(value)
    return cleaned.lower() if cleaned else None


def normalize_footballsquads_provider_key(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    segments = [
        slugify(segment)
        for segment in _FOOTBALLSQUADS_KEY_SEPARATOR_RE.split(cleaned)
        if clean_name(segment)
    ]
    normalized = "-".join(segment for segment in segments if segment and segment != "unknown").strip("-")
    if normalized:
        return normalized
    return slugify(cleaned)


def _normalize_provider_external_id(source_name: str, value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    if _clean_source_name(source_name) == FOOTBALLSQUADS_PROVIDER:
        return normalize_footballsquads_provider_key(cleaned)
    return slugify(cleaned)


def build_provider_reference_key(
    *,
    source_name: str,
    entity_type: str,
    provider_external_id: str | None = None,
    display_name: str | None = None,
    country_code: str | None = None,
    country_name: str | None = None,
    competition_external_id: str | None = None,
    competition_display_name: str | None = None,
) -> str:
    explicit_key = _normalize_provider_external_id(source_name, provider_external_id)
    if explicit_key:
        return explicit_key
    parts: list[str] = []
    if entity_type in {"competition", "club", "team_identity"}:
        if country_code:
            parts.append(country_code)
        elif country_name:
            parts.append(country_name)
    if entity_type in {"club", "team_identity"}:
        if competition_external_id:
            parts.append(competition_external_id)
        elif competition_display_name:
            parts.append(competition_display_name)
    if display_name:
        parts.append(display_name)
    if not parts and country_name:
        parts.append(country_name)
    return slugify("::".join(parts))


def _country_code_values(*values: str | None) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = clean_name(value)
        if not cleaned:
            continue
        normalized = cleaned.upper()
        if len(normalized) not in {2, 3} or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _natural_lookup_keys(*pairs: tuple[str, str | None]) -> tuple[tuple[str, str], ...]:
    keys: list[tuple[str, str]] = []
    for name, value in pairs:
        cleaned = clean_name(value)
        if not cleaned:
            continue
        keys.append((name, cleaned))
    return tuple(keys)


def _country_payload_codes(country_code_values: tuple[str, ...]) -> dict[str, str]:
    alpha2 = next((value for value in country_code_values if len(value) == 2), None)
    alpha3 = next((value for value in country_code_values if len(value) == 3), None)
    payload: dict[str, str] = {}
    if alpha2:
        payload["alpha2_code"] = alpha2
    if alpha3:
        payload["alpha3_code"] = alpha3
        payload["fifa_code"] = alpha3
    return payload


@dataclass(frozen=True, slots=True)
class CanonicalEntityCreatePlan:
    entity_type: str
    source_provider: str
    provider_external_id: str
    provider_reference_key: str
    display_name: str
    normalized_name: str
    slug: str | None
    payload: dict[str, Any]
    natural_lookup_keys: tuple[tuple[str, str], ...]
    country_code_values: tuple[str, ...] = ()
    country_id: str | None = None
    competition_id: str | None = None

    @property
    def provider_lookup_key(self) -> tuple[str, str]:
        return (self.source_provider, self.provider_external_id)


@dataclass(frozen=True, slots=True)
class CanonicalCandidateEvidence:
    entity_type: str
    candidate_id: str | None
    source_provider_match: bool
    provider_external_id_match: bool
    normalized_name_match: bool
    slug_match: bool | None = None
    short_name_match: bool | None = None
    country_code_match: bool | None = None
    country_context_match: bool | None = None
    competition_context_match: bool | None = None

    @property
    def supporting_signals(self) -> tuple[str, ...]:
        signals: list[str] = []
        for name, matched in (
            ("source_provider", self.source_provider_match),
            ("provider_external_id", self.provider_external_id_match),
            ("normalized_name", self.normalized_name_match),
            ("slug", self.slug_match),
            ("short_name", self.short_name_match),
            ("country_code", self.country_code_match),
            ("country_context", self.country_context_match),
            ("competition_context", self.competition_context_match),
        ):
            if matched:
                signals.append(name)
        return tuple(signals)

    @property
    def blocking_signals(self) -> tuple[str, ...]:
        signals: list[str] = []
        for name, matched in (
            ("country_code", self.country_code_match),
            ("country_context", self.country_context_match),
            ("competition_context", self.competition_context_match),
        ):
            if matched is False:
                signals.append(name)
        return tuple(signals)

    def to_dict(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "candidate_id": self.candidate_id,
            "source_provider_match": self.source_provider_match,
            "provider_external_id_match": self.provider_external_id_match,
            "normalized_name_match": self.normalized_name_match,
            "slug_match": self.slug_match,
            "short_name_match": self.short_name_match,
            "country_code_match": self.country_code_match,
            "country_context_match": self.country_context_match,
            "competition_context_match": self.competition_context_match,
            "supporting_signals": list(self.supporting_signals),
            "blocking_signals": list(self.blocking_signals),
        }


def prepare_country_create_plan(
    *,
    source_name: str,
    provider_external_id: str | None = None,
    display_name: str | None = None,
    country_code: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> CanonicalEntityCreatePlan:
    cleaned_source = clean_name(source_name) or "unknown"
    normalized_name = normalize_country_name(display_name) or clean_name(display_name) or "Unknown"
    provider_reference_key = build_provider_reference_key(
        source_name=cleaned_source,
        entity_type="country",
        provider_external_id=provider_external_id,
        display_name=display_name,
        country_code=country_code,
        country_name=display_name,
    )
    provider_identity = clean_name(provider_external_id) or provider_reference_key
    country_code_values = _country_code_values(country_code, provider_external_id)
    payload = {
        "source_provider": cleaned_source,
        "provider_external_id": provider_identity,
        "name": normalized_name,
        **_country_payload_codes(country_code_values),
    }
    payload.update(extra_fields or {})
    return CanonicalEntityCreatePlan(
        entity_type="country",
        source_provider=cleaned_source,
        provider_external_id=provider_identity,
        provider_reference_key=provider_reference_key,
        display_name=clean_name(display_name) or normalized_name,
        normalized_name=normalized_name,
        slug=None,
        payload=payload,
        natural_lookup_keys=_natural_lookup_keys(
            ("name", normalized_name),
            ("alpha2_code", payload.get("alpha2_code")),
            ("alpha3_code", payload.get("alpha3_code")),
            ("fifa_code", payload.get("fifa_code")),
        ),
        country_code_values=country_code_values,
    )


def prepare_competition_create_plan(
    *,
    source_name: str,
    provider_external_id: str | None = None,
    display_name: str | None = None,
    country_id: str | None = None,
    country_code: str | None = None,
    country_name: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> CanonicalEntityCreatePlan:
    cleaned_source = clean_name(source_name) or "unknown"
    normalized_name = normalize_competition_name(display_name) or clean_name(display_name) or "Unknown Competition"
    slug = slugify(normalized_name)
    provider_reference_key = build_provider_reference_key(
        source_name=cleaned_source,
        entity_type="competition",
        provider_external_id=provider_external_id,
        display_name=display_name,
        country_code=country_code,
        country_name=country_name,
    )
    provider_identity = clean_name(provider_external_id) or provider_reference_key
    payload = {
        "source_provider": cleaned_source,
        "provider_external_id": provider_identity,
        "country_id": country_id,
        "name": normalized_name,
        "slug": slug,
    }
    payload.update(extra_fields or {})
    return CanonicalEntityCreatePlan(
        entity_type="competition",
        source_provider=cleaned_source,
        provider_external_id=provider_identity,
        provider_reference_key=provider_reference_key,
        display_name=clean_name(display_name) or normalized_name,
        normalized_name=normalized_name,
        slug=slug,
        payload=payload,
        natural_lookup_keys=_natural_lookup_keys(
            ("name", normalized_name),
            ("slug", slug),
            ("country_id", country_id),
        ),
        country_id=country_id,
    )


def prepare_club_create_plan(
    *,
    source_name: str,
    provider_external_id: str | None = None,
    display_name: str | None = None,
    country_id: str | None = None,
    country_code: str | None = None,
    country_name: str | None = None,
    competition_id: str | None = None,
    competition_external_id: str | None = None,
    competition_display_name: str | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> CanonicalEntityCreatePlan:
    cleaned_source = clean_name(source_name) or "unknown"
    normalized_name = normalize_club_name(display_name) or clean_name(display_name) or "Unknown Club"
    slug = slugify(normalized_name)
    provider_reference_key = build_provider_reference_key(
        source_name=cleaned_source,
        entity_type="club",
        provider_external_id=provider_external_id,
        display_name=display_name,
        country_code=country_code,
        country_name=country_name,
        competition_external_id=competition_external_id,
        competition_display_name=competition_display_name,
    )
    provider_identity = clean_name(provider_external_id) or provider_reference_key
    payload = {
        "source_provider": cleaned_source,
        "provider_external_id": provider_identity,
        "country_id": country_id,
        "current_competition_id": competition_id,
        "name": normalized_name,
        "slug": slug,
    }
    payload.update(extra_fields or {})
    short_name = clean_name(str(payload.get("short_name"))) if payload.get("short_name") is not None else None
    return CanonicalEntityCreatePlan(
        entity_type="club",
        source_provider=cleaned_source,
        provider_external_id=provider_identity,
        provider_reference_key=provider_reference_key,
        display_name=clean_name(display_name) or normalized_name,
        normalized_name=normalized_name,
        slug=slug,
        payload=payload,
        natural_lookup_keys=_natural_lookup_keys(
            ("name", normalized_name),
            ("slug", slug),
            ("short_name", short_name),
            ("country_id", country_id),
            ("current_competition_id", competition_id),
        ),
        country_id=country_id,
        competition_id=competition_id,
    )


def compare_candidate_evidence(
    plan: CanonicalEntityCreatePlan,
    candidate: Country | Competition | Club,
) -> CanonicalCandidateEvidence:
    if plan.entity_type == "country":
        if not isinstance(candidate, Country):
            raise TypeError("Country create plans can only be compared against Country candidates.")
        candidate_name = normalize_country_name(candidate.name) or clean_name(candidate.name) or ""
        candidate_codes = {
            code.upper()
            for code in (
                clean_name(candidate.alpha2_code),
                clean_name(candidate.alpha3_code),
                clean_name(candidate.fifa_code),
            )
            if code
        }
        country_code_match = None if not plan.country_code_values else bool(candidate_codes & set(plan.country_code_values))
        return CanonicalCandidateEvidence(
            entity_type=plan.entity_type,
            candidate_id=candidate.id,
            source_provider_match=candidate.source_provider == plan.source_provider,
            provider_external_id_match=clean_name(candidate.provider_external_id) == plan.provider_external_id,
            normalized_name_match=candidate_name == plan.normalized_name,
            country_code_match=country_code_match,
        )

    if plan.entity_type == "competition":
        if not isinstance(candidate, Competition):
            raise TypeError("Competition create plans can only be compared against Competition candidates.")
        candidate_name = normalize_competition_name(candidate.name) or clean_name(candidate.name) or ""
        candidate_slug = clean_name(candidate.slug)
        return CanonicalCandidateEvidence(
            entity_type=plan.entity_type,
            candidate_id=candidate.id,
            source_provider_match=candidate.source_provider == plan.source_provider,
            provider_external_id_match=clean_name(candidate.provider_external_id) == plan.provider_external_id,
            normalized_name_match=candidate_name == plan.normalized_name,
            slug_match=None if plan.slug is None else candidate_slug == plan.slug,
            country_context_match=None if plan.country_id is None else candidate.country_id == plan.country_id,
        )

    if plan.entity_type != "club":
        raise ValueError(f"Unsupported canonical entity type '{plan.entity_type}'.")
    if not isinstance(candidate, Club):
        raise TypeError("Club create plans can only be compared against Club candidates.")
    candidate_name = normalize_club_name(candidate.name) or clean_name(candidate.name) or ""
    candidate_slug = clean_name(candidate.slug)
    candidate_short_name = clean_name(candidate.short_name)
    normalized_short_name = normalize_club_name(candidate_short_name) if candidate_short_name else None
    return CanonicalCandidateEvidence(
        entity_type=plan.entity_type,
        candidate_id=candidate.id,
        source_provider_match=candidate.source_provider == plan.source_provider,
        provider_external_id_match=clean_name(candidate.provider_external_id) == plan.provider_external_id,
        normalized_name_match=candidate_name == plan.normalized_name,
        slug_match=None if plan.slug is None else candidate_slug == plan.slug,
        short_name_match=None if normalized_short_name is None else normalized_short_name == plan.normalized_name,
        country_context_match=None if plan.country_id is None else candidate.country_id == plan.country_id,
        competition_context_match=None if plan.competition_id is None else candidate.current_competition_id == plan.competition_id,
    )


__all__ = [
    "CanonicalCandidateEvidence",
    "CanonicalEntityCreatePlan",
    "FOOTBALLSQUADS_PROVIDER",
    "build_provider_reference_key",
    "compare_candidate_evidence",
    "normalize_footballsquads_provider_key",
    "prepare_club_create_plan",
    "prepare_competition_create_plan",
    "prepare_country_create_plan",
]
