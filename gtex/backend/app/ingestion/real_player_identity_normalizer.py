from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re
import unicodedata

from app.ingestion.normalizers import clean_name, normalize_country_name, slugify
from app.schemas.real_player_ingestion import RealPlayerSeedInput


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_POSITION_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")
_FOOT_ALIASES = {
    "left": "left",
    "left_foot": "left",
    "left_footed": "left",
    "right": "right",
    "right_foot": "right",
    "right_footed": "right",
    "both": "both",
    "either": "both",
    "two_footed": "both",
    "ambidextrous": "both",
}


@dataclass(frozen=True, slots=True)
class NormalizedIdentityName:
    normalized: str
    compact: str
    tokens: tuple[str, ...]
    token_signature: str

    @property
    def first_token(self) -> str:
        return self.tokens[0] if self.tokens else ""


@dataclass(frozen=True, slots=True)
class NormalizedExternalReference:
    display_name: str | None
    provider_key: str | None
    normalized_name: str
    identity_key: str | None


@dataclass(frozen=True, slots=True)
class NormalizedRealPlayerIdentity:
    source_name: str
    source_player_key: str
    provider_identity_key: str
    canonical_name: str
    display_name: str
    normalized_full_name: str
    normalized_display_name: str
    compact_name: str
    display_compact_name: str
    name_token_signature: str
    known_aliases: tuple[str, ...]
    normalized_aliases: tuple[str, ...]
    date_of_birth: date | None
    birth_year: int | None
    age_years: int | None
    nationality: str | None
    nationality_code: str | None
    normalized_nationality: str | None
    primary_position: str
    primary_position_key: str
    secondary_positions: tuple[str, ...]
    secondary_position_keys: tuple[str, ...]
    position_family: str
    dominant_foot: str | None
    height_cm: int | None
    club_name: str | None
    club_reference_key: str | None
    league_name: str | None
    league_reference_key: str | None
    exact_identity_key: str | None
    name_birthyear_club_key: str | None
    name_birthyear_nationality_key: str | None

    def name_variants(self) -> tuple[str, ...]:
        seen: set[str] = set()
        variants: list[str] = []
        for value in (self.canonical_name, self.display_name, *self.known_aliases):
            cleaned = clean_name(value)
            if not cleaned:
                continue
            folded = cleaned.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            variants.append(cleaned)
        return tuple(variants)

    def to_dict(self) -> dict[str, object]:
        return {
            "source_name": self.source_name,
            "source_player_key": self.source_player_key,
            "provider_identity_key": self.provider_identity_key,
            "canonical_name": self.canonical_name,
            "display_name": self.display_name,
            "normalized_full_name": self.normalized_full_name,
            "normalized_display_name": self.normalized_display_name,
            "compact_name": self.compact_name,
            "display_compact_name": self.display_compact_name,
            "name_token_signature": self.name_token_signature,
            "known_aliases": list(self.known_aliases),
            "normalized_aliases": list(self.normalized_aliases),
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth is not None else None,
            "birth_year": self.birth_year,
            "age_years": self.age_years,
            "nationality": self.nationality,
            "nationality_code": self.nationality_code,
            "normalized_nationality": self.normalized_nationality,
            "primary_position": self.primary_position,
            "primary_position_key": self.primary_position_key,
            "secondary_positions": list(self.secondary_positions),
            "secondary_position_keys": list(self.secondary_position_keys),
            "position_family": self.position_family,
            "dominant_foot": self.dominant_foot,
            "height_cm": self.height_cm,
            "club_name": self.club_name,
            "club_reference_key": self.club_reference_key,
            "league_name": self.league_name,
            "league_reference_key": self.league_reference_key,
            "exact_identity_key": self.exact_identity_key,
            "name_birthyear_club_key": self.name_birthyear_club_key,
            "name_birthyear_nationality_key": self.name_birthyear_nationality_key,
        }


def fold_identity_name(value: str | None) -> str:
    if value is None:
        return ""
    folded = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return _NON_ALNUM_RE.sub(" ", folded.lower()).strip()


def normalize_identity_name(value: str | None) -> NormalizedIdentityName:
    normalized = fold_identity_name(value)
    tokens = tuple(token for token in normalized.split() if token)
    compact = "".join(tokens)
    return NormalizedIdentityName(
        normalized=normalized,
        compact=compact,
        tokens=tokens,
        token_signature="|".join(sorted(tokens)),
    )


def names_equivalent(left: str | None, right: str | None) -> bool:
    left_name = normalize_identity_name(left)
    right_name = normalize_identity_name(right)
    if not left_name.tokens or not right_name.tokens:
        return False
    if left_name.normalized == right_name.normalized or left_name.compact == right_name.compact:
        return True
    return left_name.token_signature == right_name.token_signature and left_name.first_token == right_name.first_token


