from __future__ import annotations

from types import MappingProxyType
import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^0-9a-z\s]+")
_NOISY_SUFFIXES = ("fc", "cf", "sc", "afc", "u19", "u21", "b", "ii")
_MOJIBAKE_MARKERS = ("Ã", "â", "Â")
_APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "ʼ": "'",
        "`": "'",
        "´": "'",
    }
)


def normalize_registry_key(value: str | None, *, strip_suffixes: bool = True) -> str | None:
    if value is None:
        return None
    repaired_value = _repair_common_mojibake(value)
    ascii_value = (
        unicodedata.normalize("NFKD", repaired_value.translate(_APOSTROPHE_TRANSLATION))
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
        .strip()
    )
    if not ascii_value:
        return None
    ascii_value = _PUNCTUATION_RE.sub(" ", ascii_value)
    ascii_value = _WHITESPACE_RE.sub(" ", ascii_value).strip()
    if not ascii_value:
        return None
    if not strip_suffixes:
        return ascii_value
    tokens = ascii_value.split(" ")
    while tokens and tokens[-1] in _NOISY_SUFFIXES:
        tokens.pop()
    normalized = " ".join(tokens).strip()
    return normalized or None


def normalize_compact_registry_key(value: str | None, *, strip_suffixes: bool = True) -> str | None:
    normalized = normalize_registry_key(value, strip_suffixes=strip_suffixes)
    if normalized is None:
        return None
    compact = normalized.replace(" ", "")
    return compact or None


def _freeze_aliases(raw_aliases: dict[str, list[str] | tuple[str, ...]]) -> MappingProxyType[str, tuple[str, ...]]:
    frozen: dict[str, tuple[str, ...]] = {}
    for canonical, aliases in raw_aliases.items():
        canonical_key = normalize_registry_key(canonical)
        if canonical_key is None:
            raise ValueError(f"Canonical alias key {canonical!r} normalized to an empty value.")
        seen: set[str] = set()
        ordered_aliases: list[str] = []
        for alias in aliases:
            alias_key = normalize_registry_key(alias)
            if alias_key is None or alias_key == canonical_key or alias_key in seen:
                continue
            seen.add(alias_key)
            ordered_aliases.append(alias_key)
        frozen[canonical_key] = tuple(ordered_aliases)
    return MappingProxyType(frozen)


def _build_alias_lookup(
    canonical_aliases: MappingProxyType[str, tuple[str, ...]],
    *,
    entity_label: str,
) -> MappingProxyType[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in canonical_aliases.items():
        for alias in (canonical, *aliases):
            existing = lookup.get(alias)
            if existing is not None and existing != canonical:
                raise ValueError(
                    f"Alias collision for {entity_label} alias {alias!r}: {existing!r} vs {canonical!r}."
                )
            lookup[alias] = canonical
    return MappingProxyType(lookup)


def _build_compact_alias_lookup(
    canonical_aliases: MappingProxyType[str, tuple[str, ...]],
    *,
    entity_label: str,
) -> MappingProxyType[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in canonical_aliases.items():
        canonical_compact = normalize_compact_registry_key(canonical, strip_suffixes=False)
        if canonical_compact is None:
            continue
        for alias in (canonical, *aliases):
            alias_compact = normalize_compact_registry_key(alias, strip_suffixes=False)
            if alias_compact is None:
                continue
            existing = lookup.get(alias_compact)
            if existing is not None and existing != canonical_compact:
                raise ValueError(
                    f"Alias collision for {entity_label} alias {alias_compact!r}: {existing!r} vs {canonical_compact!r}."
                )
            lookup[alias_compact] = canonical_compact
    return MappingProxyType(lookup)


def _repair_common_mojibake(value: str) -> str:
    if not any(marker in value for marker in _MOJIBAKE_MARKERS):
        return value
    for encoding in ("cp1252", "latin-1"):
        try:
            repaired = value.encode(encoding).decode("utf-8")
        except UnicodeError:
            continue
        if repaired:
            return repaired
    return value


CLUB_PLACEHOLDER_LABELS = frozenset({"free agent", "unattached"})


CLUB_ALIASES = _freeze_aliases(
    {
        "manchester united": ["man united", "manchester utd", "man utd"],
        "paris saint germain": ["psg", "paris sg"],
        "inter milan": ["internazionale"],
        "tottenham hotspur": ["spurs"],
    }
)


COUNTRY_ALIASES = _freeze_aliases(
    {
        "england": ["eng", "uk", "great britain"],
        "Côte d’Ivoire": ["ivory coast"],
        "usa": ["united states", "us", "america", "united states of america"],
        "Democratic Republic of the Congo": ["dr congo", "congo dr", "congo-kinshasa", "drc"],
        "Republic of the Congo": ["congo", "congo-brazzaville"],
        "Cabo Verde": ["cape verde"],
        "Curaçao": ["curacao"],
        "gambia": ["the gambia"],
        "guinea bissau": ["guinea-bissau"],
    }
)


CLUB_ALIAS_LOOKUP = _build_alias_lookup(CLUB_ALIASES, entity_label="club")
COUNTRY_ALIAS_LOOKUP = _build_alias_lookup(COUNTRY_ALIASES, entity_label="country")
COUNTRY_COMPACT_ALIAS_LOOKUP = _build_compact_alias_lookup(COUNTRY_ALIASES, entity_label="country")


__all__ = [
    "CLUB_ALIASES",
    "CLUB_ALIAS_LOOKUP",
    "CLUB_PLACEHOLDER_LABELS",
    "COUNTRY_ALIASES",
    "COUNTRY_ALIAS_LOOKUP",
    "COUNTRY_COMPACT_ALIAS_LOOKUP",
    "normalize_compact_registry_key",
    "normalize_registry_key",
]
