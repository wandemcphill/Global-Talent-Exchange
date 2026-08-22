from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.agents.ledger_service import AgentLedgerService
from app.models.wallet import LedgerAccount, LedgerAccountKind, LedgerUnit
from app.wallets.service import LedgerError, WalletService


def make_session() -> Session:
    from app.models.base import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_agent_account_is_system_owned_and_zero_balance_on_creation() -> None:
    with make_session() as session:
        service = AgentLedgerService(WalletService())
        account = service.get_or_create_account(session, agent_id="agent-1", unit=LedgerUnit.COIN)

        assert account.code == "agent:agent-1:coin"
        assert account.owner_user_id is None
        assert account.kind is LedgerAccountKind.SYSTEM
        assert service.balance(session, agent_id="agent-1") == Decimal("0.0000")


def test_agent_account_identity_cannot_be_reused_with_wrong_kind() -> None:
    with make_session() as session:
        session.add(
            LedgerAccount(
                code="agent:agent-1:coin",
                label="wrong",
                unit=LedgerUnit.COIN,
                kind=LedgerAccountKind.USER,
            )
        )
        session.commit()

        with pytest.raises(LedgerError, match="invalid identity"):
            AgentLedgerService(WalletService()).get_or_create_account(
                session,
                agent_id="agent-1",
                unit=LedgerUnit.COIN,
            )
