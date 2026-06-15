from __future__ import annotations

from datetime import date, timedelta
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import random
import unicodedata
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
from app.regen_universe.dna import generate_dna_profile
from app.services.club_finance_service import ClubOpsStore, get_club_ops_store
from app.services.regen_country_name_pools import COUNTRY_NAME_PROFILE_ALIASES, COUNTRY_SPECIFIC_NAME_POOLS

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


def _name_profile(
    *,
    key: str,
    ethnolinguistic_profile: str,
    religion_naming_pattern: str,
    given_names: tuple[str, ...],
    surnames: tuple[str, ...],
) -> NameProfile:
    return NameProfile(
        key=key,
        ethnolinguistic_profile=ethnolinguistic_profile,
        religion_naming_pattern=religion_naming_pattern,
        given_names=given_names,
        surnames=surnames,
    )


def _country_profile(
    *,
    country_code: str,
    default_region: str,
    default_city: str,
    urbanicity: str,
    profiles: tuple[NameProfile, ...],
    region_profile_weights: dict[str, tuple[tuple[str, float], ...]] | None = None,
) -> CountryNamingProfile:
    if region_profile_weights is None:
        if len(profiles) != 1:
            raise ValueError("region_profile_weights_required_for_multi_profile_country")
        region_profile_weights = {"default": ((profiles[0].key, 1.0),)}
    return CountryNamingProfile(
        country_code=country_code,
        default_region=default_region,
        default_city=default_city,
        urbanicity=urbanicity,
        region_profile_weights=region_profile_weights,
        profiles={profile.key: profile for profile in profiles},
    )


def _weighted_name_profile(
    country_profile: CountryNamingProfile,
    *,
    region_name: str | None,
    rng: random.Random,
) -> NameProfile:
    region_key = (region_name or country_profile.default_region).strip().lower()
    profile_weights = country_profile.region_profile_weights.get(
        region_key
    ) or country_profile.region_profile_weights.get("default")
    assert profile_weights is not None
    total = sum(max(weight, 0.0) for _, weight in profile_weights)
    if total <= 0:
        return next(iter(country_profile.profiles.values()))
    marker = rng.random() * total
    running = 0.0
    for profile_key, weight in profile_weights:
        running += max(weight, 0.0)
        if marker <= running:
            return country_profile.profiles[profile_key]
    return country_profile.profiles[profile_weights[-1][0]]


