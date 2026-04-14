from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.database import DatabaseRuntime

router = APIRouter(tags=["health"])


class ServiceCheck(BaseModel):
    status: Literal["ok", "error", "skipped"]
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, ServiceCheck]
    runtime_mode: Literal["normal", "degraded"]
    mode_reasons: list[str] = Field(default_factory=list)
    dependency_issues: dict[str, str] = Field(default_factory=dict)


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, ServiceCheck]
    runtime_mode: Literal["normal", "degraded"]
    mode_reasons: list[str] = Field(default_factory=list)
    dependency_issues: dict[str, str] = Field(default_factory=dict)


class VersionResponse(BaseModel):
    app_name: str
    environment: str
    api_version: str
    phase_marker: str


class DiagnosticsResponse(BaseModel):
    status: Literal["ok", "warning"]
    app_name: str
    environment: str
    phase_marker: str
    modules: list[str]
    route_count: int
    config_checks: dict[str, bool]
    dependency_checks: dict[str, ServiceCheck]
    runtime_mode: Literal["normal", "degraded"]
    mode_reasons: list[str] = Field(default_factory=list)
    config_issues: dict[str, str] = Field(default_factory=dict)
    dependency_issues: dict[str, str] = Field(default_factory=dict)
    dependency_notes: list[str]
    scaffolding_gaps: list[str]


class RootResponse(BaseModel):
    status: Literal["ok"]
    app_name: str
    docs_url: str
    health_url: str
    ready_url: str
    version_url: str


