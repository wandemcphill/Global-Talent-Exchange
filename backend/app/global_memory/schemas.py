from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema


class CompetitionListItemView(CommonSchema):
    id: str
    name: str
    slug: str
    competition_type: str
    age_bracket: str | None = None
    country_code: str | None = None
    is_major: bool


class CompetitionEnterRequest(CommonSchema):
    user_id: str
    competition_id: str
    player_id: str
    performance_score: float = Field(default=0.0, ge=0.0, le=100.0)
    won_title: bool = False


class PlayerRentRequest(CommonSchema):
    user_id: str
    competition_id: str
    player_id: str
    rental_fee_minor: int = Field(default=0, ge=0)
    performance_score: float = Field(default=0.0, ge=0.0, le=100.0)


class PlayerHistoryEntryView(CommonSchema):
    event: str
    competition: str
    created_at: datetime


class RegenEvolutionView(CommonSchema):
    regen_profile_id: str
    regen_type: str
    performance_score: float
    performance_threshold: float
    titles: int
    gsi: int | None = None
    tradable: bool
    unique: bool
    hall_of_fame: bool


class PlayerHistoryResponseView(CommonSchema):
    player_id: str
    display_name: str
    history: tuple[PlayerHistoryEntryView, ...] = Field(default_factory=tuple)
    evolution: RegenEvolutionView | None = None


class DynastyTitleView(CommonSchema):
    competition_id: str
    competition_name: str
    age_bracket: str | None = None
    won_at: datetime


class UserDynastyView(CommonSchema):
    user_id: str
    total_titles: int
    youth_titles: int
    senior_titles: int
    dynasty_label: str
    title_history: tuple[DynastyTitleView, ...] = Field(default_factory=tuple)


class CompetitionEntryResultView(CommonSchema):
    entry_id: str
    competition_id: str
    competition_name: str
    player_id: str
    status: str
    title_awarded: bool
    performance_score: float
    dynasty: UserDynastyView
    evolution: RegenEvolutionView | None = None


class PlayerRentResultView(CommonSchema):
    rental_id: str
    competition_id: str
    competition_name: str
    player_id: str
    rental_fee_minor: int
    status: str
    performance_score: float
    evolution: RegenEvolutionView | None = None


class NationalPoolPlayerView(CommonSchema):
    player_id: str
    display_name: str
    country_code: str | None = None
    current_club_id: str | None = None
    current_competition_id: str | None = None
    is_regen: bool
    tradable: bool
    unique: bool
    hall_of_fame: bool
    gsi: int | None = None

