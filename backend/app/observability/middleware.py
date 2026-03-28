from __future__ import annotations

from time import perf_counter
import logging
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

if TYPE_CHECKING:
    from app.observability.metrics import GTexMetrics

logger = logging.getLogger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, metrics: GTexMetrics) -> None:
        super().__init__(app)
        self.metrics = metrics

    async def dispatch(self, request: Request, call_next):
        started_at = perf_counter()
        route = self._route_label(request)
        should_record = route not in {"/health", "/ready", "/metrics"}
        if should_record:
            self.metrics.http_requests_in_progress.inc()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = perf_counter() - started_at
            if should_record:
                self.metrics.record_http_request(
                    method=request.method,
                    route=route,
                    status_code=500,
                    duration_seconds=elapsed,
                )
                logger.exception(
                    "http.request.failed",
                    extra={
                        "method": request.method,
                        "route": route,
                        "status_code": 500,
                        "duration_ms": round(elapsed * 1000, 2),
                    },
                )
            raise
        finally:
            if should_record:
                self.metrics.http_requests_in_progress.dec()

        elapsed = perf_counter() - started_at
        if should_record:
            route = self._route_label(request)
            self.metrics.record_http_request(
                method=request.method,
                route=route,
                status_code=response.status_code,
                duration_seconds=elapsed,
            )
            logger.info(
                "http.request.completed",
                extra={
                    "method": request.method,
                    "route": route,
                    "status_code": response.status_code,
                    "duration_ms": round(elapsed * 1000, 2),
                },
            )
        return response

    @staticmethod
    def _route_label(request: Request) -> str:
        route = request.scope.get("route")
        path = getattr(route, "path", None)
        if path:
            return str(path)
        return request.url.path
