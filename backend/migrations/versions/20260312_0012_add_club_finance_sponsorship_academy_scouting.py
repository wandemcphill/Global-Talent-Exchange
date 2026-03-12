"""Add club finance, sponsorship, academy, and scouting tables."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260312_0012"
down_revision = "20260312_0011"
branch_labels = None
depends_on = None

_CLUB_FINANCE_ACCOUNT_TYPES = (
    "operating_balance",
    "sponsorship_income",
    "competition_income",
    "cosmetic_income",
    "academy_spend",
    "scouting_spend",
    "branding_spend",
    "facilities_spend",
    "transfer_income",
    "transfer_spend",
)
_CLUB_FINANCE_ENTRY_TYPES = (
    "sponsorship_credit",
    "competition_reward_credit",
    "catalog_purchase_debit",
    "academy_program_debit",
    "scouting_assignment_debit",
    "manual_admin_adjustment",
    "refund",
    "reserve_hold",
)
_SPONSORSHIP_STATUSES = ("draft", "pending_approval", "active", "paused", "completed", "cancelled", "expired")
_SPONSORSHIP_ASSET_TYPES = (
    "jersey_front",
    "jersey_back",
    "sleeve_slot",
    "club_banner",
    "profile_header",
    "showcase_backdrop",
    "tournament_card_slot",
)
_ACADEMY_PLAYER_STATUSES = ("trialist", "enrolled", "developing", "standout", "promoted", "released")
_ACADEMY_PROGRAM_TYPES = (
    "fundamentals",
    "elite_development",
    "tactical_program",
    "physical_program",
    "finishing_school",
    "goalkeeper_program",
)
_SCOUT_ASSIGNMENT_STATUSES = ("planned", "active", "paused", "completed", "cancelled")
_SCOUTING_REGION_TYPES = ("domestic", "regional", "international", "diaspora")
_YOUTH_PROSPECT_RATING_BANDS = ("foundation", "development", "high_upside", "elite")
_PLAYER_PATHWAY_STAGES = ("discovered", "shortlisted", "invited", "trialing", "academy_signed", "promoted", "released")


def _as_check_values(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    op.create_table(
        "club_finance_accounts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("balance_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("allow_negative", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            f"account_type IN ({_as_check_values(_CLUB_FINANCE_ACCOUNT_TYPES)})",
            name="club_finance_account_type_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_club_finance_accounts"),
        sa.UniqueConstraint("club_id", "account_type", name="uq_club_finance_accounts_club_account_type"),
    )
    op.create_index("ix_club_finance_accounts_club_id", "club_finance_accounts", ["club_id"], unique=False)

    op.create_table(
        "club_finance_ledger_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("account_id", sa.String(length=36), nullable=False),
        sa.Column("account_type", sa.String(length=32), nullable=False),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("reference_id", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"account_type IN ({_as_check_values(_CLUB_FINANCE_ACCOUNT_TYPES)})",
            name="club_finance_ledger_account_type_allowed",
        ),
        sa.CheckConstraint(
            f"entry_type IN ({_as_check_values(_CLUB_FINANCE_ENTRY_TYPES)})",
            name="club_finance_entry_type_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["club_finance_accounts.id"],
            name="fk_club_finance_ledger_entries_account_id_club_finance_accounts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_club_finance_ledger_entries"),
    )
    op.create_index("ix_club_finance_ledger_entries_transaction_id", "club_finance_ledger_entries", ["transaction_id"], unique=False)
    op.create_index("ix_club_finance_ledger_entries_club_id", "club_finance_ledger_entries", ["club_id"], unique=False)
    op.create_index("ix_club_finance_ledger_entries_account_id", "club_finance_ledger_entries", ["account_id"], unique=False)
    op.create_index("ix_club_finance_ledger_entries_reference_id", "club_finance_ledger_entries", ["reference_id"], unique=False)

    op.create_table(
        "club_budget_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("total_budget_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("academy_allocation_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("scouting_allocation_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sponsorship_commitment_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("available_budget_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_club_budget_snapshots"),
    )
    op.create_index("ix_club_budget_snapshots_club_id", "club_budget_snapshots", ["club_id"], unique=False)

    op.create_table(
        "club_cashflow_summaries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("total_income_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_expense_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("net_cashflow_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("sponsorship_income_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("competition_income_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("academy_spend_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("scouting_spend_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_club_cashflow_summaries"),
    )
    op.create_index("ix_club_cashflow_summaries_club_id", "club_cashflow_summaries", ["club_id"], unique=False)

    op.create_table(
        "club_sponsorship_packages",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("base_amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("default_duration_months", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("payout_schedule", sa.String(length=24), server_default=sa.text("'monthly'"), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            f"asset_type IN ({_as_check_values(_SPONSORSHIP_ASSET_TYPES)})",
            name="club_sponsorship_package_asset_type_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_club_sponsorship_packages"),
        sa.UniqueConstraint("code", name="uq_club_sponsorship_packages_code"),
    )
    op.create_index("ix_club_sponsorship_packages_code", "club_sponsorship_packages", ["code"], unique=False)

    op.create_table(
        "club_sponsorship_contracts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("package_id", sa.String(length=36), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("sponsor_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("contract_amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("currency", sa.String(length=12), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("duration_months", sa.Integer(), server_default=sa.text("3"), nullable=False),
        sa.Column("payout_schedule", sa.String(length=24), server_default=sa.text("'monthly'"), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("moderation_required", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("moderation_status", sa.String(length=32), server_default=sa.text("'not_required'"), nullable=False),
        sa.Column("custom_copy", sa.String(length=80), nullable=True),
        sa.Column("custom_logo_url", sa.String(length=255), nullable=True),
        sa.Column("performance_bonus_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("settled_amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("outstanding_amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint(
            f"asset_type IN ({_as_check_values(_SPONSORSHIP_ASSET_TYPES)})",
            name="club_sponsorship_contract_asset_type_allowed",
        ),
        sa.CheckConstraint(
            f"status IN ({_as_check_values(_SPONSORSHIP_STATUSES)})",
            name="club_sponsorship_contract_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["package_id"],
            ["club_sponsorship_packages.id"],
            name="fk_club_sponsorship_contracts_package_id_club_sponsorship_packages",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_club_sponsorship_contracts"),
    )
    op.create_index("ix_club_sponsorship_contracts_club_id", "club_sponsorship_contracts", ["club_id"], unique=False)
    op.create_index("ix_club_sponsorship_contracts_package_id", "club_sponsorship_contracts", ["package_id"], unique=False)

    op.create_table(
        "club_sponsorship_assets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("slot_code", sa.String(length=80), nullable=False),
        sa.Column("is_visible", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.Column("moderation_required", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("moderation_status", sa.String(length=32), server_default=sa.text("'not_required'"), nullable=False),
        sa.Column("rendered_text", sa.String(length=120), nullable=True),
        sa.Column("asset_url", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            f"asset_type IN ({_as_check_values(_SPONSORSHIP_ASSET_TYPES)})",
            name="club_sponsorship_asset_type_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["club_sponsorship_contracts.id"],
            name="fk_club_sponsorship_assets_contract_id_club_sponsorship_contracts",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_club_sponsorship_assets"),
    )
    op.create_index("ix_club_sponsorship_assets_club_id", "club_sponsorship_assets", ["club_id"], unique=False)
    op.create_index("ix_club_sponsorship_assets_contract_id", "club_sponsorship_assets", ["contract_id"], unique=False)
    op.create_index("ix_club_sponsorship_assets_slot_code", "club_sponsorship_assets", ["slot_code"], unique=False)

    op.create_table(
        "club_sponsorship_payouts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("contract_id", sa.String(length=36), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("amount_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("status", sa.String(length=24), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["contract_id"],
            ["club_sponsorship_contracts.id"],
            name="fk_club_sponsorship_payouts_contract_id_club_sponsorship_contracts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_club_sponsorship_payouts"),
    )
    op.create_index("ix_club_sponsorship_payouts_contract_id", "club_sponsorship_payouts", ["contract_id"], unique=False)

    op.create_table(
        "academy_programs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("program_type", sa.String(length=32), nullable=False),
        sa.Column("budget_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("cycle_length_weeks", sa.Integer(), server_default=sa.text("6"), nullable=False),
        sa.Column("focus_attributes_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            f"program_type IN ({_as_check_values(_ACADEMY_PROGRAM_TYPES)})",
            name="academy_program_type_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_academy_programs"),
    )
    op.create_index("ix_academy_programs_club_id", "academy_programs", ["club_id"], unique=False)

    op.create_table(
        "academy_players",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("program_id", sa.String(length=36), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("primary_position", sa.String(length=40), nullable=False),
        sa.Column("secondary_position", sa.String(length=40), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("overall_rating", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("readiness_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completed_cycles", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("development_attributes_json", sa.JSON(), nullable=False),
        sa.Column("pathway_note", sa.String(length=255), nullable=True),
        sa.CheckConstraint(
            f"status IN ({_as_check_values(_ACADEMY_PLAYER_STATUSES)})",
            name="academy_player_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["academy_programs.id"],
            name="fk_academy_players_program_id_academy_programs",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_academy_players"),
    )
    op.create_index("ix_academy_players_club_id", "academy_players", ["club_id"], unique=False)
    op.create_index("ix_academy_players_program_id", "academy_players", ["program_id"], unique=False)

    op.create_table(
        "academy_training_cycles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("program_id", sa.String(length=36), nullable=False),
        sa.Column("cycle_index", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("focus_attributes_json", sa.JSON(), nullable=False),
        sa.Column("player_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("average_delta", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["program_id"],
            ["academy_programs.id"],
            name="fk_academy_training_cycles_program_id_academy_programs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_academy_training_cycles"),
    )
    op.create_index("ix_academy_training_cycles_club_id", "academy_training_cycles", ["club_id"], unique=False)
    op.create_index("ix_academy_training_cycles_program_id", "academy_training_cycles", ["program_id"], unique=False)

    op.create_table(
        "academy_player_progress",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("academy_player_id", sa.String(length=36), nullable=False),
        sa.Column("training_cycle_id", sa.String(length=36), nullable=True),
        sa.Column("status_before", sa.String(length=32), nullable=False),
        sa.Column("status_after", sa.String(length=32), nullable=False),
        sa.Column("delta_overall", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            f"status_before IN ({_as_check_values(_ACADEMY_PLAYER_STATUSES)})",
            name="academy_player_progress_status_before_allowed",
        ),
        sa.CheckConstraint(
            f"status_after IN ({_as_check_values(_ACADEMY_PLAYER_STATUSES)})",
            name="academy_player_progress_status_after_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["academy_player_id"],
            ["academy_players.id"],
            name="fk_academy_player_progress_academy_player_id_academy_players",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["training_cycle_id"],
            ["academy_training_cycles.id"],
            name="fk_academy_player_progress_training_cycle_id_academy_training_cycles",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_academy_player_progress"),
    )
    op.create_index("ix_academy_player_progress_academy_player_id", "academy_player_progress", ["academy_player_id"], unique=False)
    op.create_index("ix_academy_player_progress_training_cycle_id", "academy_player_progress", ["training_cycle_id"], unique=False)

    op.create_table(
        "academy_graduation_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("academy_player_id", sa.String(length=36), nullable=False),
        sa.Column("from_status", sa.String(length=32), nullable=False),
        sa.Column("to_status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.CheckConstraint(
            f"from_status IN ({_as_check_values(_ACADEMY_PLAYER_STATUSES)})",
            name="academy_graduation_from_status_allowed",
        ),
        sa.CheckConstraint(
            f"to_status IN ({_as_check_values(_ACADEMY_PLAYER_STATUSES)})",
            name="academy_graduation_to_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["academy_player_id"],
            ["academy_players.id"],
            name="fk_academy_graduation_events_academy_player_id_academy_players",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_academy_graduation_events"),
    )
    op.create_index("ix_academy_graduation_events_club_id", "academy_graduation_events", ["club_id"], unique=False)
    op.create_index("ix_academy_graduation_events_academy_player_id", "academy_graduation_events", ["academy_player_id"], unique=False)

    op.create_table(
        "scouting_regions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("region_type", sa.String(length=32), nullable=False),
        sa.Column("territory_codes_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            f"region_type IN ({_as_check_values(_SCOUTING_REGION_TYPES)})",
            name="scouting_region_type_allowed",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scouting_regions"),
        sa.UniqueConstraint("code", name="uq_scouting_regions_code"),
    )
    op.create_index("ix_scouting_regions_code", "scouting_regions", ["code"], unique=False)

    op.create_table(
        "scout_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("region_id", sa.String(length=36), nullable=True),
        sa.Column("region_code", sa.String(length=64), nullable=False),
        sa.Column("region_name", sa.String(length=120), nullable=False),
        sa.Column("focus_area", sa.String(length=120), nullable=False),
        sa.Column("budget_minor", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("scout_count", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("report_confidence_floor_bps", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"status IN ({_as_check_values(_SCOUT_ASSIGNMENT_STATUSES)})",
            name="scout_assignment_status_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["region_id"],
            ["scouting_regions.id"],
            name="fk_scout_assignments_region_id_scouting_regions",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_scout_assignments"),
    )
    op.create_index("ix_scout_assignments_club_id", "scout_assignments", ["club_id"], unique=False)
    op.create_index("ix_scout_assignments_region_id", "scout_assignments", ["region_id"], unique=False)

    op.create_table(
        "youth_prospects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("assignment_id", sa.String(length=36), nullable=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("nationality_code", sa.String(length=12), nullable=False),
        sa.Column("region_label", sa.String(length=120), nullable=False),
        sa.Column("primary_position", sa.String(length=40), nullable=False),
        sa.Column("secondary_position", sa.String(length=40), nullable=True),
        sa.Column("rating_band", sa.String(length=32), nullable=False),
        sa.Column("development_traits_json", sa.JSON(), nullable=False),
        sa.Column("pathway_stage", sa.String(length=32), nullable=False),
        sa.Column("scouting_source", sa.String(length=80), nullable=False),
        sa.Column("follow_priority", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("academy_player_id", sa.String(length=36), nullable=True),
        sa.CheckConstraint(
            f"rating_band IN ({_as_check_values(_YOUTH_PROSPECT_RATING_BANDS)})",
            name="youth_prospect_rating_band_allowed",
        ),
        sa.CheckConstraint(
            f"pathway_stage IN ({_as_check_values(_PLAYER_PATHWAY_STAGES)})",
            name="youth_prospect_pathway_stage_allowed",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["scout_assignments.id"],
            name="fk_youth_prospects_assignment_id_scout_assignments",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_youth_prospects"),
    )
    op.create_index("ix_youth_prospects_club_id", "youth_prospects", ["club_id"], unique=False)
    op.create_index("ix_youth_prospects_assignment_id", "youth_prospects", ["assignment_id"], unique=False)
    op.create_index("ix_youth_prospects_academy_player_id", "youth_prospects", ["academy_player_id"], unique=False)

    op.create_table(
        "youth_prospect_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("prospect_id", sa.String(length=36), nullable=False),
        sa.Column("assignment_id", sa.String(length=36), nullable=True),
        sa.Column("confidence_bps", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("summary_text", sa.String(length=255), nullable=False),
        sa.Column("strengths_json", sa.JSON(), nullable=False),
        sa.Column("development_flags_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["prospect_id"],
            ["youth_prospects.id"],
            name="fk_youth_prospect_reports_prospect_id_youth_prospects",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assignment_id"],
            ["scout_assignments.id"],
            name="fk_youth_prospect_reports_assignment_id_scout_assignments",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_youth_prospect_reports"),
    )
    op.create_index("ix_youth_prospect_reports_prospect_id", "youth_prospect_reports", ["prospect_id"], unique=False)
    op.create_index("ix_youth_prospect_reports_assignment_id", "youth_prospect_reports", ["assignment_id"], unique=False)

    op.create_table(
        "youth_pipeline_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=False),
        sa.Column("funnel_json", sa.JSON(), nullable=False),
        sa.Column("academy_conversion_rate_bps", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("promotion_rate_bps", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_youth_pipeline_snapshots"),
    )
    op.create_index("ix_youth_pipeline_snapshots_club_id", "youth_pipeline_snapshots", ["club_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_youth_pipeline_snapshots_club_id", table_name="youth_pipeline_snapshots")
    op.drop_table("youth_pipeline_snapshots")

    op.drop_index("ix_youth_prospect_reports_assignment_id", table_name="youth_prospect_reports")
    op.drop_index("ix_youth_prospect_reports_prospect_id", table_name="youth_prospect_reports")
    op.drop_table("youth_prospect_reports")

    op.drop_index("ix_youth_prospects_academy_player_id", table_name="youth_prospects")
    op.drop_index("ix_youth_prospects_assignment_id", table_name="youth_prospects")
    op.drop_index("ix_youth_prospects_club_id", table_name="youth_prospects")
    op.drop_table("youth_prospects")

    op.drop_index("ix_scout_assignments_region_id", table_name="scout_assignments")
    op.drop_index("ix_scout_assignments_club_id", table_name="scout_assignments")
    op.drop_table("scout_assignments")

    op.drop_index("ix_scouting_regions_code", table_name="scouting_regions")
    op.drop_table("scouting_regions")

    op.drop_index("ix_academy_graduation_events_academy_player_id", table_name="academy_graduation_events")
    op.drop_index("ix_academy_graduation_events_club_id", table_name="academy_graduation_events")
    op.drop_table("academy_graduation_events")

    op.drop_index("ix_academy_player_progress_training_cycle_id", table_name="academy_player_progress")
    op.drop_index("ix_academy_player_progress_academy_player_id", table_name="academy_player_progress")
    op.drop_table("academy_player_progress")

    op.drop_index("ix_academy_training_cycles_program_id", table_name="academy_training_cycles")
    op.drop_index("ix_academy_training_cycles_club_id", table_name="academy_training_cycles")
    op.drop_table("academy_training_cycles")

    op.drop_index("ix_academy_players_program_id", table_name="academy_players")
    op.drop_index("ix_academy_players_club_id", table_name="academy_players")
    op.drop_table("academy_players")

    op.drop_index("ix_academy_programs_club_id", table_name="academy_programs")
    op.drop_table("academy_programs")

    op.drop_index("ix_club_sponsorship_payouts_contract_id", table_name="club_sponsorship_payouts")
    op.drop_table("club_sponsorship_payouts")

    op.drop_index("ix_club_sponsorship_assets_slot_code", table_name="club_sponsorship_assets")
    op.drop_index("ix_club_sponsorship_assets_contract_id", table_name="club_sponsorship_assets")
    op.drop_index("ix_club_sponsorship_assets_club_id", table_name="club_sponsorship_assets")
    op.drop_table("club_sponsorship_assets")

    op.drop_index("ix_club_sponsorship_contracts_package_id", table_name="club_sponsorship_contracts")
    op.drop_index("ix_club_sponsorship_contracts_club_id", table_name="club_sponsorship_contracts")
    op.drop_table("club_sponsorship_contracts")

    op.drop_index("ix_club_sponsorship_packages_code", table_name="club_sponsorship_packages")
    op.drop_table("club_sponsorship_packages")

    op.drop_index("ix_club_cashflow_summaries_club_id", table_name="club_cashflow_summaries")
    op.drop_table("club_cashflow_summaries")

    op.drop_index("ix_club_budget_snapshots_club_id", table_name="club_budget_snapshots")
    op.drop_table("club_budget_snapshots")

    op.drop_index("ix_club_finance_ledger_entries_reference_id", table_name="club_finance_ledger_entries")
    op.drop_index("ix_club_finance_ledger_entries_account_id", table_name="club_finance_ledger_entries")
    op.drop_index("ix_club_finance_ledger_entries_club_id", table_name="club_finance_ledger_entries")
    op.drop_index("ix_club_finance_ledger_entries_transaction_id", table_name="club_finance_ledger_entries")
    op.drop_table("club_finance_ledger_entries")

    op.drop_index("ix_club_finance_accounts_club_id", table_name="club_finance_accounts")
    op.drop_table("club_finance_accounts")
