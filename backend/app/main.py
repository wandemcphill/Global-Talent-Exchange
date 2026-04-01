from __future__ import annotations

import logging
import os
from threading import Thread

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.container import (
    ApplicationContext,
    Container,
    bind_application_state,
    ensure_session_factory,
    resolve_database_engine,
)
from app.core.module import DomainModule, run_module_hooks
from app.ingestion.real_player_bulk_publish_job_service import RealPlayerBulkPublishJobRegistry
from app.modules import DOMAIN_MODULES

logger = logging.getLogger(__name__)
_ASGI_APP: FastAPI | None = None
_CORS_EXPOSE_HEADERS = (
    "Retry-After",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Scope",
)
INITIAL_ADMIN_EMAIL = os.getenv("GTE_BOOTSTRAP_ADMIN_EMAIL", "vidvimedialtd@gmail.com")
INITIAL_ADMIN_PASSWORD = os.getenv("GTE_BOOTSTRAP_ADMIN_PASSWORD", "NewPass1234!")
INITIAL_ADMIN_USERNAME = os.getenv("GTE_BOOTSTRAP_ADMIN_USERNAME", "vidvimedialtd")
INITIAL_ADMIN_DISPLAY_NAME = os.getenv(
    "GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME",
    "GTEX God Mode Admin",
)


def create_app(
    *,
    settings: Settings | None = None,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
    modules: tuple[DomainModule, ...] = DOMAIN_MODULES,
    run_migration_check: bool | None = None,
) -> FastAPI:
    from app.modules import register_modules
    from app.observability.logging import configure_logging

    resolved_settings = settings or get_settings()
    service_name = resolved_settings.observability_service_name or resolved_settings.kafka_client_id
    configure_logging(
        json_logs=resolved_settings.observability_log_json,
        service_name=service_name,
        environment=resolved_settings.app_env,
    )
    database_engine = resolve_database_engine(
        settings=resolved_settings,
        engine=engine,
        session_factory=session_factory,
    )
    database_session_factory = ensure_session_factory(
        engine=database_engine,
        session_factory=session_factory,
    )
    context = Container(
        settings=resolved_settings,
        engine=database_engine,
        session_factory=database_session_factory,
    )

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
    )
    app.state.settings = resolved_settings
    app.state.container = context
    app.state.context = context
    app.state.db_engine = context.database.engine
    app.state.session_factory = context.database.session_factory
    app.state.read_db_engine = context.database.read_engine
    app.state.read_session_factory = context.database.read_session_factory
    app.state.metrics = context.metrics
    app.state.module_specs = modules
    app.state.domain_modules = tuple(module.name for module in modules)
    app.state.run_migration_check = run_migration_check
    app.state.deferred_startup_thread = None
    app.state.real_player_bulk_publish_jobs = RealPlayerBulkPublishJobRegistry(
        session_factory=context.database.session_factory,
        settings=resolved_settings,
    )

    register_core(app)
    register_modules(app, modules)
    if resolved_settings.observability_tracing_enabled:
        from app.observability.tracing import configure_tracing

        configure_tracing(
            enabled=resolved_settings.observability_tracing_enabled,
            service_name=service_name,
            environment=resolved_settings.app_env,
            service_version=resolved_settings.app_version,
            exporter_endpoint=resolved_settings.observability_otlp_traces_endpoint,
            sample_ratio=resolved_settings.observability_trace_sample_ratio,
            app=app,
            engine=context.database.engine,
        )
    _configure_cors(app, resolved_settings)
    return app


