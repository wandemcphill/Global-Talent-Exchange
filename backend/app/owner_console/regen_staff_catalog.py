"""Original regen staff for the employment market.

These are not real people from the FM23 file. Ratings sit mostly in the
foundation and established bands. A small share of general managers, physios,
first-team managers, and heads of youth development are women. Portraits come
from the mature face bank in staff_portraits, continued from the eight young
regen studies.
"""

from __future__ import annotations

from functools import lru_cache

REGEN_STAFF_COUNT = 17000
FEMALE_ROLES = frozenset(
    {
        "general_manager",
        "medical_director",
        "first_team_manager",
        "head_of_youth_development",
    }
)
PORTRAIT_PUBLIC_PREFIX = "/staff-portraits"

FACE_GROUPS = (
    "west_african",
    "north_european",
    "east_asian",
    "south_european",
    "middle_eastern",
    "latino",
    "mixed_braids",
    "blonde",
)

_NATIONS = {
    "west_african": ("Nigeria", "Ghana", "Senegal", "Ivory Coast", "Cameroon"),
    "north_european": ("England", "Germany", "Sweden", "Netherlands", "Denmark"),
    "east_asian": ("Japan", "South Korea", "China"),
    "south_european": ("Spain", "Italy", "Portugal", "Greece"),
    "middle_eastern": ("Morocco", "Egypt", "Turkey", "Saudi Arabia"),
    "latino": ("Brazil", "Argentina", "Colombia", "Mexico"),
    "mixed_braids": ("France", "Brazil", "England", "Netherlands"),
    "blonde": ("Sweden", "Norway", "Denmark", "Finland", "Netherlands"),
}

_MALE = {
    "west_african": (
        ("Kofi", "Kwame", "Yaw", "Emeka", "Segun", "Malick", "Idrissa", "Kwesi", "Tunde", "Obinna", "Femi", "Lamine"),
        ("Mensah", "Diallo", "Adeyemi", "Boateng", "Traore", "Okeke", "Kamara", "Balogun", "Nwosu", "Diop"),
    ),
    "north_european": (
        ("Jonas", "Henrik", "Lars", "Erik", "Markus", "Thomas", "Andreas", "Nils", "Owen", "Callum", "Pieter", "Soren"),
        ("Keller", "Lindholm", "Berg", "Hoffmann", "Walsh", "Kruger", "Nielsen", "Hartmann", "Clarke", "Vogel"),
    ),
    "east_asian": (
        ("Hiroshi", "Kenji", "Daichi", "Minho", "Jae", "Wei", "Haruto", "Yuki", "Sung", "Tao", "Ren", "Kenta"),
        ("Sato", "Nakamura", "Park", "Kim", "Chen", "Takahashi", "Liu", "Yamamoto", "Choi", "Watanabe"),
    ),
    "south_european": (
        ("Marco", "Luca", "Andreas", "Mateo", "Diego", "Paolo", "Nuno", "Giorgos", "Alessio", "Raul", "Enzo", "Tiago"),
        ("Rossi", "Silva", "Costa", "Moretti", "Almeida", "Papadopoulos", "Greco", "Ferreira", "Romano", "Santos"),
    ),
    "middle_eastern": (
        ("Omar", "Karim", "Youssef", "Hassan", "Emre", "Farid", "Samir", "Tariq", "Adel", "Mehmet", "Nabil", "Rami"),
        ("Haddad", "El-Sayed", "Demir", "Farouk", "Qureshi", "Mansour", "Yilmaz", "Nasser", "Khoury", "Amrani"),
    ),
    "latino": (
        (
            "Mateo",
            "Santiago",
            "Lucas",
            "Andres",
            "Thiago",
            "Joao",
            "Diego",
            "Camilo",
            "Bruno",
            "Rafael",
            "Luis",
            "Pedro",
        ),
        ("Navarro", "Almeida", "Costa", "Duarte", "Silva", "Herrera", "Pereira", "Vargas", "Mendes", "Rojas"),
    ),
    "mixed_braids": (
        ("Malik", "Jordan", "Andre", "Noah", "Elias", "Marcus", "Leo", "Adam", "Isaac", "Nathan", "Caleb", "Dante"),
        ("Laurent", "Diallo", "Bennett", "Moreau", "Silva", "Okoro", "Dubois", "James", "Petit", "Barnes"),
    ),
    "blonde": (
        (
            "Soren",
            "Erik",
            "Lars",
            "Nils",
            "Johan",
            "Mikkel",
            "Anders",
            "Frederik",
            "Oskar",
            "Vilhelm",
            "Kasper",
            "Mats",
        ),
        ("Lindholm", "Bergstrom", "Nielsen", "Hansen", "Eriksson", "Dahl", "Virtanen", "Holm", "Strand", "Bakker"),
    ),
}

_FEMALE = {
    "west_african": ("Amina", "Abena", "Chioma", "Fatou", "Zainab", "Adwoa", "Ngozi", "Aisha"),
    "north_european": ("Helena", "Ingrid", "Klara", "Freya", "Marta", "Elise", "Nora", "Sigrid"),
    "east_asian": ("Hana", "Mei", "Yuna", "Aiko", "Soo", "Lin", "Hanae", "Min"),
    "south_european": ("Lucia", "Giulia", "Ines", "Elena", "Chiara", "Sofia", "Beatriz", "Marta"),
    "middle_eastern": ("Leila", "Noor", "Yasmin", "Hana", "Amira", "Dalia", "Salma", "Rana"),
    "latino": ("Camila", "Valentina", "Lucia", "Ana", "Mariana", "Renata", "Bianca", "Catalina"),
    "mixed_braids": ("Amina", "Leah", "Naomi", "Imani", "Clara", "Maya", "Alicia", "Nina"),
    "blonde": ("Freya", "Astrid", "Linnea", "Maja", "Elsa", "Annik", "Sigrid", "Thea"),
}

