"""Enforce wonderkid deduplication, age capped at 21, and Pau Cubarsi face portrait.

Revision ID: 20261103_0209_enforce_wonderkid_dedup_and_age_cap
Revises: 20261102_0208_upload_wonderkids_portraits_to_cloudinary
Create Date: 2026-11-03 00:50:00
"""

from __future__ import annotations

import json
from alembic import op
import sqlalchemy as sa

revision = "20261103_0209_enforce_wonderkid_dedup_and_age_cap"
down_revision = "20261102_0208_upload_wonderkids_portraits_to_cloudinary"
branch_labels = None
depends_on = None

# Redundant duplicate player IDs to delete
DUPLICATE_PLAYER_IDS = [
    "fc4cb742-9356-42ee-97ce-d7bf32f86e69",
    "73cf01a3-2497-4bc8-9b2c-fd4d9cbf2bc1",
    "155accf2-d9c4-42a9-861c-0b67d6c270e1",
    "9cafb0a1-8e59-4985-a6b7-21e055b3fa23",
    "5f4ea530-0c1f-4329-aaf2-4918264473f5",
    "6f0b4701-6651-49df-ab7f-55848367f83d",
    "56bd6511-1e1a-46f4-9b13-27f4dfd6bde6",
    "67555782-b7b1-4157-b538-91e3240f21cc",
    "d4e75f9a-5f2a-44c5-bfaf-db88ab41ad67",
    "c607e5e3-640a-4156-8fcc-f6a97a69f5ce",
    "5233f9e3-6175-4e03-aff4-4a2dab1aed5c",
    "a4a3e037-c04b-4a78-bb81-39c508d10b53",
    "7d36551d-f4ad-4ebf-bcf3-5fb4d4122887",
    "0f7bdb9d-467a-4a51-a0b1-ee046a63b5ba",
    "1f955ab2-601a-4890-9d74-dac324ba61a1",
    "1fdfc02d-f7e6-400b-8ca2-2caaa6fcb989",
    "7a4588b3-c72a-4e26-a8ae-7f401762b166",
    "4b348d42-2d18-4a70-8b09-fa936fcfb839",
    "b4c4832d-2098-4c12-9cbb-c51dcb5f2a96",
    "9eb8d5df-6a3a-4934-8c43-bc06d6e7bf79",
    "50c7fc01-eb44-4822-a7d1-cf199e8d6411",
    "d8d17a7a-c454-4632-bd83-f36cfec0a693",
    "e656e18f-a94f-4a00-ab64-42b789178224",
    "f947ee06-d731-4115-b778-9e58e0a4f5ca",
    "df48df51-7ba8-4c6e-8ee5-1e355c2d385a",
    "4a8e1b57-69be-44ce-af96-3023e10fa14d",
    "ef050db4-2fcb-4e12-8e68-07e5fe5ba6e7",
    "ba7764d8-796d-4952-b883-faee9048a608",
    "dd516f40-d9da-46aa-b2b9-e48f72390a06",
    "9ff1d533-8ea8-46d4-8d96-c95a07dd3a2f",
    "c1c73be4-8f69-42b3-93d3-7d52a2ea1293",
    "a062c3b5-78e7-4954-a95e-149ffb892a0d",
    "2285a81e-1f74-4b53-b097-42289f688047",
    "21659a84-0a69-4d6c-829b-a7eb20077ee4",
    "c2966847-f5dc-42be-a37a-4cbf3519c670",
    "6b71f9cf-ff25-4a6c-94fb-7ef3f9479b12",
    "348128c9-ff37-4d87-9b2f-98c4d293f9ef",
    "c4a962a2-cb36-4074-b5a8-42fc69830823",
    "9963e792-5eb3-47d0-8f99-e64e9e51f845",
    "bb81f7ba-c71c-4389-9851-bcfa159be246",
    "d8ae2199-52e6-42d4-bb3f-3dc2d9ea12d0",
    "eb459f23-0103-490d-959c-ddbe3fdb5be9",
    "4a2f8ab4-3580-4cf9-93eb-bafe91e77f0a",
    "9a038f2a-7af5-4f40-bf78-959453c52a0a",
    "ab0546c-8afb-4f8c-b36a-766b0ae6d540",
    "74b1fd6d-a4ba-4cd9-ad21-ef169a2e378d",
    "efbf4bfd-5d4f-4c9c-8d7c-5bdde4ffd947",
    "122c9d84-fb18-430d-9739-e3d1c0148aae",
    "5260c853-cdd6-4e51-9026-2319b39abb7f",
    "10921e64-7d61-4ff9-bbb3-63ab2b4715da",
    "c0843527-8b8b-40ee-8792-4c7162e58cc7",
    "0f1054c1-9bb2-465d-a5f3-9937286f8366",
    "1556b6b2-4028-41bd-a249-1224f4c8fe40",
    "6f31b032-bc8e-46a5-88be-b67144351075",
    "62db60ee-9276-44e7-b7b1-551da7113623",
    "909be77b-dda0-413c-9503-98dde6b3d096",
    "31610e47-a352-4208-abdb-35f5f369270b",
    "bf0c68d5-cc40-4e70-a2ea-39dfa7d7d62b",
    "294bf4ca-674a-4b53-8861-2d287c5c3a78",
    "1510568c-7f91-45e8-847c-6f8c74dc8e35",
    "3e264726-d15b-4955-9c30-2d2d927217ed",
    "b2fa5b7d-d213-4848-adc6-1e8d5cf6cc4c",
    "b162bc73-f940-4799-9cca-dc3c51c41458",
]

