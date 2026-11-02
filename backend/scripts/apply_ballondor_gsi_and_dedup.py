#!/usr/bin/env python3
"""Apply GTEX Generational Legend Ages, Ballon d'Or Governed GSI, and Deduplication.

Enforces:
1. Generational Legend Ages:
   - Messi & Cristiano Ronaldo: Youngest legends (Age 20; DOB in 2006)
   - Pelé & Alfredo Di Stéfano: Oldest legends (Age 30; DOB in 1996)
   - Generational bands (Band 1: 1950s-1980s [26-30], Band 2: 1990s-2010 [23-25], Band 3: Modern vets [20-22])
   - Ceiling <= 30 across all legends.
2. Ballon d'Or Governed GSI:
   - Rank 1 (Winners): GSI Floor 95 (Overrides: Messi 98, Pelé 98, CR7 98, Maradona 98)
   - Rank 2-4 (Podium): GSI Floor 90 (Override: Cantona 91, Laudrup 90)
   - Rest: GSI Floor 85 (or 80)
   - Syncs to ingestion_players and player_summary_read_models.
3. Deduplication:
   - Retires duplicate player rows (Eric Cantona Lyon, Andres Iniesta duplicate, duplicate active FM23 rows)
   - Sets is_tradable = false, player_share_markets.status = 'retired', and cleans player_summary_read_models.
"""

from __future__ import annotations

import csv
import logging
import sys
from datetime import date
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ballondor_dedup_sync")

VIRTUAL_DATE = date(2026, 11, 1)

CANONICAL_GSI_OVERRIDES = {
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
}

# Duplicate player IDs to retire (non-canonical duplicate -> canonical)
# Only retiring duplicate rows that have 0 user share holdings
KNOWN_DUPLICATE_RETIREMENTS = {
    # Eric Cantona (Lyon FM23 duplicate -> Man United FM23 canonical)
    "106bbc0a-a8b3-408e-b856-a4dad15799fd": "b421109b-b268-49cc-b2cb-0fe6cf40ce4a",
    # Andres Iniesta (unaccented FM23 duplicate -> accented canonical)
    "55f70b9b-dae9-4a55-8721-ccf9bdaa0154": "b496213b-ff42-4feb-878f-55389ae7a50c",
    # Luis Figo duplicate
    "0704b985-6e51-49fc-bf74-45820da69183": "5220d191-0220-4d93-87c2-e47d15929d7d",
}

# Known duplicate legendary profiles to deactivate
KNOWN_DUPLICATE_PROFILES_TO_DEACTIVATE = [
    "59acd2d8-9fea-47f0-b33a-df6f932ccf5c",  # eric-cantona-2002042479
    "315ea36a-68e6-4467-a5e2-12f817967237",  # andres-iniesta-2002041673
]


def load_ballondor_updates() -> dict[str, tuple[int, int, str]]:
    csv_path = Path(r"C:\Users\ayomc\.gemini\antigravity\scratch\gtex_audit\GTEX_BallonDor_All_Legends.csv")
    if not csv_path.exists():
        logger.error("Ballon d'Or CSV not found at %s", csv_path)
        return {}

    updates: dict[str, tuple[int, int, str]] = {}
    with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("canonical_name", "").strip().lower()
            pids = [
                p.strip()
                for p in row.get("all_legendary_profile_ids", "").split(";")
                if p.strip() and p.strip() != "NONE(unlinked_gtex_legend_prime_player)"
            ]
            best_place = row.get("best_place", "")

            if name in CANONICAL_GSI_OVERRIDES:
                gsi, pot = CANONICAL_GSI_OVERRIDES[name]
                reason = f"user_override_{gsi}"
            elif best_place == "1":
                gsi, pot = 95, 95
                reason = "ballondor_winner_floor_95"
            elif best_place in ("2", "3", "4"):
                gsi, pot = 90, 90
                reason = f"ballondor_top4_rank_{best_place}_floor_90"
            else:
                gsi, pot = 85, 85
                reason = "legend_default_floor_85"

            for pid in pids:
                updates[pid] = (gsi, pot, reason)

    return updates
