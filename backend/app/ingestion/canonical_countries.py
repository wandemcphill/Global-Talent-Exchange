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
        provider_external_id="GLP",
        name="Guadeloupe",
        alpha2_code="GP",
        alpha3_code="GLP",
        fifa_code="GLP",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="GIN",
        name="Guinea",
        alpha2_code="GN",
        alpha3_code="GIN",
        fifa_code="GUI",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="GNB",
        name="Guinea-Bissau",
        alpha2_code="GW",
        alpha3_code="GNB",
        fifa_code="GNB",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="MDG",
        name="Madagascar",
        alpha2_code="MG",
        alpha3_code="MDG",
        fifa_code="MAD",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="MLI",
        name="Mali",
        alpha2_code="ML",
        alpha3_code="MLI",
        fifa_code="MLI",
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
        fifa_code="MRI",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="COG",
        name="Republic of the Congo",
        alpha2_code="CG",
        alpha3_code="COG",
        fifa_code="CGO",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="SLE",
        name="Sierra Leone",
        alpha2_code="SL",
        alpha3_code="SLE",
        fifa_code="SLE",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="SYR",
        name="Syria",
        alpha2_code="SY",
        alpha3_code="SYR",
        fifa_code="SYR",
        confederation_code="AFC",
        market_region="asia",
    ),
    CanonicalCountrySeed(
        provider_external_id="SUR",
        name="Suriname",
        alpha2_code="SR",
        alpha3_code="SUR",
        fifa_code="SUR",
        confederation_code="CONCACAF",
        market_region="americas",
    ),
    CanonicalCountrySeed(
        provider_external_id="TZA",
        name="Tanzania",
        alpha2_code="TZ",
        alpha3_code="TZA",
        fifa_code="TAN",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="TGO",
        name="Togo",
        alpha2_code="TG",
        alpha3_code="TGO",
        fifa_code="TOG",
        confederation_code="CAF",
        market_region="africa",
    ),
    CanonicalCountrySeed(
        provider_external_id="CUW",
        name="Cura\u00e7ao",
        alpha2_code="CW",
        alpha3_code="CUW",
        fifa_code="CUW",
        confederation_code="CONCACAF",
        market_region="americas",
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
