from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.user import User
from app.wallets.service import WalletService


@dataclass(slots=True)
class PortfolioBalance:
    account_id: str
    code: str
    unit: str
    balance: object


@dataclass(slots=True)
class PortfolioSnapshot:
    user_id: str
    balances: list[PortfolioBalance]
    positions: list[dict]


@dataclass(slots=True)
class PortfolioService:
    wallet_service: WalletService = field(default_factory=WalletService)

    def build_for_user(self, session: Session, user: User) -> PortfolioSnapshot:
        balances = [
            PortfolioBalance(
                account_id=account.id,
                code=account.code,
                unit=account.unit.value,
                balance=self.wallet_service.get_balance(session, account),
            )
            for account in self.wallet_service.list_accounts_for_user(session, user)
        ]
        return PortfolioSnapshot(user_id=user.id, balances=balances, positions=[])
