"""Update Peter Edokpolor, Zadok Yohanna and assign desktop Cloudinary portraits.

Revision ID: 20261103_0213_update_edokpolor_yohanna_and_desktop_portraits
Revises: 20261103_0212_ingest_afcon_senior_internationals
Create Date: 2026-11-03 04:25:00.000000

"""

import json
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20261103_0213_update_edokpolor_yohanna_and_desktop_portraits"
down_revision = "20261103_0212_ingest_afcon_senior_internationals"
branch_labels = None
depends_on = None

UPDATES = [
    {
        "id": "6d135d18-f0e0-49cd-b4d1-665e3c5111ef",
        "name": "Peter Edokpolor",
        "position": "ST",
        "normalized_position": "ST",
        "secondary_positions": ["CF"],
        "real_world_club_name": "SL Benfica",
        "height_cm": 192,
        "preferred_foot": "Right",
        "governed_gsi": 72,
        "governed_potential_gsi": 81,
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676060/players/portraits/p_6d135d18_peter_edokpolor.jpg",
        "playstyle": "Explosive Striker (Pace & Dribbling)",
        "skills": ["Pace", "Dribbling", "Acceleration", "Finishing"],
        "attributes": {
            "pace": 16,
            "acceleration": 16,
            "sprint_speed": 16,
            "dribbling": 15,
            "agility": 15,
            "finishing": 14,
            "heading": 15,
            "jumping": 15,
            "strength": 15,
        },
    },
    {
        "id": "eff52911-6eed-4834-ab1c-a86cb4b6525a",
        "name": "Zadok Yohanna",
        "position": "RW",
        "normalized_position": "RW",
        "secondary_positions": ["RM", "LW", "ST"],
        "real_world_club_name": "Brighton & Hove Albion",
        "height_cm": 184,
        "preferred_foot": "Left",
        "governed_gsi": 77,
        "governed_potential_gsi": 86,
        "date_of_birth": "2008-06-29",
        "age": 18,
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676070/players/portraits/p_eff52911_zadok_yohanna.jpg",
        "playstyle": "Explosive Inverted Winger (Pace & Dribbling)",
        "skills": ["Pace", "Dribbling", "Flair", "Finishing"],
    },
    {
        "id": "b61a32d8-b8f0-4eb6-b162-feddfd72cf02",
        "name": "Adam Yakubu",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676049/players/portraits/p_b61a32d8_adam_yakubu.jpg",
    },
    {
        "id": "528b3f8c-4197-4d71-9b77-c1cbb08ec46d",
        "name": "Emmanuel Ayaosi",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676052/players/portraits/p_528b3f8c_emmanuel_ayaosi.jpg",
    },
    {
        "id": "78929e0a-ba3f-4d48-bc58-e14421a3558c",
        "name": "Gift Orban",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676055/players/portraits/p_78929e0a_gift_orban.png",
    },
    {
        "id": "97bc9cc6-c22d-4470-aec5-91729a57b947",
        "name": "Jeremy Monga",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676058/players/portraits/p_97bc9cc6_jeremy_monga.jpg",
    },
    {
        "id": "47a27eb2-17f1-4db8-b57f-1d89e5a8716b",
        "name": "Shedrack Egboh",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676062/players/portraits/p_47a27eb2_shedrack_egboh.jpg",
    },
    {
        "id": "739e961b-a7bd-43a9-b532-72f6320949b2",
        "name": "Stanley Iheanacho",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676065/players/portraits/p_739e961b_stanley_iheanacho.jpg",
    },
    {
        "id": "9f7a3068-154a-43cf-be74-72ffb8bb8061",
        "name": "Victor Adeoye",
        "portrait": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793676067/players/portraits/p_9f7a3068_victor_adeoye.jpg",
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    for item in UPDATES:
        pid = item["id"]
        portrait = item["portrait"]

        # 1. Update ingestion_players
        if "ingestion_players" in tables:
            set_clauses = []
            params = {}

            if "position" in item:
                set_clauses.append("position = :pos")
                params["pos"] = item["position"]
            if "normalized_position" in item:
                set_clauses.append("normalized_position = :norm_pos")
                params["norm_pos"] = item["normalized_position"]
            if "secondary_positions" in item:
                set_clauses.append("secondary_positions_json = CAST(:sec_pos AS json)")
                params["sec_pos"] = json.dumps(item["secondary_positions"])
            if "real_world_club_name" in item:
                set_clauses.append("real_world_club_name = :club")
                params["club"] = item["real_world_club_name"]
            if "height_cm" in item:
                set_clauses.append("height_cm = :height")
                params["height"] = item["height_cm"]
            if "preferred_foot" in item:
                set_clauses.append("preferred_foot = :foot")
                params["foot"] = item["preferred_foot"]
            if "governed_gsi" in item:
                set_clauses.append("governed_gsi = :gsi")
                params["gsi"] = item["governed_gsi"]
            if "governed_potential_gsi" in item:
                set_clauses.append("governed_potential_gsi = :pot_gsi")
                set_clauses.append("potential = :pot_gsi")
                params["pot_gsi"] = item["governed_potential_gsi"]
            if "date_of_birth" in item:
                set_clauses.append("date_of_birth = CAST(:dob AS date)")
                params["dob"] = item["date_of_birth"]

            dna_patch = {
                "portraitUrl": portrait,
                "image_url": portrait,
                "portraitStatus": "ready",
                "portraitSourceProvider": "cloudinary",
            }
            if "position" in item:
                dna_patch["position"] = item["position"]
            if "secondary_positions" in item:
                dna_patch["secondary_positions"] = item["secondary_positions"]
            if "height_cm" in item:
                dna_patch["height_cm"] = item["height_cm"]
            if "preferred_foot" in item:
                dna_patch["preferred_foot"] = item["preferred_foot"]
            if "governed_gsi" in item:
                dna_patch["overall"] = item["governed_gsi"]
                dna_patch["current_rating"] = item["governed_gsi"]
            if "governed_potential_gsi" in item:
                dna_patch["potential"] = item["governed_potential_gsi"]
                dna_patch["potential_rating"] = item["governed_potential_gsi"]
            if "date_of_birth" in item:
                dna_patch["date_of_birth"] = item["date_of_birth"]
            if "age" in item:
                dna_patch["age"] = item["age"]
            if "playstyle" in item:
                dna_patch["playstyle"] = item["playstyle"]
            if "skills" in item:
                dna_patch["skills"] = item["skills"]
            if "attributes" in item:
                dna_patch["attributes"] = item["attributes"]

            set_clauses.append(
                "dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{}' AS jsonb)) || CAST(:dna_patch AS jsonb))::json"
            )
            params["dna_patch"] = json.dumps(dna_patch)

            set_clauses.append("updated_at = NOW()")
            params["pid"] = pid

            op.execute(
                sa.text(f"UPDATE ingestion_players SET {', '.join(set_clauses)} WHERE id = :pid").bindparams(**params)
            )

        # 2. Update player_summary_read_models
        if "player_summary_read_models" in tables:
            sum_clauses = [
                "summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{}' AS jsonb)) || CAST(:sum_patch AS jsonb))::json"
            ]
            sum_patch = {
                "image_url": portrait,
                "portrait_url": portrait,
                "portrait_status": "ready",
            }
            if "position" in item:
                sum_patch["position"] = item["position"]
            if "secondary_positions" in item:
                sum_patch["secondary_positions"] = item["secondary_positions"]
            if "real_world_club_name" in item:
                sum_patch["real_world_club_name"] = item["real_world_club_name"]
            if "height_cm" in item:
                sum_patch["height_cm"] = item["height_cm"]
            if "preferred_foot" in item:
                sum_patch["preferred_foot"] = item["preferred_foot"]
            if "governed_gsi" in item:
                sum_patch["gsi"] = item["governed_gsi"]
                sum_patch["overall"] = item["governed_gsi"]
            if "governed_potential_gsi" in item:
                sum_patch["potential"] = item["governed_potential_gsi"]
            if "age" in item:
                sum_patch["age"] = item["age"]
            if "playstyle" in item:
                sum_patch["playstyle"] = item["playstyle"]
            if "skills" in item:
                sum_patch["skills"] = item["skills"]

            sum_params = {
                "sum_patch": json.dumps(sum_patch),
                "pid": pid,
            }
            if "real_world_club_name" in item:
                sum_clauses.append("current_club_name = :club_name")
                sum_params["club_name"] = item["real_world_club_name"]
            sum_clauses.append("updated_at = NOW()")

            op.execute(
                sa.text(
                    f"UPDATE player_summary_read_models SET {', '.join(sum_clauses)} WHERE player_id = :pid"
                ).bindparams(**sum_params)
            )

        # 3. Upsert ingestion_player_image_metadata
        if "ingestion_player_image_metadata" in tables:
            op.execute(
                sa.text(
                    "DELETE FROM ingestion_player_image_metadata WHERE player_id = :pid AND image_role = 'portrait'"
                ).bindparams(pid=pid)
            )
            op.execute(sa.text("""
                    INSERT INTO ingestion_player_image_metadata (
                        id, player_id, source_provider, provider_external_id, image_role, source_url,
                        moderation_status, rights_cleared, is_primary, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid()::varchar, :pid, 'cloudinary', :pid, 'portrait', :portrait,
                        'approved', true, true, NOW(), NOW()
                    )
                    """).bindparams(pid=pid, portrait=portrait))


def downgrade() -> None:
    pass
