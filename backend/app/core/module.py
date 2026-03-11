from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Callable

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from backend.app.core.container import ApplicationContext

ModuleHook = Callable[[FastAPI, ApplicationContext], None]


@dataclass(frozen=True, slots=True)
class DomainModule:
    name: str
    router: APIRouter | None = None
    on_startup: tuple[ModuleHook, ...] = field(default_factory=tuple)
    on_shutdown: tuple[ModuleHook, ...] = field(default_factory=tuple)


def register_domain_modules(app: FastAPI, modules: Iterable[DomainModule]) -> None:
    seen_module_names: set[str] = set()
    registered_routes = _route_fingerprints(app.routes)

    for module in modules:
        if module.name in seen_module_names:
            raise ValueError(f"Duplicate domain module name detected: {module.name}")
        seen_module_names.add(module.name)

        if module.router is None:
            continue

        module_routes = _route_fingerprints(module.router.routes)
        collisions = module_routes & registered_routes
        if collisions:
            collision_labels = ", ".join(
                f"{'/'.join(methods)} {path}"
                for path, methods in sorted(collisions, key=lambda item: (item[0], item[1]))
            )
            raise ValueError(f"Router collision detected for module '{module.name}': {collision_labels}")

        app.include_router(module.router)
        registered_routes.update(module_routes)


def run_module_hooks(
    app: FastAPI,
    context: ApplicationContext,
    modules: Iterable[DomainModule],
    *,
    phase: str,
) -> None:
    if phase not in {"startup", "shutdown"}:
        raise ValueError(f"Unsupported module lifecycle phase: {phase}")

    for module in modules:
        hooks = module.on_startup if phase == "startup" else module.on_shutdown
        for hook in hooks:
            hook(app, context)


def _route_fingerprints(routes: Iterable[object]) -> set[tuple[str, tuple[str, ...]]]:
    fingerprints: set[tuple[str, tuple[str, ...]]] = set()
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        fingerprints.add((route.path, tuple(sorted(route.methods or ()))))
    return fingerprints
