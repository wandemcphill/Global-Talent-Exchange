from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
import os
from pathlib import Path
import sys
from typing import Iterable, Sequence
from uuid import uuid4

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Player, PlayerImageMetadata
from app.models.base import utcnow
from app.models.card_access import CardLoanListing
from app.models.player_cards import (
    PlayerCard,
    PlayerCardHistory,
    PlayerCardHolding,
    PlayerCardListing,
    PlayerCardSupplyBatch,
    PlayerCardTier,
)
from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket
from app.models.regen import RegenProfile, RegenVisualProfile
from app.models.regen_ecosystem import NationalRegenSeed
from app.models.user import User
from app.players.read_models import PlayerSummaryReadModel
from app.services.regen_portrait_service import RegenPortraitService

# Imported for SQLAlchemy relationship mapper resolution in this focused script.
_MAPPER_IMPORTS = (PlayerShareEvent, PlayerShareHolding, RegenVisualProfile)

LAUNCH_REAL_TIER_CODE = "launch_real"
LAUNCH_REGEN_TIER_CODE = "regen_unique"
LAUNCH_EDITION_CODE = "launch_2026"
MONEY = Decimal("0.0001")


@dataclass(slots=True)
class LaunchMarketReport:
    apply: bool
    market_maker_user_id: str | None = None
    player_scope_count: int = 0
    total_players: int = 0
    tradable_players: int = 0
    real_players: int = 0
    regen_players: int = 0
    cards_created: int = 0
    cards_existing: int = 0
    card_supply_added: int = 0
    holdings_created: int = 0
    holdings_topped_up: int = 0
    sale_listings_created: int = 0
    loan_listings_created: int = 0
    regen_portraits_missing: int = 0
    regen_portraits_generated: int = 0
    national_seed_portraits_missing: int = 0
    national_seed_portraits_generated: int = 0
    real_images_missing: int = 0
    real_images_imported: int = 0
    active_share_markets: int = 0
    share_markets_hidden: int = 0
    players_seen: int = 0
    warnings: list[str] = field(default_factory=list)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Activate the launch player-card market: cards, market-maker "
            "holdings, sale/loan listings, regen portraits, and licensed real "
            "image metadata."
        )
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL") or os.environ.get("DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL or DATABASE_URL.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Omit this for a dry-run report.",
    )
    parser.add_argument("--limit", type=int, default=0, help="Limit players processed. 0 means all.")
    parser.add_argument("--market-maker-user-id", help="User id that will own launch listings.")
    parser.add_argument("--market-maker-email", help="User email that will own launch listings.")
    parser.add_argument("--season-label", default="Launch 2026")
    parser.add_argument("--target-card-supply", type=int, default=5)
    parser.add_argument("--sale-quantity", type=int, default=1)
    parser.add_argument("--loan-slots", type=int, default=1)
    parser.add_argument("--loan-duration-days", type=int, default=7)
    parser.add_argument("--sale-price-ratio", type=Decimal, default=Decimal("1.00"))
    parser.add_argument("--loan-fee-ratio", type=Decimal, default=Decimal("0.08"))
    parser.add_argument("--minimum-sale-price", type=Decimal, default=Decimal("25"))
    parser.add_argument("--minimum-loan-fee", type=Decimal, default=Decimal("5"))
    parser.add_argument(
        "--player-id-file",
        type=Path,
        help=(
            "Optional newline/comma separated ingestion_players.id allowlist. "
            "Only scoped tradable players are activated and counted."
        ),
    )
    parser.add_argument("--skip-sales", action="store_true")
    parser.add_argument("--skip-loans", action="store_true")
    parser.add_argument("--skip-regen-portraits", action="store_true")
    parser.add_argument("--skip-national-seed-portraits", action="store_true")
    parser.add_argument(
        "--real-image-csv",
        type=Path,
        help=("Optional licensed portrait CSV with player_id or provider_external_id " "and image_url/source_url."),
    )
    parser.add_argument(
        "--hide-share-markets",
        action="store_true",
        help="Set active player-share markets to launch_blocked while card trading launches.",
    )
    parser.add_argument(
        "--allow-missing-real-images",
        action="store_true",
        help="Allow --apply even when licensed real-player portrait rows are still missing.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url, GTE_DATABASE_URL, or DATABASE_URL is required.")
    if args.apply and not (args.market_maker_user_id or args.market_maker_email):
        raise SystemExit(
            "--apply requires --market-maker-user-id or --market-maker-email "
            "so launch listings are owned by an explicit admin/market account."
        )

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        report = activate_launch_market(session, args)
        if args.apply:
            session.commit()
        else:
            session.rollback()

    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


