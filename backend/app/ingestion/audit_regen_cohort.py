from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Sequence
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.models import Country, Player
from app.models.club_profile import ClubProfile
from app.models.player_cards import PlayerCard, PlayerCardTier, PlayerMarketValueSnapshot
from app.models.regen import RegenProfile
from app.models.user import User, UserRole
from app.players.read_models import PlayerSummaryReadModel
from app.value_engine.read_models import PlayerValueSnapshotRecord

AUDIT_REGEN_SOURCE_PROVIDER = "audit_regen_fixture"
AUDIT_REGEN_COHORT_KEY = "phase_a_representative_regens"
AUDIT_REGEN_TIER_CODE = "audit_regen_fixture"
AUDIT_REGEN_OWNER_EMAIL = "audit-regen-owner@gtex.local"
AUDIT_REGEN_OWNER_USERNAME = "audit_regen_owner"
AUDIT_REGEN_CLUB_SLUG = "audit-regen-athletic"
AUDIT_REGEN_AS_OF = datetime(2026, 3, 22, 15, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class AuditRegenSpec:
    key: str
    full_name: str
    country_code: str
    country_name: str
    position: str
    normalized_position: str
    date_of_birth: date
    current_value_credits: float
    global_scouting_index: float
    market_value_eur: float = 0.0
    birth_region: str | None = None
    birth_city: str | None = None


@dataclass(frozen=True, slots=True)
class AuditRegenCohortSeedResult:
    cohort_key: str
    requested_count: int
    created_player_count: int
    reused_player_count: int
    player_ids: tuple[str, ...]


DEFAULT_AUDIT_REGEN_COHORT: tuple[AuditRegenSpec, ...] = (
    AuditRegenSpec(
        key="keeper_anchor",
        full_name="Musa Danjuma",
        country_code="NG",
        country_name="Nigeria",
        position="GK",
        normalized_position="goalkeeper",
        date_of_birth=date(1999, 7, 19),
        current_value_credits=146.0,
        global_scouting_index=64.0,
        birth_region="Kano",
        birth_city="Kano",
    ),
    AuditRegenSpec(
        key="keeper_prospect",
        full_name="Rayan Bennani",
        country_code="MA",
        country_name="Morocco",
        position="GK",
        normalized_position="goalkeeper",
        date_of_birth=date(2003, 5, 11),
        current_value_credits=138.0,
        global_scouting_index=61.0,
        birth_region="Casablanca-Settat",
        birth_city="Casablanca",
    ),
    AuditRegenSpec(
        key="defender_core",
        full_name="Caio Oliveira",
        country_code="BR",
        country_name="Brazil",
        position="CB",
        normalized_position="defender",
        date_of_birth=date(2000, 2, 8),
        current_value_credits=232.0,
        global_scouting_index=69.0,
        birth_region="Sao Paulo",
        birth_city="Sao Paulo",
    ),
    AuditRegenSpec(
        key="fullback_riser",
        full_name="Kojo Mensah",
        country_code="GH",
        country_name="Ghana",
        position="RB",
        normalized_position="defender",
        date_of_birth=date(2004, 9, 2),
        current_value_credits=224.0,
        global_scouting_index=67.0,
        birth_region="Greater Accra",
        birth_city="Accra",
    ),
    AuditRegenSpec(
        key="midfield_anchor",
        full_name="Mateo Ruiz",
        country_code="ES",
        country_name="Spain",
        position="CM",
        normalized_position="midfielder",
        date_of_birth=date(1998, 11, 14),
        current_value_credits=332.0,
        global_scouting_index=75.0,
        birth_region="Madrid",
        birth_city="Madrid",
    ),
    AuditRegenSpec(
        key="midfield_box_to_box",
        full_name="Samuel Boateng",
        country_code="GH",
        country_name="Ghana",
        position="CM",
        normalized_position="midfielder",
        date_of_birth=date(2002, 4, 3),
        current_value_credits=308.0,
        global_scouting_index=72.0,
        birth_region="Ashanti",
        birth_city="Kumasi",
    ),
    AuditRegenSpec(
        key="attacking_mid_creator",
        full_name="Daniel Adebayo",
        country_code="NG",
        country_name="Nigeria",
        position="AM",
        normalized_position="midfielder",
        date_of_birth=date(2005, 1, 21),
        current_value_credits=286.0,
        global_scouting_index=70.0,
        birth_region="Lagos",
        birth_city="Lagos",
    ),
    AuditRegenSpec(
        key="winger_breakout",
        full_name="Haruto Sato",
        country_code="JP",
        country_name="Japan",
        position="RW",
        normalized_position="forward",
        date_of_birth=date(2004, 6, 17),
        current_value_credits=372.0,
        global_scouting_index=77.0,
        birth_region="Tokyo",
        birth_city="Tokyo",
    ),
    AuditRegenSpec(
        key="winger_flair",
        full_name="Adrian Garcia",
        country_code="ES",
        country_name="Spain",
        position="LW",
        normalized_position="forward",
        date_of_birth=date(2001, 3, 26),
        current_value_credits=348.0,
        global_scouting_index=74.0,
        birth_region="Madrid",
        birth_city="Madrid",
    ),
    AuditRegenSpec(
        key="striker_reference",
        full_name="Pedro Santos",
        country_code="BR",
        country_name="Brazil",
        position="ST",
        normalized_position="forward",
        date_of_birth=date(1999, 10, 5),
        current_value_credits=512.0,
        global_scouting_index=84.0,
        birth_region="Sao Paulo",
        birth_city="Sao Paulo",
    ),
    AuditRegenSpec(
        key="striker_breakout",
        full_name="Youssef El Idrissi",
        country_code="MA",
        country_name="Morocco",
        position="ST",
        normalized_position="forward",
        date_of_birth=date(2004, 12, 9),
        current_value_credits=428.0,
        global_scouting_index=79.0,
        birth_region="Rabat-Sale-Kenitra",
        birth_city="Rabat",
    ),
    AuditRegenSpec(
        key="striker_prospect",
        full_name="Kwame Ofori",
        country_code="GH",
        country_name="Ghana",
        position="ST",
        normalized_position="forward",
        date_of_birth=date(2006, 2, 12),
        current_value_credits=256.0,
        global_scouting_index=69.0,
        birth_region="Greater Accra",
        birth_city="Accra",
    ),
)


class AuditRegenCohortSeeder:
    def __init__(
        self,
        session: Session,
        *,
        cohort_key: str = AUDIT_REGEN_COHORT_KEY,
        as_of: datetime = AUDIT_REGEN_AS_OF,
    ) -> None:
        self.session = session
        self.cohort_key = cohort_key
        self.as_of = as_of

    def seed(self, specs: Sequence[AuditRegenSpec] = DEFAULT_AUDIT_REGEN_COHORT) -> AuditRegenCohortSeedResult:
        owner = self._ensure_owner()
        club = self._ensure_club(owner)
        tier = self._ensure_tier()
        created_player_count = 0
        reused_player_count = 0
        player_ids: list[str] = []

        for spec in specs:
            country = self._ensure_country(spec)
            player, created = self._ensure_player(spec, country=country, club=club)
            if created:
                created_player_count += 1
            else:
                reused_player_count += 1
            card = self._ensure_card(player, tier=tier)
            self._ensure_regen_profile(player, card=card, club=club, spec=spec)
            snapshot = self._ensure_snapshot(player, spec=spec)
            self._ensure_summary(player, snapshot=snapshot, spec=spec)
            self._ensure_market_snapshot(player, snapshot=snapshot, spec=spec)
            player_ids.append(player.id)

        self.session.flush()
        return AuditRegenCohortSeedResult(
            cohort_key=self.cohort_key,
            requested_count=len(specs),
            created_player_count=created_player_count,
            reused_player_count=reused_player_count,
            player_ids=tuple(player_ids),
        )

    def _ensure_owner(self) -> User:
        owner = self.session.scalar(select(User).where(User.email == AUDIT_REGEN_OWNER_EMAIL))
        if owner is not None:
            return owner
        owner = User(
            email=AUDIT_REGEN_OWNER_EMAIL,
            username=AUDIT_REGEN_OWNER_USERNAME,
            full_name="Audit Regen Owner",
            display_name="Audit Regen Owner",
            password_hash="audit-regen-fixture",
            role=UserRole.ADMIN,
        )
        self.session.add(owner)
        self.session.flush()
        return owner

    def _ensure_club(self, owner: User) -> ClubProfile:
        club = self.session.scalar(select(ClubProfile).where(ClubProfile.slug == AUDIT_REGEN_CLUB_SLUG))
        if club is not None:
            return club
        club = ClubProfile(
            owner_user_id=owner.id,
            club_name="Audit Regen Athletic",
            short_name="ARA",
            slug=AUDIT_REGEN_CLUB_SLUG,
            primary_color="#0F3B57",
            secondary_color="#F2C14E",
            accent_color="#F7F7F2",
            home_venue_name="Audit Regen Ground",
            country_code="NG",
            region_name="Lagos",
            city_name="Lagos",
            description="Controlled regen cohort for manual batch audit validation.",
        )
        self.session.add(club)
        self.session.flush()
        return club

    def _ensure_tier(self) -> PlayerCardTier:
        tier = self.session.scalar(select(PlayerCardTier).where(PlayerCardTier.code == AUDIT_REGEN_TIER_CODE))
        if tier is not None:
            return tier
        tier = PlayerCardTier(
            code=AUDIT_REGEN_TIER_CODE,
            name="Audit Regen Fixture",
            rarity_rank=901,
            base_mint_price_credits=Decimal("0"),
            color_hex="#0F3B57",
        )
        self.session.add(tier)
        self.session.flush()
        return tier

    def _ensure_country(self, spec: AuditRegenSpec) -> Country:
        country = self.session.scalar(select(Country).where(Country.alpha2_code == spec.country_code))
        if country is not None:
            return country
        country = Country(
            source_provider=AUDIT_REGEN_SOURCE_PROVIDER,
            provider_external_id=f"country:{spec.country_code}",
            name=spec.country_name,
            alpha2_code=spec.country_code,
            market_region="audit_fixture",
        )
        self.session.add(country)
        self.session.flush()
        return country

    def _ensure_player(
        self,
        spec: AuditRegenSpec,
        *,
        country: Country,
        club: ClubProfile,
    ) -> tuple[Player, bool]:
        player = self.session.scalar(
            select(Player).where(
                Player.source_provider == AUDIT_REGEN_SOURCE_PROVIDER,
                Player.provider_external_id == f"regen:{self.cohort_key}:{spec.key}",
            )
        )
        created = player is None
        if player is None:
            first_name, _, last_name = spec.full_name.partition(" ")
            player = Player(
                source_provider=AUDIT_REGEN_SOURCE_PROVIDER,
                provider_external_id=f"regen:{self.cohort_key}:{spec.key}",
                country_id=country.id,
                current_club_profile_id=club.id,
                full_name=spec.full_name,
                first_name=first_name,
                last_name=last_name or None,
                short_name=spec.full_name,
                position=spec.position,
                normalized_position=spec.normalized_position,
                date_of_birth=spec.date_of_birth,
                preferred_foot="right",
                market_value_eur=spec.market_value_eur,
                profile_completeness_score=1.0,
                is_tradable=True,
                is_real_player=False,
                canonical_display_name=spec.full_name,
            )
            self.session.add(player)
            self.session.flush()
        else:
            player.country_id = country.id
            player.current_club_profile_id = club.id
            player.full_name = spec.full_name
            player.position = spec.position
            player.normalized_position = spec.normalized_position
            player.date_of_birth = spec.date_of_birth
            player.market_value_eur = spec.market_value_eur
            player.is_tradable = True
            player.is_real_player = False
            player.canonical_display_name = spec.full_name
        return player, created

    def _ensure_card(self, player: Player, *, tier: PlayerCardTier) -> PlayerCard:
        edition_code = f"audit_regen:{self.cohort_key}"
        card = self.session.scalar(
            select(PlayerCard).where(
                PlayerCard.player_id == player.id,
                PlayerCard.tier_id == tier.id,
                PlayerCard.edition_code == edition_code,
            )
        )
        if card is not None:
            return card
        card = PlayerCard(
            player_id=player.id,
            tier_id=tier.id,
            edition_code=edition_code,
            display_name=player.full_name,
            season_label="2025/2026",
            card_variant="audit_regen",
            supply_total=1,
            supply_available=1,
            metadata_json={
                "cohort_key": self.cohort_key,
                "identity_rail": "regen_universe",
                "provenance": "audit_fixture",
            },
        )
        self.session.add(card)
        self.session.flush()
        return card

    def _ensure_regen_profile(
        self,
        player: Player,
        *,
        card: PlayerCard,
        club: ClubProfile,
        spec: AuditRegenSpec,
    ) -> RegenProfile:
        regen = self.session.scalar(select(RegenProfile).where(RegenProfile.player_id == player.id))
        if regen is None:
            regen = RegenProfile(
                regen_id=f"audit-regen-{self.cohort_key}-{spec.key}",
                player_id=player.id,
                linked_unique_card_id=card.id,
                generated_for_club_id=club.id,
                birth_country_code=spec.country_code,
                birth_region=spec.birth_region,
                birth_city=spec.birth_city,
                primary_position=spec.position,
                secondary_positions_json=[],
                generated_at=self.as_of,
                current_gsi=round(spec.global_scouting_index),
                current_ability_range_json={"minimum": max(round(spec.global_scouting_index) - 6, 1), "maximum": round(spec.global_scouting_index)},
                potential_range_json={"minimum": max(round(spec.global_scouting_index) + 4, 1), "maximum": round(spec.global_scouting_index) + 12},
                scout_confidence="high",
                generation_source="audit_fixture",
                status="active",
                club_quality_score=72.0,
                metadata_json={
                    "cohort_key": self.cohort_key,
                    "identity_rail": "regen_universe",
                    "provenance": "audit_fixture",
                },
            )
            self.session.add(regen)
            self.session.flush()
            return regen
        regen.linked_unique_card_id = card.id
        regen.generated_for_club_id = club.id
        regen.birth_country_code = spec.country_code
        regen.birth_region = spec.birth_region
        regen.birth_city = spec.birth_city
        regen.primary_position = spec.position
        regen.generated_at = self.as_of
        regen.current_gsi = round(spec.global_scouting_index)
        regen.metadata_json = {
            **(regen.metadata_json if isinstance(regen.metadata_json, dict) else {}),
            "cohort_key": self.cohort_key,
            "identity_rail": "regen_universe",
            "provenance": "audit_fixture",
        }
        return regen

    def _ensure_snapshot(self, player: Player, *, spec: AuditRegenSpec) -> PlayerValueSnapshotRecord:
        snapshot_id = self._snapshot_id(spec)
        snapshot = self.session.get(PlayerValueSnapshotRecord, snapshot_id)
        previous_credits = max(round(spec.current_value_credits - 12.0, 2), 1.0)
        if snapshot is None:
            snapshot = PlayerValueSnapshotRecord(
                id=snapshot_id,
                player_id=player.id,
                player_name=player.full_name,
                as_of=self.as_of,
                snapshot_type="intraday",
                previous_credits=previous_credits,
                target_credits=spec.current_value_credits,
                movement_pct=round(((spec.current_value_credits - previous_credits) / previous_credits) * 100, 2),
                football_truth_value_credits=max(spec.current_value_credits - 6.0, 1.0),
                market_signal_value_credits=max(spec.current_value_credits - 3.0, 1.0),
                scouting_signal_value_credits=spec.current_value_credits,
                egame_signal_value_credits=max(spec.current_value_credits - 8.0, 1.0),
                confidence_score=0.9,
                confidence_tier="high",
                liquidity_tier="default",
                market_integrity_score=0.93,
                signal_trust_score=0.95,
                trend_7d_pct=2.4,
                trend_30d_pct=6.8,
                trend_direction="up",
                trend_confidence=0.8,
                config_version="audit-fixture-v1",
                breakdown_json={
                    "published_card_value_credits": spec.current_value_credits,
                    "global_scouting_index": spec.global_scouting_index,
                    "previous_global_scouting_index": max(spec.global_scouting_index - 2.0, 1.0),
                    "global_scouting_index_movement_pct": 2.1,
                    "identity_rail": "regen_universe",
                },
                drivers_json=["authoritative_value_engine", "audit_fixture"],
                reason_codes_json=["regen_authoritative_fixture"],
            )
            self.session.add(snapshot)
            self.session.flush()
            return snapshot
        snapshot.player_id = player.id
        snapshot.player_name = player.full_name
        snapshot.as_of = self.as_of
        snapshot.previous_credits = previous_credits
        snapshot.target_credits = spec.current_value_credits
        snapshot.breakdown_json = {
            "published_card_value_credits": spec.current_value_credits,
            "global_scouting_index": spec.global_scouting_index,
            "previous_global_scouting_index": max(spec.global_scouting_index - 2.0, 1.0),
            "global_scouting_index_movement_pct": 2.1,
            "identity_rail": "regen_universe",
        }
        snapshot.drivers_json = ["authoritative_value_engine", "audit_fixture"]
        snapshot.reason_codes_json = ["regen_authoritative_fixture"]
        return snapshot

    def _ensure_summary(
        self,
        player: Player,
        *,
        snapshot: PlayerValueSnapshotRecord,
        spec: AuditRegenSpec,
    ) -> PlayerSummaryReadModel:
        summary = self.session.get(PlayerSummaryReadModel, player.id)
        summary_json = {
            "published_card_value_credits": spec.current_value_credits,
            "global_scouting_index": spec.global_scouting_index,
            "previous_global_scouting_index": max(spec.global_scouting_index - 2.0, 1.0),
            "global_scouting_index_movement_pct": 2.1,
            "avatar_seed_token": f"audit-regen-avatar:{self.cohort_key}:{spec.key}",
            "avatar_dna_seed": f"{self.cohort_key}:{spec.key}",
            "identity_rail": "regen_universe",
            "regen_metadata": {
                "cohort_key": self.cohort_key,
                "provenance": "audit_fixture",
            },
        }
        if summary is None:
            summary = PlayerSummaryReadModel(
                player_id=player.id,
                player_name=player.full_name,
                current_club_id=player.current_club_profile_id,
                current_club_name="Audit Regen Athletic",
                current_competition_id=None,
                current_competition_name=None,
                last_snapshot_id=snapshot.id,
                last_snapshot_at=self.as_of,
                current_value_credits=spec.current_value_credits,
                previous_value_credits=max(spec.current_value_credits - 12.0, 1.0),
                movement_pct=snapshot.movement_pct,
                average_rating=7.0,
                market_interest_score=42,
                summary_json=summary_json,
            )
            self.session.add(summary)
            self.session.flush()
            return summary
        summary.player_name = player.full_name
        summary.current_club_id = player.current_club_profile_id
        summary.current_club_name = "Audit Regen Athletic"
        summary.last_snapshot_id = snapshot.id
        summary.last_snapshot_at = self.as_of
        summary.current_value_credits = spec.current_value_credits
        summary.previous_value_credits = max(spec.current_value_credits - 12.0, 1.0)
        summary.movement_pct = snapshot.movement_pct
        summary.average_rating = 7.0
        summary.market_interest_score = 42
        summary.summary_json = summary_json
        return summary

    def _ensure_market_snapshot(
        self,
        player: Player,
        *,
        snapshot: PlayerValueSnapshotRecord,
        spec: AuditRegenSpec,
    ) -> PlayerMarketValueSnapshot:
        existing = next(
            (
                item
                for item in self.session.scalars(
                    select(PlayerMarketValueSnapshot)
                    .where(PlayerMarketValueSnapshot.player_id == player.id)
                    .order_by(PlayerMarketValueSnapshot.created_at.desc(), PlayerMarketValueSnapshot.id.desc())
                )
                if isinstance(item.metadata_json, dict)
                and item.metadata_json.get("cohort_key") == self.cohort_key
            ),
            None,
        )
        if existing is None:
            existing = PlayerMarketValueSnapshot(
                player_id=player.id,
                as_of=self.as_of,
                last_trade_price_credits=None,
                avg_trade_price_credits=spec.current_value_credits,
                volume_24h=0,
                listing_floor_price_credits=spec.current_value_credits,
                listing_count=0,
                high_24h_price_credits=spec.current_value_credits,
                low_24h_price_credits=spec.current_value_credits,
                metadata_json={},
            )
            self.session.add(existing)
        existing.as_of = self.as_of
        existing.avg_trade_price_credits = spec.current_value_credits
        existing.listing_floor_price_credits = spec.current_value_credits
        existing.high_24h_price_credits = spec.current_value_credits
        existing.low_24h_price_credits = spec.current_value_credits
        existing.metadata_json = {
            "source": "authoritative_value_engine",
            "authoritative_snapshot_id": snapshot.id,
            "identity_rail": "regen_universe",
            "cohort_key": self.cohort_key,
            "provenance": "audit_fixture",
        }
        self.session.flush()
        return existing

    def _snapshot_id(self, spec: AuditRegenSpec) -> str:
        return str(uuid5(NAMESPACE_URL, f"audit-regen-snapshot:{self.cohort_key}:{spec.key}"))


__all__ = [
    "AUDIT_REGEN_AS_OF",
    "AUDIT_REGEN_COHORT_KEY",
    "AUDIT_REGEN_SOURCE_PROVIDER",
    "AuditRegenCohortSeedResult",
    "AuditRegenCohortSeeder",
    "AuditRegenSpec",
    "DEFAULT_AUDIT_REGEN_COHORT",
]
