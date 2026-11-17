from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.core.request_security import extract_client_ip
from app.models.user import User
from app.services.first_deposit_referral_service import FirstDepositReferralError, FirstDepositReferralService

router = APIRouter()


class ReferralClickRequest(BaseModel):
    code: str = Field(min_length=4, max_length=32)


def _service(session: Session) -> FirstDepositReferralService:
    return FirstDepositReferralService(session)


def _http(exc: FirstDepositReferralError) -> HTTPException:
    status_code = status.HTTP_400_BAD_REQUEST
    if exc.code in {"referral_code_invalid"}:
        status_code = status.HTTP_404_NOT_FOUND
    elif exc.code in {
        "referral_code_inactive",
        "referral_code_expired",
        "referral_code_not_started",
        "referral_code_exhausted",
        "self_referral_blocked",
        "attribution_conflict",
        "attribution_locked",
        "programme_inactive",
    }:
        status_code = status.HTTP_409_CONFLICT
    elif exc.code == "referral_code_rate_limited":
        status_code = status.HTTP_429_TOO_MANY_REQUESTS
    return HTTPException(status_code=status_code, detail=exc.message)


@router.post("/clicks")
def record_referral_click(
    payload: ReferralClickRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    try:
        result = _service(session).record_click(
            payload.code,
            ip_address=extract_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
        session.commit()
        return result
    except FirstDepositReferralError as exc:
        session.rollback()
        raise _http(exc) from exc


@router.get("/codes/{code}/preview")
def preview_referral_code(
    code: str,
    request: Request,
    session: Session = Depends(get_session),
) -> dict:
    result = _service(session).preview_code(code, ip_address=extract_client_ip(request))
    session.commit()
    return result


@router.get("/me/affiliate")
def my_affiliate_dashboard(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = _service(session).my_affiliate(current_user)
    session.commit()
    return result
