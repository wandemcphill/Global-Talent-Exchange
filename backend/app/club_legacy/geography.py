"""Country codes to continents. Unknown countries stay unset."""

from __future__ import annotations

_AFRICA = {
    "AO",
    "BF",
    "BI",
    "BJ",
    "BW",
    "CD",
    "CF",
    "CG",
    "CI",
    "CM",
    "CV",
    "DJ",
    "DZ",
    "EG",
    "ER",
    "ET",
    "GA",
    "GH",
    "GM",
    "GN",
    "GQ",
    "GW",
    "KE",
    "KM",
    "LR",
    "LS",
    "LY",
    "MA",
    "MG",
    "ML",
    "MR",
    "MU",
    "MW",
    "MZ",
    "NA",
    "NE",
    "NG",
    "RW",
    "SC",
    "SD",
    "SL",
    "SN",
    "SO",
    "SS",
    "ST",
    "SZ",
    "TD",
    "TG",
    "TN",
    "TZ",
    "UG",
    "ZA",
    "ZM",
    "ZW",
}
_EUROPE = {
    "AL",
    "AT",
    "BA",
    "BE",
    "BG",
    "BY",
    "CH",
    "CY",
    "CZ",
    "DE",
    "DK",
    "EE",
    "ES",
    "FI",
    "FR",
    "GB",
    "GR",
    "HR",
    "HU",
    "IE",
    "IS",
    "IT",
    "LT",
    "LU",
    "LV",
    "MD",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "SE",
    "SI",
    "SK",
    "UA",
}
_NORTH_AMERICA = {
    "AG",
    "BB",
    "BS",
    "BZ",
    "CA",
    "CR",
    "CU",
    "DM",
    "DO",
    "GD",
    "GT",
    "HN",
    "HT",
    "JM",
    "MX",
    "NI",
    "PA",
    "SV",
    "TT",
    "US",
}
_SOUTH_AMERICA = {"AR", "BO", "BR", "CL", "CO", "EC", "GY", "PE", "PY", "SR", "UY", "VE"}
_ASIA = {
    "AE",
    "AF",
    "AM",
    "AZ",
    "BD",
    "BH",
    "BN",
    "BT",
    "CN",
    "GE",
    "ID",
    "IL",
    "IN",
    "IQ",
    "IR",
    "JO",
    "JP",
    "KG",
    "KH",
    "KP",
    "KR",
    "KW",
    "KZ",
    "LA",
    "LB",
    "LK",
    "MM",
    "MN",
    "MY",
    "NP",
    "OM",
    "PH",
    "PK",
    "QA",
    "SA",
    "SG",
    "SY",
    "TH",
    "TJ",
    "TM",
    "TR",
    "TW",
    "UZ",
    "VN",
    "YE",
}
_OCEANIA = {"AU", "FJ", "NZ", "PG", "WS"}
_ANTARCTICA = {"AQ"}

_CONTINENTS: tuple[tuple[str, frozenset[str]], ...] = (
    ("AF", frozenset(_AFRICA)),
    ("EU", frozenset(_EUROPE)),
    ("NA", frozenset(_NORTH_AMERICA)),
    ("SA", frozenset(_SOUTH_AMERICA)),
    ("AS", frozenset(_ASIA)),
    ("OC", frozenset(_OCEANIA)),
    ("AN", frozenset(_ANTARCTICA)),
)

CONTINENT_NAMES = {
    "AF": "Africa",
    "EU": "Europe",
    "NA": "North America",
    "SA": "South America",
    "AS": "Asia",
    "OC": "Oceania",
    "AN": "Antarctica",
}


def continent_for_country(country_code: str | None) -> str | None:
    code = (country_code or "").strip().upper()
    if not code:
        return None
    for continent, members in _CONTINENTS:
        if code in members:
            return continent
    return None


def backfill_missing_continents(session) -> int:
    """Fill continent_code from country_code. Clubs with an unknown country stay null."""
    from sqlalchemy import select

    from app.models.club_profile import ClubProfile

    updated = 0
    clubs = session.scalars(select(ClubProfile).where(ClubProfile.continent_code.is_(None))).all()
    for club in clubs:
        continent = continent_for_country(club.country_code)
        if continent:
            club.continent_code = continent
            updated += 1
    return updated


def continent_name(continent_code: str | None) -> str | None:
    if not continent_code:
        return None
    return CONTINENT_NAMES.get(continent_code.strip().upper())