# Senior players (aged >= 23) reassigned from wonderkid to established
REASSIGN_ESTABLISHED_IDS = [
    "4e3ec46e-27ac-4da9-b6bb-3e382f0c6a2d",
    "da454649-3ed9-4ed9-a49f-ab8002d53a33",
    "87efd7e2-723c-49ba-9fcf-532cd485e8ba",
    "b48192b3-f4ca-4912-9d35-352725282f57",
    "f40d6fac-4736-4fe6-b10c-7edcbb379e66",
    "83967c16-7fc1-448f-bee6-e48585657169",
    "7edead40-f8de-4bfd-933d-a994c98101ee",
    "0cc8e889-2d5d-4bd3-88cb-c7235c4c62cd",
    "da2d3215-886e-4b4b-9dc1-09ff43840014",
    "70b4b57c-028e-43c1-bcc3-2c49d1837a48",
    "c5b8c7b9-1438-44a7-90e2-3a4a710ab68a",
    "b79cc826-28c7-43c4-91a4-7653c03f454f",
    "7d9b7ae3-2b61-4914-b700-b688c49f9a74",
    "1035073a-a9ef-4115-8bec-95ebd18cdc6c",
    "05ec9f42-f543-4ce9-9b65-7291726702da",
    "f25f0b14-fcf4-4e75-8c75-2917004a3ddb",
    "bcd5ae0e-afaa-441c-9d98-0c73a667d5a9",
    "377431f7-27c8-411a-a66c-f7bf545eed61",
    "168c0e12-3698-466d-9c3e-651c6091573b",
    "160d5ffa-7aec-4aeb-846a-896fbf9622b7",
    "b68428c4-17fe-41ef-96fd-2a630f92c025",
    "0f3b69c0-b7d2-43c6-beed-b56f69142de9",
    "f960b7db-1bf5-4b3b-baff-9fa03dfb63bd",
    "14fab584-e1fe-41d0-8479-64b671b0c15f",
    "339c9c26-c4f9-4ef5-8b67-294f5eff9a3f",
    "23c37349-7e97-474d-b758-8e3131fd29d9",
    "73777cf2-50e6-410a-bd93-45860b2a173d",
    "01e72b86-9e86-429d-bce4-7add5529d08f",
    "d4bc4a09-f679-4227-8ca2-d2f20ecaaa28",
    "5b436412-0a19-44a4-bdc5-67ada11f3403",
    "a6767f5d-d8b1-4b91-b0bf-8cd4be625a47",
    "467add42-d11f-4688-b4d5-9858f3a953ff",
]