def activate_launch_market(session: Session, args: argparse.Namespace) -> LaunchMarketReport:
    report = LaunchMarketReport(apply=bool(args.apply))
    target_player_ids = _load_player_id_scope(args)
    report.player_scope_count = len(target_player_ids or ())

    total_players_statement = select(func.count()).select_from(Player)
    tradable_players_statement = select(func.count()).select_from(Player).where(Player.is_tradable.is_(True))
    real_players_statement = select(func.count()).select_from(Player).where(Player.is_real_player.is_(True))
    if target_player_ids is not None:
        total_players_statement = total_players_statement.where(Player.id.in_(target_player_ids))
        tradable_players_statement = tradable_players_statement.where(Player.id.in_(target_player_ids))
        real_players_statement = real_players_statement.where(Player.id.in_(target_player_ids))

    report.total_players = int(session.scalar(total_players_statement) or 0)
    report.tradable_players = int(session.scalar(tradable_players_statement) or 0)
    report.real_players = int(session.scalar(real_players_statement) or 0)
    report.regen_players = max(report.total_players - report.real_players, 0)
    report.active_share_markets = int(
        session.scalar(select(func.count()).select_from(PlayerShareMarket).where(PlayerShareMarket.status == "active"))
        or 0
    )

    market_maker = _resolve_market_maker(session, args)
    if market_maker is not None:
        report.market_maker_user_id = market_maker.id
    elif not args.apply:
        report.warnings.append("Dry-run only: no market-maker user was resolved, so listing writes were only counted.")

    if not args.apply:
        return _dry_run_bulk_report(session, args, report, market_maker, target_player_ids=target_player_ids)

    real_tier = _ensure_tier(
        session,
        args,
        report,
        code=LAUNCH_REAL_TIER_CODE,
        name="Launch Real Player",
        rarity_rank=25,
        color_hex="#2FB344",
    )
    regen_tier = _ensure_tier(
        session,
        args,
        report,
        code=LAUNCH_REGEN_TIER_CODE,
        name="Regen Unique",
        rarity_rank=35,
        color_hex="#7C3AED",
    )
    portrait_service = RegenPortraitService(session)

    for player, summary in _iter_tradable_players(
        session,
        limit=int(args.limit or 0),
        target_player_ids=target_player_ids,
    ):
        report.players_seen += 1
        is_real = bool(player.is_real_player)
        tier = real_tier if is_real else regen_tier
        card = _ensure_card(session, args, report, player, tier=tier, is_real=is_real)
        if market_maker is not None:
            _ensure_holding(session, args, report, card, owner=market_maker)
            _ensure_market_listings(
                session,
                args,
                report,
                card=card,
                owner=market_maker,
                reference_price=_reference_price(player, summary, minimum=args.minimum_sale_price),
            )
        if is_real:
            if not _has_approved_portrait(session, player.id):
                report.real_images_missing += 1
        elif not args.skip_regen_portraits:
            metadata = dict(player.dna_profile or {}) if isinstance(player.dna_profile, dict) else {}
            if not _first_present(metadata, "portraitUrl", "portrait_url", "image_url"):
                report.regen_portraits_missing += 1
                if args.apply:
                    portrait_service.ensure_player_portrait(player)
                    report.regen_portraits_generated += 1

    if args.real_image_csv:
        report.real_images_imported = _import_real_images(session, args)
        report.real_images_missing = max(report.real_images_missing - report.real_images_imported, 0)

    if not args.skip_national_seed_portraits:
        _ensure_national_seed_portraits(session, args, report, portrait_service)

    if args.hide_share_markets and report.active_share_markets:
        if args.apply:
            markets = session.scalars(select(PlayerShareMarket).where(PlayerShareMarket.status == "active")).all()
            for market in markets:
                market.status = "launch_blocked"
                market.metadata_json = {
                    **dict(market.metadata_json or {}),
                    "launchBlockedReason": "2d_player_card_market_launch",
                }
                session.add(market)
            report.share_markets_hidden = len(markets)
        else:
            report.share_markets_hidden = report.active_share_markets

    if report.real_images_missing:
        report.warnings.append(
            "Licensed real-player portrait rows are still missing. "
            "Pass --real-image-csv with cleared image_url/source_url values before launch."
        )
        if args.apply and not args.allow_missing_real_images:
            raise SystemExit(
                "Refusing to apply launch market activation while licensed real-player images are missing. "
                "Provide --real-image-csv or pass --allow-missing-real-images for a deliberate staged activation."
            )
    if report.tradable_players and report.sale_listings_created == 0 and not args.skip_sales:
        report.warnings.append("No sale listings were created; confirm cards already have open listings.")
    return report


