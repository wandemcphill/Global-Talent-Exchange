"""regen transfer pressure, contract offers, and headline media

Revision ID: 20260315_0007
Revises: 20260315_0005
Create Date: 2026-03-15 23:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_0007"
down_revision = "20260315_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regen_unsettling_events",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("approaching_club_id", sa.String(length=36), nullable=False),
        sa.Column("previous_state", sa.String(length=48), nullable=False, server_default="content"),
        sa.Column("resulting_state", sa.String(length=48), nullable=False, server_default="content"),
        sa.Column("effect_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("resisted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approaching_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_unsettling_events_regen_id", "regen_unsettling_events", ["regen_id"], unique=False)
    op.create_index(
        "ix_regen_unsettling_events_approaching_club_id",
        "regen_unsettling_events",
        ["approaching_club_id"],
        unique=False,
    )

    op.create_table(
        "regen_transfer_pressure_states",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("current_state", sa.String(length=48), nullable=False, server_default="content"),
        sa.Column("ambition_pressure", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("transfer_desire", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("prestige_dissatisfaction", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("title_frustration", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("pressure_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("salary_expectation_fancoin_per_year", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("active_transfer_request", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("refuses_new_contract", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("end_of_contract_pressure", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("unresolved_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_big_club_id", sa.String(length=36), nullable=True),
        sa.Column("last_resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["last_big_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_id", name="uq_regen_transfer_pressure_states_regen_id"),
    )
    op.create_index(
        "ix_regen_transfer_pressure_states_current_state",
        "regen_transfer_pressure_states",
        ["current_state"],
        unique=False,
    )
    op.create_index(
        "ix_regen_transfer_pressure_states_current_club_id",
        "regen_transfer_pressure_states",
        ["current_club_id"],
        unique=False,
    )

    op.create_table(
        "regen_big_club_approaches",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("current_club_id", sa.String(length=36), nullable=True),
        sa.Column("approaching_club_id", sa.String(length=36), nullable=False),
        sa.Column("prestige_gap_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("trophy_gap_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("resistance_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("contract_tenure_months", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("effect_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("resisted", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("resulting_state", sa.String(length=48), nullable=False, server_default="content"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["current_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["approaching_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_big_club_approaches_regen_id", "regen_big_club_approaches", ["regen_id"], unique=False)
    op.create_index(
        "ix_regen_big_club_approaches_approaching_club_id",
        "regen_big_club_approaches",
        ["approaching_club_id"],
        unique=False,
    )

    op.create_table(
        "regen_team_dynamics_effects",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("triggered_state", sa.String(length=48), nullable=False, server_default="content"),
        sa.Column("morale_penalty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("chemistry_penalty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("tactical_cohesion_penalty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("performance_penalty", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("influences_younger_players", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("unresolved_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_team_dynamics_effects_regen_id", "regen_team_dynamics_effects", ["regen_id"], unique=False)
    op.create_index("ix_regen_team_dynamics_effects_club_id", "regen_team_dynamics_effects", ["club_id"], unique=False)
    op.create_index("ix_regen_team_dynamics_effects_active", "regen_team_dynamics_effects", ["active"], unique=False)

    op.create_table(
        "regen_contract_offers",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("transfer_bid_id", sa.String(length=36), nullable=True),
        sa.Column("offering_club_id", sa.String(length=36), nullable=False),
        sa.Column("training_fee_gtex_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("minimum_salary_fancoin_per_year", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("offered_salary_fancoin_per_year", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("contract_years", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_offer_count_visible", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("decision_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="submitted"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transfer_bid_id"], ["transfer_bids.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["offering_club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_regen_contract_offers_regen_id", "regen_contract_offers", ["regen_id"], unique=False)
    op.create_index(
        "ix_regen_contract_offers_offering_club_id",
        "regen_contract_offers",
        ["offering_club_id"],
        unique=False,
    )
    op.create_index("ix_regen_contract_offers_status", "regen_contract_offers", ["status"], unique=False)

    op.create_table(
        "regen_offer_visibility_state",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("training_fee_gtex_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("minimum_salary_fancoin_per_year", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("visible_offer_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_offer_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("regen_id", name="uq_regen_offer_visibility_state_regen_id"),
    )
    op.create_index(
        "ix_regen_offer_visibility_state_offer_count",
        "regen_offer_visibility_state",
        ["visible_offer_count"],
        unique=False,
    )

    op.create_table(
        "currency_conversion_quotes",
        sa.Column("regen_id", sa.String(length=36), nullable=True),
        sa.Column("offering_club_id", sa.String(length=36), nullable=True),
        sa.Column("owner_user_id", sa.String(length=36), nullable=True),
        sa.Column("source_unit", sa.String(length=24), nullable=False, server_default="coin"),
        sa.Column("target_unit", sa.String(length=24), nullable=False, server_default="credit"),
        sa.Column("required_target_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("available_target_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("shortfall_target_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("available_source_amount", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("direct_source_equivalent", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("source_amount_required", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("premium_bps", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("can_cover_shortfall", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("expires_on", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["offering_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_currency_conversion_quotes_regen_id", "currency_conversion_quotes", ["regen_id"], unique=False)
    op.create_index(
        "ix_currency_conversion_quotes_owner_user_id",
        "currency_conversion_quotes",
        ["owner_user_id"],
        unique=False,
    )

    op.create_table(
        "transfer_headline_media_records",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("buying_club_id", sa.String(length=36), nullable=True),
        sa.Column("selling_club_id", sa.String(length=36), nullable=True),
        sa.Column("related_entity_type", sa.String(length=48), nullable=False),
        sa.Column("related_entity_id", sa.String(length=36), nullable=False),
        sa.Column("headline_category", sa.String(length=64), nullable=False),
        sa.Column("announcement_tier", sa.String(length=32), nullable=False, server_default="feed_card"),
        sa.Column("estimated_transfer_fee_eur", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_salary_package_eur", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_total_value_eur", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transfer_fee_gtex_coin", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("salary_package_fancoin", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("headline_text", sa.Text(), nullable=False),
        sa.Column("detail_text", sa.Text(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["buying_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["selling_club_id"], ["club_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_transfer_headline_media_records_regen_id", "transfer_headline_media_records", ["regen_id"], unique=False)
    op.create_index(
        "ix_transfer_headline_media_records_buying_club_id",
        "transfer_headline_media_records",
        ["buying_club_id"],
        unique=False,
    )
    op.create_index(
        "ix_transfer_headline_media_records_tier",
        "transfer_headline_media_records",
        ["announcement_tier"],
        unique=False,
    )

    op.create_table(
        "major_transfer_announcements",
        sa.Column("regen_id", sa.String(length=36), nullable=False),
        sa.Column("headline_record_id", sa.String(length=36), nullable=False),
        sa.Column("story_feed_item_id", sa.String(length=36), nullable=True),
        sa.Column("platform_announcement_id", sa.String(length=36), nullable=True),
        sa.Column("announcement_category", sa.String(length=64), nullable=False),
        sa.Column("announcement_tier", sa.String(length=32), nullable=False, server_default="feed_card"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="published"),
        sa.Column("surfaces_json", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["regen_id"], ["regen_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["headline_record_id"], ["transfer_headline_media_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_feed_item_id"], ["story_feed_items.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["platform_announcement_id"], ["platform_announcements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_major_transfer_announcements_regen_id",
        "major_transfer_announcements",
        ["regen_id"],
        unique=False,
    )
    op.create_index(
        "ix_major_transfer_announcements_tier",
        "major_transfer_announcements",
        ["announcement_tier"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_major_transfer_announcements_tier", table_name="major_transfer_announcements")
    op.drop_index("ix_major_transfer_announcements_regen_id", table_name="major_transfer_announcements")
    op.drop_table("major_transfer_announcements")
    op.drop_index("ix_transfer_headline_media_records_tier", table_name="transfer_headline_media_records")
    op.drop_index("ix_transfer_headline_media_records_buying_club_id", table_name="transfer_headline_media_records")
    op.drop_index("ix_transfer_headline_media_records_regen_id", table_name="transfer_headline_media_records")
    op.drop_table("transfer_headline_media_records")
    op.drop_index("ix_currency_conversion_quotes_owner_user_id", table_name="currency_conversion_quotes")
    op.drop_index("ix_currency_conversion_quotes_regen_id", table_name="currency_conversion_quotes")
    op.drop_table("currency_conversion_quotes")
    op.drop_index("ix_regen_offer_visibility_state_offer_count", table_name="regen_offer_visibility_state")
    op.drop_table("regen_offer_visibility_state")
    op.drop_index("ix_regen_contract_offers_status", table_name="regen_contract_offers")
    op.drop_index("ix_regen_contract_offers_offering_club_id", table_name="regen_contract_offers")
    op.drop_index("ix_regen_contract_offers_regen_id", table_name="regen_contract_offers")
    op.drop_table("regen_contract_offers")
    op.drop_index("ix_regen_team_dynamics_effects_active", table_name="regen_team_dynamics_effects")
    op.drop_index("ix_regen_team_dynamics_effects_club_id", table_name="regen_team_dynamics_effects")
    op.drop_index("ix_regen_team_dynamics_effects_regen_id", table_name="regen_team_dynamics_effects")
    op.drop_table("regen_team_dynamics_effects")
    op.drop_index("ix_regen_big_club_approaches_approaching_club_id", table_name="regen_big_club_approaches")
    op.drop_index("ix_regen_big_club_approaches_regen_id", table_name="regen_big_club_approaches")
    op.drop_table("regen_big_club_approaches")
    op.drop_index(
        "ix_regen_transfer_pressure_states_current_club_id",
        table_name="regen_transfer_pressure_states",
    )
    op.drop_index(
        "ix_regen_transfer_pressure_states_current_state",
        table_name="regen_transfer_pressure_states",
    )
    op.drop_table("regen_transfer_pressure_states")
    op.drop_index("ix_regen_unsettling_events_approaching_club_id", table_name="regen_unsettling_events")
    op.drop_index("ix_regen_unsettling_events_regen_id", table_name="regen_unsettling_events")
    op.drop_table("regen_unsettling_events")
