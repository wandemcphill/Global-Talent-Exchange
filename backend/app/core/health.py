from __future__ import annotations

from fastapi import APIRouter, Request

from backend.app.core.cache import NullCacheBackend

router = APIRouter(tags=["health"])


@router.get("/health")
def read_health(request: Request) -> dict[str, object]:
    context = request.app.state.context
    cache_backend = context.cache_backend
    cache_status = "disabled"
    if not isinstance(cache_backend, NullCacheBackend):
        cache_status = "ok" if cache_backend.ping() else "degraded"

    database_status = "ok" if context.database.ping() else "degraded"
    jobs_status = "ok"
    events_status = "ok"
    overall_status = "ok" if database_status == "ok" else "degraded"

    return {
        "status": overall_status,
        "components": {
            "database": {"status": database_status},
            "cache": {"status": cache_status},
            "jobs": {
                "status": jobs_status,
                "recent_runs": len(context.job_backend.list_recent()),
            },
            "events": {
                "status": events_status,
                "published_events": len(context.event_publisher.published_events),
                "subscribers": context.event_publisher.subscriber_count,
            },
        },
    }