class SystemStatusService:
    def build_health(self, request: Request) -> HealthResponse:
        checks = self._build_dependency_checks(request)
        runtime_mode, mode_reasons = self._runtime_mode_from_checks(checks)
        has_errors = any(check.status == "error" for check in checks.values())
        return HealthResponse(
            status="degraded" if has_errors else "ok",
            checks=checks,
            runtime_mode=runtime_mode,
            mode_reasons=mode_reasons,
            dependency_issues=self._dependency_issues_from_checks(checks),
        )

    def build_readiness(self, request: Request, *, check_schema: bool = True) -> ReadinessResponse:
        database = request.app.state.context.database
        checks = self._build_dependency_checks(request)

        if checks["database"].status == "ok" and check_schema and os.getenv("SKIP_SCHEMA_CHECK") != "true":
            checks["schema"] = self._schema_check(database)

        runtime_mode, mode_reasons = self._runtime_mode_from_checks(checks)
        has_errors = any(check.status == "error" for check in checks.values())
        return ReadinessResponse(
            status="not_ready" if has_errors else "ready",
            checks=checks,
            runtime_mode=runtime_mode,
            mode_reasons=mode_reasons,
            dependency_issues=self._dependency_issues_from_checks(checks),
        )

    def build_version(self, settings: Settings) -> VersionResponse:
        return VersionResponse(
            app_name=settings.app_name,
            environment=settings.app_env,
            api_version=settings.app_version,
            phase_marker=settings.phase_marker,
        )

    def build_diagnostics(self, request: Request) -> DiagnosticsResponse:
        settings = getattr(request.app.state, "settings", get_settings())
        project_root = Path(settings.project_root)
        frontend_root = project_root / "frontend"
        backend_root = project_root / "backend"
        config_root = Path(settings.config_root)
        dependency_checks = self._build_dependency_checks(request)
        runtime_mode, mode_reasons = self._runtime_mode_from_checks(dependency_checks)
        config_check_messages = {
            "player_universe_weighting.toml": "Missing backend config file player_universe_weighting.toml.",
            "supply_tiers.toml": "Missing backend config file supply_tiers.toml.",
            "liquidity_bands.toml": "Missing backend config file liquidity_bands.toml.",
            "value_engine_weighting.toml": "Missing backend config file value_engine_weighting.toml.",
            "media_storage.toml": "Missing backend config file media_storage.toml.",
            "sponsorship_inventory.toml": "Missing backend config file sponsorship_inventory.toml.",
            "frontend_android_folder": "Frontend android/ scaffold is missing.",
            "frontend_android_wrapper_jar": "Frontend android Gradle wrapper JAR is missing.",
            "backend_requirements_txt": "Backend requirements.txt is missing.",
            "backend_env_example": "Backend .env.example is missing.",
        }
        checks = {
            "player_universe_weighting.toml": (config_root / "player_universe_weighting.toml").exists(),
            "supply_tiers.toml": (config_root / "supply_tiers.toml").exists(),
            "liquidity_bands.toml": (config_root / "liquidity_bands.toml").exists(),
            "value_engine_weighting.toml": (config_root / "value_engine_weighting.toml").exists(),
            "media_storage.toml": (config_root / "media_storage.toml").exists(),
            "sponsorship_inventory.toml": (config_root / "sponsorship_inventory.toml").exists(),
            "frontend_android_folder": (frontend_root / "android").exists(),
            "frontend_android_wrapper_jar": (frontend_root / "android/gradle/wrapper/gradle-wrapper.jar").exists(),
            "backend_requirements_txt": (backend_root / "requirements.txt").exists(),
            "backend_env_example": (backend_root / ".env.example").exists(),
        }
        config_issues = {name: config_check_messages[name] for name, is_present in checks.items() if not is_present}
        dependency_notes: list[str] = []
        if not checks["frontend_android_wrapper_jar"]:
            dependency_notes.append(
                "Flutter-managed Android wrapper JAR is missing. Run 'flutter create . --platforms=android' inside frontend/."
            )
        if not checks["backend_requirements_txt"]:
            dependency_notes.append(
                "Python dependency manifest is missing or incomplete. Local setup will be guesswork without it."
            )
        scaffolding_gaps: list[str] = []
        if not (backend_root / "app/main.py").exists():
            scaffolding_gaps.append("Backend entrypoint backend/app/main.py is missing.")
        if not (frontend_root / "pubspec.yaml").exists():
            scaffolding_gaps.append("Frontend pubspec.yaml is missing.")
        if not (frontend_root / "lib/main.dart").exists():
            scaffolding_gaps.append("Frontend lib/main.dart is missing.")
        has_dependency_errors = any(check.status == "error" for check in dependency_checks.values())
        status_value: Literal["ok", "warning"] = (
            "ok"
            if all(checks.values()) and not scaffolding_gaps and not has_dependency_errors and runtime_mode == "normal"
            else "warning"
        )
        return DiagnosticsResponse(
            status=status_value,
            app_name=settings.app_name,
            environment=settings.app_env,
            phase_marker=settings.phase_marker,
            modules=list(getattr(request.app.state, "domain_modules", [])),
            route_count=len(getattr(request.app.router, "routes", [])),
            config_checks=checks,
            dependency_checks=dependency_checks,
            runtime_mode=runtime_mode,
            mode_reasons=mode_reasons,
            config_issues=config_issues,
            dependency_issues=self._dependency_issues_from_checks(dependency_checks),
            dependency_notes=dependency_notes,
            scaffolding_gaps=scaffolding_gaps,
        )

    def _build_dependency_checks(self, request: Request) -> dict[str, ServiceCheck]:
        database = request.app.state.context.database
        return {
            "api": ServiceCheck(status="ok"),
            "database": self._database_check(database),
            "redis": self._redis_check(request),
            "kafka": self._kafka_check(request),
        }

    @staticmethod
    def _runtime_mode_from_checks(checks: dict[str, ServiceCheck]) -> tuple[Literal["normal", "degraded"], list[str]]:
        reasons = [
            check.detail
            for name, check in checks.items()
            if name != "api" and check.status != "ok" and check.detail is not None
        ]
        return ("degraded", reasons) if reasons else ("normal", [])

    @staticmethod
    def _dependency_issues_from_checks(checks: dict[str, ServiceCheck]) -> dict[str, str]:
        issues: dict[str, str] = {}
        for name, check in checks.items():
            if name == "api" or check.status == "ok":
                continue
            issues[name] = check.detail or f"{name} reported {check.status}."
        return issues

    @staticmethod
    def _database_check(database: DatabaseRuntime) -> ServiceCheck:
        try:
            is_ready = database.ping()
        except Exception as exc:
            return ServiceCheck(status="error", detail=str(exc))
        if not is_ready:
            return ServiceCheck(status="error", detail="Database connectivity check failed.")
        return ServiceCheck(status="ok")

    @staticmethod
    def _schema_check(database: DatabaseRuntime) -> ServiceCheck:
        try:
            database.check_schema_smoke()
        except Exception as exc:
            return ServiceCheck(status="error", detail=str(exc))
        return ServiceCheck(status="ok")

    @staticmethod
    def _redis_check(request: Request) -> ServiceCheck:
        settings = getattr(request.app.state, "settings", get_settings())
        if not settings.redis_url:
            return ServiceCheck(
                status="skipped",
                detail="Redis is not configured; distributed cache, rate limiting, and queue-backed fan-out are unavailable.",
            )
        cache_backend = getattr(request.app.state, "cache_backend", None)
        if cache_backend is None:
            return ServiceCheck(status="error", detail="Redis cache backend is unavailable.")
        try:
            if cache_backend.ping():
                return ServiceCheck(status="ok")
        except Exception as exc:
            return ServiceCheck(status="error", detail=str(exc))
        return ServiceCheck(status="error", detail="Redis connectivity check failed.")

    @staticmethod
    def _kafka_check(request: Request) -> ServiceCheck:
        settings = getattr(request.app.state, "settings", get_settings())
        if not settings.kafka_enabled:
            return ServiceCheck(
                status="skipped",
                detail="Kafka brokers are not configured; event streaming is running in local fallback mode.",
            )
        if settings.outbox_relay_enabled and getattr(request.app.state, "outbox_relay", None) is None:
            return ServiceCheck(
                status="error",
                detail="Kafka brokers are configured but the outbox relay is unavailable.",
            )
        return ServiceCheck(status="ok")


