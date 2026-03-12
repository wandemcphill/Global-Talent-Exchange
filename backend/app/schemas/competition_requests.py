from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from backend.app.common.enums.competition_format import CompetitionFormat
from backend.app.common.enums.competition_visibility import CompetitionVisibility
from backend.app.common.schemas.base import CommonSchema
from backend.app.config.competition_constants import CUP_ALLOWED_PARTICIPANT_SIZES, USER_COMPETITION_MAX_PARTICIPANTS

_ONE_HUNDRED = Decimal("1")


class PayoutRuleRequest(CommonSchema):
    place: int = Field(ge=1)
    percent: Decimal = Field(gt=0, le=_ONE_HUNDRED)


class CompetitionCreateRequest(CommonSchema):
    name: str = Field(min_length=3, max_length=120)
    format: CompetitionFormat
    visibility: CompetitionVisibility = CompetitionVisibility.PUBLIC
    entry_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = Field(default="credit", min_length=1, max_length=12)
    capacity: int = Field(default=20, ge=2, le=USER_COMPETITION_MAX_PARTICIPANTS)
    creator_id: str = Field(min_length=1, max_length=36)
    creator_name: str | None = Field(default=None, min_length=1, max_length=120)
    payout_structure: tuple[PayoutRuleRequest, ...] | None = None
    platform_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    host_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    rules_summary: str | None = Field(default=None, max_length=280)
    beginner_friendly: bool | None = None
    created_at: datetime | None = None

    @model_validator(mode="after")
    def validate_competition(self) -> "CompetitionCreateRequest":
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
    capacity: int | None = Field(default=None, ge=2, le=USER_COMPETITION_MAX_PARTICIPANTS)
    payout_structure: tuple[PayoutRuleRequest, ...] | None = None
    platform_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    host_fee_pct: Decimal | None = Field(default=None, ge=0, le=_ONE_HUNDRED)
    rules_summary: str | None = Field(default=None, max_length=280)
    beginner_friendly: bool | None = None

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
    user_id: str = Field(min_length=1, max_length=36)
    user_name: str | None = Field(default=None, min_length=1, max_length=120)
    invite_code: str | None = Field(default=None, min_length=4, max_length=32)


class CompetitionLeaveRequest(CommonSchema):
    user_id: str = Field(min_length=1, max_length=36)


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


def _validate_format_capacity(format_value: CompetitionFormat, capacity: int) -> None:
    if format_value is CompetitionFormat.CUP and capacity not in CUP_ALLOWED_PARTICIPANT_SIZES:
        allowed = ", ".join(str(value) for value in CUP_ALLOWED_PARTICIPANT_SIZES)
        raise ValueError(f"Cup competitions must use one of the supported bracket sizes: {allowed}.")
