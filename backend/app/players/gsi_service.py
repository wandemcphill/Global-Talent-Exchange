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
    # Active Player Benchmarks
    "ademola lookman": (84, 90),
    "cole palmer": (89, 93),
    "cole jermaine palmer": (89, 93),
    "estêvão": (85, 90),
    "estevao": (85, 90),
    "gabriel mec": (78, 89),
    "zadok yohanna": (74, 89),
    "z. yohanna": (74, 89),
}

# External provider IDs mapped to governed (current_gsi, potential_gsi)
PROVIDER_ID_GSI_OVERRIDES: dict[str, tuple[int, int]] = {
    "5321": (84, 90),        # Lookman (sportmonks)
    "29141828": (84, 90),    # Lookman (fm23)
    "257534": (89, 93),      # Palmer (sofifa)
    "28120042": (89, 93),    # Palmer (fm23)
    "28912747": (89, 93),    # Palmer (sportmonks)
    "2002042919": (85, 90),  # Estêvão (fm23)
    "37701999": (85, 90),    # Estêvão (sportmonks)
    "2002088213": (78, 89),  # Mec (fm23)
    "2002046177": (78, 89),  # Mec (fm23)
    "1421433": (74, 89),     # Zadok (fm23)
    "37974187": (74, 89),    # Zadok (sportmonks)
    "601710": (90, 90),      # Michael Laudrup (fm23)
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
        getattr(player, "canonical_display_name", None)
        or getattr(player, "full_name", None)
        or getattr(player, "name", None)
        or ""
    ).strip().lower()

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
    dna = dict(getattr(player, "dna_profile", None) or {}) if isinstance(getattr(player, "dna_profile", None), dict) else {}
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
