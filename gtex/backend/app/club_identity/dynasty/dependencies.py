from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.db import get_session_factory
from app.club_identity.dynasty.repository import DatabaseDynastyReadRepository, DynastyReadRepository


def get_dynasty_repository(request: Request) -> DynastyReadRepository:
    repository = getattr(request.app.state, "dynasty_repository", None)
    if repository is not None:
        return repository

    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        try:
            session_factory = get_session_factory()
        except Exception:
            session_factory = None
    if session_factory is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Dynasty repository is not configured",
        )
    repository = DatabaseDynastyReadRepository(session_factory=session_factory)
    request.app.state.dynasty_repository = repository
    return repository
