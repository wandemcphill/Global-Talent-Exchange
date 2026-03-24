from __future__ import annotations

from types import MappingProxyType
import re
import unicodedata


_WHITESPACE_RE = re.compile(r"\s+")
_PUNCTUATION_RE = re.compile(r"[^0-9a-z\s]+")
_NOISY_SUFFIXES = ("fc", "cf", "sc", "afc", "u19", "u21", "b", "ii")


def normalize_registry_key(value: str | None, *, strip_suffixes: bool = True) -> str | None:
    if value is None:
        return None
    ascii_value = (
        unicodedata.normalize("NFKD", value)
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
        "cote divoire": ["ivory coast", "cote d'ivoire", "cote divoire"],
        "usa": ["united states", "us", "america", "united states of america"],
        "dr congo": ["democratic republic of the congo", "congo dr", "drc"],
        "cape verde": ["cabo verde"],
        "curacao": ["curacao"],
        "gambia": ["the gambia"],
        "guinea bissau": ["guinea-bissau"],
    }
)


CLUB_ALIAS_LOOKUP = _build_alias_lookup(CLUB_ALIASES, entity_label="club")
COUNTRY_ALIAS_LOOKUP = _build_alias_lookup(COUNTRY_ALIASES, entity_label="country")


__all__ = [
    "CLUB_ALIASES",
    "CLUB_ALIAS_LOOKUP",
    "CLUB_PLACEHOLDER_LABELS",
    "COUNTRY_ALIASES",
    "COUNTRY_ALIAS_LOOKUP",
    "normalize_registry_key",
]
