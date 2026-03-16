from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.app.club_identity.models.reputation import ClubReputationProfile
from backend.app.core.config import Settings, get_settings
from backend.app.ingestion.models import Country, Player, PlayerVerification
from backend.app.models.club_infra import ClubFacility
from backend.app.models.club_profile import ClubProfile
from backend.app.models.player_cards import (
    PlayerCard,
    PlayerCardHolding,
    PlayerCardHistory,
    PlayerCardOwnerHistory,
    PlayerCardTier,
)
from backend.app.models.player_career_entry import PlayerCareerEntry
from backend.app.models.player_contract import PlayerContract
from backend.app.models.player_lifecycle_event import PlayerLifecycleEvent
from backend.app.models.regen import (
    RegenGenerationEvent,
    RegenLineageProfile,
    RegenOnboardingFlag,
    RegenOriginMetadata,
    RegenPersonalityProfile,
    RegenProfile,
    RegenRelationshipTag,
    RegenTwinsGroup,
    RegenVisualProfile,
)
from backend.app.services.regen_service import RegenClubContext, RegenGenerationEngine

_COUNTRY_NAMES = {
    "NG": "Nigeria",
    "GH": "Ghana",
    "MA": "Morocco",
    "BR": "Brazil",
    "ES": "Spain",
    "JP": "Japan",
}


def _normalized_position(position: str) -> str:
    if position == "GK":
        return "goalkeeper"
    if position in {"CB", "RB", "LB"}:
        return "defender"
    if position in {"DM", "CM", "AM"}:
        return "midfielder"
    return "forward"