def canonical_position_key(value: str | None) -> str:
    normalized = _POSITION_NON_ALNUM_RE.sub("_", (value or "").lower()).strip("_")
    if normalized in {"gk", "goalkeeper"}:
        return "goalkeeper"
    if normalized in {"cb", "centre_back", "center_back", "centreback", "centerback"}:
        return "centre_back"
    if normalized in {"lb", "rb", "full_back", "left_back", "right_back", "wing_back", "wingback"}:
        return "full_back"
    if normalized in {"dm", "cdm", "defensive_midfielder"}:
        return "defensive_midfielder"
    if normalized in {"cm", "midfielder", "central_midfielder"}:
        return "central_midfielder"
    if normalized in {"am", "cam", "attacking_midfielder"}:
        return "attacking_midfielder"
    if normalized in {"lw", "rw", "winger", "wide_forward"}:
        return "winger"
    if normalized in {"st", "cf", "striker", "forward", "centre_forward", "center_forward"}:
        return "striker"
    return normalized or "central_midfielder"


def normalize_primary_position(value: str | None) -> str:
    key = canonical_position_key(value)
    return {
        "goalkeeper": "Goalkeeper",
        "centre_back": "Centre-Back",
        "full_back": "Full-Back",
        "defensive_midfielder": "Defensive Midfielder",
        "central_midfielder": "Central Midfielder",
        "attacking_midfielder": "Attacking Midfielder",
        "winger": "Winger",
        "striker": "Striker",
    }.get(key, "Central Midfielder")


def position_family(value: str | None) -> str:
    key = canonical_position_key(value)
    if key == "goalkeeper":
        return "goalkeeper"
    if key in {"centre_back", "full_back"}:
        return "defender"
    if key in {"winger", "striker"}:
        return "forward"
    return "midfielder"


def normalize_secondary_positions(values: list[str], *, primary_position: str) -> tuple[str, ...]:
    primary_key = canonical_position_key(primary_position)
    seen: set[str] = set()
    positions: list[str] = []
    for value in values:
        normalized = normalize_primary_position(value)
        position_key = canonical_position_key(normalized)
        if not position_key or position_key == primary_key or position_key in seen:
            continue
        seen.add(position_key)
        positions.append(normalized)
    return tuple(positions)


def normalize_preferred_foot(value: str | None) -> str | None:
    normalized = _POSITION_NON_ALNUM_RE.sub("_", (value or "").strip().lower()).strip("_")
    if not normalized:
        return None
    return _FOOT_ALIASES.get(normalized, normalized[:16])


def normalize_external_reference(value: str | None, provider_key: str | None) -> NormalizedExternalReference:
    display_name = clean_name(value)
    normalized_name = normalize_identity_name(display_name).normalized if display_name else ""
    cleaned_provider_key = clean_name(provider_key)
    identity_key = slugify(display_name or cleaned_provider_key) if (display_name or cleaned_provider_key) else None
    return NormalizedExternalReference(
        display_name=display_name,
        provider_key=cleaned_provider_key,
        normalized_name=normalized_name,
        identity_key=identity_key,
    )