def _dry_run_bulk_report(
    session: Session,
    args: argparse.Namespace,
    report: LaunchMarketReport,
    market_maker: User | None,
    *,
    target_player_ids: set[str] | None,
) -> LaunchMarketReport:
    real_tier = session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == LAUNCH_REAL_TIER_CODE))
    regen_tier = session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == LAUNCH_REGEN_TIER_CODE))
    existing_cards = _dry_run_existing_launch_cards(
        session,
        real_tier=real_tier,
        regen_tier=regen_tier,
        target_player_ids=target_player_ids,
    )
    report.cards_existing = len(existing_cards)
    report.cards_created = max(report.tradable_players - report.cards_existing, 0)
    target_supply = max(int(args.target_card_supply or 0), 0)
    report.card_supply_added = (report.cards_created * target_supply) + sum(
        max(target_supply - int(row["supply_total"] or 0), 0) for row in existing_cards
    )
    report.players_seen = report.tradable_players

    if market_maker is not None:
        needed_reserved = max(int(args.sale_quantity or 0), 0) + max(int(args.loan_slots or 0), 0)
        existing_card_ids = [str(row["card_id"]) for row in existing_cards if row.get("card_id")]
        holding_map = _dry_run_holding_map(session, existing_card_ids, market_maker.id)
        for card_id in existing_card_ids:
            holding = holding_map.get(card_id)
            if holding is None:
                report.holdings_created += 1
                continue
            available = int(holding["quantity_total"] or 0) - int(holding["quantity_reserved"] or 0)
            if available < needed_reserved:
                report.holdings_topped_up += needed_reserved - available
        report.holdings_created += report.cards_created

        if not args.skip_sales and int(args.sale_quantity or 0) > 0:
            report.sale_listings_created = report.cards_created + _dry_run_unlisted_existing_cards(
                session,
                existing_card_ids,
                market_maker.id,
                listing_model=PlayerCardListing,
                owner_column=PlayerCardListing.seller_user_id,
            )
        if not args.skip_loans and int(args.loan_slots or 0) > 0:
            report.loan_listings_created = report.cards_created + _dry_run_unlisted_existing_cards(
                session,
                existing_card_ids,
                market_maker.id,
                listing_model=CardLoanListing,
                owner_column=CardLoanListing.owner_user_id,
            )

    if not args.skip_regen_portraits:
        report.regen_portraits_missing = _count_missing_regen_portraits(session, target_player_ids=target_player_ids)
    if not args.skip_national_seed_portraits:
        report.national_seed_portraits_missing = _count_missing_national_seed_portraits(
            session, limit=int(args.limit or 0)
        )
    report.real_images_missing = _count_missing_real_player_images(session, target_player_ids=target_player_ids)
    if args.real_image_csv:
        report.real_images_imported = _import_real_images(session, args)
        report.real_images_missing = max(report.real_images_missing - report.real_images_imported, 0)
    if args.hide_share_markets:
        report.share_markets_hidden = report.active_share_markets
    if report.real_images_missing:
        report.warnings.append(
            "Licensed real-player portrait rows are still missing. "
            "Pass --real-image-csv with cleared image_url/source_url values before launch."
        )
    if report.tradable_players and report.sale_listings_created == 0 and not args.skip_sales:
        report.warnings.append("No sale listings were created; confirm cards already have open listings.")
    return report


