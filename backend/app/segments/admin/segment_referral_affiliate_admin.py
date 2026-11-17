from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.services.first_deposit_referral_service import FirstDepositReferralError, FirstDepositReferralService

router = APIRouter()


class PartnerCreateRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=160)
    campaign_name: str = Field(min_length=2, max_length=160)
    contact_email: str | None = Field(default=None, max_length=320)
    social_handle: str | None = Field(default=None, max_length=120)
    code: str | None = Field(default=None, max_length=16)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_registrations: int | None = Field(default=None, ge=1)
    notes: str | None = None
    contractual_terms: str | None = None
    owner_user_id: str | None = None
    creator_profile_id: str | None = None
    payout_destination_label: str | None = Field(default=None, max_length=255)
    payout_currency: str = Field(default="NGN", min_length=3, max_length=12)


class PartnerUpdateRequest(BaseModel):
    display_name: str | None = None
    contact_email: str | None = None
    social_handle: str | None = None
    notes: str | None = None
    contractual_terms: str | None = None
    payout_destination_label: str | None = None
    payout_currency: str | None = None
    owner_user_id: str | None = None
    reason: str | None = None


class StatusReasonRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=255)
    active: bool = True


class CommissionDecisionRequest(BaseModel):
    decision: str = Field(min_length=4, max_length=16)
    reason: str = Field(min_length=3, max_length=255)
    hold_days: int | None = Field(default=None, ge=1, le=90)


class PayoutBatchRequest(BaseModel):
    reward_ids: list[str] = Field(min_length=1)
    payout_method: str
    destination_label: str | None = None
    off_cycle_reason: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=128)


class PayoutConfirmRequest(BaseModel):
    external_reference: str | None = Field(default=None, max_length=128)


class ProgrammeSettingsRequest(BaseModel):
    user_bonus_bps: int | None = Field(default=None, ge=0, le=5000)
    referrer_commission_bps: int | None = Field(default=None, ge=0, le=5000)
    is_active: bool | None = None
    hold_days: int | None = Field(default=None, ge=0, le=90)
    payout_weekday: int | None = Field(default=None, ge=0, le=6)
    min_payout_thresholds: dict[str, str] | None = None
    eligible_account_types: list[str] | None = None
    qualifying_deposit_types: list[str] | None = None
    reason: str | None = None


def require_referral_admin(current_user: User = Depends(get_current_user)) -> User:
    role = getattr(current_user, "role", None)
    role_value = str(getattr(role, "value", role) or "")
    if role_value not in {"admin", "super_admin"} and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_access_required")
    return current_user


def _service(session: Session) -> FirstDepositReferralService:
    return FirstDepositReferralService(session)


def _http(exc: FirstDepositReferralError) -> HTTPException:
    not_found = {
        "partner_not_found",
        "reward_not_found",
        "campaign_not_found",
        "batch_not_found",
        "attribution_not_found",
        "owner_not_found",
        "creator_not_found",
    }
    conflict = {
        "hold_active",
        "reward_not_pending",
        "reward_not_approved",
        "reward_already_paid",
        "payout_beneficiary_mismatch",
        "payout_currency_mismatch",
        "below_payout_threshold",
        "duplicate_payout_confirmation",
        "payout_reference_conflict",
        "code_taken",
        "partner_suspended",
        "payout_not_scheduled",
        "threshold_not_configured",
    }
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code in not_found:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in conflict:
        status_code = status.HTTP_409_CONFLICT
    return HTTPException(status_code=status_code, detail=exc.message)


def _run(session: Session, action):
    try:
        result = action()
        session.commit()
        return result
    except FirstDepositReferralError as exc:
        session.rollback()
        raise _http(exc) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/affiliate/overview")
