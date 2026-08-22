from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.agent_brain import AgentIdentity, AgentProfile, AgentStrategy
from app.agents.agent_manager import CreatorAgent
from app.agents.learning_engine import AgentLearningState
from app.agents.state_store import AgentStateStore
from app.models import AgentRecord, AgentStrategyRecord, Base


def test_missing_agent_wallet_rehydrates_zero_balance_and_ineligible_payout() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    with session_factory() as session:
        session.add(
            AgentRecord(
                agent_id="agent_1",
                handle="agent-1",
                display_name="Agent One",
                style="commentator",
                target="football",
            )
        )
        session.add(AgentStrategyRecord(agent_id="agent_1"))
        session.commit()

    store = AgentStateStore(session_factory=session_factory)
    snapshot = store.load_agent("agent_1")

    assert snapshot is not None
    assert snapshot.wallet.balance == 0.0
    assert snapshot.wallet.payout_eligible is False