def _dry_run_existing_launch_cards(
    session: Session,
    *,
    real_tier: PlayerCardTier | None,
    regen_tier: PlayerCardTier | None,
    target_player_ids: set[str] | None = None,
) -> list[dict[str, object]]:
    tier_ids = [tier.id for tier in (real_tier, regen_tier) if tier is not None]
    if not tier_ids:
        return []
    statement = (
        select(PlayerCard.id, PlayerCard.player_id, PlayerCard.supply_total)
        .join(Player, Player.id == PlayerCard.player_id)
        .where(
            Player.is_tradable.is_(True),
            PlayerCard.edition_code == LAUNCH_EDITION_CODE,
            PlayerCard.tier_id.in_(tier_ids),
        )
    )
    if target_player_ids is not None:
        statement = statement.where(Player.id.in_(target_player_ids))
    rows = session.execute(statement).all()
    return [
        {
            "card_id": row.id,
            "player_id": row.player_id,
            "supply_total": row.supply_total,
        }
        for row in rows
    ]


def _dry_run_holding_map(session: Session, card_ids: list[str], owner_id: str) -> dict[str, dict[str, object]]:
    if not card_ids:
        return {}
    rows = session.execute(
        select(
            PlayerCardHolding.player_card_id, PlayerCardHolding.quantity_total, PlayerCardHolding.quantity_reserved
        ).where(
            PlayerCardHolding.player_card_id.in_(card_ids),
            PlayerCardHolding.owner_user_id == owner_id,
        )
    ).all()
    return {
        row.player_card_id: {
            "quantity_total": row.quantity_total,
            "quantity_reserved": row.quantity_reserved,
        }
        for row in rows
    }


def _dry_run_unlisted_existing_cards(
    session: Session,
    card_ids: list[str],
    owner_id: str,
    *,
    listing_model: object,
    owner_column: object,
) -> int:
    if not card_ids:
        return 0
    listed_ids = set(
        session.scalars(
            select(listing_model.player_card_id).where(
                listing_model.player_card_id.in_(card_ids),
                owner_column == owner_id,
                listing_model.status == "open",
            )
        ).all()
    )
    return len([card_id for card_id in card_ids if card_id not in listed_ids])


def _count_missing_regen_portraits(session: Session, *, target_player_ids: set[str] | None = None) -> int:
    statement = (
        select(Player.dna_profile)
        .join(RegenProfile, RegenProfile.player_id == Player.id)
        .where(Player.is_tradable.is_(True), Player.is_real_player.is_(False))
    )
    if target_player_ids is not None:
        statement = statement.where(Player.id.in_(target_player_ids))
    rows = session.execute(statement).all()
    total = 0
    for (dna_profile,) in rows:
        metadata = dict(dna_profile or {}) if isinstance(dna_profile, dict) else {}
        if not _first_present(metadata, "portraitUrl", "portrait_url", "image_url"):
            total += 1
    return total


def _count_missing_national_seed_portraits(session: Session, *, limit: int = 0) -> int:
    statement = select(NationalRegenSeed.metadata_json)
    if limit > 0:
        statement = statement.limit(limit)
    total = 0
    for (metadata_json,) in session.execute(statement):
        metadata = dict(metadata_json or {}) if isinstance(metadata_json, dict) else {}
        if not _first_present(metadata, "portraitUrl", "portrait_url", "image_url"):
            total += 1
    return total


def _count_missing_real_player_images(session: Session, *, target_player_ids: set[str] | None = None) -> int:
    approved_image_exists = exists().where(
        PlayerImageMetadata.player_id == Player.id,
        PlayerImageMetadata.image_role == "portrait",
        PlayerImageMetadata.moderation_status == "approved",
        PlayerImageMetadata.rights_cleared.is_(True),
        PlayerImageMetadata.source_url.is_not(None),
    )
    statement = (
        select(func.count())
        .select_from(Player)
        .where(
            Player.is_tradable.is_(True),
            Player.is_real_player.is_(True),
            ~approved_image_exists,
        )
    )
    if target_player_ids is not None:
        statement = statement.where(Player.id.in_(target_player_ids))
    return int(session.scalar(statement) or 0)


