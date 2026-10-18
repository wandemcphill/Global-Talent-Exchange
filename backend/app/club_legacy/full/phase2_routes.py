"""Phase 2 HTTP routes. Mounted under /owner/legacy/full/phase2."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_legacy.delegation import apply_preset, require_owner, set_task
from app.club_legacy.full.http import run_legacy
from app.club_legacy.full.phase2 import (
    academy_plan,
    execute_as_executive,
    executive_dict,
    gm_respond_preseason,
    hire_executive,
    pathway_recommendation,
)

router = APIRouter(prefix="/full/phase2", tags=["club-legacy"])


class HireBody(BaseModel):
    role: Literal["gm", "hoyd", "football_manager"]
    name: str = Field(min_length=2, max_length=120)
    personality: str = Field(min_length=2, max_length=40)
    wage: Decimal
    contract_months: int = 24
    authority: str | None = None


class AcademyBody(BaseModel):
    seed: int = 1


class PathwayBody(BaseModel):
    kind: Literal["promotion", "loan", "sale"]
    player_id: str
    amount: Decimal
    note: str = ""


class TaskBody(BaseModel):
    mode: Literal["owner_only", "approval_required", "automatic"]
    max_amount: Decimal | None = None


class PreseasonBody(BaseModel):
    decision: Literal["accept", "reject"]


def _recommendation(record) -> dict[str, Any]:
    return {
        "id": record.id,
        "task_key": record.task_key,
        "amount": str(record.amount),
        "status": record.status,
        "reason": record.reason,
        "confidence": record.confidence,
        "consequence": record.consequence,
        "outcome": record.outcome,
    }


@router.post("/{club_id}/executives")
def post_executive(
    club_id: str, body: HireBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        hired = hire_executive(
            session,
            club_id,
            user.id,
            role=body.role,
            name=body.name,
            personality=body.personality,
            wage=body.wage,
            contract_months=body.contract_months,
            authority=body.authority,
        )
        return executive_dict(hired)

    return run_legacy(session, go)


@router.post("/{club_id}/presets/{preset}")
def post_preset(
    club_id: str,
    preset: Literal["owner_controlled", "balanced", "executive_led"],
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        policy = apply_preset(session, club_id, preset, actor_user_id=user.id)
        amount = None if policy.max_amount is None else str(policy.max_amount)
        return {"task_key": policy.task_key, "mode": policy.mode, "max_amount": amount}

    return run_legacy(session, go)


@router.put("/{club_id}/tasks/{task_key}")
def put_task(
    club_id: str,
    task_key: str,
    body: TaskBody,
    user=Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    def go():
        require_owner(session, club_id, user.id)
        policy = set_task(session, club_id, task_key, mode=body.mode, max_amount=body.max_amount, actor_user_id=user.id)
        return {
            "task_key": policy.task_key,
            "mode": policy.mode,
            "max_amount": str(policy.max_amount) if policy.max_amount is not None else None,
        }

    return run_legacy(session, go)


@router.post("/{club_id}/academy")
def post_academy(
    club_id: str, body: AcademyBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        result = academy_plan(session, club_id, user.id, seed=body.seed)
        return {
            "summary": result["report"].summary,
            "reason": result["report"].reason,
            "confidence": result["report"].confidence,
            "consequence": result["report"].consequence,
            "prospect": result["prospect"],
            "recommendation": _recommendation(result["recommendation"]),
        }

    return run_legacy(session, go)


@router.post("/{club_id}/pathways")
def post_pathway(
    club_id: str, body: PathwayBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        record = pathway_recommendation(
            session,
            club_id,
            user.id,
            kind=body.kind,
            player_id=body.player_id,
            amount=body.amount,
            note=body.note,
        )
        return _recommendation(record)

    return run_legacy(session, go)


@router.post("/recommendations/{recommendation_id}/execute")
def post_execute(
    recommendation_id: str, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        record = execute_as_executive(session, recommendation_id=recommendation_id, actor_user_id=user.id)
        return _recommendation(record)

    return run_legacy(session, go)


@router.post("/preseason/{invite_id}/gm")
def post_gm_preseason(
    invite_id: str, body: PreseasonBody, user=Depends(get_current_user), session: Session = Depends(get_session)
) -> dict[str, Any]:
    def go():
        return gm_respond_preseason(session, invite_id=invite_id, user_id=user.id, decision=body.decision)

    return run_legacy(session, go)
