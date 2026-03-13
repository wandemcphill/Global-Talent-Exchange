from __future__ import annotations

from fastapi import APIRouter

from backend.app.club_identity.dynasty.api.router import router as dynasty_router
from backend.app.club_identity.reputation.router import router as reputation_router
from backend.app.segments.clubs.segment_clubs import router as clubs_router

router = APIRouter()
router.include_router(clubs_router)
router.include_router(reputation_router)
router.include_router(dynasty_router)

__all__ = ["router"]
