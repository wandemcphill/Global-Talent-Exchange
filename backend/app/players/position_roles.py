"""Football positions as they are actually played.

Stored rows mix four coarse buckets (DF, MF, FW, GK) with Football Manager
strings (D/WB R, AM RLC) and real role names. A coarse bucket loses to a
specific role on the same player, and a named correction wins over both.
"""

from __future__ import annotations

import re
import unicodedata

# Primary code, then the other roles the player can play.
NAMED_POSITIONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "jamal musiala": ("AM", ("LW", "LM", "CM")),
    "jeremy monga": ("LW", ("LM", "ST")),
    # Filed as a wing-back. They play in front of the defence.
    "dominik szoboszlai": ("AM", ("CM", "RW")),
    "kaoru mitoma": ("LW", ("LM",)),
    "yannick carrasco": ("LW", ("LM",)),
    "ivan perisic": ("LW", ("LM", "ST")),
    "leandro trossard": ("LW", ("ST",)),
    "thomas lemar": ("LW", ("AM", "CM")),
    "chris fuhrich": ("LW", ("LM", "AM")),
    "callum hudson-odoi": ("RW", ("LW", "ST")),
    "federico bernardeschi": ("RW", ("AM",)),
    "shaun wright-phillips": ("RW", ()),
    "franco cervi": ("LW", ("LM",)),
    "ander barrenetxea": ("LW", ()),
    "bobby decordova-reid": ("RW", ("ST",)),
    "roberto pereyra": ("AM", ("CM",)),
    "eduardo salvio": ("RW", ()),
    "bernd schneider": ("RM", ("RW",)),
    "torsten frings": ("CM", ("DM",)),
    "amadou onana": ("DM", ("CM",)),
    "cheick doucoure": ("DM", ("CM",)),
    "bernard berisha": ("LW", ("LM",)),
    "federico chiesa": ("RW", ("LW", "ST")),
    "carlos soler": ("CM", ("AM", "RM")),
    "marcos llorente": ("CM", ("RB", "RM")),
    "etienne capoue": ("DM", ("CM",)),
    "valentin rongier": ("CM", ("DM",)),
    "roman zobnin": ("CM", ("DM",)),
    "dominik kohr": ("DM", ("CM",)),
    "tanguy coulibaly": ("RW", ("LW",)),
    "kevin paredes": ("LW", ("LM",)),
    "gustavo varela": ("RW", ("RM",)),
    "giampiero pinzi": ("CM", ("DM",)),
    "bobby convey": ("LW", ("AM",)),
    "kevin zeroli": ("CM", ()),
    "kian fitz-jim": ("CM", ("AM",)),
    "dolev haziza": ("LW", ("LM",)),
    "paul seguin": ("CM", ()),
    "carlo holse": ("LW", ("RW",)),
    "felix correia": ("RW", ("LW",)),
    "przemyslaw frankowski": ("RM", ("RWB", "RW")),
    "ze roberto": ("LW", ("AM", "LM")),
    "bruno fernandes": ("AM", ("CM",)),
    "valon berisha": ("CM", ("AM",)),
    "alessandro murgia": ("CM", ("DM",)),
    "brad potts": ("CM", ("RM",)),
    "estevao willian": ("RW", ("AM", "ST", "RM")),
    "estevao willian almeida de oliveira goncalves": ("RW", ("AM", "ST", "RM")),
    "cole palmer": ("AM", ("RW", "RM", "ST")),
    "cole jermaine palmer": ("AM", ("RW", "RM", "ST")),
    "tunde akinsola": ("RW", ("RM", "AM", "ST", "LM", "LW")),
    "babatunde jimoh akinsola": ("RW", ("RM", "AM", "ST", "LM", "LW")),
    "mauro camoranesi": ("LM", ("LW", "RM", "CM", "AM", "ST")),
    "raul gonzalez": ("ST", ("AM",)),
    "raul gonzalez blanco": ("ST", ("AM",)),
    "max dowman": ("AM", ("RW", "RM", "ST")),
    "max robert dowman": ("AM", ("RW", "RM", "ST")),
    "rio ngumoha": ("LW", ("LM", "ST", "RM", "RW")),
    "rio chima ngumoha": ("LW", ("LM", "ST", "RM", "RW")),
    "trey nyoni": ("CM", ("AM",)),
    "treymaurice nyoni": ("CM", ("AM",)),
    "joshua abe": ("RW", ("RM",)),
    "joshua oluwatobi abe": ("RW", ("RM",)),
    "rivaldo vitor borba ferreira": ("ST", ("RW", "LW", "AM")),
    "adriano leite ribeiro": ("ST", ()),
    "luca williams-barnett": ("LW", ("LM", "AM", "ST")),
    "luca james williams-barnett": ("LW", ("LM", "AM", "ST")),
    "eduardo conceicao": ("LW", ("LM", "ST", "RW", "AM")),
    "eduardo conceicao silva": ("LW", ("LM", "ST", "RW", "AM")),
    "jose lucas gomes da silva": ("DM", ("CM",)),
    "ze lucas": ("DM", ("CM",)),
    "shabani nonda": ("ST", ()),
    "shabani christophe nonda": ("ST", ()),
    "marc bernal": ("DM", ("CM",)),
    "marc bernal casas": ("DM", ("CM",)),
    "mezian mesloub soares": ("LW", ("LM", "AM", "CM")),
    "mezian soares mesloub": ("LW", ("LM", "AM", "CM")),
    "djibril cisse": ("ST", ("RW",)),
    "djibril arrun cisse": ("ST", ("RW",)),
    "jose maria gutierrez": ("DM", ("CM", "AM")),
    "jose maria gutierrez hernandez": ("DM", ("CM", "AM")),
}

