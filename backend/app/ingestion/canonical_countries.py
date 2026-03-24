from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Country
from app.models.base import utcnow


CANONICAL_COUNTRY_SOURCE_PROVIDER = "gtex_canonical_country_seed"

_APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "\u2019": "'",
        "\u2018": "'",
        "\u02bc": "'",
        "`": "'",
        "\u00b4": "'",
    }
)


@dataclass(frozen=True, slots=True)
class CanonicalCountrySeed:
    provider_external_id: str
    name: str
    alpha2_code: str | None = None
    alpha3_code: str | None = None
    fifa_code: str | None = None
    confederation_code: str | None = None
    market_region: str | None = None


@dataclass(frozen=True, slots=True)
class CanonicalCountrySeedResult:
    inserted_names: tuple[str, ...] = ()
    updated_names: tuple[str, ...] = ()

    @property
    def inserted_count(self) -> int:
        return len(self.inserted_names)

    @property
    def updated_count(self) -> int:
        return len(self.updated_names)

    @property
    def changed(self) -> bool:
        return bool(self.inserted_names or self.updated_names)


CANONICAL_COUNTRY_SEEDS = (
    CanonicalCountrySeed(
        provider_external_id="CIV",
        name="C\u00f4te d\u2019Ivoire",
        alpha2_code="CI",
        alpha3_code="CIV",
        fifa_code="CIV",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="AGO",
        name="Angola",
        alpha2_code="AO",
        alpha3_code="AGO",
        fifa_code="ANG",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="BEN",
        name="Benin",
        alpha2_code="BJ",
        alpha3_code="BEN",
        fifa_code="BEN",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="BFA",
        name="Burkina Faso",
        alpha2_code="BF",
        alpha3_code="BFA",
        fifa_code="BFA",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="CPV",
        name="Cabo Verde",
        alpha2_code="CV",
        alpha3_code="CPV",
        fifa_code="CPV",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="CMR",
        name="Cameroon",
        alpha2_code="CM",
        alpha3_code="CMR",
        fifa_code="CMR",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="CAF",
        name="Central African Republic",
        alpha2_code="CF",
        alpha3_code="CAF",
        fifa_code="CTA",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="COD",
        name="Democratic Republic of the Congo",
        alpha2_code="CD",
        alpha3_code="COD",
        fifa_code="COD",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GNQ",
        name="Equatorial Guinea",
        alpha2_code="GQ",
        alpha3_code="GNQ",
        fifa_code="EQG",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GUF",
        name="French Guiana",
        alpha2_code="GF",
        alpha3_code="GUF",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="GAB",
        name="Gabon",
        alpha2_code="GA",
        alpha3_code="GAB",
        fifa_code="GAB",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GMB",
        name="Gambia",
        alpha2_code="GM",
        alpha3_code="GMB",
        fifa_code="GAM",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="COG",
        name="Republic of the Congo",
        alpha2_code="CG",
        alpha3_code="COG",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="HTI",
        name="Haiti",
        alpha2_code="HT",
        alpha3_code="HTI",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="ZWE",
        name="Zimbabwe",
        alpha2_code="ZW",
        alpha3_code="ZWE",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="MOZ",
        name="Mozambique",
        alpha2_code="MZ",
        alpha3_code="MOZ",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="KEN",
        name="Kenya",
        alpha2_code="KE",
        alpha3_code="KEN",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="TTO",
        name="Trinidad and Tobago",
        alpha2_code="TT",
        alpha3_code="TTO",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="ZMB",
        name="Zambia",
        alpha2_code="ZM",
        alpha3_code="ZMB",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="BONAIRE",
        name="Bonaire",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="BDI",
        name="Burundi",
        alpha2_code="BI",
        alpha3_code="BDI",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GUY",
        name="Guyana",
        alpha2_code="GY",
        alpha3_code="GUY",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="MRT",
        name="Mauritania",
        alpha2_code="MR",
        alpha3_code="MRT",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="PSE",
        name="Palestine",
        alpha2_code="PS",
        alpha3_code="PSE",
        confederation_code="AFC",
        market_region="asia",
    ),
    CanonicalCountrySeed(
        provider_external_id="LBR",
        name="Liberia",
        alpha2_code="LR",
        alpha3_code="LBR",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GRD",
        name="Grenada",
        alpha2_code="GD",
        alpha3_code="GRD",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="TCD",
        name="Chad",
        alpha2_code="TD",
        alpha3_code="TCD",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="CUB",
        name="Cuba",
        alpha2_code="CU",
        alpha3_code="CUB",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="NCL",
        name="New Caledonia",
        alpha2_code="NC",
        alpha3_code="NCL",
        confederation_code="OFC",
        market_region="oceania",
    ),
    CanonicalCountrySeed(
        provider_external_id="RWA",
        name="Rwanda",
        alpha2_code="RW",
        alpha3_code="RWA",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="NER",
        name="Niger",
        alpha2_code="NE",
        alpha3_code="NER",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="MAF",
        name="Saint-Martin",
        alpha2_code="MF",
        alpha3_code="MAF",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="ATG",
        name="Antigua and Barbuda",
        alpha2_code="AG",
        alpha3_code="ATG",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="BEN",
        name="Benin",
        alpha2_code="BJ",
        alpha3_code="BEN",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="BFA",
        name="Burkina Faso",
        alpha2_code="BF",
        alpha3_code="BFA",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="CAF",
        name="Central African Republic",
        alpha2_code="CF",
        alpha3_code="CAF",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GNQ",
        name="Equatorial Guinea",
        alpha2_code="GQ",
        alpha3_code="GNQ",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GUF",
        name="French Guiana",
        alpha2_code="GF",
        alpha3_code="GUF",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="GAB",
        name="Gabon",
        alpha2_code="GA",
        alpha3_code="GAB",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GNB",
        name="Guinea-Bissau",
        alpha2_code="GW",
        alpha3_code="GNB",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="MDG",
        name="Madagascar",
        alpha2_code="MG",
        alpha3_code="MDG",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="MTQ",
        name="Martinique",
        alpha2_code="MQ",
        alpha3_code="MTQ",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="MUS",
        name="Mauritius",
        alpha2_code="MU",
        alpha3_code="MUS",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="STP",
        name="Sao Tome and Principe",
        alpha2_code="ST",
        alpha3_code="STP",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="SLE",
        name="Sierra Leone",
        alpha2_code="SL",
        alpha3_code="SLE",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="SYR",
        name="Syria",
        alpha2_code="SY",
        alpha3_code="SYR",
        confederation_code="AFC",
        market_region="asia",
    ),
    CanonicalCountrySeed(
        provider_external_id="TZA",
        name="Tanzania",
        alpha2_code="TZ",
        alpha3_code="TZA",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="TGO",
        name="Togo",
        alpha2_code="TG",
        alpha3_code="TGO",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="TKM",
        name="Turkmenistan",
        alpha2_code="TM",
        alpha3_code="TKM",
        confederation_code="AFC",
        market_region="asia",
    ),
)


