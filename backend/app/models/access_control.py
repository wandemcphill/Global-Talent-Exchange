from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class OrganizationType(StrEnum):
    CLUB = "club"
    AGENCY = "agency"


class OrganizationRole(StrEnum):
    ADMIN = "admin"
    SCOUT = "scout"
    CLUB = "club"
    AGENT = "agent"


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("club_profile_id", name="uq_organizations_club_profile_id"),
        Index("ix_organizations_organization_type", "organization_type"),
        Index("ix_organizations_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    organization_type: Mapped[OrganizationType] = mapped_column(
        Enum(OrganizationType, name="organization_type", native_enum=False),
        nullable=False,
    )
    club_profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("club_profiles.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class OrganizationMembership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_organization_memberships_user_org"),
        Index("ix_organization_memberships_organization_id", "organization_id"),
        Index("ix_organization_memberships_user_id", "user_id"),
        Index("ix_organization_memberships_role", "role"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(OrganizationRole, name="organization_role", native_enum=False),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    invited_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class OrganizationInvite(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "organization_invites"
    __table_args__ = (
        UniqueConstraint("invite_code", name="uq_organization_invites_invite_code"),
        Index("ix_organization_invites_organization_id", "organization_id"),
        Index("ix_organization_invites_email", "email"),
    )

    organization_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[OrganizationRole] = mapped_column(
        Enum(OrganizationRole, name="organization_invite_role", native_enum=False),
        nullable=False,
    )
    invite_code: Mapped[str] = mapped_column(String(96), nullable=False)
    invited_by_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    accepted_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PlayerOwnership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "player_ownerships"
    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_ownerships_player_id"),
        Index("ix_player_ownerships_agent_user_id", "agent_user_id"),
        Index("ix_player_ownerships_organization_id", "organization_id"),
    )

    player_id: Mapped[str] = mapped_column(String(36), nullable=False)
    agent_user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_by_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class AccessAuditLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "access_audit_logs"
    __table_args__ = (
        Index("ix_access_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_access_audit_logs_organization_id", "organization_id"),
        Index("ix_access_audit_logs_player_id", "player_id"),
        Index("ix_access_audit_logs_action", "action"),
        Index("ix_access_audit_logs_created_at", "created_at"),
    )

    actor_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    player_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


__all__ = [
    "AccessAuditLog",
    "Organization",
    "OrganizationInvite",
    "OrganizationMembership",
    "OrganizationRole",
    "OrganizationType",
    "PlayerOwnership",
]
