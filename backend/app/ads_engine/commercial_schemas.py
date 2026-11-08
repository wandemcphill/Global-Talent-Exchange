from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AdvertiserAccountType = Literal["business", "agency", "music"]
WorkspaceMemberRole = Literal["owner", "admin", "campaign_manager", "billing", "analyst"]
MediaAssetKind = Literal["logo", "brand_image", "brand_video", "music_audio", "music_artwork"]
CommercialDivision = Literal["brand", "music"]
PaymentProviderName = Literal["paystack", "korapay"]

BRAND_PLACEMENT_KEYS: tuple[str, ...] = (
    "public_homepage",
    "login_page",
    "registration_page",
    "gtex_application",
    "sponsored_cards",
    "match_sponsor_id",
    "live_match_panel",
    "halftime_sponsorship",
    "stadium_perimeter",
)

MUSIC_PLACEMENT_KEYS: tuple[str, ...] = (
    "music_rotation",
    "music_track",
    "music_artist",
    "music_playlist",
)

ALL_PLACEMENT_KEYS: tuple[str, ...] = (
    *BRAND_PLACEMENT_KEYS,
    *MUSIC_PLACEMENT_KEYS,
    "homepage_rail",
    "homepage_hero",
    "partner_showcase",
    "auth_canvas",
)

ALLOWED_MUSIC_DURATIONS: tuple[int, ...] = (7, 21, 30, 42)


def format_ngn_from_minor(amount_minor_ngn: int | None) -> str | None:
    if amount_minor_ngn is None:
        return None
    naira = amount_minor_ngn / 100.0
    return f"₦{naira:,.2f}"


class AdvertiserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_type: AdvertiserAccountType = "business"
    company_name: str = Field(min_length=2, max_length=180)
    contact_name: str | None = Field(default=None, max_length=160)
    email: str = Field(min_length=5, max_length=320)
    phone_number: str = Field(min_length=6, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    website_url: str | None = Field(default=None, max_length=2048)
    stage_name: str | None = Field(default=None, max_length=160)
    label_name: str | None = Field(default=None, max_length=160)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        candidate = value.strip().lower()
        if "@" not in candidate or "." not in candidate.split("@", 1)[-1]:
            raise ValueError("A valid email address is required.")
        return candidate

    @field_validator("company_name", "phone_number")
    @classmethod
    def strip_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be blank.")
        return cleaned


class AdvertiserLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AdvertiserWorkspaceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    account_type: str
    company_name: str
    contact_name: str | None = None
    contact_email: str
    contact_phone: str
    website_url: str | None = None
    logo_asset_id: str | None = None
    logo_url: str | None = None
    stage_name: str | None = None
    label_name: str | None = None
    status: str
    verified_at: datetime | None = None
    suspended_reason: str | None = None
    default_currency: str = "NGN"
    created_at: datetime
    updated_at: datetime


class AdvertiserAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    session_id: str
    token_type: str = "bearer"
    expires_in: int
    refresh_expires_in: int
    landing_route: str = "/advertiser/dashboard"
    user: dict[str, Any]
    workspace: AdvertiserWorkspaceView


class AdvertiserWorkspaceUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str | None = Field(default=None, min_length=2, max_length=180)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, min_length=5, max_length=320)
    contact_phone: str | None = Field(default=None, min_length=6, max_length=64)
    website_url: str | None = Field(default=None, max_length=2048)
    logo_asset_id: str | None = Field(default=None, max_length=36)
    stage_name: str | None = Field(default=None, max_length=160)
    label_name: str | None = Field(default=None, max_length=160)


class AdvertiserMemberInviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=5, max_length=320)
    role: WorkspaceMemberRole = "campaign_manager"
    permissions: list[str] = Field(default_factory=list)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class AdvertiserMemberView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    user_id: str | None = None
    invited_email: str
    role: str
    status: str
    permissions_json: list[str] = Field(default_factory=list)
    created_at: datetime


class AdvertiserClientBrandCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand_name: str = Field(min_length=2, max_length=180)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, max_length=320)
    contact_phone: str | None = Field(default=None, max_length=64)
    website_url: str | None = Field(default=None, max_length=2048)
    logo_asset_id: str | None = Field(default=None, max_length=36)
    industry: str | None = Field(default=None, max_length=120)


class AdvertiserClientBrandView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    brand_name: str
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    website_url: str | None = None
    logo_asset_id: str | None = None
    logo_url: str | None = None
    industry: str | None = None
    is_active: bool
    created_at: datetime


class AdvertiserMediaAssetView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str | None = None
    asset_kind: str
    original_filename: str
    sanitized_filename: str
    mime_type: str
    size_bytes: int
    sha256_hash: str
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    has_audio_track: bool = False
    is_silent_verified: bool = True
    validation_status: str = "valid"
    storage_provider: str | None = None
    storage_key: str | None = None
    access_classification: str = "public"
    delivery_url: str
    created_at: datetime


class AdPlacementSpecView(BaseModel):
    id: str
    placement_key: str
    name: str
    division: str
    category: str
    description: str
    supported_media_types: list[str]
    aspect_ratio: str
    recommended_width: int | None = None
    recommended_height: int | None = None
    max_file_size_bytes: int
    max_duration_seconds: int | None = None
    requires_silent_media: bool = True
    weekly_rate_minor_ngn: int | None = None
    weekly_rate_formatted_ngn: str | None = None
    pricing_configured: bool = False
    is_enabled: bool = True
    delivery_surface_ready: bool = True
    frequency_cap_per_session: int = 10
    rotation_interval_seconds: int = 30
    priority_weight: int = 100
    device_compatibility: list[str] = Field(default_factory=list)


class AdPlacementSpecAdminUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    weekly_rate_minor_ngn: int | None = Field(default=None, ge=0)
    is_enabled: bool | None = None
    delivery_surface_ready: bool | None = None
    frequency_cap_per_session: int | None = Field(default=None, ge=1, le=500)
    rotation_interval_seconds: int | None = Field(default=None, ge=5, le=3600)
    priority_weight: int | None = Field(default=None, ge=1, le=1000)


class AdPricingPackageView(BaseModel):
    id: str
    package_code: str
    name: str
    division: str
    description: str
    duration_days: int
    placement_keys: list[str]
    is_bundle: bool = False
    is_subscription: bool = False
    billing_interval_days: int | None = None
    price_minor_ngn: int | None = None
    price_formatted_ngn: str | None = None
    pricing_configured: bool = False
    currency: str = "NGN"
    discount_percent: int = 0
    is_active: bool = True
    sort_order: int = 100


class AdPricingPackageAdminUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    package_code: str = Field(min_length=2, max_length=64)
    name: str = Field(min_length=2, max_length=160)
    division: CommercialDivision = "brand"
    description: str = Field(default="", max_length=1000)
    duration_days: int = Field(ge=7, le=365)
    placement_keys: list[str] = Field(default_factory=list)
    is_bundle: bool = False
    is_subscription: bool = False
    billing_interval_days: int | None = Field(default=None, ge=7, le=365)
    price_minor_ngn: int | None = Field(default=None, ge=0)
    discount_percent: int = Field(default=0, ge=0, le=90)
    is_active: bool = True
    sort_order: int = 100


