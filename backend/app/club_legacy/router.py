from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy import delegation, ratings
from app.club_legacy.delegation import LegacyError
from app.club_legacy.flags import legacy_enabled
from app.owner_console.models import OwnerClubState

router = APIRouter(prefix="/owner/legacy", tags=["club-legacy"])


class PresetRequest(BaseModel):
    preset: Literal["owner_controlled", "balanced", "executive_led"]


class PolicyRequest(BaseModel):
    mode: Literal["owner_only", "approval_required", "automatic"]
    max_amount: Decimal | None = None


class RecommendationRequest(BaseModel):
    task_key: str = Field(default=delegation.OPERATING_SPEND, min_length=2, max_length=64)
    amount: Decimal


def _guard(session: Session) -> None:
    if not legacy_enabled(session):
        raise HTTPException(status_code=404, detail={"code": "club_legacy_disabled"})


def _run(session: Session, fn, *args, **kwargs):
    _guard(session)
    try:
        result = fn(*args, **kwargs)
        session.commit()
        return result
    except LegacyError as exc:
        session.rollback()
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "detail": exc.detail}) from exc


def _recommendation(record) -> dict[str, Any]:
    return {
        "id": record.id,
        "club_id": record.club_id,
        "task_key": record.task_key,
        "amount": str(record.amount),
        "status": record.status,
        "outcome": record.outcome,
        "reason": record.reason,
        "confidence": record.confidence,
        "consequence": record.consequence,
    }


@router.get("/{club_id}")
def read_legacy(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        delegation.require_owner(session, club_id, user.id)
        state = session.scalar(select(OwnerClubState).where(OwnerClubState.club_id == club_id))
        if state is None:
            raise LegacyError("club_not_activated", 404)
        return ratings.legacy_snapshot(session, state)

    return _run(session, go)


@router.post("/{club_id}/policies/preset")
def apply_preset(
    club_id: str, body: PresetRequest, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        delegation.require_owner(session, club_id, user.id)
        policy = delegation.apply_preset(session, club_id, body.preset, actor_user_id=user.id)
        return delegation.policy_dict(policy)

    return _run(session, go)


@router.put("/{club_id}/policies/{task_key}")
def set_policy(
    club_id: str,
    task_key: str,
    body: PolicyRequest,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    def go():
        delegation.require_owner(session, club_id, user.id)
        policy = delegation.set_task(
            session,
            club_id,
            task_key,
            mode=body.mode,
            max_amount=body.max_amount,
            actor_user_id=user.id,
        )
        return delegation.policy_dict(policy)

    return _run(session, go)


@router.post("/{club_id}/recommendations")
def create_recommendation(
    club_id: str,
    body: RecommendationRequest,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    def go():
        record = delegation.recommend(
            session,
            club_id=club_id,
            user_id=user.id,
            task_key=body.task_key,
            amount=body.amount,
        )
        return _recommendation(record)

    return _run(session, go)


@router.post("/recommendations/{recommendation_id}/execute")
def execute_recommendation(
    recommendation_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        record = delegation.execute(session, recommendation_id=recommendation_id, actor_user_id=user.id)
        return _recommendation(record)

    return _run(session, go)


@router.get("/{club_id}/desk")
def read_desk(club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)) -> dict[str, Any]:
    def go():
        from app.club_legacy.operations import desk_snapshot

        return desk_snapshot(session, club_id, user.id)

    return _run(session, go)


class DeskActionRequest(BaseModel):
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)


@router.post("/{club_id}/desk")
def post_desk_action(
    club_id: str, body: DeskActionRequest, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        from app.club_legacy.operations import perform_desk_action

        return perform_desk_action(session, club_id, user.id, body.action, body.payload)

    return _run(session, go)


@router.get("/{club_id}/showroom")
def read_showroom(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        delegation.require_owner(session, club_id, user.id)
        from app.club_legacy.operations import showroom

        return showroom(session, club_id)

    return _run(session, go)


@router.get("/{club_id}/page")
def read_club_page(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        delegation.require_owner(session, club_id, user.id)
        from app.club_legacy.operations import club_page

        return club_page(session, club_id)

    return _run(session, go)


@router.get("/{club_id}/metrics")
def read_metrics(
    club_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    del club_id, user

    def go():
        from app.club_legacy.operations import metrics

        return metrics(session)

    return _run(session, go)


def _include_full_phase_routers() -> None:
    from app.club_legacy.full.phase1_routes import router as phase1_router
    from app.club_legacy.full.phase2_routes import router as phase2_router
    from app.club_legacy.full.phase3_routes import router as phase3_router
    from app.club_legacy.full.phase4_routes import router as phase4_router
    from app.club_legacy.full.phase5_routes import router as phase5_router
    from app.club_legacy.full.phase6_routes import router as phase6_router

    router.include_router(phase1_router)
    router.include_router(phase2_router)
    router.include_router(phase3_router)
    router.include_router(phase4_router)
    router.include_router(phase5_router)
    router.include_router(phase6_router)


_include_full_phase_routers()
