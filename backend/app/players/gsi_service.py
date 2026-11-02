"""Unified Governed GSI Resolver for GTEX.

Decouples athletic GSI from EUR market value and enforces governed ratings,
Ballon d'Or floors, and calibrated player benchmarks without promoting potential
into current rating.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Calibrated benchmarks and user-governed overrides by lowercase canonical name
CANONICAL_GSI_OVERRIDES: dict[str, tuple[int, int]] = {
    # All-Time Legends & Ballon d'Or Winners
    "lionel messi": (98, 98),
    "cristiano ronaldo": (98, 98),
    "edson arantes do nascimento (pelé)": (98, 98),
    "pelé": (98, 98),
    "diego maradona": (98, 98),
    "thierry henry": (95, 95),
    "romário de souza faria": (95, 95),
    "romário": (95, 95),
    "zinedine zidane": (95, 95),
    "ronaldinho": (95, 95),
    "alfredo di stéfano": (95, 95),
    "eric cantona": (91, 91),
    "éric cantona": (91, 91),
    "michael laudrup": (90, 90),
    # Active Stars & Wonderkids (Calibrated per FC 27 ±1 Benchmarks)
    "ademola lookman": (84, 90),
    "aleksandar pavlovic": (82, 89),
    "aleksandar pavlović": (82, 89),
    "amara diouf": (76, 90),
    "amir ibragimov": (76, 88),
    "andrea natali": (74, 86),
    "archie gray": (77, 88),
    "arda guler": (82, 90),
    "arda güler": (82, 90),
    "assan ouedraogo": (77, 88),
    "assan ouédraogo": (77, 88),
    "ayyoub bouaddi": (77, 89),
    "can uzun": (77, 89),
    "cardoso varela": (77, 89),
    "cavan sullivan": (76, 90),
    "chido obi": (75, 89),
    "chris rigg": (74, 88),
    "claudio echeverri": (78, 89),
    "claudio jeremias echeverri": (78, 89),
    "claudio jeremías echeverri": (78, 89),
    "cole jermaine palmer": (89, 93),
    "cole palmer": (89, 93),
    "dean huijsen": (78, 88),
    "ebrima tunkara": (73, 90),
    "endrick": (81, 91),
    "endrick felipe moreira de sousa": (81, 91),
    "enzo alves": (73, 88),
    "estevao": (81, 91),
    "estevao willian": (81, 91),
    "estêvão": (81, 91),
    "estêvão willian": (81, 91),
    "ethan chidiebere nwaneri": (78, 90),
    "ethan mbappe": (72, 85),
    "ethan mbappé": (72, 85),
    "ethan nwaneri": (78, 90),
    "finlay gorman": (74, 89),
    "francesco camarda": (77, 91),
    "franco mastantuono": (78, 90),
    "gabriel mec": (78, 89),
    "geovany quenda": (77, 89),
    "guille fernandez": (77, 89),
    "guille fernández": (77, 89),
    "jj gabriel": (73, 92),
    "jorrel hato": (81, 89),
    "justin lerma": (74, 88),
    "kenan yıldız": (84, 91),
    "kendry paez": (77, 89),
    "kendry páez": (77, 89),
    "kobbie mainoo": (81, 91),
    "konstantinos karetsas": (76, 88),
    "lennart karl": (78, 91),
    "leny yoro": (81, 90),
    "lewis miley": (76, 88),
    "lucas bergvall": (78, 89),
    "luka vuskovic": (77, 89),
    "luka vušković": (77, 89),
    "marc bernal": (77, 89),
    "marc bernal casas": (77, 89),
    "mathys tel": (80, 89),
    "max dowman": (74, 89),
    "michal zuk": (73, 87),
    "mikey moore": (75, 90),
    "myles anthony lewis-skelly": (76, 88),
    "myles lewis-skelly": (76, 88),
    "pau cubarsi": (83, 92),
    "pau cubarsi paredes": (83, 92),
    "pau cubarsí": (83, 92),
    "pau cubarsí paredes": (83, 92),
    "paul wanner": (77, 88),
    "pedro rodriguez": (73, 87),
    "pedro rodríguez": (73, 87),
    "rio ngumoha": (75, 89),
    "rodrigo mora": (75, 88),
    "ruslan mba": (73, 87),
    "saba kharebashvili": (74, 88),
    "samu aghehowa": (81, 89),
    "samu omorodion": (81, 89),
    "samuel omorodion aghehowa": (81, 89),
    "sean steur": (73, 87),
    "shane kluivert": (72, 86),
    "shumaira mheuka": (77, 88),
    "sverre halseth nypan": (76, 89),
    "sverre nypan": (76, 89),
    "toni fernandez": (77, 89),
    "toni fernández": (77, 89),
    "warren zaire-emery": (83, 90),
    "warren zaïre-emery": (83, 90),
    "z. yohanna": (74, 89),
    "zadok yohanna": (74, 89),
}

# External provider IDs mapped to governed (current_gsi, potential_gsi)
PROVIDER_ID_GSI_OVERRIDES: dict[str, tuple[int, int]] = {
    "1421433": (74, 89),
    "2000077193": (82, 90),
    "2000094152": (78, 89),
    "2000103330": (77, 89),
    "2000104850": (80, 89),
    "2000105654": (81, 89),
    "2000109240": (78, 88),
    "2000123586": (81, 91),
    "2000138516": (77, 88),
    "2000138835": (84, 91),
    "2000169739": (78, 89),
    "2000171034": (82, 89),
    "2000179712": (83, 90),
    "2000182795": (77, 88),
    "2000182819": (81, 90),
    "2000188173": (77, 88),
    "2000189871": (76, 88),
    "2000211219": (81, 89),
    "2000220941": (81, 91),
    "2002042919": (81, 91),
    "2002042933": (77, 89),
    "2002042937": (77, 89),
    "2002042945": (75, 90),
    "2002042946": (77, 89),
    "2002042948": (78, 90),
    "2002042951": (83, 92),
    "2002042974": (76, 88),
    "2002042976": (78, 90),
    "2002042982": (74, 88),
    "2002043015": (76, 90),
    "2002044535": (76, 88),
    "2002045113": (77, 88),
    "2002046177": (78, 89),
    "2002086609": (74, 89),
    "2002086652": (74, 89),
    "2002087591": (73, 92),
    "2002087653": (74, 88),
    "2002087805": (77, 88),
    "2002087817": (76, 88),
    "2002087865": (75, 89),
    "2002087921": (77, 89),
    "2002088033": (77, 91),
    "2002088148": (72, 86),
    "2002088168": (77, 89),
    "2002088213": (78, 89),
    "2002088219": (77, 89),
    "2002088237": (78, 91),
    "2002088246": (73, 88),
    "2002088249": (73, 87),
    "2002088256": (73, 87),
    "2002088298": (74, 89),
    "2002088307": (76, 90),
    "2002088331": (73, 90),
    "2002088353": (73, 87),
    "2002088411": (74, 88),
    "2002088421": (77, 89),
    "2002088971": (73, 92),
    "2002089123": (75, 89),
    "2002089126": (77, 89),
    "2002089127": (73, 90),
    "2002089128": (77, 89),
    "257534": (89, 93),
    "276528": (78, 89),
    "278773": (76, 88),
    "28120042": (89, 93),
    "28912747": (89, 93),
    "29141828": (84, 90),
    "37531504": (80, 89),
    "37547467": (82, 90),
    "37568808": (78, 90),
    "37577660": (76, 89),
    "37582044": (82, 89),
    "37582045": (77, 88),
    "37593237": (83, 90),
    "37598725": (84, 91),
    "37598726": (77, 89),
    "37600357": (81, 90),
    "37612542": (78, 88),
    "37622274": (81, 89),
    "37645043": (77, 88),
    "37656652": (77, 89),
    "37656790": (83, 92),
    "37656803": (75, 88),
    "37657587": (77, 89),
    "37710798": (77, 89),
    "37717176": (77, 89),
    "37720618": (74, 89),
    "37729623": (78, 90),
    "37974187": (74, 89),
    "5321": (84, 90),
    "601710": (90, 90),
}


def resolve_player_gsi(
    player: Any,
    market: Any | None = None,
) -> tuple[int, int]:
    """Resolve authoritative (current_gsi, potential_gsi) for any player.

    Precedence:
    1. Explicit governed columns (player.governed_gsi, player.governed_potential_gsi).
    2. Linked legendary profile governed columns.
    3. Explicit Canonical and Provider ID overrides (e.g. Lookman 84/90, Palmer 89/93).
    4. Market metadata governed/current GSI.
    5. DNA profile ratings (current_rating, overall) — NEVER promoted to potential.
    6. Potential rating (dna potential_rating, potential) — preserved independently.
    7. Default fallback: 65 current, 75 potential.

    Invariants:
    - Never promotes potential into current rating.
    - Never derives athletic GSI from EUR market value.
    - Always clamps between 40 and 99.
    - Ensures potential_gsi >= current_gsi.
    """
    cur_gsi: int | None = None
    pot_gsi: int | None = None

    # 1. Governed attributes directly on player object
    if hasattr(player, "governed_gsi") and getattr(player, "governed_gsi") is not None:
        cur_gsi = int(getattr(player, "governed_gsi"))
    if hasattr(player, "governed_potential_gsi") and getattr(player, "governed_potential_gsi") is not None:
        pot_gsi = int(getattr(player, "governed_potential_gsi"))

    # 2. Linked legendary profile
    if cur_gsi is None and hasattr(player, "legendary_profile") and player.legendary_profile is not None:
        leg = player.legendary_profile
        if getattr(leg, "governed_gsi", None) is not None:
            cur_gsi = int(getattr(leg, "governed_gsi"))
        if pot_gsi is None and getattr(leg, "governed_potential_gsi", None) is not None:
            pot_gsi = int(getattr(leg, "governed_potential_gsi"))

    # 3. Canonical and Provider ID overrides
    name = (
        (
            getattr(player, "canonical_display_name", None)
            or getattr(player, "full_name", None)
            or getattr(player, "name", None)
            or ""
        )
        .strip()
        .lower()
    )

    ext_id = str(getattr(player, "provider_external_id", "") or "").strip()

    if (cur_gsi is None or pot_gsi is None) and ext_id in PROVIDER_ID_GSI_OVERRIDES:
        o_cur, o_pot = PROVIDER_ID_GSI_OVERRIDES[ext_id]
        if cur_gsi is None:
            cur_gsi = o_cur
        if pot_gsi is None:
            pot_gsi = o_pot

    if (cur_gsi is None or pot_gsi is None) and name in CANONICAL_GSI_OVERRIDES:
        o_cur, o_pot = CANONICAL_GSI_OVERRIDES[name]
        if cur_gsi is None:
            cur_gsi = o_cur
        if pot_gsi is None:
            pot_gsi = o_pot

    # 4. Market metadata
    if market is not None and hasattr(market, "metadata_json") and isinstance(market.metadata_json, dict):
        m_meta = market.metadata_json
        if cur_gsi is None:
            if m_meta.get("governed_gsi"):
                cur_gsi = int(m_meta["governed_gsi"])
            elif m_meta.get("current_gsi"):
                cur_gsi = int(m_meta["current_gsi"])
            elif m_meta.get("gsi"):
                cur_gsi = int(m_meta["gsi"])
        if pot_gsi is None:
            if m_meta.get("governed_potential_gsi"):
                pot_gsi = int(m_meta["governed_potential_gsi"])
            elif m_meta.get("potential_gsi"):
                pot_gsi = int(m_meta["potential_gsi"])

    # 5. DNA profile inspection
    dna = (
        dict(getattr(player, "dna_profile", None) or {})
        if isinstance(getattr(player, "dna_profile", None), dict)
        else {}
    )
    if cur_gsi is None:
        cur_candidates = [
            dna.get("current_rating"),
            dna.get("overall"),
            dna.get("sofifa_overall"),
            getattr(player, "rating", None),
        ]
        valid_cur = [int(float(v)) for v in cur_candidates if isinstance(v, (int, float)) and float(v) > 0]
        if valid_cur:
            cur_gsi = valid_cur[0]

    if pot_gsi is None:
        pot_candidates = [
            dna.get("potential_rating"),
            dna.get("potential"),
            dna.get("sofifa_potential"),
            getattr(player, "potential", None),
        ]
        valid_pot = [int(float(v)) for v in pot_candidates if isinstance(v, (int, float)) and float(v) > 0]
        if valid_pot:
            pot_gsi = valid_pot[0]

    # 6. Apply legend minimum floor if classified as legend
    is_legend = (
        str(getattr(player, "real_player_tier", "") or "").strip().lower() == "legend"
        or str(getattr(player, "source_provider", "") or "").strip().lower() == "gtex_legend_prime"
        or getattr(player, "legendary_profile_id", None) is not None
    )
    if is_legend:
        cur_gsi = max(cur_gsi or 80, 80)
        pot_gsi = max(pot_gsi or cur_gsi, cur_gsi)

    # 7. Final defaults and clamping
    final_cur = max(40, min(99, cur_gsi if cur_gsi is not None else 65))
    final_pot = max(final_cur, min(99, pot_gsi if pot_gsi is not None else final_cur))

    return final_cur, final_pot
