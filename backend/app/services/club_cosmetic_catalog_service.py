from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.common.enums.club_brand_asset_type import ClubBrandAssetType
from backend.app.common.enums.club_cosmetic_purchase_type import ClubCosmeticPurchaseType
from backend.app.models.club_cosmetic_catalog_item import ClubCosmeticCatalogItem
from backend.app.schemas.club_branding_core import ClubCosmeticCatalogItemCore

_DEFAULT_CATALOG_ITEMS: tuple[dict[str, object], ...] = (
    {
        "sku": "JERSEY-TEMPLATE-CLASSIC",
        "purchase_type": ClubCosmeticPurchaseType.JERSEY_TEMPLATE.value,
        "name": "Classic Jersey Template",
        "description": "A transparent purchase for a clean legacy-ready jersey base.",
        "price_minor": 1500,
        "currency_code": "USD",
        "service_fee_minor": 100,
        "moderation_required": False,
        "metadata_json": {"template_id": "classic"},
    },
    {
        "sku": "TRIM-PACK-GOLD",
        "purchase_type": ClubCosmeticPurchaseType.TRIM_PACK.value,
        "name": "Gold Trim Pack",
        "description": "Premium trim accents for home, away, and third kits.",
        "price_minor": 900,
        "currency_code": "USD",
        "service_fee_minor": 50,
        "moderation_required": False,
        "metadata_json": {"trim_pack": "gold"},
    },
    {
        "sku": "SHOWCASE-THEME-HERITAGE",
        "purchase_type": ClubCosmeticPurchaseType.SHOWCASE_THEME.value,
        "asset_type": ClubBrandAssetType.SHOWCASE_BACKDROP.value,
        "name": "Heritage Showcase Theme",
        "description": "A heritage backdrop for trophy cabinet and legacy storytelling.",
        "price_minor": 2200,
        "currency_code": "USD",
        "service_fee_minor": 150,
        "moderation_required": False,
        "metadata_json": {"theme_name": "Heritage Showcase"},
    },
    {
        "sku": "CABINET-THEME-MARBLE",
        "purchase_type": ClubCosmeticPurchaseType.CABINET_DISPLAY_THEME.value,
        "asset_type": ClubBrandAssetType.CABINET_THEME.value,
        "name": "Marble Cabinet Theme",
        "description": "A marble display theme for featured trophies.",
        "price_minor": 1800,
        "currency_code": "USD",
        "service_fee_minor": 120,
        "moderation_required": False,
        "metadata_json": {"cabinet_theme_code": "marble"},
    },
    {
        "sku": "BANNER-FRAME-PRESTIGE",
        "purchase_type": ClubCosmeticPurchaseType.BANNER_FRAME.value,
        "asset_type": ClubBrandAssetType.BANNER.value,
        "name": "Prestige Banner Frame",
        "description": "A premium frame for club banner presentation.",
        "price_minor": 800,
        "currency_code": "USD",
        "service_fee_minor": 40,
        "moderation_required": False,
        "metadata_json": {"frame_code": "prestige"},
    },
    {
        "sku": "DYNASTY-BADGE-EMBER",
        "purchase_type": ClubCosmeticPurchaseType.DYNASTY_BADGE.value,
        "asset_type": ClubBrandAssetType.DYNASTY_BADGE.value,
        "name": "Ember Dynasty Badge",
        "description": "A visible dynasty badge for club identity and showcase surfaces.",
        "price_minor": 1100,
        "currency_code": "USD",
        "service_fee_minor": 60,
        "moderation_required": False,
        "metadata_json": {"badge_theme": "ember"},
    },
)


@dataclass(slots=True)
class ClubCosmeticCatalogService:
    session: Session

    def seed_defaults(self) -> list[ClubCosmeticCatalogItem]:
        items = self.session.scalars(select(ClubCosmeticCatalogItem)).all()
        if items:
            return items
        created: list[ClubCosmeticCatalogItem] = []
        for definition in _DEFAULT_CATALOG_ITEMS:
            item = ClubCosmeticCatalogItem(**definition)
            self.session.add(item)
            created.append(item)
        self.session.commit()
        return created

    def list_items(self) -> list[ClubCosmeticCatalogItemCore]:
        if not self.session.scalars(select(ClubCosmeticCatalogItem.id)).first():
            self.seed_defaults()
        items = self.session.scalars(
            select(ClubCosmeticCatalogItem)
            .where(ClubCosmeticCatalogItem.is_active.is_(True))
            .order_by(ClubCosmeticCatalogItem.price_minor.asc(), ClubCosmeticCatalogItem.sku.asc())
        ).all()
        return [ClubCosmeticCatalogItemCore.model_validate(item) for item in items]

    def get_item(self, catalog_item_id: str) -> ClubCosmeticCatalogItem:
        if not self.session.scalars(select(ClubCosmeticCatalogItem.id)).first():
            self.seed_defaults()
        item = self.session.get(ClubCosmeticCatalogItem, catalog_item_id)
        if item is None or not item.is_active:
            raise LookupError(f"catalog item {catalog_item_id} was not found")
        return item
