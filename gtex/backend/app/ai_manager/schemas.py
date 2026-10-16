from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from app.common.schemas.base import CommonSchema


class ManagerTacticalStyle(StrEnum):
    POSSESSION = "possession"
    DIRECT = "direct"
    COUNTER = "counter"
    BALANCED = "balanced"


class FinancialStrategy(StrEnum):
    SUSTAINABLE = "sustainable"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


class PlayerAvailability(StrEnum):
    AVAILABLE = "available"
    INJURED = "injured"
    SUSPENDED = "suspended"


class LineHeight(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class PressingIntensity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TempoSetting(StrEnum):
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"


class RewardDivision(StrEnum):
    D1 = "d1"
    D2 = "d2"
    D3 = "d3"
    OPEN = "open"


class PersonalityProfileInput(CommonSchema):
    aggression: float = Field(ge=0.0, le=1.0)
    risk: float = Field(ge=0.0, le=1.0)
    youth_bias: float = Field(ge=0.0, le=1.0)
    discipline: float = Field(ge=0.0, le=1.0)
    adaptability: float = Field(ge=0.0, le=1.0)


class AIManagerProfileInput(CommonSchema):
    club_id: str = Field(min_length=1)
    personality_profile: PersonalityProfileInput
    tactical_style: ManagerTacticalStyle
    financial_strategy: FinancialStrategy = FinancialStrategy.BALANCED
    risk_tolerance: float | None = Field(default=None, ge=0.0, le=1.0)


class AIManagerProfileView(CommonSchema):
    club_id: str
    personality_profile: PersonalityProfileInput
    tactical_style: ManagerTacticalStyle
    financial_strategy: FinancialStrategy
    risk_tolerance: float = Field(ge=0.0, le=1.0)


class ClubPlayerInput(CommonSchema):
    player_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=80)
    primary_position: str = Field(min_length=1, max_length=12)
    secondary_positions: list[str] = Field(default_factory=list)
    rating: int = Field(ge=1, le=100)
    potential: int = Field(ge=1, le=100)
    age: int = Field(ge=15, le=45)
    fatigue: float = Field(ge=0.0, le=1.0)
    stamina: float = Field(ge=0.0, le=1.0)
    form: float = Field(ge=0.0, le=1.0)
    injury_risk: float = Field(ge=0.0, le=1.0)
    availability: PlayerAvailability = PlayerAvailability.AVAILABLE
    wage_cost: int = Field(ge=0)
    transfer_value: int = Field(ge=0)
    morale: float = Field(default=0.5, ge=0.0, le=1.0)


class ClubFinanceContextInput(CommonSchema):
    revenue: int = Field(gt=0)
    wage_bill: int = Field(ge=0)
    transfer_budget: int = Field(ge=0)
    cash_balance: int
    scouting_budget: int = Field(default=0, ge=0)
    training_budget: int = Field(default=0, ge=0)


class OpponentContextInput(CommonSchema):
    club_name: str = Field(min_length=1, max_length=80)
    strength: int = Field(ge=1, le=100)
    tactical_style: ManagerTacticalStyle = ManagerTacticalStyle.BALANCED


class TransferTargetInput(CommonSchema):
    player_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=80)
    position: str = Field(min_length=1, max_length=12)
    skill: int = Field(ge=1, le=100)
    potential: int = Field(ge=1, le=100)
    fit_to_tactic: float = Field(ge=0.0, le=1.0)
    wage_cost: int = Field(ge=0)
    asking_price: int = Field(ge=0)
    age: int = Field(ge=15, le=45)
    is_free_agent: bool = False


class TransferMarketContextInput(CommonSchema):
    hours_since_last_transfer: float = Field(default=168.0, ge=0.0)
    targets: list[TransferTargetInput] = Field(default_factory=list)


class AutopilotRunRequest(CommonSchema):
    club_id: str = Field(min_length=1)
    user_last_active_hours: float = Field(ge=0.0)
    club_strength: int = Field(ge=1, le=100)
    opponent: OpponentContextInput
    squad: list[ClubPlayerInput] = Field(min_length=11, max_length=40)
    finance: ClubFinanceContextInput
    market: TransferMarketContextInput = Field(default_factory=TransferMarketContextInput)
    bench_size: int = Field(default=7, ge=3, le=12)
    manager_override: AIManagerProfileInput | None = None

    @model_validator(mode="after")
    def validate_manager_override(self) -> AutopilotRunRequest:
        if self.manager_override is not None and self.manager_override.club_id != self.club_id:
            raise ValueError("manager_override.club_id must match club_id")
        return self


