from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any
import unicodedata
from urllib.parse import quote

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
from app.ingestion.transfermarkt_second_zip import TransfermarktSecondZipReader
from app.providers.sportmonks_adapter import SportMonksAdapter
from app.schemas.real_player_ingestion import RealPlayerIngestionRequest, RealPlayerSeedInput

logger = logging.getLogger("refresh_target_league_real_players")

_FALLBACK_AUTH_SECRET = "local-dev-refresh-secret"
_FALLBACK_MEDIA_SECRET = "local-dev-refresh-media-secret"
_TURKEY_COUNTRY_ID = "404"
_HEIGHT_DECIMETER_MIN = 10
_HEIGHT_DECIMETER_MAX = 29
_WEIGHT_DECIMETER_MIN = 4
_WEIGHT_DECIMETER_MAX = 15
_PROVIDER_RETRY_ATTEMPTS = 5
_PROVIDER_RETRY_BASE_SECONDS = 5.0
_MANUAL_TEAM_MATCH_ALIASES: dict[str, tuple[str, ...]] = {
    "Alanyaspor": ("alanyaspor",),
    "Antalyaspor": ("antalyaspor",),
    "Basaksehir": ("istanbul basaksehir", "basaksehir"),
    "Besiktas": ("besiktas",),
    "Eyupspor": ("eyupspor",),
    "Fatih Karagumruk": ("fatih karagumruk",),
    "Fenerbahce": ("fenerbahce",),
    "Galatasaray": ("galatasaray",),
    "Gaziantep": ("gaziantep fk", "gaziantep", "gaziantep futbol kulubu"),
    "Genclerbirligi": ("genclerbirligi",),
    "Goztepe": ("goztepe",),
    "Kasimpasa": ("kasimpasa",),
    "Kayserispor": ("kayserispor",),
    "Kocaelispor": ("kocaelispor",),
    "Konyaspor": ("konyaspor",),
    "Rizespor": ("caykur rizespor", "rizespor"),
    "Samsunspor": ("samsunspor",),
    "Trabzonspor": ("trabzonspor",),
}
_MANUAL_TEAM_SEARCH_TERMS: dict[str, tuple[str, ...]] = {
    "Basaksehir": ("Istanbul Basaksehir",),
    "Besiktas": ("Besiktas",),
    "Eyupspor": ("Eyupspor",),
    "Fatih Karagumruk": ("Fatih Karagumruk",),
    "Fenerbahce": ("Fenerbahce",),
    "Gaziantep": ("Gaziantep FK", "Gaziantep"),
    "Genclerbirligi": ("Genclerbirligi",),
    "Goztepe": ("Goztepe",),
    "Kasimpasa": ("Kasimpasa",),
    "Rizespor": ("Caykur Rizespor", "Rizespor"),
}


@dataclass(frozen=True, slots=True)
class LeagueSpec:
    name: str
    competition_level: str
    desired_names: tuple[str, ...]
    fallback_competition_id: str | None = None
    fallback_season_id: str | None = None
    country_id: str | None = None
    target_club_names: tuple[str, ...] = ()
    manual_league_key: str | None = None
    # Explicit SportMonks league id. When set, resolution skips name matching
    # entirely — required for leagues whose name collides across countries
    # (e.g. Brazil "Serie A" id 648 vs Italy "Serie A" id 384).
    competition_id: str | None = None
    # Explicit SportMonks season id. When set, overrides the live currentSeason —
    # needed when the current season has no squads yet (e.g. Austria off-season).
    season_id: str | None = None


