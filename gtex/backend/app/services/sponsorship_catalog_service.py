from __future__ import annotations

from functools import lru_cache

from app.common.enums.sponsorship_asset_type import SponsorshipAssetType
from app.schemas.sponsorship_core import ClubSponsorshipPackageView


class SponsorshipCatalogService:
    def __init__(self) -> None:
        self._packages = tuple(
            ClubSponsorshipPackageView(
                id=f"pkg-{code}",
                code=code,
                name=name,
                asset_type=asset_type,
                base_amount_minor=amount_minor,
                currency="USD",
                default_duration_months=duration_months,
                payout_schedule=schedule,
                description=description,
            )
            for code, name, asset_type, amount_minor, duration_months, schedule, description in (
                (
                    "community-jersey-front",
                    "Community Jersey Front",
                    SponsorshipAssetType.JERSEY_FRONT,
                    420_000,
                    6,
                    "monthly",
                    "Transparent front-of-shirt sponsorship package for club identity surfaces.",
                ),
                (
                    "regional-sleeve-slot",
                    "Regional Sleeve Slot",
                    SponsorshipAssetType.SLEEVE_SLOT,
                    180_000,
                    6,
                    "monthly",
                    "Visible sleeve sponsorship slot for club operations and match presentation surfaces.",
                ),
                (
                    "club-banner-rotation",
                    "Club Banner Rotation",
                    SponsorshipAssetType.CLUB_BANNER,
                    120_000,
                    3,
                    "upfront",
                    "Static banner placement with transparent catalog pricing and contract duration.",
                ),
                (
                    "showcase-header",
                    "Showcase Header",
                    SponsorshipAssetType.PROFILE_HEADER,
                    95_000,
                    3,
                    "upfront",
                    "Profile header sponsor placement for club showcases and recruitment pages.",
                ),
                (
                    "youth-pathway-backdrop",
                    "Youth Pathway Backdrop",
                    SponsorshipAssetType.SHOWCASE_BACKDROP,
                    150_000,
                    6,
                    "quarterly",
                    "Backdrop placement supporting academy development and youth scouting presentation.",
                ),
            )
        )

    def list_packages(self) -> tuple[ClubSponsorshipPackageView, ...]:
        return tuple(package.model_copy(deep=True) for package in self._packages)

    def get_package(self, package_code: str) -> ClubSponsorshipPackageView | None:
        for package in self._packages:
            if package.code == package_code:
                return package.model_copy(deep=True)
        return None


@lru_cache
def get_sponsorship_catalog_service() -> SponsorshipCatalogService:
    return SponsorshipCatalogService()


__all__ = ["SponsorshipCatalogService", "get_sponsorship_catalog_service"]
