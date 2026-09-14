from __future__ import annotations

from fastapi import Depends

from app.routes.regen_offer_authorization import authorize_regen_offer_quote
from app.routes.transfer_authorization import authorize_transfer_mutation
from app.segments.player_lifecycle.regen_contract_submission import router as regen_contract_submission_router
from app.segments.player_lifecycle.scouting_action import router as scouting_action_router
from app.segments.player_lifecycle.segment_player_lifecycle import router as lifecycle_router

router = lifecycle_router
router.dependencies.append(Depends(authorize_transfer_mutation))
router.dependencies.append(Depends(authorize_regen_offer_quote))
router.include_router(regen_contract_submission_router)
router.include_router(scouting_action_router)

__all__ = ["router"]