_ROLE_LABELS: dict[str, str] = {
    "GK": "Goalkeeper",
    "CB": "Centre-Back",
    "LB": "Left Back",
    "RB": "Right Back",
    "LWB": "Left Wing-Back",
    "RWB": "Right Wing-Back",
    "FB": "Full-Back",
    "DM": "Defensive Midfielder",
    "CM": "Central Midfielder",
    "LM": "Left Midfielder",
    "RM": "Right Midfielder",
    "AM": "Attacking Midfielder",
    "LW": "Left Winger",
    "RW": "Right Winger",
    "ST": "Striker",
}

_DEFENDER = frozenset({"CB", "LB", "RB", "LWB", "RWB", "FB"})
_MIDFIELD = frozenset({"DM", "CM", "LM", "RM", "AM"})
_FORWARD = frozenset({"LW", "RW", "ST"})

_WORDS: dict[str, tuple[str, ...]] = {
    "gk": ("GK",),
    "goalkeeper": ("GK",),
    "goal keeper": ("GK",),
    "keeper": ("GK",),
    "cb": ("CB",),
    "centre-back": ("CB",),
    "center-back": ("CB",),
    "centre back": ("CB",),
    "center back": ("CB",),
    "centreback": ("CB",),
    "centerback": ("CB",),
    "central defender": ("CB",),
    "lb": ("LB",),
    "left back": ("LB",),
    "left-back": ("LB",),
    "rb": ("RB",),
    "right back": ("RB",),
    "right-back": ("RB",),
    "lwb": ("LWB",),
    "left wing-back": ("LWB",),
    "left wing back": ("LWB",),
    "rwb": ("RWB",),
    "right wing-back": ("RWB",),
    "right wing back": ("RWB",),
    "wing-back": ("LWB", "RWB"),
    "wing back": ("LWB", "RWB"),
    "full-back": ("FB",),
    "full back": ("FB",),
    "fullback": ("FB",),
    "dm": ("DM",),
    "cdm": ("DM",),
    "defensive midfielder": ("DM",),
    "cm": ("CM",),
    "centre mid": ("CM",),
    "center mid": ("CM",),
    "lm": ("LM",),
    "left midfielder": ("LM",),
    "left midfield": ("LM",),
    "rm": ("RM",),
    "right midfielder": ("RM",),
    "right midfield": ("RM",),
    "am": ("AM",),
    "cam": ("AM",),
    "attacking midfielder": ("AM",),
    "attacking mid": ("AM",),
    "lw": ("LW",),
    "left winger": ("LW",),
    "left wing": ("LW",),
    "rw": ("RW",),
    "right winger": ("RW",),
    "right wing": ("RW",),
    "winger": ("LW", "RW"),
    "st": ("ST",),
    "cf": ("ST",),
    "striker": ("ST",),
    "centre forward": ("ST",),
    "center forward": ("ST",),
    "centre-forward": ("ST",),
    "center-forward": ("ST",),
}

