from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from typing import Any, Sequence

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.auth.security import hash_password
from backend.app.auth.service import AuthService
from backend.app.core.config import DEFAULT_DATABASE_URL, Settings, load_settings
from backend.app.core.database import create_database_engine, create_session_factory, ensure_database_schema_current
from backend.app.core.events import EventPublisher, InMemoryEventPublisher
from backend.app.ingestion.models import MarketSignal, Player
from backend.app.market.service import MarketEngine
from backend.app.models.user import User, UserRole
from backend.app.models.wallet import (
    LedgerAccount,
    LedgerEntryReason,
    LedgerUnit,
    PaymentEvent,
    PaymentProvider,
    PaymentStatus,
)
from backend.app.players.read_models import PlayerSummaryReadModel
from backend.app.players.service import PlayerSummaryProjector
from backend.app.simulation.service import (
    DEFAULT_ILLIQUID_PLAYER_COUNT,
    DEFAULT_LIQUID_PLAYER_COUNT,
    DemoMarketSimulationService,
)
from backend.app.value_engine.read_models import PlayerValueSnapshotRecord
from backend.app.value_engine.service import IngestionValueEngineBridge
from backend.app.wallets.service import LedgerPosting, WalletService

from .player_universe_seeder import VerifiedPlayerUniverseSeeder

DEFAULT_DEMO_PLAYER_COUNT = 24
DEFAULT_DEMO_PROVIDER_NAME = "demo-universe"
DEFAULT_DEMO_SIGNAL_PROVIDER = "demo-market-signals"
DEFAULT_DEMO_PASSWORD = "DemoPass123"
DEFAULT_DEMO_RANDOM_SEED = 20260311
DEFAULT_DEMO_BATCH_SIZE = 500
DEFAULT_FEATURED_PLAYER_LIMIT = 5
DEFAULT_PREVIOUS_SNAPSHOT_AT = datetime(2026, 3, 10, 12, 0, tzinfo=timezone.utc)
DEFAULT_CURRENT_SNAPSHOT_AT = datetime(2026, 3, 11, 12, 0, tzinfo=timezone.utc)


@dataclass(frozen=True, slots=True)
class DemoUserSpec:
    email: str
    username: str
    display_name: str
    role: UserRole
    provider: PaymentProvider
    coin_balance: Decimal
    credit_balance: Decimal


@dataclass(frozen=True, slots=True)
class DemoUserSummary:
    user_id: str
    email: str
    username: str
    display_name: str
    role: str
    password: str
    coin_balance: Decimal
    credit_balance: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role,
            "password": self.password,
            "coin_balance": self.coin_balance,
            "credit_balance": self.credit_balance,
        }


@dataclass(frozen=True, slots=True)
class FeaturedPlayerSummary:
    player_id: str
    player_name: str
    current_club_name: str | None
    current_competition_name: str | None
    current_value_credits: float
    movement_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "current_club_name": self.current_club_name,
            "current_competition_name": self.current_competition_name,
            "current_value_credits": self.current_value_credits,
            "movement_pct": self.movement_pct,
        }


@dataclass(frozen=True, slots=True)
class DemoHoldingSummary:
    owner_username: str
    owner_email: str
    player_id: str
    player_name: str
    acquisition_credits: float
    quantity: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_username": self.owner_username,
            "owner_email": self.owner_email,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "acquisition_credits": self.acquisition_credits,
            "quantity": self.quantity,
        }


