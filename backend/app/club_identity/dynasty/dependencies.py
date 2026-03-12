from __future__ import annotations

from fastapi import HTTPException, Request, status

from backend.app.club_identity.dynasty.repository import DatabaseDynastyReadRepository, DynastyReadRepository


def get_dynasty_repository(request: Request) -> DynastyReadRepository:
    repository = getattr(request.app.state, "dynasty_repository", None)
    if repository is None:
        session_factory = getattr(request.app.state, "session_factory", None)
        if session_factory is not None:
            repository = DatabaseDynastyReadRepository(session_factory=session_factory)
            request.app.state.dynasty_repository = repository
    if repository is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dynasty repository is not configured",
        )
    return repository
