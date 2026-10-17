from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin, utcnow


class OwnerClubStaff(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_club_staff"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(8), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    personality_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    salary_per_cycle: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    last_paid_day: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    hired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerDelegationPolicy(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_delegation_policies"
    __table_args__ = (UniqueConstraint("club_id", "task", name="uq_owner_delegation_club_task"),)

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    budget_cap: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerDelegatedAction(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_delegated_actions"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
    task: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    recommendation: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class OwnerShowroomLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "owner_showroom_links"

    club_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(24), nullable=False, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
