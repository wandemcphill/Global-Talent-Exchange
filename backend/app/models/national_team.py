from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class NationalTeamCompetition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_competitions"
    __table_args__ = (UniqueConstraint("key", name="uq_national_team_competitions_key"),)

    key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    season_label: Mapped[str] = mapped_column(String(64), nullable=False)
    region_type: Mapped[str] = mapped_column(String(32), nullable=False, default="global", server_default="global")
    age_band: Mapped[str] = mapped_column(String(16), nullable=False, default="senior", server_default="senior")
    format_type: Mapped[str] = mapped_column(String(32), nullable=False, default="cup", server_default="cup")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by_user: Mapped["User | None"] = relationship()
    entries: Mapped[list["NationalTeamEntry"]] = relationship(back_populates="competition", cascade="all, delete-orphan")


class NationalTeamEntry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_entries"
    __table_args__ = (UniqueConstraint("competition_id", "country_code", name="uq_national_team_entries_competition_country"),)

    competition_id: Mapped[str] = mapped_column(String(36), ForeignKey("national_team_competitions.id", ondelete="CASCADE"), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    country_name: Mapped[str] = mapped_column(String(120), nullable=False)
    manager_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    squad_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    competition: Mapped["NationalTeamCompetition"] = relationship(back_populates="entries")
    manager_user: Mapped["User | None"] = relationship()
    squad_members: Mapped[list["NationalTeamSquadMember"]] = relationship(back_populates="entry", cascade="all, delete-orphan")
    manager_history: Mapped[list["NationalTeamManagerHistory"]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class NationalTeamSquadMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_squad_members"
    __table_args__ = (UniqueConstraint("entry_id", "user_id", name="uq_national_team_squad_members_entry_user"),)

    entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("national_team_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="selected", server_default="selected")

    entry: Mapped["NationalTeamEntry"] = relationship(back_populates="squad_members")
    user: Mapped["User"] = relationship()


class NationalTeamManagerHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_manager_history"

    entry_id: Mapped[str] = mapped_column(String(36), ForeignKey("national_team_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False, default="appointed", server_default="appointed")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    entry: Mapped["NationalTeamEntry"] = relationship(back_populates="manager_history")
    user: Mapped["User | None"] = relationship()
