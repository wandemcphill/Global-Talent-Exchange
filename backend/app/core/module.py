from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.core.container import ApplicationContext

ModuleHook = Callable[[FastAPI, ApplicationContext], None]
HookReference = ModuleHook | str
RouterTransform = Callable[[APIRouter], APIRouter]


@dataclass(frozen=True, slots=True)
class DomainModule:
    name: str
    router: APIRouter | None = None
    router_path: str | None = None
    router_attr: str = "router"
    router_transform: RouterTransform | None = None
    on_startup: tuple[HookReference, ...] = field(default_factory=tuple)
    on_shutdown: tuple[HookReference, ...] = field(default_factory=tuple)

    def load_router(self) -> APIRouter | None:
        resolved_router = self.router
        if resolved_router is None and self.router_path is not None:
            resolved_router = _resolve_attribute(
                self.router_path,
                default_attr=self.router_attr,
                expected_type=APIRouter,
                label=f"router for module '{self.name}'",
            )
        if resolved_router is None:
            return None
        if self.router_transform is not None:
            return self.router_transform(resolved_router)
        return resolved_router

    def load_hooks(self, *, phase: str) -> tuple[ModuleHook, ...]:
        hook_refs = self.on_startup if phase == "startup" else self.on_shutdown
        return tuple(
            _resolve_attribute(
                hook_ref,
                expected_type=None,
                label=f"{phase} hook for module '{self.name}'",
            )
            if isinstance(hook_ref, str)
            else hook_ref
            for hook_ref in hook_refs
        )


def register_domain_modules(app: FastAPI, modules: Iterable[DomainModule]) -> None:
    seen_module_names: set[str] = set()
    registered_routes = _route_fingerprints(app.routes)
    loaded_module_names: set[str] = set(getattr(app.state, "loaded_domain_module_names", set()))

    for module in modules:
        if module.name in seen_module_names:
            raise ValueError(f"Duplicate domain module name detected: {module.name}")
        seen_module_names.add(module.name)
        if module.name in loaded_module_names:
            continue

        router = module.load_router()
        if router is None:
            continue

        module_routes = _route_fingerprints(router.routes)
        collisions = module_routes & registered_routes
        if collisions:
            collision_labels = ", ".join(
                f"{'/'.join(methods)} {path}"
                for path, methods in sorted(collisions, key=lambda item: (item[0], item[1]))
            )
            raise ValueError(f"Router collision detected for module '{module.name}': {collision_labels}")

        app.include_router(router)
        registered_routes.update(module_routes)
        loaded_module_names.add(module.name)

    app.state.loaded_domain_module_names = loaded_module_names


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
        for hook in module.load_hooks(phase=phase):
            hook(app, context)


def _route_fingerprints(routes: Iterable[object]) -> set[tuple[str, tuple[str, ...]]]:
    fingerprints: set[tuple[str, tuple[str, ...]]] = set()
    for route in routes:
        if not isinstance(route, APIRoute):
            continue
        fingerprints.add((route.path, tuple(sorted(route.methods or ()))))
    return fingerprints


def _resolve_attribute(
    reference: str,
    *,
    default_attr: str | None = None,
    expected_type: type[Any] | None,
    label: str,
) -> Any:
    module_path, separator, attr_name = reference.partition(":")
    resolved_attr = attr_name if separator else default_attr
    if resolved_attr is None:
        raise ValueError(f"Missing attribute name while resolving {label}: {reference}")

    module = import_module(module_path)
    resolved = getattr(module, resolved_attr)
    if expected_type is not None and not isinstance(resolved, expected_type):
        raise TypeError(f"Resolved {label} is not a {expected_type.__name__}: {reference}")
    return resolved
