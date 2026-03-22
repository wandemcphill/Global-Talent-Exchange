from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


@dataclass(frozen=True, slots=True)
class NormalizedIdentityName:
    normalized: str
    compact: str
    tokens: tuple[str, ...]
    token_signature: str

    @property
    def first_token(self) -> str:
        return self.tokens[0] if self.tokens else ""


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
    return False


__all__ = [
    "NormalizedIdentityName",
    "fold_identity_name",
    "names_equivalent",
    "normalize_identity_name",
]
