from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from threading import Thread

from fastapi import FastAPI
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.auth.service import AuthService
from app.models.user import UserRole

from app.auth.dependencies import get_session as auth_get_session
from app.core.config import Settings, get_settings
from app.core.container import ApplicationContext, build_application_context
from app.core.database import create_database_engine, create_session_factory, get_session as core_get_session
from app.core.module import DomainModule, register_domain_modules, run_module_hooks
from app.db import get_session as db_get_session
from app.modules import DOMAIN_MODULES

INITIAL_ADMIN_EMAIL = "vidvimedialtd@gmail.com"
INITIAL_ADMIN_PASSWORD = "NewPass1234!"
INITIAL_ADMIN_USERNAME = "vidvimedialtd"
INITIAL_ADMIN_DISPLAY_NAME = "GTEX God Mode Admin"
logger = logging.getLogger(__name__)


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
        logger.info("app.startup.begin")
        try:
            logger.info("app.startup.database_initialize.begin")
            initialized_engine = context.database.initialize(run_migration_check=run_migration_check)
            logger.info("app.startup.database_initialize.complete")
        except Exception:
            logger.exception("app.startup.database_initialize.failed")
            raise

        logger.info("app.startup.application_state_bind.begin")
        _bind_application_state(app, context=context, engine=initialized_engine, modules=modules)
        logger.info("app.startup.application_state_bind.complete")

        logger.info("app.startup.deferred_startup.begin")
        _start_deferred_startup(app, context=context, modules=modules)
        logger.info("app.startup.deferred_startup.complete")
        logger.info("app.startup.complete")
        try:
            yield
        finally:
            logger.info("app.shutdown.begin")
            run_module_hooks(app, context, modules, phase="shutdown")
            logger.info("app.shutdown.complete")

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


def _start_deferred_startup(
    app: FastAPI,
    *,
    context: ApplicationContext,
    modules: tuple[DomainModule, ...],
) -> None:
    logger.info("app.startup.deferred_startup.thread_create")
    startup_thread = Thread(
        target=_run_deferred_startup,
        kwargs={"app": app, "context": context, "modules": modules},
        name="gtex-startup-bootstrap",
        daemon=True,
    )
    app.state.deferred_startup_thread = startup_thread
    startup_thread.start()
    logger.info("app.startup.deferred_startup.thread_started thread_name=%s", startup_thread.name)


def _run_deferred_startup(
    *,
    app: FastAPI,
    context: ApplicationContext,
    modules: tuple[DomainModule, ...],
) -> None:
    try:
        logger.info("app.startup.bootstrap.begin")
        logger.info("app.startup.initial_admin.begin")
        _ensure_initial_admin(context.database.session_factory)
        logger.info("app.startup.initial_admin.complete")
        logger.info("app.startup.module_hooks.begin")
        run_module_hooks(app, context, modules, phase="startup")
        logger.info("app.startup.module_hooks.complete")
        logger.info("app.startup.bootstrap_complete")
    except Exception:
        logger.exception("app.startup.bootstrap_failed")


app = create_app()


def _ensure_initial_admin(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as session:
        service = AuthService()
        service.ensure_admin_user(
            session,
            email=INITIAL_ADMIN_EMAIL,
            password=INITIAL_ADMIN_PASSWORD,
            username=INITIAL_ADMIN_USERNAME,
            display_name=INITIAL_ADMIN_DISPLAY_NAME,
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()
