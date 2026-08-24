from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ingestion.models import Player
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService


class PlayerShareTradeBoundary:
    """Fail-closed adapter for public player-share trading.

    Trading must never be an issuance mechanism. The underlying token service
    still exposes ``ensure_market`` for legacy/internal callers, so public
    trade callers should pass through this boundary first. The existence check
    deliberately happens before invoking the trade operation and uses a row
    lock when the backend supports it.
    """

    def __init__(self, session: Session, service: PlayerTokenMarketService | None = None) -> None:
        self.session = session
        self.service = service or PlayerTokenMarketService(session)

    def require_issued_market(self, player_id: str) -> PlayerShareMarket:
        market = self.session.scalar(
            select(PlayerShareMarket)
            .options(selectinload(PlayerShareMarket.player))
            .where(PlayerShareMarket.player_id == player_id)
            .with_for_update()
        )
        if market is None:
            raise PlayerTokenMarketError(
                "Player share market has not been issued.",
                reason="market_not_found",
            )
        return market

    def buy(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ):
        self.require_issued_market(player_id)
        return self.service.buy_shares(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            idempotency_key=idempotency_key,
        )

    def sell(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ):
        self.require_issued_market(player_id)
        return self.service.sell_shares(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            idempotency_key=idempotency_key,
        )
