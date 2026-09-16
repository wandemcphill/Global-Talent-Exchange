from __future__ import annotations

from datetime import UTC, date, datetime
import random
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.legend_layer.schemas import LegendaryPlayerRegistryRecord
from app.models.player_token_market import PlayerShareMarket
from app.models.real_player_profile import RealPlayerProfile
from app.models.real_player_source_link import RealPlayerSourceLink


class LegendaryPlayerAdapter:
    SOURCE_PROVIDER = "legendary_registry"

    def __init__(self, session: Session) -> None:
        self.session = session

    def convert_record(self, record: LegendaryPlayerRegistryRecord) -> Player:
        existing_player = self.session.scalar(
            select(Player).where(
                Player.source_provider == self.SOURCE_PROVIDER,
                Player.provider_external_id == record.registry_id,
            )
        )
        if existing_player is not None:
            self._ensure_downstream_records(existing_player, record)
            return existing_player

        country = self._resolve_country(record.nationality, record.nationality_code)

        height_delta = random.choice([-1, 0, 1])
        generated_height = record.historical_height_cm + height_delta

        first_name = record.first_name
        last_name = record.last_name
        if not first_name or not last_name:
            parts = record.full_name.strip().split(" ", 1)
            first_name = first_name or parts[0]
            last_name = last_name or (parts[1] if len(parts) > 1 else "")

        short_name = (
            record.short_name or f"{first_name[0]}. {last_name}".strip()
            if first_name and last_name
            else record.full_name
        )

        dna_profile: dict[str, Any] = {
            "is_legendary_registry": True,
            "registry_id": record.registry_id,
            "overall_rating": record.overall_rating,
            "potential": record.potential,
            "signature_traits": record.signature_traits,
            "base_attributes": record.base_attributes,
            "historical_identity": {
                "historical_height_cm": record.historical_height_cm,
                "historical_weight_kg": record.historical_weight_kg,
                "historical_club_name": record.historical_club_name,
                "historical_league_name": record.historical_league_name,
            },
        }

        dob: date | None = None
        if isinstance(record.date_of_birth, date):
            dob = record.date_of_birth
        elif isinstance(record.date_of_birth, str) and record.date_of_birth:
            try:
                dob = date.fromisoformat(record.date_of_birth)
            except ValueError:
                dob = None

        if dob is None and record.birth_year:
            dob = date(record.birth_year, 1, 1)

        player = Player(
            source_provider=self.SOURCE_PROVIDER,
            provider_external_id=record.registry_id,
            country_id=country.id if country is not None else None,
            full_name=record.full_name,
            first_name=first_name,
            last_name=last_name,
            short_name=short_name,
            position=record.primary_position,
            normalized_position=record.primary_position.upper(),
            secondary_positions_json=list(record.secondary_positions),
            date_of_birth=dob,
            height_cm=generated_height,
            weight_kg=record.historical_weight_kg,
            preferred_foot=record.preferred_foot,
            potential=record.potential,
            market_value_eur=record.market_reference_value,
            is_tradable=True,
            is_real_player=True,
            real_player_tier="legendary_registry",
            canonical_display_name=record.full_name,
            identity_confidence_score=1.0,
            real_world_club_name=record.historical_club_name or "Free Agent",
            real_world_league_name=record.historical_league_name or "Legendary Registry",
            current_market_reference_value=record.market_reference_value,
            market_reference_currency=record.market_reference_currency,
            dna_profile=dna_profile,
            last_synced_at=datetime.now(UTC),
        )
        self.session.add(player)
        self.session.flush()

        self._ensure_downstream_records(player, record)

        return player

    def _ensure_downstream_records(self, player: Player, record: LegendaryPlayerRegistryRecord) -> None:
        source_link = self.session.scalar(
            select(RealPlayerSourceLink).where(
                RealPlayerSourceLink.source_name == self.SOURCE_PROVIDER,
                RealPlayerSourceLink.source_player_key == record.registry_id,
            )
        )
        if source_link is None:
            source_link = RealPlayerSourceLink(
                gtex_player_id=player.id,
                source_name=self.SOURCE_PROVIDER,
                source_player_key=record.registry_id,
                canonical_name=record.full_name,
                nationality=record.nationality,
                primary_position=record.primary_position,
                secondary_positions_json=list(record.secondary_positions),
                current_real_world_club=record.historical_club_name or "Free Agent",
                identity_confidence_score=1.0,
                is_verified_real_player=True,
                verification_state="verified",
            )
            self.session.add(source_link)
            self.session.flush()

        profile = self.session.scalar(
            select(RealPlayerProfile).where(
                RealPlayerProfile.gtex_player_id == player.id,
            )
        )
        if profile is None:
            dob: date | None = None
            if isinstance(record.date_of_birth, date):
                dob = record.date_of_birth
            elif isinstance(record.date_of_birth, str) and record.date_of_birth:
                try:
                    dob = date.fromisoformat(record.date_of_birth)
                except ValueError:
                    dob = None
            if dob is None and record.birth_year:
                dob = date(record.birth_year, 1, 1)

            profile = RealPlayerProfile(
                gtex_player_id=player.id,
                source_link_id=source_link.id,
                source_name=self.SOURCE_PROVIDER,
                source_player_key=record.registry_id,
                canonical_name=record.full_name,
                known_aliases_json=[],
                nationality=record.nationality,
                birth_year=record.birth_year or (dob.year if dob else None),
                date_of_birth=dob,
                dominant_foot=record.preferred_foot,
                primary_position=record.primary_position,
                secondary_positions_json=list(record.secondary_positions),
                height_cm=player.height_cm,
                weight_kg=record.historical_weight_kg,
                current_club_name=record.historical_club_name or "Free Agent",
                current_league_name=record.historical_league_name or "Legendary Registry",
                competition_level="legendary",
                current_market_reference_value=record.market_reference_value,
                market_reference_currency=record.market_reference_currency,
                source_last_refreshed_at=datetime.now(UTC),
                metadata_json={
                    "signature_traits": record.signature_traits,
                    "base_attributes": record.base_attributes,
                    "registry_metadata": record.metadata_json,
                },
            )
            self.session.add(profile)
            self.session.flush()

        share_market = self.session.scalar(
            select(PlayerShareMarket).where(
                PlayerShareMarket.player_id == player.id,
            )
        )
        if share_market is None:
            base_coin_price = max(1.0, round(record.market_reference_value / 100000.0, 2))
            from decimal import Decimal

            share_market = PlayerShareMarket(
                player_id=player.id,
                total_shares=1000,
                circulating_shares=1000,
                share_price_coin=Decimal(str(base_coin_price)),
                status="active",
                metadata_json={
                    "source": "legendary_registry",
                    "registry_id": record.registry_id,
                },
            )
            self.session.add(share_market)
            self.session.flush()

    def _resolve_country(self, nationality: str, nationality_code: str | None) -> Country | None:
        if nationality_code:
            country = self.session.scalar(
                select(Country).where(
                    (Country.alpha3_code == nationality_code.upper()) | (Country.fifa_code == nationality_code.upper())
                )
            )
            if country is not None:
                return country

        country = self.session.scalar(select(Country).where(Country.name.ilike(nationality)))
        if country is not None:
            return country

        code = nationality_code.upper() if nationality_code else nationality[:3].upper()
        country = Country(
            source_provider=self.SOURCE_PROVIDER,
            provider_external_id=f"country-{code.lower()}",
            name=nationality,
            alpha2_code=code[:2],
            alpha3_code=code,
            fifa_code=code,
            market_region="Global",
        )
        self.session.add(country)
        self.session.flush()
        return country