def generate_country_display_name(
    country_profile: CountryNamingProfile,
    *,
    region_name: str | None = None,
    used_names: set[str] | None = None,
    rng: random.Random | None = None,
    forced_surname: str | None = None,
) -> tuple[NameProfile, str]:
    randomizer = rng or random.Random()
    used = used_names if used_names is not None else set()
    taken = {name.casefold() for name in used}
    profile = _weighted_name_profile(country_profile, region_name=region_name, rng=randomizer)

    def claim(candidate: str) -> str | None:
        normalized = " ".join(candidate.split())
        if not normalized:
            return None
        folded = normalized.casefold()
        if folded in taken:
            return None
        taken.add(folded)
        used.add(normalized)
        return normalized

    def claim_pair(given_name: str, surname: str) -> str | None:
        if given_name.strip().casefold() == surname.strip().casefold():
            return None
        return claim(f"{given_name} {surname}")

    for _ in range(50):
        surname = forced_surname or randomizer.choice(profile.surnames)
        candidate = claim_pair(randomizer.choice(profile.given_names), surname)
        if candidate is not None:
            return profile, candidate

    given_names = list(profile.given_names)
    surnames = [forced_surname] if forced_surname else list(profile.surnames)
    randomizer.shuffle(given_names)
    randomizer.shuffle(surnames)
    for given_name in given_names:
        for surname in surnames:
            candidate = claim_pair(given_name, surname)
            if candidate is not None:
                return profile, candidate

    surname = forced_surname or randomizer.choice(profile.surnames)
    candidate = f"{randomizer.choice(profile.given_names)} {surname} {randomizer.randint(2, 99)}"
    used.add(candidate)
    return profile, candidate


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
    "CD": CountryNamingProfile(
        country_code="CD",
        default_region="Kinshasa",
        default_city="Kinshasa",
        urbanicity="urban",
        region_profile_weights={
            "kinshasa": (
                ("kongo_christian", 0.30),
                ("luba_christian", 0.22),
                ("ngala_christian", 0.20),
                ("mongo_christian", 0.16),
                ("swahili_east_christian", 0.12),
            ),
            "katanga": (("swahili_east_christian", 0.55), ("luba_christian", 0.45)),
            "default": (
                ("kongo_christian", 0.25),
                ("luba_christian", 0.25),
                ("mongo_christian", 0.18),
                ("swahili_east_christian", 0.17),
                ("ngala_christian", 0.15),
            ),
        },
        profiles={
            "kongo_christian": NameProfile(
                key="kongo_christian",
                ethnolinguistic_profile="kongo",
                religion_naming_pattern="christian",
                given_names=("Gael", "Christian", "Glody", "Cedric", "Merveille", "Junior", "Chancel", "Yannick"),
                surnames=("Mbemba", "Bakambu", "Nkounkou", "Matumona", "Luyindama", "Mavuba", "Nzuzi", "Makaba"),
            ),
            "luba_christian": NameProfile(
                key="luba_christian",
                ethnolinguistic_profile="luba",
                religion_naming_pattern="christian",
                given_names=("Dieumerci", "Jonathan", "Joel", "Arsene", "Firmin", "Distel", "Ricky", "Elia"),
                surnames=("Mbokani", "Kabananga", "Tshibola", "Kalulu", "Mukendi", "Ilunga", "Kazadi", "Tshimanga"),
            ),
            "mongo_christian": NameProfile(
                key="mongo_christian",
                ethnolinguistic_profile="mongo",
                religion_naming_pattern="christian",
                given_names=("Tresor", "Marcel", "Herve", "Padou", "Benik", "Aaron", "Wilfried", "Chadrac"),
                surnames=("Mputu", "Bofandi", "Lomalisa", "Bompunga", "Likonza", "Botaka", "Lokwa", "Ekofo"),
            ),
            "swahili_east_christian": NameProfile(
                key="swahili_east_christian",
                ethnolinguistic_profile="swahili_congolese",
                religion_naming_pattern="christian",
                given_names=("Jacques", "Elie", "Pascal", "Issa", "Patou", "Rene", "Gedeon", "Cedrick"),
                surnames=("Kasongo", "Mutombo", "Banza", "Mwepu", "Kalonji", "Lwamba", "Ngandu", "Yav"),
            ),
            "ngala_christian": NameProfile(
                key="ngala_christian",
                ethnolinguistic_profile="ngala",
                religion_naming_pattern="christian",
                given_names=("Neeskens", "Paul", "Cedric", "Glody", "Junior", "Yannick", "Fabrice", "Dodi"),
                surnames=("Bokila", "Lema", "Mabidi", "Ngonga", "Bongonda", "Limbombe", "Mokonzi", "Litanda"),
            ),
        },
    ),
    "GH": CountryNamingProfile(
        country_code="GH",
        default_region="Greater Accra",
        default_city="Accra",
        urbanicity="urban",
        region_profile_weights={
            "greater accra": (
                ("akan_christian", 0.42),
                ("ga_dangme_christian", 0.24),
                ("ewe_christian", 0.16),
                ("mole_dagbani_muslim", 0.12),
                ("frafra_christian", 0.06),
            ),
            "ashanti": (("akan_christian", 0.88), ("mole_dagbani_muslim", 0.12)),
            "volta": (("ewe_christian", 0.90), ("akan_christian", 0.10)),
            "northern": (("mole_dagbani_muslim", 0.80), ("frafra_christian", 0.20)),
            "default": (
                ("akan_christian", 0.50),
                ("ewe_christian", 0.15),
                ("ga_dangme_christian", 0.13),
                ("mole_dagbani_muslim", 0.15),
                ("frafra_christian", 0.07),
            ),
        },
        profiles={
            "akan_christian": NameProfile(
                key="akan_christian",
                ethnolinguistic_profile="akan",
                religion_naming_pattern="christian",
                given_names=("Kwame", "Kojo", "Yaw", "Kwaku", "Kofi", "Emmanuel", "Samuel", "Michael"),
                surnames=("Mensah", "Owusu", "Boateng", "Asante", "Ofori", "Acheampong", "Sarpong", "Agyeman"),
            ),
            "ewe_christian": NameProfile(
                key="ewe_christian",
                ethnolinguistic_profile="ewe",
                religion_naming_pattern="christian",
                given_names=("Elikem", "Selorm", "Dela", "Mawuli", "Edem", "Senanu", "Worlanyo", "Kobla"),
                surnames=("Agbeko", "Dzakpasu", "Akakpo", "Gakpe", "Tornyenu", "Avornyo", "Atsu", "Nyamekye"),
            ),
            "ga_dangme_christian": NameProfile(
                key="ga_dangme_christian",
                ethnolinguistic_profile="ga_dangme",
                religion_naming_pattern="christian",
                given_names=("Nii", "Tetteh", "Okai", "Ayi", "Lartey", "Quaye", "Nelson", "Joseph"),
                surnames=("Tetteh", "Quaye", "Lartey", "Adjei", "Ankrah", "Lamptey", "Addo", "Nortey"),
            ),
            "mole_dagbani_muslim": NameProfile(
                key="mole_dagbani_muslim",
                ethnolinguistic_profile="mole_dagbani",
                religion_naming_pattern="muslim",
                given_names=("Abdul", "Mohammed", "Iddrisu", "Fatawu", "Rashid", "Yakubu", "Sadiq", "Alhassan"),
                surnames=("Issahaku", "Iddrisu", "Fuseini", "Yakubu", "Abubakar", "Salifu", "Mahama", "Mohammed"),
            ),
            "frafra_christian": NameProfile(
                key="frafra_christian",
                ethnolinguistic_profile="frafra_gurune",
                religion_naming_pattern="christian",
                given_names=("Abraham", "Azumah", "Anaba", "Akolgo", "Atia", "Asaah", "Aweko", "Anamoo"),
                surnames=("Atibilla", "Akolgo", "Anaba", "Azure", "Anamoo", "Apambila", "Aweko", "Atinga"),
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

_NAMING_PROFILES.update(
    {
        "SN": _country_profile(
            country_code="SN",
            default_region="Dakar",
            default_city="Dakar",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="wolof_muslim",
                    ethnolinguistic_profile="wolof",
                    religion_naming_pattern="muslim",
                    given_names=("Cheikh", "Moussa", "Pape", "Ousmane", "Ibrahima", "Modou", "Assane", "Mamadou"),
                    surnames=("Diop", "Ndiaye", "Fall", "Gueye", "Mbaye", "Seck", "Sarr", "Diouf"),
                ),
                _name_profile(
                    key="halpulaar_muslim",
                    ethnolinguistic_profile="halpulaar_fulani",
                    religion_naming_pattern="muslim",
                    given_names=("Amadou", "Aliou", "Saliou", "Abdoulaye", "Thierno", "Samba", "Mamadou", "Boubacar"),
                    surnames=("Ba", "Sow", "Diallo", "Barry", "Ka", "Sall", "Wane", "Tall"),
                ),
                _name_profile(
                    key="serer_mixed",
                    ethnolinguistic_profile="serer",
                    religion_naming_pattern="mixed",
                    given_names=("Augustin", "Pierre", "El Hadji", "Ferdinand", "Cheikh", "Joseph", "Habib", "Leopold"),
                    surnames=("Faye", "Sene", "Tine", "Ndour", "Diouf", "Senghor", "Ngom", "Sarr"),
                ),
                _name_profile(
                    key="mandinka_muslim",
                    ethnolinguistic_profile="mandinka",
                    religion_naming_pattern="muslim",
                    given_names=("Lamine", "Sidy", "Bouba", "Karim", "Moussa", "Yoro", "Sekou", "Fode"),
                    surnames=("Cissokho", "Diaby", "Camara", "Sane", "Konate", "Dabo", "Souare", "Manga"),
                ),
                _name_profile(
                    key="jola_mixed",
                    ethnolinguistic_profile="jola",
                    religion_naming_pattern="mixed",
                    given_names=("Robert", "Landing", "Malang", "Sekou", "Boubacar", "Yancouba", "Famara", "Ousseynou"),
                    surnames=("Diatta", "Sambou", "Coly", "Badji", "Manga", "Diedhiou", "Bassene", "Goudiaby"),
                ),
            ),
            region_profile_weights={
                "casamance": (("jola_mixed", 0.55), ("mandinka_muslim", 0.30), ("wolof_muslim", 0.15)),
                "default": (
                    ("wolof_muslim", 0.45),
                    ("halpulaar_muslim", 0.25),
                    ("serer_mixed", 0.18),
                    ("mandinka_muslim", 0.07),
                    ("jola_mixed", 0.05),
                ),
            },
        ),
        "CI": _country_profile(
            country_code="CI",
            default_region="Abidjan",
            default_city="Abidjan",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="akan_baoule_christian",
                    ethnolinguistic_profile="akan_baoule",
                    religion_naming_pattern="christian",
                    given_names=("Christian", "Serge", "Jean", "Wilfried", "Maxwell", "Yao", "Kouame", "Aristide"),
                    surnames=("Kouame", "Konan", "Yao", "Kouassi", "N'Guessan", "Brou", "Koffi", "Aka"),
                ),
                _name_profile(
                    key="mande_dioula_muslim",
                    ethnolinguistic_profile="mande_dioula",
                    religion_naming_pattern="muslim",
                    given_names=("Ibrahim", "Seydou", "Lassina", "Bakary", "Adama", "Souleymane", "Moussa", "Sekou"),
                    surnames=("Traore", "Kone", "Coulibaly", "Cisse", "Diomande", "Bamba", "Toure", "Doumbia"),
                ),
                _name_profile(
                    key="krou_bete_christian",
                    ethnolinguistic_profile="krou_bete",
                    religion_naming_pattern="christian",
                    given_names=("Gervais", "Cedric", "Roland", "Emmanuel", "Olivier", "Herve", "Wilfrid", "Serge"),
                    surnames=("Gnagne", "Zahoui", "Digbeu", "Tahi", "Zoro", "Dago", "Sery", "Gbagbo"),
                ),
                _name_profile(
                    key="gur_senufo_muslim",
                    ethnolinguistic_profile="gur_senufo",
                    religion_naming_pattern="muslim",
                    given_names=("Soumaila", "Ardjouma", "Yacouba", "Drissa", "Ousmane", "Lacina", "Issouf", "Hamed"),
                    surnames=("Soro", "Silue", "Ouattara", "Yeo", "Tuo", "Dosso", "Kone", "Coulibaly"),
                ),
                _name_profile(
                    key="lagoon_ebrie_christian",
                    ethnolinguistic_profile="lagoon_ebrie",
                    religion_naming_pattern="christian",
                    given_names=("Desire", "Eric", "Patrick", "Hyacinthe", "Armand", "Gerard", "Franck", "Constant"),
                    surnames=("Anoma", "Assi", "Akre", "Boni", "Ehui", "Tanoh", "Adje", "Loukou"),
                ),
            ),
            region_profile_weights={
                "nord": (("mande_dioula_muslim", 0.52), ("gur_senufo_muslim", 0.48)),
                "default": (
                    ("akan_baoule_christian", 0.30),
                    ("mande_dioula_muslim", 0.25),
                    ("krou_bete_christian", 0.18),
                    ("gur_senufo_muslim", 0.15),
                    ("lagoon_ebrie_christian", 0.12),
                ),
            },
        ),
        "CM": _country_profile(
            country_code="CM",
            default_region="Centre",
            default_city="Yaounde",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="beti_bantu_christian",
                    ethnolinguistic_profile="beti_bantu",
                    religion_naming_pattern="christian",
                    given_names=("Vincent", "Joel", "Landry", "Stephane", "Yannick", "Arnaud", "Patrick", "Fabrice"),
                    surnames=("Onana", "Mbarga", "Ondoa", "Ngoa", "Atangana", "Owona", "Mvondo", "Essomba"),
                ),
                _name_profile(
                    key="bamileke_christian",
                    ethnolinguistic_profile="bamileke",
                    religion_naming_pattern="christian",
                    given_names=("Clinton", "Frank", "Boris", "Wilfried", "Georges", "Gaetan", "Junior", "Bryan"),
                    surnames=("Kamga", "Tchami", "Fotso", "Njoya", "Kemajou", "Takougang", "Nguemo", "Tchatchoua"),
                ),
                _name_profile(
                    key="fulani_muslim",
                    ethnolinguistic_profile="fulani",
                    religion_naming_pattern="muslim",
                    given_names=(
                        "Ibrahim",
                        "Aboubakar",
                        "Moussa",
                        "Oumarou",
                        "Hamidou",
                        "Bachirou",
                        "Souleymanou",
                        "Nourou",
                    ),
                    surnames=("Bello", "Hamadou", "Baba", "Aminou", "Saidou", "Yaya", "Aliou", "Moustapha"),
                ),
                _name_profile(
                    key="anglophone_christian",
                    ethnolinguistic_profile="grassfields_anglophone",
                    religion_naming_pattern="christian",
                    given_names=("Christian", "Collins", "Tabe", "Ako", "Ebai", "Nkeng", "Fru", "Ndip"),
                    surnames=("Tabe", "Eyong", "Ashu", "Ngwa", "Fominyen", "Ndumu", "Atabong", "Besong"),
                ),
                _name_profile(
                    key="sahelian_muslim",
                    ethnolinguistic_profile="kanuri_shuwa",
                    religion_naming_pattern="muslim",
                    given_names=("Modibo", "Adama", "Hamadou", "Goni", "Mahamat", "Issa", "Bakari", "Saleh"),
                    surnames=("Abba", "Mahamat", "Saleh", "Goni", "Adam", "Ousman", "Brahim", "Djibrilla"),
                ),
            ),
            region_profile_weights={
                "ouest": (("bamileke_christian", 0.85), ("beti_bantu_christian", 0.15)),
                "nord": (("fulani_muslim", 0.60), ("sahelian_muslim", 0.40)),
                "default": (
                    ("beti_bantu_christian", 0.32),
                    ("bamileke_christian", 0.28),
                    ("fulani_muslim", 0.18),
                    ("anglophone_christian", 0.12),
                    ("sahelian_muslim", 0.10),
                ),
            },
        ),
        "KE": _country_profile(
            country_code="KE",
            default_region="Nairobi",
            default_city="Nairobi",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="kikuyu_christian",
                    ethnolinguistic_profile="kikuyu",
                    religion_naming_pattern="christian",
                    given_names=("Brian", "Kevin", "Dennis", "Samuel", "John", "Peter", "Anthony", "Eric"),
                    surnames=("Kamau", "Mwangi", "Njoroge", "Kariuki", "Maina", "Kimani", "Macharia", "Githinji"),
                ),
                _name_profile(
                    key="luo_christian",
                    ethnolinguistic_profile="luo",
                    religion_naming_pattern="christian",
                    given_names=("Collins", "Victor", "Lawrence", "Stephen", "Edwin", "George", "Brian", "Maurice"),
                    surnames=("Otieno", "Odhiambo", "Ouma", "Onyango", "Owino", "Ochieng", "Odera", "Omondi"),
                ),
                _name_profile(
                    key="luhya_christian",
                    ethnolinguistic_profile="luhya",
                    religion_naming_pattern="christian",
                    given_names=("Michael", "Wycliffe", "Emmanuel", "Brian", "Allan", "Vincent", "Duncan", "Boniface"),
                    surnames=("Wanyama", "Wekesa", "Simiyu", "Barasa", "Wafula", "Shikuku", "Lusala", "Khaemba"),
                ),
                _name_profile(
                    key="kalenjin_christian",
                    ethnolinguistic_profile="kalenjin",
                    religion_naming_pattern="christian",
                    given_names=("Wilson", "Brian", "Cornelius", "Geoffrey", "Eliud", "Hillary", "Vincent", "Kiprop"),
                    surnames=("Kiprono", "Kipchirchir", "Kibet", "Rotich", "Cheruiyot", "Kosgei", "Kiplagat", "Bett"),
                ),
                _name_profile(
                    key="kamba_christian",
                    ethnolinguistic_profile="kamba",
                    religion_naming_pattern="christian",
                    given_names=("Joseph", "David", "Patrick", "Benard", "Dominic", "Onesmus", "Mutua", "Musyoka"),
                    surnames=("Mutua", "Musyoka", "Kioko", "Muthama", "Nzioka", "Mulwa", "Kilonzo", "Mutiso"),
                ),
                _name_profile(
                    key="swahili_muslim",
                    ethnolinguistic_profile="swahili",
                    religion_naming_pattern="muslim",
                    given_names=("Ali", "Hamisi", "Juma", "Bakari", "Said", "Rashid", "Omari", "Salim"),
                    surnames=("Athman", "Bakari", "Juma", "Mohammed", "Said", "Abdalla", "Hassan", "Omar"),
                ),
                _name_profile(
                    key="somali_muslim",
                    ethnolinguistic_profile="somali",
                    religion_naming_pattern="muslim",
                    given_names=("Abdi", "Abdullahi", "Mohamed", "Ahmed", "Hassan", "Yusuf", "Omar", "Ibrahim"),
                    surnames=("Farah", "Hassan", "Mohamed", "Hussein", "Aden", "Noor", "Ali", "Abdi"),
                ),
            ),
            region_profile_weights={
                "coast": (("swahili_muslim", 0.62), ("somali_muslim", 0.10), ("kikuyu_christian", 0.28)),
                "rift valley": (("kalenjin_christian", 0.78), ("kikuyu_christian", 0.22)),
                "north eastern": (("somali_muslim", 0.92), ("swahili_muslim", 0.08)),
                "default": (
                    ("kikuyu_christian", 0.22),
                    ("luo_christian", 0.18),
                    ("luhya_christian", 0.16),
                    ("kalenjin_christian", 0.16),
                    ("kamba_christian", 0.10),
                    ("swahili_muslim", 0.10),
                    ("somali_muslim", 0.08),
                ),
            },
        ),
        "ET": _country_profile(
            country_code="ET",
            default_region="Addis Ababa",
            default_city="Addis Ababa",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="amhara_orthodox",
                    ethnolinguistic_profile="amhara",
                    religion_naming_pattern="ethiopian_orthodox",
                    given_names=("Abebe", "Dawit", "Yohannes", "Tewodros", "Getachew", "Solomon", "Mulugeta", "Henok"),
                    surnames=("Tesfaye", "Bekele", "Girma", "Haile", "Tadesse", "Mengistu", "Assefa", "Wolde"),
                ),
                _name_profile(
                    key="oromo",
                    ethnolinguistic_profile="oromo",
                    religion_naming_pattern="mixed",
                    given_names=("Tolosa", "Diraba", "Caala", "Boruu", "Gammachuu", "Dasta", "Gadaa", "Lelisa"),
                    surnames=("Roba", "Gudina", "Hambisa", "Boru", "Tola", "Galata", "Diba", "Jaarraa"),
                ),
                _name_profile(
                    key="tigray_orthodox",
                    ethnolinguistic_profile="tigrinya",
                    religion_naming_pattern="ethiopian_orthodox",
                    given_names=("Hagos", "Gebre", "Tesfay", "Berhe", "Kahsay", "Aregawi", "Hailay", "Goitom"),
                    surnames=("Gebremariam", "Tesfay", "Berhe", "Hagos", "Weldu", "Araya", "Kidane", "Gebretsadik"),
                ),
                _name_profile(
                    key="somali_muslim",
                    ethnolinguistic_profile="somali",
                    religion_naming_pattern="muslim",
                    given_names=("Abdi", "Mohamed", "Ahmed", "Hassan", "Yusuf", "Omar", "Ibrahim", "Abdullahi"),
                    surnames=("Farah", "Hassan", "Mohamed", "Hussein", "Aden", "Noor", "Ali", "Abdi"),
                ),
                _name_profile(
                    key="sidama_christian",
                    ethnolinguistic_profile="sidama",
                    religion_naming_pattern="christian",
                    given_names=("Markos", "Yonas", "Abel", "Biniam", "Nahom", "Eyob", "Samuel", "Dagne"),
                    surnames=("Hankamo", "Lamiso", "Garsamo", "Daka", "Bona", "Soreta", "Dilbato", "Hambela"),
                ),
                _name_profile(
                    key="gurage",
                    ethnolinguistic_profile="gurage",
                    religion_naming_pattern="mixed",
                    given_names=("Bereket", "Ermias", "Robel", "Fitsum", "Yared", "Mikias", "Natnael", "Biruk"),
                    surnames=("Mamo", "Abate", "Dejene", "Eshetu", "Belay", "Worku", "Negash", "Wolde"),
                ),
            ),
            region_profile_weights={
                "oromia": (("oromo", 0.80), ("amhara_orthodox", 0.20)),
                "tigray": (("tigray_orthodox", 0.92), ("amhara_orthodox", 0.08)),
                "somali": (("somali_muslim", 0.94), ("oromo", 0.06)),
                "default": (
                    ("amhara_orthodox", 0.30),
                    ("oromo", 0.34),
                    ("tigray_orthodox", 0.12),
                    ("somali_muslim", 0.10),
                    ("sidama_christian", 0.08),
                    ("gurage", 0.06),
                ),
            },
        ),
        "EG": _country_profile(
            country_code="EG",
            default_region="Cairo",
            default_city="Cairo",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="egyptian_arabic",
                    ethnolinguistic_profile="egyptian_arabic",
                    religion_naming_pattern="muslim_majority",
                    given_names=("Mohamed", "Ahmed", "Omar", "Mostafa", "Mahmoud", "Youssef", "Karim"),
                    surnames=("Salah", "Hegazy", "Elneny", "Ashour", "Hamdy", "Zaki"),
                ),
            ),
        ),
        "ZA": _country_profile(
            country_code="ZA",
            default_region="Gauteng",
            default_city="Johannesburg",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="zulu_christian",
                    ethnolinguistic_profile="nguni_zulu",
                    religion_naming_pattern="christian",
                    given_names=(
                        "Sphesihle",
                        "Siyabonga",
                        "Bongani",
                        "Nkosinathi",
                        "Sabelo",
                        "Lwandle",
                        "Andile",
                        "Mxolisi",
                    ),
                    surnames=("Zungu", "Khumalo", "Ndlovu", "Mthembu", "Dlamini", "Nkosi", "Zwane", "Mabaso"),
                ),
                _name_profile(
                    key="xhosa_christian",
                    ethnolinguistic_profile="nguni_xhosa",
                    religion_naming_pattern="christian",
                    given_names=("Lukhanyo", "Athenkosi", "Anele", "Sihle", "Lundi", "Sibusiso", "Avela", "Khanya"),
                    surnames=("Dyantyi", "Mgijima", "Sigcawu", "Nyezi", "Mvula", "Qwabe", "Bongo", "Tshabalala"),
                ),
                _name_profile(
                    key="sotho_tswana_christian",
                    ethnolinguistic_profile="sotho_tswana",
                    religion_naming_pattern="christian",
                    given_names=(
                        "Katlego",
                        "Thabo",
                        "Karabo",
                        "Tshepo",
                        "Kagiso",
                        "Oratile",
                        "Reabetswe",
                        "Lehlohonolo",
                    ),
                    surnames=("Mokoena", "Molefe", "Modise", "Moloi", "Tau", "Phiri", "Lekoela", "Sefolosha"),
                ),
                _name_profile(
                    key="afrikaner",
                    ethnolinguistic_profile="afrikaner",
                    religion_naming_pattern="christian",
                    given_names=("Ruben", "Pieter", "Johan", "Dewald", "Stefan", "Cobus", "Hendrik", "Riaan"),
                    surnames=("van der Merwe", "Botha", "Pretorius", "Coetzee", "van Wyk", "Venter", "Steyn", "Nel"),
                ),
                _name_profile(
                    key="english_sa",
                    ethnolinguistic_profile="english_south_african",
                    religion_naming_pattern="christian",
                    given_names=("Bradley", "Keagan", "Ryan", "Luke", "Travis", "Dean", "Grant", "Cameron"),
                    surnames=("Smith", "Williams", "Roberts", "Johnson", "Brown", "Walters", "Pearce", "Clarke"),
                ),
                _name_profile(
                    key="cape_coloured_christian",
                    ethnolinguistic_profile="cape_coloured",
                    religion_naming_pattern="christian",
                    given_names=("Keenan", "Chad", "Devon", "Caleb", "Nathan", "Ethan", "Riako", "Dillon"),
                    surnames=("Adams", "Hendricks", "September", "April", "Booysen", "Jacobs", "Februarie", "Cloete"),
                ),
                _name_profile(
                    key="cape_muslim",
                    ethnolinguistic_profile="cape_malay",
                    religion_naming_pattern="muslim",
                    given_names=("Yaseen", "Tariq", "Riyaad", "Zaid", "Imraan", "Faiz", "Ridwaan", "Nabeel"),
                    surnames=("Davids", "Salie", "Abrahams", "Ismail", "Behardien", "Parker", "Manjra", "Achmat"),
                ),
                _name_profile(
                    key="indian_sa",
                    ethnolinguistic_profile="indian_south_african",
                    religion_naming_pattern="hindu",
                    given_names=("Kavish", "Prashant", "Dhiren", "Yuvraj", "Keshav", "Sashin", "Avir", "Rohan"),
                    surnames=("Naidoo", "Govender", "Pillay", "Reddy", "Moodley", "Maharaj", "Singh", "Naicker"),
                ),
            ),
            region_profile_weights={
                "kwazulu-natal": (("zulu_christian", 0.72), ("indian_sa", 0.18), ("english_sa", 0.10)),
                "western cape": (
                    ("cape_coloured_christian", 0.40),
                    ("xhosa_christian", 0.26),
                    ("afrikaner", 0.16),
                    ("english_sa", 0.10),
                    ("cape_muslim", 0.08),
                ),
                "eastern cape": (("xhosa_christian", 0.86), ("afrikaner", 0.14)),
                "default": (
                    ("zulu_christian", 0.30),
                    ("xhosa_christian", 0.18),
                    ("sotho_tswana_christian", 0.22),
                    ("afrikaner", 0.09),
                    ("english_sa", 0.06),
                    ("cape_coloured_christian", 0.07),
                    ("cape_muslim", 0.03),
                    ("indian_sa", 0.05),
                ),
            },
        ),
        "TD": _country_profile(
            country_code="TD",
            default_region="N'Djamena",
            default_city="N'Djamena",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="sahelian_muslim",
                    ethnolinguistic_profile="chadian_arab_sahelian",
                    religion_naming_pattern="muslim",
                    given_names=("Mahamat", "Ahmat", "Abdoulaye", "Hassan", "Idriss", "Brahim", "Oumar", "Souleyman"),
                    surnames=("Mahamat", "Idriss", "Hassan", "Ahmat", "Abakar", "Saleh", "Nour", "Djimet"),
                ),
                _name_profile(
                    key="sara_christian",
                    ethnolinguistic_profile="sara",
                    religion_naming_pattern="christian",
                    given_names=(
                        "Nodjimbaye",
                        "Djimet",
                        "Ronelngar",
                        "Doumngar",
                        "Ngardoum",
                        "Beassoum",
                        "Allahonde",
                        "Bediang",
                    ),
                    surnames=(
                        "Mbaiam",
                        "Ngardoum",
                        "Nodjingar",
                        "Beassoum",
                        "Djekouri",
                        "Tolde",
                        "Madjadoum",
                        "Reoulengar",
                    ),
                ),
            ),
            region_profile_weights={
                "default": (("sahelian_muslim", 0.55), ("sara_christian", 0.45)),
            },
        ),
        "BJ": _country_profile(
            country_code="BJ",
            default_region="Littoral",
            default_city="Cotonou",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="fon_christian",
                    ethnolinguistic_profile="fon",
                    religion_naming_pattern="christian",
                    given_names=("Sessi", "Cyrille", "Stephane", "Jodel", "Steve", "Romuald", "Cedric", "Marcel"),
                    surnames=(
                        "Dossou",
                        "Houngbedji",
                        "Sessegnon",
                        "Hounkpatin",
                        "Adjovi",
                        "Tossou",
                        "Gbaguidi",
                        "Aholou",
                    ),
                ),
                _name_profile(
                    key="yoruba_nagot_muslim",
                    ethnolinguistic_profile="yoruba_nagot",
                    religion_naming_pattern="muslim",
                    given_names=("Razak", "Wakil", "Abou", "Moukaila", "Saliou", "Faridou", "Imourane", "Toura"),
                    surnames=("Tijani", "Yessoufou", "Bashiru", "Alabi", "Aminou", "Sanni", "Ola", "Ogou"),
                ),
                _name_profile(
                    key="bariba_muslim",
                    ethnolinguistic_profile="bariba",
                    religion_naming_pattern="muslim",
                    given_names=("Issa", "Adamou", "Orou", "Bio", "Sabi", "Yacoubou", "Worou", "Boni"),
                    surnames=("Bio", "Orou", "Sabi", "Yarou", "Gounou", "Tamou", "Sero", "Worou"),
                ),
            ),
            region_profile_weights={
                "borgou": (("bariba_muslim", 0.70), ("yoruba_nagot_muslim", 0.30)),
                "default": (("fon_christian", 0.50), ("yoruba_nagot_muslim", 0.25), ("bariba_muslim", 0.25)),
            },
        ),
        "ML": _country_profile(
            country_code="ML",
            default_region="Bamako",
            default_city="Bamako",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="bambara_mande_muslim",
                    ethnolinguistic_profile="bambara_mande",
                    religion_naming_pattern="muslim",
                    given_names=("Moussa", "Modibo", "Adama", "Cheick", "Bakary", "Drissa", "Mahamadou", "Lassana"),
                    surnames=("Traore", "Keita", "Coulibaly", "Diarra", "Sidibe", "Doumbia", "Dembele", "Sangare"),
                ),
                _name_profile(
                    key="fulani_songhai_muslim",
                    ethnolinguistic_profile="fulani_songhai",
                    religion_naming_pattern="muslim",
                    given_names=("Amadou", "Hamadoun", "Oumar", "Aliou", "Bocary", "Boubacar", "Yacouba", "Souleymane"),
                    surnames=("Diallo", "Maiga", "Toure", "Cisse", "Tall", "Ba", "Dicko", "Haidara"),
                ),
            ),
            region_profile_weights={
                "default": (("bambara_mande_muslim", 0.70), ("fulani_songhai_muslim", 0.30)),
            },
        ),
        "TZ": _country_profile(
            country_code="TZ",
            default_region="Dar es Salaam",
            default_city="Dar es Salaam",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="bantu_christian",
                    ethnolinguistic_profile="tanzanian_bantu",
                    religion_naming_pattern="christian",
                    given_names=("Mbwana", "Baraka", "Emmanuel", "Thomas", "John", "Simon", "Erasto", "Deogratias"),
                    surnames=("Samatta", "Mwakalebela", "Kapombe", "Lyimo", "Mushi", "Kessy", "Mwita", "Massawe"),
                ),
                _name_profile(
                    key="swahili_muslim",
                    ethnolinguistic_profile="swahili",
                    religion_naming_pattern="muslim",
                    given_names=("Hassan", "Juma", "Said", "Rashid", "Salim", "Hamisi", "Abdallah", "Ali"),
                    surnames=("Athumani", "Juma", "Said", "Mohammed", "Rashid", "Hassan", "Abdallah", "Suleiman"),
                ),
            ),
            region_profile_weights={
                "zanzibar": (("swahili_muslim", 0.92), ("bantu_christian", 0.08)),
                "default": (("bantu_christian", 0.65), ("swahili_muslim", 0.35)),
            },
        ),
        "ZW": _country_profile(
            country_code="ZW",
            default_region="Harare",
            default_city="Harare",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="shona_christian",
                    ethnolinguistic_profile="shona",
                    religion_naming_pattern="christian",
                    given_names=(
                        "Tinashe",
                        "Tatenda",
                        "Tafadzwa",
                        "Munashe",
                        "Takudzwa",
                        "Farai",
                        "Blessing",
                        "Tanaka",
                    ),
                    surnames=(
                        "Marufu",
                        "Mapfumo",
                        "Chimwanda",
                        "Nyandoro",
                        "Mutasa",
                        "Chigumba",
                        "Madzongwe",
                        "Mukombe",
                    ),
                ),
                _name_profile(
                    key="ndebele_christian",
                    ethnolinguistic_profile="ndebele",
                    religion_naming_pattern="christian",
                    given_names=(
                        "Nkosilathi",
                        "Bongani",
                        "Sibusiso",
                        "Mthokozisi",
                        "Khumbulani",
                        "Mqondisi",
                        "Nkosana",
                        "Thulani",
                    ),
                    surnames=("Ndlovu", "Moyo", "Sibanda", "Ncube", "Nyathi", "Dube", "Mpofu", "Nkomo"),
                ),
            ),
            region_profile_weights={
                "bulawayo": (("ndebele_christian", 0.80), ("shona_christian", 0.20)),
                "default": (("shona_christian", 0.80), ("ndebele_christian", 0.20)),
            },
        ),
        "BF": _country_profile(
            country_code="BF",
            default_region="Centre",
            default_city="Ouagadougou",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="mossi_mixed",
                    ethnolinguistic_profile="mossi",
                    religion_naming_pattern="mixed",
                    given_names=("Abdoulaye", "Issa", "Adama", "Boukary", "Rasmane", "Wendkuni", "Salif", "Idrissa"),
                    surnames=("Ouedraogo", "Compaore", "Kabore", "Sawadogo", "Zongo", "Nikiema", "Tapsoba", "Ilboudo"),
                ),
                _name_profile(
                    key="mande_muslim",
                    ethnolinguistic_profile="mande",
                    religion_naming_pattern="muslim",
                    given_names=("Bakary", "Moussa", "Lassina", "Souleymane", "Drissa", "Seydou", "Ibrahim", "Yacouba"),
                    surnames=("Traore", "Kone", "Sanogo", "Coulibaly", "Diallo", "Cisse", "Bamba", "Diakite"),
                ),
            ),
            region_profile_weights={
                "default": (("mossi_mixed", 0.70), ("mande_muslim", 0.30)),
            },
        ),
        "TG": _country_profile(
            country_code="TG",
            default_region="Maritime",
            default_city="Lome",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="ewe_christian",
                    ethnolinguistic_profile="ewe",
                    religion_naming_pattern="christian",
                    given_names=("Kossi", "Komlan", "Yao", "Koffi", "Mawuli", "Sena", "Elom", "Dodzi"),
                    surnames=("Agbessi", "Dogbe", "Adjavon", "Akakpo", "Amegah", "Lawson", "Apaloo", "Gakpe"),
                ),
                _name_profile(
                    key="kabye_mixed",
                    ethnolinguistic_profile="kabye",
                    religion_naming_pattern="mixed",
                    given_names=("Essohouna", "Komi", "Pyabalo", "Damba", "Tchalla", "Nadjombe", "Yendoube", "Atouli"),
                    surnames=("Tchangai", "Pyabalo", "Tchalla", "Nadjombe", "Atouli", "Lamboni", "Kombate", "Douti"),
                ),
                _name_profile(
                    key="muslim_north",
                    ethnolinguistic_profile="togolese_muslim",
                    religion_naming_pattern="muslim",
                    given_names=("Ali", "Rachid", "Issa", "Aziz", "Faouzi", "Moustapha", "Karim", "Ibrahim"),
                    surnames=("Ouro", "Tchagnao", "Salou", "Abalo", "Bukari", "Issah", "Boukari", "Alassani"),
                ),
            ),
            region_profile_weights={
                "kara": (("kabye_mixed", 0.65), ("muslim_north", 0.35)),
                "default": (("ewe_christian", 0.55), ("kabye_mixed", 0.30), ("muslim_north", 0.15)),
            },
        ),
        "UG": _country_profile(
            country_code="UG",
            default_region="Central",
            default_city="Kampala",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="baganda_bantu_christian",
                    ethnolinguistic_profile="baganda_bantu",
                    religion_naming_pattern="christian",
                    given_names=("Allan", "Brian", "Joseph", "Geoffrey", "Emmanuel", "Ronald", "Denis", "Isaac"),
                    surnames=(
                        "Lukwago",
                        "Sserwadda",
                        "Kiggundu",
                        "Ssemujju",
                        "Mukasa",
                        "Kaweesa",
                        "Nsubuga",
                        "Walusimbi",
                    ),
                ),
                _name_profile(
                    key="nilotic_christian",
                    ethnolinguistic_profile="nilotic_acholi_langi",
                    religion_naming_pattern="christian",
                    given_names=("Okello", "Otim", "Ojara", "Komakech", "Onyango", "Opio", "Ochan", "Lokong"),
                    surnames=("Okello", "Otim", "Ojok", "Komakech", "Acaye", "Olum", "Odong", "Opiyo"),
                ),
                _name_profile(
                    key="muslim_ug",
                    ethnolinguistic_profile="ugandan_muslim",
                    religion_naming_pattern="muslim",
                    given_names=("Hassan", "Ibrahim", "Ramathan", "Yunus", "Shafik", "Mansoor", "Hamza", "Muzamir"),
                    surnames=("Ssentamu", "Lubega", "Kafeero", "Ssali", "Mubiru", "Mwanje", "Kasozi", "Nsereko"),
                ),
            ),
            region_profile_weights={
                "northern": (("nilotic_christian", 0.85), ("muslim_ug", 0.15)),
                "default": (
                    ("baganda_bantu_christian", 0.55),
                    ("nilotic_christian", 0.30),
                    ("muslim_ug", 0.15),
                ),
            },
        ),
        "ZM": _country_profile(
            country_code="ZM",
            default_region="Lusaka",
            default_city="Lusaka",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="bemba_christian",
                    ethnolinguistic_profile="bemba",
                    religion_naming_pattern="christian",
                    given_names=("Chola", "Mwamba", "Mulenga", "Bwalya", "Chanda", "Kunda", "Mukuka", "Aubrey"),
                    surnames=("Mulenga", "Mwamba", "Bwalya", "Chanda", "Kunda", "Mukuka", "Musonda", "Kabwe"),
                ),
                _name_profile(
                    key="tonga_nyanja_christian",
                    ethnolinguistic_profile="tonga_nyanja",
                    religion_naming_pattern="christian",
                    given_names=("Given", "Brian", "Emmanuel", "Patson", "Fashion", "Justin", "Kennedy", "Enock"),
                    surnames=("Daka", "Phiri", "Banda", "Tembo", "Zulu", "Sakala", "Mwanza", "Lungu"),
                ),
            ),
            region_profile_weights={
                "default": (("bemba_christian", 0.55), ("tonga_nyanja_christian", 0.45)),
            },
        ),
        "AO": _country_profile(
            country_code="AO",
            default_region="Luanda",
            default_city="Luanda",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="lusophone_african",
                    ethnolinguistic_profile="lusophone_african",
                    religion_naming_pattern="christian_mixed",
                    given_names=("Jose", "Joao", "Manuel", "Nelson", "Paulo", "Domingos", "Carlos"),
                    surnames=("dos Santos", "Silva", "Mateus", "Fernandes", "Costa", "Pereira"),
                ),
            ),
        ),
        "AR": _country_profile(
            country_code="AR",
            default_region="Buenos Aires",
            default_city="Buenos Aires",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="rioplatense_spanish",
                    ethnolinguistic_profile="argentine_spanish",
                    religion_naming_pattern="mixed",
                    given_names=("Mateo", "Thiago", "Santiago", "Franco", "Tomas", "Benjamin"),
                    surnames=("Gonzalez", "Rodriguez", "Fernandez", "Lopez", "Perez", "Romero"),
                ),
            ),
        ),
        "FR": _country_profile(
            country_code="FR",
            default_region="Ile-de-France",
            default_city="Paris",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="french",
                    ethnolinguistic_profile="french",
                    religion_naming_pattern="secular_mixed",
                    given_names=("Lucas", "Nathan", "Theo", "Enzo", "Hugo", "Maxime"),
                    surnames=("Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Roux"),
                ),
            ),
        ),
        "DE": _country_profile(
            country_code="DE",
            default_region="Berlin",
            default_city="Berlin",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="german",
                    ethnolinguistic_profile="german",
                    religion_naming_pattern="secular_mixed",
                    given_names=("Lukas", "Jonas", "Leon", "Felix", "Max", "Tim"),
                    surnames=("Muller", "Schmidt", "Schneider", "Fischer", "Weber", "Wagner"),
                ),
            ),
        ),
        "IT": _country_profile(
            country_code="IT",
            default_region="Lombardy",
            default_city="Milan",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="italian",
                    ethnolinguistic_profile="italian",
                    religion_naming_pattern="mixed",
                    given_names=("Lorenzo", "Matteo", "Leonardo", "Andrea", "Riccardo", "Alessandro"),
                    surnames=("Rossi", "Russo", "Ferrari", "Esposito", "Romano", "Colombo"),
                ),
            ),
        ),
        "PT": _country_profile(
            country_code="PT",
            default_region="Lisbon",
            default_city="Lisbon",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="portuguese",
                    ethnolinguistic_profile="portuguese",
                    religion_naming_pattern="mixed",
                    given_names=("Joao", "Diogo", "Tiago", "Goncalo", "Andre", "Rafael"),
                    surnames=("Silva", "Santos", "Ferreira", "Pereira", "Costa", "Oliveira"),
                ),
            ),
        ),
        "GB": _country_profile(
            country_code="GB",
            default_region="Greater London",
            default_city="London",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="british",
                    ethnolinguistic_profile="british",
                    religion_naming_pattern="secular_mixed",
                    given_names=("Jack", "Oliver", "George", "Harry", "James", "Callum"),
                    surnames=("Smith", "Brown", "Taylor", "Wilson", "Davies", "Thompson"),
                ),
            ),
        ),
        "US": _country_profile(
            country_code="US",
            default_region="New York",
            default_city="New York",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="american_anglo",
                    ethnolinguistic_profile="american_anglo",
                    religion_naming_pattern="mixed",
                    given_names=("Aiden", "Noah", "Mason", "Liam", "Ethan", "Logan"),
                    surnames=("Johnson", "Williams", "Miller", "Davis", "Brown", "Wilson"),
                ),
                _name_profile(
                    key="american_hispanic",
                    ethnolinguistic_profile="american_hispanic",
                    religion_naming_pattern="mixed",
                    given_names=("Jose", "Angel", "Luis", "Mateo", "Diego", "Santiago"),
                    surnames=("Garcia", "Martinez", "Lopez", "Hernandez", "Gonzalez", "Ramirez"),
                ),
                _name_profile(
                    key="american_black",
                    ethnolinguistic_profile="american_black",
                    religion_naming_pattern="mixed",
                    given_names=("Jaylen", "Malik", "Darius", "Elijah", "Micah", "Kendrick"),
                    surnames=("Jackson", "Robinson", "Walker", "Washington", "Brooks", "Coleman"),
                ),
            ),
            region_profile_weights={
                "default": (("american_anglo", 0.45), ("american_hispanic", 0.30), ("american_black", 0.25)),
            },
        ),
        "TR": _country_profile(
            country_code="TR",
            default_region="Istanbul",
            default_city="Istanbul",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="turkish",
                    ethnolinguistic_profile="turkish",
                    religion_naming_pattern="muslim_secular_mix",
                    given_names=("Ahmet", "Mehmet", "Yusuf", "Emre", "Arda", "Kerem"),
                    surnames=("Yilmaz", "Kaya", "Demir", "Sahin", "Celik", "Aydin"),
                ),
            ),
        ),
        "KR": _country_profile(
            country_code="KR",
            default_region="Seoul",
            default_city="Seoul",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="korean",
                    ethnolinguistic_profile="korean",
                    religion_naming_pattern="secular",
                    given_names=("Min-jun", "Seo-jun", "Ji-ho", "Hyun-woo", "Jun-seo", "Do-yun"),
                    surnames=("Kim", "Lee", "Park", "Choi", "Jung", "Kang"),
                ),
            ),
        ),
        "CN": _country_profile(
            country_code="CN",
            default_region="Beijing",
            default_city="Beijing",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="chinese",
                    ethnolinguistic_profile="han_chinese",
                    religion_naming_pattern="secular",
                    given_names=("Wei", "Jun", "Hao", "Yichen", "Ming", "Tao"),
                    surnames=("Wang", "Li", "Zhang", "Liu", "Chen", "Yang"),
                ),
            ),
        ),
        "PL": _country_profile(
            country_code="PL",
            default_region="Masovian",
            default_city="Warsaw",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="polish",
                    ethnolinguistic_profile="polish",
                    religion_naming_pattern="christian_secular_mix",
                    given_names=("Jakub", "Mateusz", "Kacper", "Pawel", "Mikolaj", "Adam"),
                    surnames=("Nowak", "Kowalski", "Wisniewski", "Wojcik", "Lewandowski", "Kaminski"),
                ),
            ),
        ),
        "RS": _country_profile(
            country_code="RS",
            default_region="Belgrade",
            default_city="Belgrade",
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key="balkan_slavic",
                    ethnolinguistic_profile="balkan_slavic",
                    religion_naming_pattern="christian_mixed",
                    given_names=("Luka", "Nikola", "Marko", "Stefan", "Milan", "Dusan"),
                    surnames=("Jovic", "Mitrovic", "Savic", "Ilic", "Petrovic", "Milenkovic"),
                ),
            ),
        ),
    }
)


