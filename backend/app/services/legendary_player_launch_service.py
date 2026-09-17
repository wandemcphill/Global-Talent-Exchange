from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Player
from app.market.player_eligibility_policy import is_share_market_eligible
from app.models.legendary_player import LegendaryPlayerProfile
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User
from app.players.token_market_defaults import resolve_player_share_market_config
from app.players.token_service import PlayerTokenMarketError, PlayerTokenMarketService
from app.schemas.legendary_player import LegendaryPlayerProfileCreate, LegendarySeedImportRequest
from app.services.legendary_player_service import LegendaryPlayerRegistryService


class LegendaryPlayerLaunchError(ValueError):
    pass


@dataclass(slots=True)
class LegendaryPlayerLaunchService:
    """Canonical launch boundary for a fully materialized legendary player.

    The registry remains the source of truth for historical identity and
    football attributes. This service adds the explicit, admin-attributed
    production market issuance step using the same strict issuer used by GTEX.
    The caller owns the surrounding transaction.
    """

    session: Session

    @property
    def registry(self) -> LegendaryPlayerRegistryService:
        return LegendaryPlayerRegistryService(self.session)

    def materialize(
        self,
        profile: LegendaryPlayerProfileCreate,
        *,
        actor: User,
    ) -> tuple[LegendaryPlayerProfile, Player, PlayerShareMarket]:
        stored_profile, _created = self.registry.upsert_legendary_profile(profile)
        player = self.registry.instantiate_gtex_player(stored_profile)
        market = self.issue_active_market(player=player, actor=actor)
        self.session.flush()
        return stored_profile, player, market

    def materialize_bulk(
        self,
        request: LegendarySeedImportRequest,
        *,
        actor: User,
    ) -> list[tuple[LegendaryPlayerProfile, Player, PlayerShareMarket]]:
        results: list[tuple[LegendaryPlayerProfile, Player, PlayerShareMarket]] = []
        for item in request.profiles:
            results.append(self.materialize(item, actor=actor))
        self.session.flush()
        return results

    def issue_active_market(self, *, player: Player, actor: User) -> PlayerShareMarket:
        existing = self.session.scalar(
            select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)
        )
        if existing is not None:
            if existing.status != "active":
                raise LegendaryPlayerLaunchError(
                    f"Legendary player {player.id} already has a non-active market ({existing.status})."
                )
            return existing

        if not bool(player.is_tradable):
            raise LegendaryPlayerLaunchError("Legendary player must be tradable before market issuance.")
        if not is_share_market_eligible(player):
            raise LegendaryPlayerLaunchError("Legendary player is not eligible for a player-share market.")

        config = resolve_player_share_market_config(player, status="active")
        try:
            market = PlayerTokenMarketService(self.session).issue_market(
                actor=actor,
                player_id=player.id,
                total_shares=config.total_shares,
                share_price_coin=config.share_price_coin,
                liquidity_coin=config.liquidity_coin,
                status="active",
            )
        except PlayerTokenMarketError as exc:
            raise LegendaryPlayerLaunchError(
                f"Legendary player market issuance failed: {exc.detail}"
            ) from exc

        if market.status != "active":
            raise LegendaryPlayerLaunchError(
                f"Legendary player market was issued with unexpected status {market.status!r}."
            )
        return market


__all__ = ["LegendaryPlayerLaunchError", "LegendaryPlayerLaunchService"]
