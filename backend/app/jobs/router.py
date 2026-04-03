from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import get_current_user
from app.core.task_queue import NullTaskQueueBackend, get_task_queue_backend
from app.jobs.schemas import BackgroundTaskView
from app.models.user import User, UserRole

router = APIRouter(tags=["jobs"])


@router.get("/jobs/{job_id}", response_model=BackgroundTaskView)
def get_background_job(
    job_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> BackgroundTaskView:
    backend = get_task_queue_backend(request.app)
    if isinstance(backend, NullTaskQueueBackend):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Background jobs are unavailable.")
    execution = backend.get(job_id)
    if execution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Background job was not found.")
    if execution.owner_user_id and execution.owner_user_id != current_user.id and current_user.role not in {
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot access this background job.")
    return BackgroundTaskView(
        job_id=execution.job_id,
        name=execution.name,
        status=execution.status,
        queued_at=execution.queued_at,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        error=execution.error,
        result=execution.result if isinstance(execution.result, dict) else None,
    )


__all__ = ["router"]
