from __future__ import annotations

from random import Random
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.models.legendary_player import LegendaryPlayerProfile
from app.schemas.legendary_player import (
    LegendaryPlayerProfileCreate,
    LegendaryPlayerProfileView,
    LegendarySeedImportRequest,
    LegendarySeedImportResult,
)


class LegendaryPlayerRegistryService:
    """Service layer managing legendary player profiles and GTEX player instantiation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def _ensure_country(self, country_code: str) -> Country:
        clean_code = country_code.strip().upper()
        stmt = select(Country).where(
            (Country.alpha2_code == clean_code)
            | (Country.alpha3_code == clean_code)
            | (Country.fifa_code == clean_code)
        )
        country = self.session.scalars(stmt).first()
        if not country:
            country = Country(
                source_provider="gtex_legend",
                provider_external_id=f"legend_country_{clean_code.lower()}",
                name=clean_code,
                alpha2_code=clean_code if len(clean_code) == 2 else None,
                alpha3_code=clean_code if len(clean_code) == 3 else None,
                fifa_code=clean_code if len(clean_code) == 3 else None,
            )
            self.session.add(country)
            self.session.flush()
        return country

    @staticmethod
    def calculate_gtex_height(slug: str, historical_height_cm: int) -> int:
        """Deterministically calculate GTEX height using -1, 0, or +1 cm from historical height based on slug."""
        rng = Random(f"gtex-legend-height:{slug}")
        offset = rng.choice([-1, 0, 1])
        return historical_height_cm + offset

    @staticmethod
    def generate_fictional_portrait_metadata(slug: str, country_code: str) -> dict[str, object]:
        """Generate non-replicative fictional avatar configuration metadata."""
        rng = Random(f"gtex-legend-portrait:{slug}")
        return {
            "avatar_system": "gtex_fictional_avatar_v1",
            "seed_token": f"legend-{slug}",
            "dna_seed": rng.randint(10000, 99999),
            "skin_tone": rng.randint(0, 5),
            "hair_style": rng.randint(0, 8),
            "hair_color": rng.randint(0, 5),
            "face_shape": rng.randint(0, 4),
            "eyebrow_style": rng.randint(0, 3),
            "eye_type": rng.randint(0, 3),
            "nose_type": rng.randint(0, 3),
            "mouth_type": rng.randint(0, 3),
            "beard_style": rng.randint(0, 5),
            "has_accessory": rng.random() > 0.8,
            "accessory_type": rng.randint(0, 3),
            "jersey_style": rng.randint(0, 3),
            "accent_tone": rng.randint(0, 5),
            "is_fictional_non_replicative": True,
            "configured_nationality": country_code,
        }

    def upsert_legendary_profile(self, data: LegendaryPlayerProfileCreate) -> tuple[LegendaryPlayerProfile, bool]:
        """Idempotently create or update a LegendaryPlayerProfile by slug."""
        slug = data.slug.strip().lower()
        stmt = select(LegendaryPlayerProfile).where(LegendaryPlayerProfile.slug == slug)
        existing = self.session.scalars(stmt).first()

        gtex_height = data.gtex_height_cm
        if gtex_height is None:
            if existing is not None and abs(existing.gtex_height_cm - data.historical_height_cm) <= 1:
                gtex_height = existing.gtex_height_cm
            else:
                gtex_height = self.calculate_gtex_height(slug, data.historical_height_cm)

        portrait_meta = dict(data.portrait_metadata or {})
        if not portrait_meta:
            if existing is not None and existing.portrait_metadata_json:
                portrait_meta = dict(existing.portrait_metadata_json)
            else:
                portrait_meta = self.generate_fictional_portrait_metadata(slug, data.country_code)

        created = False
        if existing is None:
            profile = LegendaryPlayerProfile(
                slug=slug,
                full_name=data.full_name,
                country_code=data.country_code,
                primary_position=data.primary_position,
                secondary_positions_json=list(data.secondary_positions),
                preferred_foot=data.preferred_foot,
                historical_height_cm=data.historical_height_cm,
                gtex_height_cm=gtex_height,
                signature_traits_json=list(data.signature_traits),
                signature_role=data.signature_role,
                technical_profile_json=dict(data.technical_profile),
                physical_profile_json=dict(data.physical_profile),
                mental_profile_json=dict(data.mental_profile),
                era=data.era,
                legendary_classification=data.legendary_classification,
                is_active=data.is_active,
                is_searchable=data.is_searchable,
                is_tradable=data.is_tradable,
                is_rentable=data.is_rentable,
                is_national_team_eligible=data.is_national_team_eligible,
                portrait_metadata_json=portrait_meta,
                source_notes=data.source_notes,
                metadata_json=dict(data.metadata),
            )
            self.session.add(profile)
            created = True
        else:
            profile = existing
            profile.full_name = data.full_name
            profile.country_code = data.country_code
            profile.primary_position = data.primary_position
            profile.secondary_positions_json = list(data.secondary_positions)
            profile.preferred_foot = data.preferred_foot
            profile.historical_height_cm = data.historical_height_cm
            profile.gtex_height_cm = gtex_height
            profile.signature_traits_json = list(data.signature_traits)
            profile.signature_role = data.signature_role
            profile.technical_profile_json = dict(data.technical_profile)
            profile.physical_profile_json = dict(data.physical_profile)
            profile.mental_profile_json = dict(data.mental_profile)
            profile.era = data.era
            profile.legendary_classification = data.legendary_classification
            profile.is_active = data.is_active
            profile.is_searchable = data.is_searchable
            profile.is_tradable = data.is_tradable
            profile.is_rentable = data.is_rentable
            profile.is_national_team_eligible = data.is_national_team_eligible
            profile.portrait_metadata_json = portrait_meta
            profile.source_notes = data.source_notes
            profile.metadata_json = dict(data.metadata)

        self.session.flush()
        return profile, created

    def instantiate_gtex_player(self, profile: LegendaryPlayerProfile) -> Player:
        """Idempotently convert/instantiate a LegendaryPlayerProfile into an ordinary GTEX Player row."""
        provider_external_id = f"legend:{profile.slug}"
        stmt = select(Player).where(
            (Player.legendary_profile_id == profile.id)
            | ((Player.source_provider == "gtex_legend") & (Player.provider_external_id == provider_external_id))
        )
        existing_player = self.session.scalars(stmt).first()

        country = self._ensure_country(profile.country_code)

        names = profile.full_name.strip().split(" ", 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else None

        if existing_player is None:
            player = Player(
                legendary_profile_id=profile.id,
                source_provider="gtex_legend",
                provider_external_id=provider_external_id,
                country_id=country.id,
                full_name=profile.full_name,
                first_name=first_name,
                last_name=last_name,
                short_name=profile.full_name,
                position=profile.primary_position,
                normalized_position=profile.primary_position,
                secondary_positions_json=list(profile.secondary_positions_json or []),
                height_cm=profile.gtex_height_cm,
                preferred_foot=profile.preferred_foot,
                is_tradable=profile.is_tradable,
                is_real_player=True,
                real_player_tier=profile.legendary_classification,
                canonical_display_name=profile.full_name,
                dna_profile={
                    "era": profile.era,
                    "legendary_classification": profile.legendary_classification,
                    "signature_traits": list(profile.signature_traits_json or []),
                    "signature_role": profile.signature_role,
                    "technical_profile": dict(profile.technical_profile_json or {}),
                    "physical_profile": dict(profile.physical_profile_json or {}),
                    "mental_profile": dict(profile.mental_profile_json or {}),
                    "is_national_team_eligible": profile.is_national_team_eligible,
                    "is_rentable": profile.is_rentable,
                    "portrait_metadata": dict(profile.portrait_metadata_json or {}),
                },
            )
            self.session.add(player)
        else:
            player = existing_player
            player.legendary_profile_id = profile.id
            player.country_id = country.id
            player.full_name = profile.full_name
            player.first_name = first_name
            player.last_name = last_name
            player.short_name = profile.full_name
            player.position = profile.primary_position
            player.normalized_position = profile.primary_position
            player.secondary_positions_json = list(profile.secondary_positions_json or [])
            player.height_cm = profile.gtex_height_cm
            player.preferred_foot = profile.preferred_foot
            player.is_tradable = profile.is_tradable
            player.is_real_player = True
            player.real_player_tier = profile.legendary_classification
            player.canonical_display_name = profile.full_name

            dna = dict(player.dna_profile or {})
            dna.update(
                {
                    "era": profile.era,
                    "legendary_classification": profile.legendary_classification,
                    "signature_traits": list(profile.signature_traits_json or []),
                    "signature_role": profile.signature_role,
                    "technical_profile": dict(profile.technical_profile_json or {}),
                    "physical_profile": dict(profile.physical_profile_json or {}),
                    "mental_profile": dict(profile.mental_profile_json or {}),
                    "is_national_team_eligible": profile.is_national_team_eligible,
                    "is_rentable": profile.is_rentable,
                    "portrait_metadata": dict(profile.portrait_metadata_json or {}),
                }
            )
            player.dna_profile = dna

        self.session.flush()
        return player

    def bulk_import(self, request: LegendarySeedImportRequest) -> LegendarySeedImportResult:
        """Idempotent seed/import contract for bulk legendary profiles."""
        created_count = 0
        updated_count = 0
        instantiated_count = 0
        profile_ids: list[str] = []

        for item in request.profiles:
            profile, created = self.upsert_legendary_profile(item)
            if created:
                created_count += 1
            else:
                updated_count += 1

            if request.instantiate_all or item.instantiate_gtex_player:
                self.instantiate_gtex_player(profile)
                instantiated_count += 1

            profile_ids.append(profile.id)

        self.session.flush()
        return LegendarySeedImportResult(
            processed_count=len(request.profiles),
            created_count=created_count,
            updated_count=updated_count,
            instantiated_player_count=instantiated_count,
            profile_ids=profile_ids,
        )

    def get_by_slug(self, slug: str) -> LegendaryPlayerProfile | None:
        stmt = select(LegendaryPlayerProfile).where(LegendaryPlayerProfile.slug == slug.strip().lower())
        return self.session.scalars(stmt).first()

    def get_by_id(self, profile_id: str) -> LegendaryPlayerProfile | None:
        stmt = select(LegendaryPlayerProfile).where(LegendaryPlayerProfile.id == profile_id)
        return self.session.scalars(stmt).first()

    def search_profiles(
        self,
        *,
        country_code: str | None = None,
        position: str | None = None,
        era: str | None = None,
        classification: str | None = None,
        active_only: bool = True,
        searchable_only: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[LegendaryPlayerProfile]:
        stmt = select(LegendaryPlayerProfile)
        if active_only:
            stmt = stmt.where(LegendaryPlayerProfile.is_active == True)
        if searchable_only:
            stmt = stmt.where(LegendaryPlayerProfile.is_searchable == True)
        if country_code:
            stmt = stmt.where(LegendaryPlayerProfile.country_code == country_code.strip().upper())
        if position:
            stmt = stmt.where(LegendaryPlayerProfile.primary_position == position.strip().upper())
        if era:
            stmt = stmt.where(LegendaryPlayerProfile.era == era.strip())
        if classification:
            stmt = stmt.where(LegendaryPlayerProfile.legendary_classification == classification.strip().lower())

        stmt = stmt.order_by(LegendaryPlayerProfile.full_name.asc()).limit(limit).offset(offset)
        return self.session.scalars(stmt).all()

    @staticmethod
    def to_view(profile: LegendaryPlayerProfile) -> LegendaryPlayerProfileView:
        offset = profile.gtex_height_cm - profile.historical_height_cm
        return LegendaryPlayerProfileView(
            id=profile.id,
            slug=profile.slug,
            full_name=profile.full_name,
            country_code=profile.country_code,
            primary_position=profile.primary_position,
            secondary_positions=list(profile.secondary_positions_json or []),
            preferred_foot=profile.preferred_foot,  # type: ignore[arg-type]
            historical_height_cm=profile.historical_height_cm,
            gtex_height_cm=profile.gtex_height_cm,
            signature_traits=list(profile.signature_traits_json or []),
            signature_role=profile.signature_role,
            technical_profile=dict(profile.technical_profile_json or {}),
            physical_profile=dict(profile.physical_profile_json or {}),
            mental_profile=dict(profile.mental_profile_json or {}),
            era=profile.era,
            legendary_classification=profile.legendary_classification,
            is_active=profile.is_active,
            is_searchable=profile.is_searchable,
            is_tradable=profile.is_tradable,
            is_rentable=profile.is_rentable,
            is_national_team_eligible=profile.is_national_team_eligible,
            portrait_metadata=dict(profile.portrait_metadata_json or {}),
            source_notes=profile.source_notes,
            metadata=dict(profile.metadata_json or {}),
            created_at=profile.created_at,
            updated_at=profile.updated_at,
            height_offset_cm=offset,
        )
