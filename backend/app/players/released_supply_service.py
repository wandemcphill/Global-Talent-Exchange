from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.player_token_market import PlayerShareMarket
from app.models.user import User
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService


class ReleasedSupplyPlayerTokenMarketService(PlayerTokenMarketService):
    """Production player-share service with explicit primary released supply.

    Legacy markets with ``released_shares`` unset retain their historical
    ``total_shares - circulating_shares`` supply behavior until an explicit
    reconciliation is performed. Newly issued markets can opt into an explicit
    released amount, which the primary buy path enforces.
    """

    def _locked_market_for_release(self, player_id: str) -> PlayerShareMarket:
        market = self.session.scalar(
            select(PlayerShareMarket)
            .options(selectinload(PlayerShareMarket.player))
            .where(PlayerShareMarket.player_id == player_id)
            .with_for_update()
        )
        if market is None:
            raise PlayerTokenMarketError("Player share market was not found.", reason="market_not_found")
        return market

    def buy_shares(
        self,
        *,
        actor: User,
        player_id: str,
        share_count: int,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if share_count <= 0:
            raise PlayerTokenMarketError("Share count must be greater than zero.", reason="share_count_invalid")

        market = self._locked_market_for_release(player_id)
        self._assert_share_market_eligible(market.player)
        if market.status != "active":
            raise PlayerTokenMarketError("Player share market is not active.", reason="market_inactive")

        released = market.released_shares
        available = (
            int(released) - int(market.circulating_shares or 0)
            if released is not None
            else int(market.total_shares or 0) - int(market.circulating_shares or 0)
        )
        if share_count > max(0, available):
            raise PlayerTokenMarketError(
                "Requested shares exceed currently released supply.",
                reason="share_supply_insufficient",
            )

        return super().buy_shares(
            actor=actor,
            player_id=player_id,
            share_count=share_count,
            idempotency_key=idempotency_key,
        )

    def release_shares(
        self,
        *,
        actor: User,
        player_id: str,
        release_count: int,
    ) -> PlayerShareMarket:
        self._require_admin(actor)
        if release_count <= 0:
            raise PlayerTokenMarketError("Release count must be greater than zero.", reason="release_invalid")

        market = self._locked_market_for_release(player_id)
        if market.released_shares is None:
            raise PlayerTokenMarketError(
                "Released supply is unknown for this legacy market and must be reconciled before more supply is released.",
                reason="released_supply_unknown",
            )

        released_before = int(market.released_shares)
        target = released_before + int(release_count)
        if target > int(market.total_shares or 0):
            raise PlayerTokenMarketError(
                "Released supply cannot exceed lifetime total supply.",
                reason="released_supply_exceeds_total",
            )
        if target < int(market.circulating_shares or 0):
            raise PlayerTokenMarketError(
                "Released supply cannot be below circulating ownership.",
                reason="released_supply_below_circulation",
            )

        market.released_shares = target
        metadata = dict(market.metadata_json or {})
        metadata.update(
            {
                "released_supply_last_actor_user_id": actor.id,
                "released_supply_last_release_count": int(release_count),
                "released_supply_last_released_at": "pending_commit",
            }
        )
        market.metadata_json = metadata
        self._record_event(
            player_id=player_id,
            actor_user_id=actor.id,
            event_type="release",
            share_delta=0,
            price_per_share_coin=self._amount(market.share_price_coin),
            gross_amount_coin=self._amount(0),
            metadata_json={
                "market_id": market.id,
                "released_before": released_before,
                "released_after": target,
                "release_count": int(release_count),
                "total_shares": int(market.total_shares or 0),
                "circulating_shares": int(market.circulating_shares or 0),
            },
        )
        self.session.flush()
        return market

    def _serialize_market_view(self, market: PlayerShareMarket) -> dict[str, Any]:
        payload = super()._serialize_market_view(market)
        payload["released_shares"] = market.released_shares
        return payload

    def _serialize_market_list_item(self, market: PlayerShareMarket) -> dict[str, Any]:
        payload = super()._serialize_market_list_item(market)
        payload["released_shares"] = market.released_shares
        return payload


__all__ = ["ReleasedSupplyPlayerTokenMarketService"]
