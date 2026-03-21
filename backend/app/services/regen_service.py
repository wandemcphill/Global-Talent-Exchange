from __future__ import annotations

from datetime import date, timedelta
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import random
from uuid import uuid4

from app.core.config import Settings, get_settings
from app.schemas.regen_core import (
    AbilityRangeView,
    AcademyCandidateView,
    AcademyIntakeBatchView,
    RegenLineageView,
    RegenOriginView,
    RegenPersonalityView,
    RegenProfileView,
    StarterRegenBundleView,
)
from app.services.club_finance_service import ClubOpsStore, get_club_ops_store

_PRIMARY_POSITIONS = ("GK", "CB", "RB", "LB", "DM", "CM", "AM", "RW", "LW", "ST")
_SECONDARY_POSITIONS = {
    "GK": (),
    "CB": ("RB", "LB", "DM"),
    "RB": ("CB", "LB", "RW"),
    "LB": ("CB", "RB", "LW"),
    "DM": ("CB", "CM"),
    "CM": ("DM", "AM"),
    "AM": ("CM", "RW", "LW", "ST"),
    "RW": ("AM", "LW", "ST"),
    "LW": ("AM", "RW", "ST"),
    "ST": ("AM", "RW", "LW"),
}
_SKIN_TONES = ("deep", "brown", "olive", "fair", "tan")
_HAIR_PROFILES = ("close_crop", "short_curl", "wavy", "braids", "buzz_cut")
_KIT_STYLES = ("classic", "modern", "street", "academy")
ACADEMY_CANDIDATE_CONTROL_WINDOW_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _season_label(as_of: datetime | None = None) -> str:
    current = as_of or _utcnow()
    start_year = current.year if current.month >= 7 else current.year - 1
    return f"{start_year}/{start_year + 1}"


def _clamp(value: float, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, round(value)))


def _scale_score(value: float) -> float:
    if value <= 5:
        return max(0.0, min(100.0, (value / 5.0) * 100.0))
    return max(0.0, min(100.0, value))


@dataclass(frozen=True, slots=True)
class RegenClubContext:
    country_code: str | None = None
    region_name: str | None = None
    city_name: str | None = None
    youth_coaching: float = 50.0
    training_level: float = 50.0
    academy_level: float = 50.0
    academy_investment: float = 50.0
    first_team_gsi: float = 55.0
    club_reputation: float = 50.0
    competition_quality: float = 50.0
    manager_youth_development: float = 50.0
    urbanicity: str | None = None


@dataclass(frozen=True, slots=True)
class LineageCandidate:
    legend_type: str
    ref_id: str
    display_name: str
    country_code: str
    region_name: str | None = None
    city_name: str | None = None
    eligible_club_ids: tuple[str, ...] = ()
    eligible_country_codes: tuple[str, ...] = ()
    allow_cross_country: bool = False
    is_celebrity: bool = False
    is_licensed: bool = False
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OwnerSonContext:
    owner_user_id: str
    club_id: str
    club_country_code: str
    club_region_name: str | None = None
    club_city_name: str | None = None
    rival_club_ids: tuple[str, ...] = ()
    lifetime_count: int = 0
    lifetime_cap: int = 3


@dataclass(frozen=True, slots=True)
class OwnerSonRequest:
    request_id: str
    club_id: str
    owner_user_id: str
    created_at: datetime
    customization: dict[str, object] = field(default_factory=dict)
    total_cost_coin: int = 0
    target_club_id: str | None = None


@dataclass(frozen=True, slots=True)
class LineageSelection:
    relationship_type: str
    related_legend_type: str
    related_legend_ref_id: str
    lineage_country_code: str
    lineage_region_name: str | None
    lineage_city_name: str | None
    lineage_hometown_code: str | None
    forced_surname: str | None = None
    is_owner_son: bool = False
    is_retired_regen_lineage: bool = False
    is_real_legend_lineage: bool = False
    is_celebrity_lineage: bool = False
    is_celebrity_licensed: bool = False
    lineage_tier: str = "rare"
    narrative_text: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NameProfile:
    key: str
    ethnolinguistic_profile: str
    religion_naming_pattern: str
    given_names: tuple[str, ...]
    surnames: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CountryNamingProfile:
    country_code: str
    default_region: str
    default_city: str
    urbanicity: str
    region_profile_weights: dict[str, tuple[tuple[str, float], ...]]
    profiles: dict[str, NameProfile]


@dataclass(frozen=True, slots=True)
class GeneratedAcademyIntake:
    batch: AcademyIntakeBatchView
    regens: tuple[RegenProfileView, ...]


