from __future__ import annotations

from fastapi import APIRouter, Query, Request

from app.moments.schemas import LiveMomentsResponse
from app.moments.service import ensure_moments_engine

router = APIRouter()
api_router = APIRouter(prefix="/api/moments", tags=["moments"])
public_router = APIRouter(prefix="/moments", tags=["moments"])


@api_router.get("/live", response_model=LiveMomentsResponse)
@public_router.get("/live", response_model=LiveMomentsResponse)
def read_live_moments(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    match_id: str | None = Query(default=None),
) -> LiveMomentsResponse:
    return ensure_moments_engine(request.app).live(limit=limit, match_id=match_id)


router.include_router(api_router)
router.include_router(public_router)

__all__ = ["router"]