_TARGET_LEAGUES: tuple[LeagueSpec, ...] = (
    LeagueSpec(
        name="Premier League",
        competition_level="elite",
        # "Premier League" name collides across countries (England id 8 plus
        # ids 486/806); resolve by explicit id so name matching can't pick the
        # wrong country's empty season.
        desired_names=(),
        competition_id="8",
        fallback_competition_id="8",
        fallback_season_id="28083",
    ),
    LeagueSpec(
        name="Pro League",
        competition_level="top_flight",
        # "Pro League" name collides (Belgium id 208 vs id 944); pin by id so
        # the resolver can't pick the wrong competition's season.
        desired_names=(),
        competition_id="208",
        fallback_competition_id="208",
        fallback_season_id="25600",
    ),
    LeagueSpec(
        name="La Liga",
        competition_level="elite",
        desired_names=("La Liga",),
        competition_id="564",
        # Live current season (27965) has no squads yet; pin to 25659 (20 clubs)
        # until the new season populates.
        season_id="25659",
        fallback_competition_id="564",
        fallback_season_id="25659",
    ),
    LeagueSpec(
        name="Serie A",
        competition_level="elite",
        desired_names=("Serie A TIM", "Lega Serie A"),
        fallback_competition_id="384",
        fallback_season_id="25533",
    ),
    LeagueSpec(
        name="Ligue 1",
        competition_level="elite",
        desired_names=("Ligue 1",),
        fallback_competition_id="301",
        fallback_season_id="25651",
    ),
    LeagueSpec(
        name="Bundesliga",
        competition_level="elite",
        desired_names=("Bundesliga",),
        fallback_competition_id="82",
        fallback_season_id="25646",
    ),
    LeagueSpec(
        name="Eredivisie",
        competition_level="top_flight",
        desired_names=("Eredivisie",),
        fallback_competition_id="72",
        fallback_season_id="25597",
    ),
    LeagueSpec(
        name="Championship",
        competition_level="second_tier",
        desired_names=("Championship",),
        fallback_competition_id="9",
        fallback_season_id="25648",
    ),
    LeagueSpec(
        name="La Liga 2",
        competition_level="second_tier",
        desired_names=("La Liga 2", "LaLiga2", "Segunda Division"),
        competition_id="567",
        fallback_competition_id="567",
        fallback_season_id="25673",
    ),
    LeagueSpec(
        name="Chance Liga",
        competition_level="top_flight",
        desired_names=("Chance Liga", "Fortuna Liga"),
        competition_id="262",
        fallback_competition_id="262",
        fallback_season_id="27984",
    ),
    LeagueSpec(
        name="Brasileiro Serie A",
        competition_level="top_flight",
        # SportMonks calls this "Serie A" (id 648) — collides with Italy's
        # Serie A (id 384); resolve by explicit id, never by name.
        desired_names=(),
        competition_id="648",
        fallback_competition_id="648",
        fallback_season_id="26763",
    ),
    LeagueSpec(
        name="Liga Profesional de Futbol",
        competition_level="top_flight",
        desired_names=("Liga Profesional de Futbol", "Liga Profesional"),
        competition_id="636",
        fallback_competition_id="636",
        fallback_season_id="26808",
    ),
    LeagueSpec(
        name="Admiral Bundesliga",
        competition_level="top_flight",
        desired_names=("Admiral Bundesliga",),
        competition_id="181",
        # Current season (28003, 2025/26) has no squads yet; pin to the prior
        # season (25653) which has clubs until 2025/26 populates.
        season_id="25653",
        fallback_competition_id="181",
        fallback_season_id="25653",
    ),
    LeagueSpec(
        name="Premiership",
        competition_level="top_flight",
        desired_names=("Premiership", "Scottish Premiership"),
        fallback_competition_id="501",
        fallback_season_id="25598",
    ),
    LeagueSpec(
        name="Liga Portugal",
        competition_level="top_flight",
        desired_names=("Liga Portugal",),
        fallback_competition_id="462",
        fallback_season_id="25745",
    ),
    LeagueSpec(
        name="Super Lig",
        competition_level="top_flight",
        desired_names=("Super Lig", "Süper Lig"),
        country_id=_TURKEY_COUNTRY_ID,
        target_club_names=(
            "Alanyaspor",
            "Antalyaspor",
            "Basaksehir",
            "Besiktas",
            "Eyupspor",
            "Fatih Karagumruk",
            "Fenerbahce",
            "Galatasaray",
            "Gaziantep",
            "Genclerbirligi",
            "Goztepe",
            "Kasimpasa",
            "Kayserispor",
            "Kocaelispor",
            "Konyaspor",
            "Rizespor",
            "Samsunspor",
            "Trabzonspor",
        ),
        manual_league_key="super-lig",
    ),
    LeagueSpec(
        name="NPFL",
        competition_level="top_flight",
        desired_names=(),
        competition_id="1475",
        fallback_competition_id="1475",
        fallback_season_id="28292",
    ),
    LeagueSpec(
        name="South Africa Premier League",
        competition_level="top_flight",
        desired_names=(),
        competition_id="806",
        fallback_competition_id="806",
        fallback_season_id="28123",
    ),
    LeagueSpec(
        name="Egypt Premier League",
        competition_level="top_flight",
        desired_names=(),
        competition_id="830",
        fallback_competition_id="830",
        fallback_season_id="28307",
    ),
    LeagueSpec(
        name="Ivory Coast Ligue 1",
        competition_level="top_flight",
        desired_names=(),
        competition_id="827",
        # Live current season (28362, 2026/27) has no squads yet; pin to the
        # prior season (26390) which has clubs until 2026/27 populates.
        season_id="26390",
        fallback_competition_id="827",
        fallback_season_id="26390",
    ),
    LeagueSpec(
        name="Ghana Premier League",
        competition_level="top_flight",
        desired_names=(),
        competition_id="836",
        fallback_competition_id="836",
        fallback_season_id="27906",
    ),
    LeagueSpec(
        name="Botola Pro",
        competition_level="top_flight",
        desired_names=(),
        competition_id="860",
        # Live current season (28647, 2026/27) has no squads yet; pin to the
        # prior season (26027) which has clubs until 2026/27 populates.
        season_id="26027",
        fallback_competition_id="860",
        fallback_season_id="26027",
    ),
    LeagueSpec(
        name="Senegal Ligue 1",
        competition_level="top_flight",
        desired_names=(),
        competition_id="875",
        fallback_competition_id="875",
        fallback_season_id="28640",
    ),
    LeagueSpec(
        name="Liga BetPlay",
        competition_level="top_flight",
        desired_names=(),
        competition_id="672",
        fallback_competition_id="672",
        fallback_season_id="26881",
    ),
    LeagueSpec(
        name="Liga Pro",
        competition_level="top_flight",
        desired_names=(),
        competition_id="696",
        fallback_competition_id="696",
        fallback_season_id="27249",
    ),
    LeagueSpec(
        name="Primera Division Uruguay",
        competition_level="top_flight",
        desired_names=(),
        competition_id="770",
        fallback_competition_id="770",
        fallback_season_id="27710",
    ),
    LeagueSpec(
        name="Major League Soccer",
        competition_level="top_flight",
        desired_names=(),
        competition_id="779",
        fallback_competition_id="779",
        fallback_season_id="26720",
    ),
    LeagueSpec(
        name="Saudi Pro League",
        competition_level="top_flight",
        desired_names=(),
        competition_id="944",
        fallback_competition_id="944",
        fallback_season_id="27951",
    ),
    LeagueSpec(
        name="Brasileiro Serie B",
        competition_level="second_tier",
        # SportMonks calls this "Serie B" (id 651) — collides with Italy's
        # Serie B (id 387); resolve by explicit id, never by name.
        desired_names=(),
        competition_id="651",
        fallback_competition_id="651",
        fallback_season_id="27198",
    ),
    LeagueSpec(
        name="Serie B",
        competition_level="second_tier",
        # SportMonks calls this "Serie B" (id 387) — collides with Brazil's
        # Serie B (id 651); resolve by explicit id, never by name.
        desired_names=(),
        competition_id="387",
        fallback_competition_id="387",
        fallback_season_id="28379",
    ),
    LeagueSpec(
        name="Ligue 2",
        competition_level="second_tier",
        desired_names=(),
        competition_id="304",
        fallback_competition_id="304",
        fallback_season_id="28105",
    ),
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh target real-player leagues from SportMonks and persist real player photos."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument(
        "--report-path",
        default=str((REPO_ROOT / "tmp" / "target-league-real-player-refresh-report.json").resolve()),
        help="Path for the JSON execution report.",
    )
    parser.add_argument(
        "--provider-timeout-seconds",
        type=int,
        default=60,
        help="SportMonks request timeout in seconds.",
    )
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=0,
        help="Optional pause between club writes in milliseconds.",
    )
    parser.add_argument(
        "--state-path",
        default=str((REPO_ROOT / "tmp" / "target-league-refresh" / "state.json").resolve()),
        help="Path for the refresh checkpoint state file.",
    )
    parser.add_argument(
        "--fallback-archive-path",
        default=str((REPO_ROOT / "2nd.zip").resolve()),
        help="Optional local 2nd.zip fallback archive for clubs missing from SportMonks coverage.",
    )
    parser.add_argument(
        "--league",
        dest="leagues",
        action="append",
        default=None,
        help="Optional league name filter. Repeat to target multiple configured leagues.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    _configure_logging()
    _ensure_required_secrets()
    os.environ.setdefault("GTE_REAL_PLAYER_MAPPING_AUTO_CREATE_MISSING_ENTITIES", "1")

    settings = load_settings(
        environ={
            **os.environ,
            "DATABASE_URL": args.database_url,
            "GTE_DATABASE_URL": args.database_url,
            "GTE_PROVIDER_TIMEOUT_SECONDS": str(max(int(args.provider_timeout_seconds), 1)),
        }
    )
    engine = create_database_engine(args.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)

    adapter = SportMonksAdapter(settings=settings)
    ingestion_service = RealPlayerIngestionService(
        session_factory=session_factory,
        settings=settings,
    )

    started_at = _now_iso()
    report_path = Path(args.report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    state_path = Path(args.state_path).resolve()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    fallback_archive_path = _resolve_fallback_archive_path(args.fallback_archive_path)

    try:
        selected_league_specs = _select_league_specs(args.leagues)
        league_targets = _resolve_league_targets(adapter, selected_league_specs)
        existing_photo_map = _load_existing_photo_map(session_factory)
        existing_profile_snapshots = _load_existing_profile_snapshots(session_factory)
        resume_state = _load_resume_state(state_path)
        run_report = _run_refresh(
            adapter=adapter,
            ingestion_service=ingestion_service,
            session_factory=session_factory,
            league_targets=league_targets,
            existing_photo_map=existing_photo_map,
            existing_profile_snapshots=existing_profile_snapshots,
            pause_ms=max(int(args.pause_ms), 0),
            run_stamp=datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ"),
            state_path=state_path,
            resume_state=resume_state,
            fallback_archive_path=fallback_archive_path,
        )
        verification = _verification_snapshot(session_factory)
        payload = {
            "status": "success",
            "started_at": started_at,
            "completed_at": _now_iso(),
            "database_url": args.database_url,
            "provider_timeout_seconds": max(int(args.provider_timeout_seconds), 1),
            "state_path": str(state_path),
            "selected_leagues": [spec.name for spec in selected_league_specs],
            "run": run_report,
            "verification": verification,
        }
        _clear_resume_state(state_path)
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        payload = {
            "status": "error",
            "started_at": started_at,
            "completed_at": _now_iso(),
            "database_url": args.database_url,
            "state_path": str(state_path),
            "error": str(exc),
        }
        report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 1
    finally:
        engine.dispose()


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )


def _ensure_required_secrets() -> None:
    os.environ.setdefault("GTE_AUTH_SECRET", _FALLBACK_AUTH_SECRET)
    os.environ.setdefault("GTE_MEDIA_SIGNING_SECRET", _FALLBACK_MEDIA_SECRET)


def _select_league_specs(requested_names: list[str] | None) -> tuple[LeagueSpec, ...]:
    if not requested_names:
        return _TARGET_LEAGUES

    requested_keys = {_fold_text(name) for name in requested_names if _fold_text(name)}
    selected: list[LeagueSpec] = []
    for spec in _TARGET_LEAGUES:
        spec_keys = {_fold_text(spec.name), *(_fold_text(name) for name in spec.desired_names)}
        if requested_keys & {key for key in spec_keys if key}:
            selected.append(spec)

    if not selected:
        requested_display = ", ".join(sorted(name for name in requested_names if str(name or "").strip()))
        raise ValueError(f"No configured league targets matched: {requested_display}")
    return tuple(selected)


def _run_refresh(
    *,
    adapter: SportMonksAdapter,
    ingestion_service: RealPlayerIngestionService,
    session_factory,
    league_targets: list[dict[str, Any]],
    existing_photo_map: dict[str, str],
    existing_profile_snapshots: dict[str, dict[str, Any]],
    pause_ms: int,
    run_stamp: str,
    state_path: Path,
    resume_state: dict[str, Any],
    fallback_archive_path: Path | None,
) -> dict[str, Any]:
    completed_club_keys = set(_string_list(resume_state.get("completed_club_keys")))
    overall = {
        "target_league_count": len(league_targets),
        "target_club_count": 0,
        "resumed_completed_club_count": len(completed_club_keys),
        "payloads_seen": 0,
        "payloads_selected": 0,
        "payloads_skipped_existing_photo": 0,
        "payloads_skipped_missing_photo": 0,
        "payloads_dropped_after_validation": 0,
        "players_processed": 0,
        "players_created": 0,
        "players_updated": 0,
        "club_batches_written": 0,
        "club_batches_blocked": 0,
        "player_level_fallback_writes": 0,
        "player_level_failures": 0,
        "leagues": [],
    }
    current_timestamp = datetime.now(UTC).isoformat()

    for league_target in league_targets:
        league_name = str(league_target["league_name"])
        league_key = str(league_target["league_key"])
        competition_level = str(league_target["competition_level"])
        clubs = list(league_target["clubs"])
        overall["target_club_count"] += len(clubs)
        league_report = {
            "league_name": league_name,
            "league_key": league_key,
            "club_count": len(clubs),
            "missing_target_club_names": list(league_target.get("missing_target_club_names") or []),
            "payloads_seen": 0,
            "payloads_selected": 0,
            "payloads_skipped_existing_photo": 0,
            "payloads_skipped_missing_photo": 0,
            "payloads_dropped_after_validation": 0,
            "players_processed": 0,
            "players_created": 0,
            "players_updated": 0,
            "club_batches_written": 0,
            "club_batches_blocked": 0,
            "player_level_fallback_writes": 0,
            "player_level_failures": 0,
            "clubs": [],
        }
        logger.info("refresh league=%s clubs=%s", league_name, len(clubs))

        for club in clubs:
            club_state_key = _club_state_key(league_key=league_key, club_id=club["id"])
            if club_state_key in completed_club_keys:
                logger.info(
                    "skipping completed club league=%s club=%s club_id=%s",
                    league_name,
                    club["name"],
                    club["id"],
                )
                continue

            _write_resume_state(
                state_path,
                {
                    "run_stamp": run_stamp,
                    "updated_at": _now_iso(),
                    "current_league_name": league_name,
                    "current_league_key": league_key,
                    "current_club_name": club["name"],
                    "current_club_id": club["id"],
                    "completed_club_keys": sorted(completed_club_keys),
                },
            )
            payloads = _build_player_payloads(
                adapter=adapter,
                league_name=league_name,
                league_key=league_key,
                competition_level=competition_level,
                club=club,
                current_timestamp=current_timestamp,
                existing_profile_snapshots=existing_profile_snapshots,
            )
            league_report["payloads_seen"] += len(payloads)
            overall["payloads_seen"] += len(payloads)

            selected_payloads = list(payloads)
            skipped_existing_photo = 0
            skipped_missing_photo = 0

            league_report["payloads_selected"] += len(selected_payloads)
            league_report["payloads_skipped_existing_photo"] += skipped_existing_photo
            league_report["payloads_skipped_missing_photo"] += skipped_missing_photo
            overall["payloads_selected"] += len(selected_payloads)
            overall["payloads_skipped_existing_photo"] += skipped_existing_photo
            overall["payloads_skipped_missing_photo"] += skipped_missing_photo

            club_report = {
                "club_name": club["name"],
                "club_id": club["id"],
                "payloads_seen": len(payloads),
                "payloads_selected": len(selected_payloads),
                "payloads_skipped_existing_photo": skipped_existing_photo,
                "payloads_skipped_missing_photo": skipped_missing_photo,
                "payloads_dropped_after_validation": 0,
                "status": "skipped" if not selected_payloads else "pending",
                "players_processed": 0,
                "players_created": 0,
                "players_updated": 0,
                "player_level_fallback_writes": 0,
                "player_level_failures": 0,
                "errors": [],
            }

            if not selected_payloads:
                league_report["clubs"].append(club_report)
                continue

            _write_club_payloads(
                ingestion_service=ingestion_service,
                existing_photo_map=existing_photo_map,
                league_name=league_name,
                league_key=league_key,
                club_name=club["name"],
                club_id=club["id"],
                payloads=selected_payloads,
                club_report=club_report,
                league_report=league_report,
                overall=overall,
                run_stamp=run_stamp,
            )
            if pause_ms > 0:
                time.sleep(pause_ms / 1000)
            league_report["clubs"].append(club_report)
            completed_club_keys.add(club_state_key)
            _write_resume_state(
                state_path,
                {
                    "run_stamp": run_stamp,
                    "updated_at": _now_iso(),
                    "current_league_name": league_name,
                    "current_league_key": league_key,
                    "current_club_name": club["name"],
                    "current_club_id": club["id"],
                    "completed_club_keys": sorted(completed_club_keys),
                    "last_completed_club_name": club["name"],
                    "last_completed_club_id": club["id"],
                },
            )
            logger.info(
                "club finished league=%s club=%s status=%s processed=%s created=%s updated=%s failures=%s",
                league_name,
                club["name"],
                club_report["status"],
                club_report["players_processed"],
                club_report["players_created"],
                club_report["players_updated"],
                club_report["player_level_failures"],
            )

        missing_targets = list(league_report.get("missing_target_club_names") or [])
        if missing_targets and fallback_archive_path is not None:
            recovered_target_names: list[str] = []
            fallback_payload_groups = _build_second_zip_fallback_payload_groups(
                archive_path=fallback_archive_path,
                league_name=league_name,
                competition_level=competition_level,
                target_club_names=missing_targets,
                current_timestamp=current_timestamp,
            )
            for target_name in missing_targets:
                fallback_group = fallback_payload_groups.get(target_name)
                if not fallback_group:
                    continue
                recovered_target_names.append(target_name)
                fallback_club_name = str(fallback_group["club_name"])
                fallback_payloads = list(fallback_group["payloads"])
                club_report = {
                    "club_name": fallback_club_name,
                    "club_id": f"2ndzip:{_compact_fold_text(fallback_club_name)}",
                    "payloads_seen": len(fallback_payloads),
                    "payloads_selected": len(fallback_payloads),
                    "payloads_skipped_existing_photo": 0,
                    "payloads_skipped_missing_photo": 0,
                    "payloads_dropped_after_validation": 0,
                    "status": "pending",
                    "players_processed": 0,
                    "players_created": 0,
                    "players_updated": 0,
                    "player_level_fallback_writes": 0,
                    "player_level_failures": 0,
                    "errors": [],
                    "source": "transfermarkt_2nd_zip",
                    "target_name": target_name,
                }
                league_report["payloads_seen"] += len(fallback_payloads)
                league_report["payloads_selected"] += len(fallback_payloads)
                overall["payloads_seen"] += len(fallback_payloads)
                overall["payloads_selected"] += len(fallback_payloads)
                _write_club_payloads(
                    ingestion_service=ingestion_service,
                    existing_photo_map=existing_photo_map,
                    league_name=league_name,
                    league_key=league_key,
                    club_name=fallback_club_name,
                    club_id=club_report["club_id"],
                    payloads=fallback_payloads,
                    club_report=club_report,
                    league_report=league_report,
                    overall=overall,
                    run_stamp=run_stamp,
                )
                league_report["clubs"].append(club_report)

            if recovered_target_names:
                league_report["fallback_archive_path"] = str(fallback_archive_path)
                league_report["fallback_archive_recovered_club_names"] = recovered_target_names
                league_report["missing_target_club_names"] = [
                    name for name in missing_targets if name not in set(recovered_target_names)
                ]

        overall["leagues"].append(league_report)

    return overall


def _apply_write_report(
    target: dict[str, Any],
    league_report: dict[str, Any],
    overall: dict[str, Any],
    write_report,
) -> None:
    processed = int(write_report.players_processed)
    created = int(write_report.players_created)
    updated = int(write_report.players_updated)
    target["players_processed"] += processed
    target["players_created"] += created
    target["players_updated"] += updated
    league_report["players_processed"] += processed
    league_report["players_created"] += created
    league_report["players_updated"] += updated
    overall["players_processed"] += processed
    overall["players_created"] += created
    overall["players_updated"] += updated


def _write_club_payloads(
    *,
    ingestion_service: RealPlayerIngestionService,
    existing_photo_map: dict[str, str],
    league_name: str,
    league_key: str,
    club_name: str,
    club_id: str,
    payloads: list[dict[str, Any]],
    club_report: dict[str, Any],
    league_report: dict[str, Any],
    overall: dict[str, Any],
    run_stamp: str,
) -> None:
    try:
        write_report = _write_payload_batch(
            ingestion_service=ingestion_service,
            payloads=payloads,
            batch_id=f"target-refresh:{run_stamp}:{league_key}:{club_id}",
            ingestion_source_version=f"target-refresh:{run_stamp}:{league_key}:{club_id}",
        )
        dropped_count = int(getattr(write_report, "_dropped_payload_count", 0))
        club_report["payloads_dropped_after_validation"] += dropped_count
        league_report["payloads_dropped_after_validation"] += dropped_count
        overall["payloads_dropped_after_validation"] += dropped_count
        _apply_write_report(club_report, league_report, overall, write_report)
        club_report["status"] = "written"
        league_report["club_batches_written"] += 1
        overall["club_batches_written"] += 1
        for payload in payloads:
            photo_url = _normalized_photo_url(payload.get("photo_url"))
            if photo_url:
                existing_photo_map[str(payload["source_player_key"])] = photo_url
    except RealPlayerBatchBlockedError as exc:
        league_report["club_batches_blocked"] += 1
        overall["club_batches_blocked"] += 1
        club_report["status"] = "blocked"
        club_report["errors"].append(str(exc))
        logger.warning(
            "club batch blocked league=%s club=%s players=%s falling back to player writes",
            league_name,
            club_name,
            len(payloads),
        )
        for payload in payloads:
            try:
                write_report = _write_payload_batch(
                    ingestion_service=ingestion_service,
                    payloads=[payload],
                    batch_id=f"target-refresh:{run_stamp}:{league_key}:{club_id}:{payload['source_player_key']}",
                    ingestion_source_version=(
                        f"target-refresh:{run_stamp}:{league_key}:{club_id}:{payload['source_player_key']}"
                    ),
                )
                dropped_count = int(getattr(write_report, "_dropped_payload_count", 0))
                club_report["payloads_dropped_after_validation"] += dropped_count
                league_report["payloads_dropped_after_validation"] += dropped_count
                overall["payloads_dropped_after_validation"] += dropped_count
                _apply_write_report(club_report, league_report, overall, write_report)
                club_report["status"] = "partial"
                club_report["player_level_fallback_writes"] += 1
                league_report["player_level_fallback_writes"] += 1
                overall["player_level_fallback_writes"] += 1
                photo_url = _normalized_photo_url(payload.get("photo_url"))
                if photo_url:
                    existing_photo_map[str(payload["source_player_key"])] = photo_url
            except Exception as player_exc:  # pragma: no cover - live data dependent
                club_report["player_level_failures"] += 1
                league_report["player_level_failures"] += 1
                overall["player_level_failures"] += 1
                club_report["errors"].append(f"{payload['source_player_key']}: {player_exc}")
                logger.warning(
                    "player write failed league=%s club=%s player=%s error=%s",
                    league_name,
                    club_name,
                    payload["source_player_key"],
                    player_exc,
                )


def _write_payload_batch(
    *,
    ingestion_service: RealPlayerIngestionService,
    payloads: list[dict[str, Any]],
    batch_id: str,
    ingestion_source_version: str,
):
    valid_payloads, dropped_payload_keys = _validated_payloads(payloads)
    if not valid_payloads:
        raise ValueError(f"No valid payloads remained for batch '{batch_id}'.")
    if dropped_payload_keys:
        logger.warning(
            "dropping invalid payloads batch_id=%s source_keys=%s",
            batch_id,
            ",".join(dropped_payload_keys),
        )
    request = RealPlayerIngestionRequest.model_validate(
        {
            "mode": "batch_import",
            "ingestion_batch_id": batch_id,
            "ingestion_source_version": ingestion_source_version,
            "as_of": _now_iso(),
            "players": valid_payloads,
        }
    )
    write_report = ingestion_service.write_batch(request)
    setattr(write_report, "_dropped_payload_count", len(dropped_payload_keys))
    return write_report


def _build_player_payloads(
    *,
    adapter: SportMonksAdapter,
    league_name: str,
    league_key: str,
    competition_level: str,
    club: dict[str, Any],
    current_timestamp: str,
    existing_profile_snapshots: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_players = _provider_call(
        f"fetch players league={league_name} club={club['name']} club_id={club['id']}",
        adapter.fetch_players,
        str(club["id"]),
    )
    payloads: list[dict[str, Any]] = []
    seen_keys: set[str] = set()
    for player in raw_players:
        player_id = _required_text(player.get("id"))
        canonical_name = _required_text(player.get("name") or player.get("displayName"))
        if player_id in seen_keys or not canonical_name:
            continue
        seen_keys.add(player_id)
        existing = existing_profile_snapshots.get(player_id, {})
        display_name = _clean_text(player.get("displayName")) or canonical_name
        common_name = _clean_text(player.get("commonName"))
        detailed_position = _clean_text(player.get("detailedPosition"))
        position = _clean_text(player.get("position"))
        photo_url = _normalized_photo_url(player.get("photo_url") or player.get("imagePath"))
        height_cm = _normalize_height_cm(player.get("height"))
        if height_cm is None:
            height_cm = _normalize_height_cm(existing.get("height_cm"))
        weight_kg = _normalize_weight_kg(player.get("weight"))
        if weight_kg is None:
            weight_kg = _normalize_weight_kg(existing.get("weight_kg"))
        secondary_positions: list[str] = []
        if position and detailed_position and position != detailed_position:
            secondary_positions.append(position)
        elif isinstance(existing.get("secondary_positions"), list):
            secondary_positions = [value for value in existing["secondary_positions"] if isinstance(value, str)]
        known_aliases = [alias for alias in (common_name, display_name) if alias and alias != canonical_name]
        payloads.append(
            {
                "source_name": "sportmonks",
                "source_player_key": player_id,
                "canonical_name": canonical_name,
                "display_name": display_name,
                "known_aliases": _dedupe_strings(known_aliases),
                "nationality": _clean_text(player.get("nationality") or player.get("country")),
                "nationality_code": _clean_text(player.get("nationalityCode")),
                "date_of_birth": _clean_text(player.get("dateOfBirth")),
                "dominant_foot": existing.get("dominant_foot"),
                "primary_position": detailed_position or position,
                "secondary_positions": secondary_positions,
                "current_real_world_club": _required_text(club["name"]),
                "current_real_world_club_key": _required_text(club["id"]),
                "current_real_world_league": league_name,
                "current_real_world_league_key": league_key,
                "competition_level": competition_level,
                "height_cm": height_cm,
                "weight_kg": weight_kg,
                "appearances": existing.get("appearances"),
                "minutes_played": existing.get("minutes_played"),
                "goals": existing.get("goals"),
                "assists": existing.get("assists"),
                "clean_sheets": existing.get("clean_sheets"),
                "injury_status": existing.get("injury_status"),
                "current_market_reference_value": existing.get("current_market_reference_value"),
                "market_reference_currency": existing.get("market_reference_currency"),
                "photo_url": photo_url,
                "source_last_refreshed_at": current_timestamp,
            }
        )
    return payloads


def _validated_payloads(payloads: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    valid_payloads: list[dict[str, Any]] = []
    dropped_payload_keys: list[str] = []
    for payload in payloads:
        sanitized = _sanitize_payload(payload)
        try:
            RealPlayerSeedInput.model_validate(sanitized)
        except Exception as exc:
            source_key = str(payload.get("source_player_key") or payload.get("canonical_name") or "<unknown>")
            logger.warning("invalid payload source_key=%s error=%s", source_key, exc)
            dropped_payload_keys.append(source_key)
            continue
        valid_payloads.append(sanitized)
    return valid_payloads, dropped_payload_keys


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    sanitized["height_cm"] = _normalize_height_cm(sanitized.get("height_cm"))
    sanitized["weight_kg"] = _normalize_weight_kg(sanitized.get("weight_kg"))
    sanitized["appearances"] = _normalize_non_negative_int(sanitized.get("appearances"))
    sanitized["minutes_played"] = _normalize_non_negative_int(sanitized.get("minutes_played"))
    sanitized["goals"] = _normalize_non_negative_int(sanitized.get("goals"))
    sanitized["assists"] = _normalize_non_negative_int(sanitized.get("assists"))
    sanitized["clean_sheets"] = _normalize_non_negative_int(sanitized.get("clean_sheets"))
    sanitized["current_market_reference_value"] = _normalize_non_negative_float(
        sanitized.get("current_market_reference_value")
    )
    return sanitized


def _provider_call(description: str, func, *args, **kwargs):
    last_error: Exception | None = None
    for attempt in range(1, _PROVIDER_RETRY_ATTEMPTS + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:  # pragma: no cover - live network dependent
            last_error = exc
            if attempt >= _PROVIDER_RETRY_ATTEMPTS:
                break
            delay_seconds = min(_PROVIDER_RETRY_BASE_SECONDS * (2 ** (attempt - 1)), 60.0)
            logger.warning(
                "provider call failed description=%s attempt=%s/%s delay_seconds=%s error=%s",
                description,
                attempt,
                _PROVIDER_RETRY_ATTEMPTS,
                delay_seconds,
                exc,
            )
            time.sleep(delay_seconds)
    assert last_error is not None
    raise last_error


def _load_resume_state(state_path: Path) -> dict[str, Any]:
    if not state_path.exists():
        return {}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_resume_state(state_path: Path, payload: dict[str, Any]) -> None:
    temp_path = state_path.with_suffix(f"{state_path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    temp_path.replace(state_path)


def _clear_resume_state(state_path: Path) -> None:
    try:
        state_path.unlink(missing_ok=True)
    except OSError:
        return


def _club_state_key(*, league_key: str, club_id: str) -> str:
    return f"{league_key}:{club_id}"


def _resolve_league_targets(adapter: SportMonksAdapter, specs: tuple[LeagueSpec, ...]) -> list[dict[str, Any]]:
    competitions_by_name = {}
    competitions_by_id: dict[str, dict[str, Any]] = {}
    for competition in _provider_call("fetch competitions", adapter.fetch_competitions):
        competition_name = _fold_text(competition.get("name"))
        if competition_name:
            competitions_by_name[competition_name] = competition
        competition_pk = _required_text(competition.get("id"))
        if competition_pk:
            competitions_by_id[competition_pk] = competition

    resolved: list[dict[str, Any]] = []
    for spec in specs:
        if spec.country_id:
            resolved.append(_resolve_manual_country_league(adapter, spec))
            continue

        competition = None
        if spec.competition_id:
            # Explicit id wins — bypass name matching to avoid cross-country collisions.
            competition = competitions_by_id.get(spec.competition_id)
        else:
            for desired_name in spec.desired_names:
                competition = competitions_by_name.get(_fold_text(desired_name))
                if competition is not None:
                    break
        competition_id = _required_text(
            (competition or {}).get("id") or spec.competition_id or spec.fallback_competition_id,
        )
        season_id = _required_text(
            spec.season_id
            or ((competition or {}).get("currentSeason") or {}).get("id")
            or spec.fallback_season_id,
        )
        clubs = [
            {"id": _required_text(club.get("id")), "name": _required_text(club.get("name"))}
            for club in _provider_call(
                f"fetch clubs league={spec.name} competition_id={competition_id} season_id={season_id}",
                adapter.fetch_clubs,
                competition_id,
                season_id,
            )
            if _required_text(club.get("id")) and _required_text(club.get("name"))
        ]
        resolved.append(
            {
                "league_name": spec.name,
                "league_key": competition_id,
                "competition_level": spec.competition_level,
                "clubs": clubs,
            }
        )
    return resolved


def _resolve_manual_country_league(adapter: SportMonksAdapter, spec: LeagueSpec) -> dict[str, Any]:
    raw_teams = _provider_call(
        f"fetch country teams country_id={spec.country_id}",
        adapter._iterate_pages,  # noqa: SLF001 - internal provider paging helper is fit for this script.
        f"/teams/countries/{spec.country_id}",
        params={"include": "country;venue", "per_page": 50},
    )
    teams = [
        {"id": _required_text(team.get("id")), "name": _required_text(team.get("name"))}
        for team in raw_teams
        if _required_text(team.get("id")) and _required_text(team.get("name"))
    ]
    matched_clubs: list[dict[str, Any]] = []
    missing_targets: list[str] = []
    for target_name in spec.target_club_names:
        matched = _match_team_name(target_name, teams)
        if matched is None:
            matched = _search_manual_team(adapter, target_name)
        if matched is None:
            missing_targets.append(target_name)
            continue
        matched_clubs.append(matched)
    if not matched_clubs:
        raise RuntimeError("Could not match any SportMonks Turkey teams for the manual Super Lig refresh.")
    return {
        "league_name": spec.name,
        "league_key": _required_text(spec.manual_league_key),
        "competition_level": spec.competition_level,
        "clubs": _dedupe_clubs(matched_clubs),
        "missing_target_club_names": sorted(missing_targets),
    }


def _match_team_name(target_name: str, teams: list[dict[str, Any]]) -> dict[str, Any] | None:
    aliases = tuple(_fold_text(alias) for alias in _MANUAL_TEAM_MATCH_ALIASES.get(target_name, (target_name,)))
    compact_aliases = tuple(
        _compact_fold_text(alias) for alias in _MANUAL_TEAM_MATCH_ALIASES.get(target_name, (target_name,))
    )
    best_team: dict[str, Any] | None = None
    best_score: tuple[int, int, int] | None = None
    for team in teams:
        folded_name = _fold_text(team["name"])
        compact_name = _compact_fold_text(team["name"])
        if not folded_name:
            continue
        score: tuple[int, int, int] | None = None
        for alias, compact_alias in zip(aliases, compact_aliases, strict=False):
            alias_length = max(len(compact_alias), len(alias.replace(" ", "")))
            candidate_score: tuple[int, int, int] | None = None
            if folded_name == alias:
                candidate_score = (0, -alias_length, len(folded_name))
            elif compact_name == compact_alias:
                candidate_score = (0, -alias_length, len(compact_name))
            elif f" {alias} " in f" {folded_name} ":
                candidate_score = (1, -alias_length, len(folded_name))
            elif compact_alias and compact_alias in compact_name:
                candidate_score = (1, -alias_length, len(compact_name))
            if candidate_score is not None and (score is None or candidate_score < score):
                score = candidate_score
        if score is None:
            continue
        if best_score is None or score < best_score:
            best_score = score
            best_team = team
    return best_team


def _search_manual_team(adapter: SportMonksAdapter, target_name: str) -> dict[str, Any] | None:
    for search_term in _MANUAL_TEAM_SEARCH_TERMS.get(target_name, (target_name,)):
        payload = _provider_call(
            f"search team target={target_name} search_term={search_term}",
            adapter._get,  # noqa: SLF001 - direct team search is needed for incomplete country-team coverage.
            f"/teams/search/{quote(search_term)}",
            params={"include": "country;venue"},
        )
        teams = [
            {"id": _required_text(team.get("id")), "name": _required_text(team.get("name"))}
            for team in payload.get("data") or []
            if _required_text(team.get("id")) and _required_text(team.get("name"))
        ]
        matched = _match_team_name(target_name, teams)
        if matched is not None:
            return matched
    return None


def _dedupe_clubs(clubs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for club in clubs:
        deduped[str(club["id"])] = club
    return list(deduped.values())


def _build_second_zip_fallback_payload_groups(
    *,
    archive_path: Path,
    league_name: str,
    competition_level: str,
    target_club_names: list[str],
    current_timestamp: str,
) -> dict[str, dict[str, Any]]:
    reader = TransfermarktSecondZipReader(archive_path)
    grouped_payloads: dict[str, list[dict[str, Any]]] = {}
    for source_item in reader.iter_source_items():
        raw_payload = source_item.raw_payload
        if not isinstance(raw_payload, dict):
            continue
        payload = dict(raw_payload)
        if _required_text(payload.get("current_real_world_league_key")) != "TR1":
            continue
        club_name = _required_text(payload.get("current_real_world_club"))
        if not club_name:
            continue
        payload["current_real_world_league"] = league_name
        payload["competition_level"] = competition_level
        payload["source_last_refreshed_at"] = current_timestamp
        grouped_payloads.setdefault(club_name, []).append(payload)

    archive_teams = [{"id": name, "name": name} for name in grouped_payloads]
    results: dict[str, dict[str, Any]] = {}
    for target_name in target_club_names:
        matched_team = _match_team_name(target_name, archive_teams)
        if matched_team is None:
            continue
        matched_name = str(matched_team["name"])
        results[target_name] = {
            "club_name": matched_name,
            "payloads": grouped_payloads.get(matched_name, []),
        }
    return results


def _load_existing_photo_map(session_factory) -> dict[str, str]:
    sql = text("""
        select source_player_key, metadata_json
        from real_player_profiles
        where source_name = 'sportmonks'
        """)
    existing: dict[str, str] = {}
    with session_factory() as session:
        for source_player_key, metadata_json in session.execute(sql):
            if not source_player_key or not metadata_json:
                continue
            metadata = _json_object(metadata_json)
            photo_url = _normalized_photo_url(
                metadata.get("photo_url")
                or (
                    (metadata.get("image") or {}).get("source_url") if isinstance(metadata.get("image"), dict) else None
                )
            )
            if photo_url:
                existing[str(source_player_key)] = photo_url
    return existing


def _load_existing_profile_snapshots(session_factory) -> dict[str, dict[str, Any]]:
    sql = text("""
        select
            source_player_key,
            dominant_foot,
            secondary_positions_json,
            weight_kg,
            height_cm,
            appearances,
            minutes_played,
            goals,
            assists,
            clean_sheets,
            injury_status,
            current_market_reference_value,
            market_reference_currency
        from real_player_profiles
        where source_name = 'sportmonks'
        """)
    snapshots: dict[str, dict[str, Any]] = {}
    with session_factory() as session:
        for row in session.execute(sql):
            source_player_key = _required_text(row[0])
            if source_player_key is None:
                continue
            snapshots[source_player_key] = {
                "dominant_foot": row[1],
                "secondary_positions": _json_array(row[2]),
                "weight_kg": row[3],
                "height_cm": row[4],
                "appearances": row[5],
                "minutes_played": row[6],
                "goals": row[7],
                "assists": row[8],
                "clean_sheets": row[9],
                "injury_status": row[10],
                "current_market_reference_value": row[11],
                "market_reference_currency": row[12],
            }
    return snapshots


def _verification_snapshot(session_factory) -> dict[str, Any]:
    verification = {
        "real_player_profiles": 0,
        "player_share_markets": 0,
        "ingestion_player_image_metadata": 0,
        "target_league_photo_counts": [],
    }
    with session_factory() as session:
        verification["real_player_profiles"] = int(
            session.execute(text("select count(*) from real_player_profiles")).scalar_one()
        )
        verification["player_share_markets"] = int(
            session.execute(text("select count(*) from player_share_markets")).scalar_one()
        )
        verification["ingestion_player_image_metadata"] = int(
            session.execute(text("select count(*) from ingestion_player_image_metadata")).scalar_one()
        )
        league_names = [spec.name for spec in _TARGET_LEAGUES]
        placeholders = ", ".join(f":league_{index}" for index, _ in enumerate(league_names))
        params = {f"league_{index}": league_name for index, league_name in enumerate(league_names)}
        rows = session.execute(
            text(f"""
                select
                    current_league_name,
                    count(*) as total_profiles,
                    sum(
                        case
                            when metadata_json ->> 'photo_url' is not null
                                or metadata_json -> 'image' ->> 'source_url' is not null
                            then 1
                            else 0
                        end
                    ) as profiles_with_photo
                from real_player_profiles
                where current_league_name in ({placeholders})
                group by current_league_name
                order by current_league_name
                """),
            params,
        )
        verification["target_league_photo_counts"] = [
            {
                "league_name": row[0],
                "total_profiles": int(row[1] or 0),
                "profiles_with_photo": int(row[2] or 0),
            }
            for row in rows
        ]
    return verification


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    return {}


def _json_array(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return []
        return list(parsed) if isinstance(parsed, list) else []
    return []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalized_photo_url(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_height_cm(value: Any) -> int | None:
    parsed = _parse_int(value)
    if parsed is None:
        return None
    if _HEIGHT_DECIMETER_MIN <= parsed <= _HEIGHT_DECIMETER_MAX:
        parsed *= 10
    if 100 <= parsed <= 250:
        return parsed
    return None


def _normalize_weight_kg(value: Any) -> int | None:
    parsed = _parse_int(value)
    if parsed is None:
        return None
    if _WEIGHT_DECIMETER_MIN <= parsed <= _WEIGHT_DECIMETER_MAX:
        parsed *= 10
    if 40 <= parsed <= 150:
        return parsed
    return None


def _normalize_non_negative_int(value: Any) -> int | None:
    parsed = _parse_int(value)
    if parsed is None or parsed < 0:
        return None
    return parsed


def _normalize_non_negative_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def _parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _fold_text(value: Any) -> str:
    if value is None:
        return ""
    translated = str(value).translate(
        str.maketrans(
            {
                "ı": "i",
                "İ": "I",
                "ş": "s",
                "Ş": "S",
                "ğ": "g",
                "Ğ": "G",
                "ü": "u",
                "Ü": "U",
                "ö": "o",
                "Ö": "O",
                "ç": "c",
                "Ç": "C",
            }
        )
    )
    normalized = unicodedata.normalize("NFKD", translated)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = []
    for character in ascii_value.lower():
        cleaned.append(character if character.isalnum() else " ")
    return " ".join("".join(cleaned).split())


def _compact_fold_text(value: Any) -> str:
    return "".join(_fold_text(value).split())


def _resolve_fallback_archive_path(value: Any) -> Path | None:
    if not value:
        return None
    candidate = Path(str(value)).expanduser().resolve()
    return candidate if candidate.exists() else None


def _required_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _clean_text(value: Any) -> str | None:
    return _required_text(value)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if not cleaned:
            continue
        lowered = cleaned.casefold()
        if lowered in seen:
            continue
        seen.add(lowered)
        result.append(cleaned)
    return result


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