def canonical_country_display_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = unicodedata.normalize("NFKC", value.translate(_APOSTROPHE_TRANSLATION))
    cleaned = " ".join(normalized.split()).strip()
    if not cleaned:
        return None
    return cleaned.casefold()


CANONICAL_COUNTRY_DISPLAY_KEYS = frozenset(
    key
    for key in (canonical_country_display_key(seed.name) for seed in CANONICAL_COUNTRY_SEEDS)
    if key is not None
)


def seed_canonical_countries(session: Session) -> CanonicalCountrySeedResult:
    existing = list(session.scalars(select(Country)))
    countries_by_seed_key = {
        (country.source_provider, country.provider_external_id): country
        for country in existing
    }
    countries_by_display_key: dict[str, list[Country]] = {}
    for country in existing:
        display_key = canonical_country_display_key(country.name)
        if display_key is None:
            continue
        countries_by_display_key.setdefault(display_key, []).append(country)

    inserted_names: list[str] = []
    updated_names: list[str] = []
    for seed in CANONICAL_COUNTRY_SEEDS:
        display_key = canonical_country_display_key(seed.name)
        if display_key is None:
            continue

        seed_key = (CANONICAL_COUNTRY_SOURCE_PROVIDER, seed.provider_external_id)
        country = countries_by_seed_key.get(seed_key)
        exact_canonical_match = countries_by_display_key.get(display_key, ())
        if country is None and exact_canonical_match:
            continue

        inserted = False
        if country is None:
            country = Country(
                source_provider=CANONICAL_COUNTRY_SOURCE_PROVIDER,
                provider_external_id=seed.provider_external_id,
                name=seed.name,
            )
            session.add(country)
            countries_by_seed_key[seed_key] = country
            countries_by_display_key.setdefault(display_key, []).append(country)
            inserted = True
            inserted_names.append(seed.name)

        changed = _apply_seed(country, seed)
        if changed and not inserted:
            updated_names.append(seed.name)

    if inserted_names or updated_names:
        session.flush()

    return CanonicalCountrySeedResult(
        inserted_names=tuple(inserted_names),
        updated_names=tuple(updated_names),
    )


def _apply_seed(country: Country, seed: CanonicalCountrySeed) -> bool:
    changed = False
    for field_name, value in (
        ("source_provider", CANONICAL_COUNTRY_SOURCE_PROVIDER),
        ("provider_external_id", seed.provider_external_id),
        ("name", seed.name),
        ("alpha2_code", seed.alpha2_code),
        ("alpha3_code", seed.alpha3_code),
        ("fifa_code", seed.fifa_code),
        ("confederation_code", seed.confederation_code),
        ("market_region", seed.market_region),
        ("is_enabled_for_universe", True),
    ):
        if getattr(country, field_name) != value:
            setattr(country, field_name, value)
            changed = True
    if changed:
        country.last_synced_at = utcnow()
    return changed


__all__ = [
    "CANONICAL_COUNTRY_DISPLAY_KEYS",
    "CANONICAL_COUNTRY_SEEDS",
    "CANONICAL_COUNTRY_SOURCE_PROVIDER",
    "CanonicalCountrySeed",
    "CanonicalCountrySeedResult",
    "canonical_country_display_key",
    "seed_canonical_countries",
]
