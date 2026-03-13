from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from backend.app.core.config import Settings, get_settings
from backend.app.core.database import DatabaseRuntime

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadinessCheck(BaseModel):
    status: Literal["ok", "error"]
    detail: str | None = None


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    checks: dict[str, ReadinessCheck]


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
    dependency_notes: list[str]
    scaffolding_gaps: list[str]


class SystemStatusService:
    def build_health(self) -> HealthResponse:
        return HealthResponse()

    def build_readiness(self, database: DatabaseRuntime) -> ReadinessResponse:
        try:
            is_ready = database.ping()
        except Exception as exc:
            return ReadinessResponse(
                status="not_ready",
                checks={"database": ReadinessCheck(status="error", detail=str(exc))},
            )

        if not is_ready:
            return ReadinessResponse(
                status="not_ready",
                checks={
                    "database": ReadinessCheck(
                        status="error",
                        detail="Database connectivity check failed.",
                    )
                },
            )

        return ReadinessResponse(
            status="ready",
            checks={"database": ReadinessCheck(status="ok")},
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
        checks = {
            "player_universe_weighting.toml": (config_root / "player_universe_weighting.toml").exists(),
            "supply_tiers.toml": (config_root / "supply_tiers.toml").exists(),
            "liquidity_bands.toml": (config_root / "liquidity_bands.toml").exists(),
            "value_engine_weighting.toml": (config_root / "value_engine_weighting.toml").exists(),
            "frontend_android_folder": (frontend_root / "android").exists(),
            "frontend_android_wrapper_jar": (frontend_root / "android/gradle/wrapper/gradle-wrapper.jar").exists(),
            "backend_requirements_txt": (backend_root / "requirements.txt").exists(),
            "backend_env_example": (backend_root / ".env.example").exists(),
        }
        dependency_notes: list[str] = []
        if not checks["frontend_android_wrapper_jar"]:
            dependency_notes.append("Flutter-managed Android wrapper JAR is missing. Run 'flutter create . --platforms=android' inside frontend/.")
        if not checks["backend_requirements_txt"]:
            dependency_notes.append("Python dependency manifest is missing or incomplete. Local setup will be guesswork without it.")
        scaffolding_gaps: list[str] = []
        if not (backend_root / "app/main.py").exists():
            scaffolding_gaps.append("Backend entrypoint backend/app/main.py is missing.")
        if not (frontend_root / "pubspec.yaml").exists():
            scaffolding_gaps.append("Frontend pubspec.yaml is missing.")
        if not (frontend_root / "lib/main.dart").exists():
            scaffolding_gaps.append("Frontend lib/main.dart is missing.")
        status_value: Literal["ok", "warning"] = "ok" if all(checks.values()) and not scaffolding_gaps else "warning"
        return DiagnosticsResponse(
            status=status_value,
            app_name=settings.app_name,
            environment=settings.app_env,
            phase_marker=settings.phase_marker,
            modules=list(getattr(request.app.state, "domain_modules", [])),
            route_count=len(getattr(request.app.router, "routes", [])),
            config_checks=checks,
            dependency_notes=dependency_notes,
            scaffolding_gaps=scaffolding_gaps,
        )


def get_system_status_service() -> SystemStatusService:
    return SystemStatusService()


@router.get("/health", response_model=HealthResponse)
def read_health(service: SystemStatusService = Depends(get_system_status_service)) -> HealthResponse:
    return service.build_health()


@router.get("/ready", response_model=ReadinessResponse)
def read_ready(
    request: Request,
    response: Response,
    service: SystemStatusService = Depends(get_system_status_service),
) -> ReadinessResponse:
    readiness = service.build_readiness(request.app.state.context.database)
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
