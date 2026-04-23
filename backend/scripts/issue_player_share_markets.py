from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Country, LiquidityBand, Player, SupplyTier
from app.models.player_token_market import PlayerShareMarket
from app.players.token_market_defaults import resolve_player_share_market_config
from app.players.token_service import PlayerTokenMarketService

DEFAULT_POLICY_PATH = BACKEND_ROOT / "config" / "player_share_issuance.toml"


@dataclass(frozen=True, slots=True)
class IssuancePlan:
    tier: str
    total_shares: int
    initial_circulating_cap: int
    initial_mm_inventory_target: int
    share_price_coin: Decimal
    liquidity_coin: Decimal
    status: str


def _load_policy(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _decimal(value: object, fallback: str = "0.0000") -> Decimal:
    return Decimal(str(value if value is not None else fallback)).quantize(Decimal("0.0001"))


def _json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _normalize_tier(player: Player, policy: dict[str, Any]) -> str:
    tiers = set((policy.get("tiers") or {}).keys())
    raw_values = [
        player.real_player_tier,
        player.supply_tier.code if player.supply_tier is not None else None,
        player.supply_tier.name if player.supply_tier is not None else None,
    ]
    aliases = {
        "legend": "icon",
        "world_class": "icon",
        "world-class": "icon",
        "star": "elite",
        "starter": "core",
        "young": "prospect",
        "youth": "prospect",
    }
    for raw in raw_values:
        normalized = str(raw or "").strip().lower().replace(" ", "_")
        if not normalized:
            continue
        normalized = aliases.get(normalized, normalized)
        if normalized in tiers:
            return normalized
    return "discovery"


def _has_context(player: Player) -> bool:
    return bool(
        player.current_club_id
        or player.current_competition_id
        or player.internal_league_id
        or (player.real_world_club_name or "").strip()
        or (player.real_world_league_name or "").strip()
    )


def _blocked_by_metadata(player: Player, policy: dict[str, Any]) -> str | None:
    metadata = dict(player.dna_profile or {})
    for key in policy.get("eligibility", {}).get("block_metadata_flags", []):
        if metadata.get(str(key)):
            return f"blocked_by_{key}"
    return None


def _eligibility_block_reason(player: Player, policy: dict[str, Any]) -> str | None:
    eligibility = policy.get("eligibility", {})
    if eligibility.get("require_real_player", True) and not player.is_real_player:
        return "not_real_player"
    if eligibility.get("require_tradable", True) and not player.is_tradable:
        return "not_tradable"
    if eligibility.get("require_canonical_display_name", True) and not (player.canonical_display_name or "").strip():
        return "missing_canonical_display_name"
    if eligibility.get("require_country", True) and player.country_id is None:
        return "missing_country"
    if eligibility.get("require_club_or_competition_context", True) and not _has_context(player):
        return "missing_club_or_competition_context"
    return _blocked_by_metadata(player, policy)


def _build_plan(player: Player, policy: dict[str, Any]) -> IssuancePlan:
    tier = _normalize_tier(player, policy)
    tier_policy = (policy.get("tiers") or {})[tier]
    total_shares = int(tier_policy["total_shares"])
    resolved = resolve_player_share_market_config(player, total_shares=total_shares)
    pricing = policy.get("pricing", {})
    price = min(
        max(resolved.share_price_coin, _decimal(pricing.get("launch_floor_coin"), "0.0500")),
        _decimal(pricing.get("launch_ceiling_coin"), "1000.0000"),
    )
    liquidity_policy = policy.get("liquidity", {})
    liquidity_floor = _decimal(liquidity_policy.get("platform_minimum_coin"), "25.0000")
    if tier in {"icon", "elite", "core"}:
        liquidity_floor = max(
            liquidity_floor,
            _decimal(liquidity_policy.get("core_plus_preferred_minimum_coin"), "50.0000"),
        )
    initial_mm_inventory_target = int(tier_policy["initial_mm_inventory_target"])
    liquidity_coin = max(_decimal(price * Decimal(initial_mm_inventory_target)), liquidity_floor)
    launch_status = policy.get("launch_status", {})
    low_confidence_threshold = float(launch_status.get("low_confidence_threshold", 0.55))
    confidence = player.identity_confidence_score
    status = str(launch_status.get("default", "active"))
    if confidence is not None and float(confidence) < low_confidence_threshold:
        status = str(launch_status.get("low_confidence", "paused"))
    return IssuancePlan(
        tier=tier,
        total_shares=total_shares,
        initial_circulating_cap=int(tier_policy["initial_circulating_cap"]),
        initial_mm_inventory_target=initial_mm_inventory_target,
        share_price_coin=_decimal(price),
        liquidity_coin=liquidity_coin,
        status=status,
    )


def _base_query(args: argparse.Namespace):
    stmt = (
        select(Player)
        .options(
            selectinload(Player.share_market),
            selectinload(Player.country),
            selectinload(Player.current_club),
            selectinload(Player.current_competition),
            selectinload(Player.supply_tier),
            selectinload(Player.liquidity_band),
        )
        .where(Player.is_real_player.is_(True), Player.is_tradable.is_(True))
        .order_by(Player.updated_at.desc(), Player.id.asc())
    )
    value = (args.cohort_value or "").strip()
    if args.cohort_type == "all":
        return stmt
    if not value:
        raise SystemExit(f"--cohort-value is required for cohort type {args.cohort_type}.")
    pattern = f"%{value}%"
    if args.cohort_type == "import_batch":
        return stmt.where(or_(Player.source_provider == value, Player.normalization_profile_version == value))
    if args.cohort_type == "league":
        return stmt.where(
            or_(
                Player.current_competition_id == value,
                Player.internal_league_id == value,
                Player.real_world_league_name.ilike(pattern),
            )
        )
    if args.cohort_type == "country":
        return stmt.where(
            or_(
                Player.country_id == value,
                Player.country.has(Country.name.ilike(pattern)),
                Player.country.has(Country.alpha2_code == value.upper()),
                Player.country.has(Country.alpha3_code == value.upper()),
                Player.country.has(Country.fifa_code == value.upper()),
            )
        )
    if args.cohort_type == "supply_tier":
        return stmt.where(
            or_(
                Player.real_player_tier == value,
                Player.supply_tier.has(SupplyTier.code == value),
                Player.supply_tier.has(SupplyTier.name.ilike(pattern)),
            )
        )
    if args.cohort_type == "liquidity_band":
        return stmt.where(
            or_(
                Player.liquidity_band_id == value,
                Player.liquidity_band.has(LiquidityBand.code == value),
                Player.liquidity_band.has(LiquidityBand.name.ilike(pattern)),
            )
        )
    raise SystemExit(f"Unsupported cohort type: {args.cohort_type}")


def _record(report: dict[str, Any], bucket: str, player: Player, reason: str, plan: IssuancePlan | None = None) -> None:
    report["counts"][bucket] += 1
    item: dict[str, Any] = {
        "player_id": player.id,
        "player_name": player.canonical_display_name or player.full_name,
        "reason": reason,
    }
    if plan is not None:
        item.update(
            {
                "tier": plan.tier,
                "status": plan.status,
                "total_shares": plan.total_shares,
                "share_price_coin": plan.share_price_coin,
                "liquidity_coin": plan.liquidity_coin,
            }
        )
    report[bucket].append(item)


def issue_markets(args: argparse.Namespace) -> dict[str, Any]:
    policy = _load_policy(Path(args.policy_path))
    limit = int(args.limit or policy.get("cohorts", {}).get("default_limit", 250))
    dry_run = bool(args.dry_run or not args.activate)
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    report: dict[str, Any] = {
        "dry_run": dry_run,
        "activated": bool(args.activate and not dry_run),
        "cohort_type": args.cohort_type,
        "cohort_value": args.cohort_value,
        "limit": limit,
        "counts": {
            "created": 0,
            "updated": 0,
            "skipped_existing": 0,
            "skipped_blocked": 0,
            "failed": 0,
        },
        "created": [],
        "updated": [],
        "skipped_existing": [],
        "skipped_blocked": [],
        "failed": [],
    }
    with session_factory() as session:
        players = list(session.scalars(_base_query(args).limit(limit)).all())
        service = PlayerTokenMarketService(session)
        for player in players:
            try:
                block_reason = _eligibility_block_reason(player, policy)
                if block_reason is not None:
                    _record(report, "skipped_blocked", player, block_reason)
                    continue
                plan = _build_plan(player, policy)
                market: PlayerShareMarket | None = player.share_market
                if market is not None and market.status == "active":
                    _record(report, "skipped_existing", player, "active_market_exists", plan)
                    continue
                if market is not None and market.status == "paused":
                    _record(report, "skipped_existing", player, "paused_market_kept_paused", plan)
                    continue
                if market is not None and market.status == "closed" and int(market.circulating_shares or 0) > 0:
                    _record(report, "skipped_blocked", player, "closed_market_has_circulation", plan)
                    continue
                bucket = "updated" if market is not None else "created"
                if not dry_run:
                    issued = service.ensure_market(
                        player_id=player.id,
                        total_shares=plan.total_shares,
                        share_price_coin=plan.share_price_coin,
                        liquidity_coin=plan.liquidity_coin,
                        status=plan.status,
                    )
                    issued.metadata_json = {
                        **(issued.metadata_json or {}),
                        "issuance_tier": plan.tier,
                        "initial_circulating_cap": plan.initial_circulating_cap,
                        "initial_mm_inventory_target": plan.initial_mm_inventory_target,
                        "bulk_issuance_policy": Path(args.policy_path).name,
                    }
                _record(report, bucket, player, "eligible", plan)
            except Exception as exc:  # pragma: no cover - report safety for ops runs
                _record(report, "failed", player, exc.__class__.__name__)
                report["failed"][-1]["detail"] = str(exc)
        if dry_run:
            session.rollback()
        else:
            session.commit()
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk issue GTEX player-share markets by safe cohorts.")
    parser.add_argument("--cohort-type", default="all", choices=["all", "import_batch", "league", "country", "supply_tier", "liquidity_band"])
    parser.add_argument("--cohort-value", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true", help="Plan and report only. This is also the default unless --activate is passed.")
    parser.add_argument("--activate", action="store_true", help="Persist eligible market creations/updates.")
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--policy-path", default=str(DEFAULT_POLICY_PATH))
    parser.add_argument("--database-url", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = issue_markets(args)
    encoded = json.dumps(report, indent=2, sort_keys=True, default=_json_default)
    if args.report_path:
        report_path = Path(args.report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