_ROLE_PLAN = (
    ("first_team_manager", 3300),
    ("general_manager", 3100),
    ("medical_director", 3100),
    ("head_of_youth_development", 4550),
    ("chief_scout", 2950),
)

_STYLES = {
    "first_team_manager": (
        "Direct Possession",
        "Low Block",
        "High Press",
        "Wing Play",
        "Counter Attack",
        "Patient Build-Up",
    ),
    "general_manager": (
        "Grassroots Operator",
        "Sell and Rebuild",
        "Academy First",
        "Wage Discipline",
        "Data Recruitment",
        "Commercial Growth",
    ),
    "medical_director": (
        "Load Management",
        "Rapid Rehab",
        "Prevention First",
        "Matchday Physio",
        "Youth Screening",
    ),
    "head_of_youth_development": (
        "Diamond Mentor",
        "Technical School",
        "Athletic Pathway",
        "Local Scouting",
    ),
    "chief_scout": (
        "Regional Network",
        "Video Analyst",
        "Value Hunting",
        "Youth Eyes",
    ),
}

_TEMPERAMENTS = ("pragmatic", "calm", "demanding", "diplomatic", "fiery")

_MALE_PORTRAITS = ("41", "54", "bald", "beard", "glasses")
_FEMALE_PORTRAITS = ("42", "glasses", "long", "cropped")


def portrait_filename(group: str, gender: str, index: int) -> str:
    kind = "f" if gender == "female" else "m"
    variants = _FEMALE_PORTRAITS if gender == "female" else _MALE_PORTRAITS
    slot = (index // len(FACE_GROUPS)) % len(variants)
    return f"mature_{kind}_{group}_{variants[slot]}.jpg"


def _mix(index: int, low: int, high: int) -> int:
    span = high - low + 1
    return low + ((index * 17 + 3) % span)


def _rating(index: int) -> int:
    slot = index % 20
    if slot < 10:
        return _mix(index, 60, 70)
    if slot < 16:
        return _mix(index, 71, 78)
    if slot < 19:
        return _mix(index, 79, 84)
    return _mix(index, 85, 91)


def _wage(rating: int) -> int:
    if rating <= 70:
        return 180 + (rating - 58) * 40
    if rating <= 78:
        return 760 + (rating - 71) * 160
    if rating <= 84:
        return 2100 + (rating - 79) * 380
    return 4800 + (rating - 85) * 650


def _roles() -> list[str]:
    roles: list[str] = []
    for role, count in _ROLE_PLAN:
        roles.extend([role] * count)
    return roles


@lru_cache(maxsize=1)
def build_regen_staff_catalog() -> tuple[dict, ...]:
    roles = _roles()
    if len(roles) != REGEN_STAFF_COUNT:
        raise RuntimeError(f"regen staff role plan must total {REGEN_STAFF_COUNT}")
    people: list[dict] = []
    for index, role in enumerate(roles):
        group = FACE_GROUPS[index % len(FACE_GROUPS)]
        gender = "female" if role in FEMALE_ROLES and index % 13 == 0 else "male"
        age = 34 + ((index * 3) % 23)
        rating = _rating(index)
        wage = _wage(rating)
        male_given, family = _MALE[group]
        if gender == "female":
            given_pool = _FEMALE[group]
            given = given_pool[(index // len(FACE_GROUPS)) % len(given_pool)]
        else:
            given = male_given[(index // len(FACE_GROUPS)) % len(male_given)]
        surname = family[(index // (len(FACE_GROUPS) * 4)) % len(family)]
        nation = _NATIONS[group][index % len(_NATIONS[group])]
        style = _STYLES[role][index % len(_STYLES[role])]
        temperament = _TEMPERAMENTS[index % len(_TEMPERAMENTS)]
        portrait = portrait_filename(group, gender, index)
        staff_id = f"regen-staff-{index:05d}"
        people.append(
            {
                "id": staff_id,
                "staff_id": staff_id,
                "role": role,
                "role_label": role.replace("_", " ").title(),
                "name": f"{given} {surname}",
                "nation": nation,
                "gender": gender,
                "age": age,
                "face_group": group,
                "origin": "regen_staff",
                "portrait_url": f"{PORTRAIT_PUBLIC_PREFIX}/{portrait}",
                "rating": rating,
                "rarity": "elite" if rating >= 85 else "established" if rating >= 79 else "standard",
                "style": style,
                "temperament": temperament,
                "ambition": _mix(index, 8, 18),
                "loyalty": _mix(index + 2, 8, 18),
                "youth_development": _mix(index, 8, 18),
                "tactical_flexibility": _mix(index + 1, 8, 18),
                "min_prestige": max(10, (rating - 60) * 2),
                "salary": wage,
                "salary_gtex": wage,
                "bio": f"Regen {role.replace('_', ' ')} from {nation}, age {age}.",
                "specialty": style,
            }
        )
    return tuple(people)
