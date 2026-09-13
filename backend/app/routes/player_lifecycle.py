from __future__ import annotations

from fastapi import APIRouter

from app.segments.player_lifecycle.regen_contract_offer_routes import router as regen_contract_offer_router
from app.segments.player_lifecycle.segment_player_lifecycle import router as lifecycle_router
from app.segments.player_lifecycle.transfer_authorization_routes import router as transfer_authorization_router

router = APIRouter()
router.include_router(transfer_authorization_router)
router.include_router(regen_contract_offer_router)
router.include_router(lifecycle_router)

__all__ = ["router"]
