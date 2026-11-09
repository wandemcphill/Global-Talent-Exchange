#!/usr/bin/env python3
"""GTEX Player Calibration, Deduplication & Market Supply Reconciliation.

Enforces:
1. Vitinha (PSG): Retains 91 GSI, Potential 94, not an icon/legend (tier: world_star). Retires duplicate Sportmonks card.
2. Evanilson (Bournemouth): Retains 81 GSI, Potential 86, not an icon/legend (tier: core). Decoupled from legend profile. Retires duplicate card.
3. Marquinhos (PSG): Retains 87 GSI, Potential 88, not an icon/legend (tier: world_star). Decoupled from legend profile. Retires duplicate Spartak card.
4. Taison (PAOK): Retains 82 GSI, Potential 82, not an icon/legend (tier: core). Decoupled from legend profile. Retires duplicate Metalist card.
5. Aleksey Batrakov (Lokomotiv Moscow): 78 GSI / 88 Potential wonderkid. Decoupled from legend profile. Retires fake PSG card.
6. Pierre Ismaelo Ganiou (RC Lens): CB, GSI 79 / Potential 87. Upgraded attributes.
7. Sani Suleiman (AS Trenčín): LW, secondary LM/RW/ST, GSI 78 / Potential 88. Upgraded pacy/dribbling/physical attributes.
8. Adamu Yakubu (LNZ Cherkasy): Canonical display name Adamu Yakubu, GSI 78 / Potential 87.
9. Active Players <= 33: Decoupled from legendary profiles (wonderkids like Moerstedt, Montoro, Echeverri, Uzun, Nyoni, Mheuka, and stars like Alisson, Ederson, Alex Sandro, Gerard Moreno, Willian, Jorginho, Danilo, Adama Traore).
10. Category 3 Cross-Provider Duplicates: Retires all duplicate Sportmonks cards where an active FM23/canonical card exists (Golovin, Soumaré, Bourigeaud, Zobnin, Terzic, Morita, Pessina, Özdemir, Simeone, Galeno, etc.).
11. Young Players Calibration: Calibrates top young talents (Endrick, Mainoo, Hato, Barcola, Gray, Fortea, Martinelli, Gadou, Cissè, Ekhator, Egboh, Adeoye, Edokpolor, Iheanacho, Orakpo, Ogundana, Akahomen, Campbell, Aguado, Salazar, Enzo Alves, Luis Guilherme) to FC26/27 ratings.
12. Market Supply Reconciliation: Sets circulating_shares = COALESCE(holdings, 0) across all active player share markets and summary_json read models, unlocking available units for immediate purchase.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
import psycopg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("gtex_calibration")

DEFAULT_DATABASE_URL = (
    os.environ.get("GTE_DATABASE_URL") or os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DATABASE_URL")
)

# Young wonderkids stuck at 64-72 GSI to upgrade to FC26/27 ratings
WONDERKID_UPGRADES = {
    # Endrick (Real Madrid) - 82 / 92
    "b1a44e9d-3cba-4cc7-ac4c-7d9129be13ea": (82, 92, "Endrick"),
    # Kobbie Mainoo (Manchester United) - 81 / 91
    "03c3599a-0949-429c-a863-5b271c6ebf05": (81, 91, "Kobbie Mainoo"),
    # Archie Gray (Tottenham) - 78 / 88
    "03b4b4ef-544c-4202-aa51-20f94660b0c4": (78, 88, "Archie Gray"),
    # Jorrel Hato (Ajax) - 81 / 89
    "4ef02fe4-89bc-4df9-af59-92cb2b44f530": (81, 89, "Jorrel Hato"),
    # Bradley Barcola (PSG) - 85 / 92
    "5d4e3a8e-52a3-4b3b-83e4-b71a27c10bab": (85, 92, "Bradley Barcola"),
    # Jesús Fortea (Real Madrid) - 76 / 89
    "5e0daffa-0cca-439f-80e9-eb2344c715d6": (76, 89, "Jesús Fortea"),
    # Tommaso Martinelli (Fiorentina) - 77 / 93
    "4d83d4c8-bce9-40a4-b43c-9e4d59017839": (77, 93, "Tommaso Martinelli"),
    # Joane Gadou (RB Salzburg) - 76 / 88
    "6df00445-5533-4324-bca2-0cc2796724dd": (76, 88, "Joane Gadou"),
    # Alphadjo Cissè (Hellas Verona) - 75 / 87
    "6fdc86c4-6cc3-48e3-9789-8f0a44f49a7c": (75, 87, "Alphadjo Cissè"),
    # Jeff Ekhator (Genoa) - 76 / 86
    "50649ae3-79f0-4a64-a8dc-f62aa387a792": (76, 86, "Jeff Ekhator"),
    # Shedrack Egboh (Mosta FC) - 76 / 86
    "47a27eb2-17f1-4db8-b57f-1d89e5a8716b": (76, 86, "Shedrack Egboh"),
    # Victor Adeoye (Sporting CP) - 75 / 85
    "9f7a3068-154a-43cf-be74-72ffb8bb8061": (75, 85, "Victor Adeoye"),
    # Peter Edokpolor (Red Bull Salzburg) - 76 / 86
    "6d135d18-f0e0-49cd-b4d1-665e3c5111ef": (76, 86, "Peter Edokpolor"),
    # Stanley Iheanacho (Midtjylland) - 76 / 86
    "739e961b-a7bd-43a9-b532-72f6320949b2": (76, 86, "Stanley Iheanacho"),
    # Victor Orakpo (Nice) - 76 / 86
    "66bed7c6-3bb5-478a-97bb-678b8934010e": (76, 86, "Victor Orakpo"),
    # Shola Ogundana (Flamengo) - 76 / 86
    "d9c483d5-5cbd-4f18-b6f9-7ca2b48cc953": (76, 86, "Shola Ogundana"),
    # Marvin Akahomen (Basel) - 77 / 92
    "6d5aed82-45d3-46e1-a7e0-23a276187510": (77, 92, "Marvin Akahomen"),
    # Cole Campbell (Borussia Dortmund) - 76 / 87
    "ecefebfe-ec35-472e-ac32-13ef01902ad4": (76, 87, "Cole Campbell"),
    # Diego Aguado (Real Madrid) - 75 / 86
    "530c48e5-b6a9-404a-bc65-6b1d34c03414": (75, 86, "Diego Aguado"),
    # Manuel Serrano Salazar (Real Madrid) - 75 / 86
    "0ff63a9c-68d7-4024-9f80-3ef46262b533": (75, 86, "Manuel Serrano Salazar"),
    # Enzo Alves (Real Madrid) - 77 / 90
    "218c73ff-cf84-465d-ba85-1bf4c5de7b47": (77, 90, "Enzo Alves"),
    # Luis Guilherme (West Ham) - 78 / 88
    "d92de50f-7189-41dd-bd53-b8d175912d22": (78, 88, "Luis Guilherme"),
}

# Duplicate Sportmonks player IDs to retire where a canonical FM23 or higher-rated card exists
SPORTMONKS_DUPLICATES_TO_RETIRE = [
    # Vitinha (Paris Saint-Germain Sportmonks 52 GSI duplicate)
    "f449a7ae-4dec-44a2-a013-16e02d6fb58e",
    # Aleksandr Golovin (Monaco Sportmonks 65 GSI duplicate)
    "8d5acdff-5076-4c32-b11d-3978de8186ca",
    # Boubakary Soumaré (Sportmonks 61 GSI duplicate)
    "ed657f35-000a-487c-aba2-62f58bcc49cb",
    # Benjamin Bourigeaud (Sportmonks duplicate)
    "8a1482d2-be45-46de-9fcd-9276467bbe29",
    # Roman Zobnin (Sportmonks duplicate)
    "7ae2654c-cae6-4097-b3e8-fb95c04ca776",
    # Aleksa Terzic (Sportmonks 61 GSI duplicate)
    "f7d6f51b-482a-41f7-88bc-d7ac01e83260",
    # Hidemasa Morita (Sportmonks 52 GSI duplicate)
    "f99c7508-e47d-45b8-9b32-dd5c57681371",
    # Matteo Pessina (Sportmonks 67 GSI duplicate)
    "900281ee-317a-4e21-8c2c-44b612fe160d",
    # Berat Özdemir (Sportmonks 55 GSI duplicate)
    "db3598a6-fd81-4d55-8d97-aea2a3663b29",
    # Giuliano Simeone (Sportmonks 67 GSI duplicate)
    "eb3a2579-ecfa-4e1a-b101-7ddc9b481edd",
    # Galeno (Sportmonks duplicate)
    "dfd3ae55-3428-4ca5-b9ed-d5ba735ee47f",
    # Trey Nyoni (Liverpool Sportmonks 66 GSI duplicate -> keep Sofifa 84 GSI)
    "0b749cf4-5ed5-43a8-ac19-3653424c0743",
    # Shumaira Mheuka (Chelsea duplicate -> keep canonical)
    "a51b1cfe-2abd-49dd-b4c9-a952a7fae5b4",
    # Darragh Lenihan (Sportmonks duplicate)
    "f647acf0-9591-4975-a6db-0263a3b8feec",
    # Robbie Brady (Sportmonks duplicate)
    "b6694ee6-5e5d-49ca-a367-50f4a2db4885",
    # Eoghan O'Connell (Sportmonks duplicate)
    "944ff907-59f8-4695-9260-ee0c13edead4",
    # Callum Brittain (Sportmonks duplicate)
    "b09b7fe1-87d8-4793-b7a7-d62b3d9778b9",
    # Omar Richards (Sportmonks duplicate)
    "433f1553-2cef-49cd-87b3-9f417c0d5b7c",
    # Bartosz Bereszynski (Sportmonks duplicate)
    "3122ef86-73b6-4e27-9f4d-a5df42f0c7f8",
    # Keiller (Sportmonks duplicate)
    "c833b092-8fcf-4441-8bec-ee46c7c7d583",
    # Gustavo Assunção (Sportmonks duplicate)
    "243f57a9-3be3-4da0-9719-121435d23ca9",
]

# Duplicate cards to retire for Batrakov, Marquinhos, Evanilson, Taison
SPECIFIC_DUPLICATES_TO_RETIRE = [
    # Alexey Batrakov (fake PSG card)
    "4db507e8-3e18-414b-9cbb-909b467ddfdf",
    # Marquinhos (duplicate Spartak Moskva card)
    "e0547ef1-441e-422e-8e9c-8a7d72987f7d",
    # Evanilson (duplicate 1. FC Köln card)
    "0e957fce-b1a1-4161-8ffb-155bdbb6e13f",
    # Taison (duplicate Metalist card)
    "a38bcc33-2b4b-4eea-aaec-e6ada32f4221",
]

# Legendary profile IDs to deactivate for active players 33 and under
LEGENDARY_PROFILES_TO_DEACTIVATE = [
    # Alexey Batrakov
    "81c70037-44ae-4335-94f4-217eaa0fb18d",
    # Evanilson
    "52a424d9-2348-4808-9588-65590011143e",
    # Marquinhos
    "d9a17c33-50cf-4192-b6ae-babd1a0057bf",
    # Taison
    "a38bcc33-2b4b-4eea-aaec-e6ada32f4221",
    # Max Moerstedt
    "f2bd5d2e-a401-44ba-b326-da60b0fc04f9",
    # Álvaro Montoro
    "2ee9b9c7-76f3-412b-99c0-d1f5953774bc",
    # Claudio Echeverri
    "900fd385-267f-4439-be0d-0ff51dda988b",
    # Can Uzun
    "60d20f5b-644a-4d2a-a5b0-7b8f2fe4bedc",
    # Shumaira Mheuka
    "dd67762f-b05f-494b-b1b9-cb65c5b473f8",
    # Trey Nyoni
    "ac877628-31b2-4443-9132-8424e1c8eb58",
    # Myles Lewis-Skelly
    "e5078de2-03a5-428a-b7ee-fec04db1eb6d",
    # Francis-Ikechukwu Onyeka
    "66c2e165-4e1b-4902-9b4f-8cbb7446ac72",
    # Daniel Yáñez Barla
    "9e4b3a56-d868-4c98-8b49-f78c98286b86",
    # Andrea Natali
    "67fff626-a29f-42de-b6b6-b3c2fa9762c2",
    # Jonah Kusi-Asare
    "6a93f5fd-5799-4894-87df-4a27b9aa3bcb",
    # Artem Stepanov
    "62d4ff9c-6d35-442b-90cf-18161ea3e8f9",
    # Max Joseph Schmitt
    "bddedd6b-ca89-413d-b218-e6d3d3971e19",
    # Rento Takaoka
    "8b684c08-5195-4685-9223-4fd0044c407a",
    # Juma Bah
    "7fa07e67-fb47-440e-9232-0c293c516304",
    # Sergi Domínguez Viloria
    "763ad785-d137-4792-a6d0-09afb247c111",
    # Tarek Buchmann
    "3b9959de-7335-4caf-94f8-3939204e702a",
    # Omari Kellyman
    "a37da7f3-6943-4cc5-9b34-fc16ae29c98c",
    # Daniel Rodríguez Crespo
    "ca7fc782-d0bf-4667-8a3f-355af29e2b29",
]


def run_calibrations_and_reconciliation(database_url: str | None = None):
    db_url = database_url or DEFAULT_DATABASE_URL
    if not db_url:
        raise SystemExit("A database URL is required. Provide --database-url or set GTE_DATABASE_URL/DATABASE_URL.")

    logger.info("=== STARTING GTEX PLAYER CALIBRATIONS & MARKET RECONCILIATION ===")
    conn = psycopg.connect(db_url)
    cur = conn.cursor()
    now = datetime.now(timezone.utc)

    try:
        # =========================================================================
        # 1. PIERRE ISMAELO GANIOU (CB, 79/87 GSI, Upgraded Attributes)
        # =========================================================================
        logger.info("--- 1. Updating Pierre Ismaelo Ganiou ---")
        p_ismaelo_id = "8e6f4c2f-445b-4660-81fd-ccf6afe33872"
        p_ismaelo_dna = {
            "pace": 77,
            "defending": 80,
            "physical": 80,
            "passing": 71,
            "dribbling": 69,
            "shooting": 45,
            "overall": 79,
            "potential": 87,
        }
        cur.execute(
            """
            UPDATE ingestion_players
            SET position = 'CB',
                normalized_position = 'CB',
                secondary_positions_json = '["LB", "RB"]'::json,
                governed_gsi = 79,
                governed_potential_gsi = 87,
                dna_profile = %s::jsonb,
                is_tradable = true,
                updated_at = %s
            WHERE id = %s
        """,
            (json.dumps(p_ismaelo_dna), now, p_ismaelo_id),
        )

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(summary_json::jsonb, '{position}', '"CB"'),
                            '{gsi}', '79'
                        ),
                        '{potential_gsi}', '87'
                    ),
                    '{dna_profile}', %s::jsonb
                ),
                '{attributes}', %s::jsonb
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (json.dumps(p_ismaelo_dna), json.dumps(p_ismaelo_dna), now, p_ismaelo_id),
        )

        # =========================================================================
        # 2. SANI SULEIMAN (LW, secondary LM/RW/ST, 78/88 GSI, Pacy/Dribbling/Physical)
        # =========================================================================
        logger.info("--- 2. Updating Sani Suleiman ---")
        s_suleiman_id = "d97a6eaa-af0a-4faa-81fd-a0e0fd89110f"
        s_suleiman_dna = {
            "pace": 89,
            "dribbling": 83,
            "physical": 81,
            "shooting": 76,
            "passing": 72,
            "defending": 44,
            "overall": 78,
            "potential": 88,
        }
        cur.execute(
            """
            UPDATE ingestion_players
            SET position = 'LW',
                normalized_position = 'LW',
                secondary_positions_json = '["LM", "RW", "ST"]'::json,
                governed_gsi = 78,
                governed_potential_gsi = 88,
                dna_profile = %s::jsonb,
                is_tradable = true,
                updated_at = %s
            WHERE id = %s
        """,
            (json.dumps(s_suleiman_dna), now, s_suleiman_id),
        )

        cur.execute("""
            UPDATE players
            SET name = 'Sani Suleiman',
                position = 'FW',
                overall = 78,
                potential = 88,
                pace = 89,
                dribbling = 83,
                physical = 81,
                shooting = 76,
                passing = 72,
                defending = 44
            WHERE player_id = 37635455
        """)

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(summary_json::jsonb, '{position}', '"LW"'),
                                '{secondary_positions}', '["LM", "RW", "ST"]'::jsonb
                            ),
                            '{gsi}', '78'
                        ),
                        '{potential_gsi}', '88'
                    ),
                    '{dna_profile}', %s::jsonb
                ),
                '{attributes}', %s::jsonb
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (json.dumps(s_suleiman_dna), json.dumps(s_suleiman_dna), now, s_suleiman_id),
        )

        # =========================================================================
        # 3. ADAMU YAKUBU (Display Name, 78/87 GSI)
        # =========================================================================
        logger.info("--- 3. Updating Adamu Yakubu ---")
        a_yakubu_id = "b61a32d8-b8f0-4eb6-b162-feddfd72cf02"
        a_yakubu_dna = {
            "pace": 76,
            "passing": 77,
            "physical": 80,
            "shooting": 68,
            "defending": 78,
            "dribbling": 75,
            "overall": 78,
            "potential": 87,
        }
        cur.execute(
            """
            UPDATE ingestion_players
            SET full_name = 'Adamu Yakubu',
                canonical_display_name = 'Adamu Yakubu',
                short_name = 'A. Yakubu',
                governed_gsi = 78,
                governed_potential_gsi = 87,
                dna_profile = %s::jsonb,
                is_tradable = true,
                updated_at = %s
            WHERE id = %s
        """,
            (json.dumps(a_yakubu_dna), now, a_yakubu_id),
        )

        cur.execute("""
            UPDATE players
            SET name = 'Adamu Yakubu',
                overall = 78,
                potential = 87,
                pace = 76,
                passing = 77,
                physical = 80,
                shooting = 68,
                defending = 78,
                dribbling = 75
            WHERE player_id = 37659140
        """)

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET player_name = 'Adamu Yakubu',
                summary_json = jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(summary_json::jsonb, '{player_name}', '"Adamu Yakubu"'),
                            '{canonical_display_name}', '"Adamu Yakubu"'
                        ),
                        '{gsi}', '78'
                    ),
                    '{potential_gsi}', '87'
                ),
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, a_yakubu_id),
        )

        # =========================================================================
        # 4. VITINHA (Retain 91 GSI, Potential 94, Paris Saint-Germain, NOT an icon)
        # =========================================================================
        logger.info("--- 4. Updating Vitinha (91 GSI / 94 Potential, PSG, World Star) ---")
        vitinha_id = "38304a42-8370-4871-8b86-6a32ac4f450a"
        cur.execute(
            """
            UPDATE ingestion_players
            SET governed_gsi = 91,
                governed_potential_gsi = 94,
                real_player_tier = 'world_star',
                legendary_profile_id = NULL,
                is_real_player = true,
                is_tradable = true,
                updated_at = %s
            WHERE id = %s
        """,
            (now, vitinha_id),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET total_shares = 200,
                circulating_shares = 0,
                status = 'active',
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, vitinha_id),
        )

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(summary_json::jsonb, '{gsi}', '91'),
                                '{potential_gsi}', '94'
                            ),
                            '{real_player_tier}', '"world_star"'
                        ),
                        '{is_legend}', 'false'
                    ),
                    '{badge}', 'null'::jsonb
                ),
                '{circulating_shares}', '0'
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (now, vitinha_id),
        )

        # =========================================================================
        # 5. EVANILSON (Retain 81 GSI, Potential 86, AFC Bournemouth, NOT an icon)
        # =========================================================================
        logger.info("--- 5. Updating Evanilson (81 GSI / 86 Potential, Bournemouth) ---")
        evanilson_canonical_id = "c6c6a580-376d-4f99-8f63-8385f6d8966b"
        cur.execute(
            """
            UPDATE ingestion_players
            SET governed_gsi = 81,
                governed_potential_gsi = 86,
                real_player_tier = 'core',
                legendary_profile_id = NULL,
                is_real_player = true,
                is_tradable = true,
                real_world_club_name = 'AFC Bournemouth',
                updated_at = %s
            WHERE id = %s
        """,
            (now, evanilson_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET total_shares = 400,
                circulating_shares = 0,
                status = 'active',
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, evanilson_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(summary_json::jsonb, '{gsi}', '81'),
                                '{potential_gsi}', '86'
                            ),
                            '{real_player_tier}', '"core"'
                        ),
                        '{is_legend}', 'false'
                    ),
                    '{badge}', 'null'::jsonb
                ),
                '{circulating_shares}', '0'
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (now, evanilson_canonical_id),
        )

        # =========================================================================
        # 6. MARQUINHOS (Retain 87 GSI, Potential 88, Paris Saint-Germain, NOT an icon)
        # =========================================================================
        logger.info("--- 6. Updating Marquinhos (87 GSI / 88 Potential, PSG) ---")
        marquinhos_canonical_id = "e918697b-db3e-4e68-98e5-7b6cb4dba804"
        cur.execute(
            """
            UPDATE ingestion_players
            SET governed_gsi = 87,
                governed_potential_gsi = 88,
                real_player_tier = 'world_star',
                legendary_profile_id = NULL,
                is_real_player = true,
                is_tradable = true,
                real_world_club_name = 'Paris Saint-Germain',
                updated_at = %s
            WHERE id = %s
        """,
            (now, marquinhos_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET total_shares = 200,
                circulating_shares = 0,
                status = 'active',
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, marquinhos_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(summary_json::jsonb, '{gsi}', '87'),
                                '{potential_gsi}', '88'
                            ),
                            '{real_player_tier}', '"world_star"'
                        ),
                        '{is_legend}', 'false'
                    ),
                    '{badge}', 'null'::jsonb
                ),
                '{circulating_shares}', '0'
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (now, marquinhos_canonical_id),
        )

        # =========================================================================
        # 7. TAISON (Retain 82 GSI, Potential 82, PAOK, NOT an icon)
        # =========================================================================
        logger.info("--- 7. Updating Taison (82 GSI / 82 Potential, PAOK) ---")
        taison_canonical_id = "db3f2ab5-ce7a-48fb-87ea-a158d56fb036"
        cur.execute(
            """
            UPDATE ingestion_players
            SET governed_gsi = 82,
                governed_potential_gsi = 82,
                real_player_tier = 'core',
                legendary_profile_id = NULL,
                is_real_player = true,
                is_tradable = true,
                real_world_club_name = 'PAOK',
                updated_at = %s
            WHERE id = %s
        """,
            (now, taison_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET total_shares = 400,
                circulating_shares = 0,
                status = 'active',
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, taison_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(summary_json::jsonb, '{gsi}', '82'),
                                '{potential_gsi}', '82'
                            ),
                            '{real_player_tier}', '"core"'
                        ),
                        '{is_legend}', 'false'
                    ),
                    '{badge}', 'null'::jsonb
                ),
                '{circulating_shares}', '0'
            ),
            updated_at = %s
            WHERE player_id = %s
        """,
            (now, taison_canonical_id),
        )

        # =========================================================================
        # 8. ALEKSEY BATRAKOV (78 GSI / 88 Potential, Lokomotiv Moscow, Wonderkid)
        # =========================================================================
        logger.info("--- 8. Updating Aleksey Batrakov (78 GSI / 88 Potential, Lokomotiv Moscow) ---")
        batrakov_canonical_id = "c9454cf4-2ee3-43c6-9aff-b9c2baf97a75"
        batrakov_dna = {
            "pace": 81,
            "passing": 82,
            "dribbling": 81,
            "shooting": 76,
            "defending": 64,
            "physical": 71,
            "overall": 78,
            "potential": 88,
        }
        cur.execute(
            """
            UPDATE ingestion_players
            SET full_name = 'Aleksey Batrakov',
                canonical_display_name = 'Aleksey Batrakov',
                real_world_club_name = 'Lokomotiv Moscow',
                position = 'AM',
                normalized_position = 'AM',
                secondary_positions_json = '["CM"]'::json,
                governed_gsi = 78,
                governed_potential_gsi = 88,
                dna_profile = %s::jsonb,
                real_player_tier = 'wonderkid',
                legendary_profile_id = NULL,
                is_real_player = true,
                is_tradable = true,
                updated_at = %s
            WHERE id = %s
        """,
            (json.dumps(batrakov_dna), now, batrakov_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET total_shares = 400,
                circulating_shares = 0,
                status = 'active',
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, batrakov_canonical_id),
        )

        cur.execute(
            """
            UPDATE player_summary_read_models
            SET player_name = 'Aleksey Batrakov',
                summary_json = jsonb_set(
                    jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    jsonb_set(
                                        jsonb_set(summary_json::jsonb, '{gsi}', '78'),
                                        '{potential_gsi}', '88'
                                    ),
                                    '{real_player_tier}', '"wonderkid"'
                                ),
                                '{is_legend}', 'false'
                            ),
                            '{badge}', '"Wonderkid"'
                        ),
                        '{current_club_name}', '"Lokomotiv Moscow"'
                    ),
                    '{circulating_shares}', '0'
                ),
                updated_at = %s
            WHERE player_id = %s
        """,
            (now, batrakov_canonical_id),
        )

        # =========================================================================
        # 9. DEACTIVATE FAKE LEGEND PROFILES FOR ACTIVE PLAYERS <= 33 & WONDERKIDS
        # =========================================================================
        logger.info("--- 9. Deactivating %d fake legend profiles ---", len(LEGENDARY_PROFILES_TO_DEACTIVATE))
        cur.execute(
            """
            UPDATE legendary_player_profiles
            SET is_active = false,
                catalogue_status = 'retired',
                updated_at = %s
            WHERE id = ANY(%s)
        """,
            (now, LEGENDARY_PROFILES_TO_DEACTIVATE),
        )

        # Decouple any player linked to these deactivated profiles
        cur.execute(
            """
            UPDATE ingestion_players
            SET legendary_profile_id = NULL,
                updated_at = %s
            WHERE legendary_profile_id = ANY(%s)
        """,
            (now, LEGENDARY_PROFILES_TO_DEACTIVATE),
        )

        # =========================================================================
        # 10. RETIRE DUPLICATE CARDS (Sportmonks duplicates & specific fake cards)
        # =========================================================================
        all_retirements = list(set(SPORTMONKS_DUPLICATES_TO_RETIRE + SPECIFIC_DUPLICATES_TO_RETIRE))
        logger.info("--- 10. Retiring %d duplicate player cards ---", len(all_retirements))

        cur.execute(
            """
            UPDATE ingestion_players
            SET is_tradable = false,
                real_player_tier = 'archived_duplicate',
                legendary_profile_id = NULL,
                updated_at = %s
            WHERE id = ANY(%s)
        """,
            (now, all_retirements),
        )

        cur.execute(
            """
            UPDATE player_share_markets
            SET status = 'retired',
                circulating_shares = 0,
                updated_at = %s
            WHERE player_id = ANY(%s)
        """,
            (now, all_retirements),
        )

        cur.execute(
            """
            DELETE FROM player_summary_read_models
            WHERE player_id = ANY(%s)
        """,
            (all_retirements,),
        )

        # Update canonical cards for pairs whose Sportmonks duplicate was retired:
        # Aleksandr Golovin: Update club to AS Monaco, GSI 80 / Potential 82
        cur.execute(
            """
            UPDATE ingestion_players
            SET full_name = 'Aleksandr Golovin',
                canonical_display_name = 'Aleksandr Golovin',
                real_world_club_name = 'AS Monaco',
                governed_gsi = 80,
                governed_potential_gsi = 82,
                updated_at = %s
            WHERE id = '5251e866-09c8-4e8d-a116-56a310f3a8f1'
        """,
            (now,),
        )
        cur.execute("""
            UPDATE player_summary_read_models
            SET player_name = 'Aleksandr Golovin',
                summary_json = jsonb_set(
                    jsonb_set(
                        jsonb_set(summary_json::jsonb, '{current_club_name}', '"AS Monaco"'),
                        '{gsi}', '80'
                    ),
                    '{potential_gsi}', '82'
                )
            WHERE player_id = '5251e866-09c8-4e8d-a116-56a310f3a8f1'
        """)

        # Roman Zobnin: Update club to Spartak Moskva, GSI 79
        cur.execute(
            """
            UPDATE ingestion_players
            SET real_world_club_name = 'Spartak Moskva',
                governed_gsi = 79,
                governed_potential_gsi = 79,
                updated_at = %s
            WHERE id = '83e860fd-fbbd-4afe-b89d-5fb12020f52b'
        """,
            (now,),
        )

        # Hidemasa Morita: Update club to Sporting CP, GSI 81
        cur.execute(
            """
            UPDATE ingestion_players
            SET real_world_club_name = 'Sporting CP',
                governed_gsi = 81,
                governed_potential_gsi = 81,
                updated_at = %s
            WHERE id = '989fedfc-1cc1-4fbc-b2c5-e0975fca3434'
        """,
            (now,),
        )

        # Matteo Pessina: Update club to Monza, GSI 81
        cur.execute(
            """
            UPDATE ingestion_players
            SET real_world_club_name = 'Monza',
                governed_gsi = 81,
                governed_potential_gsi = 81,
                updated_at = %s
            WHERE id = 'ecb3d65a-ddb2-437f-9afd-f7c9ebb933a2'
        """,
            (now,),
        )

        # =========================================================================
        # 11. UPGRADE YOUNG PLAYERS STUCK AT 64-72 GSI (FC26/27 RATINGS)
        # =========================================================================
        logger.info("--- 11. Upgrading %d top young talents to FC26/27 ratings ---", len(WONDERKID_UPGRADES))
        for pid, (gsi, pot, name) in WONDERKID_UPGRADES.items():
            cur.execute(
                """
                UPDATE ingestion_players
                SET governed_gsi = %s,
                    governed_potential_gsi = %s,
                    real_player_tier = CASE WHEN %s >= 85 THEN 'world_star' ELSE 'wonderkid' END,
                    is_tradable = true,
                    updated_at = %s
                WHERE id = %s
            """,
                (gsi, pot, gsi, now, pid),
            )

            cur.execute(
                """
                UPDATE player_summary_read_models
                SET summary_json = jsonb_set(
                    jsonb_set(
                        jsonb_set(summary_json::jsonb, '{gsi}', %s::text::jsonb),
                        '{potential_gsi}', %s::text::jsonb
                    ),
                    '{potential}', %s::text::jsonb
                ),
                updated_at = %s
                WHERE player_id = %s
            """,
                (json.dumps(gsi), json.dumps(pot), json.dumps(pot), now, pid),
            )

        # =========================================================================
        # 12. MARKET SUPPLY RECONCILIATION (Unlock All Available Shares)
        # =========================================================================
        logger.info("--- 12. Reconciling Market Supply (circulating_shares = actual user holdings) ---")
        # Step 12a: In player_share_markets, set circulating_shares = actual holdings sum
        cur.execute(
            """
            UPDATE player_share_markets psm
            SET circulating_shares = COALESCE(h.held_total, 0),
                total_shares = CASE WHEN psm.total_shares <= 0 THEN 400 ELSE psm.total_shares END,
                updated_at = %s
            FROM player_share_markets psm_orig
            LEFT JOIN (
                SELECT player_id, SUM(share_count) as held_total
                FROM player_share_holdings
                GROUP BY player_id
            ) h ON psm_orig.player_id = h.player_id
            WHERE psm.player_id = psm_orig.player_id
              AND psm.status = 'active'
              AND psm.circulating_shares != COALESCE(h.held_total, 0)
        """,
            (now,),
        )
        logger.info("Reconciled %d active markets in player_share_markets.", cur.rowcount)

        # Step 12b: Sync circulating_shares, total_shares, and available_shares in player_summary_read_models
        cur.execute(
            """
            UPDATE player_summary_read_models psrm
            SET summary_json = jsonb_set(
                jsonb_set(
                    jsonb_set(
                        psrm.summary_json::jsonb,
                        '{circulating_shares}',
                        to_jsonb(COALESCE(psm.circulating_shares, 0))
                    ),
                    '{total_shares}',
                    to_jsonb(psm.total_shares)
                ),
                '{available_shares}',
                to_jsonb(GREATEST(0, psm.total_shares - COALESCE(psm.circulating_shares, 0)))
            ),
            updated_at = %s
            FROM player_share_markets psm
            WHERE psrm.player_id = psm.player_id
              AND psm.status = 'active'
              AND (
                (psrm.summary_json->>'circulating_shares')::int != COALESCE(psm.circulating_shares, 0)
                OR (psrm.summary_json->>'total_shares')::int != psm.total_shares
                OR (psrm.summary_json->>'available_shares')::int != (psm.total_shares - COALESCE(psm.circulating_shares, 0))
              )
        """,
            (now,),
        )
        logger.info(
            "Synced %d player summary read models with accurate circulating, total, and available shares.", cur.rowcount
        )

        # Commit everything atomically
        conn.commit()
        logger.info("=== SUCCESS: ALL CALIBRATIONS AND RECONCILIATIONS COMMITTED ATOMICALLY ===")

    except Exception as e:
        conn.rollback()
        logger.error("Error occurred, rolled back transaction: %s", e)
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="GTEX Player Calibration, Deduplication & Market Supply Reconciliation."
    )
    parser.add_argument(
        "--database-url",
        default=DEFAULT_DATABASE_URL,
        help="Database connection URL. Defaults to GTE_DATABASE_URL or DATABASE_URL.",
    )
    args = parser.parse_args()
    run_calibrations_and_reconciliation(database_url=args.database_url)