_COARSE: dict[str, tuple[str, ...]] = {
    "df": ("CB",),
    "def": ("CB",),
    "defender": ("CB",),
    "mf": ("CM",),
    "mid": ("CM",),
    "midfielder": ("CM",),
    "central midfielder": ("CM",),
    "fw": ("ST",),
    "fwd": ("ST",),
    "forward": ("ST",),
}

_FM = re.compile(
    r"^(GK|(?:D|WB|DM|M|AM|ST|F)(?:/(?:D|WB|DM|M|AM|ST|F))*)(?:\s+([RLC]+))?$",
    re.IGNORECASE,
)
# A slash belongs to a Football Manager code such as D/WB L. Do not split it
# into a lone "D", or a left wing-back is filed as a centre-back.
_SPLIT = re.compile(r"[,;|]+")


def person_key(name: str | None) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.lower().split())


def role_label(code: str) -> str:
    return _ROLE_LABELS.get(code, code)


def position_family(raw: str | None) -> str:
    """Four-way line used by squad picking: goalkeeper, defender, midfielder, forward."""
    codes = parse_codes(raw)
    primary = codes[0] if codes else ""
    if primary == "GK" or (raw or "").strip().lower().startswith("goal"):
        return "goalkeeper"
    if primary in _DEFENDER:
        return "defender"
    if primary in _FORWARD:
        return "forward"
    if primary in _MIDFIELD:
        return "midfielder"
    text = (raw or "").strip().lower()
    if not text:
        return "midfielder"
    if "keep" in text or text.startswith("goal"):
        return "goalkeeper"
    if any(
        token in text for token in ("wing-back", "wing back", "full-back", "full back", "centre-back", "center-back")
    ):
        return "defender"
    if "winger" in text or "striker" in text:
        return "forward"
    if "attacking mid" in text or "midfield" in text:
        return "midfielder"
    return "midfielder"


def parse_codes(raw: str | None) -> list[str]:
    codes, _coarse = _parse(raw)
    return codes


def display_codes(primary: str, secondaries: list[str] | tuple[str, ...]) -> str:
    ordered: list[str] = []
    for code in (primary, *secondaries):
        if code and code not in ordered:
            ordered.append(code)
    return " / ".join(ordered)


def resolve_positions(
    *,
    name: str | None,
    position: str | None,
    normalized_position: str | None = None,
    secondaries: list | tuple | None = None,
    profile_primary: str | None = None,
    profile_secondaries: list | tuple | None = None,
    sibling_codes: list[str] | None = None,
) -> tuple[str, list[str], str]:
    """Return (primary code, other codes, reason).

    reason is "unchanged" when the row's own position string is already the
    best evidence, and another token when a correction should be written.
    """
    named = NAMED_POSITIONS.get(person_key(name))
    if named is not None:
        primary, extras = named
        return primary, list(extras), "named"

    own, own_coarse = _merge(position, None, secondaries)
    if not own:
        own, own_coarse = _parse(normalized_position)
    profile, profile_coarse = _merge(profile_primary, None, profile_secondaries)
    sibling = [code for code in (sibling_codes or []) if code]
    norm_codes, norm_coarse = _parse(normalized_position)

    # A specific position string on the wrong line loses to the corrected code.
    # A goalkeeper contradiction is left alone: that is a bad row, not a side error.
    if (
        own
        and not own_coarse
        and norm_codes
        and not norm_coarse
        and _family_code(own[0]) != _family_code(norm_codes[0])
        and own[0] != "GK"
        and norm_codes[0] != "GK"
    ):
        return norm_codes[0], norm_codes[1:], "normalized"

    if own and not own_coarse:
        return own[0], own[1:], "unchanged"
    if profile and not profile_coarse:
        return profile[0], profile[1:], "profile"
    if own_coarse and sibling and _family_code(sibling[0]) != _family_code(own[0] if own else ""):
        return sibling[0], sibling[1:], "sibling"
    if own:
        return own[0], own[1:], "unchanged"
    if profile:
        return profile[0], profile[1:], "profile"
    return "CM", [], "unchanged"


