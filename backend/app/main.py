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
    if not _env_flag_enabled("GTE_ENABLE_PAYSTACK"):
        blocked_reasons.append("paystack_disabled")
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
