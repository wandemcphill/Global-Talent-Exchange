from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user
from backend.app.db import get_session
from backend.app.schemas.club_branding_core import ClubCosmeticPurchaseCore
from backend.app.schemas.club_requests import (
    BrandingUpsertRequest,
    CatalogPurchaseRequest,
    ClubCreateRequest,
    ClubUpdateRequest,
    JerseyCreateRequest,
    JerseyUpdateRequest,
)
from backend.app.schemas.club_responses import (
    ClubBrandingView,
    ClubCatalogView,
    ClubJerseysView,
    ClubProfileView,
    ClubPurchasesView,
    ClubShowcaseView,
    ClubTrophiesView,
)
from backend.app.services.club_branding_service import ClubBrandingService
from backend.app.services.club_cosmetic_catalog_service import ClubCosmeticCatalogService
from backend.app.services.club_jersey_service import ClubJerseyService
from backend.app.services.club_purchase_service import ClubPurchaseService
from backend.app.services.club_showcase_service import ClubShowcaseService
from backend.app.services.club_trophy_service import ClubTrophyService

router = APIRouter(prefix="/api/clubs", tags=["clubs"])


def _user_id(current_user) -> str:
    user_id = getattr(current_user, "id", None)
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_context_missing")
    return user_id


def _to_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, PermissionError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error))
    if isinstance(error, ValueError):
        status_code = status.HTTP_409_CONFLICT if str(error) == "club_slug_taken" else status.HTTP_400_BAD_REQUEST
        return HTTPException(status_code=status_code, detail=str(error))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.post("", response_model=ClubProfileView, status_code=status.HTTP_201_CREATED)
def create_club(
    payload: ClubCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubProfileView:
    try:
        club = ClubBrandingService(session).create_club_profile(owner_user_id=_user_id(current_user), payload=payload)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubProfileView(profile=ClubBrandingService(session).get_club_profile(club.id))


@router.get("/catalog", response_model=ClubCatalogView)
def get_catalog(session: Session = Depends(get_session)) -> ClubCatalogView:
    return ClubCatalogView(items=ClubCosmeticCatalogService(session).list_items())


@router.post("/catalog/purchase", response_model=ClubCosmeticPurchaseCore, status_code=status.HTTP_201_CREATED)
def purchase_catalog_item(
    payload: CatalogPurchaseRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubCosmeticPurchaseCore:
    try:
        purchase = ClubPurchaseService(session).purchase_catalog_item(
            buyer_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubCosmeticPurchaseCore.model_validate(purchase)


@router.patch("/{club_id}", response_model=ClubProfileView)
def update_club(
    club_id: str,
    payload: ClubUpdateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubProfileView:
    try:
        club = ClubBrandingService(session).update_club_profile(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubProfileView(profile=ClubBrandingService(session).get_club_profile(club.id))


@router.get("/{club_id}", response_model=ClubProfileView)
def get_club(club_id: str, session: Session = Depends(get_session)) -> ClubProfileView:
    try:
        profile = ClubBrandingService(session).get_club_profile(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubProfileView(profile=profile)


@router.get("/{club_id}/showcase", response_model=ClubShowcaseView)
def get_club_showcase(club_id: str, session: Session = Depends(get_session)) -> ClubShowcaseView:
    try:
        return ClubShowcaseService(session).get_showcase(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error


@router.get("/{club_id}/trophies", response_model=ClubTrophiesView)
def get_club_trophies(club_id: str, session: Session = Depends(get_session)) -> ClubTrophiesView:
    try:
        cabinet, trophies = ClubTrophyService(session).get_trophy_cabinet(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubTrophiesView(cabinet=cabinet, trophies=trophies)


@router.post("/{club_id}/branding", response_model=ClubBrandingView, status_code=status.HTTP_201_CREATED)
@router.patch("/{club_id}/branding", response_model=ClubBrandingView)
def upsert_branding(
    club_id: str,
    payload: BrandingUpsertRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubBrandingView:
    try:
        profile, theme, assets = ClubBrandingService(session).upsert_branding(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubBrandingView(profile=profile, theme=theme, assets=assets)


@router.get("/{club_id}/branding", response_model=ClubBrandingView)
def get_branding(club_id: str, session: Session = Depends(get_session)) -> ClubBrandingView:
    try:
        profile, theme, assets = ClubBrandingService(session).get_branding(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubBrandingView(profile=profile, theme=theme, assets=assets)


@router.post("/{club_id}/jerseys", response_model=ClubJerseysView, status_code=status.HTTP_201_CREATED)
def create_jersey(
    club_id: str,
    payload: JerseyCreateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubJerseysView:
    try:
        ClubJerseyService(session).create_jersey(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubJerseysView(jerseys=ClubJerseyService(session).list_jerseys(club_id))


@router.patch("/{club_id}/jerseys/{jersey_id}", response_model=ClubJerseysView)
def update_jersey(
    club_id: str,
    jersey_id: str,
    payload: JerseyUpdateRequest,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubJerseysView:
    try:
        ClubJerseyService(session).update_jersey(
            club_id=club_id,
            jersey_id=jersey_id,
            owner_user_id=_user_id(current_user),
            payload=payload,
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubJerseysView(jerseys=ClubJerseyService(session).list_jerseys(club_id))


@router.get("/{club_id}/jerseys", response_model=ClubJerseysView)
def list_jerseys(club_id: str, session: Session = Depends(get_session)) -> ClubJerseysView:
    try:
        jerseys = ClubJerseyService(session).list_jerseys(club_id)
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubJerseysView(jerseys=jerseys)


@router.get("/{club_id}/purchases", response_model=ClubPurchasesView)
def list_purchases(
    club_id: str,
    session: Session = Depends(get_session),
    current_user=Depends(get_current_user),
) -> ClubPurchasesView:
    try:
        purchases = ClubPurchaseService(session).list_purchases(
            club_id=club_id,
            owner_user_id=_user_id(current_user),
        )
    except Exception as error:  # noqa: BLE001
        raise _to_http_error(error) from error
    return ClubPurchasesView(purchases=purchases)