@dataclass(slots=True)
class RegenBootstrapService:
    session: Session
    settings: Settings | None = None
    engine: RegenGenerationEngine | None = None

    def __post_init__(self) -> None:
        resolved_settings = self.settings or get_settings()
        self.settings = resolved_settings
        self.engine = self.engine or RegenGenerationEngine(resolved_settings)

    def bootstrap_for_new_club(self, club: ClubProfile) -> tuple[RegenProfile, ...]:
        existing = self.session.scalars(
            select(RegenProfile).where(
                RegenProfile.generated_for_club_id == club.id,
                RegenProfile.generation_source == "new_club",
            )
        ).all()
        if existing:
            return tuple(existing)

        bundle = self.engine.generate_starter_regens(
            club_id=club.id,
            season_label=self._season_label(),
            club_context=self._club_context(club),
        )
        card_tier = self._ensure_regen_card_tier()
        persisted: list[RegenProfile] = []
        for slot_index, generated in enumerate(bundle.regens, start=1):
            country = self._ensure_country(generated.birth_country_code)
            player = Player(
                source_provider="gtex_regen",
                provider_external_id=f"regen:{generated.regen_id}",
                country_id=country.id,
                current_club_profile_id=club.id,
                full_name=generated.display_name,
                first_name=generated.display_name.split(" ", 1)[0],
                last_name=generated.display_name.split(" ", 1)[1] if " " in generated.display_name else None,
                short_name=generated.display_name,
                position=generated.primary_position,
                normalized_position=_normalized_position(generated.primary_position),
                date_of_birth=date.today() - timedelta(days=generated.age * 365),
                preferred_foot="right",
                shirt_number=None,
                market_value_eur=float(generated.current_gsi) * 12_500.0,
                profile_completeness_score=0.98,
                is_tradable=True,
            )
            self.session.add(player)
            self.session.flush()

            self.session.add(
                PlayerVerification(
                    player_id=player.id,
                    status="verified",
                    verification_source="gtex_regen_generator",
                    confidence_score=1.0,
                    rights_confirmed=True,
                    reviewer_notes="GTEX synthetic regen bootstrap.",
                )
            )

            card = PlayerCard(
                player_id=player.id,
                tier_id=card_tier.id,
                edition_code="regen_unique",
                display_name=generated.display_name,
                season_label=bundle.season_label,
                card_variant="regen_unique",
                supply_total=1,
                supply_available=1,
                metadata_json={
                    "origin_type": "regen",
                    "regen_id": generated.regen_id,
                    "visual_profile": generated.metadata.get("visual_profile", {}),
                },
            )
            self.session.add(card)
            self.session.flush()

            self.session.add(
                PlayerCardHistory(
                    player_card_id=card.id,
                    event_type="starter_bootstrap",
                    description="Starter regen unique card created for a newly founded club.",
                    delta_supply=1,
                    delta_available=1,
                    actor_user_id=club.owner_user_id,
                    metadata_json={"regen_id": generated.regen_id},
                )
            )
            self.session.add(
                PlayerCardHolding(
                    player_card_id=card.id,
                    owner_user_id=club.owner_user_id,
                    quantity_total=1,
                    quantity_reserved=0,
                    metadata_json={"origin": "starter_regen"},
                )
            )
            self.session.add(
                PlayerCardOwnerHistory(
                    player_card_id=card.id,
                    from_user_id=None,
                    to_user_id=club.owner_user_id,
                    quantity=1,
                    event_type="starter_bootstrap",
                    reference_id=generated.regen_id,
                    metadata_json={"club_id": club.id},
                )
            )
            self.session.add(
                PlayerContract(
                    player_id=player.id,
                    club_id=club.id,
                    status="active",
                    wage_amount=Decimal("0.00"),
                    release_clause_amount=None,
                    signed_on=date.today(),
                    starts_on=date.today(),
                    ends_on=date.today() + timedelta(days=730),
                )
            )
            self.session.add(
                PlayerCareerEntry(
                    player_id=player.id,
                    club_id=club.id,
                    club_name=club.club_name,
                    season_label=bundle.season_label,
                    squad_role="starter_regen",
                    appearances=0,
                    goals=0,
                    assists=0,
                    honours_json=[],
                    notes="GTEX starter regen created during club foundation.",
                    start_on=date.today(),
                    end_on=None,
                )
            )
            self.session.add(
                PlayerLifecycleEvent(
                    player_id=player.id,
                    club_id=club.id,
                    event_type="starter_bootstrap",
                    event_status="recorded",
                    occurred_on=date.today(),
                    effective_from=date.today(),
                    summary="Starter regen assigned to newly created club.",
                    details_json={"regen_id": generated.regen_id, "card_id": card.id},
                )
            )

            regen = RegenProfile(
                regen_id=generated.regen_id,
                player_id=player.id,
                linked_unique_card_id=card.id,
                generated_for_club_id=club.id,
                birth_country_code=generated.birth_country_code,
                birth_region=generated.birth_region,
                birth_city=generated.birth_city,
                primary_position=generated.primary_position,
                secondary_positions_json=list(generated.secondary_positions),
                generated_at=generated.generated_at,
                current_gsi=generated.current_gsi,
                current_ability_range_json={
                    "minimum": generated.current_ability_range.minimum,
                    "maximum": generated.current_ability_range.maximum,
                },
                potential_range_json={
                    "minimum": generated.potential_range.minimum,
                    "maximum": generated.potential_range.maximum,
                },
                scout_confidence=generated.scout_confidence,
                generation_source=generated.generation_source,
                is_special_lineage=generated.is_special_lineage,
                status=generated.status,
                club_quality_score=generated.club_quality_score,
                metadata_json=generated.metadata,
            )
            self.session.add(regen)
            self.session.flush()

            self.session.add(
                RegenPersonalityProfile(
                    regen_profile_id=regen.id,
                    temperament=generated.personality.temperament,
                    leadership=generated.personality.leadership,
                    ambition=generated.personality.ambition,
                    loyalty=generated.personality.loyalty,
                    work_rate=generated.personality.work_rate,
                    flair=generated.personality.flair,
                    resilience=generated.personality.resilience,
                    personality_tags_json=list(generated.personality.personality_tags),
                )
            )
            self.session.add(
                RegenOriginMetadata(
                    regen_profile_id=regen.id,
                    country_code=generated.origin.country_code,
                    region_name=generated.origin.region_name,
                    city_name=generated.origin.city_name,
                    hometown_club_affinity=club.club_name,
                    ethnolinguistic_profile=generated.origin.ethnolinguistic_profile,
                    religion_naming_pattern=generated.origin.religion_naming_pattern,
                    urbanicity=generated.origin.urbanicity,
                    metadata_json={},
                )
            )
            visual_profile = generated.metadata.get("visual_profile", {})
            self.session.add(
                RegenVisualProfile(
                    regen_profile_id=regen.id,
                    portrait_seed=str(visual_profile.get("portrait_seed", generated.regen_id)),
                    skin_tone=str(visual_profile.get("skin_tone") or ""),
                    hair_profile=str(visual_profile.get("hair_profile") or ""),
                    accessory_profile_json={},
                    kit_style=str(visual_profile.get("kit_style") or ""),
                    metadata_json={},
                )
            )
            lineage_payload = generated.metadata.get("lineage") if isinstance(generated.metadata, dict) else None
            if lineage_payload:
                self.session.add(
                    RegenLineageProfile(
                        regen_id=regen.id,
                        relationship_type=str(lineage_payload.get("relationship_type", "lineage")),
                        related_legend_type=str(lineage_payload.get("related_legend_type", "unknown")),
                        related_legend_ref_id=str(lineage_payload.get("related_legend_ref_id", regen.regen_id)),
                        lineage_country_code=str(lineage_payload.get("lineage_country_code", regen.birth_country_code)),
                        lineage_hometown_code=lineage_payload.get("lineage_hometown_code"),
                        is_owner_son=bool(lineage_payload.get("is_owner_son", False)),
                        is_retired_regen_lineage=bool(lineage_payload.get("is_retired_regen_lineage", False)),
                        is_real_legend_lineage=bool(lineage_payload.get("is_real_legend_lineage", False)),
                        is_celebrity_lineage=bool(lineage_payload.get("is_celebrity_lineage", False)),
                        is_celebrity_licensed=bool(lineage_payload.get("is_celebrity_licensed", False)),
                        lineage_tier=str(lineage_payload.get("lineage_tier", "rare")),
                        narrative_text=lineage_payload.get("narrative_text"),
                        metadata_json=dict(lineage_payload),
                    )
                )
                tags = generated.metadata.get("relationship_tags") or []
                for tag in tags:
                    self.session.add(
                        RegenRelationshipTag(
                            regen_id=regen.id,
                            tag=str(tag),
                            relationship_type=str(lineage_payload.get("relationship_type", "lineage")),
                            related_entity_type=str(lineage_payload.get("related_legend_type", "unknown")),
                            related_entity_id=str(lineage_payload.get("related_legend_ref_id", regen.regen_id)),
                            display_text=str(lineage_payload.get("narrative_text") or ""),
                            metadata_json={"source": "bootstrap"},
                        )
                    )
            twins_group_key = generated.metadata.get("twins_group_key") if isinstance(generated.metadata, dict) else None
            if twins_group_key:
                self.session.add(
                    RegenTwinsGroup(
                        twins_group_key=str(twins_group_key),
                        regen_id=regen.id,
                        club_id=club.id,
                        season_label=bundle.season_label,
                        visual_seed=str(visual_profile.get("portrait_seed", generated.regen_id)),
                        similarity_score=float(generated.metadata.get("twin_similarity_score", 0.85)),
                        metadata_json={"twin_variant": generated.metadata.get("twin_variant")},
                    )
                )
            self.session.add(
                RegenGenerationEvent(
                    regen_profile_id=regen.id,
                    club_id=club.id,
                    generation_source="new_club",
                    season_label=bundle.season_label,
                    event_status="generated",
                    probability_score=round(generated.potential_range.maximum / 100.0, 4),
                    quality_roll=round(generated.club_quality_score / 100.0, 4),
                    metadata_json={"starter_bundle": True},
                )
            )
            self.session.add(
                RegenOnboardingFlag(
                    regen_id=regen.id,
                    club_id=club.id,
                    onboarding_type="starter_bundle",
                    squad_bucket="first_team",
                    squad_slot=slot_index,
                    is_non_tradable=True,
                    replacement_only=True,
                    metadata_json={
                        "starter_first_team_target": 18,
                        "starter_academy_target": 18,
                        "replacement_path": "real_player_market_plus_regen_development",
                        "starter_gsi_band": generated.current_gsi,
                    },
                )
            )
            persisted.append(regen)

        return tuple(persisted)

    def _club_context(self, club: ClubProfile) -> RegenClubContext:
        facility = self.session.scalar(select(ClubFacility).where(ClubFacility.club_id == club.id))
        reputation = self.session.scalar(select(ClubReputationProfile).where(ClubReputationProfile.club_id == club.id))
        return RegenClubContext(
            country_code=club.country_code or self.settings.regen_generation.default_country_code,
            region_name=club.region_name,
            city_name=club.city_name,
            youth_coaching=float((facility.academy_level if facility is not None else 1) * 20),
            training_level=float((facility.training_level if facility is not None else 1) * 20),
            academy_level=float((facility.academy_level if facility is not None else 1) * 20),
            academy_investment=float((facility.academy_level if facility is not None else 1) * 18),
            first_team_gsi=56.0,
            club_reputation=float(reputation.current_score if reputation is not None else 10),
            competition_quality=45.0,
            manager_youth_development=50.0,
            urbanicity="urban" if club.city_name else None,
        )

    def _ensure_country(self, country_code: str) -> Country:
        resolved = country_code.upper()
        country = self.session.scalar(
            select(Country).where(
                or_(
                    Country.alpha2_code == resolved,
                    Country.alpha3_code == resolved,
                    Country.fifa_code == resolved,
                )
            )
        )
        if country is not None:
            return country
        country = Country(
            source_provider="gtex_regen",
            provider_external_id=f"country:{resolved}",
            name=_COUNTRY_NAMES.get(resolved, resolved),
            alpha2_code=resolved,
            alpha3_code=resolved,
            fifa_code=resolved,
            confederation_code=None,
            market_region="regen",
            is_enabled_for_universe=True,
        )
        self.session.add(country)
        self.session.flush()
        return country

    def _ensure_regen_card_tier(self) -> PlayerCardTier:
        tier = self.session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == "regen_unique"))
        if tier is not None:
            return tier
        tier = PlayerCardTier(
            code="regen_unique",
            name="Regen Unique",
            rarity_rank=99,
            max_supply=1,
            supply_multiplier=Decimal("1.0000"),
            base_mint_price_credits=Decimal("0.0000"),
            color_hex="#C88C2D",
            is_active=True,
            metadata_json={"origin_type": "regen"},
        )
        self.session.add(tier)
        self.session.flush()
        return tier

    def _season_label(self) -> str:
        today = date.today()
        start_year = today.year if today.month >= 7 else today.year - 1
        return f"{start_year}/{start_year + 1}"


__all__ = ["RegenBootstrapService"]
