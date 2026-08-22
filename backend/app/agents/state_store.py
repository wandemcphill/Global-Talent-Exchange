from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import inspect, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.agents.agent_brain import AgentIdentity, AgentProfile, AgentStrategy
from app.agents.agent_wallet import AgentWallet
from app.agents.learning_engine import AgentLearningState, AgentPerformanceSignal
from app.agents.models import (
    AgentLearningStateRecord,
    AgentPerformanceLogRecord,
    AgentRecord,
    AgentStrategyRecord,
    AgentWalletRecord,
)

if TYPE_CHECKING:
    from app.agents.agent_manager import CreatorAgent


@dataclass(frozen=True, slots=True)
class AgentStateSnapshot:
    profile: AgentProfile
    learning_state: AgentLearningState
    wallet: AgentWallet
    last_generated_clip_id: str | None
    last_generated_at: datetime | None


@dataclass(frozen=True, slots=True)
class AgentPerformanceLogEntry:
    agent_id: str
    clip_id: str
    primary_format: str
    variant_formats: tuple[str, ...]
    reward_total: float
    quality_score: float
    trust_score: float
    payout_eligible: bool
    payout_block_reason: str | None
    performance: AgentPerformanceSignal
    orchestrator_weight: float = 0.0
    global_exposure_feedback: float = 0.0
    winner_variant_score: float = 0.0
    metadata: dict[str, Any] | None = None
    notes: str | None = None


