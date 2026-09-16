"""Creation boundary for tradeable legendary players.

Legends are normal ``ingestion_players``.  Keeping their provenance in the
provider key (rather than a parallel asset table) deliberately lets discovery,
share ownership, and transfer-market services use their existing joins.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.ingestion.share_market_issuance import issue_markets_for_ingested_players
from app.models.player_token_market import PlayerShareMarket
from app.models.user import User

LEGENDARY_PLAYER_SOURCE = "legendary_player_foundation"


class LegendaryPlayerFoundationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class LegendaryPlayerSeed:
    key: str
    full_name: str
    nationality_name: str
    nationality_code: str
    position: str
    market_value_eur: float
    date_of_birth: date | None = None
    current_club_profile_id: str | None = None
    current_club_id: str | None = None
    current_competition_id: str | None = None


@dataclass(slots=True)
class LegendaryPlayerFoundationService:
    session: Session

    def seed(self, *, seed: LegendaryPlayerSeed, actor: User) -> Player:
        """Create or reconcile a legend and materialize its normal share market.

        The caller owns the surrounding transaction.  Issuance uses the same
        admin-attributed helper used by real-player ingestion, and failure is
        surfaced so a newly seeded legend cannot silently launch unbuyable.
        """
        key = self._required(seed.key, "key")
        full_name = self._required(seed.full_name, "full_name")
        nationality_name = self._required(seed.nationality_name, "nationality_name")
        nationality_code = self._required(seed.nationality_code, "nationality_code").upper()
        position = self._required(seed.position, "position")
        if float(seed.market_value_eur) <= 0:
            raise LegendaryPlayerFoundationError("market_value_eur must be greater than zero.")

        country = self._resolve_country(name=nationality_name, code=nationality_code)
        player = self.session.scalar(
            select(Player).where(
                Player.source_provider == LEGENDARY_PLAYER_SOURCE,
                Player.provider_external_id == key,
            )
        )
        if player is None:
            player = Player(
                source_provider=LEGENDARY_PLAYER_SOURCE,
                provider_external_id=key,
            )
            self.session.add(player)

        first_name, last_name = self._split_name(full_name)
        player.full_name = full_name
        player.canonical_display_name = full_name
        player.first_name = first_name
        player.last_name = last_name
        player.short_name = full_name
        player.country_id = country.id
        player.position = position
        player.normalized_position = position
        player.date_of_birth = seed.date_of_birth
        player.market_value_eur = float(seed.market_value_eur)
        player.current_market_reference_value = float(seed.market_value_eur)
        player.market_reference_currency = "EUR"
        player.current_club_profile_id = seed.current_club_profile_id
        player.current_club_id = seed.current_club_id
        player.current_competition_id = seed.current_competition_id
        player.is_tradable = True
        player.is_real_player = False
        player.dna_profile = {
            **(player.dna_profile or {}),
            "player_origin": "legendary",
            "legendary_player_key": key,
        }
        self.session.flush()

        issuance = issue_markets_for_ingested_players(
            self.session,
            player_ids=[player.id],
            actor_user_id=actor.id,
        )
        market = self.session.scalar(select(PlayerShareMarket.id).where(PlayerShareMarket.player_id == player.id))
        if market is None:
            raise LegendaryPlayerFoundationError(
                "Legendary player market issuance failed "
                f"(issued={issuance['issued']}, failed={issuance['failed']})."
            )
        return player

    def _resolve_country(self, *, name: str, code: str) -> Country:
        normalized_name = name.casefold()
        normalized_code = code.casefold()
        country = self.session.scalar(
            select(Country).where(
                or_(
                    func.lower(Country.alpha2_code) == normalized_code,
                    func.lower(Country.alpha3_code) == normalized_code,
                    func.lower(Country.fifa_code) == normalized_code,
                    func.lower(Country.name) == normalized_name,
                )
            )
        )
        if country is not None:
            return country
        country = Country(
            source_provider=LEGENDARY_PLAYER_SOURCE,
            provider_external_id=f"country:{code}",
            name=name,
            alpha2_code=code,
            fifa_code=code,
        )
        self.session.add(country)
        self.session.flush()
        return country

    @staticmethod
    def _required(value: str, field: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise LegendaryPlayerFoundationError(f"{field} is required.")
        return normalized

    @staticmethod
    def _split_name(full_name: str) -> tuple[str | None, str | None]:
        parts = full_name.split(maxsplit=1)
        return (parts[0], parts[1] if len(parts) > 1 else None)


__all__ = [
    "LEGENDARY_PLAYER_SOURCE",
    "LegendaryPlayerFoundationError",
    "LegendaryPlayerFoundationService",
    "LegendaryPlayerSeed",
]