@dataclass(frozen=True, slots=True)
class DemoBootstrapSummary:
    provider_name: str
    signal_provider: str
    player_target_count: int
    random_seed: int
    previous_snapshot_at: datetime
    current_snapshot_at: datetime
    universe_seed: dict[str, Any]
    players_seeded: int
    market_signals_seeded: int
    value_snapshots_seeded: int
    player_summaries_seeded: int
    holdings_seeded: int
    demo_users: tuple[DemoUserSummary, ...]
    featured_players: tuple[FeaturedPlayerSummary, ...]
    sample_holdings: tuple[DemoHoldingSummary, ...]
    liquidity_seed: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "signal_provider": self.signal_provider,
            "player_target_count": self.player_target_count,
            "random_seed": self.random_seed,
            "previous_snapshot_at": self.previous_snapshot_at,
            "current_snapshot_at": self.current_snapshot_at,
            "universe_seed": self.universe_seed,
            "players_seeded": self.players_seeded,
            "market_signals_seeded": self.market_signals_seeded,
            "value_snapshots_seeded": self.value_snapshots_seeded,
            "player_summaries_seeded": self.player_summaries_seeded,
            "holdings_seeded": self.holdings_seeded,
            "demo_users": [user.to_dict() for user in self.demo_users],
            "featured_players": [player.to_dict() for player in self.featured_players],
            "sample_holdings": [holding.to_dict() for holding in self.sample_holdings],
            "liquidity_seed": self.liquidity_seed,
        }


DEMO_USER_SPECS: tuple[DemoUserSpec, ...] = (
    DemoUserSpec(
        email="fan@demo.gte.local",
        username="demo_fan",
        display_name="Demo Fan",
        role=UserRole.USER,
        provider=PaymentProvider.MONNIFY,
        coin_balance=Decimal("150.0000"),
        credit_balance=Decimal("1200.0000"),
    ),
    DemoUserSpec(
        email="scout@demo.gte.local",
        username="demo_scout",
        display_name="Demo Scout",
        role=UserRole.USER,
        provider=PaymentProvider.FLUTTERWAVE,
        coin_balance=Decimal("90.0000"),
        credit_balance=Decimal("850.0000"),
    ),
    DemoUserSpec(
        email="admin@demo.gte.local",
        username="demo_admin",
        display_name="Demo Admin",
        role=UserRole.ADMIN,
        provider=PaymentProvider.PAYSTACK,
        coin_balance=Decimal("500.0000"),
        credit_balance=Decimal("5000.0000"),
    ),
)


