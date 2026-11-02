"""Enforce generational legend ages, Ballon d'Or governed GSI, and legend/player deduplication.

Revision ID: 20261102_0204_legend_generational_ages_ballondor_gsi_dedup
Revises: 20261102_0203_yan_diomande_rating_and_real_madrid_club
Create Date: 2026-11-02 17:42:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261102_0204_legend_generational_ages_ballondor_gsi_dedup"
down_revision = "20261102_0203_yan_diomande_rating_and_real_madrid_club"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    is_postgres = bind.dialect.name == "postgresql"

    if not is_postgres:
        return

    # 1. Update legendary_player_profiles for Ballon d'Or Winners & Overrides
    if "legendary_player_profiles" in tables:
        # All-time overrides
        op.execute("""
            UPDATE legendary_player_profiles
            SET governed_gsi = 98, governed_potential_gsi = 98, factual_date_of_birth = '1987-06-24', gsi_override_reason = 'user_override_98_all_time'
            WHERE slug = 'lionel-messi-7458500';

            UPDATE legendary_player_profiles
            SET governed_gsi = 98, governed_potential_gsi = 98, factual_date_of_birth = '1985-02-05', gsi_override_reason = 'user_override_98_all_time'
            WHERE slug = 'cristiano-ronaldo-735216';

            UPDATE legendary_player_profiles
            SET governed_gsi = 95, governed_potential_gsi = 95, factual_date_of_birth = '1926-07-04', gsi_override_reason = 'ballon_dor_winner_floor_95'
            WHERE slug = 'alfredo-di-stfano-2002041145';

            UPDATE legendary_player_profiles
            SET governed_gsi = 91, governed_potential_gsi = 91, factual_date_of_birth = '1966-05-24', gsi_override_reason = 'user_override_91_cantona'
            WHERE slug IN ('ric-cantona-2002041392', 'eric-cantona-2002042479');

            -- Ballon d'Or Winners (Floor 95)
            UPDATE legendary_player_profiles
            SET governed_gsi = 95, governed_potential_gsi = 95, gsi_override_reason = 'ballondor_winner_floor_95'
            WHERE slug IN (
              'zinedine-zidane-8076', 'ronaldo-707715', 'thierry-henry-9888', 'ronaldinho-2002041199',
              'rivaldo-2002041204', 'pavel-nedved-8440', 'andriy-shevchenko-105986', 'george-weah-2002041023',
              'marco-van-basten-852152', 'lothar-matthus-1270', 'kaka-2002041198', 'fabio-cannavaro-1845'
            ) OR full_name IN (
              'Johan Cruyff', 'Franz Beckenbauer', 'Michel Platini', 'Roberto Baggio', 'Hristo Stoichkov',
              'Kaká', 'Kaka', 'Fabio Cannavaro'
            );

            -- Ballon d'Or Top 4 Podium Finishers (Floor 90)
            UPDATE legendary_player_profiles
            SET governed_gsi = 90, governed_potential_gsi = 90, gsi_override_reason = 'ballondor_top4_floor_90'
            WHERE slug IN (
              'michael-laudrup-601710', 'dennis-bergkamp-2010481', 'paolo-maldini-45', 'steven-gerrard-108658',
              'frank-lampard-2004697', 'xavi-4200583', 'andrs-iniesta-2002041699', 'arjen-robben-850881',
              'franck-ribry-8426264', 'david-beckham-2003443', 'alessandro-del-piero-8074', 'francesco-totti-2002042128',
              'didier-drogba-6201102', 'wayne-rooney-5108390', 'alan-shearer-2002041341', 'iker-casillas-6700151'
            ) OR full_name IN (
              'Dennis Bergkamp', 'Paolo Maldini', 'Steven Gerrard', 'Frank Lampard', 'Xavi', 'Andrés Iniesta',
              'Oliver Kahn', 'Gianluigi Buffon', 'Manuel Neuer', 'Franck Ribéry', 'Arjen Robben'
            );

            -- Ruud Gullit (94) and Franco Baresi (93)
            UPDATE legendary_player_profiles
            SET governed_gsi = 94, governed_potential_gsi = 94, gsi_override_reason = 'ballondor_winner_gullit_94'
            WHERE slug = 'ruud-gullit-2010704' OR full_name = 'Ruud Gullit';

            UPDATE legendary_player_profiles
            SET governed_gsi = 93, governed_potential_gsi = 93, gsi_override_reason = 'ballondor_runner_up_baresi_93'
            WHERE slug = 'franco-baresi-52' OR full_name = 'Franco Baresi';

            -- All remaining legends floor at 85
            UPDATE legendary_player_profiles
            SET governed_gsi = 85, governed_potential_gsi = 85, gsi_override_reason = 'legend_default_floor_85', gsi_methodology_version = 'v2.0'
            WHERE governed_gsi IS NULL;
            """)

    # 2. Update ingestion_players and sync from legendary_player_profiles
    if "ingestion_players" in tables:
        op.execute("""
            -- Core overrides on ingestion_players
            UPDATE ingestion_players
            SET governed_gsi = 98, governed_potential_gsi = 98, factual_date_of_birth = '1987-06-24', date_of_birth = '2006-06-24'
            WHERE id = '0892023b-65d0-4c6a-b1a5-b4d24aab721d';

            UPDATE ingestion_players
            SET governed_gsi = 98, governed_potential_gsi = 98, factual_date_of_birth = '1985-02-05', date_of_birth = '2006-02-05'
            WHERE id = '6e5ecc38-5ebe-453e-8ebb-9e297b6fbf0b';

            UPDATE ingestion_players
            SET governed_gsi = 98, governed_potential_gsi = 98, factual_date_of_birth = '1940-10-23', date_of_birth = '1996-10-23'
            WHERE id = 'c3f233ee-54fc-4e52-8b21-03bccac241dd';

            UPDATE ingestion_players
            SET governed_gsi = 95, governed_potential_gsi = 95, factual_date_of_birth = '1926-07-04', date_of_birth = '1996-07-04'
            WHERE id = '72211585-4621-494d-8c7f-d8a4e3173ff5';

            UPDATE ingestion_players
            SET governed_gsi = 91, governed_potential_gsi = 91, factual_date_of_birth = '1966-05-24', date_of_birth = '2001-05-24'
            WHERE id = 'b421109b-b268-49cc-b2cb-0fe6cf40ce4a';

            UPDATE ingestion_players
            SET governed_gsi = 90, governed_potential_gsi = 90, factual_date_of_birth = '1964-06-15', date_of_birth = '2001-06-15'
            WHERE id = '192e748c-a21e-4c00-9f1b-2a122bae06a9';

            -- Sync governed GSI from legendary_player_profiles to ingestion_players
            UPDATE ingestion_players ip
            SET governed_gsi = lp.governed_gsi,
                governed_potential_gsi = lp.governed_potential_gsi,
                gsi_methodology_version = lp.gsi_methodology_version,
                gsi_override_reason = lp.gsi_override_reason
            FROM legendary_player_profiles lp
            WHERE ip.legendary_profile_id = lp.id
              AND lp.governed_gsi IS NOT NULL;
            """)

    # 3. Deduplication of player rows & markets
    if "ingestion_players" in tables and "player_share_markets" in tables:
        op.execute("""
            -- Deduplicate Eric Cantona duplicate (Lyon) and Andres Iniesta duplicate
            UPDATE ingestion_players SET is_tradable = false WHERE id IN ('106bbc0a-a8b3-408e-b856-a4dad15799fd', '55f70b9b-dae9-4a55-8721-ccf9bdaa0154', '0704b985-6e51-49fc-bf74-45820da69183');
            UPDATE player_share_markets SET status = 'retired', circulating_shares = 0 WHERE player_id IN ('106bbc0a-a8b3-408e-b856-a4dad15799fd', '55f70b9b-dae9-4a55-8721-ccf9bdaa0154', '0704b985-6e51-49fc-bf74-45820da69183');
            UPDATE legendary_player_profiles SET is_active = false, is_searchable = false, is_tradable = false WHERE id IN ('59acd2d8-9fea-47f0-b33a-df6f932ccf5c', '315ea36a-68e6-4467-a5e2-12f817967237');

            -- Retire 39 duplicate FM23 active player rows
            UPDATE ingestion_players
            SET is_tradable = false
            WHERE id IN (
              '098b1b6d-7bbc-4ac4-861e-aab373d2c2be', '1b5999e8-32ac-4051-a1f2-634223411f47', '1d9937d2-a462-4bd4-889b-f6dce155acc2',
              '2575d076-ce6e-4bc6-b2e0-94e456d44d80', '5bd14e17-20c6-468e-9c87-e0a5e8d8e997', 'd91322df-947d-49dd-a3b4-686097747d90',
              'bd65c112-ca88-4fd2-8b93-b8af1a8c20ad', '882396e3-ed27-44d9-b30e-7b0a3f0c08d4', '8f6c2765-0542-4e88-b4b5-8ec9dbc68657',
              '6f5cc20f-fb59-4c6a-ba8c-b715504a6075', '77e375b1-cbbc-454a-ad3b-ec35f27743c3', '0cc3c580-f9bd-4066-a468-20363bf3d3ba',
              '862d907b-917a-4508-a19d-da3481ae778d', '3af04242-dde7-44e9-927a-e6cfb4f778fb', '48150ec5-de18-4ea2-afe9-c47b194839f7',
              '229e304e-ff6f-4c55-ab13-682c0ee5a91b', '84bcd2b8-347c-44ae-ae5c-e088bf0957b6', '6a0d9f47-21c9-45eb-9752-58db83c170d6',
              '1b6dfb98-417f-4e99-9efc-46df169d1bcf', 'de9feb52-e745-4a26-a70a-753165181f15', '81d65ee8-aa9e-419b-9cc7-07d8f432020b',
              '5d1d7c21-e482-4a3c-910f-ed29db291e78', '73659cd8-10e8-4d41-886e-e3b33c839f68', '9bb4b8c1-0b9e-4804-baa9-a62cf480c3d4',
              'aed52552-d17e-4c2c-99f2-bc3406476aa5', '3847afa4-7774-4493-a45e-22db092894d3', 'bbb54792-5c78-449e-8d9a-fccbfd06922f',
              '26b863cd-f64b-4d98-91ce-87432efde4af', 'fe6e5b60-eee5-428f-9dab-ab466cdc7df2', '21410153-11f5-422a-8b83-8812b484c1a3',
              '491602eb-7cb6-4fa0-aeb9-603041d7c16b', '18d1edff-1e8f-4f92-82a6-fe09cb90933e', 'c07a7e5b-6bb9-4397-b2f3-1380ba1f7aa4',
              'b0b1846b-1dd4-480d-8261-86aeddd93e90', '12f64ea4-1ee3-48ac-adc6-9e322e3f122e', '0968c794-0859-493f-98b3-bb6c009ccf78',
              'f9ecfb64-a7b0-4718-abb9-d8426f34f3bc', '890f2134-b9b8-411d-aec3-a2236dc9590d', '41dc02ba-d95d-40db-a7e5-4a4912a8b1bc'
            );

            UPDATE player_share_markets
            SET status = 'retired', circulating_shares = 0
            WHERE player_id IN (
              '098b1b6d-7bbc-4ac4-861e-aab373d2c2be', '1b5999e8-32ac-4051-a1f2-634223411f47', '1d9937d2-a462-4bd4-889b-f6dce155acc2',
              '2575d076-ce6e-4bc6-b2e0-94e456d44d80', '5bd14e17-20c6-468e-9c87-e0a5e8d8e997', 'd91322df-947d-49dd-a3b4-686097747d90',
              'bd65c112-ca88-4fd2-8b93-b8af1a8c20ad', '882396e3-ed27-44d9-b30e-7b0a3f0c08d4', '8f6c2765-0542-4e88-b4b5-8ec9dbc68657',
              '6f5cc20f-fb59-4c6a-ba8c-b715504a6075', '77e375b1-cbbc-454a-ad3b-ec35f27743c3', '0cc3c580-f9bd-4066-a468-20363bf3d3ba',
              '862d907b-917a-4508-a19d-da3481ae778d', '3af04242-dde7-44e9-927a-e6cfb4f778fb', '48150ec5-de18-4ea2-afe9-c47b194839f7',
              '229e304e-ff6f-4c55-ab13-682c0ee5a91b', '84bcd2b8-347c-44ae-ae5c-e088bf0957b6', '6a0d9f47-21c9-45eb-9752-58db83c170d6',
              '1b6dfb98-417f-4e99-9efc-46df169d1bcf', 'de9feb52-e745-4a26-a70a-753165181f15', '81d65ee8-aa9e-419b-9cc7-07d8f432020b',
              '5d1d7c21-e482-4a3c-910f-ed29db291e78', '73659cd8-10e8-4d41-886e-e3b33c839f68', '9bb4b8c1-0b9e-4804-baa9-a62cf480c3d4',
              'aed52552-d17e-4c2c-99f2-bc3406476aa5', '3847afa4-7774-4493-a45e-22db092894d3', 'bbb54792-5c78-449e-8d9a-fccbfd06922f',
              '26b863cd-f64b-4d98-91ce-87432efde4af', 'fe6e5b60-eee5-428f-9dab-ab466cdc7df2', '21410153-11f5-422a-8b83-8812b484c1a3',
              '491602eb-7cb6-4fa0-aeb9-603041d7c16b', '18d1edff-1e8f-4f92-82a6-fe09cb90933e', 'c07a7e5b-6bb9-4397-b2f3-1380ba1f7aa4',
              'b0b1846b-1dd4-480d-8261-86aeddd93e90', '12f64ea4-1ee3-48ac-adc6-9e322e3f122e', '0968c794-0859-493f-98b3-bb6c009ccf78',
              'f9ecfb64-a7b0-4718-abb9-d8426f34f3bc', '890f2134-b9b8-411d-aec3-a2236dc9590d', '41dc02ba-d95d-40db-a7e5-4a4912a8b1bc'
            );
            """)

    # 4. Synchronize player_summary_read_models
    if "player_summary_read_models" in tables:
        op.execute("""
            -- Mark retired duplicate player summaries as archived
            UPDATE player_summary_read_models
            SET summary_json = jsonb_set(jsonb_set(summary_json::jsonb, '{market_visibility,status}', '"archived"'), '{market_visibility,eligible}', 'false')
            WHERE player_id IN (
              '106bbc0a-a8b3-408e-b856-a4dad15799fd', '55f70b9b-dae9-4a55-8721-ccf9bdaa0154', '0704b985-6e51-49fc-bf74-45820da69183',
              '098b1b6d-7bbc-4ac4-861e-aab373d2c2be', '1b5999e8-32ac-4051-a1f2-634223411f47', '1d9937d2-a462-4bd4-889b-f6dce155acc2',
              '2575d076-ce6e-4bc6-b2e0-94e456d44d80', '5bd14e17-20c6-468e-9c87-e0a5e8d8e997', 'd91322df-947d-49dd-a3b4-686097747d90',
              'bd65c112-ca88-4fd2-8b93-b8af1a8c20ad', '882396e3-ed27-44d9-b30e-7b0a3f0c08d4', '8f6c2765-0542-4e88-b4b5-8ec9dbc68657',
              '6f5cc20f-fb59-4c6a-ba8c-b715504a6075', '77e375b1-cbbc-454a-ad3b-ec35f27743c3', '0cc3c580-f9bd-4066-a468-20363bf3d3ba',
              '862d907b-917a-4508-a19d-da3481ae778d', '3af04242-dde7-44e9-927a-e6cfb4f778fb', '48150ec5-de18-4ea2-afe9-c47b194839f7',
              '229e304e-ff6f-4c55-ab13-682c0ee5a91b', '84bcd2b8-347c-44ae-ae5c-e088bf0957b6', '6a0d9f47-21c9-45eb-9752-58db83c170d6',
              '1b6dfb98-417f-4e99-9efc-46df169d1bcf', 'de9feb52-e745-4a26-a70a-753165181f15', '81d65ee8-aa9e-419b-9cc7-07d8f432020b',
              '5d1d7c21-e482-4a3c-910f-ed29db291e78', '73659cd8-10e8-4d41-886e-e3b33c839f68', '9bb4b8c1-0b9e-4804-baa9-a62cf480c3d4',
              'aed52552-d17e-4c2c-99f2-bc3406476aa5', '3847afa4-7774-4493-a45e-22db092894d3', 'bbb54792-5c78-449e-8d9a-fccbfd06922f',
              '26b863cd-f64b-4d98-91ce-87432efde4af', 'fe6e5b60-eee5-428f-9dab-ab466cdc7df2', '21410153-11f5-422a-8b83-8812b484c1a3',
              '491602eb-7cb6-4fa0-aeb9-603041d7c16b', '18d1edff-1e8f-4f92-82a6-fe09cb90933e', 'c07a7e5b-6bb9-4397-b2f3-1380ba1f7aa4',
              'b0b1846b-1dd4-480d-8261-86aeddd93e90', '12f64ea4-1ee3-48ac-adc6-9e322e3f122e', '0968c794-0859-493f-98b3-bb6c009ccf78',
              'f9ecfb64-a7b0-4718-abb9-d8426f34f3bc', '890f2134-b9b8-411d-aec3-a2236dc9590d', '41dc02ba-d95d-40db-a7e5-4a4912a8b1bc'
            );

            -- Sync governed ratings into summary_json for all legends
            UPDATE player_summary_read_models s
            SET summary_json = jsonb_set(
                  jsonb_set(
                    jsonb_set(
                      s.summary_json::jsonb,
                      '{gsi}',
                      to_jsonb(p.governed_gsi)
                    ),
                    '{overall}',
                    to_jsonb(p.governed_gsi)
                  ),
                  '{potential}',
                  to_jsonb(COALESCE(p.governed_potential_gsi, p.governed_gsi))
                )
            FROM ingestion_players p
            WHERE s.player_id = p.id
              AND p.governed_gsi IS NOT NULL;
            """)


def downgrade() -> None:
    pass
