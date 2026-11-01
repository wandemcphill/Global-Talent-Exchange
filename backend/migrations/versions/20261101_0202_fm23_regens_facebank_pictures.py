"""Assign nationality and ethnicity-matched facebank pictures to FM23 regens.

Enforces:
1. Every FM23 regen introduced to the game receives a facebank picture.
2. The portrait strictly matches the regen's nationality/ethnicity.
3. Assets are chosen deterministically from the approved Cloudinary facebank.
4. Quarantined players (Ryan Matos 2002088877) never receive portraits.
5. Preserves existing real photos for verified active wonderkids.

Revision ID: 20261101_0202_fm23_regens_facebank_pictures
Revises: 20261101_0201_legend_generational_ages
"""

from __future__ import annotations

import json
from pathlib import Path
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite

revision = "20261101_0202_fm23_regens_facebank_pictures"
down_revision = "20261101_0201_legend_generational_ages"
branch_labels = None
depends_on = None

MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "generated_media"
    / "regen_newgen_faces"
    / "manifest.json"
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "ingestion_players" not in tables or not MANIFEST_PATH.exists():
        return

    from scripts.assign_fm23_regen_facebank_portraits import FaceBankIndex

    index = FaceBankIndex(MANIFEST_PATH)
    is_postgres = bind.dialect.name == "postgresql"

    # Query candidate players:
    # 1. source_provider = 'fm23_genie_scout' AND real_player_tier = 'regen'
    # 2. Or provider_external_id starting with '2002' missing portrait
    # 3. Exclude Ryan Matos (2002088877)
    country_join = ""
    country_cols = "NULL as country_name, NULL as alpha2_code, NULL as alpha3_code"
    if "ingestion_countries" in tables:
        country_join = "LEFT JOIN ingestion_countries c ON p.country_id = c.id"
        country_cols = "c.name as country_name, c.alpha2_code, c.alpha3_code"

    query_str = f"""
        SELECT 
            p.id, 
            p.provider_external_id, 
            p.dna_profile, 
            p.real_player_tier,
            {country_cols}
        FROM ingestion_players p
        {country_join}
        WHERE p.source_provider = 'fm23_genie_scout'
          AND p.provider_external_id != '2002088877'
          AND p.id != 'c1a2dddc-9b29-482f-ba06-0b39763830ba'
          AND (
              p.real_player_tier = 'regen'
              OR (
                  p.provider_external_id LIKE '2002%'
                  AND (
                      p.dna_profile IS NULL 
                      OR p.dna_profile->>'portraitUrl' IS NULL 
                      OR p.dna_profile->>'portraitUrl' = ''
                      OR p.dna_profile->>'portraitStatus' = 'missing'
                  )
              )
          )
    """

    candidates = bind.execute(sa.text(query_str)).mappings().all()

    for row in candidates:
        player_id = row["id"]
        provider_id = row["provider_external_id"]
        raw_dna = row["dna_profile"]
        if isinstance(raw_dna, str):
            try:
                dna = json.loads(raw_dna)
            except Exception:
                dna = {}
        elif isinstance(raw_dna, dict):
            dna = raw_dna
        else:
            dna = {}

        # If already has a real CDN image from sportmonks or transfermarkt, do not overwrite
        existing_url = str(dna.get("portraitUrl") or "")
        if "sportmonks" in existing_url or "transfermarkt" in existing_url:
            continue

        payload = index.build_regen_portrait_payload(
            player_id=player_id,
            provider_external_id=provider_id,
            dna_profile=dna,
            country_name=row.get("country_name"),
            country_code=row.get("alpha2_code") or row.get("alpha3_code"),
        )
        if not payload:
            continue

        updated_dna_json = json.dumps(payload["dna_profile"])

        # Update ingestion_players dna_profile
        bind.execute(
            sa.text(
                "UPDATE ingestion_players SET dna_profile = :dna WHERE id = :id"
            ).bindparams(
                sa.bindparam("dna", updated_dna_json, type_=sa.JSON if not is_postgres else postgresql.JSONB),
                sa.bindparam("id", player_id),
            )
        )

        # Upsert ingestion_player_image_metadata
        if "ingestion_player_image_metadata" in tables:
            img = payload["image_metadata"]
            if is_postgres:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO ingestion_player_image_metadata (
                            id, source_provider, provider_external_id, player_id,
                            image_role, source_url, storage_key, width, height,
                            mime_type, file_size_bytes, checksum_sha256,
                            moderation_status, rights_cleared, is_primary, last_processed_at
                        ) VALUES (
                            gen_random_uuid()::text, :src_prov, :prov_ext_id, :pid,
                            :role, :src_url, :storage_key, :width, :height,
                            :mime_type, :file_size, :checksum,
                            :mod_status, :rights, :is_primary, NOW()
                        )
                        ON CONFLICT (player_id, image_role) DO UPDATE SET
                            source_provider = EXCLUDED.source_provider,
                            provider_external_id = EXCLUDED.provider_external_id,
                            source_url = EXCLUDED.source_url,
                            storage_key = EXCLUDED.storage_key,
                            width = EXCLUDED.width,
                            height = EXCLUDED.height,
                            mime_type = EXCLUDED.mime_type,
                            file_size_bytes = EXCLUDED.file_size_bytes,
                            checksum_sha256 = EXCLUDED.checksum_sha256,
                            moderation_status = EXCLUDED.moderation_status,
                            rights_cleared = EXCLUDED.rights_cleared,
                            is_primary = EXCLUDED.is_primary,
                            last_processed_at = NOW()
                        """
                    ).bindparams(
                        sa.bindparam("src_prov", img["source_provider"]),
                        sa.bindparam("prov_ext_id", img["provider_external_id"]),
                        sa.bindparam("pid", player_id),
                        sa.bindparam("role", img["image_role"]),
                        sa.bindparam("src_url", img["source_url"]),
                        sa.bindparam("storage_key", img["storage_key"]),
                        sa.bindparam("width", img["width"]),
                        sa.bindparam("height", img["height"]),
                        sa.bindparam("mime_type", img["mime_type"]),
                        sa.bindparam("file_size", img["file_size_bytes"]),
                        sa.bindparam("checksum", img["checksum_sha256"]),
                        sa.bindparam("mod_status", img["moderation_status"]),
                        sa.bindparam("rights", img["rights_cleared"]),
                        sa.bindparam("is_primary", img["is_primary"]),
                    )
                )

        # Upsert player_faces
        if "player_faces" in tables:
            pf = payload["player_face"]
            if is_postgres:
                bind.execute(
                    sa.text(
                        """
                        INSERT INTO player_faces (
                            id, player_id, avatar_seed, facial_features,
                            hairstyle, skin_tone, accessories, generated_at
                        ) VALUES (
                            gen_random_uuid()::text, :pid, :seed, :features,
                            :hair, :skin, :accessories, NOW()
                        )
                        ON CONFLICT (player_id) DO UPDATE SET
                            avatar_seed = EXCLUDED.avatar_seed,
                            facial_features = EXCLUDED.facial_features,
                            hairstyle = EXCLUDED.hairstyle,
                            skin_tone = EXCLUDED.skin_tone,
                            accessories = EXCLUDED.accessories,
                            generated_at = NOW()
                        """
                    ).bindparams(
                        sa.bindparam("pid", player_id),
                        sa.bindparam("seed", pf["avatar_seed"]),
                        sa.bindparam("features", json.dumps(pf["facial_features"]), type_=postgresql.JSONB),
                        sa.bindparam("hair", pf["hairstyle"]),
                        sa.bindparam("skin", pf["skin_tone"]),
                        sa.bindparam("accessories", json.dumps(pf["accessories"]), type_=postgresql.JSONB),
                    )
                )


def downgrade() -> None:
    pass
