from __future__ import annotations

"""One-time SoFIFA / EA FC player-database importer.

Reads a downloaded SoFIFA (EA Sports FC) CSV snapshot and feeds it through the
existing :class:`RealPlayerIngestionService`, exactly like
``refresh_target_league_real_players.py`` does for SportMonks -- but the payloads
come from a frozen CSV instead of a live provider. This is the "PES-style" static
ingest: run it once, then the app reads its own database with no subscription.

Design decisions (see the GTEX plan discussion):

* The market value in the CSV (SoFIFA ``value_eur``) is **not** used as the in-app
  price. Instead we derive an authoritative reference value from ``overall`` via a
  GSI tier curve (:data:`GSI_TIERS`). That guarantees the value engine produces a
  pricing snapshot (otherwise the batch write is blocked) *and* gives the tiered
  pricing the design calls for (a whole "class" of players costs the same at launch;
  live trading diverges them later).
* Player faces are EA/SoFIFA licensed assets. With ``--images cloudinary`` we mirror
  them to your Cloudinary account (public ``type=upload``) so the app loads fast and
  does not hotlink SoFIFA. Each image row is still stored with ``rights_cleared=False``
  by the ingestion service, so the app can fall back to stylized avatars with a single
  switch before any public launch. ``--images url`` keeps the raw SoFIFA URL;
  ``--images none`` drops images entirely (avatars only).

Usage::

    python -m scripts.import_sofifa_players \
        --csv /path/to/players_fc25.csv \
        --database-url "$GTE_DATABASE_URL" \
        --images cloudinary

    # dry-run a single league, 50 players, no DB writes:
    python -m scripts.import_sofifa_players --csv players.csv --league "Premier League" \
        --limit 50 --dry-run
"""

import argparse
import csv
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import httpx

from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.ingestion.real_player_ingestion_service import (
    RealPlayerBatchBlockedError,
    RealPlayerIngestionService,
)
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest, RealPlayerSeedInput
from scripts.sofifa_pricing import compute_price_credits, credits_to_naira

logger = logging.getLogger("import_sofifa_players")

SOURCE_NAME = "sofifa_fc25"
_FALLBACK_AUTH_SECRET = "local-dev-import-secret"
_FALLBACK_MEDIA_SECRET = "local-dev-import-media-secret"
_CLOUDINARY_FOLDER = "players/sofifa"
_UPLOAD_TIMEOUT_SECONDS = 30.0


# --------------------------------------------------------------------------- #
# GSI tier curve: overall rating -> (tier label, authoritative reference value  #
# in EUR). Values are deliberately flat within a tier so a whole "class" of     #
# players costs the same at launch; the value engine converts EUR -> credits    #
# and the liquidity band assigns the tradable price. Tune freely.               #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class GsiTier:
    code: str
    min_overall: int
    reference_value_eur: float


GSI_TIERS: tuple[GsiTier, ...] = (
    GsiTier("world_class", 88, 120_000_000.0),   # Mbappe / Bellingham / Yamal class
    GsiTier("top_class", 84, 60_000_000.0),      # Osimhen class
    GsiTier("quality", 80, 28_000_000.0),
    GsiTier("solid", 75, 12_000_000.0),
    GsiTier("squad", 70, 4_000_000.0),
    GsiTier("prospect", 0, 1_000_000.0),
)


def resolve_tier(overall: int | None) -> GsiTier:
    value = overall if overall is not None else 0
    for tier in GSI_TIERS:
        if value >= tier.min_overall:
            return tier
    return GSI_TIERS[-1]


# --------------------------------------------------------------------------- #
# Flexible column resolution. Different SoFIFA/EA FC CSV exports use slightly    #
# different headers; map each logical field to the first header that exists.     #
# --------------------------------------------------------------------------- #
_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "player_id": ("player_id", "sofifa_id", "id", "fifa_id"),
    "full_name": ("full_name", "long_name"),
    "name": ("name", "player_name", "short_name", "known_as", "common_name"),
    "short_name": ("short_name", "known_as", "common_name"),
    "positions": ("player_positions", "positions", "position", "best_position"),
    "overall": ("overall", "overall_rating", "ovr", "rating"),
    "potential": ("potential", "pot"),
    "club_rating": ("club_rating", "club_overall", "team_rating"),
    "value_eur": ("value_eur", "value", "market_value", "value_euro"),
    "dob": ("dob", "date_of_birth", "birth_date", "birthday"),
    "age": ("age",),
    "height_cm": ("height_cm", "height", "height_cm_"),
    "weight_kg": ("weight_kg", "weight"),
    "club": ("club_name", "club", "club_team", "team_name", "team"),
    "league": ("league_name", "league", "club_league_name", "competition"),
    "nationality": ("nationality_name", "nationality", "nation"),
    "national_team_country": ("country_name",),
    "description": ("description", "bio"),
    "nationality_code": ("nationality_code", "nation_code", "country_code"),
    "preferred_foot": ("preferred_foot", "foot"),
    "jersey": ("club_jersey_number", "jersey_number", "shirt_number", "kit_number"),
    "photo": ("player_face_url", "player_face", "face_url", "image", "image_url", "photo_url", "url"),
    "national_team": ("nation_team_name", "national_team", "nation_name"),
    "national_team_position": ("nation_position", "national_team_position"),
    "national_team_jersey": ("nation_jersey_number", "national_team_jersey"),
}


