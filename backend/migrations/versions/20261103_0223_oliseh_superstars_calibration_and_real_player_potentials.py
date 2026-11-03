"""Sunday Oliseh DM/CM position correction, superstars rating/potential calibration, and universal real player potentials.

Revision ID: 20261103_0223_oliseh_superstars_calibration_and_real_player_potentials
Revises: 20261103_0222_comprehensive_platform_deduplication_and_tradability
Create Date: 2026-11-03 17:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "20261103_0223_oliseh_superstars_calibration_and_real_player_potentials"
down_revision = "20261103_0222_comprehensive_platform_deduplication_and_tradability"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Sunday Oliseh: DM/CM NOT CB
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET position = 'DM/CM',
                normalized_position = 'DM',
                secondary_positions_json = '["CM"]'::json
            WHERE id = '267d8895-ba83-4b09-a21e-64f5fd23196a'
               OR full_name = 'Sunday Oliseh'
               OR canonical_display_name = 'Sunday Oliseh';
            """))

    op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(
                  jsonb_set(COALESCE(summary_json::jsonb, '{}'::jsonb), '{position}', '"DM/CM"'),
                  '{normalized_position}', '"DM"'
                )::json
            WHERE player_id = '267d8895-ba83-4b09-a21e-64f5fd23196a'
               OR player_name = 'Sunday Oliseh';
            """))

    # 2. Victor Osimhen: Rating 90, Potential 91
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_gsi = 90,
                governed_potential_gsi = 91,
                potential = 91,
                dna_profile = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(dna_profile::jsonb, '{}'::jsonb), '{overall}', '90'),
                      '{potential}', '91'
                    ),
                    '{current_rating}', '90'
                  ),
                  '{potential_rating}', '91'
                )::json
            WHERE id = '2dc62da9-550b-423b-bfe3-445de565051e'
               OR (full_name ILIKE '%Victor Osimhen%' AND COALESCE(real_player_tier, '') != 'archived_duplicate');
            """))

    op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET average_rating = 90.0,
                summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(COALESCE(summary_json::jsonb, '{}'::jsonb), '{gsi}', '90'),
                    '{overall}', '90'
                  ),
                  '{potential}', '91'
                )::json
            WHERE player_id = '2dc62da9-550b-423b-bfe3-445de565051e'
               OR player_name ILIKE '%Victor Osimhen%';
            """))

    # 3. Michael Olise: Rating 90, Potential 93 (retire duplicate 63ce3e82-7695-40ea-89ee-908126c0c038)
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_gsi = 90,
                governed_potential_gsi = 93,
                potential = 93,
                dna_profile = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(dna_profile::jsonb, '{}'::jsonb), '{overall}', '90'),
                      '{potential}', '93'
                    ),
                    '{current_rating}', '90'
                  ),
                  '{potential_rating}', '93'
                )::json
            WHERE id = '7adffe47-8001-41da-beda-af3b89c8527f'
               OR (full_name = 'Michael Olise' AND COALESCE(real_player_tier, '') != 'archived_duplicate');

            UPDATE ingestion_players
            SET real_player_tier = 'archived_duplicate',
                is_tradable = false
            WHERE id = '63ce3e82-7695-40ea-89ee-908126c0c038';

            DELETE FROM player_summary_read_models
            WHERE player_id = '63ce3e82-7695-40ea-89ee-908126c0c038';
            """))

    op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET average_rating = 90.0,
                summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(COALESCE(summary_json::jsonb, '{}'::jsonb), '{gsi}', '90'),
                    '{overall}', '90'
                  ),
                  '{potential}', '93'
                )::json
            WHERE player_id = '7adffe47-8001-41da-beda-af3b89c8527f'
               OR player_name = 'Michael Olise';
            """))

    # 4. Kylian Mbappé: Rating 93, Potential 95
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_gsi = 93,
                governed_potential_gsi = 95,
                potential = 95,
                dna_profile = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(dna_profile::jsonb, '{}'::jsonb), '{overall}', '93'),
                      '{potential}', '95'
                    ),
                    '{current_rating}', '93'
                  ),
                  '{potential_rating}', '95'
            )::json
            WHERE id = '729dc5c1-fc66-4b4a-933b-b69785cebaf1'
               OR (full_name ILIKE '%Kylian Mbapp%' AND COALESCE(real_player_tier, '') != 'archived_duplicate');
            """))

    op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET average_rating = 93.0,
                summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(COALESCE(summary_json::jsonb, '{}'::jsonb), '{gsi}', '93'),
                    '{overall}', '93'
                  ),
                  '{potential}', '95'
                )::json
            WHERE player_id = '729dc5c1-fc66-4b4a-933b-b69785cebaf1'
               OR (player_name ILIKE '%Kylian Mbapp%' AND player_name NOT ILIKE '%Ethan%');
            """))

    # 5. Lamine Yamal: Rating 91, Potential 96, RW / ST / LW / AM
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_gsi = 91,
                governed_potential_gsi = 96,
                potential = 96,
                position = 'RW/ST/LW/AM',
                normalized_position = 'RW',
                secondary_positions_json = '["ST", "LW", "AM"]'::json,
                dna_profile = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(dna_profile::jsonb, '{}'::jsonb), '{overall}', '91'),
                      '{potential}', '96'
                    ),
                    '{current_rating}', '91'
                  ),
                  '{potential_rating}', '96'
                )::json
            WHERE id = '5456d831-66d3-40f1-8dc6-89ea195eac73'
               OR (full_name ILIKE '%Yamal%' AND COALESCE(real_player_tier, '') != 'archived_duplicate');
            """))

    op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET average_rating = 91.0,
                summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(summary_json::jsonb, '{}'::jsonb), '{gsi}', '91'),
                      '{overall}', '91'
                    ),
                    '{potential}', '96'
                  ),
                  '{position}', '"RW/ST/LW/AM"'
                )::json
            WHERE player_id = '5456d831-66d3-40f1-8dc6-89ea195eac73'
               OR player_name ILIKE '%Yamal%';
            """))

    # 6. Ousmane Dembélé: Rating 91, Potential 92
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_gsi = 91,
                governed_potential_gsi = 92,
                potential = 92,
                dna_profile = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(dna_profile::jsonb, '{}'::jsonb), '{overall}', '91'),
                      '{potential}', '92'
                    ),
                    '{current_rating}', '91'
                  ),
                  '{potential_rating}', '92'
                )::json
            WHERE id = '379bb246-c951-44e8-8584-fd8dbe1e4cc1'
               OR (full_name ILIKE '%Ousmane Demb%' AND COALESCE(real_player_tier, '') != 'archived_duplicate');
            """))

    op.execute(sa.text("""
            UPDATE player_summary_read_models
            SET average_rating = 91.0,
                summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(COALESCE(summary_json::jsonb, '{}'::jsonb), '{gsi}', '91'),
                    '{overall}', '91'
                  ),
                  '{potential}', '92'
                )::json
            WHERE player_id = '379bb246-c951-44e8-8584-fd8dbe1e4cc1'
               OR player_name ILIKE '%Ousmane Demb%';
            """))

    # 7. Universal GSI and Potential Ratings for All Real Players (Legends Excluded)
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_potential_gsi = LEAST(99, governed_gsi + CASE
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '2005-01-01' THEN 7
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '2002-01-01' THEN 5
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '1998-01-01' THEN 3
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '1994-01-01' THEN 2
                  ELSE 1
                END),
                potential = LEAST(99, governed_gsi + CASE
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '2005-01-01' THEN 7
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '2002-01-01' THEN 5
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '1998-01-01' THEN 3
                  WHEN date_of_birth IS NOT NULL AND date_of_birth >= '1994-01-01' THEN 2
                  ELSE 1
                END)
            WHERE COALESCE(real_player_tier, '') != 'archived_duplicate'
              AND COALESCE(real_player_tier, '') != 'legend'
              AND source_provider NOT IN ('gtex_legend', 'gtex_legend_prime')
              AND legendary_profile_id IS NULL
              AND (governed_potential_gsi IS NULL OR governed_potential_gsi <= governed_gsi OR potential IS NULL OR potential <= governed_gsi);
            """))

    # Sync DNA profile for real players needing overall / potential update
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET dna_profile = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      jsonb_set(COALESCE(dna_profile::jsonb, '{}'::jsonb), '{overall}', to_jsonb(governed_gsi)),
                      '{potential}', to_jsonb(governed_potential_gsi)
                    ),
                    '{current_rating}', to_jsonb(governed_gsi)
                  ),
                  '{potential_rating}', to_jsonb(governed_potential_gsi)
                )::json
            WHERE COALESCE(real_player_tier, '') != 'archived_duplicate'
              AND COALESCE(real_player_tier, '') != 'legend'
              AND source_provider NOT IN ('gtex_legend', 'gtex_legend_prime')
              AND legendary_profile_id IS NULL
              AND (
                (dna_profile->>'potential') IS NULL
                OR (dna_profile->>'potential')::int != governed_potential_gsi
                OR (dna_profile->>'overall') IS NULL
                OR (dna_profile->>'overall')::int != governed_gsi
              );
            """))

    # Sync player_summary_read_models for real players
    op.execute(sa.text("""
            UPDATE player_summary_read_models ps
            SET summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(COALESCE(ps.summary_json::jsonb, '{}'::jsonb), '{gsi}', to_jsonb(p.governed_gsi)),
                    '{overall}', to_jsonb(p.governed_gsi)
                  ),
                  '{potential}', to_jsonb(p.governed_potential_gsi)
                )::json
            FROM ingestion_players p
            WHERE ps.player_id = p.id
              AND COALESCE(p.real_player_tier, '') != 'archived_duplicate'
              AND COALESCE(p.real_player_tier, '') != 'legend'
              AND p.source_provider NOT IN ('gtex_legend', 'gtex_legend_prime')
              AND p.legendary_profile_id IS NULL
              AND (
                (ps.summary_json->>'potential') IS NULL
                OR (ps.summary_json->>'potential')::int != p.governed_potential_gsi
                OR (ps.summary_json->>'gsi') IS NULL
                OR (ps.summary_json->>'gsi')::int != p.governed_gsi
              );
            """))

    # 8. Legends: strictly excluded from growth curves (governed_potential_gsi = governed_gsi)
    op.execute(sa.text("""
            UPDATE ingestion_players
            SET governed_potential_gsi = governed_gsi,
                potential = governed_gsi
            WHERE (
              real_player_tier = 'legend'
              OR source_provider IN ('gtex_legend', 'gtex_legend_prime')
              OR legendary_profile_id IS NOT NULL
            )
            AND (governed_potential_gsi != governed_gsi OR potential != governed_gsi);
            """))


def downgrade() -> None:
    pass