class LiveMatchDecisionRequest(CommonSchema):
    club_id: str = Field(min_length=1)
    minute: int = Field(ge=0, le=130)
    score_for: int = Field(ge=0)
    score_against: int = Field(ge=0)
    xg_for: float = Field(default=0.0, ge=0.0)
    xg_against: float = Field(default=0.0, ge=0.0)
    possession_share: float = Field(default=0.5, ge=0.0, le=1.0)
    red_cards_for: int = Field(default=0, ge=0, le=4)
    red_cards_against: int = Field(default=0, ge=0, le=4)
    average_stamina: float = Field(ge=0.0, le=1.0)
    average_fatigue: float | None = Field(default=None, ge=0.0, le=1.0)
    opponent_switched_shape: bool = False
    substitutions_used: int = Field(default=0, ge=0, le=7)
    maximum_substitutions: int = Field(default=5, ge=1, le=7)
    manager_override: AIManagerProfileInput | None = None

    @model_validator(mode="after")
    def validate_manager_override(self) -> LiveMatchDecisionRequest:
        if self.manager_override is not None and self.manager_override.club_id != self.club_id:
            raise ValueError("manager_override.club_id must match club_id")
        if self.substitutions_used > self.maximum_substitutions:
            raise ValueError("substitutions_used cannot exceed maximum_substitutions")
        return self


class RewardPreviewRequest(CommonSchema):
    base_reward: int = Field(gt=0)
    difficulty_multiplier: float = Field(default=1.0, ge=0.25, le=5.0)
    division: RewardDivision = RewardDivision.OPEN
    win_streak: int = Field(default=0, ge=0, le=50)
    tournament_stage_weight: float = Field(default=0.0, ge=0.0, le=5.0)
    entry_fee_pool: int = Field(default=0, ge=0)
    entry_fee_multiplier: float = Field(default=1.0, ge=0.0, le=10.0)
    ai_active: bool = False
    premium_features_enabled: bool = False


class SelectedPlayerView(CommonSchema):
    player_id: str
    name: str
    slot: str
    rating: int
    age: int
    fatigue: float = Field(ge=0.0, le=1.0)
    form: float = Field(ge=0.0, le=1.0)
    selection_score: float
    natural_position: bool


class RoleAssignmentView(CommonSchema):
    slot: str
    player_id: str
    role: str


class SquadPlanView(CommonSchema):
    formation: str
    line_height: LineHeight
    pressing: PressingIntensity
    tempo: TempoSetting
    attack_bias: float = Field(ge=0.0, le=1.0)
    starting_eleven: list[SelectedPlayerView] = Field(min_length=11, max_length=11)
    bench: list[SelectedPlayerView] = Field(default_factory=list)
    role_assignments: list[RoleAssignmentView] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)


class TransferRecommendationView(CommonSchema):
    action: str
    player_name: str | None = None
    score: float | None = None
    rationale: str


class TrainingAssignmentView(CommonSchema):
    player_id: str
    player_name: str
    focus: str
    intensity: str
    rationale: str


class FinanceActionView(CommonSchema):
    action: str
    rationale: str


class AutopilotActivationView(CommonSchema):
    ai_active: bool
    mode: str
    inactivity_threshold_hours: float = Field(ge=0.0)
    reward_penalty_multiplier: float = Field(ge=0.0, le=1.0)
    applied_win_streak_bonus_cap: float = Field(ge=0.0, le=1.0)
    summary: str


class RewardPolicySummaryView(CommonSchema):
    ai_reward_multiplier: float = Field(ge=0.0, le=1.0)
    ai_win_streak_bonus_cap: float = Field(ge=0.0, le=1.0)
    premium_efficiency_tools: list[str]
    blocked_pay_to_win_paths: list[str]


class AutopilotRunResponse(CommonSchema):
    manager: AIManagerProfileView
    activation: AutopilotActivationView
    squad_plan: SquadPlanView
    transfer_actions: list[TransferRecommendationView]
    training_plan: list[TrainingAssignmentView]
    finance_actions: list[FinanceActionView]
    reward_policy: RewardPolicySummaryView
    decision_log: list[str]


class LiveDecisionResponse(CommonSchema):
    directive: str
    formation: str
    attack_bias: float = Field(ge=0.0, le=1.0)
    tempo: TempoSetting
    line_height: LineHeight
    pressing: PressingIntensity
    waste_time_behavior: bool
    trigger_substitution: bool
    substitution_reason: str | None = None
    rationale: list[str]


class RewardPreviewResponse(CommonSchema):
    base_reward: int
    final_reward: int
    division_multiplier: float
    raw_win_streak_bonus: float = Field(ge=0.0, le=5.0)
    applied_win_streak_bonus: float = Field(ge=0.0, le=5.0)
    reward_multiplier: float
    tournament_bonus: int
    prize_pool_reward: int
    ai_penalty_multiplier: float = Field(ge=0.0, le=1.0)
    premium_efficiency_tools: list[str]
    blocked_pay_to_win_paths: list[str]
    competitive_integrity_passed: bool
