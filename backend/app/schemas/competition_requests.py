from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import AliasChoices, Field, field_validator, model_validator

from app.common.enums.competition_format import CompetitionFormat
from app.common.enums.competition_visibility import CompetitionVisibility
from app.common.schemas.base import CommonSchema
from app.config.competition_constants import CUP_ALLOWED_PARTICIPANT_SIZES, USER_COMPETITION_MAX_PARTICIPANTS
from app.schemas.competition_lifecycle import CompetitionStructureRequest, CompetitionVisibilityRuleRequest

_ONE_HUNDRED = Decimal("1")
_PAYOUT_LABEL_TO_PLACE = {"first": 1, "second": 2, "third": 3}


class CompetitionHostType(StrEnum):
    GTEX_HOSTED = "gtex_hosted"
    USER_HOSTED = "user_hosted"


class PayoutRuleRequest(CommonSchema):
    place: int = Field(ge=1)
    percent: Decimal = Field(gt=0, le=_ONE_HUNDRED)


class CompetitionCreateRequest(CommonSchema):
    name: str = Field(min_length=3, max_length=120)
    format: CompetitionFormat
    visibility: CompetitionVisibility = CompetitionVisibility.PUBLIC
    type: str | None = Field(default=None, max_length=48)
    host_type: CompetitionHostType | None = Field(
        default=None,
        validation_alias=AliasChoices("host_type", "hostType"),
    )
    entry_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    buy_in_amount: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("buy_in_amount", "buyInAmount"),
    )
    currency: str = Field(default="credit", min_length=1, max_length=12)
    competition_mode: str | None = Field(
        default=None,
        max_length=32,
        validation_alias=AliasChoices("competition_mode", "competitionMode"),
    )
    is_ranked: bool = Field(default=True, validation_alias=AliasChoices("is_ranked", "isRanked", "ranked"))
    registration_deadline: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("registration_deadline", "registrationDeadline"),
    )
    prize_mode: str | None = Field(
        default=None, max_length=32, validation_alias=AliasChoices("prize_mode", "prizeMode")
    )
    payout_mode: str | None = Field(
        default=None, max_length=32, validation_alias=AliasChoices("payout_mode", "payoutMode")
    )
    host_funded_prize_total: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("host_funded_prize_total", "hostFundedPrizeTotal"),
    )
    fixed_prizes: dict[str, Decimal] | None = Field(
        default=None,
        validation_alias=AliasChoices("fixed_prizes", "fixedPrizes"),
    )
    capacity: int = Field(default=20, ge=2, le=USER_COMPETITION_MAX_PARTICIPANTS)
    max_players: int | None = Field(
        default=None,
        ge=2,
        le=USER_COMPETITION_MAX_PARTICIPANTS,
        validation_alias=AliasChoices("max_players", "maxPlayers"),
    )
    creator_id: str | None = Field(default=None, min_length=1, max_length=36)
    creator_name: str | None = Field(default=None, min_length=1, max_length=120)
    competition_type: str | None = Field(default=None, max_length=32)
    source_type: str | None = Field(default=None, max_length=48)
    source_id: str | None = Field(default=None, max_length=36)
    payout_structure: tuple[PayoutRuleRequest, ...] | None = None
    prize_distribution: dict[str, Decimal] | None = Field(
        default=None,
        validation_alias=AliasChoices("prize_distribution", "prizeDistribution"),
    )
    platform_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    host_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    rules: str | None = Field(default=None, max_length=280)
    rules_summary: str | None = Field(default=None, max_length=280)
    special_rules: str | None = Field(
        default=None,
        max_length=500,
        validation_alias=AliasChoices("special_rules", "specialRules"),
    )
    beginner_friendly: bool | None = None
    min_club_ranking: int | None = Field(
        default=None, ge=0, validation_alias=AliasChoices("min_club_ranking", "minClubRanking")
    )
    max_club_ranking: int | None = Field(
        default=None, ge=0, validation_alias=AliasChoices("max_club_ranking", "maxClubRanking")
    )
    division: str | None = Field(default=None, max_length=64)
    region: str | None = Field(default=None, max_length=64)
    country_code: str | None = Field(
        default=None, max_length=8, validation_alias=AliasChoices("country_code", "countryCode")
    )
    featured: bool = False
    manual_approval_required: bool = Field(
        default=False,
        validation_alias=AliasChoices("manual_approval_required", "manualApprovalRequired"),
    )
    online_now: bool = Field(default=False, validation_alias=AliasChoices("online_now", "onlineNow"))
    scheduled_start_at: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("scheduled_start_at", "startDateTime", "start_date_time"),
    )
    passcode: str | None = Field(default=None, min_length=3, max_length=64)
    seed_method: str | None = Field(default=None, max_length=24)
    structure: CompetitionStructureRequest | None = None
    visibility_rules: tuple[CompetitionVisibilityRuleRequest, ...] | None = None
    created_at: datetime | None = None

    @field_validator("host_type", mode="before")
    @classmethod
    def normalize_host_type(cls, value: object) -> object:
        if value is None or isinstance(value, CompetitionHostType):
            return value
        normalized = str(value).strip().lower()
        if normalized in {"gtex", "gtex_hosted", "gtex-hosted", "official", "platform"}:
            return CompetitionHostType.GTEX_HOSTED
        if normalized in {"user", "user_hosted", "user-hosted", "creator", "creator_hosted"}:
            return CompetitionHostType.USER_HOSTED
        return value

    @model_validator(mode="after")
    def validate_competition(self) -> "CompetitionCreateRequest":
        if self.type and self.source_type is None:
            self.source_type = self.type
        if self.host_type is None and self.source_type is not None:
            self.host_type = _host_type_from_source(self.source_type)
        if self.host_type is not None:
            self.source_type = self.host_type.value
            if self.type is None:
                self.type = self.host_type.value
        if self.buy_in_amount is not None:
            self.entry_fee = self.buy_in_amount
        if self.max_players is not None:
            self.capacity = self.max_players
        if self.prize_distribution and not self.payout_structure:
            self.payout_structure = _payout_rules_from_distribution(self.prize_distribution)
        if self.rules and self.rules_summary is None:
            self.rules_summary = self.rules
        if self.special_rules and self.rules_summary is None:
            self.rules_summary = self.special_rules[:280]
        _validate_fee_shares(
            platform_fee_pct=self.platform_fee_pct,
            host_fee_pct=self.host_fee_pct,
            payout_structure=self.payout_structure,
        )
        _validate_format_capacity(self.format, self.capacity)
        return self


