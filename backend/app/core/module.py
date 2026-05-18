from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from importlib import import_module
import logging
from time import perf_counter
from typing import Any, Callable

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from app.core.api_contract import register_versioned_route_aliases
from app.core.container import ApplicationContext

ModuleHook = Callable[[FastAPI, ApplicationContext], None]
HookReference = ModuleHook | str
RouterTransform = Callable[[APIRouter], APIRouter]

logger = logging.getLogger(__name__)


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
            (
                _resolve_attribute(
                    hook_ref,
                    expected_type=None,
                    label=f"{phase} hook for module '{self.name}'",
                )
                if isinstance(hook_ref, str)
                else hook_ref
            )
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
            loaded_module_names.add(module.name)
            app.state.loaded_domain_module_names = loaded_module_names
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
        register_versioned_route_aliases(app, router.routes)
        registered_routes.update(module_routes)
        loaded_module_names.add(module.name)
        app.state.loaded_domain_module_names = loaded_module_names

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
            hook_label = _hook_label(hook)
            hook_stage = _classify_hook_stage(hook_label)
            if phase == "startup" and _should_skip_startup_hook(context, hook_label, hook_stage):
                _record_hook_profile(
                    app,
                    module_name=module.name,
                    hook_name=hook_label,
                    phase=phase,
                    stage=hook_stage,
                    duration_seconds=0.0,
                    status="skipped",
                )
                logger.info(
                    "app.startup.hook.skipped module=%s hook=%s stage=%s profile=%s",
                    module.name,
                    hook_label,
                    hook_stage,
                    getattr(context.settings, "startup_profile", "production"),
                )
                continue
            started_at = perf_counter()
            status = "complete"
            try:
                hook(app, context)
            except Exception:
                status = "failed"
                raise
            finally:
                duration_seconds = perf_counter() - started_at
                _record_hook_profile(
                    app,
                    module_name=module.name,
                    hook_name=hook_label,
                    phase=phase,
                    stage=hook_stage,
                    duration_seconds=duration_seconds,
                    status=status,
                )
                if phase == "startup":
                    logger.info(
                        "app.startup.hook.%s module=%s hook=%s stage=%s duration_ms=%.2f",
                        status,
                        module.name,
                        hook_label,
                        hook_stage,
                        duration_seconds * 1000,
                    )


def _hook_label(hook: ModuleHook) -> str:
    module_name = getattr(hook, "__module__", "")
    hook_name = getattr(hook, "__name__", repr(hook))
    return f"{module_name}:{hook_name}" if module_name else hook_name


def _classify_hook_stage(hook_label: str) -> str:
    normalized = hook_label.lower()
    if "preseeded_national" in normalized or "preload" in normalized or "portrait" in normalized:
        return "preload"
    if (
        ".worker" in normalized
        or "scheduler" in normalized
        or "runtime" in normalized
        or ":bind_" in normalized
        or "install_broadcast_runtime" in normalized
    ):
        return "worker"
    if "seed" in normalized or "defaults" in normalized or "catalog" in normalized:
        return "seed"
    return "critical"


def _should_skip_startup_hook(
    context: ApplicationContext,
    hook_label: str,
    hook_stage: str,
) -> bool:
    settings = context.settings
    normalized = hook_label.lower()
    if hook_stage == "seed" and not getattr(settings, "run_startup_seeding", True):
        return True
    if "regen" in normalized and hook_stage == "preload" and not getattr(settings, "regen_preload_enabled", True):
        return True
    if "portrait" in normalized and not getattr(settings, "portrait_preload_enabled", True):
        return True
    if getattr(settings, "fast_test_startup_enabled", False) and hook_stage in {"seed", "preload", "worker"}:
        return True
    return False


def _record_hook_profile(
    app: FastAPI,
    *,
    module_name: str,
    hook_name: str,
    phase: str,
    stage: str,
    duration_seconds: float,
    status: str,
) -> None:
    records = getattr(app.state, "startup_hook_records", None)
    if records is None:
        records = []
        app.state.startup_hook_records = records
    records.append(
        {
            "module": module_name,
            "hook": hook_name,
            "phase": phase,
            "stage": stage,
            "duration_ms": round(duration_seconds * 1000, 3),
            "status": status,
        }
    )


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