# Wonderkids clamped to 2005 (age 21)
CLAMP_AGE_21_MAP = {
    "50df4978-e1db-40f1-a564-21c37c160a04": "2005-08-04",
    "e9e150e0-872c-47ad-932e-8cdc500d0dc9": "2005-05-06",
    "823b33db-2822-4624-bc41-9f4731cc7406": "2005-07-27",
    "bb9b29b2-f4c7-468d-bc3f-b1a9e2090f00": "2005-08-04",
    "85607f34-35af-4ce6-a7d2-ca1b25a2aec5": "2005-02-16",
    "14d9be6e-78c6-4b72-9324-4ea274a2c25a": "2005-08-26",
    "83b8df79-e6e8-4a2d-b7ca-41c2ecc0b0c0": "2005-02-03",
    "c4da752a-19a9-41e0-adc3-5e3c6e4cfc9c": "2005-01-12",
    "5e914ea1-fc5d-4f75-a974-1dfb1c1e18d1": "2005-05-01",
    "59cbcaf7-07cf-4ad4-a912-4b6dfd52e60d": "2005-04-24",
    "ea11dddc-e58e-493a-ae09-0b3c853fd765": "2005-07-10",
    "eab25a64-2751-4d70-9e55-82b332a2ced5": "2005-07-23",
    "cbdc8711-2a3b-4d42-9328-ddb9e4a533b2": "2005-02-17",
    "f1f7b587-3504-40f7-bf1a-73b90c7d28c9": "2005-04-25",
    "4fa3e473-5efd-4361-b1f9-7cf9eba91fed": "2005-02-11",
    "2ac8a578-d1d7-4e00-8ba8-63f1f87cc7b8": "2005-05-05",
    "b1b8c832-a97f-4d54-97b4-3b43f27af494": "2005-06-19",
    "c960e75a-20ac-4f7f-a912-bc9d634debcf": "2005-10-12",
    "06516707-9d1a-4236-a544-840b4afe5f3e": "2005-01-09",
    "ab457ad3-77b1-4f77-98a5-a2ad78000c57": "2005-03-10",
    "9e36624d-91a2-4f5f-8d89-f258e45902c3": "2005-12-29",
    "df7c641c-57d5-42bf-8335-f7823066556a": "2005-11-19",
    "ea6acc9b-8e0d-450d-9734-a4f7466104a8": "2005-12-05",
    "a9f91082-bbf4-455d-b2a3-20dd93db8bf2": "2005-11-30",
}

# Wonderkids with missing DOB populated
SET_NULL_DOB_MAP = {
    "c0b79f2c-61bc-4629-a8df-924726312044": "2007-04-30",
    "040084ba-f131-4c52-bd8d-0842e9f7e865": "2007-05-05",
    "7828e81f-32c2-4941-904b-74e6fd5d604e": "2007-06-15",
}

CUBARSI_ID = "323765c4-43db-46ad-b289-3a7704147854"
CUBARSI_FACE_URL = (
    "https://res.cloudinary.com/dvxiniqew/image/upload/v1793662546/players/wonderkids/wk_323765c4_pau_cubarsi_face.jpg"
)


