from __future__ import annotations

from app.segments.player_lifecycle.regen_contract_submission import router as regen_contract_submission_router
from app.segments.player_lifecycle.segment_player_lifecycle import router as lifecycle_router

router = lifecycle_router
router.include_router(regen_contract_submission_router)

__all__ = ["router"]