_NAMING_PROFILES: dict[str, CountryNamingProfile] = {
    "NG": CountryNamingProfile(
        country_code="NG",
        default_region="Lagos",
        default_city="Lagos",
        urbanicity="urban",
        region_profile_weights={
            "lagos": (("yoruba_christian", 0.72), ("yoruba_muslim", 0.28)),
            "ogun": (("yoruba_christian", 0.78), ("yoruba_muslim", 0.22)),
            "oyo": (("yoruba_christian", 0.75), ("yoruba_muslim", 0.25)),
            "enugu": (("igbo_christian", 1.0),),
            "anambra": (("igbo_christian", 1.0),),
            "abia": (("igbo_christian", 1.0),),
            "kano": (("hausa_muslim", 1.0),),
            "kaduna": (("hausa_muslim", 0.82), ("hausa_christian", 0.18)),
        },
        profiles={
            "yoruba_christian": NameProfile(
                key="yoruba_christian",
                ethnolinguistic_profile="yoruba",
                religion_naming_pattern="christian",
                given_names=("Oluwaseun", "Ayomide", "Damilola", "Temiloluwa", "Fiyinfoluwa", "Samuel", "Daniel"),
                surnames=("Adekunle", "Adebayo", "Ogunleye", "Balogun", "Ojo", "Olatunji"),
            ),
            "yoruba_muslim": NameProfile(
                key="yoruba_muslim",
                ethnolinguistic_profile="yoruba",
                religion_naming_pattern="muslim",
                given_names=("Abdulraheem", "Mubarak", "Azeez", "Ridwan", "Ibrahim", "Mustapha"),
                surnames=("Adeleke", "Akinola", "Babatunde", "Balogun", "Lawal", "Adeyemi"),
            ),
            "igbo_christian": NameProfile(
                key="igbo_christian",
                ethnolinguistic_profile="igbo",
                religion_naming_pattern="christian",
                given_names=("Chibuzor", "Chinedu", "Kelechi", "Obinna", "Ifeanyi", "Jacob", "Somtochukwu"),
                surnames=("Okeke", "Eze", "Okafor", "Nwosu", "Umeh", "Onyeka"),
            ),
            "hausa_muslim": NameProfile(
                key="hausa_muslim",
                ethnolinguistic_profile="hausa",
                religion_naming_pattern="muslim",
                given_names=("Ibrahim", "Musa", "Abdullahi", "Sani", "Usman", "Kabiru", "Aminu"),
                surnames=("Musa", "Bello", "Garba", "Shehu", "Danjuma", "Suleiman"),
            ),
            "hausa_christian": NameProfile(
                key="hausa_christian",
                ethnolinguistic_profile="hausa",
                religion_naming_pattern="christian",
                given_names=("Yakubu", "Bitrus", "Jonathan", "Daniel", "Ishaya"),
                surnames=("Bako", "James", "Haruna", "Dogo", "Pam"),
            ),
        },
    ),
    "GH": CountryNamingProfile(
        country_code="GH",
        default_region="Greater Accra",
        default_city="Accra",
        urbanicity="urban",
        region_profile_weights={"default": (("akan", 1.0),)},
        profiles={
            "akan": NameProfile(
                key="akan",
                ethnolinguistic_profile="akan",
                religion_naming_pattern="mixed",
                given_names=("Kwame", "Kojo", "Yaw", "Kwaku", "Emmanuel", "Samuel"),
                surnames=("Mensah", "Owusu", "Boateng", "Asante", "Annan", "Ofori"),
            ),
        },
    ),
    "MA": CountryNamingProfile(
        country_code="MA",
        default_region="Casablanca-Settat",
        default_city="Casablanca",
        urbanicity="urban",
        region_profile_weights={"default": (("maghrebi_arabic", 1.0),)},
        profiles={
            "maghrebi_arabic": NameProfile(
                key="maghrebi_arabic",
                ethnolinguistic_profile="maghrebi_arabic",
                religion_naming_pattern="muslim",
                given_names=("Youssef", "Ayoub", "Zakaria", "Hamza", "Rayan", "Ilyas"),
                surnames=("El Idrissi", "Amrani", "Bennani", "Alaoui", "Mansouri", "Haddad"),
            ),
        },
    ),
    "BR": CountryNamingProfile(
        country_code="BR",
        default_region="Sao Paulo",
        default_city="Sao Paulo",
        urbanicity="urban",
        region_profile_weights={"default": (("brazil_portuguese", 1.0),)},
        profiles={
            "brazil_portuguese": NameProfile(
                key="brazil_portuguese",
                ethnolinguistic_profile="brazilian_portuguese",
                religion_naming_pattern="mixed",
                given_names=("Joao", "Pedro", "Gabriel", "Mateus", "Vinicius", "Caio"),
                surnames=("Silva", "Santos", "Costa", "Oliveira", "Souza", "Pereira"),
            ),
        },
    ),
    "ES": CountryNamingProfile(
        country_code="ES",
        default_region="Madrid",
        default_city="Madrid",
        urbanicity="urban",
        region_profile_weights={"default": (("spanish", 1.0),)},
        profiles={
            "spanish": NameProfile(
                key="spanish",
                ethnolinguistic_profile="spanish",
                religion_naming_pattern="mixed",
                given_names=("Alejandro", "Mateo", "Pablo", "Hugo", "Daniel", "Adrian"),
                surnames=("Garcia", "Lopez", "Martinez", "Fernandez", "Ruiz", "Navarro"),
            ),
        },
    ),
    "JP": CountryNamingProfile(
        country_code="JP",
        default_region="Tokyo",
        default_city="Tokyo",
        urbanicity="urban",
        region_profile_weights={"default": (("japanese", 1.0),)},
        profiles={
            "japanese": NameProfile(
                key="japanese",
                ethnolinguistic_profile="japanese",
                religion_naming_pattern="secular",
                given_names=("Haruto", "Ren", "Kaito", "Sora", "Yuto", "Riku"),
                surnames=("Sato", "Suzuki", "Takahashi", "Tanaka", "Watanabe", "Ito"),
            ),
        },
    ),
}


