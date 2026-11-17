from __future__ import annotations

_GENERIC_CLUB_WORDS = frozenset({"FC", "CF", "SC", "AC", "AFC"})


def club_initials(club_name: str) -> str:
    """Three-letter crest code for every club name."""
    words = []
    for raw in club_name.replace("-", " ").upper().split():
        token = "".join(character for character in raw if character.isalnum())
        if token:
            words.append(token)
    if not words:
        return "FCL"
    if len(words) >= 3:
        code = "".join(word[0] for word in words[:3])
    elif len(words) == 2:
        first, second = words
        if first in _GENERIC_CLUB_WORDS or second in _GENERIC_CLUB_WORDS:
            code = (first + second)[:3]
        else:
            code = (first[0] + second)[:3]
    else:
        code = words[0][:3]
    return (code + "FCX")[:3]