def upgrade() -> None:
    conn = op.get_bind()
    is_postgres = conn.dialect.name == "postgresql"
    if not is_postgres:
        return

    insp = sa.inspect(conn)
    tables = set(insp.get_table_names())

    # 1. Update Pau Cubarsi face portrait
    if "ingestion_players" in tables:
        dna_patch = json.dumps(
            {
                "portraitUrl": CUBARSI_FACE_URL,
                "image_url": CUBARSI_FACE_URL,
                "portraitStatus": "ready",
                "portraitSourceProvider": "transfermarkt_face_portrait",
            }
        ).replace("'", "''")

        op.execute(f"""
            UPDATE ingestion_players
            SET
                dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{dna_patch}' AS jsonb))::json,
                updated_at = NOW()
            WHERE id = '{CUBARSI_ID}';
        """)

    if "ingestion_player_image_metadata" in tables:
        op.execute(f"""
            DELETE FROM ingestion_player_image_metadata WHERE player_id = '{CUBARSI_ID}' AND image_role = 'portrait';
            INSERT INTO ingestion_player_image_metadata (
                id, player_id, source_provider, provider_external_id,
                image_role, source_url, moderation_status, rights_cleared,
                is_primary, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), '{CUBARSI_ID}', 'transfermarkt_face_portrait', '{CUBARSI_ID}',
                'portrait', '{CUBARSI_FACE_URL}', 'approved', true,
                true, NOW(), NOW()
            );
        """)

    if "player_summary_read_models" in tables:
        sum_patch = json.dumps(
            {
                "image_url": CUBARSI_FACE_URL,
                "portrait_url": CUBARSI_FACE_URL,
                "portrait_status": "ready",
            }
        ).replace("'", "''")

        op.execute(f"""
            UPDATE player_summary_read_models
            SET
                summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{sum_patch}' AS jsonb))::json,
                updated_at = NOW()
            WHERE player_id = '{CUBARSI_ID}';
        """)

    # 2. Delete duplicate records
    for did in DUPLICATE_PLAYER_IDS:
        if "ingestion_player_image_metadata" in tables:
            op.execute(f"DELETE FROM ingestion_player_image_metadata WHERE player_id = '{did}';")
        if "player_summary_read_models" in tables:
            op.execute(f"DELETE FROM player_summary_read_models WHERE player_id = '{did}';")
        if "ingestion_players" in tables:
            op.execute(f"DELETE FROM ingestion_players WHERE id = '{did}';")

    # 3. Reassign senior players to 'established'
    for pid in REASSIGN_ESTABLISHED_IDS:
        patch = json.dumps({"tier": "established", "real_player_tier": "established"}).replace("'", "''")
        if "ingestion_players" in tables:
            op.execute(f"""
                UPDATE ingestion_players
                SET real_player_tier = 'established',
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{patch}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE id = '{pid}';
            """)
        if "player_summary_read_models" in tables:
            op.execute(f"""
                UPDATE player_summary_read_models
                SET summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{patch}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = '{pid}';
            """)

    # 4. Clamp wonderkids born in 2004 to age 21
    for pid, new_dob in CLAMP_AGE_21_MAP.items():
        patch = json.dumps({"age": 21, "date_of_birth": new_dob}).replace("'", "''")
        if "ingestion_players" in tables:
            op.execute(f"""
                UPDATE ingestion_players
                SET date_of_birth = '{new_dob}',
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{patch}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE id = '{pid}';
            """)
        if "player_summary_read_models" in tables:
            op.execute(f"""
                UPDATE player_summary_read_models
                SET summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{patch}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = '{pid}';
            """)

    # 5. Populate NULL DOBs
    for pid, new_dob in SET_NULL_DOB_MAP.items():
        patch = json.dumps({"date_of_birth": new_dob}).replace("'", "''")
        if "ingestion_players" in tables:
            op.execute(f"""
                UPDATE ingestion_players
                SET date_of_birth = '{new_dob}',
                    dna_profile = (COALESCE(CAST(dna_profile AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{patch}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE id = '{pid}';
            """)
        if "player_summary_read_models" in tables:
            op.execute(f"""
                UPDATE player_summary_read_models
                SET summary_json = (COALESCE(CAST(summary_json AS jsonb), CAST('{{}}' AS jsonb)) || CAST('{patch}' AS jsonb))::json,
                    updated_at = NOW()
                WHERE player_id = '{pid}';
            """)


def downgrade() -> None:
    pass
