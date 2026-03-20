"""governance and dispute engine

Revision ID: 20260314_0035
Revises: 20260314_0034
Create Date: 2026-03-14 17:15:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260314_0035"
down_revision = "20260314_0034"
branch_labels = None
depends_on = None


governanceproposalscope = sa.Enum("club", "platform", name="governanceproposalscope")
governanceproposalstatus = sa.Enum("draft", "open", "closed", "accepted", "rejected", name="governanceproposalstatus")
governancevotechoice = sa.Enum("yes", "no", "abstain", name="governancevotechoice")
dispute_status = sa.Enum("open", "awaiting_user", "awaiting_admin", "resolved", "closed", name="dispute_status", native_enum=False)


def upgrade() -> None:
    bind = op.get_bind()
    governanceproposalscope.create(bind, checkfirst=True)
    governanceproposalstatus.create(bind, checkfirst=True)
    governancevotechoice.create(bind, checkfirst=True)
    dispute_status.create(bind, checkfirst=True)

    op.create_table(
        "governance_proposals",
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("proposer_user_id", sa.String(length=36), nullable=False),
        sa.Column("scope", governanceproposalscope, nullable=False),
        sa.Column("status", governanceproposalstatus, nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("voting_starts_at_iso", sa.String(length=40), nullable=True),
        sa.Column("voting_ends_at_iso", sa.String(length=40), nullable=True),
        sa.Column("minimum_tokens_required", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("quorum_token_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("yes_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("abstain_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unique_voter_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposer_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_governance_proposals_club_id"), "governance_proposals", ["club_id"], unique=False)
    op.create_index(op.f("ix_governance_proposals_proposer_user_id"), "governance_proposals", ["proposer_user_id"], unique=False)

    op.create_table(
        "governance_votes",
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("voter_user_id", sa.String(length=36), nullable=False),
        sa.Column("club_id", sa.String(length=36), nullable=True),
        sa.Column("choice", governancevotechoice, nullable=False),
        sa.Column("token_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("influence_weight", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("is_proxy_vote", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["club_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_id"], ["governance_proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["voter_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "voter_user_id", name="uq_governance_votes_proposal_user"),
    )
    op.create_index(op.f("ix_governance_votes_club_id"), "governance_votes", ["club_id"], unique=False)
    op.create_index(op.f("ix_governance_votes_proposal_id"), "governance_votes", ["proposal_id"], unique=False)
    op.create_index(op.f("ix_governance_votes_voter_user_id"), "governance_votes", ["voter_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_governance_votes_voter_user_id"), table_name="governance_votes")
    op.drop_index(op.f("ix_governance_votes_proposal_id"), table_name="governance_votes")
    op.drop_index(op.f("ix_governance_votes_club_id"), table_name="governance_votes")
    op.drop_table("governance_votes")

    op.drop_index(op.f("ix_governance_proposals_proposer_user_id"), table_name="governance_proposals")
    op.drop_index(op.f("ix_governance_proposals_club_id"), table_name="governance_proposals")
    op.drop_table("governance_proposals")

    bind = op.get_bind()
    dispute_status.drop(bind, checkfirst=True)
    governancevotechoice.drop(bind, checkfirst=True)
    governanceproposalstatus.drop(bind, checkfirst=True)
    governanceproposalscope.drop(bind, checkfirst=True)
