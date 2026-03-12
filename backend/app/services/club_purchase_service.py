from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.common.enums.club_identity_visibility import ClubIdentityVisibility
from backend.app.models.club_branding_asset import ClubBrandingAsset
from backend.app.models.club_cosmetic_purchase import ClubCosmeticPurchase
from backend.app.models.club_identity_theme import ClubIdentityTheme
from backend.app.models.club_profile import ClubProfile
from backend.app.schemas.club_branding_core import ClubCosmeticPurchaseCore
from backend.app.schemas.club_requests import CatalogPurchaseRequest
from backend.app.services.club_cosmetic_catalog_service import ClubCosmeticCatalogService


@dataclass(slots=True)
class ClubPurchaseService:
    session: Session

    def purchase_catalog_item(
        self,
        *,
        buyer_user_id: str,
        payload: CatalogPurchaseRequest,
    ) -> ClubCosmeticPurchase:
        club = self._require_owned_club(payload.club_id, buyer_user_id)
        item = ClubCosmeticCatalogService(self.session).get_item(payload.catalog_item_id)
        purchase = ClubCosmeticPurchase(
            purchase_ref=f"club-purchase-{uuid4().hex[:16]}",
            club_id=club.id,
            buyer_user_id=buyer_user_id,
            catalog_item_id=item.id,
            purchase_type=item.purchase_type,
            amount_minor=item.price_minor,
            currency_code=item.currency_code,
            status="completed",
            review_status="pending_review" if item.moderation_required else "clear",
            payment_reference=payload.payment_reference,
            metadata_json={
                **payload.metadata_json,
                "sku": item.sku,
                "service_fee_minor": item.service_fee_minor,
            },
        )
        self.session.add(purchase)
        if item.asset_type == "showcase_backdrop":
            self.session.add(
                ClubIdentityTheme(
                    club_id=club.id,
                    name=str(item.metadata_json.get("theme_name", item.name)),
                    backdrop_asset_ref=item.sku,
                    cabinet_theme_code=str(item.metadata_json.get("cabinet_theme_code", "")) or None,
                    frame_code=str(item.metadata_json.get("frame_code", "")) or None,
                    visibility=ClubIdentityVisibility.PUBLIC.value,
                    metadata_json={"catalog_item_id": item.id, "purchase_ref": purchase.purchase_ref},
                )
            )
        elif item.asset_type is not None:
            self.session.add(
                ClubBrandingAsset(
                    club_id=club.id,
                    asset_type=item.asset_type,
                    asset_name=item.name,
                    asset_ref=item.sku,
                    catalog_item_id=item.id,
                    moderation_status="approved",
                    metadata_json={"purchase_ref": purchase.purchase_ref},
                )
            )
        self.session.commit()
        self.session.refresh(purchase)
        return purchase

    def list_purchases(
        self,
        *,
        club_id: str,
        owner_user_id: str | None = None,
    ) -> list[ClubCosmeticPurchaseCore]:
        if owner_user_id is not None:
            self._require_owned_club(club_id, owner_user_id)
        elif self.session.get(ClubProfile, club_id) is None:
            raise LookupError(f"club {club_id} was not found")
        purchases = self.session.scalars(
            select(ClubCosmeticPurchase)
            .where(ClubCosmeticPurchase.club_id == club_id)
            .order_by(ClubCosmeticPurchase.created_at.desc())
        ).all()
        return [ClubCosmeticPurchaseCore.model_validate(item) for item in purchases]

    def _require_owned_club(self, club_id: str, owner_user_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        if club.owner_user_id != owner_user_id:
            raise PermissionError("club_owner_required")
        return club