def _install_country_specific_name_pools() -> None:
    for code, pool in COUNTRY_SPECIFIC_NAME_POOLS.items():
        # Do not clobber hand-engineered, ethnicity/region-coherent profiles
        # (e.g. NG's Yoruba/Igbo/Hausa sub-profiles). The flat single-pool draws
        # given names and surnames independently, which mixes sub-ethnicities.
        if code in _NAMING_PROFILES:
            continue
        _NAMING_PROFILES[code] = _country_profile(
            country_code=code,
            default_region=str(pool["region"]),
            default_city=str(pool["city"]),
            urbanicity="urban",
            profiles=(
                _name_profile(
                    key=f"{code.lower()}_local",
                    ethnolinguistic_profile=str(pool["ethno"]),
                    religion_naming_pattern=str(pool["pattern"]),
                    given_names=tuple(str(name) for name in pool["given"]),
                    surnames=tuple(str(name) for name in pool["surnames"]),
                ),
            ),
        )


_install_country_specific_name_pools()

_COUNTRY_PROFILE_ALIASES: dict[str, tuple[str, str, str]] = {
    "DZ": ("MA", "Algiers", "Algiers"),
    "TN": ("MA", "Tunis", "Tunis"),
    "LY": ("MA", "Tripoli", "Tripoli"),
    "SD": ("EG", "Khartoum", "Khartoum"),
    "GM": ("SN", "Banjul", "Banjul"),
    "MR": ("SN", "Nouakchott", "Nouakchott"),
    "BF": ("CI", "Centre", "Ouagadougou"),
    "ML": ("CI", "Bamako", "Bamako"),
    "BJ": ("GH", "Littoral", "Cotonou"),
    "TG": ("GH", "Maritime", "Lome"),
    "LR": ("GH", "Montserrado", "Monrovia"),
    "SL": ("GH", "Western Area", "Freetown"),
    "GA": ("CM", "Estuaire", "Libreville"),
    "CG": ("CM", "Brazzaville", "Brazzaville"),
    "CD": ("CM", "Kinshasa", "Kinshasa"),
    "CF": ("CM", "Bangui", "Bangui"),
    "GQ": ("CM", "Bioko Norte", "Malabo"),
    "UG": ("KE", "Central Region", "Kampala"),
    "TZ": ("KE", "Dar es Salaam", "Dar es Salaam"),
    "RW": ("KE", "Kigali", "Kigali"),
    "BI": ("KE", "Bujumbura Mairie", "Bujumbura"),
    "ER": ("ET", "Maekel", "Asmara"),
    "MZ": ("AO", "Maputo", "Maputo"),
    "CV": ("AO", "Praia", "Praia"),
    "ST": ("AO", "Agua Grande", "Sao Tome"),
    "GW": ("AO", "Bissau", "Bissau"),
    "ZW": ("ZA", "Harare", "Harare"),
    "ZM": ("ZA", "Lusaka", "Lusaka"),
    "BW": ("ZA", "Gaborone", "Gaborone"),
    "NA": ("ZA", "Khomas", "Windhoek"),
    "LS": ("ZA", "Maseru", "Maseru"),
    "SZ": ("ZA", "Hhohho", "Mbabane"),
    "MW": ("ZA", "Lilongwe", "Lilongwe"),
    "UY": ("AR", "Montevideo", "Montevideo"),
    "CL": ("AR", "Santiago Metropolitan", "Santiago"),
    "PY": ("AR", "Asuncion", "Asuncion"),
    "PE": ("AR", "Lima", "Lima"),
    "CO": ("AR", "Bogota", "Bogota"),
    "VE": ("AR", "Caracas", "Caracas"),
    "EC": ("AR", "Pichincha", "Quito"),
    "BO": ("AR", "La Paz", "La Paz"),
    "MX": ("AR", "Mexico City", "Mexico City"),
    "CR": ("AR", "San Jose", "San Jose"),
    "PA": ("AR", "Panama", "Panama City"),
    "DO": ("AR", "Santo Domingo", "Santo Domingo"),
    "HN": ("AR", "Francisco Morazan", "Tegucigalpa"),
    "SV": ("AR", "San Salvador", "San Salvador"),
    "GT": ("AR", "Guatemala", "Guatemala City"),
    "BE": ("FR", "Brussels-Capital", "Brussels"),
    "LU": ("FR", "Luxembourg", "Luxembourg"),
    "CH": ("FR", "Zurich", "Zurich"),
    "AT": ("DE", "Vienna", "Vienna"),
    "IE": ("GB", "Dublin", "Dublin"),
    "NL": ("GB", "North Holland", "Amsterdam"),
    "DK": ("GB", "Capital Region", "Copenhagen"),
    "SE": ("GB", "Stockholm", "Stockholm"),
    "NO": ("GB", "Oslo", "Oslo"),
    "FI": ("GB", "Uusimaa", "Helsinki"),
    "CZ": ("PL", "Prague", "Prague"),
    "SK": ("PL", "Bratislava", "Bratislava"),
    "UA": ("PL", "Kyiv", "Kyiv"),
    "HU": ("PL", "Budapest", "Budapest"),
    "HR": ("RS", "Zagreb", "Zagreb"),
    "BA": ("RS", "Sarajevo", "Sarajevo"),
    "ME": ("RS", "Podgorica", "Podgorica"),
    "MK": ("RS", "Skopje", "Skopje"),
    "SI": ("RS", "Ljubljana", "Ljubljana"),
    "BG": ("RS", "Sofia", "Sofia"),
    "AL": ("IT", "Tirana", "Tirana"),
    "CA": ("US", "Ontario", "Toronto"),
    "AU": ("GB", "New South Wales", "Sydney"),
    "NZ": ("GB", "Auckland", "Auckland"),
    "TW": ("CN", "Taipei", "Taipei"),
    "HK": ("CN", "Hong Kong", "Hong Kong"),
    "SA": ("EG", "Riyadh", "Riyadh"),
    "QA": ("EG", "Doha", "Doha"),
    "AE": ("EG", "Dubai", "Dubai"),
    "JO": ("EG", "Amman", "Amman"),
    "LB": ("EG", "Beirut", "Beirut"),
    "SY": ("EG", "Damascus", "Damascus"),
    "IQ": ("EG", "Baghdad", "Baghdad"),
    "KW": ("EG", "Kuwait City", "Kuwait City"),
    "OM": ("EG", "Muscat", "Muscat"),
    "BH": ("EG", "Manama", "Manama"),
    "NE": ("SN", "Niamey", "Niamey"),
    "TD": ("CM", "N'Djamena", "N'Djamena"),
    "MG": ("AO", "Antananarivo", "Antananarivo"),
    "MU": ("ZA", "Port Louis", "Port Louis"),
    "TT": ("GB", "Port of Spain", "Port of Spain"),
    "AG": ("GB", "Saint John", "Saint John's"),
    "GD": ("GB", "Saint George", "Saint George's"),
    "GY": ("GB", "Demerara-Mahaica", "Georgetown"),
    "CU": ("AR", "Havana", "Havana"),
    "HT": ("FR", "Ouest", "Port-au-Prince"),
    "GF": ("FR", "Cayenne", "Cayenne"),
    "MQ": ("FR", "Fort-de-France", "Fort-de-France"),
    "MF": ("FR", "Marigot", "Marigot"),
    "NC": ("FR", "South Province", "Noumea"),
    "PS": ("EG", "Ramallah", "Ramallah"),
    "TM": ("TR", "Ashgabat", "Ashgabat"),
}