def _merge(primary: str | None, alternate: str | None, extras: list | tuple | None) -> tuple[list[str], bool]:
    codes, coarse = _parse(primary)
    if not codes:
        codes, coarse = _parse(alternate)
    extra_codes: list[str] = []
    for value in extras or []:
        parsed, was_coarse = _parse(str(value))
        if was_coarse:
            continue
        for code in parsed:
            if code not in extra_codes:
                extra_codes.append(code)
    if not codes:
        return extra_codes, not extra_codes
    for code in extra_codes:
        if code not in codes:
            codes.append(code)
    return codes, coarse


def _parse(raw: str | None) -> tuple[list[str], bool]:
    text = " ".join((raw or "").replace("_", " ").replace("-", " ").split())
    if not text:
        return [], True
    lowered = text.lower()
    if lowered in _COARSE:
        return list(_COARSE[lowered]), True
    if lowered in _WORDS:
        return list(_WORDS[lowered]), False

    if " / " in text:
        codes: list[str] = []
        coarse = True
        for part in text.split(" / "):
            parsed, was_coarse = _parse(part.strip())
            coarse = coarse and was_coarse
            for code in parsed:
                if code not in codes:
                    codes.append(code)
        if codes:
            return codes, coarse

    parts = [part.strip() for part in _SPLIT.split(text) if part.strip()]
    if len(parts) > 1:
        codes: list[str] = []
        coarse = True
        for part in parts:
            parsed, was_coarse = _parse(part)
            coarse = coarse and was_coarse
            for code in parsed:
                if code not in codes:
                    codes.append(code)
        if codes:
            return codes, coarse

    fm = _FM.match(text.upper())
    if fm:
        return _expand_fm(fm.group(1).upper(), (fm.group(2) or "").upper()), False

    compact = text.upper()
    if compact in _ROLE_LABELS:
        return [compact], compact in {"CB", "CM", "ST"} and lowered in _COARSE
    return [], True


def _expand_fm(roles: str, sides: str) -> list[str]:
    codes: list[str] = []
    for role in roles.split("/"):
        for code in _expand_role(role, sides):
            if code not in codes:
                codes.append(code)
    return codes


def _expand_role(role: str, sides: str) -> list[str]:
    has_l = "L" in sides
    has_r = "R" in sides
    has_c = "C" in sides or not sides
    if role == "GK":
        return ["GK"]
    if role == "D":
        found: list[str] = []
        if "C" in sides or not sides:
            found.append("CB")
        if has_l:
            found.append("LB")
        if has_r:
            found.append("RB")
        return found or ["CB"]
    if role == "WB":
        found = []
        if has_l or not sides:
            found.append("LWB")
        if has_r:
            found.append("RWB")
        return found
    if role == "DM":
        return ["DM"]
    if role == "M":
        found = []
        if has_c:
            found.append("CM")
        if has_l:
            found.append("LM")
        if has_r:
            found.append("RM")
        return found or ["CM"]
    if role == "AM":
        found = []
        if has_c and "C" in sides:
            found.append("AM")
        if has_l:
            found.append("LW")
        if has_r:
            found.append("RW")
        if not found:
            found.append("AM")
        return found
    if role in {"ST", "F"}:
        return ["ST"]
    return []


def _family_code(code: str) -> str:
    if code == "GK":
        return "goalkeeper"
    if code in _DEFENDER:
        return "defender"
    if code in _FORWARD:
        return "forward"
    return "midfielder"
