from __future__ import annotations

from datetime import date, datetime

from pydantic import Field

from app.common.schemas.base import CommonSchema


class CompetitionListItemView(CommonSchema):
    id: str
    global_competition_id: str
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
    event_type: str
    event: str
    competition: str
    global_player_id: str
    global_competition_id: str | None = None
    global_match_id: str | None = None
    timeline_json: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class PlayerCareerArcView(CommonSchema):
    age: int | None = None
    peak_age_range: tuple[int, int] = (25, 29)
    decline_curve: str
    injury_risk: str


class PlayerPerformanceTimelineEntryView(CommonSchema):
    season_label: str
    club_id: str | None = None
    club_name: str | None = None
    competition_id: str | None = None
    competition_name: str | None = None
    appearances: int = 0
    goals: int = 0
    assists: int = 0
    average_rating: float | None = None


class ClubHistoryView(CommonSchema):
    club_id: str | None = None
    club_name: str


class CompetitionHistoryView(CommonSchema):
    competition_id: str | None = None
    global_competition_id: str | None = None
    competition_name: str


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
    scarcity_tier: str
    unique_traits: tuple[str, ...] = Field(default_factory=tuple)
    legacy_boost_score: float = 0.0


class PlayerHistoryResponseView(CommonSchema):
    player_id: str
    global_player_id: str
    display_name: str
    clubs: tuple[ClubHistoryView, ...] = Field(default_factory=tuple)
    competitions: tuple[CompetitionHistoryView, ...] = Field(default_factory=tuple)
    titles: int = 0
    performance_timeline: tuple[PlayerPerformanceTimelineEntryView, ...] = Field(default_factory=tuple)
    career_arc: PlayerCareerArcView
    history: tuple[PlayerHistoryEntryView, ...] = Field(default_factory=tuple)
    evolution: RegenEvolutionView | None = None


class DynastyTitleView(CommonSchema):
    competition_id: str
    global_competition_id: str
    competition_name: str
    age_bracket: str | None = None
    won_at: datetime


class UserDynastyView(CommonSchema):
    user_id: str
    total_titles: int
    youth_titles: int
    senior_titles: int
    earnings_minor: int
    player_development_score: float
    legacy_boost_score: float
    dynasty_label: str
    title_history: tuple[DynastyTitleView, ...] = Field(default_factory=tuple)


class DynastyLeaderboardEntryView(CommonSchema):
    rank: int
    user_id: str
    total_titles: int
    player_development_score: float
    earnings_minor: int
    legacy_boost_score: float
    dynasty_label: str


class HallOfFamePlayerView(CommonSchema):
    player_id: str
    global_player_id: str
    display_name: str
    club_id: str | None = None
    club_name: str | None = None
    inducted_at: datetime
    scarcity_tier: str
    legacy_boost_score: float
    immutable_record: bool = True


class CompetitionEntryResultView(CommonSchema):
    entry_id: str
    competition_id: str
    global_competition_id: str
    competition_name: str
    player_id: str
    global_player_id: str
    status: str
    title_awarded: bool
    performance_score: float
    dynasty: UserDynastyView
    evolution: RegenEvolutionView | None = None


class PlayerRentResultView(CommonSchema):
    rental_id: str
    competition_id: str
    global_competition_id: str
    competition_name: str
    player_id: str
    global_player_id: str
    rental_fee_minor: int
    status: str
    performance_score: float
    evolution: RegenEvolutionView | None = None


class NationalPoolPlayerView(CommonSchema):
    player_id: str
    global_player_id: str
    display_name: str
    country_code: str | None = None
    current_club_id: str | None = None
    current_competition_id: str | None = None
    is_regen: bool
    tradable: bool
    unique: bool
    hall_of_fame: bool
    gsi: int | None = None
    scarcity_tier: str | None = None


__all__ = [
    "ClubHistoryView",
    "CompetitionEnterRequest",
    "CompetitionEntryResultView",
    "CompetitionHistoryView",
    "CompetitionListItemView",
    "DynastyLeaderboardEntryView",
    "DynastyTitleView",
    "HallOfFamePlayerView",
    "NationalPoolPlayerView",
    "PlayerCareerArcView",
    "PlayerHistoryEntryView",
    "PlayerHistoryResponseView",
    "PlayerPerformanceTimelineEntryView",
    "PlayerRentRequest",
    "PlayerRentResultView",
    "RegenEvolutionView",
    "UserDynastyView",
]
