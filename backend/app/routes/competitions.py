from __future__ import annotations

from fastapi import APIRouter

from app.competitions.router import router as competition_control_router
from app.segments.competitions.segment_competitions import router as competition_segment_router

router = APIRouter()
router.include_router(competition_segment_router)
router.include_router(competition_control_router)

__all__ = ["router"]