def normalize_real_player_identity(payload: RealPlayerSeedInput, *, as_of: date) -> NormalizedRealPlayerIdentity:
    canonical_name = clean_name(payload.canonical_name) or payload.canonical_name.strip()
    display_name = clean_name(payload.display_name) or canonical_name
    canonical_normalized = normalize_identity_name(canonical_name)
    display_normalized = normalize_identity_name(display_name)
    known_aliases = _dedupe_names(payload.known_aliases, exclude=(canonical_name, display_name))
    normalized_aliases = tuple(
        dict.fromkeys(
            normalized.normalized
            for normalized in (normalize_identity_name(value) for value in known_aliases)
            if normalized.tokens
        )
    )
    date_of_birth = payload.date_of_birth
    birth_year = _resolve_birth_year(date_of_birth, payload.birth_year, payload.age, as_of)
    age_years = _resolve_age_years(date_of_birth, birth_year, payload.age, as_of)
    nationality = _normalize_nationality_name(payload.nationality)
    nationality_code = _normalize_country_code(payload.nationality_code)
    normalized_nationality = normalize_identity_name(nationality).normalized if nationality else None
    primary_position = normalize_primary_position(payload.primary_position)
    primary_position_key = canonical_position_key(primary_position)
    secondary_positions = normalize_secondary_positions(payload.secondary_positions, primary_position=primary_position)
    secondary_position_keys = tuple(canonical_position_key(value) for value in secondary_positions)
    dominant_foot = normalize_preferred_foot(payload.dominant_foot)
    club_reference = normalize_external_reference(payload.current_real_world_club, payload.current_real_world_club_key)
    league_reference = normalize_external_reference(payload.current_real_world_league, payload.current_real_world_league_key)
    provider_identity_key = f"{slugify(payload.source_name)}::{slugify(payload.source_player_key)}"
    exact_identity_key = (
        f"{canonical_normalized.normalized}|{date_of_birth.isoformat()}"
        if date_of_birth is not None and canonical_normalized.tokens
        else None
    )
    name_birthyear_club_key = _fallback_identity_key(
        token_signature=canonical_normalized.token_signature,
        birth_year=birth_year,
        anchor_key=club_reference.identity_key,
        anchor_type="club",
    )
    nationality_anchor = nationality_code or normalized_nationality
    name_birthyear_nationality_key = _fallback_identity_key(
        token_signature=canonical_normalized.token_signature,
        birth_year=birth_year,
        anchor_key=nationality_anchor,
        anchor_type="nat",
    )
    return NormalizedRealPlayerIdentity(
        source_name=payload.source_name,
        source_player_key=payload.source_player_key,
        provider_identity_key=provider_identity_key,
        canonical_name=canonical_name,
        display_name=display_name,
        normalized_full_name=canonical_normalized.normalized,
        normalized_display_name=display_normalized.normalized,
        compact_name=canonical_normalized.compact,
        display_compact_name=display_normalized.compact,
        name_token_signature=canonical_normalized.token_signature,
        known_aliases=known_aliases,
        normalized_aliases=normalized_aliases,
        date_of_birth=date_of_birth,
        birth_year=birth_year,
        age_years=age_years,
        nationality=nationality,
        nationality_code=nationality_code,
        normalized_nationality=normalized_nationality,
        primary_position=primary_position,
        primary_position_key=primary_position_key,
        secondary_positions=secondary_positions,
        secondary_position_keys=secondary_position_keys,
        position_family=position_family(primary_position),
        dominant_foot=dominant_foot,
        height_cm=payload.height_cm,
        club_name=club_reference.display_name,
        club_reference_key=club_reference.identity_key,
        league_name=league_reference.display_name,
        league_reference_key=league_reference.identity_key,
        exact_identity_key=exact_identity_key,
        name_birthyear_club_key=name_birthyear_club_key,
        name_birthyear_nationality_key=name_birthyear_nationality_key,
    )


def _resolve_birth_year(
    date_of_birth: date | None,
    birth_year: int | None,
    age: int | None,
    reference_date: date,
) -> int | None:
    if date_of_birth is not None:
        return date_of_birth.year
    if birth_year is not None:
        return birth_year
    if age is not None:
        return reference_date.year - age
    return None


def _resolve_age_years(
    date_of_birth: date | None,
    birth_year: int | None,
    age: int | None,
    reference_date: date,
) -> int | None:
    if date_of_birth is not None:
        years = reference_date.year - date_of_birth.year
        if (reference_date.month, reference_date.day) < (date_of_birth.month, date_of_birth.day):
            years -= 1
        return max(years, 13)
    if age is not None:
        return max(age, 13)
    if birth_year is not None:
        return max(reference_date.year - birth_year, 13)
    return None


def _normalize_country_code(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    upper = cleaned.upper()
    if len(upper) not in {2, 3}:
        return upper[:12]
    return upper


def _normalize_nationality_name(value: str | None) -> str | None:
    cleaned = clean_name(value)
    if not cleaned:
        return None
    if len(cleaned) in {2, 3} and cleaned.upper() == cleaned:
        return None
    return normalize_country_name(cleaned) or cleaned


def _fallback_identity_key(
    *,
    token_signature: str,
    birth_year: int | None,
    anchor_key: str | None,
    anchor_type: str,
) -> str | None:
    if not token_signature or birth_year is None or not anchor_key:
        return None
    return f"{token_signature}|{birth_year}|{anchor_type}:{anchor_key}"


def _dedupe_names(values: list[str], *, exclude: tuple[str, ...]) -> tuple[str, ...]:
    seen = {value.casefold() for value in exclude if value}
    deduped: list[str] = []
    for value in values:
        cleaned = clean_name(value)
        if not cleaned:
            continue
        folded = cleaned.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        deduped.append(cleaned)
    return tuple(deduped)


__all__ = [
    "NormalizedExternalReference",
    "NormalizedIdentityName",
    "NormalizedRealPlayerIdentity",
    "canonical_position_key",
    "fold_identity_name",
    "names_equivalent",
    "normalize_external_reference",
    "normalize_identity_name",
    "normalize_preferred_foot",
    "normalize_primary_position",
    "normalize_real_player_identity",
    "normalize_secondary_positions",
    "position_family",
]
