from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from app.common.schemas.base import CommonSchema
from app.match_engine.schemas import MatchSimulationRequest


class TacticalStyleProfile(StrEnum):
    POSSESSION = "possession"
    COUNTER = "counter"
    LONG_BALL = "long_ball"
    BALANCED = "balanced"
    DIRECT = "direct"


class PressingProfile(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TempoProfile(StrEnum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class ConnectionQuality(StrEnum):
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    EXCELLENT = "excellent"


class AvailabilityStatus(StrEnum):
    ONLINE = "online"
    AWAY = "away"
    OFFLINE = "offline"


class SimulationMatchType(StrEnum):
    QUICK = "quick"
    TOURNAMENT = "tournament"
    HOSTED = "hosted"


class QuickGameStyle(StrEnum):
    BALANCED = "balanced"
    TACTICAL_CLASH = "tactical_clash"


class SimulationExecutionMode(StrEnum):
    LIVE = "live"
    ASYNC = "async"
    HYBRID = "hybrid"


class BotClubProfile(StrEnum):
    BEGINNER = "beginner"
    BALANCED = "balanced"
    ELITE_TACTICAL = "elite_tactical"


class HostedCompetitionType(StrEnum):
    LEAGUE_MODE = "league_mode"
    TACTICAL_CUP = "tactical_cup"
    TRANSFER_SHOWCASE_CUP = "transfer_showcase_cup"


class TacticalProfileInput(CommonSchema):
    style: TacticalStyleProfile
    pressing: PressingProfile
    tempo: TempoProfile


class SimulationGameProfileInput(CommonSchema):
    user_id: str = Field(min_length=1)
    club_id: str = Field(min_length=1)
    club_name: str | None = Field(default=None, min_length=1, max_length=80)
    manager_rating: int = Field(ge=0, le=4000)
    tactical_profile: TacticalProfileInput
    squad_strength: int = Field(ge=1, le=100)
    squad_depth: int = Field(ge=1, le=100)
    preferred_match_type: list[SimulationMatchType] = Field(default_factory=list, min_length=1)
    connection_quality: ConnectionQuality
    region: str = Field(min_length=2, max_length=32)
    availability: AvailabilityStatus


class SimulationGameProfileView(CommonSchema):
    user_id: str
    club_id: str
    club_name: str
    manager_rating: int
    tactical_profile: TacticalProfileInput
    squad_strength: int
    squad_depth: int
    preferred_match_type: list[SimulationMatchType]
    connection_quality: ConnectionQuality
    region: str
    availability: AvailabilityStatus
    is_bot: bool = False
    bot_profile: BotClubProfile | None = None


class QuickGamePreferences(CommonSchema):
    match_style: QuickGameStyle = QuickGameStyle.BALANCED
    allow_tactical_clash: bool = True
    max_rating_delta: int = Field(default=50, ge=10, le=300)
    max_squad_strength_delta: int = Field(default=5, ge=1, le=25)
    preferred_execution_mode: SimulationExecutionMode | None = None


class QuickGameRequest(CommonSchema):
    mode: Literal["quick_game"] = "quick_game"
    user_id: str = Field(min_length=1)
    include_bots: bool = True
    preferences: QuickGamePreferences = Field(default_factory=QuickGamePreferences)


class MatchContextView(CommonSchema):
    type: str
    expected_difficulty: str
    tactical_story: str
    tactical_compatibility_score: int = Field(ge=0, le=100)
    rating_delta: int
    squad_strength_delta: int
    latency_tier: str
    queue_source: str


class MatchSimulationBridgeView(CommonSchema):
    seed_hint: int
    recommended_mode: SimulationExecutionMode
    live_supported: bool = True
    async_supported: bool = True
    marketplace_feedback_enabled: bool = True
    match_engine_request: MatchSimulationRequest


class QuickGameResponse(CommonSchema):
    match_id: str
    live_match_key: str | None = None
    viewer_route: str | None = None
    opponent: SimulationGameProfileView
    match_context: MatchContextView
    simulation_bridge: MatchSimulationBridgeView
    free_matches_remaining: int = Field(default=10, ge=0, le=10)
    free_matches_used: int = Field(default=0, ge=0, le=10)
    charge_on_loss: bool = True
    charge_required_now: bool = False
    entry_currency: str = "credit"
    entry_currency_label: str = "Fan Coin"
    fan_coin_entry_fee: Decimal = Field(default=Decimal("0"), ge=0)
    entitlement_status: str = "free_run_active"
    settlement_status: str | None = None
    result: str | None = None
    rules_copy: str = "Play free until you lose or reach 10 matches."


class FastMatchEntitlementResponse(CommonSchema):
    free_match_limit: int = Field(default=10, ge=0)
    free_matches_used: int = Field(default=0, ge=0)
    free_matches_remaining: int = Field(default=10, ge=0)
    wins_count: int = Field(default=0, ge=0)
    losses_count: int = Field(default=0, ge=0)
    draws_count: int = Field(default=0, ge=0)
    current_streak: int = Field(default=0, ge=0)
    has_lost_free_run: bool = False
    free_eligibility_exhausted: bool = False
    charge_required_now: bool = False
    entry_currency: str = "credit"
    entry_currency_label: str = "Fan Coin"
    fan_coin_entry_fee: Decimal = Field(default=Decimal("0"), ge=0)
    entitlement_status: str = "free_run_active"


class QuickTournamentPreferences(CommonSchema):
    avoid_same_style_early: bool = True
    spread_strong_squads: bool = True
    allow_bots: bool = True
    preferred_execution_mode: SimulationExecutionMode = SimulationExecutionMode.HYBRID


class QuickTournamentRequest(CommonSchema):
    mode: Literal["quick_tournament"] = "quick_tournament"
    user_id: str = Field(min_length=1)
    size: int = Field(default=8, ge=4, le=16)
    entrant_user_ids: list[str] = Field(default_factory=list)
    preferences: QuickTournamentPreferences = Field(default_factory=QuickTournamentPreferences)

    @model_validator(mode="after")
    def validate_size(self) -> QuickTournamentRequest:
        if self.size not in {4, 8, 16}:
            raise ValueError("Quick tournaments currently support 4, 8, or 16 entrants.")
        return self


class TournamentMatchView(CommonSchema):
    match_id: str
    home: SimulationGameProfileView | None = None
    away: SimulationGameProfileView | None = None
    context: str
    storybeat: str
    simulation_mode: SimulationExecutionMode
    match_engine_request: MatchSimulationRequest | None = None


class TournamentRoundView(CommonSchema):
    round: int = Field(ge=1)
    label: str
    matches: list[TournamentMatchView]


class QuickTournamentResponse(CommonSchema):
    tournament_id: str
    bracket: list[TournamentRoundView]
    narrative: str
    entrants: list[SimulationGameProfileView]
    marketplace_feedback_enabled: bool = True


class HostedCompetitionEligibilityInput(CommonSchema):
    tactical_styles: list[TacticalStyleProfile] = Field(default_factory=list)
    min_squad_strength: int | None = Field(default=None, ge=1, le=100)
    max_squad_strength: int | None = Field(default=None, ge=1, le=100)
    regions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_strength_window(self) -> HostedCompetitionEligibilityInput:
        if (
            self.min_squad_strength is not None
            and self.max_squad_strength is not None
            and self.min_squad_strength > self.max_squad_strength
        ):
            raise ValueError("min_squad_strength cannot be greater than max_squad_strength")
        return self


class HostedCompetitionPreviewRequest(CommonSchema):
    host_user_id: str = Field(min_length=1)
    competition_type: HostedCompetitionType
    title: str | None = Field(default=None, min_length=2, max_length=120)
    target_club_count: int | None = Field(default=None, ge=4, le=20)
    participant_user_ids: list[str] = Field(default_factory=list)
    allow_bots: bool = False
    simulation_mode: SimulationExecutionMode = SimulationExecutionMode.HYBRID
    eligibility: HostedCompetitionEligibilityInput = Field(default_factory=HostedCompetitionEligibilityInput)

    @model_validator(mode="after")
    def validate_human_only(self) -> "HostedCompetitionPreviewRequest":
        if self.allow_bots:
            raise ValueError("GTEX hosted competitions do not allow AI or bot participants.")
        return self


class MarketplaceFeedbackHooksView(CommonSchema):
    player_form_updates: bool = True
    scout_visibility_updates: bool = True
    transfer_demand_updates: bool = True
    in_form_badges: bool = True


class HostedCompetitionPreviewResponse(CommonSchema):
    competition_id: str
    competition_type: HostedCompetitionType
    title: str
    format: str
    simulation_mode: SimulationExecutionMode
    qualified_clubs: list[SimulationGameProfileView]
    narrative: str
    match_flow: list[str]
    marketplace_hooks: MarketplaceFeedbackHooksView
