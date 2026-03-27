from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.club_finance.schemas import ClubFinanceTransactionView, ClubFinanceView, SponsorView
from app.club_finance.service import ClubFinanceService
from app.models.user import User

router = APIRouter(tags=["club-finance"])


@router.get("/finance", response_model=ClubFinanceView)
def get_finance(
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ClubFinanceView:
    service = ClubFinanceService(session)
    payload = service.get_finance_view(actor=actor)
    profile = payload["profile"]
    return ClubFinanceView(
        id=profile.id,
        user_id=profile.user_id,
        balance=profile.balance,
        weekly_wages=profile.weekly_wages,
        sponsorship_income=profile.sponsorship_income,
        match_income=profile.match_income,
        transfer_profit=profile.transfer_profit,
        expenses=profile.expenses,
        transfers_blocked=profile.transfers_blocked,
        forced_sale_required=profile.forced_sale_required,
        forced_sale_player_id=profile.forced_sale_player_id,
        last_weekly_cycle_on=profile.last_weekly_cycle_on,
        recent_transactions=[
            ClubFinanceTransactionView.model_validate(item, from_attributes=True)
            for item in payload["transactions"]
        ],
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


@router.get("/sponsors", response_model=list[SponsorView])
def get_sponsors(
    actor: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[SponsorView]:
    service = ClubFinanceService(session)
    payload = service.list_sponsors_for_user(actor=actor)
    return [
        SponsorView(
            id=item["sponsor"].id,
            name=item["sponsor"].name,
            tier=item["sponsor"].tier,
            payout=item["sponsor"].payout,
            requirements_json=item["sponsor"].requirements_json,
            active=item["sponsor"].active,
            requirements_met=item["requirements_met"],
            metrics_json=item["metrics_json"],
            created_at=item["sponsor"].created_at,
            updated_at=item["sponsor"].updated_at,
        )
        for item in payload
    ]


__all__ = ["router"]
