"""Owner delegation. Execution reads the policy that is current, not the one that was current when the recommendation was made."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.club_legacy.models import ClubLegacyAuditEvent, ClubLegacyPolicy, ClubLegacyRecommendation
from app.models.base import utcnow
from app.models.club_profile import ClubProfile
from app.owner_console.ai import inbox_body
from app.owner_console.models import OwnerInboxItem

OPERATING_SPEND = "operating_spend"
MODES = ("owner_only", "approval_required", "automatic")
PRESETS: dict[str, dict[str, Any]] = {
    "owner_controlled": {"mode": "owner_only", "max_amount": None},
    "balanced": {"mode": "approval_required", "max_amount": Decimal("1000")},
    "executive_led": {"mode": "automatic", "max_amount": Decimal("5000")},
}


class LegacyError(ValueError):
    def __init__(self, code: str, status: int = 400, detail: str | None = None):
        self.code = code
        self.status = status
        self.detail = detail or code
        super().__init__(code)


def _money(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(Decimal(value).quantize(Decimal("0.01")))


def _audit(session: Session, *, club_id: str | None, actor_user_id: str | None, action: str, detail: dict) -> None:
    session.add(ClubLegacyAuditEvent(club_id=club_id, actor_user_id=actor_user_id, action=action, detail_json=detail))


def require_owner(session: Session, club_id: str, user_id: str) -> ClubProfile:
    profile = session.get(ClubProfile, club_id)
    if profile is None:
        raise LegacyError("club_not_found", 404)
    if profile.owner_user_id != user_id:
        raise LegacyError("not_club_owner", 403)
    return profile


def policy_for(session: Session, club_id: str, task_key: str = OPERATING_SPEND) -> ClubLegacyPolicy | None:
    return session.scalar(
        select(ClubLegacyPolicy).where(ClubLegacyPolicy.club_id == club_id, ClubLegacyPolicy.task_key == task_key)
    )


def policy_dict(policy: ClubLegacyPolicy) -> dict[str, Any]:
    return {
        "club_id": policy.club_id,
        "task_key": policy.task_key,
        "mode": policy.mode,
        "max_amount": _money(policy.max_amount),
    }


def apply_preset(session: Session, club_id: str, preset: str, *, actor_user_id: str) -> ClubLegacyPolicy:
    if preset not in PRESETS:
        raise LegacyError("unknown_preset")
    spec = PRESETS[preset]
    policy = set_task(
        session,
        club_id,
        OPERATING_SPEND,
        mode=spec["mode"],
        max_amount=spec["max_amount"],
        actor_user_id=actor_user_id,
    )
    _audit(
        session,
        club_id=club_id,
        actor_user_id=actor_user_id,
        action="preset_applied",
        detail={"preset": preset, "mode": policy.mode, "max_amount": _money(policy.max_amount)},
    )
    return policy


def set_task(
    session: Session,
    club_id: str,
    task_key: str,
    *,
    mode: str,
    max_amount: Decimal | None,
    actor_user_id: str,
) -> ClubLegacyPolicy:
    if mode not in MODES:
        raise LegacyError("unknown_mode")
    policy = policy_for(session, club_id, task_key)
    if policy is None:
        policy = ClubLegacyPolicy(club_id=club_id, task_key=task_key, mode=mode, max_amount=max_amount, scope_json={})
        session.add(policy)
    else:
        policy.mode = mode
        policy.max_amount = max_amount
        policy.updated_at = utcnow()
    session.flush()
    _audit(
        session,
        club_id=club_id,
        actor_user_id=actor_user_id,
        action="policy_set",
        detail={"task_key": task_key, "mode": mode, "max_amount": _money(max_amount)},
    )
    return policy


def recommend(
    session: Session,
    *,
    club_id: str,
    user_id: str,
    task_key: str,
    amount: Decimal,
) -> ClubLegacyRecommendation:
    gross = Decimal(amount).quantize(Decimal("0.01"))
    if gross <= 0:
        raise LegacyError("amount_must_be_positive")
    profile = require_owner(session, club_id, user_id)
    record = ClubLegacyRecommendation(
        club_id=club_id,
        user_id=user_id,
        task_key=task_key,
        amount=gross,
        status="recommended",
    )
    session.add(record)
    session.flush()
    policy = policy_for(session, club_id, task_key)
    if policy is not None and policy.mode == "approval_required":
        what = f"Approve {task_key.replace('_', ' ')} of {gross}."
        why = "This task is set to require the owner's approval before it runs."
        session.add(
            OwnerInboxItem(
                user_id=profile.owner_user_id,
                club_id=club_id,
                kind="legacy_approval",
                sender="Club Legacy",
                title=f"Approval needed: {task_key.replace('_', ' ')}",
                what=what,
                why=why,
                body=inbox_body("Club Legacy", what, why),
                actions_json=[
                    {"key": "approve", "label": "Approve", "style": "primary"},
                    {"key": "reject", "label": "Reject", "style": "ghost"},
                ],
                payload_json={"recommendation_id": record.id, "task_key": task_key, "amount": str(gross)},
                is_decision=True,
            )
        )
    _audit(
        session,
        club_id=club_id,
        actor_user_id=user_id,
        action="recommendation_created",
        detail={"recommendation_id": record.id, "task_key": task_key, "amount": str(gross)},
    )
    session.flush()
    return record


def execute(session: Session, *, recommendation_id: str, actor_user_id: str) -> ClubLegacyRecommendation:
    record = session.get(ClubLegacyRecommendation, recommendation_id)
    if record is None:
        raise LegacyError("recommendation_not_found", 404)
    require_owner(session, record.club_id, actor_user_id)
    if record.status != "recommended":
        raise LegacyError("recommendation_already_settled", 409)
    policy = policy_for(session, record.club_id, record.task_key)
    if policy is not None and policy.mode == "automatic" and policy.max_amount is not None:
        if record.amount > policy.max_amount:
            record.status = "blocked"
            record.outcome = (
                f"{record.task_key} of {record.amount} exceeds the current automatic limit of {policy.max_amount}."
            )
            _audit(
                session,
                club_id=record.club_id,
                actor_user_id=actor_user_id,
                action="execution_blocked",
                detail={"recommendation_id": record.id, "reason": "over_threshold", "outcome": record.outcome},
            )
            session.flush()
            return record
    if policy is not None and policy.mode == "owner_only":
        record.outcome = "Recorded as an owner action. Automatic staff execution is not allowed for this task."
    elif policy is None:
        record.outcome = "Recorded by the owner. This club has no delegation policy, so staff cannot run it."
    else:
        record.outcome = f"Executed under the current {policy.mode} policy."
    record.status = "executed"
    _audit(
        session,
        club_id=record.club_id,
        actor_user_id=actor_user_id,
        action="execution_completed",
        detail={"recommendation_id": record.id, "outcome": record.outcome, "mode": policy.mode if policy else None},
    )
    session.flush()
    return record