def affiliate_overview(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> dict:
    return _service(session).overview()


@router.get("/affiliate/settings")
def affiliate_settings(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> dict:
    result = _service(session).settings_view()
    session.commit()
    return result


@router.put("/affiliate/settings")
def update_affiliate_settings(
    payload: ProgrammeSettingsRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(session, lambda: _service(session).update_settings(actor, payload.model_dump(exclude_unset=True)))


@router.get("/affiliate/partners")
def affiliate_partners(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_partners()


@router.post("/affiliate/partners", status_code=status.HTTP_201_CREATED)
def create_affiliate_partner(
    payload: PartnerCreateRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(session, lambda: _service(session).create_partner(actor, payload.model_dump()))


@router.get("/affiliate/partners/{partner_id}")
def affiliate_partner_detail(
    partner_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(require_referral_admin),
) -> dict:
    return _run(session, lambda: _service(session).partner_detail(partner_id))


@router.patch("/affiliate/partners/{partner_id}")
def update_affiliate_partner(
    partner_id: str,
    payload: PartnerUpdateRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(
        session,
        lambda: _service(session).update_partner(actor, partner_id, payload.model_dump(exclude_unset=True)),
    )


@router.post("/affiliate/partners/{partner_id}/status")
def set_affiliate_partner_status(
    partner_id: str,
    payload: StatusReasonRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(
        session,
        lambda: _service(session).set_partner_status(actor, partner_id, active=payload.active, reason=payload.reason),
    )


@router.post("/affiliate/campaigns/{campaign_id}/status")
def set_affiliate_campaign_status(
    campaign_id: str,
    payload: StatusReasonRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(
        session,
        lambda: _service(session).set_campaign_status(actor, campaign_id, active=payload.active, reason=payload.reason),
    )


@router.get("/affiliate/links")
def affiliate_links(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_links()


@router.get("/affiliate/attributions")
def affiliate_attributions(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_attributions()


@router.get("/affiliate/attributions/{attribution_id}")
def affiliate_attribution_history(
    attribution_id: str,
    session: Session = Depends(get_session),
    _: User = Depends(require_referral_admin),
) -> dict:
    return _run(session, lambda: _service(session).attribution_history(attribution_id))


@router.get("/affiliate/conversions")
def affiliate_conversions(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_conversions()


@router.get("/affiliate/commissions")
def affiliate_commissions(
    status_filter: str | None = Query(default=None, alias="status"),
    session: Session = Depends(get_session),
    _: User = Depends(require_referral_admin),
) -> list:
    return _run(session, lambda: _service(session).list_commissions(status_filter))


@router.post("/affiliate/commissions/{reward_id}/decision")
def decide_affiliate_commission(
    reward_id: str,
    payload: CommissionDecisionRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(
        session,
        lambda: _service(session).decide_commission(
            actor,
            reward_id,
            decision=payload.decision,
            reason=payload.reason,
            hold_days=payload.hold_days,
        ),
    )


@router.get("/affiliate/payouts/preview")
def affiliate_payout_preview(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).payout_preview()


@router.get("/affiliate/payout-batches")
def affiliate_payout_batches(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_batches()


@router.post("/affiliate/payout-batches", status_code=status.HTTP_201_CREATED)
def create_affiliate_payout_batch(
    payload: PayoutBatchRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(
        session,
        lambda: _service(session).create_payout_batch(
            actor,
            reward_ids=payload.reward_ids,
            payout_method=payload.payout_method,
            destination_label=payload.destination_label,
            off_cycle_reason=payload.off_cycle_reason,
            idempotency_key=payload.idempotency_key,
        ),
    )


@router.post("/affiliate/payout-batches/{batch_id}/confirm")
def confirm_affiliate_payout_batch(
    batch_id: str,
    payload: PayoutConfirmRequest,
    session: Session = Depends(get_session),
    actor: User = Depends(require_referral_admin),
) -> dict:
    return _run(
        session,
        lambda: _service(session).confirm_payout_batch(
            actor, batch_id, external_reference=payload.external_reference
        ),
    )


@router.get("/affiliate/fraud")
def affiliate_fraud(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_fraud()


@router.get("/affiliate/analytics")
def affiliate_analytics(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> dict:
    return _service(session).analytics()


@router.get("/affiliate/audits")
def affiliate_audits(session: Session = Depends(get_session), _: User = Depends(require_referral_admin)) -> list:
    return _service(session).list_audits()


@router.get("/affiliate/reports/{kind}")
def affiliate_report(
    kind: str,
    session: Session = Depends(get_session),
    _: User = Depends(require_referral_admin),
) -> Response:
    try:
        body = _service(session).export_csv(kind)
    except FirstDepositReferralError as exc:
        raise _http(exc) from exc
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="gtex-referral-{kind}.csv"'},
    )
