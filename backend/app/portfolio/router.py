from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.dependencies import get_current_user, get_session
from backend.app.models.user import User
from backend.app.portfolio.schemas import PortfolioHoldingView, PortfolioSummaryView, PortfolioView
from backend.app.portfolio.service import PortfolioService
from backend.app.wallets.schemas import PortfolioSnapshotView
from backend.app.wallets.service import WalletService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioView)
def get_portfolio(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PortfolioView:
    snapshot = PortfolioService().build_for_user(session, current_user)
    return PortfolioView(holdings=[PortfolioHoldingView.model_validate(item) for item in snapshot.holdings])


@router.get("/snapshot", response_model=PortfolioSnapshotView)
def get_portfolio_snapshot(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PortfolioSnapshotView:
    snapshot = WalletService().build_portfolio_snapshot(session, current_user)
    return PortfolioSnapshotView(
        user_id=snapshot.user_id,
        currency=snapshot.currency,
        available_balance=snapshot.available_balance,
        reserved_balance=snapshot.reserved_balance,
        total_balance=snapshot.total_balance,
        holdings=snapshot.holdings,
    )


@router.get("/summary", response_model=PortfolioSummaryView)
def get_portfolio_summary(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> PortfolioSummaryView:
    summary = PortfolioService().build_summary(session, current_user)
    return PortfolioSummaryView.model_validate(summary)