@dataclass(slots=True)
class DemoBootstrapService:
    session_factory: sessionmaker[Session]
    settings: Settings | None = None
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)

    def seed(
        self,
        *,
        player_target_count: int = DEFAULT_DEMO_PLAYER_COUNT,
        provider_name: str = DEFAULT_DEMO_PROVIDER_NAME,
        signal_provider: str = DEFAULT_DEMO_SIGNAL_PROVIDER,
        demo_password: str = DEFAULT_DEMO_PASSWORD,
        random_seed: int = DEFAULT_DEMO_RANDOM_SEED,
        batch_size: int = DEFAULT_DEMO_BATCH_SIZE,
        previous_snapshot_at: datetime = DEFAULT_PREVIOUS_SNAPSHOT_AT,
        current_snapshot_at: datetime = DEFAULT_CURRENT_SNAPSHOT_AT,
        featured_player_limit: int = DEFAULT_FEATURED_PLAYER_LIMIT,
        with_liquidity: bool = False,
        liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
        illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
        market_engine: MarketEngine | None = None,
    ) -> DemoBootstrapSummary:
        if player_target_count <= 0:
            raise ValueError("player_target_count must be greater than zero.")
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero.")
        if previous_snapshot_at >= current_snapshot_at:
            raise ValueError("previous_snapshot_at must be earlier than current_snapshot_at.")

        resolved_settings = self.settings or load_settings()
        wallet_service = WalletService(event_publisher=self.event_publisher)
        auth_service = AuthService(wallet_service=wallet_service)

        with self.session_factory() as session:
            self._ensure_demo_users(session, auth_service=auth_service, wallet_service=wallet_service, demo_password=demo_password)
            self._reset_demo_holdings(session, wallet_service=wallet_service)
            self._purge_demo_read_models(session, provider_name=provider_name)
            universe_summary = VerifiedPlayerUniverseSeeder(session, settings=resolved_settings).seed(
                target_player_count=player_target_count,
                provider_name=provider_name,
                random_seed=random_seed,
                replace_provider_data=True,
                batch_size=batch_size,
            )
            player_ids = self._list_demo_player_ids(session, provider_name=provider_name)
            market_signals_seeded = self._seed_market_signals(
                session,
                player_ids=player_ids,
                signal_provider=signal_provider,
                previous_snapshot_at=previous_snapshot_at,
                current_snapshot_at=current_snapshot_at,
            )
            session.commit()

        value_bridge = IngestionValueEngineBridge(
            session_factory=self.session_factory,
            event_publisher=self.event_publisher,
            summary_projector=PlayerSummaryProjector(),
            settings=resolved_settings,
            default_lookback_days=resolved_settings.value_snapshot_lookback_days,
        )
        previous_snapshots = value_bridge.run(as_of=previous_snapshot_at, player_ids=player_ids)
        current_snapshots = value_bridge.run(as_of=current_snapshot_at, player_ids=player_ids)

        with self.session_factory() as session:
            self._ensure_frontend_market_states(
                session,
                player_ids=player_ids,
                current_snapshot_at=current_snapshot_at,
            )
            featured_players = self._load_featured_players(
                session,
                player_ids=player_ids,
                limit=featured_player_limit,
            )
            sample_holdings = self._seed_demo_holdings(
                session,
                wallet_service=wallet_service,
                featured_players=featured_players,
            )
            self._ensure_demo_users(session, auth_service=auth_service, wallet_service=wallet_service, demo_password=demo_password)
            demo_users = self._load_demo_user_summaries(
                session,
                wallet_service=wallet_service,
                demo_password=demo_password,
            )
            player_summaries_seeded = self._count_player_summaries(session, player_ids=player_ids)
            session.commit()

        liquidity_seed: dict[str, Any] | None = None
        if with_liquidity:
            liquidity_service = DemoMarketSimulationService(
                session_factory=self.session_factory,
                event_publisher=self.event_publisher,
            )
            liquidity_seed = liquidity_service.seed_demo_liquidity(
                random_seed=random_seed,
                liquid_player_count=liquid_player_count,
                illiquid_player_count=illiquid_player_count,
                demo_password=demo_password,
            ).to_dict()
            if market_engine is not None:
                liquidity_seed = liquidity_service.replay_market_state(market_engine).to_dict()

        return DemoBootstrapSummary(
            provider_name=provider_name,
            signal_provider=signal_provider,
            player_target_count=player_target_count,
            random_seed=random_seed,
            previous_snapshot_at=previous_snapshot_at,
            current_snapshot_at=current_snapshot_at,
            universe_seed=universe_summary.to_dict(),
            players_seeded=len(player_ids),
            market_signals_seeded=market_signals_seeded,
            value_snapshots_seeded=len(previous_snapshots) + len(current_snapshots),
            player_summaries_seeded=player_summaries_seeded,
            holdings_seeded=len(sample_holdings),
            demo_users=demo_users,
            featured_players=featured_players,
            sample_holdings=sample_holdings,
            liquidity_seed=liquidity_seed,
        )

    def _ensure_demo_users(
        self,
        session: Session,
        *,
        auth_service: AuthService,
        wallet_service: WalletService,
        demo_password: str,
    ) -> None:
        for spec in DEMO_USER_SPECS:
            user = session.scalar(select(User).where(User.email == spec.email))
            if user is None:
                user = auth_service.register_user(
                    session,
                    email=spec.email,
                    full_name=spec.display_name,
                    phone_number="0000000000",
                    is_over_18=True,
                    username=spec.username,
                    password=demo_password,
                    display_name=spec.display_name,
                    role=spec.role,
                )
            else:
                user.username = spec.username
                user.display_name = spec.display_name
                user.role = spec.role
                user.is_active = True
                user.password_hash = hash_password(demo_password)
                session.flush()
                wallet_service.ensure_default_accounts(session, user)

            payment_reference = f"demo-payment-{spec.username}"
            payment_event = session.scalar(
                select(PaymentEvent).where(PaymentEvent.provider_reference == payment_reference)
            )
            if payment_event is None:
                payment_event = wallet_service.create_payment_event(
                    session,
                    user=user,
                    provider=spec.provider,
                    provider_reference=payment_reference,
                    amount=spec.coin_balance,
                    pack_code="demo-balance",
                )
            if payment_event.user_id != user.id:
                raise ValueError(f"Payment event {payment_reference} is bound to a different user.")
            if payment_event.status == PaymentStatus.PENDING:
                wallet_service.verify_payment_event(session, payment_event, actor=user)

            self._rebalance_account(
                session,
                wallet_service=wallet_service,
                user=user,
                unit=LedgerUnit.COIN,
                target_balance=spec.coin_balance,
                reference=f"demo-rebalance-{spec.username}-coin",
            )
            self._rebalance_account(
                session,
                wallet_service=wallet_service,
                user=user,
                unit=LedgerUnit.CREDIT,
                target_balance=spec.credit_balance,
                reference=f"demo-rebalance-{spec.username}-credit",
            )

        session.flush()

    def _rebalance_account(
        self,
        session: Session,
        *,
        wallet_service: WalletService,
        user: User,
        unit: LedgerUnit,
        target_balance: Decimal,
        reference: str,
    ) -> None:
        account = wallet_service.get_user_account(session, user, unit)
        current_balance = wallet_service.get_balance(session, account)
        delta = Decimal(target_balance) - current_balance
        if delta == Decimal("0.0000"):
            return

        platform_account = wallet_service.ensure_platform_account(session, unit)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=account, amount=delta),
                LedgerPosting(account=platform_account, amount=-delta),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            reference=reference,
            description="Demo bootstrap balance reconciliation",
            actor=user,
        )

    def _purge_demo_read_models(self, session: Session, *, provider_name: str) -> None:
        player_ids = self._list_demo_player_ids(session, provider_name=provider_name)
        if not player_ids:
            return

        session.execute(
            delete(PlayerValueSnapshotRecord).where(PlayerValueSnapshotRecord.player_id.in_(tuple(player_ids)))
        )
        session.execute(
            delete(PlayerSummaryReadModel).where(PlayerSummaryReadModel.player_id.in_(tuple(player_ids)))
        )

    def _list_demo_player_ids(self, session: Session, *, provider_name: str) -> list[str]:
        statement = (
            select(Player.id)
            .where(Player.source_provider == provider_name)
            .order_by(Player.full_name.asc(), Player.id.asc())
        )
        return list(session.scalars(statement))

    def _seed_market_signals(
        self,
        session: Session,
        *,
        player_ids: Sequence[str],
        signal_provider: str,
        previous_snapshot_at: datetime,
        current_snapshot_at: datetime,
    ) -> int:
        session.execute(delete(MarketSignal).where(MarketSignal.source_provider == signal_provider))
        if not player_ids:
            return 0

        rows: list[dict[str, Any]] = []
        previous_anchor = previous_snapshot_at - timedelta(hours=1)
        current_anchor = current_snapshot_at - timedelta(hours=1)
        for index, player_id in enumerate(player_ids):
            base_value = 42 + (index * 3)
            trend_direction = 1 if index % 4 in (0, 1) else -1
            trend_delta = 6 + (index % 4)
            # Alternate winners and decliners so the frontend seed always has both states available.
            current_value = base_value + trend_delta if trend_direction > 0 else max(1, base_value - trend_delta)
            watchlist_score = 10 + (index % 5) if trend_direction > 0 else 4 + (index % 3)
            holder_count_score = 18 + index if trend_direction > 0 else 9 + index
            rows.extend(
                (
                    {
                        "source_provider": signal_provider,
                        "provider_external_id": f"{player_id}-current-previous",
                        "player_id": player_id,
                        "signal_type": "current_credits",
                        "score": float(base_value),
                        "as_of": previous_anchor,
                        "notes": "Demo seed previous snapshot anchor",
                    },
                    {
                        "source_provider": signal_provider,
                        "provider_external_id": f"{player_id}-current-latest",
                        "player_id": player_id,
                        "signal_type": "current_credits",
                        "score": float(current_value),
                        "as_of": current_anchor,
                        "notes": "Demo seed current snapshot anchor",
                    },
                    {
                        "source_provider": signal_provider,
                        "provider_external_id": f"{player_id}-watchlist",
                        "player_id": player_id,
                        "signal_type": "watchlist_adds",
                        "score": float(watchlist_score),
                        "as_of": current_snapshot_at - timedelta(days=index % 4),
                        "notes": "Demo scouting activity",
                    },
                    {
                        "source_provider": signal_provider,
                        "provider_external_id": f"{player_id}-holder-count",
                        "player_id": player_id,
                        "signal_type": "holder_count",
                        "score": float(holder_count_score),
                        "as_of": current_anchor,
                        "notes": "Demo holder count",
                    },
                )
            )

        session.execute(insert(MarketSignal), rows)
        session.flush()
        return len(rows)

    def _load_demo_users(self, session: Session) -> tuple[User, ...]:
        users: list[User] = []
        for spec in DEMO_USER_SPECS:
            user = session.scalar(select(User).where(User.email == spec.email))
            if user is None:
                raise ValueError(f"Demo user {spec.email} is missing after bootstrap.")
            users.append(user)
        return tuple(users)

    def _load_demo_user_summaries(
        self,
        session: Session,
        *,
        wallet_service: WalletService,
        demo_password: str,
    ) -> tuple[DemoUserSummary, ...]:
        summaries: list[DemoUserSummary] = []
        for spec in DEMO_USER_SPECS:
            user = session.scalar(select(User).where(User.email == spec.email))
            if user is None:
                raise ValueError(f"Demo user {spec.email} is missing after bootstrap.")
            coin_account = wallet_service.get_user_account(session, user, LedgerUnit.COIN)
            credit_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
            summaries.append(
                DemoUserSummary(
                    user_id=user.id,
                    email=user.email,
                    username=user.username,
                    display_name=user.display_name or user.username,
                    role=user.role.value,
                    password=demo_password,
                    coin_balance=wallet_service.get_balance(session, coin_account),
                    credit_balance=wallet_service.get_balance(session, credit_account),
                )
            )
        return tuple(summaries)

    def _ensure_frontend_market_states(
        self,
        session: Session,
        *,
        player_ids: Sequence[str],
        current_snapshot_at: datetime,
    ) -> None:
        if not player_ids:
            return

        snapshots = session.scalars(
            select(PlayerValueSnapshotRecord)
            .where(
                PlayerValueSnapshotRecord.player_id.in_(tuple(player_ids)),
                PlayerValueSnapshotRecord.as_of == current_snapshot_at,
            )
            .order_by(PlayerValueSnapshotRecord.player_id.asc())
        ).all()
        if not snapshots:
            return

        if not any(snapshot.movement_pct > 0 for snapshot in snapshots):
            self._apply_demo_market_state(session, snapshot=snapshots[0], state="rising")
        if not any(snapshot.movement_pct < 0 for snapshot in snapshots):
            self._apply_demo_market_state(session, snapshot=snapshots[-1], state="falling")

        session.flush()

    def _apply_demo_market_state(
        self,
        session: Session,
        *,
        snapshot: PlayerValueSnapshotRecord,
        state: str,
    ) -> None:
        movement_pct = 0.084 if state == "rising" else -0.084
        target_credits = round(max(snapshot.previous_credits * (1.0 + movement_pct), 1.0), 2)

        breakdown_payload = dict(snapshot.breakdown_json) if isinstance(snapshot.breakdown_json, dict) else {}
        breakdown_payload["demo_market_state"] = state
        breakdown_payload["published_card_value_credits"] = target_credits

        snapshot.target_credits = target_credits
        snapshot.movement_pct = movement_pct
        snapshot.football_truth_value_credits = target_credits
        snapshot.market_signal_value_credits = target_credits
        snapshot.breakdown_json = breakdown_payload
        snapshot.drivers_json = [driver for driver in ("demo_seed_frontend_state", f"demo_{state}") if driver]

        summary = session.get(PlayerSummaryReadModel, snapshot.player_id)
        if summary is not None:
            summary.current_value_credits = target_credits
            summary.previous_value_credits = snapshot.previous_credits
            summary.movement_pct = movement_pct
            summary_payload = dict(summary.summary_json) if isinstance(summary.summary_json, dict) else {}
            summary_payload["demo_market_state"] = state
            summary.summary_json = summary_payload

    def _load_featured_players(
        self,
        session: Session,
        *,
        player_ids: Sequence[str],
        limit: int,
    ) -> tuple[FeaturedPlayerSummary, ...]:
        if limit <= 0 or not player_ids:
            return ()

        statement = (
            select(PlayerSummaryReadModel)
            .where(PlayerSummaryReadModel.player_id.in_(tuple(player_ids)))
            .order_by(
                PlayerSummaryReadModel.current_value_credits.desc(),
                PlayerSummaryReadModel.player_name.asc(),
            )
            .limit(limit)
        )
        return tuple(
            FeaturedPlayerSummary(
                player_id=summary.player_id,
                player_name=summary.player_name,
                current_club_name=summary.current_club_name,
                current_competition_name=summary.current_competition_name,
                current_value_credits=summary.current_value_credits,
                movement_pct=summary.movement_pct,
            )
            for summary in session.scalars(statement)
        )

    def _reset_demo_holdings(
        self,
        session: Session,
        *,
        wallet_service: WalletService,
    ) -> None:
        for user in self._load_demo_users(session):
            position_accounts = session.scalars(
                select(LedgerAccount).where(LedgerAccount.code.like(f"position:{user.id}:%:available"))
            ).all()
            for account in position_accounts:
                quantity = wallet_service.get_balance(session, account)
                if quantity <= Decimal("0.0000"):
                    continue

                player_id = self._player_id_from_position_account_code(account.code)
                exit_price = self._resolve_demo_holding_price(session, player_id)
                proceeds = (quantity * exit_price).quantize(Decimal("0.0001"))
                external_reference = f"demo-holding-reset-{user.username}-{player_id}"

                wallet_service.credit_trade_proceeds(
                    session,
                    user=user,
                    amount=proceeds,
                    reference=external_reference,
                    description="Demo bootstrap reset seeded position proceeds",
                    external_reference=external_reference,
                )
                wallet_service.settle_available_position_units(
                    session,
                    user=user,
                    player_id=player_id,
                    quantity=quantity,
                    reference=external_reference,
                    description="Demo bootstrap reset seeded position units",
                    external_reference=external_reference,
                )

    def _seed_demo_holdings(
        self,
        session: Session,
        *,
        wallet_service: WalletService,
        featured_players: Sequence[FeaturedPlayerSummary],
    ) -> tuple[DemoHoldingSummary, ...]:
        demo_users = self._load_demo_users(session)
        if not demo_users or not featured_players:
            return ()

        holdings: list[DemoHoldingSummary] = []
        for index, player in enumerate(featured_players):
            owner = demo_users[index % len(demo_users)]
            acquisition_credits = Decimal(str(player.current_value_credits)).quantize(Decimal("0.0001"))
            reference = f"demo-holding-buy-{owner.username}-{player.player_id}"

            self._ensure_credit_capacity(
                session,
                wallet_service=wallet_service,
                user=owner,
                required_amount=acquisition_credits,
                reference=f"{reference}-capacity",
            )
            wallet_service.settle_available_funds(
                session,
                user=owner,
                amount=acquisition_credits,
                reference=reference,
                description="Demo bootstrap portfolio acquisition cash leg",
                external_reference=reference,
            )
            wallet_service.credit_position_units(
                session,
                user=owner,
                player_id=player.player_id,
                quantity=Decimal("1.0000"),
                reference=reference,
                description="Demo bootstrap portfolio acquisition asset leg",
                external_reference=reference,
            )
            holdings.append(
                DemoHoldingSummary(
                    owner_username=owner.username,
                    owner_email=owner.email,
                    player_id=player.player_id,
                    player_name=player.player_name,
                    acquisition_credits=float(acquisition_credits),
                )
            )
        return tuple(holdings)

    def _ensure_credit_capacity(
        self,
        session: Session,
        *,
        wallet_service: WalletService,
        user: User,
        required_amount: Decimal,
        reference: str,
    ) -> None:
        available_account = wallet_service.get_user_account(session, user, LedgerUnit.CREDIT)
        available_balance = wallet_service.get_balance(session, available_account)
        if available_balance >= required_amount:
            return
        self._rebalance_account(
            session,
            wallet_service=wallet_service,
            user=user,
            unit=LedgerUnit.CREDIT,
            target_balance=required_amount,
            reference=reference,
        )

    def _resolve_demo_holding_price(self, session: Session, player_id: str) -> Decimal:
        summary = session.get(PlayerSummaryReadModel, player_id)
        if summary is not None and summary.current_value_credits and summary.current_value_credits > 0:
            return Decimal(str(summary.current_value_credits)).quantize(Decimal("0.0001"))

        snapshot = session.scalar(
            select(PlayerValueSnapshotRecord)
            .where(PlayerValueSnapshotRecord.player_id == player_id)
            .order_by(PlayerValueSnapshotRecord.as_of.desc(), PlayerValueSnapshotRecord.created_at.desc())
            .limit(1)
        )
        if snapshot is not None and snapshot.target_credits > 0:
            return Decimal(str(snapshot.target_credits)).quantize(Decimal("0.0001"))

        signal = session.scalar(
            select(MarketSignal)
            .where(
                MarketSignal.player_id == player_id,
                MarketSignal.signal_type == "current_credits",
            )
            .order_by(MarketSignal.as_of.desc(), MarketSignal.created_at.desc(), MarketSignal.id.desc())
            .limit(1)
        )
        if signal is not None and signal.score > 0:
            return Decimal(str(signal.score)).quantize(Decimal("0.0001"))

        return Decimal("1.0000")

    @staticmethod
    def _player_id_from_position_account_code(code: str) -> str:
        _, _, player_id, _ = code.split(":", 3)
        return player_id

    def _count_player_summaries(self, session: Session, *, player_ids: Sequence[str]) -> int:
        if not player_ids:
            return 0
        statement = select(PlayerSummaryReadModel.player_id).where(
            PlayerSummaryReadModel.player_id.in_(tuple(player_ids))
        )
        return len(list(session.scalars(statement)))