class ColumnMap:
    def __init__(self, header: Iterable[str]) -> None:
        self._lookup = {col.strip().lower(): col for col in header}
        self._resolved: dict[str, str | None] = {}
        for logical, aliases in _COLUMN_ALIASES.items():
            self._resolved[logical] = next(
                (self._lookup[alias] for alias in aliases if alias in self._lookup), None
            )

    def get(self, row: dict[str, Any], logical: str) -> str | None:
        column = self._resolved.get(logical)
        if column is None:
            return None
        value = row.get(column)
        if value is None:
            return None
        cleaned = str(value).strip()
        return cleaned or None

    def require(self, logical: str) -> None:
        if self._resolved.get(logical) is None:
            raise SystemExit(
                f"CSV is missing a required column for '{logical}'. "
                f"Expected one of: {', '.join(_COLUMN_ALIASES[logical])}"
            )


# --------------------------------------------------------------------------- #
# Cloudinary public upload (mirrors app/core/cloudinary_upload.py signing, but   #
# type=upload for publicly reachable player faces).                              #
# --------------------------------------------------------------------------- #
def cloudinary_configured() -> bool:
    return bool(
        os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
        and os.environ.get("CLOUDINARY_API_KEY", "").strip()
        and os.environ.get("CLOUDINARY_API_SECRET", "").strip()
    )


def _sign(params: dict[str, str], api_secret: str) -> str:
    to_sign = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{to_sign}{api_secret}".encode()).hexdigest()


