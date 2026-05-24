from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from threading import Thread
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.api_contract import install_api_contracts
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
INITIAL_ADMIN_EMAIL = os.getenv("GTE_BOOTSTRAP_ADMIN_EMAIL") or ""
INITIAL_ADMIN_PASSWORD = os.getenv("GTE_BOOTSTRAP_ADMIN_PASSWORD") or ""
INITIAL_ADMIN_USERNAME = os.getenv("GTE_BOOTSTRAP_ADMIN_USERNAME") or ""
INITIAL_ADMIN_DISPLAY_NAME = os.getenv("GTE_BOOTSTRAP_ADMIN_DISPLAY_NAME") or ""
_STRICT_LIVE_FORBIDDEN_ENV_FLAGS = (
    "GTE_ENABLE_API_V1_DEMO_FIXTURES",
    "GTE_DEMO_SIMULATION_ENABLED",
    "GTE_DEMO_SIMULATION_BOOTSTRAP",
    "GTE_DEMO_SIMULATION_SEED_ON_BOOT",
    "GTE_ENABLE_LEGACY_MATCH_SIMULATION",
    "GTE_ENABLE_INFINITE_LEAGUE_LIVE_BRIDGE",
    "GTE_ENABLE_INFINITE_LEAGUE_DEMO_RUNTIME",
    "GTE_ENABLE_BROADCAST_GENERATED_PROGRAMS",
    "GTE_ENABLE_REGEN_FALLBACK_PROSPECTS",
    "GTE_ENABLE_SYNTHETIC_YOUTH_TOURNAMENT_SQUADS",
    "GTE_ENABLE_FULL_EXPERIENCE_SIMULATION",
    "GTE_ENABLE_WORLD_SUPER_CUP_DEMO",
    "GTE_ENABLE_MOCK_INGESTION_PROVIDER",
    "GTE_ENABLE_MOCK_KORAPAY",
    "GTE_ENABLE_PAYSTACK",
)


@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    await _startup_app(app)
    try:
        yield
    finally:
        await _shutdown_app(app)


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
    production_like = str(resolved_settings.app_env or "").strip().lower() in {"production", "prod", "staging"}
    _enforce_strict_live_startup_gate(resolved_settings, production_like=production_like)

    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        docs_url=None if production_like else "/docs",
        redoc_url=None if production_like else "/redoc",
        openapi_url=None if production_like else "/openapi.json",
        lifespan=_app_lifespan,
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
    app.state.deferred_startup_skipped = False
    app.state.startup_profile_records = []
    app.state.startup_hook_records = []
    app.state.real_player_bulk_publish_jobs = RealPlayerBulkPublishJobRegistry(
        session_factory=context.database.session_factory,
        settings=resolved_settings,
    )

    register_core(app)
    install_api_contracts(app)
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