def seed_demo_data(
    *,
    database_url: str = DEFAULT_DATABASE_URL,
    settings: Settings | None = None,
    player_target_count: int = DEFAULT_DEMO_PLAYER_COUNT,
    provider_name: str = DEFAULT_DEMO_PROVIDER_NAME,
    signal_provider: str = DEFAULT_DEMO_SIGNAL_PROVIDER,
    demo_password: str = DEFAULT_DEMO_PASSWORD,
    random_seed: int = DEFAULT_DEMO_RANDOM_SEED,
    batch_size: int = DEFAULT_DEMO_BATCH_SIZE,
    featured_player_limit: int = DEFAULT_FEATURED_PLAYER_LIMIT,
    with_liquidity: bool = False,
    liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
    illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
) -> DemoBootstrapSummary:
    resolved_settings = settings or load_settings(
        environ={
            **os.environ,
            "GTE_DATABASE_URL": database_url,
        }
    )
    engine = create_database_engine(database_url)
    try:
        ensure_database_schema_current(engine)
        session_factory = create_session_factory(engine)
        service = DemoBootstrapService(
            session_factory=session_factory,
            settings=resolved_settings,
        )
        return service.seed(
            player_target_count=player_target_count,
            provider_name=provider_name,
            signal_provider=signal_provider,
            demo_password=demo_password,
            random_seed=random_seed,
            batch_size=batch_size,
            featured_player_limit=featured_player_limit,
            with_liquidity=with_liquidity,
            liquid_player_count=liquid_player_count,
            illiquid_player_count=illiquid_player_count,
        )
    finally:
        engine.dispose()


