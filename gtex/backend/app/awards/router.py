from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.awards.schemas import (
    AwardCategoryView,
    AwardNomineeBucketView,
    AwardWinnerView,
    AwardsCeremonyView,
)
from app.awards.service import AwardsCultureService


router = APIRouter(tags=["awards"])


def _service(session: Session = Depends(get_session)) -> AwardsCultureService:
    return AwardsCultureService(session)


@router.get("/awards/categories", response_model=list[AwardCategoryView])
def list_award_categories(service: AwardsCultureService = Depends(_service)) -> list[AwardCategoryView]:
    return [AwardCategoryView.model_validate(item) for item in service.list_categories()]


@router.get("/awards/nominees", response_model=list[AwardNomineeBucketView])
def list_award_nominees(
    season_id: str | None = Query(default=None),
    award_code: str | None = Query(default=None),
    service: AwardsCultureService = Depends(_service),
) -> list[AwardNomineeBucketView]:
    return [
        AwardNomineeBucketView.model_validate(item)
        for item in service.list_nominees(season_id=season_id, award_code=award_code)
    ]


@router.get("/awards/winners", response_model=list[AwardWinnerView])
def list_award_winners(
    season_id: str | None = Query(default=None),
    award_code: str | None = Query(default=None),
    service: AwardsCultureService = Depends(_service),
) -> list[AwardWinnerView]:
    return [
        AwardWinnerView.model_validate(item)
        for item in service.list_winners(season_id=season_id, award_code=award_code)
    ]


@router.get("/awards/ceremony", response_model=AwardsCeremonyView)
def get_awards_ceremony(
    season_id: str | None = Query(default=None),
    service: AwardsCultureService = Depends(_service),
) -> AwardsCeremonyView:
    payload = service.get_ceremony(season_id=season_id)
    return AwardsCeremonyView.model_validate(payload)


__all__ = ["router"]
