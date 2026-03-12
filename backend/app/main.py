from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.dependencies import get_session as auth_get_session
from backend.app.core.config import Settings, get_settings
from backend.app.core.container import ApplicationContext, build_application_context
from backend.app.core.database import create_database_engine, create_session_factory, get_session as core_get_session
from backend.app.core.module import DomainModule, register_domain_modules, run_module_hooks
from backend.app.db import get_session as db_get_session
from backend.app.modules import DOMAIN_MODULES


def create_app(
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
    database_session_factory = session_factory or create_session_factory(database_engine)
    context = build_application_context(
        settings=resolved_settings,
        engine=database_engine,
        session_factory=database_session_factory,
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        initialized_engine = context.database.initialize(run_migration_check=run_migration_check)
        _bind_application_state(app, context=context, engine=initialized_engine, modules=modules)
        run_module_hooks(app, context, modules, phase="startup")
        try:
            yield
        finally:
            run_module_hooks(app, context, modules, phase="shutdown")

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        lifespan=lifespan,
    )
    app.dependency_overrides[auth_get_session] = context.database.get_session
    app.dependency_overrides[db_get_session] = context.database.get_session
    app.dependency_overrides[core_get_session] = context.database.get_session
    register_domain_modules(app, modules)
    return app


def _resolve_database_engine(
    *,
    settings: Settings,
    engine: Engine | None,
    session_factory: sessionmaker[Session] | None,
) -> Engine:
    if engine is not None:
        return engine
    bound_engine = session_factory.kw.get("bind") if session_factory is not None else None  # type: ignore[union-attr]
    if bound_engine is not None:
        return bound_engine
    return create_database_engine(settings.database_url)


def _bind_application_state(
    app: FastAPI,
    *,
    context: ApplicationContext,
    engine: Engine,
    modules: tuple[DomainModule, ...],
) -> None:
    app.state.settings = context.settings
    app.state.context = context
    app.state.db_engine = engine
    app.state.session_factory = context.database.session_factory
    app.state.cache_backend = context.cache_backend
    app.state.event_publisher = context.event_publisher
    app.state.job_backend = context.job_backend
    app.state.notifications = context.notifications
    app.state.realtime = context.realtime
    app.state.market_engine = context.market_engine
    app.state.ingestion_pipeline = context.ingestion_pipeline
    app.state.value_engine_bridge = context.value_engine_bridge
    app.state.ingestion_job_runner = context.ingestion_job_runner
    app.state.domain_modules = tuple(module.name for module in modules)


app = create_app()
