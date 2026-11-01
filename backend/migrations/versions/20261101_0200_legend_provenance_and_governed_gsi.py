"""Add legend provenance and governed GSI columns.

Revision ID: 20261101_0200_legend_provenance_and_governed_gsi
Revises: 20261101_0156_account_types_creator_and_trader_kyc
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20261101_0200_legend_provenance_and_governed_gsi"
down_revision = "20261101_0156_account_types_creator_and_trader_kyc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    is_postgres = bind.dialect.name == "postgresql"

    new_columns = [
        ("factual_date_of_birth", sa.Date(), True, None),
        ("source_game_date_of_birth", sa.Date(), True, None),
        ("prime_age_at_snapshot", sa.Integer(), True, None),
        ("governed_gsi", sa.Integer(), True, None),
        ("governed_potential_gsi", sa.Integer(), True, None),
        ("gsi_methodology_version", sa.String(32), False, "v2.0"),
        ("gsi_override_reason", sa.Text(), True, None),
    ]

    for table_name in ("legendary_player_profiles", "ingestion_players"):
        if table_name in tables:
            existing = {c["name"] for c in inspector.get_columns(table_name)}
            for col_name, col_type, nullable, default in new_columns:
                if col_name not in existing:
                    if default is not None:
                        op.add_column(
                            table_name,
                            sa.Column(col_name, col_type, nullable=nullable, server_default=default),
                        )
                    else:
                        op.add_column(
                            table_name,
                            sa.Column(col_name, col_type, nullable=nullable),
                        )

    # Data migration statements (only executed when running on PostgreSQL)
    if is_postgres:
        # 1. Backfill source_game_date_of_birth from date_of_birth
        if "legendary_player_profiles" in tables:
            op.execute(
                """
                UPDATE legendary_player_profiles
                SET source_game_date_of_birth = date_of_birth
                WHERE source_game_date_of_birth IS NULL AND date_of_birth IS NOT NULL;
                """
            )
            op.execute(
                """
                UPDATE legendary_player_profiles
                SET prime_age_at_snapshot = 2023 - EXTRACT(YEAR FROM date_of_birth)
                WHERE prime_age_at_snapshot IS NULL AND date_of_birth IS NOT NULL;
                """
            )

        if "ingestion_players" in tables:
            op.execute(
                """
                UPDATE ingestion_players
                SET source_game_date_of_birth = date_of_birth
                WHERE source_game_date_of_birth IS NULL 
                  AND date_of_birth IS NOT NULL
                  AND (legendary_profile_id IS NOT NULL OR source_provider = 'fm23_genie_scout');
                """
            )
            op.execute(
                """
                UPDATE ingestion_players
                SET prime_age_at_snapshot = 2023 - EXTRACT(YEAR FROM date_of_birth)
                WHERE prime_age_at_snapshot IS NULL 
                  AND date_of_birth IS NOT NULL
                  AND (legendary_profile_id IS NOT NULL OR source_provider = 'fm23_genie_scout');
                """
            )

        # 2. Backfill verified factual_date_of_birth and governed_gsi on legendary_player_profiles
        legend_updates = [
            ("Pelé", "1940-10-23", 98, 98, "all_time_legend_override_98"),
            ("Romário", "1966-01-29", 95, 95, "retrospective_1994_winner_95"),
            ("Lionel Messi", "1987-06-24", 98, 98, "user_override_98_all_time"),
            ("Cristiano Ronaldo", "1985-02-05", 98, 98, "user_override_98_all_time"),
            ("Thierry Henry", "1977-08-17", 95, 95, "user_override_95_ballon_dor_winner_tier"),
            ("Diego Maradona", "1960-10-30", 98, 98, "all_time_legend_override_98"),
            ("Zinedine Zidane", "1972-06-23", 95, 95, "ballon_dor_winner_floor_95"),
            ("Éric Cantona", "1966-05-24", 91, 91, "user_rule_below_messi_cr7_zidane_91"),
            ("Eric Cantona", "1966-05-24", 91, 91, "user_rule_below_messi_cr7_zidane_91"),
            ("Alfredo Di Stéfano", "1926-07-04", 95, 95, "ballon_dor_winner_floor_95"),
            ("Ronaldinho", "1980-03-21", 95, 95, "ballon_dor_winner_floor_95"),
            ("Michael Laudrup", "1964-06-15", 90, 90, "ballon_dor_top4_floor_90"),
        ]

        for name, dob, gsi, pot_gsi, reason in legend_updates:
            safe_name = name.replace("'", "''")
            safe_reason = reason.replace("'", "''")
            op.execute(
                f"""
                UPDATE legendary_player_profiles
                SET factual_date_of_birth = '{dob}',
                    governed_gsi = {gsi},
                    governed_potential_gsi = {pot_gsi},
                    gsi_methodology_version = 'v2.0',
                    gsi_override_reason = '{safe_reason}'
                WHERE full_name = '{safe_name}';
                """
            )

        # 3. Backfill verified factual_date_of_birth and governed_gsi on ingestion_players
        player_updates = [
            ("c3f233ee-54fc-4e52-8b21-03bccac241dd", "1940-10-23", 98, 98, "all_time_legend_override_98"),
            ("64ac17c6-768d-4cae-9cac-7ccbd0b079d9", "1966-01-29", 95, 95, "retrospective_1994_winner_95"),
            ("192e748c-a21e-4c00-9f1b-2a122bae06a9", "1964-06-15", 90, 90, "ballon_dor_top4_floor_90"),
            ("0a737828-344e-453f-a7ea-392eb50af184", "1997-10-20", 84, 90, "benchmark_active_player_lookman_84_90"),
            ("ec2d85a8-b8c0-45b0-a8e5-68583d77abdf", "1997-10-20", 84, 90, "benchmark_active_player_lookman_84_90"),
            ("48b614bd-3547-48c0-860f-d700564a6866", "2002-05-06", 89, 93, "benchmark_active_player_palmer_89_93"),
            ("7d8283e6-d7f3-421a-bba1-a99bf76a4228", "2002-05-06", 89, 93, "benchmark_active_player_palmer_89_93"),
            ("b2fe3c0b-ced5-42c8-88da-e898153eb3fc", "2002-05-06", 89, 93, "benchmark_active_player_palmer_89_93"),
            ("5c630eb2-f19d-4bd7-8d9e-7b2c74e297be", "2007-04-24", 85, 90, "benchmark_active_player_estevao_85_90"),
            ("cebeafaa-32fd-448b-b848-daaf43782a0a", "2007-04-24", 85, 90, "benchmark_active_player_estevao_85_90"),
            ("0abd831b-ff11-4134-9564-68e75c787d98", "2008-04-11", 78, 89, "benchmark_active_player_mec_78_89"),
            ("335a34c3-0a04-48b2-8097-091c0a338105", "2008-04-11", 78, 89, "benchmark_active_player_mec_78_89"),
            ("eff52911-6eed-4834-ab1c-a86cb4b6525a", "2007-06-29", 74, 89, "benchmark_active_player_zadok_74_89"),
            ("b4f634ff-cae8-4fbb-bf97-0e3d95025c59", "2007-06-29", 74, 89, "benchmark_active_player_zadok_74_89"),
        ]

        for player_id, dob, gsi, pot_gsi, reason in player_updates:
            safe_reason = reason.replace("'", "''")
            op.execute(
                f"""
                UPDATE ingestion_players
                SET factual_date_of_birth = '{dob}',
                    governed_gsi = {gsi},
                    governed_potential_gsi = {pot_gsi},
                    gsi_methodology_version = 'v2.0',
                    gsi_override_reason = '{safe_reason}'
                WHERE id = '{player_id}';
                """
            )

        # Also backfill ingestion_players linked to the updated legendary profiles
        op.execute(
            """
            UPDATE ingestion_players p
            SET factual_date_of_birth = l.factual_date_of_birth,
                governed_gsi = l.governed_gsi,
                governed_potential_gsi = l.governed_potential_gsi,
                gsi_methodology_version = l.gsi_methodology_version,
                gsi_override_reason = l.gsi_override_reason
            FROM legendary_player_profiles l
            WHERE p.legendary_profile_id = l.id
              AND l.governed_gsi IS NOT NULL;
            """
        )


def downgrade() -> None:
    columns = [
        "factual_date_of_birth",
        "source_game_date_of_birth",
        "prime_age_at_snapshot",
        "governed_gsi",
        "governed_potential_gsi",
        "gsi_methodology_version",
        "gsi_override_reason",
    ]
    for table_name in ("ingestion_players", "legendary_player_profiles"):
        for col in columns:
            op.drop_column(table_name, col)