def _load_player_id_scope(args: argparse.Namespace) -> set[str] | None:
    path: Path | None = args.player_id_file
    if path is None:
        return None
    if not path.exists():
        raise SystemExit(f"Player id scope file not found: {path}")
    player_ids: set[str] = set()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        for raw_value in stripped.replace(",", " ").split():
            value = raw_value.strip()
            if not value or value.lower() in {"id", "player_id"}:
                continue
            player_ids.add(value)
    if not player_ids:
        raise SystemExit(f"Player id scope file did not contain any ids: {path}")
    return player_ids


def _resolve_market_maker(session: Session, args: argparse.Namespace) -> User | None:
    if args.market_maker_user_id:
        return session.get(User, args.market_maker_user_id)
    if args.market_maker_email:
        return session.scalar(select(User).where(func.lower(User.email) == args.market_maker_email.lower()))
    return None


def _ensure_tier(
    session: Session,
    args: argparse.Namespace,
    report: LaunchMarketReport,
    *,
    code: str,
    name: str,
    rarity_rank: int,
    color_hex: str,
) -> PlayerCardTier:
    tier = session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == code))
    if tier is not None:
        return tier
    if not args.apply:
        return PlayerCardTier(
            code=code,
            name=name,
            rarity_rank=rarity_rank,
            color_hex=color_hex,
            max_supply=None,
            base_mint_price_credits=Decimal("0"),
            metadata_json={"dry_run_placeholder": True},
        )
    tier = PlayerCardTier(
        code=code,
        name=name,
        rarity_rank=rarity_rank,
        color_hex=color_hex,
        max_supply=None,
        base_mint_price_credits=Decimal("0"),
        metadata_json={"source": "launch_market_activation"},
    )
    session.add(tier)
    session.flush()
    report.warnings.append(f"Created missing card tier {code}.")
    return tier


