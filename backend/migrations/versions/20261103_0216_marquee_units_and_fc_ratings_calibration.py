"""Calibrate active player FC ratings, fix available units, and configure Harry Kane.

Revision ID: 20261103_0216_marquee_units_and_fc_ratings_calibration
Revises: 20261103_0215_kaka_saka_neymar_legends_and_runnr_portraits
Create Date: 2026-11-03 05:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261103_0216_marquee_units_and_fc_ratings_calibration"
down_revision = "20261103_0215_kaka_saka_neymar_legends_and_runnr_portraits"
branch_labels = None
depends_on = None

# Superstars with authentic EA Sports FC calibration: (name, cur, pot, dob, norm_pos, sec_pos_json, ids)
SUPERSTAR_CALIBRATION = [
    (
        "Kylian Mbappé",
        91,
        94,
        "1998-12-20",
        "ST",
        '["ST", "CF", "LW"]',
        ["64b8ed47-c422-4b03-a0f6-c8bfef31aa35"],
    ),
    (
        "Rodri",
        91,
        91,
        "1996-06-22",
        "CDM",
        '["CDM", "CM"]',
        [
            "5f79b913-9e1f-4735-93b0-b3ce2c4d9577",
            "46707639-3e2f-4ea0-9b18-4e268d5fc3e5",
        ],
    ),
    (
        "Erling Haaland",
        91,
        94,
        "2000-07-21",
        "ST",
        '["ST", "CF"]',
        [
            "4b1549cc-9aa6-4429-bf10-4ffd56656e63",
            "1fb93a01-efcd-4b36-8152-b6bda9515a47",
            "3d18f24e-3539-4abe-911c-98877c07f24a",
        ],
    ),
    (
        "Vinícius Júnior",
        90,
        94,
        "2000-07-12",
        "LW",
        '["LW", "ST", "LM"]',
        [
            "42e150d2-dafe-4fd4-8c96-6bf0844893a6",
            "b89bf448-982b-4cfb-86cc-1525eb4e70d1",
        ],
    ),
    (
        "Jude Bellingham",
        90,
        94,
        "2003-06-29",
        "CAM",
        '["CAM", "CM"]',
        [
            "574f0bc7-7878-40b3-ac11-627d7071e344",
            "517f060d-ea68-49f1-9e94-ddb3e5265585",
        ],
    ),
    (
        "Kevin De Bruyne",
        90,
        90,
        "1991-06-28",
        "CM",
        '["CM", "CAM"]',
        [
            "72baf131-8754-4356-8517-3106cd4c5d4e",
            "8da7661e-425e-4bdc-a3f5-7f433a137b53",
        ],
    ),
    (
        "Mohamed Salah",
        89,
        89,
        "1992-06-15",
        "RW",
        '["RW", "RM"]',
        [
            "df370379-7c76-42fd-916f-0148736b3919",
            "4a30088c-414d-4830-9c0a-792e53846750",
        ],
    ),
    (
        "Thibaut Courtois",
        89,
        89,
        "1992-05-11",
        "GK",
        '["GK"]',
        [
            "0fb47397-8e40-4f65-ad37-fd0760515e03",
            "8ae00cde-200a-4977-8e87-168005381ca0",
        ],
    ),
    (
        "Martin Ødegaard",
        89,
        90,
        "1998-12-17",
        "CAM",
        '["CAM", "CM"]',
        ["840f3c12-0fb7-44df-b36d-22956f9bd05e"],
    ),
    (
        "Virgil van Dijk",
        89,
        89,
        "1991-07-08",
        "CB",
        '["CB"]',
        ["4d17082b-81bb-441b-b37b-063cd182c246"],
    ),
    (
        "Alisson",
        89,
        89,
        "1992-10-02",
        "GK",
        '["GK"]',
        ["b5dacfbf-30e5-457f-9fa3-69cb6e86731b"],
    ),
    (
        "Lautaro Martínez",
        89,
        90,
        "1997-08-22",
        "ST",
        '["ST", "CF"]',
        [
            "3703b7a3-3818-4323-bb31-16b9859bb139",
            "7e252c63-b3ae-4b76-bb35-f21c43b4aeea",
        ],
    ),
    (
        "Florian Wirtz",
        88,
        92,
        "2003-05-03",
        "CAM",
        '["CAM", "RW"]',
        [
            "48614a50-f44f-4f19-bbd4-34b52f0a0cc3",
            "219a9266-53e0-40f3-bd0b-6b2328661a30",
        ],
    ),
    (
        "Phil Foden",
        88,
        91,
        "2000-05-28",
        "RW",
        '["RW", "CAM", "LW"]',
        [
            "6e02c92b-f97d-475a-9c0b-64b69471b9fe",
            "e4531612-1457-47b8-8685-889d58b8a587",
        ],
    ),
    (
        "Federico Valverde",
        88,
        90,
        "1998-07-22",
        "CM",
        '["CM", "RW"]',
        ["4a2b1337-8870-41cc-a365-57b1b1bdb6f8"],
    ),
    (
        "Bernardo Silva",
        88,
        88,
        "1994-08-10",
        "CM",
        '["CM", "RW"]',
        [
            "5f961c24-015a-4088-80b7-9c781c95af97",
            "3625dca5-b6db-4761-ba28-32e1124101d0",
        ],
    ),
    (
        "Robert Lewandowski",
        88,
        88,
        "1988-08-21",
        "ST",
        '["ST"]',
        [
            "bc7ec6df-0763-4606-a2a4-21ea47dbf685",
            "c1a1f90f-0b11-4054-b98c-5397cc7dc2a9",
        ],
    ),
    (
        "Rúben Dias",
        88,
        89,
        "1997-05-14",
        "CB",
        '["CB"]',
        ["23e4eace-561b-42bb-b80c-4c609ee2e0d3"],
    ),
    (
        "Bukayo Saka",
        87,
        90,
        "2001-09-05",
        "RW",
        '["RW", "RM"]',
        [
            "f4b4531b-a342-48b5-8f43-618cfa0dc49a",
            "c02852d3-656f-49d8-bcb2-f83234525e27",
        ],
    ),
    (
        "William Saliba",
        87,
        91,
        "2001-03-24",
        "CB",
        '["CB"]',
        [
            "6dcbd148-e1a5-4be0-855f-06f2afa01c6c",
            "442ba7f0-334d-4ef0-9a6d-2313b56c1f04",
        ],
    ),
    (
        "Declan Rice",
        87,
        89,
        "1999-01-14",
        "CDM",
        '["CDM", "CM"]',
        ["bcf4a070-c621-48d1-aeca-b017253b4f24"],
    ),
    (
        "Nicolò Barella",
        87,
        87,
        "1997-02-07",
        "CM",
        '["CM"]',
        [
            "130fe326-887f-4cde-8130-9c909a5fdcbf",
            "5346b6d0-2b75-45b8-b9d1-f22bd6bb7f8e",
        ],
    ),
    (
        "Cole Palmer",
        87,
        92,
        "2002-05-06",
        "CAM",
        '["CAM", "RW"]',
        ["7d8283e6-d7f3-421a-bba1-a99bf76a4228"],
    ),
    (
        "Jamal Musiala",
        87,
        93,
        "2003-02-26",
        "CAM",
        '["CAM", "CM"]',
        ["8da7038b-6a83-4cf0-9218-ba5de2c7477d"],
    ),
    (
        "Victor Osimhen",
        87,
        89,
        "1998-12-29",
        "ST",
        '["ST"]',
        [
            "cd6eaa94-3e3a-4187-bc2c-8ec16f2be165",
            "2dc62da9-550b-423b-bfe3-445de565051e",
        ],
    ),
    (
        "Bruno Fernandes",
        87,
        87,
        "1994-09-08",
        "CAM",
        '["CAM", "CM"]',
        [
            "ba3d04ec-078b-4be0-9fdc-ecd15313a049",
            "6f5cc20f-fb59-4c6a-ba8c-b715504a6075",
        ],
    ),
    (
        "Eduardo Camavinga",
        86,
        91,
        "2002-11-10",
        "CM",
        '["CM", "CDM", "LB"]',
        [
            "c477a7c3-8c72-4534-a13a-f26cb82953de",
            "685b8558-8aed-488b-9f81-0f496b72657e",
        ],
    ),
    (
        "Aurélien Tchouaméni",
        86,
        89,
        "2000-01-27",
        "CDM",
        '["CDM", "CM"]',
        [
            "aa8e2d25-a9ea-4e94-ab75-b46f4186ffc9",
            "bb27b6f9-ada8-4929-bb00-1a67e1ea4395",
        ],
    ),
    (
        "Trent Alexander-Arnold",
        86,
        88,
        "1998-10-07",
        "RB",
        '["RB", "RWB"]',
        [
            "b6843650-2a0b-4b63-8ff4-b0af7aeb3509",
            "e211be2d-c14c-460c-ac2e-9834d2f50c90",
        ],
    ),
    (
        "Ousmane Dembélé",
        86,
        87,
        "1997-05-15",
        "RW",
        '["RW", "LW"]',
        [
            "4e7ae637-9a9a-435e-8151-d6cfa2962c3e",
            "379bb246-c951-44e8-8584-fd8dbe1e4cc1",
        ],
    ),
    (
        "Khvicha Kvaratskhelia",
        86,
        90,
        "2001-02-12",
        "LW",
        '["LW"]',
        ["b4a864a0-e8e2-476c-8dfa-c390e842d96a"],
    ),
    (
        "Andrew Robertson",
        85,
        85,
        "1994-03-11",
        "LB",
        '["LB"]',
        [
            "5bd14e17-20c6-468e-9c87-e0a5e8d8e997",
            "cfb3b2ad-11ed-4bbb-ad9b-7a1ca1f1742c",
        ],
    ),
    (
        "Kingsley Coman",
        84,
        84,
        "1996-06-13",
        "LM",
        '["LM", "LW", "RM"]',
        [
            "bbb54792-5c78-449e-8d9a-fccbfd06922f",
            "84fa6bd1-779d-4074-9318-4bce54787ffa",
        ],
    ),
    (
        "Leon Goretzka",
        83,
        83,
        "1995-02-06",
        "CM",
        '["CM", "CDM"]',
        [
            "26b863cd-f64b-4d98-91ce-87432efde4af",
            "b62d2957-06d5-4a86-9631-0e038e9a6ea8",
        ],
    ),
    (
        "Ivan Toney",
        80,
        80,
        "1996-03-16",
        "ST",
        '["ST"]',
        ["de9feb52-e745-4a26-a70a-753165181f15"],
    ),
    (
        "Moussa Dembélé",
        75,
        75,
        "1996-07-12",
        "ST",
        '["ST"]',
        [
            "77e51ece-7b79-47f3-a88f-33004d26d28f",
            "7286e299-ccde-4cdc-a372-4080963f8945",
        ],
    ),
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # =========================================================================
    # PHASE 1: INGESTION_PLAYERS CALIBRATION
    # =========================================================================

    # 1. Harry Kane: CF/ST/AM, age 32, rating 90
    conn.execute(sa.text("""
        UPDATE ingestion_players
        SET date_of_birth = '1993-07-28',
            factual_date_of_birth = '1993-07-28',
            position = 'CF/ST/AM',
            normalized_position = 'ST',
            secondary_positions_json = CAST('["CF", "ST", "CAM", "AM"]' AS json),
            governed_gsi = 90,
            governed_potential_gsi = 90,
            gsi_override_reason = 'fc25_27_calibration',
            real_player_tier = 'marquee',
            dna_profile = CAST(jsonb_set(
                jsonb_set(
                    jsonb_set(COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb)), '{overall}', CAST('90' AS jsonb)),
                    '{current_rating}', CAST('90' AS jsonb)
                ),
                '{potential_rating}', CAST('90' AS jsonb)
            ) AS json)
        WHERE id IN ('50235403-679f-48c8-88a0-7614e76ccc0e', '0b429e4e-3588-4e05-aed4-70015f211585')
           OR full_name = 'Harry Kane';
    """))

    # 2. Top active superstars calibration in ingestion_players
    for (
        name,
        cur_r,
        pot_r,
        dob,
        n_pos,
        s_pos,
        explicit_ids,
    ) in SUPERSTAR_CALIBRATION:
        if explicit_ids:
            conn.execute(
                sa.text("""
                UPDATE ingestion_players
                SET governed_gsi = :cur_gsi,
                    governed_potential_gsi = :pot_gsi,
                    gsi_override_reason = 'fc25_27_calibration',
                    date_of_birth = COALESCE(:dob, date_of_birth),
                    factual_date_of_birth = COALESCE(:dob, factual_date_of_birth),
                    normalized_position = COALESCE(:norm_pos, normalized_position),
                    secondary_positions_json = COALESCE(CAST(:sec_pos AS json), secondary_positions_json),
                    real_player_tier = CASE WHEN :cur_gsi >= 85 THEN 'marquee' ELSE 'established' END,
                    dna_profile = CAST(jsonb_set(
                        jsonb_set(COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb)), '{overall}', to_jsonb(CAST(:cur_gsi AS int))),
                        '{current_rating}', to_jsonb(CAST(:cur_gsi AS int))
                    ) AS json)
                WHERE id = ANY(:ids);
            """),
                {
                    "cur_gsi": cur_r,
                    "pot_gsi": pot_r,
                    "dob": dob,
                    "norm_pos": n_pos,
                    "sec_pos": s_pos,
                    "ids": explicit_ids,
                },
            )

    # 3. All remaining players stamped with 'legend_default_floor_85' or marquee with NULL governed_gsi
    conn.execute(sa.text("""
        UPDATE ingestion_players
        SET governed_gsi = CAST(dna_profile->>'current_rating' AS int),
            governed_potential_gsi = GREATEST(
                COALESCE(CAST(dna_profile->>'potential_rating' AS int), CAST(dna_profile->>'current_rating' AS int)),
                CAST(dna_profile->>'current_rating' AS int)
            ),
            gsi_override_reason = 'dna_profile_calibrated',
            real_player_tier = CASE 
                WHEN CAST(dna_profile->>'current_rating' AS int) >= 85 THEN 'marquee' 
                ELSE 'established' 
            END
        WHERE (gsi_override_reason = 'legend_default_floor_85' OR (real_player_tier = 'marquee' AND governed_gsi IS NULL))
          AND dna_profile->>'current_rating' IS NOT NULL
          AND CAST(dna_profile->>'current_rating' AS int) > 0
          AND real_player_tier != 'regen'
          AND is_real_player = true;
    """))

    # =========================================================================
    # PHASE 2: PLAYER_SHARE_MARKETS CALIBRATION & UNITS
    # =========================================================================

    # 4. Harry Kane markets
    conn.execute(sa.text("""
        UPDATE player_share_markets
        SET total_shares = 200,
            released_shares = 200,
            circulating_shares = 0,
            status = 'active',
            updated_at = NOW()
        WHERE player_id IN ('50235403-679f-48c8-88a0-7614e76ccc0e', '0b429e4e-3588-4e05-aed4-70015f211585');
    """))

    # 5. Superstar explicit markets
    for (
        name,
        cur_r,
        pot_r,
        dob,
        n_pos,
        s_pos,
        explicit_ids,
    ) in SUPERSTAR_CALIBRATION:
        if explicit_ids:
            conn.execute(
                sa.text("""
                UPDATE player_share_markets
                SET status = 'active',
                    total_shares = CASE WHEN :cur_gsi >= 85 THEN GREATEST(total_shares, 200) ELSE GREATEST(total_shares, 400) END,
                    released_shares = CASE WHEN :cur_gsi >= 85 THEN GREATEST(total_shares, 200) ELSE GREATEST(total_shares, 400) END,
                    circulating_shares = 0
                WHERE player_id = ANY(:ids)
                  AND player_id != '192e748c-a21e-4c00-9f1b-2a122bae06a9';
            """),
                {"cur_gsi": cur_r, "ids": explicit_ids},
            )

    # 6. Set available units on all marquee players in player_share_markets
    conn.execute(sa.text("""
        UPDATE player_share_markets
        SET status = 'active',
            total_shares = GREATEST(total_shares, 200),
            released_shares = GREATEST(total_shares, 200),
            circulating_shares = 0,
            updated_at = NOW()
        WHERE player_id IN (
            SELECT id FROM ingestion_players
            WHERE real_player_tier = 'marquee'
              AND is_tradable = true
              AND id != '192e748c-a21e-4c00-9f1b-2a122bae06a9'
        );
    """))

    # 7. Ensure all genuine historical legends in player_share_markets are active, tradeable, and have 1 unit available
    conn.execute(sa.text("""
        UPDATE player_share_markets
        SET status = 'active',
            total_shares = 1,
            released_shares = 1,
            circulating_shares = 0,
            updated_at = NOW()
        WHERE player_id IN (
            SELECT id FROM ingestion_players
            WHERE real_player_tier = 'legend'
              AND is_tradable = true
              AND is_real_player = true
              AND id != '192e748c-a21e-4c00-9f1b-2a122bae06a9'
        );
    """))

    # 8. Re-activate accidentally retired active established player markets
    conn.execute(sa.text("""
        UPDATE player_share_markets
        SET status = 'active',
            total_shares = GREATEST(total_shares, 400),
            released_shares = GREATEST(total_shares, 400),
            circulating_shares = 0,
            updated_at = NOW()
        WHERE status = 'retired'
          AND player_id IN (
            SELECT id FROM ingestion_players
            WHERE real_player_tier = 'established'
              AND is_tradable = true
              AND id != '192e748c-a21e-4c00-9f1b-2a122bae06a9'
        );
    """))


def downgrade() -> None:
    pass
