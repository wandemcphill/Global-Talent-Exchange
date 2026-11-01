"""Dedicated, idempotent historical market inventory reconciliation script.

Performs a comprehensive, non-destructive audit and dry-run reconciliation of:
1. Existing-holder counts per player market.
2. Existing holdings greater than one (under the whole-player acquisition rule).
3. One-of-one market conflicts (legends/regens with multiple units or holders).
4. Duplicate player identity conflicts.
5. Existing circulating inventory vs proposed compliant inventory.
6. Ledger, event, and holding consistency checks.
7. Before-and-after reconciliation totals.

Safety guarantees:
- Read-only by default (no records deleted, balances rewritten, or inventory reset).
- Idempotent and safe to run against production replicas or live databases.
- Supports JSON and CSV reporting.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Player
from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket

logger = logging.getLogger(__name__)


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    nfkd = unicodedata.normalize("NFKD", name)
    unaccented = "".join(c for c in nfkd if not unicodedata.combining(c))
    return "".join(c.lower() for c in unaccented if c.isalnum() or c.isspace()).strip()


@dataclass
class HoldingConflict:
    holding_id: str
    user_id: str
    player_id: str
    player_name: str
    share_count: int
    average_cost_coin: str


@dataclass
class OneOfOneConflict:
    market_id: str
    player_id: str
    player_name: str
    total_shares: int
    circulating_shares: int
    holder_count: int
    total_held_shares: int


@dataclass
class DuplicateIdentityConflict:
    canonical_normalized_name: str
    player_ids: list[str]
    player_names: list[str]
    countries: list[str | None]
    is_real_flags: list[bool]


@dataclass
class CirculationMismatch:
    market_id: str
    player_id: str
    player_name: str
    circulating_shares: int
    sum_holdings: int
    sum_event_deltas: int
    difference: int


@dataclass
class InventoryReconciliationReport:
    dry_run: bool = True
    total_markets: int = 0
    total_holdings: int = 0
    total_holders: int = 0
    current_total_circulating: int = 0
    proposed_compliant_circulating: int = 0
    excess_circulating_units: int = 0
    holdings_greater_than_one_count: int = 0
    one_of_one_conflicts_count: int = 0
    duplicate_identity_groups_count: int = 0
    circulation_mismatches_count: int = 0
    holdings_greater_than_one: list[HoldingConflict] = field(default_factory=list)
    one_of_one_conflicts: list[OneOfOneConflict] = field(default_factory=list)
    duplicate_identity_conflicts: list[DuplicateIdentityConflict] = field(default_factory=list)
    circulation_mismatches: list[CirculationMismatch] = field(default_factory=list)
    summary_by_player_type: dict[str, dict[str, Any]] = field(default_factory=dict)
    gates: dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def audit_market_inventory(session: Session, *, dry_run: bool = True) -> InventoryReconciliationReport:
    """Run full read-only audit of historical market inventory."""
    report = InventoryReconciliationReport(dry_run=dry_run)

    # 1. Fetch all players and markets
    players = {p.id: p for p in session.scalars(select(Player)).all()}
    markets = session.scalars(select(PlayerShareMarket)).all()
    report.total_markets = len(markets)

    # 2. Holdings audit
    holdings = session.scalars(select(PlayerShareHolding)).all()
    report.total_holdings = len(holdings)

    player_holdings: dict[str, list[PlayerShareHolding]] = defaultdict(list)
    unique_holders = set()

    for h in holdings:
        if h.share_count > 0:
            unique_holders.add(h.user_id)
            player_holdings[h.player_id].append(h)
            if h.share_count > 1:
                p = players.get(h.player_id)
                report.holdings_greater_than_one.append(
                    HoldingConflict(
                        holding_id=str(h.id),
                        user_id=str(h.user_id),
                        player_id=str(h.player_id),
                        player_name=p.full_name if p else "Unknown",
                        share_count=int(h.share_count),
                        average_cost_coin=str(h.average_cost_coin),
                    )
                )

    report.total_holders = len(unique_holders)
    report.holdings_greater_than_one_count = len(report.holdings_greater_than_one)

    # 3. Events audit for delta reconciliation
    event_deltas = {
        str(player_id): int(delta or 0)
        for player_id, delta in session.execute(
            select(PlayerShareEvent.player_id, func.sum(PlayerShareEvent.share_delta)).group_by(
                PlayerShareEvent.player_id
            )
        ).all()
    }

    # 4. Check markets, 1-of-1 conflicts, and circulation consistency
    real_circulating = 0
    legend_circulating = 0
    proposed_total = 0

    for m in markets:
        p = players.get(m.player_id)
        player_name = p.full_name if p else "Unknown"
        is_real = bool(p.is_real_player) if p else True
        circulating = int(m.circulating_shares or 0)
        report.current_total_circulating += circulating

        held_list = player_holdings.get(m.player_id, [])
        sum_held = sum(int(h.share_count) for h in held_list)
        sum_events = event_deltas.get(str(m.player_id), 0)

        # Check circulation consistency
        if circulating != sum_held or circulating != sum_events:
            report.circulation_mismatches.append(
                CirculationMismatch(
                    market_id=str(m.id),
                    player_id=str(m.player_id),
                    player_name=player_name,
                    circulating_shares=circulating,
                    sum_holdings=sum_held,
                    sum_event_deltas=sum_events,
                    difference=circulating - sum_held,
                )
            )

        # Proposed compliant inventory: 1 unit per unique holder
        compliant_units_for_market = len(held_list)
        if not is_real:
            # 1-of-1 asset: max 1 unit globally
            compliant_units_for_market = min(1, compliant_units_for_market)
            legend_circulating += circulating
            if circulating > 1 or len(held_list) > 1 or sum_held > 1:
                report.one_of_one_conflicts.append(
                    OneOfOneConflict(
                        market_id=str(m.id),
                        player_id=str(m.player_id),
                        player_name=player_name,
                        total_shares=int(m.total_shares or 0),
                        circulating_shares=circulating,
                        holder_count=len(held_list),
                        total_held_shares=sum_held,
                    )
                )
        else:
            # Real player: max 600 units
            compliant_units_for_market = min(600, compliant_units_for_market)
            real_circulating += circulating

        proposed_total += compliant_units_for_market

    report.proposed_compliant_circulating = proposed_total
    report.excess_circulating_units = max(0, report.current_total_circulating - proposed_total)
    report.one_of_one_conflicts_count = len(report.one_of_one_conflicts)
    report.circulation_mismatches_count = len(report.circulation_mismatches)

    # 5. Check duplicate player identities
    name_groups: dict[str, list[Player]] = defaultdict(list)
    for p in players.values():
        norm = _normalize_name(p.full_name or p.canonical_display_name)
        if norm:
            name_groups[norm].append(p)

    for norm_name, group in name_groups.items():
        if len(group) > 1:
            report.duplicate_identity_conflicts.append(
                DuplicateIdentityConflict(
                    canonical_normalized_name=norm_name,
                    player_ids=[p.id for p in group],
                    player_names=[p.full_name or "Unknown" for p in group],
                    countries=[getattr(p, "country_id", None) for p in group],
                    is_real_flags=[bool(p.is_real_player) for p in group],
                )
            )
    report.duplicate_identity_groups_count = len(report.duplicate_identity_conflicts)

    report.summary_by_player_type = {
        "real_players": {
            "circulating": real_circulating,
        },
        "legendary_and_regen": {
            "circulating": legend_circulating,
            "one_of_one_conflicts": report.one_of_one_conflicts_count,
        },
    }

    report.gates = {
        "no_unreconciled_circulation_mismatches": report.circulation_mismatches_count == 0,
        "no_unresolved_one_of_one_conflicts": report.one_of_one_conflicts_count == 0,
        "all_holdings_within_single_unit_rule": report.holdings_greater_than_one_count == 0,
        "no_duplicate_identity_conflicts": report.duplicate_identity_groups_count == 0,
    }

    return report


def generate_csv_report(report: InventoryReconciliationReport) -> str:
    """Format the report as human-readable CSV sections."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header section
    writer.writerow(["GTEX HISTORICAL MARKET INVENTORY RECONCILIATION REPORT"])
    writer.writerow(["Dry Run", report.dry_run])
    writer.writerow(["Total Markets", report.total_markets])
    writer.writerow(["Total Holdings", report.total_holdings])
    writer.writerow(["Total Unique Holders", report.total_holders])
    writer.writerow(["Current Circulating Units", report.current_total_circulating])
    writer.writerow(["Proposed Compliant Units", report.proposed_compliant_circulating])
    writer.writerow(["Excess Circulating Units", report.excess_circulating_units])
    writer.writerow([])

    # Holdings > 1
    writer.writerow(["HOLDINGS GREATER THAN ONE", len(report.holdings_greater_than_one)])
    writer.writerow(["Holding ID", "User ID", "Player ID", "Player Name", "Share Count", "Average Cost (Coin)"])
    for h in report.holdings_greater_than_one:
        writer.writerow([h.holding_id, h.user_id, h.player_id, h.player_name, h.share_count, h.average_cost_coin])
    writer.writerow([])

    # 1-of-1 Conflicts
    writer.writerow(["ONE-OF-ONE MARKET CONFLICTS", len(report.one_of_one_conflicts)])
    writer.writerow(
        ["Market ID", "Player ID", "Player Name", "Total Supply", "Circulating", "Holder Count", "Held Total"]
    )
    for o in report.one_of_one_conflicts:
        writer.writerow(
            [
                o.market_id,
                o.player_id,
                o.player_name,
                o.total_shares,
                o.circulating_shares,
                o.holder_count,
                o.total_held_shares,
            ]
        )
    writer.writerow([])

    # Duplicate Identities
    writer.writerow(["DUPLICATE IDENTITY CONFLICTS", len(report.duplicate_identity_conflicts)])
    writer.writerow(["Normalized Name", "Player IDs", "Player Names", "Is Real Flags"])
    for d in report.duplicate_identity_conflicts:
        writer.writerow(
            [
                d.canonical_normalized_name,
                "; ".join(d.player_ids),
                "; ".join(d.player_names),
                "; ".join(map(str, d.is_real_flags)),
            ]
        )
    writer.writerow([])

    # Circulation Mismatches
    writer.writerow(["CIRCULATION MISMATCHES", len(report.circulation_mismatches)])
    writer.writerow(
        ["Market ID", "Player ID", "Player Name", "Circulating", "Sum Holdings", "Sum Events", "Difference"]
    )
    for m in report.circulation_mismatches:
        writer.writerow(
            [
                m.market_id,
                m.player_id,
                m.player_name,
                m.circulating_shares,
                m.sum_holdings,
                m.sum_event_deltas,
                m.difference,
            ]
        )

    return output.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile and audit historical GTEX market inventory.")
    parser.add_argument("--database-url", default=None, help="Database connection URL")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format")
    parser.add_argument("--output", default=None, help="Filepath to write the reconciliation report")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Perform read-only dry run (default True)")
    args = parser.parse_args()

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)

    try:
        with session_factory() as session:
            report = audit_market_inventory(session, dry_run=args.dry_run)

        content: str
        if args.format == "csv":
            content = generate_csv_report(report)
        else:
            content = json.dumps(report.to_dict(), indent=2, sort_keys=True, default=str)

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")
            print(f"Reconciliation report saved to {args.output}")
        else:
            print(content)

        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
