from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.common.enums.club_reputation_tier import ClubReputationTier
from backend.app.common.schemas.base import CommonSchema
from backend.app.schemas.club_branding_core import (
    ClubCosmeticCatalogItemCore,
    ClubCosmeticPurchaseCore,
    ClubJerseyDesignCore,
)
from backend.app.schemas.club_dynasty_core import ClubDynastyMilestoneCore, ClubDynastyProgressCore
from backend.app.schemas.club_identity_core import ClubBrandingAssetCore, ClubIdentityThemeCore, ClubProfileCore
from backend.app.schemas.club_reputation_core import ClubReputationCore
from backend.app.schemas.club_trophy_core import ClubTrophyCabinetCore, ClubTrophyCore


class ClubProfileView(CommonSchema):
    profile: ClubProfileCore


class ClubReputationView(CommonSchema):
    reputation: ClubReputationCore


class ClubShowcaseView(CommonSchema):
    club_id: str
    club_name: str
    slug: str
    reputation_score: int
    reputation_tier: ClubReputationTier
    dynasty_score: int
    dynasty_title: str
    featured_trophy: ClubTrophyCore | None = None
    active_theme: ClubIdentityThemeCore | None = None
    assets: list[ClubBrandingAssetCore] = Field(default_factory=list)
    recent_trophies: list[ClubTrophyCore] = Field(default_factory=list)
    generated_at: datetime


class ClubDynastyView(CommonSchema):
    progress: ClubDynastyProgressCore
    milestones: list[ClubDynastyMilestoneCore] = Field(default_factory=list)


class ClubTrophiesView(CommonSchema):
    cabinet: ClubTrophyCabinetCore
    trophies: list[ClubTrophyCore] = Field(default_factory=list)


class ClubBrandingView(CommonSchema):
    profile: ClubProfileCore
    theme: ClubIdentityThemeCore | None = None
    assets: list[ClubBrandingAssetCore] = Field(default_factory=list)


class ClubJerseysView(CommonSchema):
    jerseys: list[ClubJerseyDesignCore] = Field(default_factory=list)


class ClubCatalogView(CommonSchema):
    items: list[ClubCosmeticCatalogItemCore] = Field(default_factory=list)


class ClubPurchasesView(CommonSchema):
    purchases: list[ClubCosmeticPurchaseCore] = Field(default_factory=list)
