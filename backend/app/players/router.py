from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.players.schemas import PlayerSummaryView
from app.players.service import PlayerSummaryQueryService

router = APIRouter(prefix="/players", tags=["players"])


@router.get("/summaries/recent", response_model=list[PlayerSummaryView])
def list_recent_player_summaries(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[PlayerSummaryView]:
    service = PlayerSummaryQueryService(session)
    return [PlayerSummaryView.model_validate(item) for item in service.list_recent(limit)]


@router.get("/{player_id}/summary", response_model=PlayerSummaryView)
def get_player_summary(
    player_id: str,
    session: Session = Depends(get_session),
) -> PlayerSummaryView:
    summary = PlayerSummaryQueryService(session).get_summary(player_id)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Player summary for {player_id} was not found")
    return PlayerSummaryView.model_validate(summary)
