from __future__ import annotations

from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.club_sale_market.router import router as club_sale_market_router
from app.club_identity.dynasty.api.router import router as dynasty_router
from app.club_identity.reputation.router import router as reputation_router
from app.club_identity.trophies.router import router as trophies_router
from app.segments.clubs.segment_clubs import router as clubs_router

base_router = APIRouter()
base_router.include_router(club_sale_market_router)
base_router.include_router(clubs_router)
base_router.include_router(reputation_router, prefix="/api")
base_router.include_router(reputation_router, prefix="/api/v2")
base_router.include_router(reputation_router)
base_router.include_router(dynasty_router)
base_router.include_router(trophies_router)

router = APIRouter()
router.include_router(base_router)

existing_paths = {r.path for r in base_router.routes if isinstance(r, APIRoute)}

for r in list(base_router.routes):
    if not isinstance(r, APIRoute):
        continue
    if r.path.startswith("/api/clubs"):
        suffix = r.path[len("/api/clubs") :]
        v2_path = f"/api/v2/clubs{suffix}"
        short_path = f"/clubs{suffix}"
        if v2_path not in existing_paths:
            router.add_api_route(
                v2_path,
                r.endpoint,
                methods=list(r.methods or []),
                response_model=r.response_model,
                dependencies=r.dependencies,
                summary=r.summary,
                description=r.description,
                tags=r.tags,
                status_code=r.status_code,
            )
            existing_paths.add(v2_path)
        if short_path not in existing_paths:
            router.add_api_route(
                short_path,
                r.endpoint,
                methods=list(r.methods or []),
                response_model=r.response_model,
                dependencies=r.dependencies,
                summary=r.summary,
                description=r.description,
                tags=r.tags,
                status_code=r.status_code,
            )
            existing_paths.add(short_path)
    elif r.path.startswith("/clubs"):
        suffix = r.path[len("/clubs") :]
        api_path = f"/api/clubs{suffix}"
        v2_path = f"/api/v2/clubs{suffix}"
        if api_path not in existing_paths:
            router.add_api_route(
                api_path,
                r.endpoint,
                methods=list(r.methods or []),
                response_model=r.response_model,
                dependencies=r.dependencies,
                summary=r.summary,
                description=r.description,
                tags=r.tags,
                status_code=r.status_code,
            )
            existing_paths.add(api_path)
        if v2_path not in existing_paths:
            router.add_api_route(
                v2_path,
                r.endpoint,
                methods=list(r.methods or []),
                response_model=r.response_model,
                dependencies=r.dependencies,
                summary=r.summary,
                description=r.description,
                tags=r.tags,
                status_code=r.status_code,
            )
            existing_paths.add(v2_path)

__all__ = ["router"]