def _normalized_country_name_alias(country_name: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", country_name or "")
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_name.replace("`", "'").replace("\u2019", "'").replace("\u2018", "'").split()).casefold()


@lru_cache(maxsize=None)
def resolve_country_naming_profile(country_code: str | None, *, default_country_code: str) -> CountryNamingProfile:
    normalized_country_code = (country_code or default_country_code).strip().upper()
    direct_profile = _NAMING_PROFILES.get(normalized_country_code)
    if direct_profile is not None:
        return direct_profile
    alias = _COUNTRY_PROFILE_ALIASES.get(normalized_country_code)
    if alias is not None:
        base_code, default_region, default_city = alias
        base_profile = _NAMING_PROFILES[base_code]
        return CountryNamingProfile(
            country_code=normalized_country_code,
            default_region=default_region,
            default_city=default_city,
            urbanicity=base_profile.urbanicity,
            region_profile_weights=base_profile.region_profile_weights,
            profiles=base_profile.profiles,
        )
    return _NAMING_PROFILES[default_country_code]


def resolve_country_naming_profile_for_country(
    *,
    country_code: str | None,
    country_name: str | None,
    alpha2_code: str | None = None,
    alpha3_code: str | None = None,
    fifa_code: str | None = None,
    default_country_code: str,
) -> CountryNamingProfile:
    for candidate in (alpha2_code, fifa_code, alpha3_code, country_code):
        normalized = (candidate or "").strip().upper()
        if normalized in _NAMING_PROFILES or normalized in _COUNTRY_PROFILE_ALIASES:
            return resolve_country_naming_profile(normalized, default_country_code=default_country_code)
    name_alias = COUNTRY_NAME_PROFILE_ALIASES.get(_normalized_country_name_alias(country_name))
    if name_alias:
        return resolve_country_naming_profile(name_alias, default_country_code=default_country_code)
    return resolve_country_naming_profile(country_code, default_country_code=default_country_code)


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
        scout_confidence = self._scout_confidence(
            quality_score=quality_score, generation_source=generation_source, rng=rng
        )
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
        regen_type = self._regen_type(lineage_selection)
        parent_legacy_id = (
            lineage_selection.related_legend_ref_id
            if regen_type == "legend_regen" and lineage_selection is not None
            else None
        )
        growth_curve = self._growth_curve(
            current_rating=current_gsi,
            potential=potential.maximum,
            quality_score=quality_score,
            decision_traits=decision_traits,
            personality=personality,
        )
        morale = self._starting_morale(decision_traits=decision_traits, personality=personality)
        chemistry_affinity = self._chemistry_affinity(
            decision_traits=decision_traits,
            personality=personality,
            origin=origin,
            regen_type=regen_type,
        )
        story_seed = self._story_seed(
            decision_traits=decision_traits,
            personality=personality,
            origin=origin,
            regen_type=regen_type,
            lineage_selection=lineage_selection,
        )
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
            "dna_profile": generate_dna_profile(
                position=primary_position,
                country_code=origin.country_code,
                lineage_metadata=lineage_metadata or None,
                rng=rng,
            ),
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
        uniqueness_score = self._uniqueness_score(
            regen_type=regen_type,
            current_rating=current_gsi,
            potential=potential.maximum,
            secondary_positions=secondary_positions,
            decision_traits=decision_traits,
            personality=personality,
            story_seed=story_seed,
            is_special_lineage=is_special_lineage,
        )
        metadata.update(
            {
                "regen_type": regen_type,
                "parent_legacy_id": parent_legacy_id,
                "growth_curve": growth_curve,
                "morale": morale,
                "chemistry_affinity": chemistry_affinity,
                "story_seed": story_seed,
                "uniqueness_score": uniqueness_score,
            }
        )
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
            current_rating=current_gsi,
            potential=potential.maximum,
            scout_confidence=scout_confidence,
            generation_source=generation_source,
            regen_type=regen_type,
            parent_legacy_id=parent_legacy_id,
            status="academy_candidate" if generation_source == "academy" else "active",
            is_special_lineage=is_special_lineage,
            uniqueness_score=uniqueness_score,
            growth_curve=growth_curve,
            morale=morale,
            chemistry_affinity=chemistry_affinity,
            story_seed=story_seed,
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

    def _regen_type(self, lineage_selection: LineageSelection | None) -> str:
        if lineage_selection is None:
            return "organic_newgen"
        if (
            lineage_selection.is_real_legend_lineage
            or lineage_selection.is_retired_regen_lineage
            or lineage_selection.relationship_type in {"son_of_legend", "hometown_legacy"}
        ):
            return "legend_regen"
        return "organic_newgen"

    def _starting_morale(
        self,
        *,
        decision_traits: dict[str, int],
        personality: RegenPersonalityView,
    ) -> float:
        morale = (
            (decision_traits["loyalty"] * 0.24)
            + (decision_traits["professionalism"] * 0.24)
            + (decision_traits["patience"] * 0.18)
            + (decision_traits["adaptability"] * 0.14)
            + (personality.resilience * 0.20)
        ) / 100.0
        return round(max(0.3, min(0.95, morale)), 4)

    def _growth_curve(
        self,
        *,
        current_rating: int,
        potential: int,
        quality_score: float,
        decision_traits: dict[str, int],
        personality: RegenPersonalityView,
    ) -> float:
        upside = max(potential - current_rating, 0) / 35.0
        growth = (
            (upside * 0.42)
            + ((decision_traits["professionalism"] / 100.0) * 0.20)
            + ((personality.resilience / 100.0) * 0.12)
            + ((decision_traits["adaptability"] / 100.0) * 0.10)
            + ((quality_score / 100.0) * 0.16)
        )
        return round(max(0.2, min(1.0, growth)), 4)

    def _chemistry_affinity(
        self,
        *,
        decision_traits: dict[str, int],
        personality: RegenPersonalityView,
        origin: RegenOriginView,
        regen_type: str,
    ) -> dict[str, float]:
        hometown_weight = decision_traits["hometown_affinity"] / 100.0
        return {
            "academy_discipline": round(decision_traits["professionalism"] / 100.0, 4),
            "street_flair": round(personality.flair / 100.0, 4),
            "elite_ambition": round(max(decision_traits["ambition"], decision_traits["trophy_hunger"]) / 100.0, 4),
            "local_loyalty": round(hometown_weight if origin.city_name else hometown_weight * 0.65, 4),
            "legacy_aura": round(0.9 if regen_type == "legend_regen" else 0.35, 4),
        }

    def _story_seed(
        self,
        *,
        decision_traits: dict[str, int],
        personality: RegenPersonalityView,
        origin: RegenOriginView,
        regen_type: str,
        lineage_selection: LineageSelection | None,
    ) -> dict[str, str]:
        if regen_type == "legend_regen":
            background = "legacy academy heir"
        elif personality.flair >= 72 and origin.urbanicity == "urban":
            background = "street footballer"
        elif decision_traits["professionalism"] >= 72:
            background = "academy standout"
        else:
            background = "regional prospect"

        if decision_traits["temperament"] >= 72:
            temperament = "aggressive"
        elif decision_traits["temperament"] <= 38:
            temperament = "calm"
        else:
            temperament = "balanced"

        if decision_traits["ambition"] >= 85:
            ambition = "world_class"
        elif decision_traits["ambition"] >= 70:
            ambition = "elite"
        elif decision_traits["ambition"] >= 55:
            ambition = "top_flight"
        else:
            ambition = "steady"

        pressure_total = decision_traits["professionalism"] + decision_traits["patience"] + personality.resilience
        if pressure_total >= 220:
            pressure_response = "clutch"
        elif decision_traits["temperament"] >= 75 and decision_traits["patience"] <= 42:
            pressure_response = "volatile"
        else:
            pressure_response = "steady"

        lineage_note = (
            f" carrying a {lineage_selection.relationship_type.replace('_', ' ')} thread"
            if lineage_selection is not None
            else ""
        )
        snippet = (
            f"{background.title()}{lineage_note}, built for {ambition.replace('_', ' ')} ceilings "
            f"with a {pressure_response.replace('_', ' ')} edge."
        )
        return {
            "background": background,
            "temperament": temperament,
            "ambition": ambition,
            "pressure_response": pressure_response,
            "snippet": snippet,
        }

    def _uniqueness_score(
        self,
        *,
        regen_type: str,
        current_rating: int,
        potential: int,
        secondary_positions: tuple[str, ...],
        decision_traits: dict[str, int],
        personality: RegenPersonalityView,
        story_seed: dict[str, str],
        is_special_lineage: bool,
    ) -> float:
        rarity_weight = 0.32 if regen_type == "legend_regen" else 0.12
        if is_special_lineage:
            rarity_weight += 0.08
        trait_combo_uniqueness = (
            (sum(1 for value in decision_traits.values() if value >= 75) * 0.035)
            + (0.05 if personality.flair >= 75 and decision_traits["professionalism"] >= 70 else 0.0)
            + (min(len(personality.personality_tags), 3) * 0.025)
        )
        stat_distribution_entropy = min(
            0.24,
            ((max(potential - current_rating, 0) / 100.0) * 0.18) + (len(secondary_positions) * 0.03),
        )
        narrative_seed_complexity = min(
            0.22,
            0.08
            + (0.05 if story_seed["background"] == "street footballer" else 0.0)
            + (0.05 if story_seed["pressure_response"] == "clutch" else 0.0)
            + (0.04 if story_seed["ambition"] == "world_class" else 0.0),
        )
        score = rarity_weight + trait_combo_uniqueness + stat_distribution_entropy + narrative_seed_complexity
        return round(max(0.0, min(1.0, score)), 4)

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
        leadership = _clamp(
            (temperament * 0.35) + (professionalism * 0.3) + (ambition * 0.25) + rng.randint(-6, 6), 30, 82
        )
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
            if candidate.legend_type == "real_legend"
            and self._lineage_candidate_allowed(candidate, club_id, club_context)
        ]
        eligible_retired = [
            candidate
            for candidate in lineage_pool
            if candidate.legend_type == "retired_regen"
            and self._lineage_candidate_allowed(candidate, club_id, club_context)
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
            lineage_country_code=(
                club_context.country_code or self.settings.regen_generation.default_country_code
            ).upper(),
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
    def _adjust_range(
        base: AbilityRangeView, rng: random.Random, *, min_value: int = 30, max_value: int = 99
    ) -> AbilityRangeView:
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
        country_profile = resolve_country_naming_profile(
            base_regen.birth_country_code,
            default_country_code=self.settings.regen_generation.default_country_code,
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
        hair_index = (
            _HAIR_PROFILES.index(visual_profile.get("hair_profile"))
            if visual_profile.get("hair_profile") in _HAIR_PROFILES
            else 0
        )
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
        country_code = (
            lineage_country or club_context.country_code or self.settings.regen_generation.default_country_code
        ).upper()
        country_profile = resolve_country_naming_profile(
            country_code,
            default_country_code=self.settings.regen_generation.default_country_code,
        )
        region_name = lineage_region or club_context.region_name or country_profile.default_region
        city_name = lineage_city or club_context.city_name or country_profile.default_city
        profile, display_name = generate_country_display_name(
            country_profile,
            region_name=region_name,
            used_names=used_names,
            rng=rng,
            forced_surname=forced_surname,
        )
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
        customization_cost = (
            config.owner_son_paid_request_customization_cost if customization_keys & payload.keys() else 0
        )
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
                    owner_user_id = lineage.get("owner_user_id") or (
                        owner_context.owner_user_id if owner_context else None
                    )
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
            self.store.season_regen_generation_counts[resolved_season] = self.store.season_regen_generation_counts.get(
                resolved_season, 0
            ) + len(bundle.regens)
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
    "generate_country_display_name",
    "get_regen_service",
    "resolve_country_naming_profile",
    "resolve_country_naming_profile_for_country",
]
