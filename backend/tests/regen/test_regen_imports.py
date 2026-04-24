from __future__ import annotations

import importlib


def test_regen_router_and_module_imports_smoke() -> None:
    imported = {
        name: importlib.import_module(name)
        for name in (
            "app.regen_ecosystem.router",
            "app.regen_universe.router",
            "app.routes.player_agency",
            "app.modules",
        )
    }

    assert imported["app.regen_ecosystem.router"].router is not None
    assert imported["app.regen_universe.router"].router is not None
    assert imported["app.routes.player_agency"].router is not None
    assert imported["app.modules"].DOMAIN_MODULES
