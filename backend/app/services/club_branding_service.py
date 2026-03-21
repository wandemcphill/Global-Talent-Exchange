from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.enums.club_identity_visibility import ClubIdentityVisibility
from app.models.club_branding_asset import ClubBrandingAsset
from app.models.club_identity_theme import ClubIdentityTheme
from app.models.club_profile import ClubProfile
from app.schemas.club_identity_core import ClubBrandingAssetCore, ClubIdentityThemeCore, ClubProfileCore
from app.schemas.club_requests import BrandingUpsertRequest, ClubCreateRequest, ClubUpdateRequest
from app.services.club_dynasty_service import ClubDynastyService
from app.services.regen_bootstrap_service import RegenBootstrapService
from app.services.club_reputation_service import ClubReputationService
from app.services.club_trophy_service import ClubTrophyService


@dataclass(slots=True)
class ClubBrandingService:
    session: Session

    def create_club_profile(self, *, owner_user_id: str, payload: ClubCreateRequest) -> ClubProfile:
        existing = self.session.scalar(select(ClubProfile).where(ClubProfile.slug == payload.slug))
        if existing is not None:
            raise ValueError("club_slug_taken")
        club = ClubProfile(
            owner_user_id=owner_user_id,
            club_name=payload.club_name,
            short_name=payload.short_name,
            slug=payload.slug,
            crest_asset_ref=payload.crest_asset_ref,
            primary_color=payload.primary_color,
            secondary_color=payload.secondary_color,
            accent_color=payload.accent_color,
            home_venue_name=payload.home_venue_name,
            country_code=payload.country_code.upper() if payload.country_code else None,
            region_name=payload.region_name,
            city_name=payload.city_name,
            description=payload.description,
            visibility=payload.visibility.value,
            founded_at=payload.founded_at,
        )
        self.session.add(club)
        self.session.flush()
        ClubReputationService(self.session).ensure_profile(club.id)
        ClubDynastyService(self.session).ensure_progress(club.id)
        ClubTrophyService(self.session).ensure_cabinet(club.id)
        self.session.flush()
        RegenBootstrapService(self.session).bootstrap_for_new_club(club)
        self.session.commit()
        self.session.refresh(club)
        return club

    def update_club_profile(
        self,
        *,
        club_id: str,
        owner_user_id: str,
        payload: ClubUpdateRequest,
    ) -> ClubProfile:
        club = self._require_owned_club(club_id, owner_user_id)
        updates = payload.model_dump(exclude_unset=True)
        for field_name, value in updates.items():
            if field_name == "visibility" and isinstance(value, ClubIdentityVisibility):
                value = value.value
            if field_name == "country_code" and isinstance(value, str):
                value = value.upper()
            setattr(club, field_name, value)
        self.session.commit()
        self.session.refresh(club)
        return club

    def get_club_profile(self, club_id: str) -> ClubProfileCore:
        return ClubProfileCore.model_validate(self._require_club(club_id))

    def upsert_branding(
        self,
        *,
        club_id: str,
        owner_user_id: str,
        payload: BrandingUpsertRequest,
    ) -> tuple[ClubProfileCore, ClubIdentityThemeCore | None, list[ClubBrandingAssetCore]]:
        club = self._require_owned_club(club_id, owner_user_id)
        theme = self.session.scalar(
            select(ClubIdentityTheme)
            .where(ClubIdentityTheme.club_id == club_id, ClubIdentityTheme.is_active.is_(True))
            .order_by(ClubIdentityTheme.updated_at.desc())
        )
        if payload.theme_name or payload.header_asset_ref or payload.backdrop_asset_ref or payload.cabinet_theme_code:
            if theme is None:
                theme = ClubIdentityTheme(
                    club_id=club_id,
                    name=payload.theme_name or f"{club.club_name} Theme",
                )
                self.session.add(theme)
            else:
                theme.name = payload.theme_name or theme.name
            theme.header_asset_ref = payload.header_asset_ref
            theme.backdrop_asset_ref = payload.backdrop_asset_ref
            theme.cabinet_theme_code = payload.cabinet_theme_code
            theme.frame_code = payload.frame_code
            theme.visibility = payload.visibility.value
            theme.metadata_json = payload.metadata_json
            theme.is_active = True

        for asset in payload.assets:
            self.session.add(
                ClubBrandingAsset(
                    club_id=club_id,
                    asset_type=asset.asset_type.value,
                    asset_name=asset.asset_name,
                    asset_ref=asset.asset_ref,
                    catalog_item_id=asset.catalog_item_id,
                    slot_key=asset.slot_key,
                    moderation_status="pending_review" if asset.custom_text else "approved",
                    metadata_json={**asset.metadata_json, "custom_text": asset.custom_text},
                )
            )
        self.session.commit()
        return self.get_branding(club_id)

    def get_branding(
        self,
        club_id: str,
    ) -> tuple[ClubProfileCore, ClubIdentityThemeCore | None, list[ClubBrandingAssetCore]]:
        club = self._require_club(club_id)
        theme = self.session.scalar(
            select(ClubIdentityTheme)
            .where(ClubIdentityTheme.club_id == club_id, ClubIdentityTheme.is_active.is_(True))
            .order_by(ClubIdentityTheme.updated_at.desc())
        )
        assets = self.session.scalars(
            select(ClubBrandingAsset)
            .where(ClubBrandingAsset.club_id == club_id)
            .order_by(ClubBrandingAsset.created_at.desc())
        ).all()
        return (
            ClubProfileCore.model_validate(club),
            ClubIdentityThemeCore.model_validate(theme) if theme is not None else None,
            [ClubBrandingAssetCore.model_validate(item) for item in assets],
        )

    def _require_club(self, club_id: str) -> ClubProfile:
        club = self.session.get(ClubProfile, club_id)
        if club is None:
            raise LookupError(f"club {club_id} was not found")
        return club

    def _require_owned_club(self, club_id: str, owner_user_id: str) -> ClubProfile:
        club = self._require_club(club_id)
        if club.owner_user_id != owner_user_id:
            raise PermissionError("club_owner_required")
        return club
