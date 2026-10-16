from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import html
import json
import logging
import os
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.parse import quote

import requests
from requests import Session
from sqlalchemy import text

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.ingestion.real_player_ingestion_service import (
    RealPlayerBatchBlockedError,
    RealPlayerIngestionService,
)
from app.ingestion.normalizers import normalize_country_name
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest, RealPlayerSeedInput

logger = logging.getLogger("import_transfermarkt_real_players")

_FALLBACK_AUTH_SECRET = "local-dev-refresh-secret"  # pragma: allowlist secret
_FALLBACK_MEDIA_SECRET = "local-dev-refresh-media-secret"  # pragma: allowlist secret
_TM_BASE_URL = "https://www.transfermarkt.co.uk"
_TM_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
_PROVIDER_RETRY_ATTEMPTS = 4
_PROVIDER_RETRY_BASE_SECONDS = 3.0
_OUTER_PLAYER_ROW_RE = re.compile(
    r'<tr class="(?:odd|even)">(?P<row>.*?<a href="/[^"]+/marktwertverlauf/spieler/\d+">[^<]*</a></td></tr>)',
    re.S,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CompetitionSpec:
    name: str
    competition_code: str
    slug: str
    competition_level: str


@dataclass(frozen=True, slots=True)
class YouthCountrySpec:
    ranking_name: str
    search_name: str


_REQUESTED_COMPETITIONS: tuple[CompetitionSpec, ...] = (
    CompetitionSpec("Saudi Pro League", "SA1", "saudi-professional-league", "elite"),
    CompetitionSpec("Major League Soccer", "MLS1", "major-league-soccer", "elite"),
    CompetitionSpec("Brazilian Serie A", "BRA1", "campeonato-brasileiro-serie-a", "elite"),
    CompetitionSpec("Argentinian Primera Division", "AR1N", "liga-profesional-de-futbol", "elite"),
    CompetitionSpec("Belgian Pro League", "BE1", "jupiler-pro-league", "elite"),
    CompetitionSpec("Spanish La Liga 2", "ES2", "laliga2", "second_tier"),
    CompetitionSpec("Italian Serie B", "IT2", "serie-b", "second_tier"),
    CompetitionSpec("Eredivisie", "NL1", "eredivisie", "elite"),
    CompetitionSpec("Bundesliga", "L1", "bundesliga", "elite"),
    CompetitionSpec("Czech First League", "TS1", "chance-liga", "elite"),
    CompetitionSpec("Portuguese Primeira Liga", "PO1", "liga-nos", "elite"),
)

_TOP_40_COUNTRIES: tuple[YouthCountrySpec, ...] = (
    YouthCountrySpec("Argentina", "Argentina"),
    YouthCountrySpec("France", "France"),
    YouthCountrySpec("Spain", "Spain"),
    YouthCountrySpec("England", "England"),
    YouthCountrySpec("Brazil", "Brazil"),
    YouthCountrySpec("Belgium", "Belgium"),
    YouthCountrySpec("Netherlands", "Netherlands"),
    YouthCountrySpec("Colombia", "Colombia"),
    YouthCountrySpec("Portugal", "Portugal"),
    YouthCountrySpec("Italy", "Italy"),
    YouthCountrySpec("Uruguay", "Uruguay"),
    YouthCountrySpec("Croatia", "Croatia"),
    YouthCountrySpec("Germany", "Germany"),
    YouthCountrySpec("Morocco", "Morocco"),
    YouthCountrySpec("Switzerland", "Switzerland"),
    YouthCountrySpec("Mexico", "Mexico"),
    YouthCountrySpec("Japan", "Japan"),
    YouthCountrySpec("USA", "United States"),
    YouthCountrySpec("Senegal", "Senegal"),
    YouthCountrySpec("IR Iran", "Iran"),
    YouthCountrySpec("Denmark", "Denmark"),
    YouthCountrySpec("Austria", "Austria"),
    YouthCountrySpec("Korea Republic", "South Korea"),
    YouthCountrySpec("Australia", "Australia"),
    YouthCountrySpec("Ukraine", "Ukraine"),
    YouthCountrySpec("Türkiye", "Turkey"),
    YouthCountrySpec("Ecuador", "Ecuador"),
    YouthCountrySpec("Panama", "Panama"),
    YouthCountrySpec("Poland", "Poland"),
    YouthCountrySpec("Sweden", "Sweden"),
    YouthCountrySpec("Wales", "Wales"),
    YouthCountrySpec("Hungary", "Hungary"),
    YouthCountrySpec("Venezuela", "Venezuela"),
    YouthCountrySpec("Canada", "Canada"),
    YouthCountrySpec("Serbia", "Serbia"),
    YouthCountrySpec("Russia", "Russia"),
    YouthCountrySpec("Qatar", "Qatar"),
    YouthCountrySpec("Egypt", "Egypt"),
    YouthCountrySpec("Côte d'Ivoire", "Ivory Coast"),
    YouthCountrySpec("Nigeria", "Nigeria"),
)

_TOP_70_COUNTRIES: tuple[str, ...] = (
    "Argentina",
    "France",
    "Spain",
    "England",
    "Brazil",
    "Belgium",
    "Netherlands",
    "Colombia",
    "Portugal",
    "Italy",
    "Uruguay",
    "Croatia",
    "Germany",
    "Morocco",
    "Switzerland",
    "Mexico",
    "Japan",
    "USA",
    "Senegal",
    "IR Iran",
    "Denmark",
    "Austria",
    "Korea Republic",
    "Australia",
    "Ukraine",
    "Türkiye",
    "Ecuador",
    "Panama",
    "Poland",
    "Sweden",
    "Wales",
    "Hungary",
    "Venezuela",
    "Canada",
    "Serbia",
    "Russia",
    "Qatar",
    "Egypt",
    "Côte d'Ivoire",
    "Nigeria",
    "Tunisia",
    "Chile",
    "Slovakia",
    "Romania",
    "Algeria",
    "Czechia",
    "Scotland",
    "Peru",
    "Norway",
    "Costa Rica",
    "Mali",
    "Iraq",
    "Slovenia",
    "South Africa",
    "Republic of Ireland",
    "Saudi Arabia",
    "Burkina Faso",
    "Bosnia and Herzegovina",
    "Jordan",
    "Albania",
    "Honduras",
    "North Macedonia",
    "Cabo Verde",
    "United Arab Emirates",
    "Northern Ireland",
)
_COUNTRY_NORMALIZATION_OVERRIDES = {
    "usa": "United States",
    "ir iran": "Iran",
    "korea republic": "South Korea",
    "turkiye": "Turkey",
    "cote divoire": "Ivory Coast",
    "czechia": "Czech Republic",
    "republic of ireland": "Ireland",
    "united arab emirates": "United Arab Emirates",
}


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    _configure_logging()

    started_at = _now_iso()
    report_path = Path(args.report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    settings = load_settings(
        environ={
            **os.environ,
            "DATABASE_URL": args.database_url,
            "GTE_DATABASE_URL": args.database_url,
            "GTE_AUTH_SECRET": os.environ.get("GTE_AUTH_SECRET", _FALLBACK_AUTH_SECRET),
            "GTE_MEDIA_SIGNING_SECRET": os.environ.get("GTE_MEDIA_SIGNING_SECRET", _FALLBACK_MEDIA_SECRET),
        }
    )
    engine = create_database_engine(args.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    ingestion_service = RealPlayerIngestionService(
        session_factory=session_factory,
        settings=settings,
    )

    tm_session = requests.Session()
    tm_session.headers.update(_TM_HEADERS)

    selected_specs = _select_competitions(args.leagues)
    report: dict[str, Any] = {
        "status": "success",
        "started_at": started_at,
        "completed_at": None,
        "database_url": args.database_url,
        "selected_leagues": [spec.name for spec in selected_specs],
        "domestic": [],
        "youth": {
            "teams_written": 0,
            "teams_failed": 0,
            "players_processed": 0,
            "players_created": 0,
            "players_updated": 0,
            "player_level_failures": 0,
            "teams": [],
        },
    }

    try:
        if not args.skip_domestic:
            for spec in selected_specs:
                report["domestic"].append(
                    _run_competition_import(
                        tm_session=tm_session,
                        ingestion_service=ingestion_service,
                        spec=spec,
                        run_stamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
                        pause_ms=max(int(args.pause_ms), 0),
                        timeout_seconds=max(int(args.provider_timeout_seconds), 1),
                    )
                )

        if not args.skip_youth:
            report["youth"] = _run_youth_import(
                tm_session=tm_session,
                ingestion_service=ingestion_service,
                run_stamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
                pause_ms=max(int(args.pause_ms), 0),
                timeout_seconds=max(int(args.provider_timeout_seconds), 1),
            )

        report["verification"] = _verification_snapshot(session_factory)
        report["completed_at"] = _now_iso()
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        error_payload = {
            **report,
            "status": "error",
            "error": str(exc),
            "completed_at": _now_iso(),
        }
        report_path.write_text(json.dumps(error_payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(error_payload, indent=2, sort_keys=True))
        return 1
    finally:
        tm_session.close()
        engine.dispose()


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import live Transfermarkt players into the app.")
    parser.add_argument(
        "--database-url",
        default="sqlite:///C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/gte_backend.db",
    )
    parser.add_argument(
        "--report-path",
        default="C:/Users/ayomc/Desktop/GLOBAL TALENT EXCHANGE/tmp/transfermarkt-real-player-import-report.json",
    )
    parser.add_argument(
        "--provider-timeout-seconds",
        type=int,
        default=60,
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=250,
    )
    parser.add_argument(
        "--league",
        dest="leagues",
        action="append",
        default=[],
        help="Repeat to limit the domestic import to specific requested league names.",
    )
    parser.add_argument("--skip-domestic", action="store_true")
    parser.add_argument("--skip-youth", action="store_true")
    return parser.parse_args(argv)


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _select_competitions(requested_leagues: list[str]) -> tuple[CompetitionSpec, ...]:
    if not requested_leagues:
        return _REQUESTED_COMPETITIONS
    requested = {_fold_text(value) for value in requested_leagues if _fold_text(value)}
    selected = tuple(spec for spec in _REQUESTED_COMPETITIONS if _fold_text(spec.name) in requested)
    if not selected:
        raise ValueError("None of the requested leagues matched the configured Transfermarkt competition list.")
    return selected


def _run_competition_import(
    *,
    tm_session: Session,
    ingestion_service: RealPlayerIngestionService,
    spec: CompetitionSpec,
    run_stamp: str,
    pause_ms: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    competition_url = f"{_TM_BASE_URL}/{spec.slug}/startseite/wettbewerb/{spec.competition_code}"
    competition_html = _get_html(
        tm_session,
        competition_url,
        description=f"competition {spec.name}",
        timeout_seconds=timeout_seconds,
    )
    clubs = _parse_competition_clubs(competition_html)
    report: dict[str, Any] = {
        "competition_name": spec.name,
        "competition_code": spec.competition_code,
        "club_count": len(clubs),
        "clubs_written": 0,
        "club_batches_blocked": 0,
        "players_processed": 0,
        "players_created": 0,
        "players_updated": 0,
        "player_level_failures": 0,
        "clubs": [],
    }

    logger.info("importing competition=%s clubs=%s", spec.name, len(clubs))
    for club in clubs:
        club_report = {
            "club_id": club["id"],
            "club_name": club["name"],
            "players_processed": 0,
            "players_created": 0,
            "players_updated": 0,
            "player_level_failures": 0,
            "status": "pending",
            "errors": [],
        }
        try:
            squad_url = f"{_TM_BASE_URL}/{club['slug']}/kader/verein/{club['id']}/saison_id/{club['season_id']}"
            squad_html = _get_html(
                tm_session,
                squad_url,
                description=f"squad {spec.name} {club['name']}",
                timeout_seconds=timeout_seconds,
            )
            payloads = _parse_domestic_squad_payloads(
                squad_html=squad_html,
                league_name=spec.name,
                league_key=spec.competition_code,
                competition_level=spec.competition_level,
                club=club,
            )
            if not payloads:
                club_report["status"] = "empty"
                report["clubs"].append(club_report)
                continue
            _write_payload_group(
                ingestion_service=ingestion_service,
                tm_session=tm_session,
                payloads=payloads,
                run_stamp=run_stamp,
                batch_prefix=f"tm-club:{spec.competition_code}:{club['id']}",
                report_target=club_report,
                timeout_seconds=timeout_seconds,
            )
            report["clubs_written"] += 1
            report["club_batches_blocked"] += int(club_report["status"] == "partial")
        except Exception as exc:  # pragma: no cover - live data dependent
            club_report["status"] = "error"
            club_report["errors"].append(str(exc))
            logger.warning(
                "competition import failed league=%s club=%s error=%s",
                spec.name,
                club["name"],
                exc,
            )
        report["players_processed"] += int(club_report["players_processed"])
        report["players_created"] += int(club_report["players_created"])
        report["players_updated"] += int(club_report["players_updated"])
        report["player_level_failures"] += int(club_report["player_level_failures"])
        report["clubs"].append(club_report)
        if pause_ms > 0:
            time.sleep(pause_ms / 1000.0)
    return report


def _run_youth_import(
    *,
    tm_session: Session,
    ingestion_service: RealPlayerIngestionService,
    run_stamp: str,
    pause_ms: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "teams_written": 0,
        "teams_failed": 0,
        "players_processed": 0,
        "players_created": 0,
        "players_updated": 0,
        "player_level_failures": 0,
        "teams": [],
    }
    for country in _TOP_40_COUNTRIES:
        for age_group in ("U20", "U17"):
            team_report = {
                "country": country.ranking_name,
                "age_group": age_group,
                "team_slug": None,
                "team_id": None,
                "players_processed": 0,
                "players_created": 0,
                "players_updated": 0,
                "player_level_failures": 0,
                "status": "pending",
                "errors": [],
            }
            try:
                team_ref = _resolve_youth_team_reference(
                    tm_session=tm_session,
                    query=f"{country.search_name} {age_group}",
                    age_group=age_group,
                    timeout_seconds=timeout_seconds,
                )
                team_report["team_slug"] = team_ref["slug"]
                team_report["team_id"] = team_ref["id"]
                team_html = _get_html(
                    tm_session,
                    f"{_TM_BASE_URL}/{team_ref['slug']}/startseite/verein/{team_ref['id']}",
                    description=f"youth team {country.ranking_name} {age_group}",
                    timeout_seconds=timeout_seconds,
                )
                payloads = _parse_youth_team_payloads(
                    squad_html=team_html,
                    country_name=country.ranking_name,
                    age_group=age_group,
                )
                if not payloads:
                    team_report["status"] = "empty"
                    report["teams"].append(team_report)
                    continue
                _write_payload_group(
                    ingestion_service=ingestion_service,
                    tm_session=tm_session,
                    payloads=payloads,
                    run_stamp=run_stamp,
                    batch_prefix=f"tm-youth:{_fold_text(country.ranking_name)}:{age_group.lower()}",
                    report_target=team_report,
                    timeout_seconds=timeout_seconds,
                )
                report["teams_written"] += 1
            except Exception as exc:  # pragma: no cover - live data dependent
                team_report["status"] = "error"
                team_report["errors"].append(str(exc))
                report["teams_failed"] += 1
                logger.warning(
                    "youth import failed country=%s age_group=%s error=%s",
                    country.ranking_name,
                    age_group,
                    exc,
                )
            report["players_processed"] += int(team_report["players_processed"])
            report["players_created"] += int(team_report["players_created"])
            report["players_updated"] += int(team_report["players_updated"])
            report["player_level_failures"] += int(team_report["player_level_failures"])
            report["teams"].append(team_report)
            if pause_ms > 0:
                time.sleep(pause_ms / 1000.0)
    return report


def _write_payload_group(
    *,
    ingestion_service: RealPlayerIngestionService,
    tm_session: Session,
    payloads: list[dict[str, Any]],
    run_stamp: str,
    batch_prefix: str,
    report_target: dict[str, Any],
    timeout_seconds: int,
) -> None:
    try:
        write_report = _write_payload_batch(
            ingestion_service=ingestion_service,
            payloads=payloads,
            batch_id=f"{batch_prefix}:{run_stamp}",
        )
        _apply_write_report(report_target, write_report)
        report_target["status"] = "written"
    except RealPlayerBatchBlockedError as exc:
        report_target["status"] = "partial"
        report_target["errors"].append(str(exc))
        logger.info("batch blocked prefix=%s players=%s falling back to player writes", batch_prefix, len(payloads))
        for payload in payloads:
            try:
                write_report = _write_payload_batch(
                    ingestion_service=ingestion_service,
                    payloads=[payload],
                    batch_id=f"{batch_prefix}:{payload['source_player_key']}:{run_stamp}",
                )
                _apply_write_report(report_target, write_report)
            except Exception as first_exc:  # pragma: no cover - live data dependent
                enriched_payload = _enrich_payload_from_profile(
                    tm_session=tm_session,
                    payload=payload,
                    timeout_seconds=timeout_seconds,
                )
                if enriched_payload is None:
                    report_target["player_level_failures"] += 1
                    report_target["errors"].append(f"{payload['source_player_key']}: {first_exc}")
                    continue
                try:
                    write_report = _write_payload_batch(
                        ingestion_service=ingestion_service,
                        payloads=[enriched_payload],
                        batch_id=f"{batch_prefix}:{payload['source_player_key']}:enriched:{run_stamp}",
                    )
                    _apply_write_report(report_target, write_report)
                except Exception as second_exc:
                    report_target["player_level_failures"] += 1
                    report_target["errors"].append(f"{payload['source_player_key']}: {second_exc}")


def _apply_write_report(target: dict[str, Any], write_report) -> None:
    target["players_processed"] += int(write_report.players_processed)
    target["players_created"] += int(write_report.players_created)
    target["players_updated"] += int(write_report.players_updated)


def _write_payload_batch(
    *,
    ingestion_service: RealPlayerIngestionService,
    payloads: list[dict[str, Any]],
    batch_id: str,
):
    valid_payloads = _validated_payloads(payloads)
    if not valid_payloads:
        raise ValueError(f"No valid payloads remained for batch {batch_id}.")
    request = RealPlayerIngestionRequest.model_validate(
        {
            "mode": "batch_import",
            "ingestion_batch_id": batch_id,
            "ingestion_source_version": batch_id,
            "as_of": _now_iso(),
            "players": valid_payloads,
        }
    )
    return ingestion_service.write_batch(request)


def _validated_payloads(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid_payloads: list[dict[str, Any]] = []
    for payload in payloads:
        sanitized = _sanitize_payload(payload)
        try:
            RealPlayerSeedInput.model_validate(sanitized)
        except Exception as exc:
            logger.warning(
                "dropping invalid payload source_key=%s error=%s",
                payload.get("source_player_key"),
                exc,
            )
            continue
        valid_payloads.append(sanitized)
    return valid_payloads


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    sanitized["canonical_name"] = _clean_text(sanitized.get("canonical_name"))
    sanitized["display_name"] = _clean_text(sanitized.get("display_name"))
    sanitized["nationality"] = _normalize_country(sanitized.get("nationality"))
    sanitized["national_team_name"] = _normalize_country(sanitized.get("national_team_name"))
    sanitized["national_team_code"] = _clean_text(sanitized.get("national_team_code"))
    sanitized["national_team_age_group"] = _clean_text(sanitized.get("national_team_age_group"))
    sanitized["photo_url"] = _clean_text(sanitized.get("photo_url"))
    sanitized["primary_position"] = _clean_text(sanitized.get("primary_position"))
    sanitized["current_real_world_club"] = _clean_text(sanitized.get("current_real_world_club"))
    sanitized["current_real_world_club_key"] = _clean_text(sanitized.get("current_real_world_club_key"))
    sanitized["current_real_world_league"] = _clean_text(sanitized.get("current_real_world_league"))
    sanitized["current_real_world_league_key"] = _clean_text(sanitized.get("current_real_world_league_key"))
    sanitized["dominant_foot"] = _clean_text(sanitized.get("dominant_foot"))
    sanitized["height_cm"] = _normalize_int(sanitized.get("height_cm"))
    sanitized["age"] = _normalize_int(sanitized.get("age"))
    sanitized["current_market_reference_value"] = _normalize_float(sanitized.get("current_market_reference_value"))
    if sanitized.get("date_of_birth"):
        sanitized["date_of_birth"] = _normalize_date(sanitized["date_of_birth"])
    sanitized.pop("_tm_profile_path", None)
    return sanitized


def _parse_competition_clubs(competition_html: str) -> list[dict[str, str]]:
    clubs_by_id: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r'<a title="(?P<name>[^"]+)" href="/(?P<slug>[^"]+)/kader/verein/(?P<id>\d+)/saison_id/(?P<season>\d+)"'
    )
    for match in pattern.finditer(competition_html):
        club_id = match.group("id")
        clubs_by_id[club_id] = {
            "id": club_id,
            "name": _clean_text(match.group("name")) or club_id,
            "slug": match.group("slug"),
            "season_id": match.group("season"),
        }
    return list(clubs_by_id.values())


def _parse_domestic_squad_payloads(
    *,
    squad_html: str,
    league_name: str,
    league_key: str,
    competition_level: str,
    club: dict[str, str],
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for row_match in _OUTER_PLAYER_ROW_RE.finditer(squad_html):
        row = row_match.group("row")
        player_match = re.search(
            r'table class="inline-table">.*?(?:data-src|src)="(?P<photo>https://[^"]+)"[^>]*title="(?P<img_title>[^"]+)".*?'
            r'<a href="(?P<profile>/[^"]+/profil/spieler/(?P<id>\d+))">\s*(?P<name>.*?)\s*</a>.*?'
            r"<tr>\s*<td>\s*(?P<position>.*?)\s*</td>\s*</tr>.*?"
            r'<td class="zentriert">(?P<age>\d+)</td>.*?'
            r'<a href="/[^"]+/marktwertverlauf/spieler/\d+">(?P<value>[^<]*)</a>',
            row,
            re.S,
        )
        if player_match is None:
            continue
        nationalities = re.findall(
            r'title="([^"]+)" alt="[^"]+" class="flaggenrahmen"',
            row,
        )
        payloads.append(
            {
                "source_name": "transfermarkt",
                "source_player_key": player_match.group("id"),
                "canonical_name": _strip_tags(player_match.group("name")),
                "display_name": _strip_tags(player_match.group("name")),
                "known_aliases": [],
                "nationality": _normalize_country(nationalities[0] if nationalities else None),
                "age": _normalize_int(player_match.group("age")),
                "primary_position": _strip_tags(player_match.group("position")),
                "current_real_world_club": club["name"],
                "current_real_world_club_key": club["id"],
                "current_real_world_league": league_name,
                "current_real_world_league_key": league_key,
                "competition_level": competition_level,
                "current_market_reference_value": _parse_market_value_eur(player_match.group("value")),
                "market_reference_currency": "EUR",
                "photo_url": _clean_text(player_match.group("photo")),
                "source_last_refreshed_at": _now_iso(),
                "_tm_profile_path": player_match.group("profile"),
            }
        )
    return payloads


def _parse_youth_team_payloads(
    *,
    squad_html: str,
    country_name: str,
    age_group: str,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    normalized_country = _normalize_country(country_name)
    for row_match in _OUTER_PLAYER_ROW_RE.finditer(squad_html):
        row = row_match.group("row")
        player_match = re.search(
            r'table class="inline-table">.*?(?:data-src|src)="(?P<photo>https://[^"]+)"[^>]*title="(?P<img_title>[^"]+)".*?'
            r'<a href="(?P<profile>/[^"]+/profil/spieler/(?P<id>\d+))">\s*(?P<name>.*?)\s*</a>.*?'
            r"<tr>\s*<td>\s*(?P<position>.*?)\s*</td>\s*</tr>.*?"
            r'<td class="zentriert">(?P<dob>\d{2}/\d{2}/\d{4})\s*\((?P<age>\d+)\)</td>.*?'
            r'<a title="(?P<club>[^"]+)" href="/(?P<club_slug>[^"]+)/startseite/verein/(?P<club_id>\d+)".*?'
            r'<a href="/[^"]+/marktwertverlauf/spieler/\d+">(?P<value>[^<]*)</a>',
            row,
            re.S,
        )
        if player_match is None:
            continue
        payloads.append(
            {
                "source_name": "transfermarkt",
                "source_player_key": player_match.group("id"),
                "canonical_name": _strip_tags(player_match.group("name")),
                "display_name": _strip_tags(player_match.group("name")),
                "known_aliases": [],
                "nationality": normalized_country,
                "national_team_name": normalized_country,
                "national_team_age_group": age_group,
                "date_of_birth": _normalize_date(player_match.group("dob")),
                "age": _normalize_int(player_match.group("age")),
                "primary_position": _strip_tags(player_match.group("position")),
                "current_real_world_club": _clean_text(player_match.group("club")),
                "current_real_world_club_key": player_match.group("club_id"),
                "competition_level": "international_youth",
                "current_market_reference_value": _parse_market_value_eur(player_match.group("value")),
                "market_reference_currency": "EUR",
                "photo_url": _clean_text(player_match.group("photo")),
                "source_last_refreshed_at": _now_iso(),
                "_tm_profile_path": player_match.group("profile"),
            }
        )
    return payloads


def _resolve_youth_team_reference(
    *,
    tm_session: Session,
    query: str,
    age_group: str,
    timeout_seconds: int,
) -> dict[str, str]:
    search_html = _get_html(
        tm_session,
        f"{_TM_BASE_URL}/schnellsuche/ergebnis/schnellsuche?query={quote(query)}",
        description=f"search {query}",
        timeout_seconds=timeout_seconds,
    )
    suffix = age_group.lower()
    matches: list[dict[str, str]] = []
    pattern = re.compile(r'/(?P<slug>[^"]+)/startseite/verein/(?P<id>\d+)')
    for match in pattern.finditer(search_html):
        slug = match.group("slug")
        if f"-{suffix}" not in slug:
            continue
        item = {"slug": slug, "id": match.group("id")}
        if item not in matches:
            matches.append(item)
    if not matches:
        raise RuntimeError(f"No Transfermarkt {age_group} result found for search '{query}'.")
    return matches[0]


def _enrich_payload_from_profile(
    *,
    tm_session: Session,
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any] | None:
    profile_path = payload.get("_tm_profile_path")
    if not isinstance(profile_path, str) or not profile_path:
        return None
    try:
        html_payload = _get_html(
            tm_session,
            f"{_TM_BASE_URL}{profile_path}",
            description=f"profile {payload.get('source_player_key')}",
            timeout_seconds=timeout_seconds,
        )
    except Exception:
        return None
    enriched = dict(payload)
    if not enriched.get("date_of_birth"):
        dob_match = re.search(r"Date of birth/Age:.*?(\d{2}/\d{2}/\d{4})", html_payload, re.S)
        if dob_match:
            enriched["date_of_birth"] = _normalize_date(dob_match.group(1))
    if not enriched.get("height_cm"):
        height_match = re.search(r"Height:</span>\s*<span[^>]*>\s*([0-9],[0-9]{2})", html_payload, re.S)
        if height_match:
            enriched["height_cm"] = _parse_metric_height_cm(height_match.group(1))
    if not enriched.get("dominant_foot"):
        foot_match = re.search(r"Foot:</span>\s*<span[^>]*>\s*([^<]+?)\s*</span>", html_payload, re.S)
        if foot_match:
            enriched["dominant_foot"] = _clean_text(foot_match.group(1))
    if not enriched.get("nationality"):
        citizenship_match = re.search(r"Citizenship:</span>\s*<span[^>]*>(.*?)</span>", html_payload, re.S)
        if citizenship_match:
            enriched["nationality"] = _normalize_country(_strip_tags(citizenship_match.group(1)))
    return enriched


def _get_html(
    session: Session,
    url: str,
    *,
    description: str,
    timeout_seconds: int,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, _PROVIDER_RETRY_ATTEMPTS + 1):
        try:
            response = session.get(url, timeout=timeout_seconds)
            response.raise_for_status()
            return response.text
        except Exception as exc:  # pragma: no cover - network dependent
            last_error = exc
            if attempt >= _PROVIDER_RETRY_ATTEMPTS:
                break
            delay_seconds = min(_PROVIDER_RETRY_BASE_SECONDS * (2 ** (attempt - 1)), 30.0)
            logger.warning(
                "request failed description=%s attempt=%s/%s delay=%ss error=%s",
                description,
                attempt,
                _PROVIDER_RETRY_ATTEMPTS,
                delay_seconds,
                exc,
            )
            time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def _verification_snapshot(session_factory) -> dict[str, Any]:
    with session_factory() as session:
        counts = {
            "distinct_profiles": int(
                session.execute(text("select count(distinct gtex_player_id) from real_player_profiles")).scalar_one()
            ),
            "distinct_markets": int(
                session.execute(text("select count(distinct player_id) from player_share_markets")).scalar_one()
            ),
            "profiles_without_market": int(session.execute(text("""
                        select count(*) from (
                            select distinct gtex_player_id from real_player_profiles
                            except
                            select distinct player_id from player_share_markets
                        )
                        """)).scalar_one()),
            "image_rows": int(
                session.execute(text("select count(*) from ingestion_player_image_metadata")).scalar_one()
            ),
        }
        nationality_rows = session.execute(text("""
                select distinct coalesce(country_name, '')
                from players
                where country_name is not null and trim(country_name) <> ''
                """))
        present = {_normalize_country(row[0]) for row in nationality_rows if row[0]}
        missing_top_70 = [country for country in _TOP_70_COUNTRIES if _normalize_country(country) not in present]
        counts["top_70_national_team_presence"] = {
            "covered": len(_TOP_70_COUNTRIES) - len(missing_top_70),
            "total": len(_TOP_70_COUNTRIES),
            "missing": missing_top_70,
        }
        counts["transfermarkt_source_links"] = int(
            session.execute(
                text("select count(*) from real_player_source_links where source_name = 'transfermarkt'")
            ).scalar_one()
        )
        return counts


def _normalize_date(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _parse_metric_height_cm(value: str | None) -> int | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    cleaned = cleaned.replace("m", "").replace(",", ".")
    try:
        meters = float(cleaned)
    except ValueError:
        return None
    return int(round(meters * 100))


def _parse_market_value_eur(value: str | None) -> float | None:
    cleaned = _clean_text(value)
    if not cleaned or cleaned == "-":
        return None
    normalized = (
        cleaned.replace("€", "")
        .replace("EUR", "")
        .replace("eur", "")
        .replace("&euro;", "")
        .replace(",", "")
        .strip()
        .lower()
    )
    if not normalized or normalized == "-":
        return None
    multiplier = 1.0
    if normalized.endswith("bn"):
        multiplier = 1_000_000_000.0
        normalized = normalized[:-2]
    elif normalized.endswith("m"):
        multiplier = 1_000_000.0
        normalized = normalized[:-1]
    elif normalized.endswith("k"):
        multiplier = 1_000.0
        normalized = normalized[:-1]
    try:
        return float(normalized) * multiplier
    except ValueError:
        return None


def _normalize_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_country(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    folded = _fold_text(cleaned)
    if folded in _COUNTRY_NORMALIZATION_OVERRIDES:
        return _COUNTRY_NORMALIZATION_OVERRIDES[folded]
    normalized = normalize_country_name(cleaned)
    return normalized or cleaned


def _strip_tags(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    return _WHITESPACE_RE.sub(" ", _TAG_RE.sub(" ", html.unescape(cleaned))).strip() or None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text_value = str(value)
    text_value = html.unescape(text_value).replace("\xa0", " ")
    text_value = _WHITESPACE_RE.sub(" ", text_value).strip()
    return text_value or None


def _fold_text(value: str | None) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    return cleaned.casefold()


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
