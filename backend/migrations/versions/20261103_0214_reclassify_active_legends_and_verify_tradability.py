"""Reclassify active players from legend tier to marquee/established and verify legend tradability.

Revision ID: 20261103_0214_reclassify_active_legends_and_verify_tradability
Revises: 20261103_0213_update_edokpolor_yohanna_and_desktop_portraits
Create Date: 2026-11-03 04:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261103_0214_reclassify_active_legends_and_verify_tradability"
down_revision = "20261103_0213_update_edokpolor_yohanna_and_desktop_portraits"
branch_labels = None
depends_on = None

# Active FM23 players mistakenly ingested with real_player_tier = 'legend'
ACTIVE_FM23_PLAYER_IDS = [
    "5f79b913-9e1f-4735-93b0-b3ce2c4d9577",  # Rodri (Man City)
    "0fb47397-8e40-4f65-ad37-fd0760515e03",  # Thibaut Courtois
    "de9feb52-e745-4a26-a70a-753165181f15",  # Ivan Toney
    "f9ecfb64-a7b0-4718-abb9-d8426f34f3bc",  # Piotr Zielinski
    "5bd14e17-20c6-468e-9c87-e0a5e8d8e997",  # Andrew Robertson
    "890f2134-b9b8-411d-aec3-a2236dc9590d",  # Sergej Milinkovic-Savic
    "b0b1846b-1dd4-480d-8261-86aeddd93e90",  # Milan Skriniar
    "73659cd8-10e8-4d41-886e-e3b33c839f68",  # Jose Gaya
    "491602eb-7cb6-4fa0-aeb9-603041d7c16b",  # Marcos Llorente
    "bd65c112-ca88-4fd2-8b93-b8af1a8c20ad",  # Aymeric Laporte
    "1d9937d2-a462-4bd4-889b-f6dce155acc2",  # Adrien Rabiot
    "bbb54792-5c78-449e-8d9a-fccbfd06922f",  # Kingsley Coman
    "26b863cd-f64b-4d98-91ce-87432efde4af",  # Leon Goretzka
    "aed52552-d17e-4c2c-99f2-bc3406476aa5",  # Julian Brandt
    "d91322df-947d-49dd-a3b4-686097747d90",  # Arkadiusz Milik
    "6a0d9f47-21c9-45eb-9752-58db83c170d6",  # Florian Miguel
    "0968c794-0859-493f-98b3-bb6c009ccf78",  # Petr Sevcik
    "81d65ee8-aa9e-419b-9cc7-07d8f432020b",  # James Ward-Prowse
    "1b6dfb98-417f-4e99-9efc-46df169d1bcf",  # Isi Palazon
    "12f64ea4-1ee3-48ac-adc6-9e322e3f122e",  # Pablo Fornals
]

# Direct active player profiles in legendary_player_profiles to deactivate
ACTIVE_LPP_PROFILE_IDS = [
    "f05353da-de12-4b51-83dd-28b851cfa6ba",  # Kylian Mbappé
    "b6bb0d2c-fd58-45eb-ba1f-c25f8a7aae82",  # Rodri (Rodrigo Hernández)
    "d613d0c7-7f27-40dd-82bd-db1b59834506",  # Rodri
    "65d74d40-a83e-4b0e-b868-37f54ce381da",  # Moussa Dembélé
    "b2630dbe-d822-4de2-9b92-10203384f5d0",  # Ousmane Dembélé
    "653d4ad6-638e-427f-95c3-0ce42270c621",  # Mousa Dembélé
    "06d974f5-2500-4d9c-baa4-267dcd0775ce",  # Mohamed Salah
    "0b616cc0-c26d-4644-b9a4-4cfc173ebe72",  # Phil Foden
    "2ee7af7e-cfa0-4506-88ed-ba0edfdc0dbc",  # Philip Walter Foden
    "0d1b24f6-b487-4ce9-b8e3-5cd5c550c266",  # Bruno Fernandes
    "4261a1db-1dfb-4689-b261-e0677c6ac546",  # Viktor Gyökeres
    "70488550-e95f-4c9c-ad9a-2f023069401a",  # Martin Ødegaard
    "780980ed-ed3d-4942-be43-566a4cc2c791",  # Alphonso Davies
    "8d99c07b-1bea-4983-8725-dba1d88dbe1b",  # Eberechi Eze
    "8f4e3906-16f4-4ac0-911c-08a1a731834d",  # Lautaro Martínez
    "de8e8fdb-9e52-4222-a57b-f534ff636f9a",  # James Maddison
    "eabaaac5-26dd-4ecb-b9a5-d8098d5e6bf9",  # Nicolò Barella
    "eb5b7a70-0f1c-4457-a9dc-32134a8d0659",  # Kieran Tierney
    "3154f9d7-c743-4a08-8831-09da8cc0182f",  # Rodrigo De Paul
    "81f7b879-b846-437b-a87d-2e95d70dff5e",  # Rodrigo Javier de Paul
    "8fae4b71-c32d-4e84-b035-56cf58d4e43d",  # Bruno Guimarães
    "dbee4b9b-c247-406a-a431-ea44c3d40b63",  # Rodrigo Bentancur
]

# Duplicate inactive legend copies that should remain untradable
DUPLICATE_LEGEND_IDS = [
    "0704b985-6e51-49fc-bf74-45820da69183",  # duplicate Figo (Lyon)
    "106bbc0a-a8b3-408e-b856-a4dad15799fd",  # duplicate Cantona (Lyon)
    "55f70b9b-dae9-4a55-8721-ccf9bdaa0154",  # duplicate Iniesta (Barca duplicate)
    "862d907b-917a-4508-a19d-da3481ae778d",  # duplicate Emerson (Roma)
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # 1. Deactivate active player profiles in legendary_player_profiles linked to active provider records
    conn.execute(
        sa.text("""
        UPDATE legendary_player_profiles lpp
        SET is_active = false,
            is_searchable = false,
            is_tradable = false,
            updated_at = NOW()
        FROM ingestion_players ip
        WHERE ip.legendary_profile_id = lpp.id
          AND (
              ip.source_provider IN ('sportmonks', 'sofifa_fc25')
              OR ip.id = ANY(:active_fm_ids)
          );
    """),
        {"active_fm_ids": ACTIVE_FM23_PLAYER_IDS},
    )

    # 2. Deactivate known direct active player profiles in legendary_player_profiles
    conn.execute(
        sa.text("""
        UPDATE legendary_player_profiles
        SET is_active = false,
            is_searchable = false,
            is_tradable = false,
            updated_at = NOW()
        WHERE id = ANY(:active_lpp_ids);
    """),
        {"active_lpp_ids": ACTIVE_LPP_PROFILE_IDS},
    )

    # 3. Reclassify active Sportmonks and Sofifa FC 25 players to marquee / established
    conn.execute(sa.text("""
        UPDATE ingestion_players
        SET real_player_tier = CASE 
                WHEN COALESCE(governed_gsi, 80) >= 85 THEN 'marquee'
                ELSE 'established'
            END,
            legendary_profile_id = NULL,
            is_tradable = true,
            updated_at = NOW()
        WHERE source_provider IN ('sportmonks', 'sofifa_fc25')
          AND real_player_tier = 'legend'
          AND real_player_tier != 'regen'
          AND is_real_player = true;
    """))

    # 4. Reclassify active FM23 players to marquee / established
    conn.execute(
        sa.text("""
        UPDATE ingestion_players
        SET real_player_tier = CASE 
                WHEN id IN (
                    '5f79b913-9e1f-4735-93b0-b3ce2c4d9577', -- Rodri
                    '0fb47397-8e40-4f65-ad37-fd0760515e03', -- Courtois
                    '5bd14e17-20c6-468e-9c87-e0a5e8d8e997'  -- Robertson
                ) THEN 'marquee'
                ELSE 'established'
            END,
            legendary_profile_id = NULL,
            is_tradable = true,
            updated_at = NOW()
        WHERE id = ANY(:active_fm_ids);
    """),
        {"active_fm_ids": ACTIVE_FM23_PLAYER_IDS},
    )

    # 5. Clear legendary_profile_id linkage on all non-legend players (e.g. Mbappé, Rodri, etc.)
    conn.execute(sa.text("""
        UPDATE ingestion_players
        SET legendary_profile_id = NULL,
            updated_at = NOW()
        WHERE real_player_tier != 'legend'
          AND legendary_profile_id IS NOT NULL;
    """))

    # 6. Ensure all genuine historical legends in ingestion_players are tradeable and buyable
    conn.execute(
        sa.text("""
        UPDATE ingestion_players
        SET is_tradable = true,
            updated_at = NOW()
        WHERE real_player_tier = 'legend'
          AND id != ALL(:dup_ids)
          AND real_player_tier != 'regen'
          AND is_real_player = true;
    """),
        {"dup_ids": DUPLICATE_LEGEND_IDS},
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # Downgrade re-enables active profiles if needed
    conn.execute(
        sa.text("""
        UPDATE legendary_player_profiles
        SET is_active = true,
            is_searchable = true,
            is_tradable = true,
            updated_at = NOW()
        WHERE id = ANY(:active_lpp_ids);
    """),
        {"active_lpp_ids": ACTIVE_LPP_PROFILE_IDS},
    )
