from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PolicyDocumentVersionSummary(BaseModel):
    id: str
    version_label: str
    effective_at: datetime
    published_at: datetime
    changelog: str | None = None


class PolicyDocumentSummary(BaseModel):
    id: str
    document_key: str
    title: str
    is_mandatory: bool
    active: bool
    latest_version: PolicyDocumentVersionSummary | None = None


class PolicyDocumentDetail(PolicyDocumentSummary):
    body_markdown: str | None = None


class PolicyAcceptanceRequest(BaseModel):
    document_key: str = Field(min_length=2, max_length=64)
    version_label: str = Field(min_length=1, max_length=32)
    ip_address: str | None = Field(default=None, max_length=64)
    device_id: str | None = Field(default=None, max_length=128)


class PolicyAcceptanceResponse(BaseModel):
    acceptance_id: str
    document_key: str
    version_label: str
    accepted_at: datetime


class PolicyAcceptanceSummary(BaseModel):
    document_key: str
    title: str
    version_label: str
    accepted_at: datetime


class UserRegionUpdateRequest(BaseModel):
    region_code: str = Field(min_length=2, max_length=8)


class UserRegionProfileView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    region_code: str
    current_region: str
    selected_at: datetime
    last_changed_at: datetime
    locked_until: datetime | None
    change_count: int
    permanent_locked: bool
    next_change_eligible_at: datetime | None = None
    permanent_change_used: bool = False
    locked: bool = False
    override_metadata: dict | None = None


class AdminRegionOverrideRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=36)
    region_code: str = Field(min_length=2, max_length=8)
    reason: str | None = Field(default=None, max_length=255)


class PolicyDocumentVersionUpsertRequest(BaseModel):
    document_key: str = Field(min_length=2, max_length=64)
    title: str = Field(min_length=3, max_length=160)
    version_label: str = Field(min_length=1, max_length=32)
    body_markdown: str = Field(min_length=20)
    changelog: str | None = None
    is_mandatory: bool = True
    active: bool = True
    is_published: bool = True
    effective_at: datetime | None = None
    published_at: datetime | None = None


class CountryFeaturePolicyResponse(BaseModel):
    country_code: str
    bucket_type: str
    deposits_enabled: bool
    market_trading_enabled: bool
    platform_reward_withdrawals_enabled: bool
    user_hosted_gift_withdrawals_enabled: bool
    gtex_competition_gift_withdrawals_enabled: bool
    national_reward_withdrawals_enabled: bool
    one_time_region_change_after_days: int
    active: bool


class PolicyRequirementSummary(BaseModel):
    document_key: str
    title: str
    version_label: str
    is_mandatory: bool
    effective_at: datetime
    reason: str = "latest_version_not_accepted"


class UserComplianceStatus(BaseModel):
    country_code: str
    country_policy_bucket: str
    deposits_enabled: bool
    market_trading_enabled: bool
    platform_reward_withdrawals_enabled: bool
    required_policy_acceptances_missing: int = 0
    missing_policy_acceptances: list[PolicyRequirementSummary] = []
    can_deposit: bool = True
    can_withdraw_platform_rewards: bool = True
    can_trade_market: bool = True


class CountryFeaturePolicyUpsertRequest(BaseModel):
    country_code: str = Field(min_length=2, max_length=8)
    bucket_type: str = Field(default="default", min_length=1, max_length=32)
    deposits_enabled: bool = True
    market_trading_enabled: bool = True
    platform_reward_withdrawals_enabled: bool = True
    user_hosted_gift_withdrawals_enabled: bool = False
    gtex_competition_gift_withdrawals_enabled: bool = False
    national_reward_withdrawals_enabled: bool = False
    one_time_region_change_after_days: int = Field(default=180, ge=0, le=3650)
    active: bool = True


class CountryFeaturePolicyAdminSummary(CountryFeaturePolicyResponse):
    id: str
    updated_at: datetime