def build_parser() -> argparse.ArgumentParser:
    class _HelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
        pass

    parser = argparse.ArgumentParser(
        description="Seed the local demo dataset used by frontend demos and QA.",
        epilog=(
            "Examples:\n"
            "  python backend/scripts/bootstrap_demo.py --player-count 24 --seed 20260311\n"
            "  python backend/scripts/bootstrap_demo.py --player-count 24 --with-liquidity --seed 20260311"
        ),
        formatter_class=_HelpFormatter,
    )
    parser.add_argument("--database-url", default=os.getenv("GTE_DATABASE_URL", DEFAULT_DATABASE_URL), help="Target database URL.")
    parser.add_argument("--player-count", type=int, default=DEFAULT_DEMO_PLAYER_COUNT, help="Number of demo players to seed into the local universe.")
    parser.add_argument("--provider", default=DEFAULT_DEMO_PROVIDER_NAME, help="Synthetic provider slug written onto demo player records.")
    parser.add_argument("--signal-provider", default=DEFAULT_DEMO_SIGNAL_PROVIDER, help="Synthetic provider slug written onto demo market signals.")
    parser.add_argument("--password", default=DEFAULT_DEMO_PASSWORD, help="Password assigned to the local demo users for login flows.")
    parser.add_argument("--seed", type=int, default=DEFAULT_DEMO_RANDOM_SEED, help="Deterministic seed for repeatable demo users, holdings, and optional liquidity.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_DEMO_BATCH_SIZE, help="Batch size used while seeding the demo player universe.")
    parser.add_argument("--featured-limit", type=int, default=DEFAULT_FEATURED_PLAYER_LIMIT, help="Number of featured players to include in the summary output.")
    parser.add_argument("--with-liquidity", action=argparse.BooleanOptionalAction, default=False, help="Also seed deterministic exchange-side liquidity and trade history.")
    parser.add_argument("--liquid-player-count", type=int, default=DEFAULT_LIQUID_PLAYER_COUNT, help="Number of high-activity players to receive liquid demo markets.")
    parser.add_argument("--illiquid-player-count", type=int, default=DEFAULT_ILLIQUID_PLAYER_COUNT, help="Number of low-activity players to receive illiquid demo markets.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = seed_demo_data(
        database_url=args.database_url,
        player_target_count=args.player_count,
        provider_name=args.provider,
        signal_provider=args.signal_provider,
        demo_password=args.password,
        random_seed=args.seed,
        batch_size=args.batch_size,
        featured_player_limit=args.featured_limit,
        with_liquidity=args.with_liquidity,
        liquid_player_count=args.liquid_player_count,
        illiquid_player_count=args.illiquid_player_count,
    )
    print(json.dumps(summary.to_dict(), indent=2, default=str))
    return 0


__all__ = [
    "DEFAULT_CURRENT_SNAPSHOT_AT",
    "DEFAULT_DEMO_BATCH_SIZE",
    "DEFAULT_DEMO_PASSWORD",
    "DEFAULT_DEMO_PLAYER_COUNT",
    "DEFAULT_DEMO_PROVIDER_NAME",
    "DEFAULT_DEMO_RANDOM_SEED",
    "DEFAULT_DEMO_SIGNAL_PROVIDER",
    "DEFAULT_FEATURED_PLAYER_LIMIT",
    "DEFAULT_ILLIQUID_PLAYER_COUNT",
    "DEFAULT_LIQUID_PLAYER_COUNT",
    "DEFAULT_PREVIOUS_SNAPSHOT_AT",
    "DEMO_USER_SPECS",
    "DemoBootstrapService",
    "DemoBootstrapSummary",
    "DemoHoldingSummary",
    "DemoUserSummary",
    "FeaturedPlayerSummary",
    "build_parser",
    "main",
    "seed_demo_data",
]
