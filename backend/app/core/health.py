from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request, Response, status
from pydantic import BaseModel

from backend.app.core.config import Settings
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
