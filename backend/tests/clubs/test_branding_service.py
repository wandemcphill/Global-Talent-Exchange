from __future__ import annotations

from backend.app.schemas.club_requests import BrandingUpsertRequest, ClubCreateRequest, JerseyCreateRequest
from backend.app.services.club_branding_service import ClubBrandingService
from backend.app.services.club_cosmetic_catalog_service import ClubCosmeticCatalogService
from backend.app.services.club_jersey_service import ClubJerseyService


def _create_club(session) -> str:
    club = ClubBrandingService(session).create_club_profile(
        owner_user_id="user-owner",
        payload=ClubCreateRequest.model_validate(
            {
                "club_name": "Identity FC",
                "short_name": "IFC",
                "slug": "identity-fc",
                "primary_color": "#004466",
                "secondary_color": "#ffffff",
                "accent_color": "#ff6600",
                "visibility": "public",
            }
        ),
    )
    return club.id


def test_branding_and_jersey_services_create_moderation_aware_custom_assets(session) -> None:
    club_id = _create_club(session)
    branding_service = ClubBrandingService(session)
    jersey_service = ClubJerseyService(session)

    profile, theme, assets = branding_service.upsert_branding(
        club_id=club_id,
        owner_user_id="user-owner",
        payload=BrandingUpsertRequest.model_validate(
            {
                "theme_name": "Heritage Night",
                "backdrop_asset_ref": "heritage-backdrop",
                "assets": [
                    {
                        "asset_type": "banner",
                        "asset_name": "Founder Banner",
                        "asset_ref": "banner-1",
                        "custom_text": "Legacy Lives Here",
                    }
                ],
            }
        ),
    )
    jersey = jersey_service.create_jersey(
        club_id=club_id,
        owner_user_id="user-owner",
        payload=JerseyCreateRequest.model_validate(
            {
                "name": "Home Kit",
                "slot_type": "home",
                "base_template_id": "classic",
                "primary_color": "#004466",
                "secondary_color": "#ffffff",
                "trim_color": "#ff6600",
                "motto_text": "Legacy Lives Here",
            }
        ),
    )
    catalog_items = ClubCosmeticCatalogService(session).list_items()

    assert profile.club_name == "Identity FC"
    assert theme is not None and theme.name == "Heritage Night"
    assert len(assets) == 1
    assert assets[0].moderation_status == "pending_review"
    assert jersey.moderation_status == "pending_review"
    assert len(catalog_items) >= 6
