from __future__ import annotations

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Sequence

from sqlalchemy import text

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT, SCRIPT_PATH.parent):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.database import create_database_engine
from app.value_engine.pricing_curve import round_gtex_display_value
from app.value_engine.scoring import credits_from_real_world_value

SUMMARY_BACKFILL_SOURCE = "canonical_player_summary_backfill_v1"
ESTIMATED_VALUE_TAG = "gtex_estimated_value_v1"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill app-facing player_summary_read_models from canonical real-player rows. "
            "This publishes existing provider-backed or tagged estimated facts; it does not "
            "invent player metadata."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write changes. Default is dry-run.")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--sample-size", type=int, default=10)
    parser.add_argument(
        "--include-existing",
        action="store_true",
        help="Also repair existing summaries with blank club/competition or non-positive value.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    engine = create_database_engine(args.database_url)
    try:
        with engine.begin() as connection:
            report = _backfill_summaries(
                connection,
                apply=bool(args.apply),
                limit=max(1, int(args.limit)),
                offset=max(0, int(args.offset)),
                sample_size=max(0, int(args.sample_size)),
                include_existing=bool(args.include_existing),
            )
        print(json.dumps(report, sort_keys=True, default=str))
    finally:
        engine.dispose()
    return 0


def _backfill_summaries(
    connection: Any,
    *,
    apply: bool,
    limit: int,
    offset: int,
    sample_size: int,
    include_existing: bool,
) -> dict[str, Any]:
    rows = _fetch_candidates(
        connection,
        include_existing=include_existing,
        limit=limit,
        offset=offset,
    )
    stats: dict[str, Any] = {
        "apply": apply,
        "include_existing": include_existing,
        "limit": limit,
        "offset": offset,
        "scanned": 0,
        "created": 0,
        "updated": 0,
        "skipped_no_real_value": 0,
        "estimated_value_tagged": 0,
        "samples": [],
    }
    payloads: list[dict[str, Any]] = []
    now = datetime.now(UTC)
    for row in rows:
        stats["scanned"] += 1
        market_value_eur = _positive_float(row["market_value_eur"])
        if market_value_eur is None:
            stats["skipped_no_real_value"] += 1
            _sample(stats, row=row, action="skipped_no_real_value", sample_size=sample_size)
            continue

        value_credits = round_gtex_display_value(credits_from_real_world_value(market_value_eur))
        if value_credits is None or value_credits <= 0:
            stats["skipped_no_real_value"] += 1
            _sample(stats, row=row, action="skipped_no_real_value", sample_size=sample_size)
            continue

        estimated = ESTIMATED_VALUE_TAG in str(row.get("dna_profile_text") or "")
        summary_json = _summary_payload(
            row,
            market_value_eur=market_value_eur,
            estimated=estimated,
        )
        created = row["summary_player_id"] is None
        payloads.append(
            {
                "player_id": row["player_id"],
                "player_name": row["player_name"],
                "current_club_id": row["current_club_id"],
                "current_club_name": row["current_club_name"] or row["real_world_club_name"],
                "current_competition_id": row["current_competition_id"],
                "current_competition_name": row["current_competition_name"] or row["real_world_league_name"],
                "last_snapshot_at": row["last_snapshot_at"] or now,
                "current_value_credits": value_credits,
                "previous_value_credits": row["previous_value_credits"] or value_credits,
                "movement_pct": row["movement_pct"] or 0.0,
                "market_interest_score": row["market_interest_score"] or 0,
                "summary_json": json.dumps(summary_json, sort_keys=True, default=str),
            }
        )
        if estimated:
            stats["estimated_value_tagged"] += 1
        if created:
            stats["created"] += 1
            _sample(stats, row=row, action="created", sample_size=sample_size)
        else:
            stats["updated"] += 1
            _sample(stats, row=row, action="updated", sample_size=sample_size)

    if apply and payloads:
        connection.execute(_UPSERT_SUMMARY_SQL, payloads)
    return stats


def _fetch_candidates(
    connection: Any,
    *,
    include_existing: bool,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    existing_filter = """
        (
            s.player_id is null
            or s.current_value_credits <= 0
            or s.current_club_name is null
            or length(trim(s.current_club_name)) = 0
            or s.current_competition_name is null
            or length(trim(s.current_competition_name)) = 0
        )
    """
    missing_filter = "s.player_id is null"
    rows = connection.execute(
        text(f"""
            select p.id as player_id,
                   p.full_name as player_name,
                   p.normalized_position,
                   p.position,
                   p.current_club_id,
                   club.name as current_club_name,
                   p.real_world_club_name,
                   p.current_competition_id,
                   competition.name as current_competition_name,
                   p.real_world_league_name,
                   coalesce(p.current_market_reference_value, p.market_value_eur) as market_value_eur,
                   p.dna_profile::text as dna_profile_text,
                   s.player_id as summary_player_id,
                   s.last_snapshot_at,
                   s.previous_value_credits,
                   s.movement_pct,
                   s.market_interest_score,
                   s.summary_json::text as existing_summary_json
            from ingestion_players p
            left join player_summary_read_models s
              on s.player_id = p.id
            left join ingestion_clubs club
              on club.id = p.current_club_id
            left join ingestion_competitions competition
              on competition.id = p.current_competition_id
            where p.is_real_player is true
              and p.is_tradable is true
              and ({existing_filter if include_existing else missing_filter})
            order by p.full_name asc, p.id asc
            limit :limit offset :offset
            """),
        {"limit": limit, "offset": offset},
    ).mappings()
    return [dict(row) for row in rows]


def _summary_payload(
    row: dict[str, Any],
    *,
    market_value_eur: float,
    estimated: bool,
) -> dict[str, Any]:
    payload = _decode_json_object(row.get("existing_summary_json"))
    payload["summary_backfill_source"] = SUMMARY_BACKFILL_SOURCE
    payload["position"] = row.get("normalized_position") or row.get("position")
    real_player_profile = dict(payload.get("real_player_profile") or {})
    real_player_profile["current_market_reference_value"] = market_value_eur
    real_player_profile["market_reference_currency"] = "EUR"
    real_player_profile["market_value_source"] = ESTIMATED_VALUE_TAG if estimated else "canonical_player_market_value"
    payload["real_player_profile"] = real_player_profile
    payload["club_assignment"] = {
        **dict(payload.get("club_assignment") or {}),
        "status": "club_assigned" if row.get("current_club_id") else "team_context_pending",
        "current_club_id": row.get("current_club_id"),
        "current_club_name": row.get("current_club_name") or row.get("real_world_club_name"),
        "current_competition_id": row.get("current_competition_id"),
        "current_competition_name": row.get("current_competition_name") or row.get("real_world_league_name"),
    }
    if estimated:
        payload[ESTIMATED_VALUE_TAG] = True
        payload["value_estimation"] = {
            **dict(payload.get("value_estimation") or {}),
            "source": ESTIMATED_VALUE_TAG,
            "is_estimated": True,
        }
    return payload


def _decode_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if not value:
        return {}
    try:
        payload = json.loads(str(value))
    except json.JSONDecodeError:
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _positive_float(value: Any) -> float | None:
    if value is None:
        return None
    number = float(value)
    return number if number > 0 else None


def _sample(stats: dict[str, Any], *, row: dict[str, Any], action: str, sample_size: int) -> None:
    samples = stats["samples"]
    if len(samples) >= sample_size:
        return
    samples.append(
        {
            "action": action,
            "player_id": row["player_id"],
            "player_name": row["player_name"],
            "club_id": row["current_club_id"],
            "competition_id": row["current_competition_id"],
        }
    )


_UPSERT_SUMMARY_SQL = text("""
    insert into player_summary_read_models (
        player_id,
        player_name,
        current_club_id,
        current_club_name,
        current_competition_id,
        current_competition_name,
        last_snapshot_at,
        current_value_credits,
        previous_value_credits,
        movement_pct,
        market_interest_score,
        summary_json
    )
    values (
        :player_id,
        :player_name,
        :current_club_id,
        :current_club_name,
        :current_competition_id,
        :current_competition_name,
        :last_snapshot_at,
        :current_value_credits,
        :previous_value_credits,
        :movement_pct,
        :market_interest_score,
        cast(:summary_json as json)
    )
    on conflict (player_id) do update set
        player_name = excluded.player_name,
        current_club_id = excluded.current_club_id,
        current_club_name = excluded.current_club_name,
        current_competition_id = excluded.current_competition_id,
        current_competition_name = excluded.current_competition_name,
        current_value_credits = excluded.current_value_credits,
        previous_value_credits = case
            when player_summary_read_models.previous_value_credits <= 0
            then excluded.previous_value_credits
            else player_summary_read_models.previous_value_credits
        end,
        movement_pct = coalesce(player_summary_read_models.movement_pct, excluded.movement_pct),
        market_interest_score = coalesce(
            player_summary_read_models.market_interest_score,
            excluded.market_interest_score
        ),
        summary_json = excluded.summary_json,
        updated_at = now()
    """)


if __name__ == "__main__":
    raise SystemExit(main())
