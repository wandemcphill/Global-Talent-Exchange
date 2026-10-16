"""Add organization-based access control tables.

Revision ID: 20260326_0034_role_based_access_control
Revises: 20260324_0033_merge_auth_email_and_bulk_import_heads
Create Date: 2026-03-26 23:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260326_0034_role_based_access_control"
down_revision = "20260324_0033_merge_auth_email_and_bulk_import_heads"
branch_labels = None
depends_on = None


organization_type = sa.Enum("club", "agency", name="organization_type", native_enum=False)
organization_role = sa.Enum("admin", "scout", "club", "agent", name="organization_role", native_enum=False)
organization_invite_role = sa.Enum("admin", "scout", "club", "agent", name="organization_invite_role", native_enum=False)


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("organization_type", organization_type, nullable=False),
        sa.Column("club_profile_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["club_profile_id"], ["club_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("club_profile_id", name="uq_organizations_club_profile_id"),
    )
    op.create_index("ix_organizations_organization_type", "organizations", ["organization_type"], unique=False)
    op.create_index("ix_organizations_name", "organizations", ["name"], unique=False)
    op.create_index("ix_organizations_club_profile_id", "organizations", ["club_profile_id"], unique=False)

    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("role", organization_role, nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_organization_memberships_user_org"),
    )
    op.create_index("ix_organization_memberships_organization_id", "organization_memberships", ["organization_id"], unique=False)
    op.create_index("ix_organization_memberships_user_id", "organization_memberships", ["user_id"], unique=False)
    op.create_index("ix_organization_memberships_role", "organization_memberships", ["role"], unique=False)

    op.create_table(
        "organization_invites",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("role", organization_invite_role, nullable=False),
        sa.Column("invite_code", sa.String(length=96), nullable=False),
        sa.Column("invited_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("accepted_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["accepted_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["invited_by_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code", name="uq_organization_invites_invite_code"),
    )
    op.create_index("ix_organization_invites_organization_id", "organization_invites", ["organization_id"], unique=False)
    op.create_index("ix_organization_invites_email", "organization_invites", ["email"], unique=False)

    op.create_table(
        "player_ownerships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("player_id", sa.String(length=36), nullable=False),
        sa.Column("agent_user_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("assigned_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.ForeignKeyConstraint(["agent_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("player_id", name="uq_player_ownerships_player_id"),
    )
    op.create_index("ix_player_ownerships_agent_user_id", "player_ownerships", ["agent_user_id"], unique=False)
    op.create_index("ix_player_ownerships_organization_id", "player_ownerships", ["organization_id"], unique=False)

    op.create_table(
        "access_audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("target_user_id", sa.String(length=36), nullable=True),
        sa.Column("player_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_access_audit_logs_actor_user_id", "access_audit_logs", ["actor_user_id"], unique=False)
    op.create_index("ix_access_audit_logs_organization_id", "access_audit_logs", ["organization_id"], unique=False)
    op.create_index("ix_access_audit_logs_player_id", "access_audit_logs", ["player_id"], unique=False)
    op.create_index("ix_access_audit_logs_action", "access_audit_logs", ["action"], unique=False)
    op.create_index("ix_access_audit_logs_created_at", "access_audit_logs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_access_audit_logs_created_at", table_name="access_audit_logs")
    op.drop_index("ix_access_audit_logs_action", table_name="access_audit_logs")
    op.drop_index("ix_access_audit_logs_player_id", table_name="access_audit_logs")
    op.drop_index("ix_access_audit_logs_organization_id", table_name="access_audit_logs")
    op.drop_index("ix_access_audit_logs_actor_user_id", table_name="access_audit_logs")
    op.drop_table("access_audit_logs")

    op.drop_index("ix_player_ownerships_organization_id", table_name="player_ownerships")
    op.drop_index("ix_player_ownerships_agent_user_id", table_name="player_ownerships")
    op.drop_table("player_ownerships")

    op.drop_index("ix_organization_invites_email", table_name="organization_invites")
    op.drop_index("ix_organization_invites_organization_id", table_name="organization_invites")
    op.drop_table("organization_invites")

    op.drop_index("ix_organization_memberships_role", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_user_id", table_name="organization_memberships")
    op.drop_index("ix_organization_memberships_organization_id", table_name="organization_memberships")
    op.drop_table("organization_memberships")

    op.drop_index("ix_organizations_club_profile_id", table_name="organizations")
    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_index("ix_organizations_organization_type", table_name="organizations")
    op.drop_table("organizations")
