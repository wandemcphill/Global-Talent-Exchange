from __future__ import annotations

from contextvars import ContextVar
from typing import Callable, Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.player_token_market import PlayerShareMarket
from app.models.user import User
from app.players import legacy_token_service as _legacy

PlayerTokenMarketError = _legacy.PlayerTokenMarketError

_trade_reference: ContextVar[str | None] = ContextVar("player_share_trade_reference", default=None)
_original_generate_uuid = _legacy.generate_uuid


def _ledger_reference_token() -> str:
    """Return the request-scoped durable trade reference token, never a fresh UUID."""
    reference = _trade_reference.get()
    if reference:
        return reference
    return _original_generate_uuid()


# Issuance/bootstrap keeps its legacy UUID behavior. Only trade calls receive
# the deterministic reference through the request-scoped context below.
_legacy.generate_uuid = _ledger_reference_token


class PlayerTokenMarketService(_legacy.PlayerTokenMarketService):
    """Production-facing player-share service with a strict trade boundary.

    Legacy ``ensure_market`` remains available to explicit issuance/bootstrap
    callers. During buy/sell, the already-issued market is injected into the
    inherited implementation so it cannot create one implicitly.
    """

    _trade_market_override: PlayerShareMarket | None = None

    @staticmethod
    def _trade_reference(
        *,
        market_id: str,
        actor_id: str,
        side: str,
        circulating_shares: int,
        share_count: int,
    ) -> str:
        return (
            f"market:{market_id}:actor:{actor_id}:side:{side}:"
            f"before:{int(circulating_shares)}:shares:{int(share_count)}"
        )

    def _require_trade_market(self, player_id: str) -> PlayerShareMarket:
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

    def ensure_market(self, *, player_id: str, **kwargs: Any):
        override = self._trade_market_override
        if override is not None and override.player_id == player_id:
            return override
        return super().ensure_market(player_id=player_id, **kwargs)

    def _run_trade_with_boundary(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        side: str,
        operation: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        market = self._require_trade_market(player_id)
        reference = self._trade_reference(
            market_id=market.id,
            actor_id=actor.id,
            side=side,
            circulating_shares=int(market.circulating_shares or 0),
            share_count=share_count,
        )
        previous_override = self._trade_market_override
        reference_token = _trade_reference.set(reference)
        self._trade_market_override = market
        try:
            return operation()
        finally:
            self._trade_market_override = previous_override
            _trade_reference.reset(reference_token)

    def buy_shares(self, *, actor: User, player_id: str, share_count: int) -> dict[str, Any]:
        return self._run_trade_with_boundary(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            side="buy",
            operation=lambda: super(PlayerTokenMarketService, self).buy_shares(
                actor=actor,
                player_id=player_id,
                share_count=share_count,
            ),
        )

    def sell_shares(self, *, actor: User, player_id: str, share_count: int) -> dict[str, Any]:
        return self._run_trade_with_boundary(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            side="sell",
            operation=lambda: super(PlayerTokenMarketService, self).sell_shares(
                actor=actor,
                player_id=player_id,
                share_count=share_count,
            ),
        )


__all__ = ["PlayerTokenMarketError", "PlayerTokenMarketService"]