@dataclass(slots=True)
class RegenGenerationEngine:
    settings: Settings

    def compute_club_quality_score(self, context: RegenClubContext) -> float:
        weighted = (
            (_scale_score(context.youth_coaching) * 0.20)
            + (_scale_score(context.training_level) * 0.17)
            + (_scale_score(context.academy_level) * 0.20)
            + (_scale_score(context.academy_investment) * 0.12)
            + (_scale_score(context.first_team_gsi) * 0.15)
            + (_scale_score(context.club_reputation) * 0.10)
            + (_scale_score(context.competition_quality) * 0.04)
            + (_scale_score(context.manager_youth_development) * 0.02)
        )
        tuning = self._country_tuning(context.country_code)
        return max(10.0, min(95.0, round(weighted * tuning.academy_quality_bias, 2)))

    def generate_starter_regens(
        self,
        *,
        club_id: str,
        season_label: str,
        club_context: RegenClubContext,
        count: int | None = None,
        used_names: set[str] | None = None,
        rng: random.Random | None = None,
    ) -> StarterRegenBundleView:
        randomizer = rng or random.Random()
        regens = tuple(
            self._build_regen(
                club_id=club_id,
                generation_source="new_club",
                club_context=club_context,
                age=randomizer.randint(
                    self.settings.regen_generation.starter_age_min,
                    self.settings.regen_generation.starter_age_max,
                ),
                used_names=used_names or set(),
                rng=randomizer,
                current_gsi_override=self._starter_gsi(randomizer, club_context),
            )
            for _ in range(count or self.settings.regen_generation.starter_regen_count)
        )
        return StarterRegenBundleView(club_id=club_id, season_label=season_label, regens=regens)

    def generate_academy_intake(
        self,
        *,
        club_id: str,
        season_label: str,
        club_context: RegenClubContext,
        intake_size: int,
        used_names: set[str] | None = None,
        rng: random.Random | None = None,
        lineage_pool: tuple[LineageCandidate, ...] = (),
        owner_context: OwnerSonContext | None = None,
        owner_son_request: OwnerSonRequest | None = None,
    ) -> GeneratedAcademyIntake:
        randomizer = rng or random.Random()
        quality_score = self.compute_club_quality_score(club_context)
        batch_id = f"aint-{uuid4().hex[:12]}"
        generated_at = _utcnow()
        candidates: list[AcademyCandidateView] = []
        regens: list[RegenProfileView] = []
        used_local_names = used_names or set()
        lineage_assigned = False
        remaining_slots = intake_size
        if intake_size >= 2 and randomizer.random() < self.settings.regen_generation.twin_probability:
            twin_age = randomizer.randint(15, 18)
            twin_a, twin_b = self._build_twin_pair(
                club_id=club_id,
                club_context=club_context,
                age=twin_age,
                used_names=used_local_names,
                rng=randomizer,
            )
            regens.extend((twin_a, twin_b))
            remaining_slots -= 2
        for _ in range(max(remaining_slots, 0)):
            age = randomizer.randint(15, 18)
            lineage_selection = None
            if owner_son_request is not None:
                lineage_selection = self._resolve_lineage(
                    club_id=club_id,
                    club_context=club_context,
                    lineage_pool=lineage_pool,
                    owner_context=owner_context,
                    owner_son_request=owner_son_request,
                    rng=randomizer,
                )
                owner_son_request = None
                lineage_assigned = lineage_selection is not None or lineage_assigned
            elif not lineage_assigned:
                lineage_selection = self._resolve_lineage(
                    club_id=club_id,
                    club_context=club_context,
                    lineage_pool=lineage_pool,
                    owner_context=owner_context,
                    owner_son_request=None,
                    rng=randomizer,
                )
                lineage_assigned = lineage_selection is not None or lineage_assigned
            regen = self._build_regen(
                club_id=club_id,
                generation_source="academy",
                club_context=club_context,
                age=age,
                used_names=used_local_names,
                rng=randomizer,
                lineage_selection=lineage_selection,
            )
            regens.append(regen)
            candidate = AcademyCandidateView(
                id=f"acnd-{uuid4().hex[:12]}",
                batch_id=batch_id,
                club_id=club_id,
                regen_profile_id=regen.id,
                display_name=regen.display_name,
                age=regen.age,
                nationality_code=regen.birth_country_code,
                birth_region=regen.birth_region,
                birth_city=regen.birth_city,
                primary_position=regen.primary_position,
                secondary_position=regen.secondary_positions[0] if regen.secondary_positions else None,
                current_ability_range=regen.current_ability_range,
                potential_range=regen.potential_range,
                scout_confidence=regen.scout_confidence,
                status="academy_candidate",
                hometown_club_affinity=regen.origin.city_name or regen.origin.region_name,
                generated_at=generated_at,
                decision_deadline_on=(generated_at + timedelta(days=ACADEMY_CANDIDATE_CONTROL_WINDOW_DAYS)).date(),
                free_agency_status="club_control_window",
                platform_capture_share_pct=70,
                previous_club_capture_share_pct=30,
                special_training_eligible=regen.potential_range.maximum <= 75,
            )
            candidates.append(candidate)
        return GeneratedAcademyIntake(
            batch=AcademyIntakeBatchView(
                id=batch_id,
                club_id=club_id,
                season_label=season_label,
                intake_size=len(candidates),
                academy_quality_score=quality_score,
                generated_at=generated_at,
                candidates=tuple(candidates),
            ),
            regens=tuple(regens),
        )

    def _build_regen(
        self,
        *,
        club_id: str,
        generation_source: str,
        club_context: RegenClubContext,
        age: int,
        used_names: set[str],
        rng: random.Random,
        current_gsi_override: int | None = None,
        lineage_selection: LineageSelection | None = None,
        visual_seed_override: str | None = None,
    ) -> RegenProfileView:
        quality_score = self.compute_club_quality_score(club_context)
        origin, display_name = self._generate_identity(
            club_context=club_context,
            used_names=used_names,
            rng=rng,
            lineage_selection=lineage_selection,
        )
        customization = self._owner_customization(lineage_selection)
        if customization.get("name"):
            display_name = self._apply_custom_name(str(customization["name"]), used_names, rng)
        primary_position = rng.choice(_PRIMARY_POSITIONS)
        if customization.get("position"):
            primary_position = str(customization["position"])
        secondary_pool = _SECONDARY_POSITIONS[primary_position]
        secondary_positions = () if not secondary_pool else (secondary_pool[rng.randrange(len(secondary_pool))],)
        current_ability, potential = (
            self._starter_ranges(current_gsi=current_gsi_override or 58, rng=rng)
            if generation_source == "new_club"
            else self._academy_ranges(
                quality_score=quality_score,
                country_code=origin.country_code,
                rng=rng,
            )
        )
        current_gsi = current_gsi_override or round((current_ability.minimum + current_ability.maximum) / 2)
        scout_confidence = self._scout_confidence(quality_score=quality_score, generation_source=generation_source, rng=rng)
        regen_identifier = f"rgn-{uuid4().hex[:12]}"
        visual_seed = visual_seed_override or sha256(f"{regen_identifier}:{display_name}".encode("utf-8")).hexdigest()
        personality = self._build_personality(rng)
        decision_traits = {
            "ambition": personality.ambition,
            "loyalty": personality.loyalty,
            "professionalism": personality.professionalism,
            "greed": personality.greed,
            "patience": personality.patience,
            "hometown_affinity": personality.hometown_affinity,
            "trophy_hunger": personality.trophy_hunger,
            "media_appetite": personality.media_appetite,
            "temperament": personality.temperament,
            "adaptability": personality.adaptability,
        }
        lineage_metadata: dict[str, object] = {}
        relationship_tags: list[str] = []
        is_special_lineage = False
        if lineage_selection is not None:
            is_special_lineage = True
            lineage_metadata = {
                "relationship_type": lineage_selection.relationship_type,
                "related_legend_type": lineage_selection.related_legend_type,
                "related_legend_ref_id": lineage_selection.related_legend_ref_id,
                "lineage_country_code": lineage_selection.lineage_country_code,
                "lineage_region_name": lineage_selection.lineage_region_name,
                "lineage_city_name": lineage_selection.lineage_city_name,
                "lineage_hometown_code": lineage_selection.lineage_hometown_code,
                "lineage_tier": lineage_selection.lineage_tier,
                "is_owner_son": lineage_selection.is_owner_son,
                "is_retired_regen_lineage": lineage_selection.is_retired_regen_lineage,
                "is_real_legend_lineage": lineage_selection.is_real_legend_lineage,
                "is_celebrity_lineage": lineage_selection.is_celebrity_lineage,
                "is_celebrity_licensed": lineage_selection.is_celebrity_licensed,
                "narrative_text": lineage_selection.narrative_text,
            }
            if lineage_selection.metadata:
                lineage_metadata.update(lineage_selection.metadata)
            if customization:
                lineage_metadata["customization"] = dict(customization)
            relationship_tags = list(lineage_selection.tags)
        metadata = {
            "decision_traits": decision_traits,
            "career_state": {
                "contract_currency": "FanCoin",
                "transfer_listed": False,
                "free_agent": False,
                "retired": False,
            },
            "visual_profile": {
                "portrait_seed": visual_seed[:16],
                "skin_tone": _SKIN_TONES[int(visual_seed[0], 16) % len(_SKIN_TONES)],
                "hair_profile": _HAIR_PROFILES[int(visual_seed[1], 16) % len(_HAIR_PROFILES)],
                "kit_style": _KIT_STYLES[int(visual_seed[2], 16) % len(_KIT_STYLES)],
            },
        }
        if customization.get("hairstyle"):
            metadata["visual_profile"]["hair_profile"] = str(customization["hairstyle"])
        if lineage_metadata:
            metadata["lineage"] = lineage_metadata
        if relationship_tags:
            metadata["relationship_tags"] = relationship_tags
        if lineage_selection is not None:
            if lineage_selection.is_real_legend_lineage:
                metadata["son_of_legend"] = True
            if lineage_selection.is_owner_son:
                metadata["club_owner_son"] = True
            if lineage_selection.is_retired_regen_lineage:
                metadata["son_of_retired_regen"] = True
            if lineage_selection.relationship_type == "hometown_legacy":
                metadata["hometown_legacy"] = True
        return RegenProfileView(
            id=regen_identifier,
            regen_id=regen_identifier,
            club_id=club_id,
            player_id=None,
            linked_unique_card_id=f"card-{uuid4().hex[:12]}",
            display_name=display_name,
            age=age,
            birth_country_code=origin.country_code,
            birth_region=origin.region_name,
            birth_city=origin.city_name,
            primary_position=primary_position,
            secondary_positions=secondary_positions,
            current_gsi=current_gsi,
            current_ability_range=current_ability,
            potential_range=potential,
            scout_confidence=scout_confidence,
            generation_source=generation_source,
            status="academy_candidate" if generation_source == "academy" else "active",
            is_special_lineage=is_special_lineage,
            generated_at=_utcnow(),
            club_quality_score=quality_score,
            personality=personality,
            origin=origin,
            lineage=(
                None
                if lineage_selection is None
                else RegenLineageView(
                    relationship_type=lineage_selection.relationship_type,
                    related_legend_type=lineage_selection.related_legend_type,
                    related_legend_ref_id=lineage_selection.related_legend_ref_id,
                    lineage_country_code=lineage_selection.lineage_country_code,
                    lineage_hometown_code=lineage_selection.lineage_hometown_code,
                    is_owner_son=lineage_selection.is_owner_son,
                    is_retired_regen_lineage=lineage_selection.is_retired_regen_lineage,
                    is_real_legend_lineage=lineage_selection.is_real_legend_lineage,
                    is_celebrity_lineage=lineage_selection.is_celebrity_lineage,
                    is_celebrity_licensed=lineage_selection.is_celebrity_licensed,
                    lineage_tier=lineage_selection.lineage_tier,
                    narrative_text=lineage_selection.narrative_text,
                    tags=tuple(lineage_selection.tags),
                    metadata=dict(lineage_selection.metadata),
                )
            ),
            metadata=metadata,
        )

    def _starter_gsi(self, rng: random.Random, club_context: RegenClubContext) -> int:
        minimum = self.settings.regen_generation.starter_gsi_min
        maximum = self.settings.regen_generation.starter_gsi_max
        club_anchor = min(maximum, max(minimum, round((_scale_score(club_context.first_team_gsi) * 0.22) + 48)))
        return _clamp(rng.triangular(minimum, maximum, club_anchor), minimum, maximum)

    def _starter_ranges(self, *, current_gsi: int, rng: random.Random) -> tuple[AbilityRangeView, AbilityRangeView]:
        current = AbilityRangeView(
            minimum=_clamp(current_gsi - rng.randint(4, 6), 42, 78),
            maximum=_clamp(current_gsi + rng.randint(3, 5), 48, 80),
        )
        potential_max = _clamp(current.maximum + rng.randint(5, 10), current.maximum + 2, 82)
        potential = AbilityRangeView(
            minimum=_clamp(potential_max - rng.randint(6, 10), current.maximum, potential_max),
            maximum=potential_max,
        )
        return current, potential

    def _academy_ranges(
        self,
        *,
        quality_score: float,
        country_code: str,
        rng: random.Random,
    ) -> tuple[AbilityRangeView, AbilityRangeView]:
        base_current = 40 + (quality_score * 0.16) + rng.randint(-5, 5)
        current_low = _clamp(base_current - rng.randint(4, 7), 34, 75)
        current_high = _clamp(current_low + rng.randint(7, 12), current_low + 4, 82)
        elite_probability = self._elite_probability(quality_score=quality_score, country_code=country_code)
        potential_high = _clamp(64 + (quality_score * 0.18) + rng.randint(4, 18), current_high + 8, 97)
        if rng.random() < elite_probability:
            potential_high = max(potential_high, rng.randint(90, 97))
        potential_low = _clamp(potential_high - rng.randint(10, 18), current_high + 4, potential_high)
        return (
            AbilityRangeView(minimum=current_low, maximum=current_high),
            AbilityRangeView(minimum=potential_low, maximum=potential_high),
        )

    def _elite_probability(self, *, quality_score: float, country_code: str) -> float:
        config = self.settings.regen_generation
        tuning = self._country_tuning(country_code)
        probability = config.base_elite_probability + (quality_score / 100.0) * 0.05 + tuning.elite_probability_boost
        return min(config.max_elite_probability, max(config.base_elite_probability, probability))

    def _scout_confidence(self, *, quality_score: float, generation_source: str, rng: random.Random) -> str:
        if generation_source == "new_club":
            return "High"
        roll = quality_score + rng.randint(-10, 10)
        if roll >= 72:
            return "High"
        if roll >= 48:
            return "Medium"
        return "Low"

    def _build_personality(self, rng: random.Random) -> RegenPersonalityView:
        ambition = rng.randint(48, 86)
        loyalty = rng.randint(40, 82)
        professionalism = rng.randint(42, 88)
        greed = rng.randint(30, 84)
        patience = rng.randint(34, 84)
        hometown_affinity = rng.randint(32, 88)
        trophy_hunger = rng.randint(42, 90)
        media_appetite = rng.randint(18, 80)
        temperament = rng.randint(42, 78)
        adaptability = rng.randint(36, 86)
        work_rate = _clamp((professionalism * 0.6) + (ambition * 0.25) + rng.randint(-6, 6), 35, 92)
        resilience = _clamp((patience * 0.45) + (adaptability * 0.35) + rng.randint(-8, 8), 36, 90)
        leadership = _clamp((temperament * 0.35) + (professionalism * 0.3) + (ambition * 0.25) + rng.randint(-6, 6), 30, 82)
        flair = rng.randint(35, 84)
        tags: list[str] = []
        if professionalism >= 72:
            tags.append("professional")
        if ambition >= 72:
            tags.append("driven")
        if loyalty >= 70 or hometown_affinity >= 75:
            tags.append("club_loyal")
        if greed >= 72:
            tags.append("hard_bargainer")
        if not tags:
            tags.extend(("academy_bred", "grounded") if rng.random() < 0.5 else ("composed", "driven"))
        return RegenPersonalityView(
            temperament=temperament,
            leadership=leadership,
            ambition=ambition,
            loyalty=loyalty,
            professionalism=professionalism,
            greed=greed,
            patience=patience,
            hometown_affinity=hometown_affinity,
            trophy_hunger=trophy_hunger,
            media_appetite=media_appetite,
            adaptability=adaptability,
            work_rate=work_rate,
            flair=flair,
            resilience=resilience,
            personality_tags=tuple(tags),
        )

    def _resolve_lineage(
        self,
        *,
        club_id: str,
        club_context: RegenClubContext,
        lineage_pool: tuple[LineageCandidate, ...],
        owner_context: OwnerSonContext | None,
        owner_son_request: OwnerSonRequest | None,
        rng: random.Random,
    ) -> LineageSelection | None:
        config = self.settings.regen_generation
        if owner_son_request is not None:
            if owner_context is None:
                raise ValueError("owner_son_request_missing_context")
            if owner_context.lifetime_count >= owner_context.lifetime_cap:
                raise ValueError("owner_son_lifetime_cap_reached")
            return self._build_owner_son_lineage(owner_context, owner_son_request, rng)

        if rng.random() >= config.lineage_base_probability:
            return None

        eligible_legends = [
            candidate
            for candidate in lineage_pool
            if candidate.legend_type == "real_legend" and self._lineage_candidate_allowed(candidate, club_id, club_context)
        ]
        eligible_retired = [
            candidate
            for candidate in lineage_pool
            if candidate.legend_type == "retired_regen" and self._lineage_candidate_allowed(candidate, club_id, club_context)
        ]
        allow_owner = owner_context is not None and owner_context.lifetime_count < owner_context.lifetime_cap
        allow_hometown = club_context.city_name is not None or club_context.region_name is not None

        choices: list[tuple[str, float]] = []
        if eligible_legends and config.lineage_legend_probability > 0:
            choices.append(("legend", config.lineage_legend_probability))
        if eligible_retired and config.lineage_retired_regen_probability > 0:
            choices.append(("retired_regen", config.lineage_retired_regen_probability))
        if allow_owner and config.lineage_owner_probability > 0:
            choices.append(("owner", config.lineage_owner_probability))
        if allow_hometown and config.lineage_hometown_probability > 0:
            choices.append(("hometown", config.lineage_hometown_probability))
        if not choices:
            return None

        selection_key = self._weighted_choice(tuple(choices), rng)
        if selection_key == "legend":
            candidate = rng.choice(eligible_legends)
            return self._build_legend_lineage(candidate)
        if selection_key == "retired_regen":
            candidate = rng.choice(eligible_retired)
            return self._build_retired_regen_lineage(candidate)
        if selection_key == "owner" and owner_context is not None:
            return self._build_owner_son_lineage(owner_context, None, rng)
        if selection_key == "hometown":
            return self._build_hometown_lineage(club_id, club_context)
        return None

    def _lineage_candidate_allowed(
        self,
        candidate: LineageCandidate,
        club_id: str,
        club_context: RegenClubContext,
    ) -> bool:
        if candidate.is_celebrity and not candidate.is_licensed:
            return False
        if candidate.eligible_club_ids and club_id not in candidate.eligible_club_ids:
            return False
        club_country = (club_context.country_code or "").upper()
        candidate_country = candidate.country_code.upper()
        if candidate_country == club_country:
            return True
        if candidate.allow_cross_country:
            return True
        if club_country and club_country in {code.upper() for code in candidate.eligible_country_codes}:
            return True
        return False

    @staticmethod
    def _candidate_surname(display_name: str) -> str | None:
        parts = [part for part in display_name.strip().split(" ") if part]
        if len(parts) < 2:
            return None
        return parts[-1]

    def _build_legend_lineage(self, candidate: LineageCandidate) -> LineageSelection:
        surname = self._candidate_surname(candidate.display_name)
        metadata = {
            "legend_name": candidate.display_name,
            "legend_country_code": candidate.country_code,
            "legend_region_name": candidate.region_name,
            "legend_city_name": candidate.city_name,
        }
        if candidate.metadata:
            metadata.update(candidate.metadata)
        return LineageSelection(
            relationship_type="son_of_legend",
            related_legend_type="real_legend",
            related_legend_ref_id=candidate.ref_id,
            lineage_country_code=candidate.country_code.upper(),
            lineage_region_name=candidate.region_name,
            lineage_city_name=candidate.city_name,
            lineage_hometown_code=candidate.city_name or candidate.region_name,
            forced_surname=surname,
            is_real_legend_lineage=True,
            is_celebrity_lineage=candidate.is_celebrity,
            is_celebrity_licensed=candidate.is_licensed,
            tags=("son_of_legend", "lineage"),
            metadata=metadata,
        )

    def _build_retired_regen_lineage(self, candidate: LineageCandidate) -> LineageSelection:
        surname = self._candidate_surname(candidate.display_name)
        metadata = {
            "legend_name": candidate.display_name,
            "legend_country_code": candidate.country_code,
            "legend_region_name": candidate.region_name,
            "legend_city_name": candidate.city_name,
        }
        if candidate.metadata:
            metadata.update(candidate.metadata)
        return LineageSelection(
            relationship_type="son_of_retired_regen",
            related_legend_type="retired_regen",
            related_legend_ref_id=candidate.ref_id,
            lineage_country_code=candidate.country_code.upper(),
            lineage_region_name=candidate.region_name,
            lineage_city_name=candidate.city_name,
            lineage_hometown_code=candidate.city_name or candidate.region_name,
            forced_surname=surname,
            is_retired_regen_lineage=True,
            tags=("son_of_retired_regen", "lineage"),
            metadata=metadata,
        )

    def _build_owner_son_lineage(
        self,
        owner_context: OwnerSonContext,
        owner_son_request: OwnerSonRequest | None,
        rng: random.Random,
    ) -> LineageSelection:
        destination_club_id = owner_context.club_id
        if owner_context.rival_club_ids and rng.random() < self.settings.regen_generation.owner_son_rival_club_chance:
            destination_club_id = rng.choice(owner_context.rival_club_ids)
        metadata: dict[str, object] = {
            "owner_user_id": owner_context.owner_user_id,
            "owner_club_id": owner_context.club_id,
            "owner_destination_club_id": destination_club_id,
        }
        if owner_son_request is not None:
            metadata.update(
                {
                    "owner_request_id": owner_son_request.request_id,
                    "paid_request": True,
                    "customization": dict(owner_son_request.customization),
                    "cost_coin": owner_son_request.total_cost_coin,
                }
            )
        return LineageSelection(
            relationship_type="son_of_owner",
            related_legend_type="club_owner",
            related_legend_ref_id=owner_context.owner_user_id,
            lineage_country_code=owner_context.club_country_code.upper(),
            lineage_region_name=owner_context.club_region_name,
            lineage_city_name=owner_context.club_city_name,
            lineage_hometown_code=owner_context.club_city_name or owner_context.club_region_name,
            is_owner_son=True,
            tags=("son_of_owner", "lineage"),
            metadata=metadata,
        )

    def _build_hometown_lineage(self, club_id: str, club_context: RegenClubContext) -> LineageSelection:
        hometown_code = club_context.city_name or club_context.region_name or ""
        return LineageSelection(
            relationship_type="hometown_legacy",
            related_legend_type="hometown",
            related_legend_ref_id=club_id,
            lineage_country_code=(club_context.country_code or self.settings.regen_generation.default_country_code).upper(),
            lineage_region_name=club_context.region_name,
            lineage_city_name=club_context.city_name,
            lineage_hometown_code=hometown_code,
            tags=("hometown_hero", "lineage"),
            metadata={"hometown_code": hometown_code},
        )

    def _owner_customization(self, lineage_selection: LineageSelection | None) -> dict[str, object]:
        if lineage_selection is None or not lineage_selection.is_owner_son:
            return {}
        metadata = lineage_selection.metadata or {}
        if not isinstance(metadata, dict):
            return {}
        if not metadata.get("paid_request"):
            return {}
        customization = metadata.get("customization")
        if not isinstance(customization, dict):
            return {}
        return self._sanitize_owner_customization(customization)

    @staticmethod
    def _sanitize_owner_customization(customization: dict[str, object]) -> dict[str, object]:
        sanitized: dict[str, object] = {}
        raw_name = customization.get("name")
        if isinstance(raw_name, str):
            trimmed = " ".join(raw_name.split())
            if trimmed:
                sanitized["name"] = trimmed
        raw_position = customization.get("position")
        if isinstance(raw_position, str):
            position = raw_position.strip().upper()
            if position in _PRIMARY_POSITIONS:
                sanitized["position"] = position
        raw_foot = customization.get("favorite_foot")
        if isinstance(raw_foot, str):
            foot = raw_foot.strip().lower()
            if foot in {"left", "right", "both"}:
                sanitized["favorite_foot"] = foot
        raw_height = customization.get("height_cm")
        if raw_height is not None:
            try:
                height_cm = int(raw_height)
            except (TypeError, ValueError):
                height_cm = None
            if height_cm is not None and 145 <= height_cm <= 210:
                sanitized["height_cm"] = height_cm
        raw_hairstyle = customization.get("hairstyle")
        if isinstance(raw_hairstyle, str):
            hairstyle = raw_hairstyle.strip().lower()
            if hairstyle in _HAIR_PROFILES:
                sanitized["hairstyle"] = hairstyle
        return sanitized

    @staticmethod
    def _apply_custom_name(name: str, used_names: set[str], rng: random.Random) -> str:
        desired = " ".join(name.split())
        if not desired:
            return name
        if desired not in used_names:
            used_names.add(desired)
            return desired
        for _ in range(20):
            candidate = f"{desired} {rng.randint(2, 99)}"
            if candidate not in used_names:
                used_names.add(candidate)
                return candidate
        candidate = f"{desired} {rng.randint(100, 999)}"
        used_names.add(candidate)
        return candidate

    @staticmethod
    def _adjust_range(base: AbilityRangeView, rng: random.Random, *, min_value: int = 30, max_value: int = 99) -> AbilityRangeView:
        delta_min = rng.randint(-2, 2)
        delta_max = rng.randint(-2, 2)
        if delta_min == 0 and delta_max == 0:
            delta_min = rng.choice((-1, 1))
        new_min = _clamp(base.minimum + delta_min, min_value, max_value - 1)
        new_max = _clamp(base.maximum + delta_max, new_min + 1, max_value)
        return AbilityRangeView(minimum=new_min, maximum=new_max)

    def _build_twin_pair(
        self,
        *,
        club_id: str,
        club_context: RegenClubContext,
        age: int,
        used_names: set[str],
        rng: random.Random,
    ) -> tuple[RegenProfileView, RegenProfileView]:
        group_key = f"twins-{uuid4().hex[:10]}"
        base_regen = self._build_regen(
            club_id=club_id,
            generation_source="academy",
            club_context=club_context,
            age=age,
            used_names=used_names,
            rng=rng,
        )
        base_visual_seed = str(base_regen.metadata.get("visual_profile", {}).get("portrait_seed", ""))
        base_current = base_regen.current_ability_range
        base_potential = base_regen.potential_range

        surname = base_regen.display_name.split(" ")[-1]
        country_profile = _NAMING_PROFILES.get(
            base_regen.birth_country_code,
            _NAMING_PROFILES[self.settings.regen_generation.default_country_code],
        )
        given_pool: list[str] = []
        for profile in country_profile.profiles.values():
            given_pool.extend(profile.given_names)
        for _ in range(25):
            candidate_name = f"{rng.choice(given_pool)} {surname}"
            if candidate_name not in used_names:
                used_names.add(candidate_name)
                break
        else:
            candidate_name = f"{base_regen.display_name} Jr {rng.randint(2, 99)}"
            used_names.add(candidate_name)

        twin_personality = base_regen.personality.model_copy(
            update={
                "temperament": _clamp(base_regen.personality.temperament + rng.randint(-6, 6), 30, 95),
                "ambition": _clamp(base_regen.personality.ambition + rng.randint(-6, 6), 30, 95),
                "loyalty": _clamp(base_regen.personality.loyalty + rng.randint(-6, 6), 30, 95),
            }
        )
        twin_current = self._adjust_range(base_current, rng)
        twin_potential = self._adjust_range(base_potential, rng)
        similarity_score = max(
            0.7,
            round(
                1.0
                - (
                    abs(base_current.minimum - twin_current.minimum)
                    + abs(base_current.maximum - twin_current.maximum)
                    + abs(base_potential.maximum - twin_potential.maximum)
                )
                / 120.0,
                3,
            ),
        )

        twin_metadata = dict(base_regen.metadata)
        visual_profile = dict(twin_metadata.get("visual_profile") or {})
        if base_visual_seed:
            visual_profile["portrait_seed"] = base_visual_seed
        hair_index = _HAIR_PROFILES.index(visual_profile.get("hair_profile")) if visual_profile.get("hair_profile") in _HAIR_PROFILES else 0
        visual_profile["hair_profile"] = _HAIR_PROFILES[(hair_index + 1) % len(_HAIR_PROFILES)]
        twin_metadata["visual_profile"] = visual_profile
        twin_metadata["twins_group_key"] = group_key
        twin_metadata["twin_variant"] = "B"
        twin_metadata["relationship_tags"] = list({*(twin_metadata.get("relationship_tags") or []), "twin"})
        twin_metadata["twin_similarity_score"] = similarity_score

        twin_regen = base_regen.model_copy(
            update={
                "id": f"rgn-{uuid4().hex[:12]}",
                "regen_id": f"rgn-{uuid4().hex[:12]}",
                "linked_unique_card_id": f"card-{uuid4().hex[:12]}",
                "display_name": candidate_name,
                "current_ability_range": twin_current,
                "potential_range": twin_potential,
                "personality": twin_personality,
                "metadata": twin_metadata,
                "is_special_lineage": True,
            }
        )

        base_metadata = dict(base_regen.metadata)
        base_metadata["twins_group_key"] = group_key
        base_metadata["twin_variant"] = "A"
        base_metadata["relationship_tags"] = list({*(base_metadata.get("relationship_tags") or []), "twin"})
        base_metadata["twin_similarity_score"] = similarity_score
        base_regen = base_regen.model_copy(
            update={
                "metadata": base_metadata,
                "is_special_lineage": True,
            }
        )
        return base_regen, twin_regen

    def _generate_identity(
        self,
        *,
        club_context: RegenClubContext,
        used_names: set[str],
        rng: random.Random,
        lineage_selection: LineageSelection | None = None,
    ) -> tuple[RegenOriginView, str]:
        lineage_country = lineage_selection.lineage_country_code if lineage_selection else None
        lineage_region = lineage_selection.lineage_region_name if lineage_selection else None
        lineage_city = lineage_selection.lineage_city_name if lineage_selection else None
        forced_surname = lineage_selection.forced_surname if lineage_selection else None
        country_code = (lineage_country or club_context.country_code or self.settings.regen_generation.default_country_code).upper()
        country_profile = _NAMING_PROFILES.get(country_code, _NAMING_PROFILES[self.settings.regen_generation.default_country_code])
        region_name = lineage_region or club_context.region_name or country_profile.default_region
        city_name = lineage_city or club_context.city_name or country_profile.default_city
        region_key = region_name.strip().lower()
        profile_weights = country_profile.region_profile_weights.get(region_key) or country_profile.region_profile_weights.get("default")
        assert profile_weights is not None
        profile_key = self._weighted_choice(profile_weights, rng)
        profile = country_profile.profiles[profile_key]

        for _ in range(50):
            surname = forced_surname or rng.choice(profile.surnames)
            display_name = f"{rng.choice(profile.given_names)} {surname}"
            if display_name not in used_names:
                used_names.add(display_name)
                return (
                    RegenOriginView(
                        country_code=country_profile.country_code,
                        region_name=region_name,
                        city_name=city_name,
                        ethnolinguistic_profile=profile.ethnolinguistic_profile,
                        religion_naming_pattern=profile.religion_naming_pattern,
                        urbanicity=club_context.urbanicity or country_profile.urbanicity,
                    ),
                    display_name,
                )
        surname = forced_surname or rng.choice(profile.surnames)
        display_name = f"{rng.choice(profile.given_names)} {surname} {rng.randint(2, 99)}"
        used_names.add(display_name)
        return (
            RegenOriginView(
                country_code=country_profile.country_code,
                region_name=region_name,
                city_name=city_name,
                ethnolinguistic_profile=profile.ethnolinguistic_profile,
                religion_naming_pattern=profile.religion_naming_pattern,
                urbanicity=club_context.urbanicity or country_profile.urbanicity,
            ),
            display_name,
        )

    def _country_tuning(self, country_code: str | None):
        resolved = (country_code or self.settings.regen_generation.default_country_code).upper()
        for tuning in self.settings.regen_generation.country_tuning:
            if tuning.country_code == resolved:
                return tuning
        return self.settings.regen_generation.country_tuning[0]

    @staticmethod
    def _weighted_choice(choices: tuple[tuple[str, float], ...], rng: random.Random) -> str:
        total = sum(weight for _, weight in choices)
        roll = rng.random() * total
        running = 0.0
        for key, weight in choices:
            running += weight
            if roll <= running:
                return key
        return choices[-1][0]