class BrandCampaignWizardCreateRequest(BaseModel):
    """4-Step Brand Campaign Wizard payload. Start/end dates are never accepted from advertiser input."""

    model_config = ConfigDict(extra="forbid")

    # Step 1: Business details
    company_name: str = Field(min_length=2, max_length=160)
    contact_email: str = Field(min_length=5, max_length=320)
    contact_phone: str = Field(min_length=6, max_length=64)
    contact_name: str | None = Field(default=None, max_length=160)
    website_url: str | None = Field(default=None, max_length=2048)
    logo_asset_id: str | None = Field(default=None, max_length=36)
    client_brand_id: str | None = Field(default=None, max_length=36)

    # Step 2: Advertising placements (1 or multiple from central registry)
    placements: list[str] = Field(min_length=1, max_length=9)

    # Step 3: Creative upload
    creative_asset_id: str = Field(min_length=1, max_length=36)
    headline: str = Field(min_length=2, max_length=180)
    description: str = Field(default="", max_length=360)

    # Step 4: Campaign duration & NGN pricing
    duration_days: int = Field(default=7, ge=7, le=365)
    package_code: str | None = Field(default=None, max_length=64)
    is_subscription: bool = False
    submit_immediately: bool = True

    @field_validator("duration_days")
    @classmethod
    def enforce_minimum_brand_duration(cls, value: int) -> int:
        if value < 7:
            raise ValueError("The minimum brand advertising campaign duration is 7 days.")
        return value


class MusicPromotionWizardCreateRequest(BaseModel):
    """Dedicated Musician Audio Promotion workflow payload."""

    model_config = ConfigDict(extra="forbid")

    # Step 1: Upload music & optional cover art
    audio_asset_id: str = Field(min_length=1, max_length=36)
    track_title: str | None = Field(default=None, max_length=180)
    artist_name: str | None = Field(default=None, max_length=160)
    stage_name: str | None = Field(default=None, max_length=160)
    label_name: str | None = Field(default=None, max_length=160)
    genre: str | None = Field(default=None, max_length=80)
    artwork_asset_id: str | None = Field(default=None, max_length=36)
    external_profile_url: str | None = Field(default=None, max_length=2048)

    # Step 2: Select package (7, 21, 30, 42 days or monthly subscription)
    duration_days: int = Field(default=7)
    package_code: str | None = Field(default=None, max_length=64)
    is_subscription: bool = False

    # Step 3: Rights & Explicit declaration
    explicit_content: bool = False
    rights_declaration_accepted: bool = Field(...)
    rights_holder: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_music_package_and_rights(self) -> "MusicPromotionWizardCreateRequest":
        if not self.rights_declaration_accepted:
            raise ValueError(
                "You must confirm that you own or control the rights to promote and stream this track on GTEX."
            )
        if not self.is_subscription and self.duration_days not in ALLOWED_MUSIC_DURATIONS:
            raise ValueError("Music promotion duration must be 7, 21, 30, or 42 days (or a 30-day subscription).")
        return self


class CommercialPriceCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    division: CommercialDivision = "brand"
    placements: list[str] = Field(default_factory=list)
    duration_days: int = Field(default=7, ge=7, le=365)
    package_code: str | None = None
    is_subscription: bool = False


class CommercialPriceCalculationResponse(BaseModel):
    division: str
    placements: list[str]
    duration_days: int
    package_code: str | None = None
    is_subscription: bool = False
    currency: str = "NGN"
    pricing_configured: bool
    pricing_status: Literal["configured", "unconfigured"]
    subtotal_minor_ngn: int | None = None
    discount_minor_ngn: int = 0
    total_minor_ngn: int | None = None
    formatted_total_ngn: str | None = None
    breakdown: list[dict[str, Any]] = Field(default_factory=list)
    unconfigured_items: list[str] = Field(default_factory=list)


class CommercialCampaignView(BaseModel):
    id: str
    workspace_id: str | None = None
    advertiser_id: str | None = None
    client_brand_id: str | None = None
    campaign_type: str
    brand_name: str
    contact_email: str | None = None
    contact_phone: str | None = None
    contact_name: str | None = None
    website_url: str | None = None
    headline: str
    description: str
    placement: str
    placements: list[str]
    destination_url: str
    logo_asset_id: str | None = None
    logo_url: str | None = None
    creative_asset_id: str | None = None
    creative_url: str | None = None
    creative_media_type: str | None = None
    is_silent_creative: bool = True
    duration_days: int
    start_at: datetime | None = None
    end_at: datetime | None = None
    status: str
    payment_status: str
    payment_reference: str | None = None
    price_minor_ngn: int
    price_formatted_ngn: str
    currency: str
    pricing_model: str
    is_subscription: bool = False
    is_approved: bool
    is_active: bool
    review_note: str | None = None
    music_title: str | None = None
    music_artist_name: str | None = None
    music_genre: str | None = None
    music_audio_asset_id: str | None = None
    music_artwork_asset_id: str | None = None
    music_audio_url: str | None = None
    music_artwork_url: str | None = None
    music_explicit_content: bool = False
    music_rights_declaration_accepted: bool = False
    music_rights_verified: bool = False
    music_rights_holder: str | None = None
    created_at: datetime
    updated_at: datetime


class PaymentInitiateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    campaign_id: str = Field(min_length=1, max_length=36)
    provider: PaymentProviderName = "paystack"
    callback_url: str | None = Field(default=None, max_length=2048)
    idempotency_key: str | None = Field(default=None, max_length=120)
    subscription_consent_accepted: bool = False


class PaymentRecordView(BaseModel):
    id: str
    reference: str
    idempotency_key: str
    workspace_id: str
    campaign_id: str | None = None
    subscription_id: str | None = None
    provider: str
    provider_reference: str | None = None
    amount_minor_ngn: int
    amount_formatted_ngn: str
    currency: str = "NGN"
    status: str
    checkout_url: str | None = None
    verified_at: datetime | None = None
    verification_source: str | None = None
    failure_reason: str | None = None
    invoice_number: str | None = None
    created_at: datetime


class InvoiceView(BaseModel):
    id: str
    invoice_number: str
    workspace_id: str
    campaign_id: str | None = None
    payment_record_id: str | None = None
    subtotal_minor_ngn: int
    tax_minor_ngn: int
    discount_minor_ngn: int
    total_minor_ngn: int
    total_formatted_ngn: str
    currency: str = "NGN"
    status: str
    issued_at: datetime
    paid_at: datetime | None = None
    line_items: list[dict[str, Any]] = Field(default_factory=list)
    billing_details: dict[str, Any] = Field(default_factory=dict)


class SubscriptionView(BaseModel):
    id: str
    workspace_id: str
    campaign_id: str
    provider: str
    amount_minor_ngn: int
    amount_formatted_ngn: str
    currency: str = "NGN"
    billing_interval_days: int
    status: str
    consent_accepted: bool
    consent_accepted_at: datetime | None = None
    consent_terms_text: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    next_billing_at: datetime | None = None
    grace_period_ends_at: datetime | None = None
    retry_count: int = 0
    cancelled_at: datetime | None = None
    cancellation_reason: str | None = None
    created_at: datetime


class SubscriptionActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["cancel", "pause", "resume", "renew"]
    reason: str | None = Field(default=None, max_length=500)


class RefundCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_record_id: str = Field(min_length=1, max_length=36)
    amount_minor_ngn: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=4, max_length=1000)


class RefundRecordView(BaseModel):
    id: str
    payment_record_id: str
    workspace_id: str
    campaign_id: str | None = None
    amount_minor_ngn: int
    amount_formatted_ngn: str
    currency: str = "NGN"
    reason: str
    status: str
    approved_by_user_id: str
    created_at: datetime


class AdminWorkspaceActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["verify", "suspend", "reactivate"]
    note: str | None = Field(default=None, max_length=1000)


class AdminCampaignModerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "reject", "request_changes", "pause", "resume", "suspend", "takedown", "archive"]
    note: str | None = Field(default=None, max_length=1000)


class MusicRotationTrackView(BaseModel):
    campaign_id: str
    track_id: str
    title: str
    artist: str
    genre: str | None = None
    audio_url: str
    artwork_url: str | None = None
    explicit_content: bool = False
    sponsored_disclosure: str = "Promoted on GTEX Music Network"
    rights_holder: str | None = None
    priority: int = 100
    duration_days: int = 7
    start_at: datetime
    end_at: datetime


class MusicRotationFeedResponse(BaseModel):
    generated_at: datetime
    rotation_policy: dict[str, Any]
    tracks: list[MusicRotationTrackView]