def upload_remote_image_to_cloudinary(source_url: str, *, public_id: str, client: httpx.Client) -> str | None:
    """Fetch a remote face image and re-upload it to Cloudinary. Returns the secure URL."""
    cloud_name = os.environ["CLOUDINARY_CLOUD_NAME"].strip()
    api_key = os.environ["CLOUDINARY_API_KEY"].strip()
    api_secret = os.environ["CLOUDINARY_API_SECRET"].strip()
    timestamp = str(int(time.time()))
    signed_params = {
        "folder": _CLOUDINARY_FOLDER,
        "public_id": public_id,
        "overwrite": "false",
        "timestamp": timestamp,
    }
    # Cloudinary can fetch the remote URL itself (no need to download bytes locally).
    data = {
        **signed_params,
        "file": source_url,
        "api_key": api_key,
        "signature": _sign(signed_params, api_secret),
    }
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/image/upload"
    try:
        response = client.post(url, data=data, timeout=_UPLOAD_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        logger.warning("cloudinary upload failed public_id=%s error=%s", public_id, exc)
        return None
    if response.status_code >= 400:
        logger.warning(
            "cloudinary rejected upload public_id=%s status=%s body=%s",
            public_id,
            response.status_code,
            response.text[:180],
        )
        return None
    payload = response.json()
    return payload.get("secure_url") or payload.get("url")


# --------------------------------------------------------------------------- #
# Row -> payload                                                                #
# --------------------------------------------------------------------------- #
def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _parse_dob(value: str | None, age: int | None, as_of: datetime) -> tuple[date | None, int | None]:
    """Return (date_of_birth, age). Prefer an explicit DOB; else keep age only."""
    if value:
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date(), age
            except ValueError:
                continue
    return None, age


# --------------------------------------------------------------------------- #
# Nationality extraction. This SoFIFA export's `country_name` column is the      #
# national-TEAM squad (filled for only ~4% of players), NOT birth nationality.   #
# Birth nationality is in the free-text `description`, e.g.                       #
#   "Rodri (born ...) is a Spanish footballer who plays ... for Manchester City" #
# We parse it via (1) explicit national-team phrase, (2) "from <Country>",       #
# (3) demonym + map. Order = highest confidence first.                           #
# --------------------------------------------------------------------------- #
_NATIONAL_TEAM_RE = re.compile(r"the ([A-Z][A-Za-z .'-]+?) national team")
_FROM_COUNTRY_RE = re.compile(r"(?:footballer|soccer player|player) from ([A-Z][A-Za-z .'-]+?)(?: \(country\))?[‎\s]* who")
_DEMONYM_RE = re.compile(r"\bis an? ([A-Z][A-Za-zÀ-ÿ]+(?:[- ][A-Z]?[A-Za-zÀ-ÿ]+)?) (?:footballer|soccer player)")

# Demonym -> country name. Covers the footballing world; extend as needed.
_DEMONYM_TO_COUNTRY: dict[str, str] = {
    # SoFIFA describes English players as "British" (Scots/Welsh/NI get their own demonym),
    # so British -> England is the correct majority mapping for this dataset.
    "British": "England",
    "English": "England", "Scottish": "Scotland", "Welsh": "Wales", "Northern Irish": "Northern Ireland",
    "Irish": "Ireland", "French": "France", "Spanish": "Spain", "Italian": "Italy", "German": "Germany",
    "Portuguese": "Portugal", "Dutch": "Netherlands", "Belgian": "Belgium", "Brazilian": "Brazil",
    "Argentine": "Argentina", "Argentinian": "Argentina", "Uruguayan": "Uruguay", "Chilean": "Chile",
    "Colombian": "Colombia", "Peruvian": "Peru", "Ecuadorian": "Ecuador", "Paraguayan": "Paraguay",
    "Bolivian": "Bolivia", "Venezuelan": "Venezuela", "Mexican": "Mexico", "American": "United States",
    "Canadian": "Canada", "Costa Rican": "Costa Rica", "Honduran": "Honduras", "Panamanian": "Panama",
    "Jamaican": "Jamaica", "Croatian": "Croatia", "Serbian": "Serbia", "Slovenian": "Slovenia",
    "Slovak": "Slovakia", "Czech": "Czech Republic", "Polish": "Poland", "Hungarian": "Hungary",
    "Austrian": "Austria", "Swiss": "Switzerland", "Danish": "Denmark", "Swedish": "Sweden",
    "Norwegian": "Norway", "Finnish": "Finland", "Icelandic": "Iceland", "Russian": "Russia",
    "Ukrainian": "Ukraine", "Romanian": "Romania", "Bulgarian": "Bulgaria", "Greek": "Greece",
    "Turkish": "Turkey", "Bosnian": "Bosnia and Herzegovina", "Montenegrin": "Montenegro",
    "Macedonian": "North Macedonia", "Albanian": "Albania", "Kosovar": "Kosovo", "Georgian": "Georgia",
    "Armenian": "Armenia", "Azerbaijani": "Azerbaijan", "Israeli": "Israel", "Nigerian": "Nigeria",
    "Ghanaian": "Ghana", "Ivorian": "Ivory Coast", "Senegalese": "Senegal", "Cameroonian": "Cameroon",
    "Malian": "Mali", "Egyptian": "Egypt", "Moroccan": "Morocco", "Algerian": "Algeria", "Tunisian": "Tunisia",
    "South African": "South Africa", "Kenyan": "Kenya", "Zimbabwean": "Zimbabwe", "Zambian": "Zambia",
    "Congolese": "DR Congo", "Guinean": "Guinea", "Gabonese": "Gabon", "Burkinabè": "Burkina Faso",
    "Burkinabé": "Burkina Faso", "Burkinabe": "Burkina Faso", "Togolese": "Togo", "Angolan": "Angola", "Ugandan": "Uganda",
    "Liberian": "Liberia", "Sierra Leonean": "Sierra Leone", "Gambian": "Gambia", "Mozambican": "Mozambique",
    "Cape Verdean": "Cape Verde", "Japanese": "Japan", "South Korean": "South Korea", "Korean": "South Korea",
    "Chinese": "China", "Australian": "Australia", "Iranian": "Iran", "Iraqi": "Iraq", "Saudi": "Saudi Arabia",
    "Qatari": "Qatar", "Emirati": "United Arab Emirates", "Uzbek": "Uzbekistan", "Thai": "Thailand",
    "Indonesian": "Indonesia", "Indian": "India", "New Zealand": "New Zealand", "Jordanian": "Jordan",
    "Lebanese": "Lebanon", "Syrian": "Syria", "Palestinian": "Palestine", "Cypriot": "Cyprus",
    "Luxembourgish": "Luxembourg", "Maltese": "Malta", "Estonian": "Estonia", "Latvian": "Latvia",
    "Lithuanian": "Lithuania", "Belarusian": "Belarus", "Moldovan": "Moldova", "Curaçaoan": "Curaçao",
    "Surinamese": "Suriname", "Haitian": "Haiti", "Trinidadian": "Trinidad and Tobago", "Grenadian": "Grenada",
    "Comorian": "Comoros", "Beninese": "Benin", "Nigerien": "Niger", "Chadian": "Chad", "Namibian": "Namibia",
    "Botswanan": "Botswana", "Malagasy": "Madagascar", "Mauritanian": "Mauritania", "Rwandan": "Rwanda",
    "Burundian": "Burundi", "Tanzanian": "Tanzania", "Sudanese": "Sudan",
    # Variant spellings / less-common nations seen in this dataset's descriptions.
    "Saudi Arabian": "Saudi Arabia", "Ukranian": "Ukraine", "Kosovan": "Kosovo",
    "Bissau-Guinean": "Guinea-Bissau", "Luxembourgian": "Luxembourg", "Curaçao": "Curaçao",
    "Equatoguinean": "Equatorial Guinea", "Guyanese": "Guyana", "Uzbekistani": "Uzbekistan",
    "Filipino": "Philippines", "Saint Lucian": "Saint Lucia", "New Zealander": "New Zealand",
    "Faroese": "Faroe Islands", "Montserratian": "Montserrat", "Bermudian": "Bermuda",
    "Antiguan": "Antigua and Barbuda", "Barbadian": "Barbados", "Vincentian": "Saint Vincent and the Grenadines",
    "Malawian": "Malawi", "Lesotho": "Lesotho", "Swazi": "Eswatini", "Djiboutian": "Djibouti",
    "Somali": "Somalia", "Eritrean": "Eritrea", "Ethiopian": "Ethiopia", "Kazakh": "Kazakhstan",
    "Kyrgyz": "Kyrgyzstan", "Tajik": "Tajikistan", "Turkmen": "Turkmenistan", "Vietnamese": "Vietnam",
    "Malaysian": "Malaysia", "Singaporean": "Singapore", "Bahraini": "Bahrain", "Kuwaiti": "Kuwait",
    "Omani": "Oman", "Yemeni": "Yemen", "Afghan": "Afghanistan", "Nepalese": "Nepal", "Pakistani": "Pakistan",
    "Bangladeshi": "Bangladesh", "Sri Lankan": "Sri Lanka", "Cuban": "Cuba", "Dominican": "Dominican Republic",
    "Guatemalan": "Guatemala", "Salvadoran": "El Salvador", "Nicaraguan": "Nicaragua", "Belizean": "Belize",
}


def nationality_from_description(description: str | None) -> str | None:
    if not description:
        return None
    text = description.replace("\xa0", " ").replace("‎", "")
    match = _NATIONAL_TEAM_RE.search(text)
    if match:
        return match.group(1).strip()
    match = _FROM_COUNTRY_RE.search(text)
    if match:
        return match.group(1).strip()
    match = _DEMONYM_RE.search(text)
    if match:
        demonym = match.group(1).strip()
        return _DEMONYM_TO_COUNTRY.get(demonym)
    return None


def _clean_name(value: str | None) -> str | None:
    """Strip stray scraper artifacts: NBSP, replacement chars, trailing ' -' separators."""
    if not value:
        return None
    cleaned = value.replace("\xa0", " ").replace("�", "").strip()
    while cleaned.endswith("-") or cleaned.endswith("."):
        cleaned = cleaned[:-1].strip()
    cleaned = " ".join(cleaned.split())
    return cleaned or None


def _split_positions(raw: str | None) -> tuple[str | None, list[str]]:
    if not raw:
        return None, []
    parts = [part.strip() for part in raw.replace("|", ",").split(",") if part.strip()]
    if not parts:
        return None, []
    return parts[0], parts[1:]


def _normalize_height_cm(value: Any) -> int | None:
    parsed = _parse_int(value)
    if parsed is None:
        return None
    return parsed if 100 <= parsed <= 250 else None


def _normalize_weight_kg(value: Any) -> int | None:
    parsed = _parse_int(value)
    if parsed is None:
        return None
    return parsed if 40 <= parsed <= 150 else None


def build_payload(
    row: dict[str, Any],
    columns: ColumnMap,
    *,
    as_of: datetime,
    photo_url: str | None,
    now_iso: str,
) -> dict[str, Any] | None:
    player_id = columns.get(row, "player_id")
    short_name = _clean_name(columns.get(row, "name"))
    full_name = _clean_name(columns.get(row, "full_name"))
    canonical = full_name or short_name
    display = short_name or full_name
    if not player_id or not canonical:
        return None
    name = canonical

    overall = _parse_int(columns.get(row, "overall"))
    tier = resolve_tier(overall)
    primary_position, secondary_positions = _split_positions(columns.get(row, "positions"))
    dob, age = _parse_dob(columns.get(row, "dob"), _parse_int(columns.get(row, "age")), as_of)
    # `national_team_country` (SoFIFA country_name) is the national-team squad, filled for
    # only ~4% of players. Use it when present (highest confidence), else parse birth
    # nationality out of the free-text description.
    national_team = columns.get(row, "national_team") or columns.get(row, "national_team_country")
    nationality = (
        columns.get(row, "nationality")
        or columns.get(row, "national_team_country")
        or nationality_from_description(columns.get(row, "description"))
    )

    return {
        "source_name": SOURCE_NAME,
        "source_player_key": player_id,
        "canonical_name": canonical,
        "display_name": display,
        "nationality": nationality,
        "nationality_code": columns.get(row, "nationality_code"),
        "national_team_name": national_team,
        "date_of_birth": dob.isoformat() if dob else None,
        "age": age,
        "dominant_foot": (columns.get(row, "preferred_foot") or "").lower() or None,
        "overall_rating": _parse_int(columns.get(row, "overall")),
        "potential": _parse_int(columns.get(row, "potential")),
        "club_rating": _parse_int(columns.get(row, "club_rating")),
        "primary_position": primary_position,
        "secondary_positions": secondary_positions,
        "current_real_world_club": columns.get(row, "club"),
        "current_real_world_club_key": columns.get(row, "club"),
        "current_real_world_league": columns.get(row, "league"),
        "current_real_world_league_key": columns.get(row, "league"),
        "competition_level": tier.code,
        "height_cm": _normalize_height_cm(columns.get(row, "height_cm")),
        "weight_kg": _normalize_weight_kg(columns.get(row, "weight_kg")),
        # Authoritative reference value derived from GSI tier -> guarantees pricing
        # and produces the tiered "a whole class costs the same" launch pricing.
        "current_market_reference_value": tier.reference_value_eur,
        "market_reference_currency": "EUR",
        "real_player_tier": tier.code,
        "photo_url": photo_url,
        "source_last_refreshed_at": now_iso,
    }


# --------------------------------------------------------------------------- #
# CSV reading + grouping                                                         #
# --------------------------------------------------------------------------- #
def detect_encoding(csv_path: Path) -> str:
    """SoFIFA scraper exports are often cp1252 (accented names, € sign). Try strict
    UTF-8 first; fall back to cp1252 if the file isn't valid UTF-8."""
    sample = csv_path.read_bytes()[:200_000]
    try:
        sample.decode("utf-8")
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "cp1252"


def read_rows(
    csv_path: Path,
    columns_out: list[ColumnMap],
    league_filter: set[str] | None,
    limit: int | None,
    encoding: str,
):
    with csv_path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise SystemExit("CSV has no header row.")
        columns = ColumnMap(reader.fieldnames)
        for logical in ("player_id", "name", "overall"):
            columns.require(logical)
        columns_out.append(columns)
        emitted = 0
        for row in reader:
            if league_filter is not None:
                league = (columns.get(row, "league") or "").strip().lower()
                if league not in league_filter:
                    continue
            yield row, columns
            emitted += 1
            if limit is not None and emitted >= limit:
                return


def preseed_competitions(session_factory, payloads: list[dict[str, Any]]) -> dict[str, int]:
    """Create a Competition per league with a country, so clubs can auto-create.

    The ingestion service only auto-creates a club when its competition has a
    country (`_club_auto_create_is_safe`); but it resolves competitions with
    country=None, so on a fresh DB every club is skipped. We pre-seed each league's
    competition with its modal player nationality as the country, keyed by the same
    provider id the player payloads use, so the service binds to it.
    """
    from collections import Counter, defaultdict

    from sqlalchemy import func, select

    from app.ingestion.models import Competition, Country

    modal: dict[str, str] = {}
    counts: dict[str, Counter] = defaultdict(Counter)
    for p in payloads:
        league = (p.get("current_real_world_league") or "").strip()
        nat = (p.get("nationality") or "").strip()
        if league and nat:
            counts[league][nat] += 1
    for league, c in counts.items():
        modal[league] = c.most_common(1)[0][0]

    leagues = sorted({(p.get("current_real_world_league") or "").strip() for p in payloads if (p.get("current_real_world_league") or "").strip()})
    result = {"competitions": 0, "countries_created": 0}
    with session_factory() as session:
        country_cache: dict[str, str] = {}
        for league in leagues:
            country_name = modal.get(league)
            country_id: str | None = None
            if country_name:
                key = country_name.casefold()
                if key in country_cache:
                    country_id = country_cache[key]
                else:
                    country = session.scalar(select(Country).where(func.lower(Country.name) == key))
                    if country is None:
                        country = Country(
                            source_provider=SOURCE_NAME,
                            provider_external_id=country_name,
                            name=country_name,
                        )
                        session.add(country)
                        session.flush()
                        result["countries_created"] += 1
                    country_id = country.id
                    country_cache[key] = country_id
            comp = session.scalar(
                select(Competition).where(
                    Competition.source_provider == SOURCE_NAME,
                    Competition.provider_external_id == league,
                )
            )
            if comp is None:
                comp = Competition(
                    source_provider=SOURCE_NAME,
                    provider_external_id=league,
                    name=league,
                    slug=league.lower().replace(" ", "-")[:180],
                    competition_type="league",
                    country_id=country_id,
                )
                session.add(comp)
                result["competitions"] += 1
            else:
                comp.country_id = country_id or comp.country_id
        session.commit()
    return result


def group_by_club(payloads: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for payload in payloads:
        club = payload.get("current_real_world_club") or "__unknown__"
        groups.setdefault(str(club), []).append(payload)
    return groups


# --------------------------------------------------------------------------- #
# CLI                                                                           #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import a SoFIFA / EA FC player CSV into GTEX (one-time freeze).")
    parser.add_argument("--csv", default=None, help="Path to the SoFIFA/EA FC players CSV.")
    parser.add_argument(
        "--csv-url",
        default=os.environ.get("CSV_URL"),
        help="URL to download the CSV from (used when --csv is not a local file, e.g. on Render). Defaults to $CSV_URL.",
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument(
        "--images",
        choices=("none", "url", "cloudinary"),
        default="cloudinary",
        help="Image handling: 'cloudinary' mirrors faces to your account, 'url' keeps SoFIFA URLs, 'none' drops them.",
    )
    parser.add_argument("--league", dest="leagues", action="append", default=None, help="Filter to league name(s). Repeatable.")
    parser.add_argument("--limit", type=int, default=None, help="Only import the first N rows (after league filter).")
    parser.add_argument(
        "--encoding",
        default="auto",
        help="CSV encoding. 'auto' tries UTF-8 then falls back to cp1252 (typical for SoFIFA exports).",
    )
    parser.add_argument("--dry-run", action="store_true", help="Parse and report, but do not write to the DB.")
    parser.add_argument(
        "--report-path",
        default=str((REPO_ROOT / "tmp" / "sofifa-import-report.json").resolve()),
        help="Path for the JSON execution report.",
    )
    return parser


def _ensure_required_secrets() -> None:
    os.environ.setdefault("GTE_AUTH_SECRET", _FALLBACK_AUTH_SECRET)
    os.environ.setdefault("GTE_MEDIA_SIGNING_SECRET", _FALLBACK_MEDIA_SECRET)


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if args.csv:
        csv_path = Path(args.csv).expanduser().resolve()
    elif args.csv_url:
        csv_path = REPO_ROOT / "tmp" / "sofifa-download.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("downloading CSV from %s", args.csv_url)
        with httpx.stream("GET", args.csv_url, timeout=120.0, follow_redirects=True) as resp:
            resp.raise_for_status()
            with csv_path.open("wb") as fh:
                for chunk in resp.iter_bytes():
                    fh.write(chunk)
        logger.info("downloaded CSV to %s (%s bytes)", csv_path, csv_path.stat().st_size)
    else:
        raise SystemExit("Provide --csv <path> or --csv-url <url> (or $CSV_URL).")
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")
    if not args.dry_run and not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required (or use --dry-run).")

    _ensure_required_secrets()
    os.environ.setdefault("GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES", "1")

    as_of = datetime.now(UTC)
    now_iso = as_of.isoformat()
    league_filter = {name.strip().lower() for name in args.leagues} if args.leagues else None
    encoding = detect_encoding(csv_path) if args.encoding == "auto" else args.encoding
    logger.info("using encoding=%s", encoding)

    if args.images == "cloudinary" and not cloudinary_configured():
        raise SystemExit(
            "--images cloudinary requires CLOUDINARY_CLOUD_NAME / CLOUDINARY_API_KEY / CLOUDINARY_API_SECRET."
        )

    # 1) Read + build payloads (uploading images if requested).
    columns_holder: list[ColumnMap] = []
    payloads: list[dict[str, Any]] = []
    frozen_prices: dict[str, float] = {}
    rows_seen = 0
    images_uploaded = 0
    http_client = httpx.Client() if args.images == "cloudinary" else None
    try:
        for row, columns in read_rows(csv_path, columns_holder, league_filter, args.limit, encoding):
            rows_seen += 1
            source_photo = columns.get(row, "photo")
            photo_url: str | None = None
            if args.images == "url":
                photo_url = source_photo
            elif args.images == "cloudinary" and source_photo and http_client is not None:
                player_id = columns.get(row, "player_id") or str(rows_seen)
                hosted = upload_remote_image_to_cloudinary(
                    source_photo, public_id=f"{SOURCE_NAME}_{player_id}", client=http_client
                )
                if hosted:
                    photo_url = hosted
                    images_uploaded += 1
                else:
                    photo_url = source_photo  # fall back to source URL if mirroring failed
            payload = build_payload(row, columns, as_of=as_of, photo_url=photo_url, now_iso=now_iso)
            if payload is not None:
                payloads.append(payload)
                # Frozen launch price (banded GSI 60 / age 20 / team 20). At ingest,
                # effective GSI == overall, so this is the launch price.
                _age = None
                if payload.get("date_of_birth"):
                    try:
                        _age = (as_of.date() - date.fromisoformat(payload["date_of_birth"])).days / 365.25
                    except ValueError:
                        _age = None
                _price, _tier, _ = compute_price_credits(
                    overall=payload.get("overall_rating"),
                    club_rating=payload.get("club_rating"),
                    age=_age,
                )
                frozen_prices[payload["source_player_key"]] = _price
            if rows_seen % 500 == 0:
                logger.info("processed rows=%s payloads=%s images_uploaded=%s", rows_seen, len(payloads), images_uploaded)
    finally:
        if http_client is not None:
            http_client.close()

    tier_breakdown: dict[str, int] = {}
    for payload in payloads:
        tier_breakdown[payload["real_player_tier"]] = tier_breakdown.get(payload["real_player_tier"], 0) + 1
    club_groups = group_by_club(payloads)
    logger.info(
        "parsed rows=%s payloads=%s clubs=%s tiers=%s", rows_seen, len(payloads), len(club_groups), tier_breakdown
    )

    report: dict[str, Any] = {
        "status": "dry_run" if args.dry_run else "pending",
        "csv": str(csv_path),
        "as_of": now_iso,
        "rows_seen": rows_seen,
        "payloads_built": len(payloads),
        "clubs": len(club_groups),
        "images_mode": args.images,
        "images_uploaded": images_uploaded,
        "tier_breakdown": tier_breakdown,
        "resolved_columns": {k: v for k, v in (columns_holder[0]._resolved.items() if columns_holder else {})},
    }

    if args.dry_run:
        _write_report(Path(args.report_path), report)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    # 2) Feed the existing ingestion service, one club-batch at a time.
    settings = load_settings(
        environ={**os.environ, "DATABASE_URL": args.database_url, "GTE_DATABASE_URL": args.database_url}
    )
    engine = create_database_engine(args.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    ingestion_service = RealPlayerIngestionService(session_factory=session_factory, settings=settings)

    # Resume-skip: drop payloads already imported so a restart continues where it
    # left off instead of re-processing (the full run is many hours over the pooler).
    from sqlalchemy import select as _select

    from app.ingestion.models import Player as _Player

    with session_factory() as _s:
        already = {
            k for (k,) in _s.execute(
                _select(_Player.provider_external_id).where(_Player.source_provider == SOURCE_NAME)
            ).all()
        }
    if already:
        before = len(payloads)
        payloads = [p for p in payloads if p["source_player_key"] not in already]
        report["resume_skipped"] = before - len(payloads)
        logger.info("resume: skipped %s already-imported players, %s remaining", before - len(payloads), len(payloads))

    # Pre-seed competitions with countries so clubs can auto-create (else every
    # player is skipped_mapping on a fresh DB).
    preseed = preseed_competitions(session_factory, payloads)
    report["preseed"] = preseed
    logger.info("preseeded competitions=%s countries_created=%s", preseed["competitions"], preseed["countries_created"])

    run_stamp = as_of.strftime("%Y%m%dT%H%M%SZ")
    totals = {"processed": 0, "created": 0, "updated": 0, "batches_written": 0, "batches_blocked": 0, "player_failures": 0}
    try:
        for club, club_payloads in club_groups.items():
            _write_club_batch(
                ingestion_service=ingestion_service,
                club=club,
                payloads=club_payloads,
                run_stamp=run_stamp,
                totals=totals,
            )
        # Freeze the banded launch price as authoritative.
        repriced = reprice_frozen(session_factory, frozen_prices)
        report["repriced_players"] = repriced
        logger.info("repriced (frozen banded price) players=%s", repriced)
        report["status"] = "success"
    except Exception as exc:  # noqa: BLE001
        report["status"] = "error"
        report["error"] = str(exc)
        logger.exception("import failed")
    finally:
        report["totals"] = totals
        engine.dispose()

    _write_report(Path(args.report_path), report)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "success" else 1


def reprice_frozen(session_factory, frozen_prices: dict[str, float]) -> int:
    """Overwrite each imported player's authoritative price with the frozen banded
    price, making the importer the pricing authority (per launch decision).

    Writes to `PlayerSummaryReadModel.current_value_credits` (what the app displays
    and trades on) and the value snapshot `target_credits`, so nothing re-derives a
    different number.
    """
    from sqlalchemy import select

    from app.ingestion.models import Player
    from app.players.read_models import PlayerSummaryReadModel
    from app.value_engine.read_models import PlayerValueSnapshotRecord

    updated = 0
    with session_factory() as session:
        id_by_key = {
            key: pid
            for pid, key in session.execute(
                select(Player.id, Player.provider_external_id).where(Player.source_provider == SOURCE_NAME)
            ).all()
        }
        for key, price in frozen_prices.items():
            pid = id_by_key.get(key)
            if pid is None:
                continue
            summary = session.get(PlayerSummaryReadModel, pid)
            if summary is not None:
                summary.current_value_credits = price
                summary.previous_value_credits = price
                summary.movement_pct = 0.0
            for snap in session.scalars(
                select(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.player_id == pid)
            ):
                snap.target_credits = price
                snap.base_value_credits = price
            updated += 1
        session.commit()
    return updated


def _write_club_batch(
    *,
    ingestion_service: RealPlayerIngestionService,
    club: str,
    payloads: list[dict[str, Any]],
    run_stamp: str,
    totals: dict[str, int],
) -> None:
    valid = _validated_payloads(payloads)
    if not valid:
        return
    club_slug = hashlib.sha1(club.encode("utf-8")).hexdigest()[:10]
    batch_id = f"sofifa-import:{run_stamp}:{club_slug}"
    request = RealPlayerIngestionRequest.model_validate(
        {
            "mode": "batch_import",
            "ingestion_batch_id": batch_id,
            "ingestion_source_version": batch_id,
            "as_of": datetime.now(UTC).isoformat(),
            "players": valid,
        }
    )
    try:
        write_report = ingestion_service.write_batch(request)
        totals["processed"] += int(write_report.players_processed)
        totals["created"] += int(write_report.players_created)
        totals["updated"] += int(write_report.players_updated)
        totals["batches_written"] += 1
        logger.info(
            "club=%s written processed=%s created=%s updated=%s",
            club,
            write_report.players_processed,
            write_report.players_created,
            write_report.players_updated,
        )
    except RealPlayerBatchBlockedError as exc:
        # Fall back to per-player writes so one bad row can't sink a whole club.
        totals["batches_blocked"] += 1
        logger.warning("club=%s batch blocked (%s); retrying per-player", club, exc)
        for single in valid:
            single_id = f"{batch_id}:{single['source_player_key']}"
            single_request = RealPlayerIngestionRequest.model_validate(
                {
                    "mode": "batch_import",
                    "ingestion_batch_id": single_id,
                    "ingestion_source_version": single_id,
                    "as_of": datetime.now(UTC).isoformat(),
                    "players": [single],
                }
            )
            try:
                write_report = ingestion_service.write_batch(single_request)
                totals["processed"] += int(write_report.players_processed)
                totals["created"] += int(write_report.players_created)
                totals["updated"] += int(write_report.players_updated)
            except Exception as player_exc:  # noqa: BLE001
                totals["player_failures"] += 1
                logger.warning("player write failed key=%s error=%s", single["source_player_key"], player_exc)


def _validated_payloads(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid: list[dict[str, Any]] = []
    for payload in payloads:
        try:
            RealPlayerSeedInput.model_validate(payload)
        except Exception as exc:  # noqa: BLE001
            logger.warning("invalid payload key=%s error=%s", payload.get("source_player_key"), exc)
            continue
        valid.append(payload)
    return valid


def _write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path = report_path.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
