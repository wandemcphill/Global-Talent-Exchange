from __future__ import annotations

from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.dependencies import get_session
from backend.app.core.config import Settings, get_settings
from backend.app.core.container import ApplicationContext, build_application_context
from backend.app.core.module import DomainModule, register_domain_modules, run_module_hooks
from backend.app.ingestion.demo_bootstrap import CANONICAL_DEMO_PLAYER_COUNT
from backend.app.main import _bind_application_state, _resolve_database_engine
from backend.app.modules import DOMAIN_MODULES
from backend.app.simulation.runtime import seed_demo_simulation_for_app
from backend.app.simulation.service import DEFAULT_ILLIQUID_PLAYER_COUNT, DEFAULT_LIQUID_PLAYER_COUNT


def create_demo_simulation_app(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
    modules: tuple[DomainModule, ...] = DOMAIN_MODULES,
    run_migration_check: bool | None = None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    database_engine = _resolve_database_engine(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
    )
    database_session_factory = session_factory or sessionmaker(
        bind=database_engine,
        autoflush=False,
        expire_on_commit=False,
    )
    context = build_application_context(
        settings=resolved_settings,
        engine=database_engine,
        session_factory=database_session_factory,
    )

    demo_simulation_enabled = _get_bool("GTE_DEMO_SIMULATION_ENABLED", True)
    bootstrap_demo = _get_bool("GTE_DEMO_SIMULATION_BOOTSTRAP", False)
    seed_liquidity_on_boot = _get_bool("GTE_DEMO_SIMULATION_SEED_ON_BOOT", False)
    demo_player_count = _get_int("GTE_DEMO_SIMULATION_PLAYER_COUNT", CANONICAL_DEMO_PLAYER_COUNT)
    liquid_player_count = _get_int("GTE_DEMO_SIMULATION_LIQUID_PLAYERS", DEFAULT_LIQUID_PLAYER_COUNT)
    illiquid_player_count = _get_int("GTE_DEMO_SIMULATION_ILLIQUID_PLAYERS", DEFAULT_ILLIQUID_PLAYER_COUNT)
    simulation_seed = _get_int("GTE_DEMO_SIMULATION_SEED", 20260311)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialized_engine = context.database.initialize(run_migration_check=run_migration_check)
        _bind_application_state(app, context=context, engine=initialized_engine, modules=modules)
        run_module_hooks(app, context, modules, phase="startup")
        if demo_simulation_enabled:
            seed_demo_simulation_for_app(
                app,
                bootstrap_demo=bootstrap_demo,
                with_liquidity_seed=bootstrap_demo or seed_liquidity_on_boot,
                demo_player_count=demo_player_count,
                simulation_seed=simulation_seed,
                liquid_player_count=liquid_player_count,
                illiquid_player_count=illiquid_player_count,
            )
        try:
            yield
        finally:
            run_module_hooks(app, context, modules, phase="shutdown")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.dependency_overrides[get_session] = context.database.get_session
    register_domain_modules(app, modules)
    return app


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


__all__ = ["create_demo_simulation_app"]