def _env_flag_enabled(name: str) -> bool:
    return str(os.getenv(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _enforce_strict_live_startup_gate(settings: Settings, *, production_like: bool) -> None:
    if not production_like:
        return
    blocked_reasons: list[str] = []
    if settings.test_auth_fixture_mode:
        blocked_reasons.append("test_auth_fixture_mode")
    if settings.startup_profile != "production":
        blocked_reasons.append(f"startup_profile:{settings.startup_profile}")
    if str(settings.default_ingestion_provider or "").strip().lower() == "mock":
        blocked_reasons.append("mock_ingestion_provider")
    blocked_reasons.extend(name for name in _STRICT_LIVE_FORBIDDEN_ENV_FLAGS if _env_flag_enabled(name))
    if blocked_reasons:
        raise RuntimeError("GTEX strict-live startup gate blocked backend boot: " + ", ".join(sorted(blocked_reasons)))


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
    from app.auth.middleware import AuthEnforcementMiddleware
    from app.core.database import get_read_session as core_get_read_session
    from app.core.database import get_session as core_get_session
    from app.core.health import router as health_router
    from app.core.request_security import RequestHardeningMiddleware
    from app.core.rate_limit import RateLimitMiddleware
    from app.db import get_session as db_get_session
    from app.observability.middleware import ObservabilityMiddleware

    context: Container = app.state.container
    settings: Settings = app.state.settings

    _mount_tts_app(app)
    _mount_generated_media(app)
    app.include_router(health_router)
    app.add_middleware(AuthEnforcementMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestHardeningMiddleware)
    if settings.observability_metrics_enabled:
        app.add_middleware(ObservabilityMiddleware, metrics=context.metrics)
    app.dependency_overrides[db_get_session] = context.database.get_session
    app.dependency_overrides[core_get_session] = context.database.get_session
    app.dependency_overrides[core_get_read_session] = context.database.get_read_session
    app.dependency_overrides[auth_get_session] = context.database.get_session


def _mount_generated_media(app: FastAPI) -> None:
    media_root = os.environ.get("GTE_GENERATED_MEDIA_ROOT")
    directory = Path(media_root) if media_root else Path(__file__).resolve().parents[1] / "generated_media"
    app.mount("/generated-media", StaticFiles(directory=str(directory), check_dir=False), name="generated_media")


async def _startup_app(app: FastAPI) -> None:
    runtime_context: Container = app.state.container
    module_specs: tuple[DomainModule, ...] = tuple(getattr(app.state, "module_specs", ()))
    try:
        logger.info(
            "app.startup.begin run_migration_check=%s settings_run_migration_check=%s",
            app.state.run_migration_check,
            app.state.settings.run_migration_check,
        )
        _run_startup_step(
            app,
            "runtime.initialize",
            lambda: runtime_context.initialize(run_migration_check=app.state.run_migration_check),
        )
        _run_startup_step(
            app,
            "application_state.bind",
            lambda: bind_application_state(app, context=runtime_context, modules=module_specs),
        )
        if getattr(app.state, "realtime", None) is not None:
            app.state.realtime.bind_loop(asyncio.get_running_loop())
        _run_startup_step(app, "health.database", lambda: check_db(app))
        if _should_skip_redis_check(app.state.settings):
            _record_startup_step(app, "health.redis", 0.0, status="skipped")
            logger.info("app.startup.health.redis.skipped profile=%s", app.state.settings.startup_profile)
        else:
            _run_startup_step(app, "health.redis", lambda: check_redis(app))
        if _should_skip_background_start(app.state.settings):
            _record_startup_step(app, "outbox_relay.start", 0.0, status="skipped")
            logger.info("app.startup.outbox_relay.skipped profile=%s", app.state.settings.startup_profile)
        else:
            _run_startup_step(app, "outbox_relay.start", runtime_context.start_outbox_relay)
        if _should_skip_metrics_refresh(app.state.settings):
            _record_startup_step(app, "metrics.refresh", 0.0, status="skipped")
            logger.info("app.startup.metrics.refresh.skipped profile=%s", app.state.settings.startup_profile)
        else:
            _run_startup_step(app, "metrics.refresh", runtime_context.metrics.refresh_from_database)
        if not app.state.settings.deferred_startup_enabled or app.state.settings.fast_test_startup_enabled:
            app.state.deferred_startup_thread = None
            app.state.deferred_startup_skipped = True
            _record_startup_step(app, "deferred_startup.thread", 0.0, status="skipped")
            logger.info(
                "app.startup.deferred_startup.skipped enabled=%s profile=%s",
                app.state.settings.deferred_startup_enabled,
                app.state.settings.startup_profile,
            )
        else:
            _run_startup_step(
                app,
                "deferred_startup.thread",
                lambda: _start_deferred_startup(app, context=runtime_context, modules=module_specs),
            )
        logger.info("app.startup.complete")
    except Exception:
        logger.exception(
            "app.startup.failed run_migration_check=%s settings_run_migration_check=%s",
            app.state.run_migration_check,
            app.state.settings.run_migration_check,
        )
        raise


async def _shutdown_app(app: FastAPI) -> None:
    runtime_context: Container = app.state.container
    module_specs: tuple[DomainModule, ...] = tuple(getattr(app.state, "module_specs", ()))
    logger.info("app.shutdown.begin")
    startup_thread = getattr(app.state, "deferred_startup_thread", None)
    if startup_thread is not None and startup_thread.is_alive():
        startup_thread.join(timeout=1)
    publish_jobs = getattr(app.state, "real_player_bulk_publish_jobs", None)
    if publish_jobs is not None:
        publish_jobs.shutdown(timeout=1.0)
    realtime = getattr(app.state, "realtime", None)
    if realtime is not None:
        await realtime.shutdown()
    run_module_hooks(app, runtime_context, module_specs, phase="shutdown")
    runtime_context.shutdown()
    logger.info("app.shutdown.complete")


def _run_startup_step(app: FastAPI, name: str, action):
    started_at = perf_counter()
    status = "complete"
    try:
        return action()
    except Exception:
        status = "failed"
        raise
    finally:
        _record_startup_step(app, name, perf_counter() - started_at, status=status)


def _record_startup_step(
    app: FastAPI,
    name: str,
    duration_seconds: float,
    *,
    status: str,
) -> None:
    records = getattr(app.state, "startup_profile_records", None)
    if records is None:
        records = []
        app.state.startup_profile_records = records
    records.append(
        {
            "name": name,
            "duration_ms": round(duration_seconds * 1000, 3),
            "status": status,
        }
    )
    logger.info("app.startup.step.%s name=%s duration_ms=%.2f", status, name, duration_seconds * 1000)


def _should_skip_redis_check(settings: Settings) -> bool:
    return settings.fast_test_startup_enabled and not settings.redis_url


def _should_skip_background_start(settings: Settings) -> bool:
    return settings.fast_test_startup_enabled or not settings.outbox_relay_enabled


def _should_skip_metrics_refresh(settings: Settings) -> bool:
    return settings.fast_test_startup_enabled


def check_db(app: FastAPI) -> None:
    logger.info("app.startup.health.database.begin")
    should_run_schema_check = _should_run_schema_check()
    if not should_run_schema_check:
        logger.info("app.startup.health.database.schema_check.skipped env_var=SKIP_SCHEMA_CHECK")
    try:
        app.state.container.check_db(check_schema=should_run_schema_check)
    except RuntimeError as exc:
        if not should_run_schema_check or not _should_attempt_schema_repair(exc):
            raise
        logger.warning("app.startup.health.database.schema_repair.begin detail=%s", exc)
        app.state.container.database.initialize(run_migration_check=True)
        app.state.container.check_db(check_schema=True)
        logger.info("app.startup.health.database.schema_repair.complete")
    logger.info("app.startup.health.database.complete")


def check_redis(app: FastAPI) -> None:
    logger.info("app.startup.health.redis.begin")
    app.state.container.check_redis()
    logger.info("app.startup.health.redis.complete")


def _default_asgi_run_migration_check(settings: Settings) -> bool:
    return settings.run_migration_check


def _should_run_schema_check() -> bool:
    return os.getenv("SKIP_SCHEMA_CHECK") != "true"


def _should_attempt_schema_repair(exc: RuntimeError) -> bool:
    return str(exc).startswith("Database schema smoke check failed.")


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
    if (
        not settings.bootstrap_admin_email
        or not settings.bootstrap_admin_password
        or not settings.bootstrap_admin_username
    ):
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
            display_name=(settings.bootstrap_admin_display_name or settings.bootstrap_admin_username),
            role=UserRole.SUPER_ADMIN,
        )
        session.commit()


def __getattr__(name: str) -> FastAPI:
    if name == "app":
        return get_asgi_app()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


app: FastAPI


__all__ = [
    "INITIAL_ADMIN_DISPLAY_NAME",
    "INITIAL_ADMIN_EMAIL",
    "INITIAL_ADMIN_PASSWORD",
    "INITIAL_ADMIN_USERNAME",
    "app",
    "create_app",
    "get_asgi_app",
]