def get_system_status_service() -> SystemStatusService:
    return SystemStatusService()


@router.api_route("/", methods=["GET", "HEAD"], response_model=RootResponse, include_in_schema=False)
def read_root(request: Request) -> RootResponse:
    settings = getattr(request.app.state, "settings", get_settings())
    return RootResponse(
        status="ok",
        app_name=settings.app_name,
        docs_url="/docs",
        health_url="/health",
        ready_url="/ready",
        version_url="/version",
    )


@router.get("/health", response_model=HealthResponse)
def read_health(
    request: Request,
    response: Response,
    service: SystemStatusService = Depends(get_system_status_service),
) -> HealthResponse:
    health = service.build_health(request)
    if health.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return health


@router.get("/ready", response_model=ReadinessResponse)
def read_ready(
    request: Request,
    response: Response,
    service: SystemStatusService = Depends(get_system_status_service),
) -> ReadinessResponse:
    readiness = service.build_readiness(request, check_schema=True)
    if readiness.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return readiness


@router.get("/version", response_model=VersionResponse)
def read_version(
    request: Request,
    service: SystemStatusService = Depends(get_system_status_service),
) -> VersionResponse:
    return service.build_version(request.app.state.settings)


@router.get("/diagnostics", response_model=DiagnosticsResponse)
def read_diagnostics(
    request: Request,
    service: SystemStatusService = Depends(get_system_status_service),
) -> DiagnosticsResponse:
    return service.build_diagnostics(request)


@router.get("/metrics", include_in_schema=False)
def read_metrics(request: Request) -> Response:
    return request.app.state.metrics.metrics_response()
