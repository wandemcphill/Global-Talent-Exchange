"""Persist per-player performance for completed competition matches.

Revision ID: 20260902_0117_player_match_performance
Revises: 20260828_0116_economic_policy_collapse_hardening

Creates ``player_match_performances``, the record that closes the first break in
the chain ``match -> performance -> form -> valuation -> market -> ownership``.

Before this table existed the match engine rated every player on every simulated
match and then discarded the result: ratings were attached to the HTTP response
and never written anywhere, so nothing downstream could see them.

Rows are written only for competition matches and only for canonical
``ingestion_players`` ids. ``player_id`` deliberately carries no foreign key: it is
validated by the recorder before insert, which gives the same guarantee without
letting one unrecognised id abort settlement of an otherwise valid match.

Idempotent: creating a table that already exists is skipped.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260902_0117_player_match_performance"
down_revision = "20260828_0116_economic_policy_collapse_hardening"
branch_labels = None
depends_on = None

TABLE_NAME = "player_match_performances"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME in inspector.get_table_names():
        return

    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("player_name", sa.String(length=160), nullable=True),
        sa.Column("match_id", sa.String(length=36), nullable=False),
        sa.Column("competition_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("started", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("minutes_played", sa.Integer(), server_default="0", nullable=False),
        sa.Column("goals", sa.Integer(), server_default="0", nullable=False),
        sa.Column("assists", sa.Integer(), server_default="0", nullable=False),
        sa.Column("saves", sa.Integer(), server_default="0", nullable=False),
        sa.Column("shots_on_target", sa.Integer(), server_default="0", nullable=False),
        sa.Column("key_passes", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tackles_won", sa.Integer(), server_default="0", nullable=False),
        sa.Column("interceptions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("yellow_cards", sa.Integer(), server_default="0", nullable=False),
        sa.Column("red_card", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("xg", sa.Float(), server_default="0", nullable=False),
        sa.Column("eligible_for_valuation", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("ineligibility_reason", sa.String(length=48), nullable=True),
        sa.ForeignKeyConstraint(
            ["match_id"],
            ["competition_matches.id"],
            name="fk_player_match_performances_match_id_competition_matches",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_player_match_performances"),
        sa.UniqueConstraint("player_id", "match_id", name="uq_player_match_performances_player_match"),
    )
    op.create_index(
        "ix_player_match_performances_player_occurred",
        TABLE_NAME,
        ["player_id", "occurred_at"],
    )
    op.create_index(
        "ix_player_match_performances_eligible",
        TABLE_NAME,
        ["player_id", "eligible_for_valuation"],
    )
    op.create_index(op.f("ix_player_match_performances_player_id"), TABLE_NAME, ["player_id"])
    op.create_index(op.f("ix_player_match_performances_match_id"), TABLE_NAME, ["match_id"])
    op.create_index(op.f("ix_player_match_performances_competition_id"), TABLE_NAME, ["competition_id"])
    op.create_index(op.f("ix_player_match_performances_club_id"), TABLE_NAME, ["club_id"])
    op.create_index(op.f("ix_player_match_performances_occurred_at"), TABLE_NAME, ["occurred_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if TABLE_NAME not in inspector.get_table_names():
        return
    op.drop_table(TABLE_NAME)
