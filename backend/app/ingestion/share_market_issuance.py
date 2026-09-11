"""Compatibility-boundary for the old ingestion-time share-market issuer.

Phase 6 decouples market issuance from player ingestion. The normal ingestion
path may still call this function for compatibility, but it is now disabled
unless explicitly enabled with ``GTE_INGESTION_ISSUANCE_ENABLED=true``.
The independent strict issuer is the normal operational issuance path.
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
ENABLED_ENV_VAR = "GTE_INGESTION_ISSUANCE_ENABLED"
ISSUANCE_RUNNER = "ingestion.share_market_issuance.compatibility"


def issuance_enabled() -> bool:
    return os.environ.get(ENABLED_ENV_VAR, "false").strip().lower() == "true"


def issuance_actor_id() -> str | None:
    value = os.environ.get(ACTOR_ENV_VAR, "").strip()
    return value or None


def issue_markets_for_ingested_players(
    session: Session,
    *,
    player_ids: list[str],
    actor_user_id: str | None = None,
) -> dict[str, int]:
    """Compatibility issuer retained for controlled exception use only."""
    summary = {"issued": 0, "skipped_existing": 0, "skipped_ineligible": 0, "failed": 0}
    if not player_ids:
        return summary

    if not issuance_enabled():
        logger.info(
            "ingestion.share_market_issuance.skipped reason=phase6_decoupled env=%s players=%d",
            ENABLED_ENV_VAR,
            len(player_ids),
        )
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
            summary["failed"] += 1
            logger.exception("ingestion.share_market_issuance.failed player_id=%s", player.id)
            continue

        market.metadata_json = {
            **(market.metadata_json or {}),
            "issuance_runner": ISSUANCE_RUNNER,
        }
        summary["issued"] += 1

    logger.info(
        "ingestion.share_market_issuance.complete issued=%d skipped_existing=%d skipped_ineligible=%d failed=%d",
        summary["issued"],
        summary["skipped_existing"],
        summary["skipped_ineligible"],
        summary["failed"],
    )
    return summary