class RegenService:
    def __init__(
        self,
        *,
        store: ClubOpsStore | None = None,
        settings: Settings | None = None,
        engine: RegenGenerationEngine | None = None,
    ) -> None:
        self.store = store or get_club_ops_store()
        self.settings = settings or get_settings()
        self.engine = engine or RegenGenerationEngine(self.settings)

    def request_owner_son(
        self,
        *,
        club_id: str,
        owner_user_id: str,
        customization: dict[str, object] | None = None,
    ) -> OwnerSonRequest:
        self._ensure_club_setup(club_id)
        config = self.settings.regen_generation
        payload = customization or {}
        base_cost = config.owner_son_paid_request_base_cost
        name_cost = config.owner_son_paid_request_name_cost if payload.get("name") else 0
        customization_keys = {"position", "favorite_foot", "height_cm", "hairstyle"}
        customization_cost = config.owner_son_paid_request_customization_cost if customization_keys & payload.keys() else 0
        total_cost = base_cost + name_cost + customization_cost
        with self.store.lock:
            existing_requests: list[object] = []
            for requests in self.store.owner_son_pending_requests_by_club.values():
                existing_requests.extend(
                    request for request in requests if getattr(request, "owner_user_id", None) == owner_user_id
                )
            for requests in self.store.owner_son_fulfilled_requests_by_club.values():
                existing_requests.extend(
                    request for request in requests if getattr(request, "owner_user_id", None) == owner_user_id
                )
            if len(existing_requests) >= config.owner_son_paid_request_limit:
                raise ValueError("owner_son_paid_request_limit_reached")
            request = OwnerSonRequest(
                request_id=f"owner-son-{uuid4().hex[:12]}",
                club_id=club_id,
                owner_user_id=owner_user_id,
                created_at=_utcnow(),
                customization=payload,
                total_cost_coin=total_cost,
            )
            self.store.owner_son_pending_requests_by_club.setdefault(club_id, []).append(request)
        return request

    def generate_academy_intake(
        self,
        *,
        club_id: str,
        club_context: RegenClubContext,
        season_label: str | None = None,
        intake_size: int | None = None,
        total_active_player_base: int | None = None,
        random_seed: int | None = None,
        lineage_pool: tuple[LineageCandidate, ...] = (),
        owner_context: OwnerSonContext | None = None,
        owner_son_request_id: str | None = None,
        rival_club_ids: tuple[str, ...] = (),
    ) -> AcademyIntakeBatchView:
        resolved_season = season_label or _season_label()
        self._ensure_club_setup(club_id)
        with self.store.lock:
            existing_batch = next(
                (
                    batch
                    for batch in self.store.academy_intake_batches_by_club.get(club_id, {}).values()
                    if getattr(batch, "season_label", None) == resolved_season
                ),
                None,
            )
        if existing_batch is not None:
            raise ValueError("academy_intake_already_generated")

        randomizer = random.Random(random_seed)
        requested = intake_size or randomizer.randint(
            self.settings.regen_generation.academy_intake_min_players,
            self.settings.regen_generation.academy_intake_max_players,
        )
        allowed = self._remaining_generation_capacity(
            season_label=resolved_season,
            total_active_player_base=total_active_player_base,
        )
        if allowed <= 0:
            raise ValueError("season_regen_supply_cap_reached")
        effective_size = max(1, min(requested, allowed))
        used_names = self._used_names(club_id)
        pending_request: OwnerSonRequest | None = None
        if owner_son_request_id is not None:
            with self.store.lock:
                for request in self.store.owner_son_pending_requests_by_club.get(club_id, []):
                    if getattr(request, "request_id", None) == owner_son_request_id:
                        pending_request = request
                        break
        else:
            with self.store.lock:
                pending_requests = self.store.owner_son_pending_requests_by_club.get(club_id, [])
                if pending_requests:
                    pending_request = pending_requests[0]
        if pending_request is not None and owner_context is None:
            owner_son_count = self.store.owner_son_lifetime_counts_by_user.get(pending_request.owner_user_id, 0)
            owner_context = OwnerSonContext(
                owner_user_id=pending_request.owner_user_id,
                club_id=club_id,
                club_country_code=club_context.country_code or self.settings.regen_generation.default_country_code,
                club_region_name=club_context.region_name,
                club_city_name=club_context.city_name,
                rival_club_ids=rival_club_ids,
                lifetime_count=owner_son_count,
                lifetime_cap=self.settings.regen_generation.owner_son_lifetime_cap,
            )
        if owner_context is not None:
            owner_son_count = self.store.owner_son_lifetime_counts_by_user.get(owner_context.owner_user_id, 0)
            owner_context = OwnerSonContext(
                owner_user_id=owner_context.owner_user_id,
                club_id=owner_context.club_id,
                club_country_code=owner_context.club_country_code,
                club_region_name=owner_context.club_region_name,
                club_city_name=owner_context.club_city_name,
                rival_club_ids=owner_context.rival_club_ids or rival_club_ids,
                lifetime_count=owner_son_count,
                lifetime_cap=self.settings.regen_generation.owner_son_lifetime_cap,
            )
            if pending_request is not None and owner_context.lifetime_count >= owner_context.lifetime_cap:
                raise ValueError("owner_son_lifetime_cap_reached")
        generated = self.engine.generate_academy_intake(
            club_id=club_id,
            season_label=resolved_season,
            club_context=club_context,
            intake_size=effective_size,
            used_names=used_names,
            rng=randomizer,
            lineage_pool=lineage_pool,
            owner_context=owner_context,
            owner_son_request=pending_request,
        )
        batch = generated.batch
        with self.store.lock:
            self.store.academy_intake_batches_by_club.setdefault(club_id, {})[batch.id] = batch
            self.store.academy_candidates_by_club.setdefault(club_id, {})
            self.store.regen_profiles_by_club.setdefault(club_id, {})
            self.store.regen_generation_events_by_club.setdefault(club_id, [])
            for candidate in batch.candidates:
                self.store.academy_candidates_by_club[club_id][candidate.id] = candidate
            for regen in generated.regens:
                self.store.regen_profiles_by_club[club_id][regen.id] = regen
                self.store.regen_generation_events_by_club[club_id].append(
                    {
                        "regen_id": regen.regen_id,
                        "club_id": club_id,
                        "season_label": resolved_season,
                        "generation_source": regen.generation_source,
                    }
                )
            if pending_request is not None:
                pending_list = self.store.owner_son_pending_requests_by_club.get(club_id, [])
                if pending_request in pending_list:
                    pending_list.remove(pending_request)
                self.store.owner_son_fulfilled_requests_by_club.setdefault(club_id, []).append(pending_request)
            for regen in generated.regens:
                lineage = regen.metadata.get("lineage") or {}
                if lineage.get("is_owner_son") or regen.metadata.get("club_owner_son"):
                    owner_user_id = lineage.get("owner_user_id") or (owner_context.owner_user_id if owner_context else None)
                    if owner_user_id:
                        self.store.owner_son_lifetime_counts_by_user[owner_user_id] = (
                            self.store.owner_son_lifetime_counts_by_user.get(owner_user_id, 0) + 1
                        )
            self.store.season_regen_generation_counts[resolved_season] = (
                self.store.season_regen_generation_counts.get(resolved_season, 0) + effective_size
            )
        return batch

    def generate_starter_regens(
        self,
        *,
        club_id: str,
        club_context: RegenClubContext,
        season_label: str | None = None,
        total_active_player_base: int | None = None,
        random_seed: int | None = None,
    ) -> StarterRegenBundleView:
        resolved_season = season_label or _season_label()
        self._ensure_club_setup(club_id)
        with self.store.lock:
            existing_regens = tuple(
                regen
                for regen in self.store.regen_profiles_by_club.get(club_id, {}).values()
                if regen.generation_source == "new_club"
            )
        if existing_regens:
            return StarterRegenBundleView(club_id=club_id, season_label=resolved_season, regens=existing_regens)

        requested = self.settings.regen_generation.starter_regen_count
        allowed = self._remaining_generation_capacity(
            season_label=resolved_season,
            total_active_player_base=total_active_player_base,
        )
        if allowed < requested:
            raise ValueError("season_regen_supply_cap_reached")
        bundle = self.engine.generate_starter_regens(
            club_id=club_id,
            season_label=resolved_season,
            club_context=club_context,
            count=requested,
            used_names=self._used_names(club_id),
            rng=random.Random(random_seed),
        )
        with self.store.lock:
            self.store.regen_profiles_by_club.setdefault(club_id, {})
            self.store.regen_generation_events_by_club.setdefault(club_id, [])
            for regen in bundle.regens:
                self.store.regen_profiles_by_club[club_id][regen.id] = regen
                self.store.regen_generation_events_by_club[club_id].append(
                    {
                        "regen_id": regen.regen_id,
                        "club_id": club_id,
                        "season_label": resolved_season,
                        "generation_source": regen.generation_source,
                    }
                )
            self.store.season_regen_generation_counts[resolved_season] = (
                self.store.season_regen_generation_counts.get(resolved_season, 0) + len(bundle.regens)
            )
        return bundle

    def list_regens(self, club_id: str) -> tuple[RegenProfileView, ...]:
        with self.store.lock:
            return tuple(self.store.regen_profiles_by_club.get(club_id, {}).values())

    def list_academy_candidates(self, club_id: str) -> tuple[AcademyCandidateView, ...]:
        with self.store.lock:
            return tuple(self.store.academy_candidates_by_club.get(club_id, {}).values())

    def expire_candidate_control_windows(self, *, reference_on: date | None = None) -> tuple[AcademyCandidateView, ...]:
        effective_date = reference_on or _utcnow().date()
        released: list[AcademyCandidateView] = []
        with self.store.lock:
            for candidates in self.store.academy_candidates_by_club.values():
                for candidate_id, candidate in list(candidates.items()):
                    if candidate.status != "academy_candidate" or candidate.decision_deadline_on is None:
                        continue
                    if candidate.decision_deadline_on > effective_date:
                        continue
                    updated = candidate.model_copy(
                        update={
                            "status": "free_agent",
                            "free_agency_status": "open_market",
                        }
                    )
                    candidates[candidate_id] = updated
                    released.append(updated)
        return tuple(released)

    def list_free_agents(self) -> tuple[AcademyCandidateView, ...]:
        with self.store.lock:
            free_agents = [
                candidate
                for candidates in self.store.academy_candidates_by_club.values()
                for candidate in candidates.values()
                if candidate.status == "free_agent"
            ]
        return tuple(sorted(free_agents, key=lambda candidate: (candidate.generated_at, candidate.display_name)))

    def get_season_generation_count(self, season_label: str) -> int:
        with self.store.lock:
            return self.store.season_regen_generation_counts.get(season_label, 0)

    def get_season_generation_cap(self, *, total_active_player_base: int | None = None) -> int:
        active_base = total_active_player_base or self.settings.regen_generation.default_active_player_base
        return max(1, round(active_base * self.settings.regen_generation.seasonal_supply_cap_ratio))

    def _remaining_generation_capacity(self, *, season_label: str, total_active_player_base: int | None) -> int:
        cap = self.get_season_generation_cap(total_active_player_base=total_active_player_base)
        used = self.get_season_generation_count(season_label)
        return max(0, cap - used)

    def _used_names(self, club_id: str) -> set[str]:
        with self.store.lock:
            regens = self.store.regen_profiles_by_club.get(club_id, {}).values()
            candidates = self.store.academy_candidates_by_club.get(club_id, {}).values()
            return {item.display_name for item in regens} | {item.display_name for item in candidates}

    def _ensure_club_setup(self, club_id: str) -> None:
        with self.store.lock:
            self.store.regen_profiles_by_club.setdefault(club_id, {})
            self.store.academy_intake_batches_by_club.setdefault(club_id, {})
            self.store.academy_candidates_by_club.setdefault(club_id, {})
            self.store.regen_generation_events_by_club.setdefault(club_id, [])
            self.store.owner_son_pending_requests_by_club.setdefault(club_id, [])
            self.store.owner_son_fulfilled_requests_by_club.setdefault(club_id, [])


@lru_cache
def get_regen_service() -> RegenService:
    return RegenService(store=get_club_ops_store(), settings=get_settings())


__all__ = [
    "LineageCandidate",
    "LineageSelection",
    "OwnerSonContext",
    "OwnerSonRequest",
    "RegenClubContext",
    "RegenGenerationEngine",
    "RegenService",
    "get_regen_service",
]
