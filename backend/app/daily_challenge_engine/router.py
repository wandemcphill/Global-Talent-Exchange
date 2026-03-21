from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.daily_challenge_engine.schemas import (
    DailyChallengeClaimResponse,
    DailyChallengeClaimView,
    DailyChallengeListResponse,
    DailyChallengeMeResponse,
    DailyChallengeView,
)
from app.daily_challenge_engine.service import DailyChallengeError, DailyChallengeService
from app.models.daily_challenge import DailyChallenge
from app.models.user import User

router = APIRouter(prefix='/daily-challenges', tags=['daily-challenges'])


def _challenge_view(item) -> DailyChallengeView:
    return DailyChallengeView.model_validate(item, from_attributes=True)


def _claim_view(item) -> DailyChallengeClaimView:
    return DailyChallengeClaimView.model_validate(item, from_attributes=True)


@router.get('', response_model=DailyChallengeListResponse)
def list_daily_challenges(session: Session = Depends(get_session)) -> DailyChallengeListResponse:
    service = DailyChallengeService(session)
    return DailyChallengeListResponse(
        feature_enabled=service.feature_enabled(),
        challenges=[_challenge_view(item) for item in service.list_challenges()],
    )


@router.get('/me', response_model=DailyChallengeMeResponse)
def get_my_daily_challenges(user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> DailyChallengeMeResponse:
    service = DailyChallengeService(session)
    today = datetime.now(UTC).date()
    claims = service.claims_for_user_on(user=user, claim_day=today)
    claimed_keys = {item.metadata_json.get('challenge_key') for item in claims}
    available = [item.challenge_key for item in service.list_challenges() if item.challenge_key not in claimed_keys]
    return DailyChallengeMeResponse(
        feature_enabled=service.feature_enabled(),
        claims_today=[_claim_view(item) for item in claims],
        available_challenge_keys=available,
    )


@router.post('/{challenge_key}/claim', response_model=DailyChallengeClaimResponse)
def claim_daily_challenge(challenge_key: str, user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> DailyChallengeClaimResponse:
    service = DailyChallengeService(session)
    try:
        claim = service.claim(user=user, challenge_key=challenge_key)
        session.commit()
        session.refresh(claim)
        challenge = session.get(DailyChallenge, claim.challenge_id)
    except DailyChallengeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DailyChallengeClaimResponse(
        challenge=_challenge_view(challenge),
        claim=_claim_view(claim),
        reward_summary=f"Claimed {claim.reward_amount} {claim.reward_unit} from {challenge_key}.",
    )
