"""Expand ingestion schema for the 100,000-player tradable universe."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260311_0003"
down_revision = "20260311_0002"
branch_labels = None
depends_on = None

INTERNAL_LEAGUES = (
    {
        "id": "00000000-0000-0000-0000-0000000000a1",
        "code": "league_a",
        "name": "League A",
        "rank": 1,
        "competition_multiplier": 1.20,
        "visibility_weight": 1.00,
        "description": "Highest-visibility competitions in the tradable universe.",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-0000000000b1",
        "code": "league_b",
        "name": "League B",
        "rank": 2,
        "competition_multiplier": 1.10,
        "visibility_weight": 0.85,
        "description": "Strong professional competitions with meaningful market demand.",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-0000000000c1",
        "code": "league_c",
        "name": "League C",
        "rank": 3,
        "competition_multiplier": 1.05,
        "visibility_weight": 0.70,
        "description": "Broadly tradable competitions with moderate liquidity expectations.",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-0000000000d1",
        "code": "league_d",
        "name": "League D",
        "rank": 4,
        "competition_multiplier": 0.95,
        "visibility_weight": 0.55,
        "description": "Developmental competitions with narrower demand and slower repricing.",
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-0000000000e1",
        "code": "league_e",
        "name": "League E",
        "rank": 5,
        "competition_multiplier": 0.85,
        "visibility_weight": 0.40,
        "description": "Long-tail competitions retained for full-universe coverage.",
        "is_active": True,
    },
)

SUPPLY_TIERS = (
    {
        "id": "00000000-0000-0000-0000-000000001001",
        "code": "icon",
        "name": "Icon",
        "rank": 1,
        "min_score": 0.97,
        "max_score": 1.00,
        "target_share": 0.01,
        "circulating_supply": 90,
        "daily_pack_supply": 2,
        "season_mint_cap": 120,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000001002",
        "code": "elite",
        "name": "Elite",
        "rank": 2,
        "min_score": 0.90,
        "max_score": 0.9699,
        "target_share": 0.04,
        "circulating_supply": 180,
        "daily_pack_supply": 4,
        "season_mint_cap": 260,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000001003",
        "code": "core",
        "name": "Core",
        "rank": 3,
        "min_score": 0.72,
        "max_score": 0.8999,
        "target_share": 0.20,
        "circulating_supply": 360,
        "daily_pack_supply": 12,
        "season_mint_cap": 520,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000001004",
        "code": "prospect",
        "name": "Prospect",
        "rank": 4,
        "min_score": 0.50,
        "max_score": 0.7199,
        "target_share": 0.30,
        "circulating_supply": 600,
        "daily_pack_supply": 24,
        "season_mint_cap": 840,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000001005",
        "code": "discovery",
        "name": "Discovery",
        "rank": 5,
        "min_score": 0.00,
        "max_score": 0.4999,
        "target_share": 0.45,
        "circulating_supply": 900,
        "daily_pack_supply": 48,
        "season_mint_cap": 1500,
        "is_active": True,
    },
)

LIQUIDITY_BANDS = (
    {
        "id": "00000000-0000-0000-0000-000000002001",
        "code": "entry",
        "name": "Entry",
        "rank": 1,
        "min_price_credits": 0,
        "max_price_credits": 49,
        "max_spread_bps": 1400,
        "maker_inventory_target": 60,
        "instant_sell_fee_bps": 1200,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000002002",
        "code": "growth",
        "name": "Growth",
        "rank": 2,
        "min_price_credits": 50,
        "max_price_credits": 149,
        "max_spread_bps": 1000,
        "maker_inventory_target": 90,
        "instant_sell_fee_bps": 1000,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000002003",
        "code": "premium",
        "name": "Premium",
        "rank": 3,
        "min_price_credits": 150,
        "max_price_credits": 399,
        "max_spread_bps": 700,
        "maker_inventory_target": 120,
        "instant_sell_fee_bps": 850,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000002004",
        "code": "bluechip",
        "name": "Bluechip",
        "rank": 4,
        "min_price_credits": 400,
        "max_price_credits": 999,
        "max_spread_bps": 500,
        "maker_inventory_target": 150,
        "instant_sell_fee_bps": 700,
        "is_active": True,
    },
    {
        "id": "00000000-0000-0000-0000-000000002005",
        "code": "marquee",
        "name": "Marquee",
        "rank": 5,
        "min_price_credits": 1000,
        "max_price_credits": None,
        "max_spread_bps": 350,
        "maker_inventory_target": 200,
        "instant_sell_fee_bps": 600,
        "is_active": True,
    },
)


def upgrade() -> None:
    op.create_table(
        "ingestion_internal_leagues",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("competition_multiplier", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("visibility_weight", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_internal_leagues"),
        sa.UniqueConstraint("code", name="uq_ingestion_internal_leagues_code"),
        sa.UniqueConstraint("name", name="uq_ingestion_internal_leagues_name"),
        sa.UniqueConstraint("rank", name="uq_ingestion_internal_leagues_rank"),
    )
    op.create_index("ix_ingestion_internal_leagues_name", "ingestion_internal_leagues", ["name"], unique=False)

    op.create_table(
        "ingestion_supply_tiers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("min_score", sa.Float(), nullable=False),
        sa.Column("max_score", sa.Float(), nullable=False),
        sa.Column("target_share", sa.Float(), nullable=False),
        sa.Column("circulating_supply", sa.Integer(), nullable=False),
        sa.Column("daily_pack_supply", sa.Integer(), nullable=False),
        sa.Column("season_mint_cap", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_supply_tiers"),
        sa.UniqueConstraint("code", name="uq_ingestion_supply_tiers_code"),
        sa.UniqueConstraint("name", name="uq_ingestion_supply_tiers_name"),
        sa.UniqueConstraint("rank", name="uq_ingestion_supply_tiers_rank"),
    )
    op.create_index("ix_ingestion_supply_tiers_name", "ingestion_supply_tiers", ["name"], unique=False)

    op.create_table(
        "ingestion_liquidity_bands",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("min_price_credits", sa.Integer(), nullable=False),
        sa.Column("max_price_credits", sa.Integer(), nullable=True),
        sa.Column("max_spread_bps", sa.Integer(), nullable=False),
        sa.Column("maker_inventory_target", sa.Integer(), nullable=False),
        sa.Column("instant_sell_fee_bps", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_liquidity_bands"),
        sa.UniqueConstraint("code", name="uq_ingestion_liquidity_bands_code"),
        sa.UniqueConstraint("name", name="uq_ingestion_liquidity_bands_name"),
        sa.UniqueConstraint("rank", name="uq_ingestion_liquidity_bands_rank"),
    )
    op.create_index("ix_ingestion_liquidity_bands_name", "ingestion_liquidity_bands", ["name"], unique=False)

    _seed_catalog_tables()

    with op.batch_alter_table("ingestion_countries") as batch_op:
        batch_op.add_column(sa.Column("fifa_code", sa.String(length=8), nullable=True))
        batch_op.add_column(sa.Column("confederation_code", sa.String(length=16), nullable=True))
        batch_op.add_column(sa.Column("market_region", sa.String(length=32), nullable=True))
        batch_op.add_column(
            sa.Column("is_enabled_for_universe", sa.Boolean(), server_default=sa.text("1"), nullable=False)
        )
        batch_op.create_index("ix_ingestion_countries_fifa_code", ["fifa_code"], unique=False)
        batch_op.create_index("ix_ingestion_countries_confederation_code", ["confederation_code"], unique=False)

    with op.batch_alter_table("ingestion_competitions") as batch_op:
        batch_op.add_column(sa.Column("internal_league_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("format_type", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("age_bracket", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("domestic_level", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("is_tradable", sa.Boolean(), server_default=sa.text("1"), nullable=False))
        batch_op.add_column(sa.Column("competition_strength", sa.Float(), nullable=True))
        batch_op.create_index("ix_ingestion_competitions_internal_league_id", ["internal_league_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_ingestion_competitions_internal_league_id_ingestion_internal_leagues",
            "ingestion_internal_leagues",
            ["internal_league_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("ingestion_seasons") as batch_op:
        batch_op.add_column(sa.Column("season_status", sa.String(length=32), server_default=sa.text("'upcoming'"), nullable=False))
        batch_op.add_column(sa.Column("trading_window_opens_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("trading_window_closes_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("data_completeness_score", sa.Float(), nullable=True))

    with op.batch_alter_table("ingestion_clubs") as batch_op:
        batch_op.add_column(sa.Column("current_competition_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("internal_league_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("gender", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("popularity_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("is_tradable", sa.Boolean(), server_default=sa.text("1"), nullable=False))
        batch_op.create_index("ix_ingestion_clubs_current_competition_id", ["current_competition_id"], unique=False)
        batch_op.create_index("ix_ingestion_clubs_internal_league_id", ["internal_league_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_ingestion_clubs_current_competition_id_ingestion_competitions",
            "ingestion_competitions",
            ["current_competition_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_ingestion_clubs_internal_league_id_ingestion_internal_leagues",
            "ingestion_internal_leagues",
            ["internal_league_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.add_column(sa.Column("current_competition_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("internal_league_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("supply_tier_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("liquidity_band_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("market_value_eur", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("profile_completeness_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("is_tradable", sa.Boolean(), server_default=sa.text("1"), nullable=False))
        batch_op.create_index("ix_ingestion_players_current_competition_id", ["current_competition_id"], unique=False)
        batch_op.create_index("ix_ingestion_players_internal_league_id", ["internal_league_id"], unique=False)
        batch_op.create_index("ix_ingestion_players_supply_tier_id", ["supply_tier_id"], unique=False)
        batch_op.create_index("ix_ingestion_players_liquidity_band_id", ["liquidity_band_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_ingestion_players_current_competition_id_ingestion_competitions",
            "ingestion_competitions",
            ["current_competition_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_ingestion_players_internal_league_id_ingestion_internal_leagues",
            "ingestion_internal_leagues",
            ["internal_league_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_ingestion_players_supply_tier_id_ingestion_supply_tiers",
            "ingestion_supply_tiers",
            ["supply_tier_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_ingestion_players_liquidity_band_id_ingestion_liquidity_bands",
            "ingestion_liquidity_bands",
            ["liquidity_band_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "ingestion_player_verifications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("verification_source", sa.String(length=64), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("rights_confirmed", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_player_verifications_player_id_ingestion_players", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_player_verifications"),
        sa.UniqueConstraint("player_id", name="uq_ingestion_player_verifications_player_id"),
    )
    op.create_index("ix_ingestion_player_verifications_status", "ingestion_player_verifications", ["status"], unique=False)

    op.create_table(
        "ingestion_player_image_metadata",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_provider", sa.String(length=64), nullable=False),
        sa.Column("provider_external_id", sa.String(length=128), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("image_role", sa.String(length=32), server_default=sa.text("'portrait'"), nullable=False),
        sa.Column("source_url", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(length=64), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("moderation_status", sa.String(length=32), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("rights_cleared", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["player_id"], ["ingestion_players.id"], name="fk_ingestion_player_image_metadata_player_id_ingestion_players", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_player_image_metadata"),
        sa.UniqueConstraint("source_provider", "provider_external_id", name="uq_ingestion_player_images_provider_external_id"),
        sa.UniqueConstraint("player_id", "image_role", name="uq_ingestion_player_images_player_role"),
    )
    op.create_index("ix_ingestion_player_images_player_id", "ingestion_player_image_metadata", ["player_id"], unique=False)
    op.create_index("ix_ingestion_player_images_moderation_status", "ingestion_player_image_metadata", ["moderation_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ingestion_player_images_moderation_status", table_name="ingestion_player_image_metadata")
    op.drop_index("ix_ingestion_player_images_player_id", table_name="ingestion_player_image_metadata")
    op.drop_table("ingestion_player_image_metadata")

    op.drop_index("ix_ingestion_player_verifications_status", table_name="ingestion_player_verifications")
    op.drop_table("ingestion_player_verifications")

    with op.batch_alter_table("ingestion_players") as batch_op:
        batch_op.drop_constraint("fk_ingestion_players_liquidity_band_id_ingestion_liquidity_bands", type_="foreignkey")
        batch_op.drop_constraint("fk_ingestion_players_supply_tier_id_ingestion_supply_tiers", type_="foreignkey")
        batch_op.drop_constraint("fk_ingestion_players_internal_league_id_ingestion_internal_leagues", type_="foreignkey")
        batch_op.drop_constraint("fk_ingestion_players_current_competition_id_ingestion_competitions", type_="foreignkey")
        batch_op.drop_index("ix_ingestion_players_liquidity_band_id")
        batch_op.drop_index("ix_ingestion_players_supply_tier_id")
        batch_op.drop_index("ix_ingestion_players_internal_league_id")
        batch_op.drop_index("ix_ingestion_players_current_competition_id")
        batch_op.drop_column("is_tradable")
        batch_op.drop_column("profile_completeness_score")
        batch_op.drop_column("market_value_eur")
        batch_op.drop_column("liquidity_band_id")
        batch_op.drop_column("supply_tier_id")
        batch_op.drop_column("internal_league_id")
        batch_op.drop_column("current_competition_id")

    with op.batch_alter_table("ingestion_clubs") as batch_op:
        batch_op.drop_constraint("fk_ingestion_clubs_internal_league_id_ingestion_internal_leagues", type_="foreignkey")
        batch_op.drop_constraint("fk_ingestion_clubs_current_competition_id_ingestion_competitions", type_="foreignkey")
        batch_op.drop_index("ix_ingestion_clubs_internal_league_id")
        batch_op.drop_index("ix_ingestion_clubs_current_competition_id")
        batch_op.drop_column("is_tradable")
        batch_op.drop_column("popularity_score")
        batch_op.drop_column("gender")
        batch_op.drop_column("internal_league_id")
        batch_op.drop_column("current_competition_id")

    with op.batch_alter_table("ingestion_seasons") as batch_op:
        batch_op.drop_column("data_completeness_score")
        batch_op.drop_column("trading_window_closes_at")
        batch_op.drop_column("trading_window_opens_at")
        batch_op.drop_column("season_status")

    with op.batch_alter_table("ingestion_competitions") as batch_op:
        batch_op.drop_constraint("fk_ingestion_competitions_internal_league_id_ingestion_internal_leagues", type_="foreignkey")
        batch_op.drop_index("ix_ingestion_competitions_internal_league_id")
        batch_op.drop_column("competition_strength")
        batch_op.drop_column("is_tradable")
        batch_op.drop_column("domestic_level")
        batch_op.drop_column("age_bracket")
        batch_op.drop_column("format_type")
        batch_op.drop_column("internal_league_id")

    with op.batch_alter_table("ingestion_countries") as batch_op:
        batch_op.drop_index("ix_ingestion_countries_confederation_code")
        batch_op.drop_index("ix_ingestion_countries_fifa_code")
        batch_op.drop_column("is_enabled_for_universe")
        batch_op.drop_column("market_region")
        batch_op.drop_column("confederation_code")
        batch_op.drop_column("fifa_code")

    op.drop_index("ix_ingestion_liquidity_bands_name", table_name="ingestion_liquidity_bands")
    op.drop_table("ingestion_liquidity_bands")

    op.drop_index("ix_ingestion_supply_tiers_name", table_name="ingestion_supply_tiers")
    op.drop_table("ingestion_supply_tiers")

    op.drop_index("ix_ingestion_internal_leagues_name", table_name="ingestion_internal_leagues")
    op.drop_table("ingestion_internal_leagues")


def _seed_catalog_tables() -> None:
    internal_league_table = sa.table(
        "ingestion_internal_leagues",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("rank", sa.Integer()),
        sa.column("competition_multiplier", sa.Float()),
        sa.column("visibility_weight", sa.Float()),
        sa.column("description", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    supply_tier_table = sa.table(
        "ingestion_supply_tiers",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("rank", sa.Integer()),
        sa.column("min_score", sa.Float()),
        sa.column("max_score", sa.Float()),
        sa.column("target_share", sa.Float()),
        sa.column("circulating_supply", sa.Integer()),
        sa.column("daily_pack_supply", sa.Integer()),
        sa.column("season_mint_cap", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )
    liquidity_band_table = sa.table(
        "ingestion_liquidity_bands",
        sa.column("id", sa.String()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("rank", sa.Integer()),
        sa.column("min_price_credits", sa.Integer()),
        sa.column("max_price_credits", sa.Integer()),
        sa.column("max_spread_bps", sa.Integer()),
        sa.column("maker_inventory_target", sa.Integer()),
        sa.column("instant_sell_fee_bps", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
    )

    op.bulk_insert(internal_league_table, list(INTERNAL_LEAGUES))
    op.bulk_insert(supply_tier_table, list(SUPPLY_TIERS))
    op.bulk_insert(liquidity_band_table, list(LIQUIDITY_BANDS))
