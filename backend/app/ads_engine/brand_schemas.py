from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.common.schemas.base import CommonSchema


BrandPlacement = Literal["homepage_rail", "homepage_hero", "partner_showcase", "auth_canvas"]
MusicPlacement = Literal["music_track", "music_artist", "music_playlist"]


class BrandAdvertiserProfileUpsertRequest(CommonSchema):
    company_name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=160)
    website_url: str | None = Field(default=None, max_length=2048)
    billing_email: str = Field(min_length=5, max_length=320)

    @field_validator("billing_email")
    @classmethod
    def validate_billing_email(cls, value: str) -> str:
        value = value.strip()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("Enter a valid billing email address.")
        return value

    @field_validator("website_url")
    @classmethod
    def validate_website_url(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        from urllib.parse import urlsplit
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Website URL must be an HTTP(S) URL without embedded credentials.")
        return value.strip()


class BrandAdvertiserProfileView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    company_name: str
    contact_name: str
    website_url: str | None = None
    billing_email: str


class BrandCampaignUpsertRequest(CommonSchema):
    campaign_type: Literal["brand", "music"] = "brand"
    brand_name: str = Field(min_length=2, max_length=160)
    headline: str = Field(min_length=3, max_length=180)
    description: str = Field(default="", max_length=360)
    placement: Literal[
        "homepage_rail", "homepage_hero", "partner_showcase", "auth_canvas",
        "music_track", "music_artist", "music_playlist"
    ]
    destination_url: str = Field(min_length=8, max_length=2048)
    logo_url: str | None = Field(default=None, max_length=2048)
    creative_url: str | None = Field(default=None, max_length=2048)
    start_at: datetime
    end_at: datetime
    budget_amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    pricing_model: Literal["CPM", "CPC"] = "CPM"
    unit_price: Decimal = Field(gt=0, max_digits=18, decimal_places=4)
    music_target_type: Literal["track", "artist", "playlist"] | None = None
    music_target_id: str | None = Field(default=None, max_length=160)
    music_title: str | None = Field(default=None, max_length=180)
    music_artist_name: str | None = Field(default=None, max_length=160)
    music_playlist_name: str | None = Field(default=None, max_length=160)
    music_genre: str | None = Field(default=None, max_length=80)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        normalized = value.strip().upper()
        if len(normalized) != 3 or not normalized.isalpha():
            raise ValueError("Currency must be a three-letter ISO-style code.")
        return normalized

    @field_validator("destination_url", "logo_url", "creative_url")
    @classmethod
    def validate_http_urls(cls, value: str | None) -> str | None:
        if value is None:
            return None
        from urllib.parse import urlsplit
        parsed = urlsplit(value.strip())
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("Campaign URLs must use HTTP(S) and must not contain embedded credentials.")
        return value.strip()

    @model_validator(mode="after")
    def validate_campaign(self) -> "BrandCampaignUpsertRequest":
        if self.end_at <= self.start_at:
            raise ValueError("Campaign end_at must be after start_at.")
        if self.campaign_type == "brand":
            if self.placement not in {"homepage_rail", "homepage_hero", "partner_showcase", "auth_canvas"}:
                raise ValueError("Brand campaigns must use a public GTEX brand placement.")
            if self.music_target_type or self.music_target_id:
                raise ValueError("Music target fields are only valid for music campaigns.")
        else:
            expected = {
                "track": "music_track",
                "artist": "music_artist",
                "playlist": "music_playlist",
            }
            if not self.music_target_type or self.placement != expected.get(self.music_target_type):
                raise ValueError("Music campaign placement must match its target type.")
            if not self.music_target_id or not self.music_target_id.strip():
                raise ValueError("Music campaigns require a stable track, artist, or playlist identifier.")
            if self.music_target_type == "track" and not (self.music_title and self.music_artist_name):
                raise ValueError("Track promotions require both a track title and artist name.")
            if self.music_target_type == "artist" and not self.music_artist_name:
                raise ValueError("Artist promotions require an artist name.")
            if self.music_target_type == "playlist" and not self.music_playlist_name:
                raise ValueError("Playlist promotions require a playlist name.")
        return self


class BrandCampaignView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)

    id: str
    advertiser_id: str | None = None
    campaign_type: str
    brand_name: str
    headline: str
    description: str
    placement: str
    destination_url: str
    logo_url: str | None = None
    creative_url: str | None = None
    start_at: datetime
    end_at: datetime
    budget_amount: Decimal
    currency: str
    pricing_model: str
    unit_price: Decimal
    status: str
    is_approved: bool
    is_active: bool
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    music_target_type: str | None = None
    music_target_id: str | None = None
    music_title: str | None = None
    music_artist_name: str | None = None
    music_playlist_name: str | None = None
    music_genre: str | None = None


class BrandCampaignHistoryView(CommonSchema):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_user_id: str
    action: str
    note: str | None = None
    from_status: str
    to_status: str
    created_at: datetime


class CampaignReportView(CommonSchema):
    campaign_id: str
    campaign_name: str
    status: str
    currency: str
    budget_amount: Decimal
    pricing_model: str
    unit_price: Decimal
    impressions: int
    clicks: int
    conversions: int
    ctr_percent: float
    estimated_spend: Decimal
    estimated_budget_remaining: Decimal
    billing_state: Literal["reporting_only_no_payment_collected"] = "reporting_only_no_payment_collected"


class CampaignReportsResponse(CommonSchema):
    reports: list[CampaignReportView] = Field(default_factory=list)
    generated_at: datetime


class BrandCampaignReviewRequest(CommonSchema):
    action: Literal["approve", "reject", "pause", "archive"]
    note: str | None = Field(default=None, max_length=2000)


class BrandCampaignEventRequest(CommonSchema):
    campaign_id: str = Field(min_length=36, max_length=36)
    event_type: Literal["impression", "click"]
    idempotency_key: str = Field(min_length=8, max_length=96)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AdminConversionEventRequest(CommonSchema):
    idempotency_key: str = Field(min_length=8, max_length=96)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class PublicMusicPromotionView(CommonSchema):
    campaign_id: str
    brand_name: str
    headline: str
    description: str
    destination_url: str
    creative_url: str | None = None
    target_type: Literal["track", "artist", "playlist"]
    target_id: str
    track_title: str | None = None
    artist_name: str | None = None
    playlist_name: str | None = None
    genre: str | None = None


class PublicMusicPromotionsResponse(CommonSchema):
    promotions: list[PublicMusicPromotionView] = Field(default_factory=list)
    generated_at: datetime


class BrandAdEventResponse(CommonSchema):
    accepted: bool
    duplicate: bool = False
