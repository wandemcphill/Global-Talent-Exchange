from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_session
from app.models.user import User
from app.portfolios.schemas import PortfolioView
from app.portfolios.service import PortfolioService

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get("/me", response_model=PortfolioView)
def get_my_portfolio(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PortfolioView:
    snapshot = PortfolioService().build_for_user(session, current_user)
    return PortfolioView.model_validate(snapshot)
