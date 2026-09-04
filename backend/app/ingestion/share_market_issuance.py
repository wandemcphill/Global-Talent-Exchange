"""Issue player-share markets for freshly ingested players.

Ingestion writes profiles and pricing but historically never issued share
markets, so every ingested player arrived tradable-but-unissued.  The market
listing papered over that by lazily creating a market per listed row inside a
GET -- wallet, transaction and ledger postings included, ~17 queries a row, and
rolled back because a read path never commits, so the work was redone on every
request and never actually persisted.

The listing is now read-only, which means issuance has to happen where the
player is created.  This module is that step: it runs inside the ingestion
transaction so a batch either lands with markets or does not land at all.

Issuance stays admin-attributed via the strict
``PlayerTokenMarketService.issue_market`` path (it records a
``player_share_events`` row per issuance) rather than the legacy
``ensure_market`` compatibility shim, which must never be a source of issuance
provenance.

Configure the attributed actor with ``GTE_INGESTION_ISSUANCE_ACTOR_USER_ID``.
When it is unset or does not resolve to a user, issuance is skipped and the
batch still lands -- ingestion must not start failing because an operational
setting is missing.
"""

from __future__ import annotations

import logging
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.market.player_eligibility_policy import is_share_market_eligible
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User
from app.players.legacy_token_service import PlayerTokenMarketError, PlayerTokenMarketService
from app.players.token_market_defaults import resolve_player_share_market_config

logger = logging.getLogger(__name__)

ACTOR_ENV_VAR = "GTE_INGESTION_ISSUANCE_ACTOR_USER_ID"
ISSUANCE_RUNNER = "ingestion.share_market_issuance"


def issuance_actor_id() -> str | None:
    value = os.environ.get(ACTOR_ENV_VAR, "").strip()
    return value or None


def issue_markets_for_ingested_players(
    session: Session,
    *,
    player_ids: list[str],
    actor_user_id: str | None = None,
) -> dict[str, int]:
    """Issue a share market for each ingested player that does not have one.

    Idempotent: players that already hold a market row are skipped, so a
    re-ingested batch does not double-issue.
    """
    summary = {"issued": 0, "skipped_existing": 0, "skipped_ineligible": 0, "failed": 0}
    if not player_ids:
        return summary

    actor_id = actor_user_id or issuance_actor_id()
    if actor_id is None:
        logger.warning(
            "ingestion.share_market_issuance.skipped reason=actor_not_configured env=%s players=%d",
            ACTOR_ENV_VAR,
            len(player_ids),
        )
        return summary

    actor = session.scalar(select(User).where(User.id == actor_id))
    if actor is None:
        logger.warning(
            "ingestion.share_market_issuance.skipped reason=actor_not_found actor_id=%s players=%d",
            actor_id,
            len(player_ids),
        )
        return summary

    # One query for the whole batch rather than a per-player existence check.
    already_issued = set(
        session.scalars(select(PlayerShareMarket.player_id).where(PlayerShareMarket.player_id.in_(player_ids)))
    )
    players = list(session.scalars(select(Player).where(Player.id.in_(player_ids))))
    service = PlayerTokenMarketService(session)

    for player in players:
        if player.id in already_issued:
            summary["skipped_existing"] += 1
            continue
        if not bool(player.is_tradable) or not is_share_market_eligible(player):
            summary["skipped_ineligible"] += 1
            continue

        config = resolve_player_share_market_config(player)
        try:
            market = service.issue_market(
                actor=actor,
                player_id=player.id,
                total_shares=config.total_shares,
                share_price_coin=config.share_price_coin,
                liquidity_coin=config.liquidity_coin,
                status=config.status,
            )
        except PlayerTokenMarketError:
            # A single ineligible or conflicting player must not abort the
            # whole ingestion batch; the counts surface it instead.
            summary["failed"] += 1
            logger.exception("ingestion.share_market_issuance.failed player_id=%s", player.id)
            continue

        market.metadata_json = {
            **(market.metadata_json or {}),
            "issuance_runner": ISSUANCE_RUNNER,
        }
        summary["issued"] += 1

    logger.info(
        "ingestion.share_market_issuance.complete issued=%d skipped_existing=%d " "skipped_ineligible=%d failed=%d",
        summary["issued"],
        summary["skipped_existing"],
        summary["skipped_ineligible"],
        summary["failed"],
    )
    return summary
