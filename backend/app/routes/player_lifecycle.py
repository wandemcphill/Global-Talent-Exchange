from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.routing import APIRoute

from app.routes.player_lifecycle_authorization import authorize_player_lifecycle_mutation
from app.routes.regen_offer_authorization import authorize_regen_offer_quote
from app.routes.transfer_authorization import authorize_transfer_mutation
from app.segments.player_lifecycle.regen_contract_submission import router as regen_contract_submission_router
from app.segments.player_lifecycle.scouting_action import router as scouting_action_router
from app.segments.player_lifecycle.segment_player_lifecycle import router as lifecycle_router

# Pass dependencies to include_router: appending to an already-populated
# router's `dependencies` does not reach routes registered before the append.
_AUTHORIZATION_DEPENDENCIES = [
    Depends(authorize_transfer_mutation),
    Depends(authorize_regen_offer_quote),
    Depends(authorize_player_lifecycle_mutation),
]


def _split_mutations(source: APIRouter) -> tuple[APIRouter, APIRouter]:
    reads, mutations = APIRouter(), APIRouter()
    for route in source.routes:
        is_mutation = isinstance(route, APIRoute) and bool(route.methods - {"GET", "HEAD"})
        (mutations if is_mutation else reads).routes.append(route)
    return reads, mutations


_lifecycle_reads, _lifecycle_mutations = _split_mutations(lifecycle_router)

router = APIRouter()
# Public lifecycle reads stay anonymous; the authorizers resolve the caller, so only mutations get them.
router.include_router(_lifecycle_reads)
router.include_router(_lifecycle_mutations, dependencies=_AUTHORIZATION_DEPENDENCIES)
router.include_router(regen_contract_submission_router, dependencies=_AUTHORIZATION_DEPENDENCIES)
router.include_router(scouting_action_router, dependencies=_AUTHORIZATION_DEPENDENCIES)

__all__ = ["router"]
