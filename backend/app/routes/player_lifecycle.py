from __future__ import annotations

from app.segments.player_lifecycle.regen_contract_offer_routes import router as regen_contract_offer_router
from app.segments.player_lifecycle.segment_player_lifecycle import router

router.include_router(regen_contract_offer_router)

__all__ = ["router"]
