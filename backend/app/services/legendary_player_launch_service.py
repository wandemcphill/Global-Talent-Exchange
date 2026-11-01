from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, or_, select
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
    """Canonical launch boundary for a fully approved legendary player.

    The registry remains the source of truth for historical identity and
    football attributes. This service adds the explicit approval gate and the
    admin-attributed production market issuance step using the same strict
    issuer used by GTEX. The caller owns the surrounding transaction.
    """

    session: Session

    @property
    def registry(self) -> LegendaryPlayerRegistryService:
        return LegendaryPlayerRegistryService(self.session)

    def _assert_no_active_player_promotion(self, profile: LegendaryPlayerProfileCreate) -> None:
        if profile.date_of_birth is None:
            return
        age = date.today().year - profile.date_of_birth.year
        if (date.today().month, date.today().day) < (profile.date_of_birth.month, profile.date_of_birth.day):
            age -= 1
        if age >= 31:
            return

        normalized_name = profile.full_name.strip().lower()
        candidates = self.session.scalars(
            select(Player).where(
                or_(
                    func.lower(Player.full_name) == normalized_name,
                    func.lower(Player.canonical_display_name) == normalized_name,
                    func.lower(Player.short_name) == normalized_name,
                )
            )
        ).all()
        for player in candidates:
            source = str(player.source_provider or "").strip().lower()
            tier = str(player.real_player_tier or "").strip().lower()
            if (
                not bool(player.is_tradable)
                or source in {"gtex_legend", "gtex_legend_prime"}
                or tier in {"legend", "legendary", "icon", "immortal", "world_class", "hero"}
            ):
                continue

            active_age = None
            if player.date_of_birth is not None:
                active_age = date.today().year - player.date_of_birth.year
                if (date.today().month, date.today().day) < (
                    player.date_of_birth.month,
                    player.date_of_birth.day,
                ):
                    active_age -= 1

            dna = player.dna_profile if isinstance(player.dna_profile, dict) else {}
            current_ratings = [
                dna.get("overall"),
                dna.get("current_rating"),
                dna.get("sofifa_overall"),
                player.rating,
            ]
            current_gsi = max(
                (
                    int(float(value))
                    for value in current_ratings
                    if isinstance(value, (int, float)) and float(value) > 0
                ),
                default=0,
            )
            if (active_age is not None and active_age < 31) or current_gsi >= 80:
                raise LegendaryPlayerLaunchError(
                    f"{profile.full_name} already has an active real-player identity "
                    f"(age {active_age if active_age is not None else 'unknown'}, current GSI {current_gsi}); "
                    "keep that identity active instead of launching a legend duplicate."
                )

    @staticmethod
    def _assert_launch_approved(profile: LegendaryPlayerProfileCreate) -> None:
        if profile.editorial_status != "approved":
            raise LegendaryPlayerLaunchError(f"Legendary profile {profile.slug!r} is not editorially approved.")
        if profile.rights_status != "approved":
            raise LegendaryPlayerLaunchError(f"Legendary profile {profile.slug!r} does not have rights approval.")
        if profile.catalogue_status not in {"approved", "imported"}:
            raise LegendaryPlayerLaunchError(
                f"Legendary profile {profile.slug!r} is not release-approved ({profile.catalogue_status!r})."
            )
        if profile.portrait_metadata.get("is_fictional_non_replicative") is not True:
            raise LegendaryPlayerLaunchError(
                f"Legendary profile {profile.slug!r} lacks approved fictional/non-replicative portrait metadata."
            )
        forbidden_portrait_keys = {
            "source_image_ref",
            "image",
            "image_url",
            "reference_image_url",
            "portrait_url",
        }
        if forbidden_portrait_keys.intersection(profile.portrait_metadata):
            raise LegendaryPlayerLaunchError(
                f"Legendary profile {profile.slug!r} contains a source portrait reference."
            )

    def materialize(
        self,
        profile: LegendaryPlayerProfileCreate,
        *,
        actor: User,
    ) -> tuple[LegendaryPlayerProfile, Player, PlayerShareMarket]:
        self._assert_launch_approved(profile)
        self._assert_no_active_player_promotion(profile)
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
        existing = self.session.scalar(select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id))
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
            raise LegendaryPlayerLaunchError(f"Legendary player market issuance failed: {exc.detail}") from exc

        if market.status != "active":
            raise LegendaryPlayerLaunchError(
                f"Legendary player market was issued with unexpected status {market.status!r}."
            )
        return market


__all__ = ["LegendaryPlayerLaunchError", "LegendaryPlayerLaunchService"]