class CompetitionUpdateRequest(CommonSchema):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    visibility: CompetitionVisibility | None = None
    entry_fee: Decimal | None = Field(default=None, ge=0)
    is_ranked: bool | None = Field(default=None, validation_alias=AliasChoices("is_ranked", "isRanked", "ranked"))
    registration_deadline: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("registration_deadline", "registrationDeadline"),
    )
    competition_mode: str | None = Field(
        default=None, max_length=32, validation_alias=AliasChoices("competition_mode", "competitionMode")
    )
    prize_mode: str | None = Field(
        default=None, max_length=32, validation_alias=AliasChoices("prize_mode", "prizeMode")
    )
    payout_mode: str | None = Field(
        default=None, max_length=32, validation_alias=AliasChoices("payout_mode", "payoutMode")
    )
    host_funded_prize_total: Decimal | None = Field(
        default=None,
        ge=0,
        validation_alias=AliasChoices("host_funded_prize_total", "hostFundedPrizeTotal"),
    )
    fixed_prizes: dict[str, Decimal] | None = Field(
        default=None,
        validation_alias=AliasChoices("fixed_prizes", "fixedPrizes"),
    )
    capacity: int | None = Field(default=None, ge=2, le=USER_COMPETITION_MAX_PARTICIPANTS)
    payout_structure: tuple[PayoutRuleRequest, ...] | None = None
    platform_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    host_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    rules_summary: str | None = Field(default=None, max_length=280)
    beginner_friendly: bool | None = None
    scheduled_start_at: datetime | None = None
    competition_type: str | None = Field(default=None, max_length=32)
    seed_method: str | None = Field(default=None, max_length=24)
    structure: CompetitionStructureRequest | None = None
    visibility_rules: tuple[CompetitionVisibilityRuleRequest, ...] | None = None

    @model_validator(mode="after")
    def validate_competition(self) -> "CompetitionUpdateRequest":
        _validate_fee_shares(
            platform_fee_pct=self.platform_fee_pct,
            host_fee_pct=self.host_fee_pct,
            payout_structure=self.payout_structure,
        )
        return self


class CompetitionPublishRequest(CommonSchema):
    open_for_join: bool = True


class CompetitionJoinRequest(CommonSchema):
    user_id: str | None = Field(default=None, min_length=1, max_length=36)
    user_name: str | None = Field(default=None, min_length=1, max_length=120)
    club_id: str | None = Field(
        default=None, min_length=1, max_length=36, validation_alias=AliasChoices("club_id", "clubId")
    )
    club_name: str | None = Field(default=None, min_length=2, max_length=120)
    invite_code: str | None = Field(default=None, min_length=4, max_length=32)
    passcode: str | None = Field(default=None, min_length=3, max_length=64)


