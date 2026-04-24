from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


def _enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


class StoryEventType(StrEnum):
    UNDERDOG_RUN = "underdog_run"
    GIANT_KILLING = "giant_killing"
    REVENGE_MATCH = "revenge_match"
    STAR_BREAKOUT = "star_breakout"


class RentalContractStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"


class FreePlayerTier(StrEnum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"


class StadiumAdPlacement(StrEnum):
    BILLBOARD = "billboard"
    SIDELINE = "sideline"
    DIGITAL_SCREEN = "digital_screen"


class RentalContract(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_rental_contracts"
    __table_args__ = (
        Index("ix_national_team_rental_contracts_tournament_id", "tournament_id"),
        Index("ix_national_team_rental_contracts_entry_id", "entry_id"),
        Index("ix_national_team_rental_contracts_user_id", "user_id"),
        Index("ix_national_team_rental_contracts_player_id", "player_id"),
        Index("ix_national_team_rental_contracts_status", "status"),
    )

    player_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    tournament_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("national_team_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    entry_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_team_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    loan_price_coin: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal("0.0000"), server_default="0.0000"
    )
    is_free_player: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    free_player_tier: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[RentalContractStatus] = mapped_column(
        Enum(
            RentalContractStatus,
            name="national_team_rental_contract_status",
            native_enum=False,
            values_callable=_enum_values,
        ),
        nullable=False,
        default=RentalContractStatus.ACTIVE,
        server_default=RentalContractStatus.ACTIVE.value,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class NationalTeamRentalSquadMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "national_team_rental_squad_members"
    __table_args__ = (
        UniqueConstraint("entry_id", "player_id", name="uq_national_team_rental_squad_members_entry_player"),
        UniqueConstraint("rental_contract_id", name="uq_national_team_rental_squad_members_contract"),
        Index("ix_national_team_rental_squad_members_entry_id", "entry_id"),
    )

    entry_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("national_team_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    rental_contract_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("national_team_rental_contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    player_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
    )
    player_name: Mapped[str] = mapped_column(String(160), nullable=False)
    overall_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="rental", server_default="rental")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="selected", server_default="selected")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StoryEvent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournament_story_events"
    __table_args__ = (
        Index("ix_tournament_story_events_competition_id", "competition_id"),
        Index("ix_tournament_story_events_match_id", "match_id"),
        Index("ix_tournament_story_events_type", "type"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("national_team_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("competition_matches.id", ondelete="SET NULL"),
        nullable=True,
    )
    type: Mapped[StoryEventType] = mapped_column(
        Enum(StoryEventType, name="tournament_story_event_type", native_enum=False, values_callable=_enum_values),
        nullable=False,
    )
    entities: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class TournamentTheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "tournament_themes"
    __table_args__ = (
        UniqueConstraint("competition_id", name="uq_tournament_themes_competition_id"),
        Index("ix_tournament_themes_competition_id", "competition_id"),
    )

    competition_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("national_team_competitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    video_asset_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    audio_theme_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    visual_style: Mapped[str] = mapped_column(
        String(64), nullable=False, default="gtex_default", server_default="gtex_default"
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class StadiumAd(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "stadium_ads"
    __table_args__ = (
        Index("ix_stadium_ads_competition_id", "competition_id"),
        Index("ix_stadium_ads_placement", "placement"),
        Index("ix_stadium_ads_priority", "priority"),
    )

    competition_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("national_team_competitions.id", ondelete="CASCADE"),
        nullable=True,
    )
    asset_url: Mapped[str] = mapped_column(String(255), nullable=False)
    placement: Mapped[StadiumAdPlacement] = mapped_column(
        Enum(StadiumAdPlacement, name="stadium_ad_placement", native_enum=False, values_callable=_enum_values),
        nullable=False,
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100, server_default="100")
    rotation_interval_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=30, server_default="30")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


__all__ = [
    "FreePlayerTier",
    "NationalTeamRentalSquadMember",
    "RentalContract",
    "RentalContractStatus",
    "StadiumAd",
    "StadiumAdPlacement",
    "StoryEvent",
    "StoryEventType",
    "TournamentTheme",
]
