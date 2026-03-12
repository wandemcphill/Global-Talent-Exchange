from __future__ import annotations

from pydantic import Field

from backend.app.common.schemas.base import CommonSchema
from backend.app.schemas.club_branding_core import ClubCosmeticPurchaseCore, ClubJerseyDesignCore
from backend.app.schemas.club_dynasty_core import ClubDynastyProgressCore
from backend.app.schemas.club_identity_core import ClubBrandingAssetCore, ClubIdentityThemeCore, ClubProfileCore
from backend.app.schemas.club_reputation_core import ClubReputationCore
from backend.app.schemas.club_trophy_core import ClubTrophyCore


class ModerateBrandingRequest(CommonSchema):
    asset_ids: list[str] = Field(default_factory=list)
    jersey_ids: list[str] = Field(default_factory=list)
    moderation_status: str = Field(min_length=3, max_length=24)
    reason: str | None = Field(default=None, max_length=255)


class BrandingModerationResultView(CommonSchema):
    updated_assets: list[ClubBrandingAssetCore] = Field(default_factory=list)
    updated_jerseys: list[ClubJerseyDesignCore] = Field(default_factory=list)


class AdminClubDetailView(CommonSchema):
    profile: ClubProfileCore
    reputation: ClubReputationCore
    dynasty: ClubDynastyProgressCore
    trophies: list[ClubTrophyCore] = Field(default_factory=list)
    branding_assets: list[ClubBrandingAssetCore] = Field(default_factory=list)
    jerseys: list[ClubJerseyDesignCore] = Field(default_factory=list)
    theme: ClubIdentityThemeCore | None = None
    purchases: list[ClubCosmeticPurchaseCore] = Field(default_factory=list)
