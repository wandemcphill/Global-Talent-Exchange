"""Create or upgrade legend Kaka, create active Bukayo Saka, deduplicate Neymar as legend, and assign RUNNR UPDATE portraits.

Revision ID: 20261103_0215_kaka_saka_neymar_legends_and_runnr_portraits
Revises: 20261103_0214_reclassify_active_legends_and_verify_tradability
Create Date: 2026-11-03 05:45:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261103_0215_kaka_saka_neymar_legends_and_runnr_portraits"
down_revision = "20261103_0214_reclassify_active_legends_and_verify_tradability"
branch_labels = None
depends_on = None

PORTRAITS = {
    "c08d733b-ad89-44ee-9148-b6207b7e1291": {
        "slug": "kaka-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679942/players/portraits/p_c08d733b_kaka-legend.jpg",
        "local_url": "/img/portraits/legends/kaka-legend.png",
        "is_legend": True,
    },
    "f4b4531b-a342-48b5-8f43-618cfa0dc49a": {
        "slug": "bukayo-saka",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679946/players/portraits/p_f4b4531b_bukayo-saka.jpg",
        "local_url": "/img/portraits/bukayo-saka.png",
        "is_legend": False,
    },
    "f6e920aa-77d5-4f52-8b39-e5f34e55b1ca": {
        "slug": "neymar-jr-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679952/players/portraits/p_f6e920aa_neymar-jr-legend.jpg",
        "local_url": "/img/portraits/legends/neymar-jr-legend.png",
        "is_legend": True,
    },
    "4a4cae28-9d6d-4660-be47-997ff5692f05": {
        "slug": "emmanuel-olisadebe-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679956/players/portraits/p_4a4cae28_emmanuel-olisadebe-legend.jpg",
        "local_url": "/img/portraits/legends/emmanuel-olisadebe-legend.png",
        "is_legend": True,
    },
    "e2b6629d-b2fb-4a5c-9172-258276a33d3a": {
        "slug": "francesco-totti-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679959/players/portraits/p_e2b6629d_francesco-totti-legend.jpg",
        "local_url": "/img/portraits/legends/francesco-totti-legend.png",
        "is_legend": True,
    },
    "2ac6c6e1-8cc8-4560-bfc9-d0209b1bca32": {
        "slug": "jay-jay-okocha-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679962/players/portraits/p_2ac6c6e1_jay-jay-okocha-legend.jpg",
        "local_url": "/img/portraits/legends/jay-jay-okocha-legend.png",
        "is_legend": True,
    },
    "1c332e7b-30b9-4aa8-ab5c-80e105add418": {
        "slug": "john-obi-mikel-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679964/players/portraits/p_1c332e7b_john-obi-mikel-legend.jpg",
        "local_url": "/img/portraits/legends/john-obi-mikel-legend.png",
        "is_legend": True,
    },
    "2be1396f-3e46-4967-8571-797ef0f5c89b": {
        "slug": "frederic-kanoute-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679968/players/portraits/p_2be1396f_frederic-kanoute-legend.jpg",
        "local_url": "/img/portraits/legends/frederic-kanoute-legend.png",
        "is_legend": True,
    },
    "716524f4-f2c3-4f16-a793-37570e128151": {
        "slug": "luca-toni-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679970/players/portraits/p_716524f4_luca-toni-legend.jpg",
        "local_url": "/img/portraits/legends/luca-toni-legend.png",
        "is_legend": True,
    },
    "65655f82-555f-4b49-a734-df930dade8c1": {
        "slug": "marcos-senna-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679973/players/portraits/p_65655f82_marcos-senna-legend.jpg",
        "local_url": "/img/portraits/legends/marcos-senna-legend.png",
        "is_legend": True,
    },
    "504acd87-5b6d-41bb-ac26-b274951b671a": {
        "slug": "nwankwo-kanu-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679975/players/portraits/p_504acd87_nwankwo-kanu-legend.jpg",
        "local_url": "/img/portraits/legends/nwankwo-kanu-legend.png",
        "is_legend": True,
    },
    "c477096f-c848-4d33-84fc-055bf3063eb8": {
        "slug": "segun-odegbami-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679979/players/portraits/p_c477096f_segun-odegbami-legend.jpg",
        "local_url": "/img/portraits/legends/segun-odegbami-legend.png",
        "is_legend": True,
    },
    "b11fac24-3b09-4d50-8bab-3ae2f2460075": {
        "slug": "teslim-balogun-legend",
        "cloudinary_url": "https://res.cloudinary.com/dvxiniqew/image/upload/v1793679981/players/portraits/p_b11fac24_teslim-balogun-legend.jpg",
        "local_url": "/img/portraits/legends/teslim-balogun-legend.png",
        "is_legend": True,
    },
}


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # 1. Enable unaccent extension
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # 2. Kaká
    kaka_id = "c08d733b-ad89-44ee-9148-b6207b7e1291"
    kaka_legend_id = "073e6cdb-8af9-4fd3-ab1d-71368fea9d30"
    kaka_pic = PORTRAITS[kaka_id]["cloudinary_url"]

    op.execute(sa.text("""
        UPDATE ingestion_players
        SET full_name = 'Kaká',
            canonical_display_name = 'Kaká',
            first_name = 'Ricardo',
            last_name = 'Kaká',
            short_name = 'Kaká',
            position = 'AM',
            normalized_position = 'AM',
            secondary_positions_json = CAST('["ST", "LW"]' AS JSON),
            governed_gsi = 93,
            governed_potential_gsi = 93,
            potential = 93,
            real_player_tier = 'legend',
            is_real_player = true,
            is_tradable = true,
            legendary_profile_id = :l_id,
            dna_profile = (
                COALESCE(dna_profile::jsonb, '{}'::jsonb) ||
                jsonb_build_object(
                    'portrait_url', CAST(:pic AS text),
                    'image_url', CAST(:pic AS text),
                    'current_rating', 93,
                    'overall', 93,
                    'potential_rating', 93,
                    'position', 'AM',
                    'secondary_positions', json_build_array('ST', 'LW'),
                    'pace', 92,
                    'shooting', 90,
                    'passing', 92,
                    'dribbling', 94,
                    'defending', 55,
                    'physical', 78
                )
            )::json,
            updated_at = NOW()
        WHERE id = :p_id;
    """).bindparams(l_id=kaka_legend_id, pic=kaka_pic, p_id=kaka_id))

    op.execute(sa.text("""
        UPDATE legendary_player_profiles
        SET full_name = 'Kaká',
            slug = 'kaka-legend',
            primary_position = 'AM',
            secondary_positions_json = CAST('["ST", "LW"]' AS JSON),
            governed_gsi = 93,
            governed_potential_gsi = 93,
            portrait_metadata_json = (
                COALESCE(portrait_metadata_json::jsonb, '{}'::jsonb) ||
                jsonb_build_object('portrait_url', CAST(:pic AS text), 'source_provider', 'cloudinary', 'rights_cleared', true, 'moderation_status', 'approved')
            )::json,
            updated_at = NOW()
        WHERE id = :l_id;
    """).bindparams(pic=kaka_pic, l_id=kaka_legend_id))

    op.execute(sa.text("""
        UPDATE player_share_markets
        SET status = 'active',
            share_price_coin = 820.0,
            updated_at = NOW()
        WHERE player_id = :p_id;
    """).bindparams(p_id=kaka_id))

    op.execute(sa.text("""
        UPDATE player_summary_read_models
        SET player_name = 'Kaká',
            summary_json = (
                COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                jsonb_build_object(
                    'player_name', 'Kaká',
                    'gsi', 93,
                    'overall', 93,
                    'global_scouting_index', 93,
                    'potential', 93,
                    'position', 'AM',
                    'is_legend', true,
                    'real_player_tier', 'legend',
                    'is_tradable', true,
                    'portrait_url', CAST(:pic AS text),
                    'image_url', CAST(:pic AS text),
                    'market_visibility', jsonb_build_object('status', 'visible', 'eligible', true)
                )
            )::json,
            current_value_credits = 820.0,
            updated_at = NOW()
        WHERE player_id = :p_id;
    """).bindparams(pic=kaka_pic, p_id=kaka_id))

    # 3. Bukayo Saka
    saka_id = "f4b4531b-a342-48b5-8f43-618cfa0dc49a"
    saka_dup_id = "c02852d3-656f-49d8-bcb2-f83234525e27"
    saka_pic = PORTRAITS[saka_id]["cloudinary_url"]

    op.execute(sa.text("""
        UPDATE ingestion_players
        SET full_name = 'Bukayo Saka',
            canonical_display_name = 'Bukayo Saka',
            first_name = 'Bukayo',
            last_name = 'Saka',
            position = 'RW',
            normalized_position = 'RW',
            secondary_positions_json = CAST('["RM", "LW", "LB"]' AS JSON),
            governed_gsi = 85,
            governed_potential_gsi = 89,
            potential = 89,
            real_player_tier = 'marquee',
            is_real_player = true,
            is_tradable = true,
            legendary_profile_id = NULL,
            dna_profile = (
                COALESCE(dna_profile::jsonb, '{}'::jsonb) ||
                jsonb_build_object(
                    'portrait_url', CAST(:pic AS text),
                    'image_url', CAST(:pic AS text),
                    'current_rating', 85,
                    'overall', 85,
                    'potential_rating', 89,
                    'position', 'RW',
                    'secondary_positions', json_build_array('RM', 'LW', 'LB'),
                    'pace', 87,
                    'shooting', 83,
                    'passing', 84,
                    'dribbling', 88,
                    'defending', 68,
                    'physical', 76
                )
            )::json,
            updated_at = NOW()
        WHERE id = :p_id;
    """).bindparams(pic=saka_pic, p_id=saka_id))

    op.execute(sa.text("""
        UPDATE player_share_markets
        SET status = 'active',
            share_price_coin = 239.46,
            updated_at = NOW()
        WHERE player_id = :p_id;
    """).bindparams(p_id=saka_id))

    op.execute(sa.text("""
        UPDATE player_summary_read_models
        SET player_name = 'Bukayo Saka',
            summary_json = (
                COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                jsonb_build_object(
                    'player_name', 'Bukayo Saka',
                    'gsi', 85,
                    'overall', 85,
                    'global_scouting_index', 85,
                    'potential', 89,
                    'position', 'RW',
                    'is_legend', false,
                    'real_player_tier', 'marquee',
                    'is_tradable', true,
                    'portrait_url', CAST(:pic AS text),
                    'image_url', CAST(:pic AS text),
                    'market_visibility', jsonb_build_object('status', 'visible', 'eligible', true)
                )
            )::json,
            current_value_credits = 239.46,
            updated_at = NOW()
        WHERE player_id = :p_id;
    """).bindparams(pic=saka_pic, p_id=saka_id))

    # Retire Saka duplicate
    op.execute(
        sa.text("UPDATE ingestion_players SET is_tradable = false, updated_at = NOW() WHERE id = :dup_id;").bindparams(
            dup_id=saka_dup_id
        )
    )
    op.execute(
        sa.text(
            "UPDATE player_share_markets SET status = 'retired', updated_at = NOW() WHERE player_id = :dup_id;"
        ).bindparams(dup_id=saka_dup_id)
    )
    op.execute(sa.text("""
        UPDATE player_summary_read_models
        SET summary_json = (
                COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                jsonb_build_object('is_tradable', false, 'market_visibility', jsonb_build_object('status', 'hidden', 'eligible', false))
            )::json,
            updated_at = NOW()
        WHERE player_id = :dup_id;
    """).bindparams(dup_id=saka_dup_id))

    # 4. Neymar Jr
    neymar_canon_id = "f6e920aa-77d5-4f52-8b39-e5f34e55b1ca"
    neymar_dup_id = "f17a2b00-1781-4c57-b151-b7bad93bf227"
    neymar_legend_id = "a0f792b0-9a28-4ef6-b258-000000neymar"
    neymar_pic = PORTRAITS[neymar_canon_id]["cloudinary_url"]

    op.execute(sa.text("""
        INSERT INTO legendary_player_profiles (
            id, slug, full_name, country_code, primary_position, secondary_positions_json,
            preferred_foot, historical_height_cm, gtex_height_cm, era,
            legendary_classification, is_active, is_searchable, is_tradable,
            is_rentable, is_national_team_eligible, governed_gsi, governed_potential_gsi,
            date_of_birth, factual_date_of_birth, portrait_metadata_json,
            created_at, updated_at
        ) VALUES (
            :l_id, 'neymar-jr-legend', 'Neymar Jr', 'BRA', 'LW', CAST('["AM", "SS", "ST"]' AS JSON),
            'Right', 175, 175, '2010s Champions',
            'icon', true, true, true,
            true, true, 92, 92,
            '1992-02-05', '1992-02-05',
            jsonb_build_object('portrait_url', CAST(:pic AS text), 'source_provider', 'cloudinary', 'rights_cleared', true, 'moderation_status', 'approved')::json,
            NOW(), NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            full_name = EXCLUDED.full_name,
            slug = EXCLUDED.slug,
            primary_position = EXCLUDED.primary_position,
            secondary_positions_json = EXCLUDED.secondary_positions_json,
            governed_gsi = EXCLUDED.governed_gsi,
            governed_potential_gsi = EXCLUDED.governed_potential_gsi,
            portrait_metadata_json = EXCLUDED.portrait_metadata_json,
            updated_at = NOW();
    """).bindparams(l_id=neymar_legend_id, pic=neymar_pic))

    op.execute(sa.text("""
        UPDATE ingestion_players
        SET full_name = 'Neymar Jr',
            canonical_display_name = 'Neymar Jr',
            first_name = 'Neymar',
            last_name = 'da Silva Santos Júnior',
            short_name = 'Neymar',
            date_of_birth = '1992-02-05',
            factual_date_of_birth = '1992-02-05',
            position = 'LW',
            normalized_position = 'LW',
            secondary_positions_json = CAST('["AM", "SS", "ST"]' AS JSON),
            governed_gsi = 92,
            governed_potential_gsi = 92,
            potential = 92,
            real_player_tier = 'legend',
            is_real_player = true,
            is_tradable = true,
            legendary_profile_id = :l_id,
            dna_profile = (
                COALESCE(dna_profile::jsonb, '{}'::jsonb) ||
                jsonb_build_object(
                    'portrait_url', CAST(:pic AS text),
                    'image_url', CAST(:pic AS text),
                    'current_rating', 92,
                    'overall', 92,
                    'potential_rating', 92,
                    'position', 'LW',
                    'secondary_positions', json_build_array('AM', 'SS', 'ST'),
                    'pace', 91,
                    'shooting', 89,
                    'passing', 88,
                    'dribbling', 95,
                    'defending', 38,
                    'physical', 65
                )
            )::json,
            updated_at = NOW()
        WHERE id = :p_id;
    """).bindparams(l_id=neymar_legend_id, pic=neymar_pic, p_id=neymar_canon_id))

    op.execute(sa.text("""
        UPDATE player_share_markets
        SET status = 'active',
            share_price_coin = 720.0,
            updated_at = NOW()
        WHERE player_id = :p_id;
    """).bindparams(p_id=neymar_canon_id))

    op.execute(sa.text("""
        UPDATE player_summary_read_models
        SET player_name = 'Neymar Jr',
            summary_json = (
                COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                jsonb_build_object(
                    'player_name', 'Neymar Jr',
                    'gsi', 92,
                    'overall', 92,
                    'global_scouting_index', 92,
                    'potential', 92,
                    'position', 'LW',
                    'is_legend', true,
                    'real_player_tier', 'legend',
                    'is_tradable', true,
                    'portrait_url', CAST(:pic AS text),
                    'image_url', CAST(:pic AS text),
                    'market_visibility', jsonb_build_object('status', 'visible', 'eligible', true)
                )
            )::json,
            current_value_credits = 720.0,
            updated_at = NOW()
        WHERE player_id = :p_id;
    """).bindparams(pic=neymar_pic, p_id=neymar_canon_id))

    # Retire Neymar duplicate
    op.execute(
        sa.text("UPDATE ingestion_players SET is_tradable = false, updated_at = NOW() WHERE id = :dup_id;").bindparams(
            dup_id=neymar_dup_id
        )
    )
    op.execute(
        sa.text(
            "UPDATE player_share_markets SET status = 'retired', updated_at = NOW() WHERE player_id = :dup_id;"
        ).bindparams(dup_id=neymar_dup_id)
    )
    op.execute(sa.text("""
        UPDATE player_summary_read_models
        SET summary_json = (
                COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                jsonb_build_object('is_tradable', false, 'market_visibility', jsonb_build_object('status', 'hidden', 'eligible', false))
            )::json,
            updated_at = NOW()
        WHERE player_id = :dup_id;
    """).bindparams(dup_id=neymar_dup_id))

    # 5. OTHER 10 LEGENDS FROM RUNNR UPDATE
    OTHER_LEGENDS = [
        ("4a4cae28-9d6d-4660-be47-997ff5692f05", "c8459972-05e9-4e87-85b0-2d35ff4f532a", "Emmanuel Olisadebe", None),
        ("e2b6629d-b2fb-4a5c-9172-258276a33d3a", "1fd7d30a-baea-468d-a951-9c2dc60ae625", "Francesco Totti", None),
        ("2ac6c6e1-8cc8-4560-bfc9-d0209b1bca32", "7a529995-7b2a-4117-8b64-7e581b2a95fb", "Jay-Jay Okocha", None),
        ("1c332e7b-30b9-4aa8-ab5c-80e105add418", "fa2fc947-79bf-49d2-88a1-ae7ab5ff9e43", "John Obi Mikel", None),
        (
            "2be1396f-3e46-4967-8571-797ef0f5c89b",
            "37b66ff9-ea14-4eef-80d8-7a5d0da5101d",
            "Frédéric Kanouté",
            "frederic-kanoute-legend",
        ),
        ("716524f4-f2c3-4f16-a793-37570e128151", "d019de1f-a493-4bcc-9e78-1ab5a5a756cc", "Luca Toni", None),
        ("65655f82-555f-4b49-a734-df930dade8c1", "bf37a70f-7e4a-4409-8dc6-f8dcb4da9f2d", "Marcos Senna", None),
        ("504acd87-5b6d-41bb-ac26-b274951b671a", "f2ae390a-1f3c-4748-a519-cf330b44ed18", "Nwankwo Kanu", None),
        ("c477096f-c848-4d33-84fc-055bf3063eb8", "c477096f-c848-4d33-84fc-055bf3063eb8", "Segun Odegbami", None),
        ("b11fac24-3b09-4d50-8bab-3ae2f2460075", "b11fac24-3b09-4d50-8bab-3ae2f2460075", "Teslim Balogun", None),
    ]

    for p_id, l_id, clean_name, fixed_slug in OTHER_LEGENDS:
        pic = PORTRAITS[p_id]["cloudinary_url"]
        op.execute(sa.text("""
            UPDATE ingestion_players
            SET full_name = :name,
                canonical_display_name = :name,
                dna_profile = (
                    COALESCE(dna_profile::jsonb, '{}'::jsonb) ||
                    jsonb_build_object('portrait_url', CAST(:pic AS text), 'image_url', CAST(:pic AS text))
                )::json,
                updated_at = NOW()
            WHERE id = :p_id;
        """).bindparams(name=clean_name, pic=pic, p_id=p_id))

        if fixed_slug:
            op.execute(sa.text("""
                UPDATE legendary_player_profiles
                SET full_name = :name,
                    slug = :slug,
                    portrait_metadata_json = (
                        COALESCE(portrait_metadata_json::jsonb, '{}'::jsonb) ||
                        jsonb_build_object('portrait_url', CAST(:pic AS text), 'source_provider', 'cloudinary', 'rights_cleared', true, 'moderation_status', 'approved')
                    )::json,
                    updated_at = NOW()
                WHERE id = :l_id;
            """).bindparams(name=clean_name, slug=fixed_slug, pic=pic, l_id=l_id))
        else:
            op.execute(sa.text("""
                UPDATE legendary_player_profiles
                SET full_name = :name,
                    portrait_metadata_json = (
                        COALESCE(portrait_metadata_json::jsonb, '{}'::jsonb) ||
                        jsonb_build_object('portrait_url', CAST(:pic AS text), 'source_provider', 'cloudinary', 'rights_cleared', true, 'moderation_status', 'approved')
                    )::json,
                    updated_at = NOW()
                WHERE id = :l_id;
            """).bindparams(name=clean_name, pic=pic, l_id=l_id))

        op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET player_name = :name,
                summary_json = (
                    COALESCE(summary_json::jsonb, '{}'::jsonb) ||
                    jsonb_build_object('player_name', CAST(:name AS text), 'portrait_url', CAST(:pic AS text), 'image_url', CAST(:pic AS text))
                )::json,
                updated_at = NOW()
            WHERE player_id = :p_id;
        """).bindparams(name=clean_name, pic=pic, p_id=p_id))

    # 6. Upsert ingestion_player_image_metadata
    for spec_pid, data in PORTRAITS.items():
        pic = data["cloudinary_url"]
        op.execute(
            sa.text(
                "DELETE FROM ingestion_player_image_metadata WHERE player_id = :p_id AND image_role = 'portrait';"
            ).bindparams(p_id=spec_pid)
        )
        op.execute(sa.text("""
            INSERT INTO ingestion_player_image_metadata (
                id, player_id, source_provider, provider_external_id, image_role,
                source_url, moderation_status, rights_cleared, is_primary, created_at, updated_at
            ) VALUES (
                gen_random_uuid()::varchar, :p_id, 'cloudinary', :p_id, 'portrait',
                :pic, 'approved', true, true, NOW(), NOW()
            );
        """).bindparams(p_id=spec_pid, pic=pic))


def downgrade() -> None:
    pass
