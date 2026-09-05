"""One-time repair: undo historical market_value_eur distortion from the old
legend_layer narrative multiplier.

From `e5418eb9` until it was fixed in `f406aa76` ("fix: return tradable price
and market issuance to their owners"), `legend_layer/service.py`'s
`_apply_market_reaction` ran on every matchday narrative event and:

  1. Computed `multiplier = 1 + clamp(-0.18, 0.18, perception_delta/100 +
     (rating-6.5)/50)` from that event's news-article perception swing and
     player rating.
  2. Set `player.market_value_eur = round(current_value * multiplier, 2)` --
     UNCLAMPED across events, so a player touched by many matches could drift
     arbitrarily far from any real value through pure compounding.
  3. Mirrored the corrupted number onto `player.current_market_reference_value`
     every time, which is also value_engine's baseline input (see the fix
     commit's docstring) -- so the distortion fed forward into every
     value_engine snapshot computed since, not just the display field.
  4. If `current_value <= 0.0` (player had no value yet), FABRICATED one:
     `max(100_000.0, max(rating, 6.0) * 120_000.0)`, then multiplied that
     invented number by the event's own multiplier in the same step. A value
     with this origin has no real basis to restore to -- see fabrication
     detection below.

The fix stopped this going forward. This script repairs the backlog it left
behind. It is intentionally scoped to `market_value_eur` only (and, for real
players, the field it was permanently overwriting on every touch --
`current_market_reference_value`): `player_share_markets.share_price_coin`
was governor-clamped and has had legitimate trading/issuance/admin activity
layered on top of it since, so it is not repaired here.

AUDIT TRAIL
-----------
`event_type = "narrative"` on `player_share_events` was written *only* by the
buggy code path (confirmed: no other call site in the codebase creates this
event type), so it is the complete, ordered record of every mutation. Each
row's `metadata_json` stores the exact `perception_delta` and `rating` the
multiplier was computed from, so every historical multiplier is exactly
reconstructible.

RESTORE STRATEGY -- splits on `player.is_real_player`
------------------------------------------------------
Real players: ingestion is the *unconditional*, re-runnable, external-data
writer of `market_value_eur` -- so the field's own history isn't a reliable
place to reverse-engineer a true value from (ingestion overwrites rather than
multiplies, breaking any order-independent "divide out the bad multipliers"
math if a sync happened between two narrative events). Instead this script
restores from a source the bug never touched: `real_player_profiles
.current_market_reference_value`, falling back to
`real_player_import_staging.rough_market_value` -- both populated only by
ingestion, independent of `ingestion_players.market_value_eur` itself. A
player with neither is reported, not guessed at.

Regens: they have no external ground truth at all -- market_value_eur is
entirely internally generated (seeded once at creation from
`current_gsi * 12_500`, then evolved *multiplicatively* by a periodic growth
job; see `regen_universe/expansion_service.py`). Because every known writer
after creation is a pure multiplication on the same field, multiplication
commutes: dividing the current (corrupted) value by the product of every
reconstructed narrative-event multiplier yields exactly what the field would
be today had legend_layer never touched it, regardless of how the legitimate
growth-job multiplications were interleaved with the buggy ones.

WHY FABRICATION CAN'T BE DETECTED BY MAGNITUDE, AND WHAT IS USED INSTEAD (regens only)
----------------------------------------------------------------------------------------
If the fallback ever fired for a player, the reversal math above recovers a
number with no real basis -- there is no true value to divide back to. Two
magnitude-based detectors were tried and both were rejected after simulation,
not because of a tolerance-tuning problem but a structural one: the growth
job (`regen_universe/expansion_service.py`) also multiplies `market_value_eur`
on a recurring basis, and it leaves no audit trail -- only legend_layer's
narrative events are recorded in `player_share_events`. Any comparison of a
reconstructed value to the fabrication formula (`fabricated_value(rating) =
max(100_000, max(rating, 6.0) * 120_000)`) is contaminated by an unknown
number of un-recorded growth-job multiplications applied since, and that
drift compounds with career length:

  1. Comparing "value right after the player's first narrative event" (the
     only position the fallback could have fired at, since the fabricated
     value is always positive and no later writer can take a positive value
     non-positive) against `fabricated_value(first_rating) * first_multiplier`
     missed 65%+ of genuine fabrication cases even in short (1-12 event)
     simulated careers, because growth-job multiplications after that first
     event shift the comparison point unpredictably.
  2. Comparing the final reversed value against a GSI-derived floor
     (`regen_profiles.current_gsi * 12_500 * tolerance` -- current_gsi is a
     value the bug never touched, and it only ever grows) doesn't fare any
     better: over longer simulated careers (up to 40 growth/narrative
     cycles), no tolerance separated the two populations -- loose enough to
     catch a meaningful share of fabrication also flagged a comparable share
     of ordinary long, legitimately-grown careers as implausible, because a
     fabricated-then-grown trajectory and a genuinely-seeded-then-grown one
     occupy the same numeric range by construction of the game's own
     economy (both scale off a rating/GSI-driven formula in the same
     100k-1.2M+ neighborhood).

So this script does not attempt to separate the two by value. Instead it
relies on a factual signal: `regen_profiles` existing for a player confirms
it went through the known creation pipeline (`regen_creation/service.py`,
`services/regen_bootstrap_service.py`), which always seeds a positive
`current_gsi * 12_500` value at genesis -- meaning the fallback's
`current_value <= 0.0` trigger condition should not arise for it in the
first place. A player with no `regen_profiles` row at all can't be confirmed
to have gone through that pipeline, so it is flagged for manual review
instead of assumed. This is not airtight (a value could in principle have
been zeroed out by some other, unmodeled process before a narrative event),
but it is the strongest signal actually available, stated honestly rather
than dressed up as more precise than it is. Regens have no external ground
truth at all -- their value has always been a synthetic estimate -- so even
a clean reversal here is the best available reconstruction, not a
certainty.

Players whose current `market_value_eur` is already <= 0 are left alone and
reported too -- there's nothing to divide out of a non-positive number, and
for them the fallback's trigger condition demonstrably does hold right now.

Every write is COALESCE-free and unconditional for the population it targets
(a player is only in scope because we know, from the narrative-event audit
trail, that its current value is corrupted) and leaves its own audit trail: a
`player_share_events` row with `event_type = "market_value_repair"` recording
the old value, new value, and restore source.

Default is audit-only (no writes; the transaction is rolled back). Pass
--apply to write. Run co-located with the database (a Render one-off job),
not from a laptop over a remote pooler.

Usage:
    python backend/scripts/repair_legend_layer_market_value_distortion.py \
        --database-url "$DATABASE_URL"
    python backend/scripts/repair_legend_layer_market_value_distortion.py \
        --database-url "$DATABASE_URL" --apply
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from decimal import Decimal
import json
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
for candidate in (str(ROOT_DIR), str(BACKEND_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from sqlalchemy import select, text

# `app.models` is the aggregate registry and must be imported before any
# individual model module, otherwise importing a model directly re-enters it
# mid-initialization and raises a circular ImportError.
import app.models  # noqa: F401, E402
from app.core.database import create_database_engine, create_session_factory, load_model_modules  # noqa: E402
from app.ingestion.models import Player  # noqa: E402
from app.ingestion.real_player_import_models import RealPlayerImportStagingRecord  # noqa: E402
from app.models.player_token_market import PlayerShareEvent, PlayerShareMarket  # noqa: E402
from app.models.real_player_profile import RealPlayerProfile  # noqa: E402
from app.models.regen import RegenProfile  # noqa: E402

MULTIPLIER_FLOOR = -0.18
MULTIPLIER_CEILING = 0.18
COMMIT_BATCH_SIZE = 500


@dataclass(slots=True)
class RepairStats:
    narrative_events_total: int = 0
    players_with_narrative_events: int = 0
    real_players_restored_from_pristine_source: int = 0
    real_players_missing_pristine_source: int = 0
    regens_restored_via_reversal: int = 0
    regens_missing_regen_profile: int = 0
    regens_non_positive_current_value_skipped: int = 0
    real_players_missing_pristine_samples: list[dict[str, object]] = field(default_factory=list)
    regens_missing_regen_profile_samples: list[dict[str, object]] = field(default_factory=list)
    regens_non_positive_current_value_samples: list[dict[str, object]] = field(default_factory=list)


def _reconstruct_multiplier(*, perception_delta: float, rating: float) -> float:
    raw = (perception_delta / 100.0) + ((rating - 6.5) / 50.0)
    clamped = max(MULTIPLIER_FLOOR, min(MULTIPLIER_CEILING, raw))
    return float(Decimal("1.0000") + Decimal(str(clamped)))


def _positive_float(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _event_metadata(raw: object) -> dict[str, object]:
    # A raw `text()` query isn't typed, so whether the driver hands back
    # `metadata_json` already deserialized or as a JSON string depends on the
    # DBAPI's own auto-adaptation (psycopg does; sqlite3 doesn't) rather than
    # anything SQLAlchemy guarantees here. Handle both.
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _pristine_real_value(session, player: Player) -> float | None:
    profile = session.scalar(select(RealPlayerProfile).where(RealPlayerProfile.gtex_player_id == player.id))
    if profile is not None:
        value = _positive_float(profile.current_market_reference_value)
        if value is not None and (profile.market_reference_currency or "EUR").strip().upper() == "EUR":
            return value
        source_name = profile.source_name
        source_key = profile.source_player_key
    else:
        source_name = player.source_provider
        source_key = player.provider_external_id

    if source_name and source_key:
        staging = session.scalar(
            select(RealPlayerImportStagingRecord).where(
                RealPlayerImportStagingRecord.provider_name == source_name,
                RealPlayerImportStagingRecord.provider_player_id == source_key,
            )
        )
        if staging is not None:
            value = _positive_float(staging.rough_market_value)
            if value is not None and (staging.rough_market_value_currency or "EUR").strip().upper() == "EUR":
                return value
    return None


def _record_repair_event(
    session,
    *,
    player: Player,
    old_value: float | None,
    new_value: float,
    source: str,
    extra_metadata: dict[str, object] | None = None,
) -> None:
    market = session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id))
    session.add(
        PlayerShareEvent(
            player_id=player.id,
            actor_user_id=None,
            event_type="market_value_repair",
            share_delta=0,
            price_per_share_coin=market.share_price_coin if market is not None else Decimal("0.0000"),
            gross_amount_coin=Decimal("0.0000"),
            metadata_json={
                "reason": "legend_layer_narrative_multiplier_distortion",
                "old_market_value_eur": old_value,
                "new_market_value_eur": new_value,
                "restore_source": source,
                **(extra_metadata or {}),
            },
        )
    )


def _sample(bucket: list[dict[str, object]], *, player: Player, extra: dict[str, object], sample_size: int) -> None:
    if len(bucket) >= sample_size:
        return
    bucket.append(
        {
            "player_id": player.id,
            "full_name": player.full_name,
            "is_real_player": bool(player.is_real_player),
            "current_market_value_eur": player.market_value_eur,
            **extra,
        }
    )


def repair(
    *,
    database_url: str,
    apply: bool = False,
    limit: int | None = None,
    batch_size: int = COMMIT_BATCH_SIZE,
    sample_size: int = 25,
) -> RepairStats:
    engine = create_database_engine(database_url)
    load_model_modules()
    stats = RepairStats()
    try:
        session_factory = create_session_factory(engine)
        with session_factory() as session:
            event_rows = session.execute(text("""
                    SELECT player_id, created_at, metadata_json
                    FROM player_share_events
                    WHERE event_type = 'narrative'
                    ORDER BY player_id ASC, created_at ASC
                    """)).all()
            stats.narrative_events_total = len(event_rows)

            grouped: dict[str, list] = {}
            for row in event_rows:
                grouped.setdefault(row.player_id, []).append(row)
            stats.players_with_narrative_events = len(grouped)

            player_ids = list(grouped.keys())
            if limit is not None:
                player_ids = player_ids[:limit]

            pending = 0
            for player_id in player_ids:
                rows = grouped[player_id]
                player = session.get(Player, player_id)
                if player is None:
                    continue
                old_value = player.market_value_eur

                if player.is_real_player:
                    pristine = _pristine_real_value(session, player)
                    if pristine is None:
                        stats.real_players_missing_pristine_source += 1
                        _sample(
                            stats.real_players_missing_pristine_samples,
                            player=player,
                            extra={"narrative_events": len(rows)},
                            sample_size=sample_size,
                        )
                        continue
                    new_value = round(pristine, 2)
                    if apply:
                        player.market_value_eur = new_value
                        player.current_market_reference_value = new_value
                        player.market_reference_currency = "EUR"
                        _record_repair_event(
                            session,
                            player=player,
                            old_value=old_value,
                            new_value=new_value,
                            source="real_player_pristine_reference",
                        )
                    stats.real_players_restored_from_pristine_source += 1
                    pending += 1
                else:
                    if old_value is None or old_value <= 0.0:
                        stats.regens_non_positive_current_value_skipped += 1
                        _sample(
                            stats.regens_non_positive_current_value_samples,
                            player=player,
                            extra={"narrative_events": len(rows)},
                            sample_size=sample_size,
                        )
                        continue

                    multipliers: list[float] = []
                    for row in rows:
                        meta = _event_metadata(row.metadata_json)
                        rating = float(meta.get("rating") or 0.0)
                        perception_delta = float(meta.get("perception_delta") or 0.0)
                        multipliers.append(_reconstruct_multiplier(perception_delta=perception_delta, rating=rating))

                    # Order-independent: multiplication commutes, so dividing out
                    # every reconstructed narrative multiplier removes exactly the
                    # bug's effect regardless of how legitimate growth-job
                    # multiplications were interleaved with it (see module
                    # docstring). Only invalid if the bug's fabrication fallback
                    # ever fired for this player, which a `regen_profiles` row
                    # rules out in practice (see docstring for why a magnitude
                    # check can't do this job instead).
                    pre_narrative_value = float(old_value)
                    for multiplier in multipliers:
                        pre_narrative_value = pre_narrative_value / multiplier

                    regen_profile = session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
                    if regen_profile is None:
                        stats.regens_missing_regen_profile += 1
                        _sample(
                            stats.regens_missing_regen_profile_samples,
                            player=player,
                            extra={
                                "narrative_events": len(rows),
                                "reconstructed_pre_narrative_value": round(pre_narrative_value, 2),
                            },
                            sample_size=sample_size,
                        )
                        continue

                    new_value = round(pre_narrative_value, 2)
                    if apply:
                        player.market_value_eur = new_value
                        _record_repair_event(
                            session,
                            player=player,
                            old_value=old_value,
                            new_value=new_value,
                            source="regen_narrative_multiplier_reversal",
                            extra_metadata={"current_gsi": regen_profile.current_gsi},
                        )
                    stats.regens_restored_via_reversal += 1
                    pending += 1

                if apply and pending >= batch_size:
                    session.commit()
                    session.expunge_all()
                    pending = 0

            if apply:
                session.commit()
            else:
                session.rollback()
    finally:
        engine.dispose()
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write repairs. Default is audit-only (no writes, transaction rolled back).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process this many distinct touched players (ordered by player_id).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=COMMIT_BATCH_SIZE,
        help=f"Rows per commit when --apply is set (default: {COMMIT_BATCH_SIZE}).",
    )
    parser.add_argument("--sample-size", type=int, default=25, help="Max sample rows to include per flagged category.")
    args = parser.parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    stats = repair(
        database_url=args.database_url,
        apply=args.apply,
        limit=args.limit,
        batch_size=args.batch_size,
        sample_size=args.sample_size,
    )
    print(json.dumps({**asdict(stats), "apply": bool(args.apply)}, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