class CompetitionJoinActionRequest(CompetitionJoinRequest):
    competition_id: str = Field(min_length=1, max_length=36)


class CompetitionLeaveRequest(CommonSchema):
    user_id: str = Field(min_length=1, max_length=36)


class RandomCompetitionRequest(CommonSchema):
    mode: str = Field(default="one_v_one", max_length=32)
    club_id: str | None = Field(
        default=None, min_length=1, max_length=36, validation_alias=AliasChoices("club_id", "clubId")
    )
    confirm: bool = False


class CompetitionInviteCreateRequest(CommonSchema):
    issued_by: str = Field(min_length=1, max_length=36)
    max_uses: int = Field(default=1, ge=1, le=100)
    expires_at: datetime | None = None
    note: str | None = Field(default=None, max_length=140)


def validate_format_capacity_for_update(format_value: CompetitionFormat, capacity: int | None) -> None:
    if capacity is None:
        return
    _validate_format_capacity(format_value, capacity)


def _validate_fee_shares(
    *,
    platform_fee_pct: Decimal | None,
    host_fee_pct: Decimal | None,
    payout_structure: tuple[PayoutRuleRequest, ...] | None,
) -> None:
    if platform_fee_pct is not None and host_fee_pct is not None and (platform_fee_pct + host_fee_pct) > _ONE_HUNDRED:
        raise ValueError("Total fees cannot exceed 100% of entry fees.")
    if not payout_structure:
        return
    places = [rule.place for rule in payout_structure]
    if len(places) != len(set(places)):
        raise ValueError("Payout places must be unique.")
    if places != sorted(places):
        raise ValueError("Payout places must be in ascending order.")
    total = sum(rule.percent for rule in payout_structure)
    if total != _ONE_HUNDRED:
        raise ValueError("Payout percentages must total 100% of the prize pool.")
    for rule in payout_structure:
        scaled = (rule.percent * Decimal("100")).normalize()
        if scaled != scaled.to_integral_value():
            raise ValueError("Payout percentages must use whole percentage points.")


def _host_type_from_source(value: str) -> CompetitionHostType | None:
    normalized = value.strip().lower()
    if normalized in {"gtex", "platform", "gtex_platform", "gtex_competition", "gtex_hosted"}:
        return CompetitionHostType.GTEX_HOSTED
    if normalized in {"user", "user_hosted", "creator", "creator_hosted"}:
        return CompetitionHostType.USER_HOSTED
    return None


def _payout_rules_from_distribution(distribution: dict[str, Decimal]) -> tuple[PayoutRuleRequest, ...]:
    raw_rules: list[tuple[int, Decimal]] = []
    for key, value in distribution.items():
        normalized_key = str(key).strip().lower()
        place = _PAYOUT_LABEL_TO_PLACE.get(normalized_key)
        if place is None and normalized_key.isdigit():
            place = int(normalized_key)
        if place is None:
            continue
        raw_rules.append((place, Decimal(value)))
    if not raw_rules:
        raise ValueError("Prize distribution must include first, second, third, or numeric places.")
    total = sum(value for _, value in raw_rules)
    if total <= 0:
        raise ValueError("Prize distribution must allocate a positive share.")
    if total > _ONE_HUNDRED:
        raw_rules = [(place, value / Decimal("100")) for place, value in raw_rules]
    normalized_total = sum(value for _, value in raw_rules)
    if normalized_total != _ONE_HUNDRED:
        raw_rules = [(place, (value / normalized_total).quantize(Decimal("0.01"))) for place, value in raw_rules]
        correction = _ONE_HUNDRED - sum(value for _, value in raw_rules)
        if raw_rules:
            first_place, first_value = raw_rules[0]
            raw_rules[0] = (first_place, first_value + correction)
    return tuple(
        PayoutRuleRequest(place=place, percent=percent)
        for place, percent in sorted(raw_rules, key=lambda item: item[0])
    )


def _validate_format_capacity(format_value: CompetitionFormat, capacity: int) -> None:
    if format_value is CompetitionFormat.CUP and capacity not in CUP_ALLOWED_PARTICIPANT_SIZES:
        allowed = ", ".join(str(value) for value in CUP_ALLOWED_PARTICIPANT_SIZES)
        raise ValueError(f"Cup competitions must use one of the supported bracket sizes: {allowed}.")
