from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.live_ops.schemas import LiveEventView, SeasonPassClaimRequest, SeasonPassClaimView, SeasonPassView, SeasonPassXpGrantView
from app.live_ops.service import LiveOpsError, LiveOpsService
from app.models.user import User

router = APIRouter(tags=["live-ops"])


@router.get("/season-pass", response_model=SeasonPassView)
def get_season_pass(
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SeasonPassView:
    service = LiveOpsService(session)
    payload = service.get_pass_view(actor=actor)
    season_pass = payload["season_pass"]
    return SeasonPassView(
        id=season_pass.id,
        user_id=season_pass.user_id,
        season_id=season_pass.season_id,
        tier=season_pass.tier,
        xp=season_pass.xp,
        level=season_pass.level,
        rewards_json=season_pass.rewards_json,
        claims=[SeasonPassClaimView.model_validate(item, from_attributes=True) for item in payload["claims"]],
        recent_xp_grants=[
            SeasonPassXpGrantView.model_validate(item, from_attributes=True)
            for item in payload["recent_xp_grants"]
        ],
        created_at=season_pass.created_at,
        updated_at=season_pass.updated_at,
    )


@router.post("/season-pass/claim", response_model=SeasonPassClaimView)
def claim_season_pass_reward(
    payload: SeasonPassClaimRequest,
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> SeasonPassClaimView:
    service = LiveOpsService(session)
    try:
        claim = service.claim_reward(actor=actor, level=payload.level, season_id=payload.season_id)
        session.commit()
        session.refresh(claim)
        return SeasonPassClaimView.model_validate(claim, from_attributes=True)
    except LiveOpsError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail) from exc


@router.get("/live-events", response_model=list[LiveEventView])
def list_live_events(
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[LiveEventView]:
    del actor
    service = LiveOpsService(session)
    return [LiveEventView.model_validate(item, from_attributes=True) for item in service.list_events()]


__all__ = ["router"]
