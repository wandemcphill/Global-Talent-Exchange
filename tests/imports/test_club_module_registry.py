from __future__ import annotations

from app.modules import DOMAIN_MODULES

_CANONICAL_CLUB_CHILD_ROUTER_PATHS = {
    "app.segments.clubs.segment_clubs:router",
    "app.club_sale_market.router:router",
    "app.club_identity.reputation.router:router",
    "app.club_identity.dynasty.api.router:router",
    "app.club_identity.trophies.router:router",
}


def test_canonical_clubs_is_the_only_module_owner_for_aggregate_club_routers() -> None:
    modules_by_name = {module.name: module for module in DOMAIN_MODULES}

    assert "canonical_clubs" in modules_by_name
    assert modules_by_name["canonical_clubs"].router_path == "app.routes.clubs:router"

    registered_child_router_paths = {
        module.router_path for module in DOMAIN_MODULES if module.router_path in _CANONICAL_CLUB_CHILD_ROUTER_PATHS
    }

    assert registered_child_router_paths == set()