def _iter_tradable_players(
    session: Session,
    *,
    limit: int,
    target_player_ids: set[str] | None = None,
) -> Iterable[tuple[Player, PlayerSummaryReadModel | None]]:
    statement = (
        select(Player, PlayerSummaryReadModel)
        .outerjoin(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
        .where(Player.is_tradable.is_(True))
        .order_by(Player.is_real_player.desc(), Player.full_name.asc())
    )
    if target_player_ids is not None:
        statement = statement.where(Player.id.in_(target_player_ids))
    if limit > 0:
        statement = statement.limit(limit)
    return session.execute(statement).all()


def _ensure_card(
    session: Session,
    args: argparse.Namespace,
    report: LaunchMarketReport,
    player: Player,
    *,
    tier: PlayerCardTier,
    is_real: bool,
) -> PlayerCard:
    card = session.scalar(
        select(PlayerCard).where(
            PlayerCard.player_id == player.id,
            PlayerCard.tier_id == tier.id,
            PlayerCard.edition_code == LAUNCH_EDITION_CODE,
        )
    )
    if card is None:
        report.cards_created += 1
        card = PlayerCard(
            player_id=player.id,
            tier_id=tier.id,
            edition_code=LAUNCH_EDITION_CODE,
            display_name=player.canonical_display_name or player.full_name,
            season_label=args.season_label,
            card_variant="real_player" if is_real else "regen",
            supply_total=0,
            supply_available=0,
            metadata_json={
                "source": "launch_market_activation",
                "realPlayer": is_real,
            },
        )
        if args.apply:
            session.add(card)
            session.flush()
    else:
        report.cards_existing += 1

    target_supply = max(int(args.target_card_supply or 0), 0)
    missing_supply = max(target_supply - int(card.supply_total or 0), 0)
    if missing_supply:
        report.card_supply_added += missing_supply
        if args.apply:
            card.supply_total = int(card.supply_total or 0) + missing_supply
            card.supply_available = int(card.supply_available or 0) + missing_supply
            session.add(
                PlayerCardSupplyBatch(
                    batch_key=f"launch-market:{card.player_id}:{card.tier_id}:{LAUNCH_EDITION_CODE}",
                    player_card_id=card.id,
                    player_id=player.id,
                    tier_id=tier.id,
                    quantity=missing_supply,
                    source_type="launch_market_activation",
                    source_reference=LAUNCH_EDITION_CODE,
                    notes="Launch market activation supply.",
                    metadata_json={"target_supply": target_supply},
                )
            )
            session.add(
                PlayerCardHistory(
                    player_card_id=card.id,
                    event_type="launch_supply_added",
                    description="Launch player-card market supply activated.",
                    delta_supply=missing_supply,
                    delta_available=missing_supply,
                    metadata_json={"source": "launch_market_activation"},
                )
            )
            session.add(card)
    return card


def _ensure_holding(
    session: Session,
    args: argparse.Namespace,
    report: LaunchMarketReport,
    card: PlayerCard,
    *,
    owner: User,
) -> PlayerCardHolding:
    holding = session.scalar(
        select(PlayerCardHolding).where(
            PlayerCardHolding.player_card_id == card.id,
            PlayerCardHolding.owner_user_id == owner.id,
        )
    )
    needed = max(int(args.sale_quantity or 0), 0) + max(int(args.loan_slots or 0), 0)
    if holding is None:
        report.holdings_created += 1
        holding = PlayerCardHolding(
            player_card_id=card.id,
            owner_user_id=owner.id,
            quantity_total=max(needed, int(args.target_card_supply or 0)),
            quantity_reserved=0,
            last_acquired_at=utcnow(),
            metadata_json={"source": "launch_market_activation"},
        )
        if args.apply:
            session.add(holding)
            session.flush()
        return holding

    available = int(holding.quantity_total or 0) - int(holding.quantity_reserved or 0)
    if available < needed:
        delta = needed - available
        report.holdings_topped_up += delta
        if args.apply:
            holding.quantity_total = int(holding.quantity_total or 0) + delta
            holding.last_acquired_at = utcnow()
            holding.metadata_json = {
                **dict(holding.metadata_json or {}),
                "launchMarketTopupAt": utcnow().isoformat(),
            }
            session.add(holding)
    return holding


def _ensure_market_listings(
    session: Session,
    args: argparse.Namespace,
    report: LaunchMarketReport,
    *,
    card: PlayerCard,
    owner: User,
    reference_price: Decimal,
) -> None:
    if not args.skip_sales and int(args.sale_quantity or 0) > 0:
        existing_sale = session.scalar(
            select(PlayerCardListing).where(
                PlayerCardListing.player_card_id == card.id,
                PlayerCardListing.seller_user_id == owner.id,
                PlayerCardListing.status == "open",
            )
        )
        if existing_sale is None:
            report.sale_listings_created += 1
            if args.apply:
                session.add(
                    PlayerCardListing(
                        listing_id=str(uuid4()),
                        player_card_id=card.id,
                        seller_user_id=owner.id,
                        quantity=int(args.sale_quantity),
                        price_per_card_credits=_money(
                            max(reference_price * args.sale_price_ratio, args.minimum_sale_price)
                        ),
                        status="open",
                        is_negotiable=False,
                        metadata_json={"source": "launch_market_activation"},
                    )
                )
                _reserve_holding(session, card.id, owner.id, int(args.sale_quantity))

    if not args.skip_loans and int(args.loan_slots or 0) > 0:
        existing_loan = session.scalar(
            select(CardLoanListing).where(
                CardLoanListing.player_card_id == card.id,
                CardLoanListing.owner_user_id == owner.id,
                CardLoanListing.status == "open",
            )
        )
        if existing_loan is None:
            report.loan_listings_created += 1
            if args.apply:
                session.add(
                    CardLoanListing(
                        player_card_id=card.id,
                        owner_user_id=owner.id,
                        total_slots=int(args.loan_slots),
                        available_slots=int(args.loan_slots),
                        duration_days=int(args.loan_duration_days),
                        loan_fee_credits=_money(max(reference_price * args.loan_fee_ratio, args.minimum_loan_fee)),
                        currency="gtex_coin",
                        status="open",
                        is_negotiable=True,
                        expires_at=utcnow() + timedelta(days=30),
                        terms_json={"source": "launch_market_activation"},
                        metadata_json={"source": "launch_market_activation"},
                    )
                )
                _reserve_holding(session, card.id, owner.id, int(args.loan_slots))


def _reserve_holding(session: Session, card_id: str, owner_id: str, quantity: int) -> None:
    holding = session.scalar(
        select(PlayerCardHolding).where(
            PlayerCardHolding.player_card_id == card_id,
            PlayerCardHolding.owner_user_id == owner_id,
        )
    )
    if holding is None:
        return
    holding.quantity_reserved = int(holding.quantity_reserved or 0) + quantity
    session.add(holding)


def _reference_price(player: Player, summary: PlayerSummaryReadModel | None, *, minimum: Decimal) -> Decimal:
    raw = None
    if summary is not None:
        raw = summary.current_value_credits
    if raw is None:
        raw = player.current_market_reference_value
    try:
        price = Decimal(str(raw))
    except Exception:
        price = minimum
    return _money(max(price, minimum))


def _ensure_national_seed_portraits(
    session: Session,
    args: argparse.Namespace,
    report: LaunchMarketReport,
    portrait_service: RegenPortraitService,
) -> None:
    statement = select(NationalRegenSeed).order_by(NationalRegenSeed.country_code, NationalRegenSeed.display_name)
    if int(args.limit or 0) > 0:
        statement = statement.limit(int(args.limit))
    for seed in session.scalars(statement):
        metadata = dict(seed.metadata_json or {}) if isinstance(seed.metadata_json, dict) else {}
        if _first_present(metadata, "portraitUrl", "portrait_url", "image_url"):
            continue
        report.national_seed_portraits_missing += 1
        if args.apply:
            portrait_service.ensure_national_seed_portrait(seed)
            report.national_seed_portraits_generated += 1


def _import_real_images(session: Session, args: argparse.Namespace) -> int:
    path: Path = args.real_image_csv
    if not path.exists():
        raise SystemExit(f"Real image CSV not found: {path}")
    imported = 0
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            url = (row.get("image_url") or row.get("source_url") or "").strip()
            if not url:
                continue
            player = _resolve_image_player(session, row)
            if player is None or not bool(player.is_real_player):
                continue
            imported += 1
            if not args.apply:
                continue
            provider = (row.get("source_provider") or "licensed_real_player_image").strip()
            provider_external_id = (
                row.get("image_external_id") or row.get("provider_external_id") or f"{provider}:{player.id}:portrait"
            ).strip()
            image = session.scalar(
                select(PlayerImageMetadata).where(
                    PlayerImageMetadata.player_id == player.id,
                    PlayerImageMetadata.image_role == "portrait",
                )
            )
            if image is None:
                image = PlayerImageMetadata(
                    source_provider=provider,
                    provider_external_id=provider_external_id,
                    player_id=player.id,
                    image_role="portrait",
                )
                session.add(image)
            image.source_provider = provider
            image.provider_external_id = provider_external_id
            image.source_url = url
            image.storage_key = (row.get("storage_key") or "").strip() or None
            image.mime_type = (row.get("mime_type") or "image/jpeg").strip()
            image.moderation_status = (row.get("moderation_status") or "approved").strip()
            image.rights_cleared = _boolish(row.get("rights_cleared"), default=True)
            image.is_primary = True
            image.last_processed_at = utcnow()
            session.add(image)
    return imported


def _resolve_image_player(session: Session, row: dict[str, str]) -> Player | None:
    player_id = (row.get("player_id") or "").strip()
    if player_id:
        player = session.get(Player, player_id)
        if player is not None:
            return player
    provider_external_id = (row.get("provider_external_id") or "").strip()
    if provider_external_id:
        player = session.scalar(select(Player).where(Player.provider_external_id == provider_external_id))
        if player is not None:
            return player
    player_name = (row.get("player_name") or row.get("name") or "").strip()
    if player_name:
        return session.scalar(select(Player).where(func.lower(Player.full_name) == player_name.lower()))
    return None


def _has_approved_portrait(session: Session, player_id: str) -> bool:
    image = session.scalar(
        select(PlayerImageMetadata).where(
            PlayerImageMetadata.player_id == player_id,
            PlayerImageMetadata.image_role == "portrait",
            PlayerImageMetadata.moderation_status == "approved",
            PlayerImageMetadata.rights_cleared.is_(True),
        )
    )
    return image is not None and bool((image.source_url or image.storage_key or "").strip())


def _first_present(values: dict[str, object], *keys: str) -> str | None:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def _boolish(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "y", "approved", "cleared"}


if __name__ == "__main__":
    raise SystemExit(main())
