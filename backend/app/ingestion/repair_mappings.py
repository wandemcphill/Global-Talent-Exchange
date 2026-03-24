from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

from app.core.config import load_settings
from app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from app.ingestion.mapping_resolver import ClubResolutionContext, MappingResolver
from app.ingestion.second_zip_real_player_ops_service import SecondZipRealPlayerOpsService
from app.ingestion.second_zip_base_eligibility import SecondZipBaseEligibilityPolicy, evaluate_second_zip_players_csv_row
from app.ingestion.unresolved_logger import DEFAULT_UNRESOLVED_REPORT_PATH, UnresolvedMappingLogger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scan a 2nd.zip archive for unresolved club/country mappings.")
    parser.add_argument("--file", required=True, help="Path to the 2nd.zip archive to scan.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL.",
    )
    parser.add_argument("--limit", type=int, default=None, help="Optional limit of eligible players to inspect.")
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_UNRESOLVED_REPORT_PATH),
        help="CSV output path for unresolved mapping groups.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be greater than zero when provided.")

    engine = create_database_engine(args.database_url)
    ensure_database_schema_current(engine)
    session_factory = create_session_factory(engine)
    service = SecondZipRealPlayerOpsService(
        session_factory=session_factory,
        settings=load_settings(
            environ={
                **os.environ,
                "GTE_DATABASE_URL": args.database_url,
                "DATABASE_URL": args.database_url,
            }
        ),
    )
    resolver = MappingResolver()
    logger = UnresolvedMappingLogger(csv_path=Path(args.csv_path))

    total_rows_read = 0
    eligible_rows = 0
    selected_players = 0
    resolved_rows = 0
    skipped_rows = 0
    unresolved_rows = 0

    try:
        with service.archive_intake.extract_archive(Path(args.file).expanduser().resolve()) as extracted:
            lookups = service._load_lookups(extracted.workdir)
            policy = SecondZipBaseEligibilityPolicy(reference_date=service.reference_date)
            with session_factory() as session:
                for _, source_row in service._iter_player_rows(extracted.get_path("players.csv"), start_row_number=1):
                    total_rows_read += 1
                    eligibility = evaluate_second_zip_players_csv_row(source_row, policy=policy)
                    if not eligibility.eligible:
                        continue
                    eligible_rows += 1
                    if args.limit is not None and selected_players >= args.limit:
                        break
                    try:
                        payload = service._build_seed_input(source_row=source_row, lookups=lookups)
                    except Exception:
                        skipped_rows += 1
                        selected_players += 1
                        continue

                    selected_players += 1
                    country_resolution = resolver.resolve_country(
                        session,
                        raw_name=payload.nationality,
                        raw_code=payload.nationality_code,
                    )
                    club_resolution = resolver.resolve_club(
                        session,
                        raw_name=payload.current_real_world_club,
                        context=ClubResolutionContext(
                            competition_name=payload.current_real_world_league,
                            competition_id=payload.current_real_world_league_key,
                            country_name=payload.nationality,
                        ),
                    )

                    if country_resolution.status == "unresolved" or club_resolution.status == "unresolved":
                        unresolved_rows += 1
                        logger.record(
                            raw_club_name=payload.current_real_world_club,
                            raw_country_name=payload.nationality,
                            competition_name=payload.current_real_world_league,
                            player_name=payload.canonical_name,
                        )
                        continue
                    if country_resolution.status != "resolved" or club_resolution.status != "resolved":
                        skipped_rows += 1
                        continue
                    resolved_rows += 1
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2

    csv_path = logger.write_csv(args.csv_path)
    payload = {
        "archive_path": str(Path(args.file).expanduser().resolve()),
        "source_row_count": total_rows_read,
        "eligible_row_count": eligible_rows,
        "selected_player_count": selected_players,
        "resolved_row_count": resolved_rows,
        "skipped_row_count": skipped_rows,
        "unresolved_row_count": unresolved_rows,
        "unresolved_group_count": len(logger.summary()),
        "csv_path": str(csv_path),
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