def _resolve_database_engine(
    *,
    settings: Settings,
    engine: Engine | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> Engine:
    return resolve_database_engine(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
    )


def _bind_application_state(
    app: FastAPI,
    *,
    context: ApplicationContext,
    engine: Engine | None = None,
    modules: tuple[DomainModule, ...] = DOMAIN_MODULES,
) -> None:
    bind_application_state(app, context=context, modules=modules)
    if engine is not None:
        app.state.db_engine = engine


def get_asgi_app() -> FastAPI:
    global _ASGI_APP
    if _ASGI_APP is None:
        settings = get_settings()
        _ASGI_APP = create_app(
            settings=settings,
            run_migration_check=_default_asgi_run_migration_check(settings),
        )
    return _ASGI_APP


def register_core(app: FastAPI) -> None:
    from app.auth.dependencies import get_session as auth_get_session
    from app.core.database import get_read_session as core_get_read_session
    from app.core.database import get_session as core_get_session
    from app.core.health import router as health_router
    from app.core.rate_limit import RateLimitMiddleware
    from app.db import get_session as db_get_session
    from app.observability.middleware import ObservabilityMiddleware

    context: Container = app.state.container
    settings: Settings = app.state.settings

    _mount_tts_app(app)
    app.include_router(health_router)
    app.add_middleware(RateLimitMiddleware)
    if settings.observability_metrics_enabled:
        app.add_middleware(ObservabilityMiddleware, metrics=context.metrics)
    app.dependency_overrides[db_get_session] = context.database.get_session
    app.dependency_overrides[core_get_session] = context.database.get_session
    app.dependency_overrides[core_get_read_session] = context.database.get_read_session
    app.dependency_overrides[auth_get_session] = context.database.get_session

    @app.on_event("startup")
    async def startup() -> None:
        runtime_context: Container = app.state.container
        module_specs: tuple[DomainModule, ...] = tuple(getattr(app.state, "module_specs", ()))
        try:
            logger.info(
                "app.startup.begin run_migration_check=%s settings_run_migration_check=%s",
                app.state.run_migration_check,
                app.state.settings.run_migration_check,
            )
            runtime_context.initialize(run_migration_check=app.state.run_migration_check)
            bind_application_state(app, context=runtime_context, modules=module_specs)
            check_db(app)
            check_redis(app)
            runtime_context.metrics.refresh_from_database()
            _start_deferred_startup(app, context=runtime_context, modules=module_specs)
            logger.info("app.startup.complete")
        except Exception:
            logger.exception(
                "app.startup.failed run_migration_check=%s settings_run_migration_check=%s",
                app.state.run_migration_check,
                app.state.settings.run_migration_check,
            )
            raise

    @app.on_event("shutdown")
    async def shutdown() -> None:
        from app.realtime.websocket_gateway import shutdown_match_stream_websocket_gateway

        runtime_context: Container = app.state.container
        module_specs: tuple[DomainModule, ...] = tuple(getattr(app.state, "module_specs", ()))
        logger.info("app.shutdown.begin")
        startup_thread = getattr(app.state, "deferred_startup_thread", None)
        if startup_thread is not None and startup_thread.is_alive():
            startup_thread.join(timeout=1)
        publish_jobs = getattr(app.state, "real_player_bulk_publish_jobs", None)
        if publish_jobs is not None:
            publish_jobs.shutdown(timeout=1.0)
        await shutdown_match_stream_websocket_gateway(app)
        run_module_hooks(app, runtime_context, module_specs, phase="shutdown")
        runtime_context.shutdown()
        logger.info("app.shutdown.complete")


def check_db(app: FastAPI) -> None:
    logger.info("app.startup.health.database.begin")
    app.state.container.check_db(check_schema=True)
    logger.info("app.startup.health.database.complete")


def check_redis(app: FastAPI) -> None:
    logger.info("app.startup.health.redis.begin")
    app.state.container.check_redis()
    logger.info("app.startup.health.redis.complete")


def _default_asgi_run_migration_check(settings: Settings) -> bool:
    return settings.run_migration_check if settings.app_env.lower() != "production" else False


def _configure_cors(app: FastAPI, settings: Settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_origin_regex=settings.cors_allow_origin_regex,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=list(_CORS_EXPOSE_HEADERS),
    )


def _mount_tts_app(app: FastAPI) -> None:
    if getattr(app.state, "tts_mounted", False):
        return
    from importlib import import_module
    import sys

    from app.core.config import PROJECT_ROOT

    module = None
    try:
        module = import_module("services.tts.app")
    except ModuleNotFoundError:
        project_root = str(PROJECT_ROOT)
        if project_root not in sys.path:
            sys.path.append(project_root)
        try:
            module = import_module("services.tts.app")
        except ModuleNotFoundError:
            logger.warning("app.tts.mount.skipped reason=module_not_found")
            app.state.tts_mounted = False
            return

    app.mount("/tts", module.create_app())
    app.state.tts_mounted = True


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
        module_loader_lock = getattr(app.state, "module_loader_lock", None)
        if module_loader_lock is None:
            logger.info("app.startup.initial_admin.begin")
            _ensure_initial_admin(context.settings, context.database.session_factory)
            logger.info("app.startup.initial_admin.complete")
            logger.info("app.startup.module_hooks.begin")
            run_module_hooks(app, context, modules, phase="startup")
            logger.info("app.startup.module_hooks.complete")
        else:
            with module_loader_lock:
                logger.info("app.startup.initial_admin.begin")
                _ensure_initial_admin(context.settings, context.database.session_factory)
                logger.info("app.startup.initial_admin.complete")
                logger.info("app.startup.module_hooks.begin")
                run_module_hooks(app, context, modules, phase="startup")
                logger.info("app.startup.module_hooks.complete")
        logger.info("app.startup.bootstrap_complete")
    except Exception:
        logger.exception("app.startup.bootstrap_failed")


def _ensure_initial_admin(
    settings: Settings,
    session_factory: sessionmaker[Session],
) -> None:
    from app.auth.service import AuthService
    from app.models.user import UserRole

    if not settings.bootstrap_admin_enabled:
        logger.info("app.startup.initial_admin.skipped reason=disabled")
        return
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password or not settings.bootstrap_admin_username:
        logger.warning(
            "app.startup.initial_admin.skipped reason=incomplete_config enabled=%s",
            settings.bootstrap_admin_enabled,
        )
        return
    with session_factory() as session:
        service = AuthService()
        service.ensure_admin_user(
            session,
            email=settings.bootstrap_admin_email,
            password=settings.bootstrap_admin_password,
            username=settings.bootstrap_admin_username,
            display_name=(
                settings.bootstrap_admin_display_name
                or settings.bootstrap_admin_username
            ),
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()


def __getattr__(name: str) -> FastAPI:
    if name == "app":
        return get_asgi_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "INITIAL_ADMIN_DISPLAY_NAME",
    "INITIAL_ADMIN_EMAIL",
    "INITIAL_ADMIN_PASSWORD",
    "INITIAL_ADMIN_USERNAME",
    "app",
    "create_app",
    "get_asgi_app",
]