@dataclass(slots=True)
class AgentStateStore:
    session_factory: sessionmaker[Session]

    def list_agents(self) -> list[AgentStateSnapshot]:
        with self.session_factory() as session:
            if not self._is_ready(session):
                return []
            records = list(session.scalars(select(AgentRecord).order_by(AgentRecord.agent_id.asc())).all())
            return [self._snapshot_for(session, record.agent_id, record=record) for record in records]

    def load_agent(self, agent_id: str) -> AgentStateSnapshot | None:
        with self.session_factory() as session:
            if not self._is_ready(session):
                return None
            record = session.get(AgentRecord, agent_id)
            if record is None:
                return None
            return self._snapshot_for(session, agent_id, record=record)

    def save_agent(self, agent: CreatorAgent) -> None:
        with self.session_factory() as session:
            if not self._is_ready(session):
                return
            agent_id = agent.profile.identity.agent_id
            record = session.get(AgentRecord, agent_id)
            if record is None:
                record = AgentRecord(agent_id=agent_id)
                session.add(record)
            record.handle = agent.profile.identity.handle
            record.display_name = agent.profile.identity.display_name
            record.style = agent.profile.identity.style
            record.target = agent.profile.identity.target
            record.last_generated_clip_id = agent.last_generated_clip_id
            record.last_generated_at = agent.last_generated_at
            record.state_version = 1
            session.flush()

            strategy_record = session.get(AgentStrategyRecord, agent_id)
            if strategy_record is None:
                strategy_record = AgentStrategyRecord(agent_id=agent_id)
                session.add(strategy_record)
            strategy_record.risk_level = float(agent.profile.strategy.risk_level)
            strategy_record.avg_duration = int(agent.profile.strategy.avg_duration)
            strategy_record.tempo = str(agent.profile.strategy.tempo)
            strategy_record.audience_bias = str(agent.profile.strategy.audience_bias)
            strategy_record.preferred_formats_json = list(agent.profile.strategy.preferred_formats)
            strategy_record.event_focus_json = list(agent.profile.strategy.event_focus)
            strategy_record.cadence_minutes = int(agent.profile.strategy.cadence_minutes)
            strategy_record.experimental_share = float(agent.profile.strategy.experimental_share)
            strategy_record.global_exposure_feedback = float(agent.profile.strategy.global_exposure_feedback)
            strategy_record.shared_brain = str(agent.profile.strategy.shared_brain)

            learning_record = session.get(AgentLearningStateRecord, agent_id)
            if learning_record is None:
                learning_record = AgentLearningStateRecord(agent_id=agent_id)
                session.add(learning_record)
            learning_record.exploration_rate = float(agent.learning_state.exploration_rate)
            learning_record.last_reward = float(agent.learning_state.last_reward)
            learning_record.average_reward = float(agent.learning_state.average_reward)
            learning_record.win_streak = int(agent.learning_state.win_streak)
            learning_record.loss_streak = int(agent.learning_state.loss_streak)
            learning_record.total_posts = int(agent.learning_state.total_posts)
            learning_record.total_rewards = float(agent.learning_state.total_rewards)
            learning_record.total_penalties = float(agent.learning_state.total_penalties)
            learning_record.preferred_formats_json = dict(agent.learning_state.preferred_formats)
            learning_record.last_updated_at = agent.learning_state.last_updated_at

            wallet_record = session.get(AgentWalletRecord, agent_id)
            if wallet_record is None:
                wallet_record = AgentWalletRecord(agent_id=agent_id)
                session.add(wallet_record)
            wallet_record.balance = float(agent.wallet.balance)
            wallet_record.lifetime_earnings = float(agent.wallet.lifetime_earnings)
            wallet_record.boost_spend = float(agent.wallet.boost_spend)
            wallet_record.roi = float(agent.wallet.roi)
            wallet_record.last_spend = float(agent.wallet.last_spend)
            wallet_record.last_earnings = float(agent.wallet.last_earnings)
            wallet_record.trust_score = float(agent.wallet.trust_score)
            wallet_record.quality_score = float(agent.wallet.quality_score)
            wallet_record.repetition_ratio = float(agent.wallet.repetition_ratio)
            wallet_record.payout_eligible = bool(agent.wallet.payout_eligible)
            wallet_record.last_block_reason = agent.wallet.last_block_reason
            session.commit()

    def record_performance_log(self, entry: AgentPerformanceLogEntry) -> None:
        with self.session_factory() as session:
            if not self._is_ready(session):
                return
            session.add(
                AgentPerformanceLogRecord(
                    agent_id=entry.agent_id,
                    clip_id=entry.clip_id,
                    primary_format=entry.primary_format,
                    variant_formats_json=list(entry.variant_formats),
                    reward_total=float(entry.reward_total),
                    quality_score=float(entry.quality_score),
                    trust_score=float(entry.trust_score),
                    payout_eligible=bool(entry.payout_eligible),
                    payout_block_reason=entry.payout_block_reason,
                    view_count=int(entry.performance.view_count),
                    watch_time=float(entry.performance.watch_time),
                    shares=int(entry.performance.shares),
                    comments=int(entry.performance.comments),
                    completion_rate=float(entry.performance.completion_rate),
                    share_rate=float(entry.performance.share_rate),
                    comment_rate=float(entry.performance.comment_rate),
                    velocity=float(entry.performance.velocity),
                    impressions=int(entry.performance.impressions),
                    penalties=float(entry.performance.penalties),
                    earnings=float(entry.performance.earnings),
                    skip_rate=float(entry.performance.skip_rate),
                    orchestrator_weight=float(entry.orchestrator_weight),
                    global_exposure_feedback=float(entry.global_exposure_feedback),
                    winner_variant_score=float(entry.winner_variant_score),
                    notes=entry.notes,
                    metadata_json=dict(entry.metadata or {}),
                )
            )
            session.commit()

    def repetition_ratio(self, *, agent_id: str, primary_format: str, lookback: int = 5) -> float:
        with self.session_factory() as session:
            if not self._is_ready(session):
                return 0.0
            logs = list(
                session.scalars(
                    select(AgentPerformanceLogRecord)
                    .where(AgentPerformanceLogRecord.agent_id == agent_id)
                    .order_by(AgentPerformanceLogRecord.created_at.desc())
                    .limit(max(int(lookback), 1))
                ).all()
            )
            if not logs:
                return 0.0
            repeated = sum(1 for item in logs if item.primary_format == primary_format)
            return round(repeated / max(len(logs), 1), 4)

    def update_strategy_feedback(self, *, agent_id: str, global_exposure_feedback: float) -> None:
        with self.session_factory() as session:
            if not self._is_ready(session):
                return
            strategy_record = session.get(AgentStrategyRecord, agent_id)
            if strategy_record is None:
                return
            strategy_record.global_exposure_feedback = float(global_exposure_feedback)
            session.commit()

    def _snapshot_for(
        self, session: Session, agent_id: str, *, record: AgentRecord | None = None
    ) -> AgentStateSnapshot:
        agent_record = record or session.get(AgentRecord, agent_id)
        if agent_record is None:
            raise KeyError(f"Unknown agent {agent_id}")
        strategy_record = session.get(AgentStrategyRecord, agent_id)
        learning_record = session.get(AgentLearningStateRecord, agent_id)
        wallet_record = session.get(AgentWalletRecord, agent_id)
        return AgentStateSnapshot(
            profile=AgentProfile(
                identity=AgentIdentity(
                    agent_id=agent_record.agent_id,
                    handle=agent_record.handle,
                    display_name=agent_record.display_name,
                    style=agent_record.style,
                    target=agent_record.target,
                ),
                strategy=AgentStrategy(
                    risk_level=float(strategy_record.risk_level if strategy_record is not None else 0.5),
                    avg_duration=int(strategy_record.avg_duration if strategy_record is not None else 12),
                    tempo=str(strategy_record.tempo if strategy_record is not None else "medium"),
                    audience_bias=str(strategy_record.audience_bias if strategy_record is not None else "general"),
                    preferred_formats=tuple(
                        str(item) for item in (strategy_record.preferred_formats_json or [])
                    )
                    if strategy_record is not None
                    else (),
                    event_focus=tuple(str(item) for item in (strategy_record.event_focus_json or []))
                    if strategy_record is not None
                    else (),
                    cadence_minutes=int(strategy_record.cadence_minutes if strategy_record is not None else 8),
                    experimental_share=float(
                        strategy_record.experimental_share if strategy_record is not None else 0.3
                    ),
                    global_exposure_feedback=float(
                        strategy_record.global_exposure_feedback if strategy_record is not None else 0.0
                    ),
                    shared_brain=str(strategy_record.shared_brain if strategy_record is not None else "copilot"),
                ),
            ),
            learning_state=AgentLearningState(
                exploration_rate=float(learning_record.exploration_rate if learning_record is not None else 0.35),
                last_reward=float(learning_record.last_reward if learning_record is not None else 0.0),
                average_reward=float(learning_record.average_reward if learning_record is not None else 0.0),
                win_streak=int(learning_record.win_streak if learning_record is not None else 0),
                loss_streak=int(learning_record.loss_streak if learning_record is not None else 0),
                total_posts=int(learning_record.total_posts if learning_record is not None else 0),
                total_rewards=float(learning_record.total_rewards if learning_record is not None else 0.0),
                total_penalties=float(learning_record.total_penalties if learning_record is not None else 0.0),
                preferred_formats=dict(learning_record.preferred_formats_json or {})
                if learning_record is not None
                else {},
                last_updated_at=(
                    self._with_utc(learning_record.last_updated_at) or datetime.now(UTC)
                    if learning_record is not None
                    else datetime.now(UTC)
                ),
            ),
            wallet=AgentWallet(
                balance=float(wallet_record.balance if wallet_record is not None else 0.0),
                lifetime_earnings=float(wallet_record.lifetime_earnings if wallet_record is not None else 0.0),
                boost_spend=float(wallet_record.boost_spend if wallet_record is not None else 0.0),
                roi=float(wallet_record.roi if wallet_record is not None else 0.0),
                last_spend=float(wallet_record.last_spend if wallet_record is not None else 0.0),
                last_earnings=float(wallet_record.last_earnings if wallet_record is not None else 0.0),
                trust_score=float(wallet_record.trust_score if wallet_record is not None else 0.8),
                quality_score=float(wallet_record.quality_score if wallet_record is not None else 0.65),
                repetition_ratio=float(wallet_record.repetition_ratio if wallet_record is not None else 0.0),
                payout_eligible=bool(wallet_record.payout_eligible if wallet_record is not None else False),
                last_block_reason=wallet_record.last_block_reason if wallet_record is not None else None,
            ),
            last_generated_clip_id=agent_record.last_generated_clip_id,
            last_generated_at=self._with_utc(agent_record.last_generated_at),
        )

    @staticmethod
    def _is_ready(session: Session) -> bool:
        bind = session.get_bind()
        if bind is None:
            return False
        try:
            inspector = inspect(bind)
            return bool(
                inspector.has_table(AgentRecord.__tablename__)
                and inspector.has_table(AgentStrategyRecord.__tablename__)
                and inspector.has_table(AgentLearningStateRecord.__tablename__)
                and inspector.has_table(AgentWalletRecord.__tablename__)
                and inspector.has_table(AgentPerformanceLogRecord.__tablename__)
            )
        except SQLAlchemyError:
            return False
        except Exception:
            return False

    @staticmethod
    def _with_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def build_agent_state_store(*, session_factory: sessionmaker[Session] | None) -> AgentStateStore | None:
    if session_factory is None:
        return None
    return AgentStateStore(session_factory=session_factory)


__all__ = [
    "AgentPerformanceLogEntry",
    "AgentStateSnapshot",
    "AgentStateStore",
    "build_agent_state_store",
]
