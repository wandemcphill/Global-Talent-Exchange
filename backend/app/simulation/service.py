from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Sequence
import random

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.security import hash_password
from app.auth.service import AuthService
from app.core.events import EventPublisher, InMemoryEventPublisher
from app.ingestion.models import Player
from app.ledger.models import LedgerEventRecord
from app.market.service import MarketEngine
from app.matching.models import TradeExecution
from app.matching.service import MatchingService
from app.models.user import User, UserRole
from app.models.wallet import LedgerAccount, LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.orders.models import Order, OrderSide, OrderStatus
from app.orders.service import OrderService
from app.players.read_models import PlayerSummaryReadModel
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
PRICE_QUANTUM = Decimal("1")
DEFAULT_SIMULATION_SEED = 20260311
DEFAULT_LIQUID_PLAYER_COUNT = 4
DEFAULT_ILLIQUID_PLAYER_COUNT = 2
DEFAULT_SIMULATION_CREDIT_BALANCE = Decimal("250000.0000")
DEFAULT_TICK_COUNT = 3


@dataclass(frozen=True, slots=True)
class SimulationUserSpec:
    email: str
    username: str
    display_name: str
    role: UserRole = UserRole.USER
    credit_balance: Decimal = DEFAULT_SIMULATION_CREDIT_BALANCE


@dataclass(frozen=True, slots=True)
class SimulationPlayerProfile:
    player_id: str
    player_name: str
    reference_price: Decimal
    current_value_credits: Decimal
    market_interest_score: int
    activity_intensity: int
    spread_steps: tuple[int, ...]
    trade_history_count: int
    liquidity_label: str


@dataclass(frozen=True, slots=True)
class SeededPlayerSummary:
    player_id: str
    player_name: str
    liquidity_label: str
    activity_intensity: int
    reference_price: Decimal
    best_bid: Decimal | None
    best_ask: Decimal | None
    spread: Decimal | None
    open_bid_levels: int
    open_ask_levels: int
    trade_executions_seeded: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "player_name": self.player_name,
            "liquidity_label": self.liquidity_label,
            "activity_intensity": self.activity_intensity,
            "reference_price": self.reference_price,
            "best_bid": self.best_bid,
            "best_ask": self.best_ask,
            "spread": self.spread,
            "open_bid_levels": self.open_bid_levels,
            "open_ask_levels": self.open_ask_levels,
            "trade_executions_seeded": self.trade_executions_seeded,
        }


@dataclass(frozen=True, slots=True)
class DemoLiquiditySeedSummary:
    player_count: int
    buy_orders_seeded: int
    sell_orders_seeded: int
    trade_executions_seeded: int
    simulation_users: tuple[str, ...]
    liquid_player_id: str | None
    illiquid_player_id: str | None
    players: tuple[SeededPlayerSummary, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_count": self.player_count,
            "buy_orders_seeded": self.buy_orders_seeded,
            "sell_orders_seeded": self.sell_orders_seeded,
            "trade_executions_seeded": self.trade_executions_seeded,
            "simulation_users": list(self.simulation_users),
            "liquid_player_id": self.liquid_player_id,
            "illiquid_player_id": self.illiquid_player_id,
            "players": [player.to_dict() for player in self.players],
        }


@dataclass(frozen=True, slots=True)
class SimulationTickSummary:
    tick_number: int
    orders_created: int
    trade_executions_created: int
    players_touched: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick_number": self.tick_number,
            "orders_created": self.orders_created,
            "trade_executions_created": self.trade_executions_created,
            "players_touched": list(self.players_touched),
        }


SIMULATION_USER_SPECS: tuple[SimulationUserSpec, ...] = (
    SimulationUserSpec(
        email="simulation.maker.alpha@gte.local",
        username="sim_maker_alpha",
        display_name="Simulation Maker Alpha",
    ),
    SimulationUserSpec(
        email="simulation.maker.beta@gte.local",
        username="sim_maker_beta",
        display_name="Simulation Maker Beta",
    ),
    SimulationUserSpec(
        email="simulation.maker.gamma@gte.local",
        username="sim_maker_gamma",
        display_name="Simulation Maker Gamma",
    ),
    SimulationUserSpec(
        email="simulation.taker.alpha@gte.local",
        username="sim_taker_alpha",
        display_name="Simulation Taker Alpha",
    ),
    SimulationUserSpec(
        email="simulation.taker.beta@gte.local",
        username="sim_taker_beta",
        display_name="Simulation Taker Beta",
    ),
    SimulationUserSpec(
        email="simulation.taker.gamma@gte.local",
        username="sim_taker_gamma",
        display_name="Simulation Taker Gamma",
    ),
)


class SimulationSeedError(ValueError):
    pass


@dataclass(slots=True)
class DemoMarketSimulationService:
    session_factory: sessionmaker[Session]
    event_publisher: EventPublisher = field(default_factory=InMemoryEventPublisher)

    def seed_demo_liquidity(
        self,
        *,
        random_seed: int = DEFAULT_SIMULATION_SEED,
        liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
        illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
        demo_password: str = "DemoPass123",
    ) -> DemoLiquiditySeedSummary:
        if liquid_player_count <= 0:
            raise SimulationSeedError("liquid_player_count must be greater than zero.")
        if illiquid_player_count < 0:
            raise SimulationSeedError("illiquid_player_count must be greater than or equal to zero.")

        auth_service = AuthService()
        wallet_service = WalletService(event_publisher=self.event_publisher)
        order_service = OrderService(event_publisher=self.event_publisher)
        matching_service = MatchingService()

        with self.session_factory() as session:
            simulation_users = self._ensure_simulation_users(
                session,
                auth_service=auth_service,
                wallet_service=wallet_service,
                demo_password=demo_password,
            )
            self._reset_simulation_exchange_state(session, simulation_users=simulation_users, wallet_service=wallet_service)
            profiles = self._select_player_profiles(
                session,
                liquid_player_count=liquid_player_count,
                illiquid_player_count=illiquid_player_count,
            )
            if not profiles:
                raise SimulationSeedError("No tradable players were found. Seed demo data before seeding liquidity.")

            buy_orders_seeded = 0
            sell_orders_seeded = 0
            trade_executions_seeded = 0
            player_summaries: list[SeededPlayerSummary] = []

            for index, profile in enumerate(profiles):
                rng = random.Random(random_seed + (index * 997))
                seeded_trades = self._seed_trade_history_for_player(
                    session,
                    profile=profile,
                    simulation_users=simulation_users,
                    order_service=order_service,
                    rng=rng,
                )
                trade_executions_seeded += seeded_trades

                bid_levels, ask_levels = self._seed_order_ladder_for_player(
                    session,
                    profile=profile,
                    simulation_users=simulation_users,
                    order_service=order_service,
                    rng=rng,
                )
                buy_orders_seeded += bid_levels
                sell_orders_seeded += ask_levels

                order_book = matching_service.build_order_book(session, player_id=profile.player_id)
                best_bid = order_book.bids[0].price if order_book.bids else None
                best_ask = order_book.asks[0].price if order_book.asks else None
                spread = self._normalize_amount(best_ask - best_bid) if best_bid is not None and best_ask is not None else None
                player_summaries.append(
                    SeededPlayerSummary(
                        player_id=profile.player_id,
                        player_name=profile.player_name,
                        liquidity_label=profile.liquidity_label,
                        activity_intensity=profile.activity_intensity,
                        reference_price=profile.reference_price,
                        best_bid=best_bid,
                        best_ask=best_ask,
                        spread=spread,
                        open_bid_levels=bid_levels,
                        open_ask_levels=ask_levels,
                        trade_executions_seeded=seeded_trades,
                    )
                )

            session.commit()

        return DemoLiquiditySeedSummary(
            player_count=len(player_summaries),
            buy_orders_seeded=buy_orders_seeded,
            sell_orders_seeded=sell_orders_seeded,
            trade_executions_seeded=trade_executions_seeded,
            simulation_users=tuple(user.username for user in simulation_users),
            liquid_player_id=next((item.player_id for item in player_summaries if item.liquidity_label == "liquid"), None),
            illiquid_player_id=next((item.player_id for item in player_summaries if item.liquidity_label == "illiquid"), None),
            players=tuple(player_summaries),
        )

    def run_simulation_tick(
        self,
        *,
        tick_number: int,
        random_seed: int = DEFAULT_SIMULATION_SEED,
        liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
        illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
    ) -> SimulationTickSummary:
        if tick_number < 1:
            raise SimulationSeedError("tick_number must be at least 1.")

        order_service = OrderService(event_publisher=self.event_publisher)
        with self.session_factory() as session:
            simulation_users = self._load_simulation_users(session)
            profiles = self._select_player_profiles(
                session,
                liquid_player_count=liquid_player_count,
                illiquid_player_count=illiquid_player_count,
            )
            if not profiles:
                raise SimulationSeedError("No tradable players were found. Seed demo data before running simulation ticks.")
            if len(simulation_users) < 2:
                raise SimulationSeedError("Simulation users are missing. Run seed_demo_liquidity before simulation ticks.")

            orders_created = 0
            trades_created = 0
            touched: list[str] = []

            for index, profile in enumerate(profiles):
                rng = random.Random(random_seed + (tick_number * 10_000) + index)
                seller = simulation_users[(index + tick_number) % len(simulation_users)]
                buyer = simulation_users[(index + tick_number + 1) % len(simulation_users)]
                price_shift = rng.randint(-profile.activity_intensity, profile.activity_intensity)
                price = max(
                    Decimal("1.0000"),
                    self._normalize_amount(profile.reference_price + Decimal(price_shift)),
                )
                quantity = Decimal(profile.activity_intensity)

                order_service.place_order(
                    session,
                    user=seller,
                    player_id=profile.player_id,
                    side=OrderSide.SELL,
                    quantity=quantity,
                    max_price=price,
                )
                order_service.place_order(
                    session,
                    user=buyer,
                    player_id=profile.player_id,
                    side=OrderSide.BUY,
                    quantity=quantity,
                    max_price=price,
                )
                orders_created += 2
                trades_created += 1
                touched.append(profile.player_id)

                resting_bid = max(Decimal("1.0000"), self._normalize_amount(price - Decimal(profile.activity_intensity)))
                resting_ask = self._normalize_amount(price + Decimal(profile.activity_intensity))
                order_service.place_order(
                    session,
                    user=buyer,
                    player_id=profile.player_id,
                    side=OrderSide.BUY,
                    quantity=Decimal("1.0000"),
                    max_price=resting_bid,
                )
                order_service.place_order(
                    session,
                    user=seller,
                    player_id=profile.player_id,
                    side=OrderSide.SELL,
                    quantity=Decimal("1.0000"),
                    max_price=resting_ask,
                )
                orders_created += 2

            session.commit()

        return SimulationTickSummary(
            tick_number=tick_number,
            orders_created=orders_created,
            trade_executions_created=trades_created,
            players_touched=tuple(sorted(set(touched))),
        )

    def run_simulation_ticks(
        self,
        *,
        tick_count: int = DEFAULT_TICK_COUNT,
        start_tick: int = 1,
        random_seed: int = DEFAULT_SIMULATION_SEED,
        liquid_player_count: int = DEFAULT_LIQUID_PLAYER_COUNT,
        illiquid_player_count: int = DEFAULT_ILLIQUID_PLAYER_COUNT,
    ) -> tuple[SimulationTickSummary, ...]:
        if tick_count <= 0:
            raise SimulationSeedError("tick_count must be greater than zero.")
        return tuple(
            self.run_simulation_tick(
                tick_number=start_tick + offset,
                random_seed=random_seed,
                liquid_player_count=liquid_player_count,
                illiquid_player_count=illiquid_player_count,
            )
            for offset in range(tick_count)
        )

    def replay_market_state(self, market_engine: MarketEngine) -> DemoLiquiditySeedSummary:
        with self.session_factory() as session:
            profiles = self._select_player_profiles(
                session,
                liquid_player_count=DEFAULT_LIQUID_PLAYER_COUNT,
                illiquid_player_count=DEFAULT_ILLIQUID_PLAYER_COUNT,
            )
            player_ids = [profile.player_id for profile in profiles]
            orders = session.scalars(
                select(Order)
                .where(Order.player_id.in_(tuple(player_ids)))
                .order_by(Order.created_at.asc(), Order.id.asc())
            ).all()
            orders_by_id = {order.id: order for order in orders}
            executions = session.scalars(
                select(TradeExecution)
                .where(TradeExecution.player_id.in_(tuple(player_ids)))
                .order_by(TradeExecution.created_at.asc(), TradeExecution.id.asc())
            ).all()
            order_book_by_player = {profile.player_id: MatchingService().build_order_book(session, player_id=profile.player_id) for profile in profiles}

        player_summaries: list[SeededPlayerSummary] = []
        for profile in profiles:
            order_book = order_book_by_player[profile.player_id]
            if order_book.asks:
                best_ask = order_book.asks[0].price
                ask_order = next(
                    (
                        order
                        for order in orders
                        if order.player_id == profile.player_id
                        and order.side == OrderSide.SELL
                        and order.status in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}
                        and self._normalize_amount(order.max_price) == best_ask
                    ),
                    None,
                )
                if ask_order is not None:
                    market_engine.create_listing(
                        asset_id=profile.player_id,
                        seller_user_id=ask_order.user_id,
                        listing_type="transfer",
                        ask_price=int(best_ask),
                        note="Simulation replay best ask",
                    )
            if order_book.bids:
                best_bid = order_book.bids[0].price
                bid_order = next(
                    (
                        order
                        for order in orders
                        if order.player_id == profile.player_id
                        and order.side == OrderSide.BUY
                        and order.status in {OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED}
                        and self._normalize_amount(order.max_price) == best_bid
                    ),
                    None,
                )
                if bid_order is not None:
                    market_engine.create_trade_intent(
                        user_id=bid_order.user_id,
                        asset_id=profile.player_id,
                        direction="buy",
                        price_ceiling=int(best_bid),
                        note="Simulation replay best bid",
                    )

            replayed_executions = 0
            for execution in executions:
                if execution.player_id != profile.player_id:
                    continue
                buy_order = orders_by_id.get(execution.buy_order_id)
                sell_order = orders_by_id.get(execution.sell_order_id)
                market_engine.record_execution(
                    asset_id=profile.player_id,
                    price=float(execution.price),
                    quantity=float(execution.quantity),
                    buyer_user_id=buy_order.user_id if buy_order is not None else None,
                    seller_user_id=sell_order.user_id if sell_order is not None else None,
                    occurred_at=execution.created_at,
                    source="simulation.replay",
                )
                replayed_executions += 1

            best_bid = order_book.bids[0].price if order_book.bids else None
            best_ask = order_book.asks[0].price if order_book.asks else None
            spread = self._normalize_amount(best_ask - best_bid) if best_bid is not None and best_ask is not None else None
            player_summaries.append(
                SeededPlayerSummary(
                    player_id=profile.player_id,
                    player_name=profile.player_name,
                    liquidity_label=profile.liquidity_label,
                    activity_intensity=profile.activity_intensity,
                    reference_price=profile.reference_price,
                    best_bid=best_bid,
                    best_ask=best_ask,
                    spread=spread,
                    open_bid_levels=len(order_book.bids),
                    open_ask_levels=len(order_book.asks),
                    trade_executions_seeded=replayed_executions,
                )
            )

        return DemoLiquiditySeedSummary(
            player_count=len(player_summaries),
            buy_orders_seeded=sum(item.open_bid_levels for item in player_summaries),
            sell_orders_seeded=sum(item.open_ask_levels for item in player_summaries),
            trade_executions_seeded=sum(item.trade_executions_seeded for item in player_summaries),
            simulation_users=tuple(spec.username for spec in SIMULATION_USER_SPECS),
            liquid_player_id=next((item.player_id for item in player_summaries if item.liquidity_label == "liquid"), None),
            illiquid_player_id=next((item.player_id for item in player_summaries if item.liquidity_label == "illiquid"), None),
            players=tuple(player_summaries),
        )

    def _ensure_simulation_users(
        self,
        session: Session,
        *,
        auth_service: AuthService,
        wallet_service: WalletService,
        demo_password: str,
    ) -> tuple[User, ...]:
        users: list[User] = []
        for spec in SIMULATION_USER_SPECS:
            user = session.scalar(select(User).where(User.email == spec.email))
            if user is None:
                user = auth_service.register_user(
                    session,
                    email=spec.email,
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
                wallet_service.ensure_default_accounts(session, user)
                session.flush()

            self._rebalance_user_wallets(
                session,
                wallet_service=wallet_service,
                user=user,
                available_target=spec.credit_balance,
                escrow_target=Decimal("0.0000"),
            )
            users.append(user)
        session.flush()
        return tuple(users)

    def _load_simulation_users(self, session: Session) -> tuple[User, ...]:
        users = [
            session.scalar(select(User).where(User.username == spec.username))
            for spec in SIMULATION_USER_SPECS
        ]
        return tuple(user for user in users if user is not None)

    def _reset_simulation_exchange_state(
        self,
        session: Session,
        *,
        simulation_users: Sequence[User],
        wallet_service: WalletService,
    ) -> None:
        user_ids = tuple(user.id for user in simulation_users)
        if not user_ids:
            return

        order_ids = tuple(
            session.scalars(
                select(Order.id).where(Order.user_id.in_(user_ids))
            )
        )
        if order_ids:
            session.execute(
                delete(TradeExecution).where(
                    or_(
                        TradeExecution.buy_order_id.in_(order_ids),
                        TradeExecution.sell_order_id.in_(order_ids),
                    )
                )
            )
            session.execute(delete(LedgerEventRecord).where(LedgerEventRecord.aggregate_id.in_(order_ids)))
            session.execute(delete(Order).where(Order.id.in_(order_ids)))

        for spec, user in zip(SIMULATION_USER_SPECS, simulation_users, strict=True):
            self._rebalance_user_wallets(
                session,
                wallet_service=wallet_service,
                user=user,
                available_target=spec.credit_balance,
                escrow_target=Decimal("0.0000"),
            )

    def _select_player_profiles(
        self,
        session: Session,
        *,
        liquid_player_count: int,
        illiquid_player_count: int,
    ) -> tuple[SimulationPlayerProfile, ...]:
        rows = session.execute(
            select(Player, PlayerSummaryReadModel)
            .join(PlayerSummaryReadModel, PlayerSummaryReadModel.player_id == Player.id)
            .where(Player.is_tradable.is_(True))
            .order_by(
                PlayerSummaryReadModel.current_value_credits.desc(),
                PlayerSummaryReadModel.market_interest_score.desc(),
                Player.full_name.asc(),
            )
        ).all()
        if not rows:
            return ()

        top_rows = rows[:liquid_player_count]
        bottom_rows = rows[-illiquid_player_count:] if illiquid_player_count else []
        selected_rows: list[tuple[Player, PlayerSummaryReadModel]] = []
        seen: set[str] = set()
        for row in [*top_rows, *bottom_rows]:
            player, summary = row
            if player.id in seen:
                continue
            seen.add(player.id)
            selected_rows.append((player, summary))

        profiles: list[SimulationPlayerProfile] = []
        for index, (player, summary) in enumerate(selected_rows):
            liquidity_label = "liquid" if index < len(top_rows) else "illiquid"
            if liquidity_label == "liquid":
                activity_intensity = 3
                spread_steps = (2, 4, 6)
                trade_history_count = 3
            else:
                activity_intensity = 1
                spread_steps = (10, 16)
                trade_history_count = 1
            reference_price = self._normalize_price(summary.current_value_credits)
            profiles.append(
                SimulationPlayerProfile(
                    player_id=player.id,
                    player_name=player.full_name,
                    reference_price=reference_price,
                    current_value_credits=self._normalize_amount(summary.current_value_credits),
                    market_interest_score=summary.market_interest_score,
                    activity_intensity=activity_intensity,
                    spread_steps=spread_steps,
                    trade_history_count=trade_history_count,
                    liquidity_label=liquidity_label,
                )
            )
        return tuple(profiles)

    def _seed_trade_history_for_player(
        self,
        session: Session,
        *,
        profile: SimulationPlayerProfile,
        simulation_users: Sequence[User],
        order_service: OrderService,
        rng: random.Random,
    ) -> int:
        seeded = 0
        for index in range(profile.trade_history_count):
            seller = simulation_users[(index * 2) % len(simulation_users)]
            buyer = simulation_users[(index * 2 + 1) % len(simulation_users)]
            price_adjustment = rng.randint(-profile.activity_intensity, profile.activity_intensity)
            trade_price = max(Decimal("1.0000"), self._normalize_amount(profile.reference_price + Decimal(price_adjustment)))
            quantity = Decimal(profile.activity_intensity)
            order_service.place_order(
                session,
                user=seller,
                player_id=profile.player_id,
                side=OrderSide.SELL,
                quantity=quantity,
                max_price=trade_price,
            )
            order_service.place_order(
                session,
                user=buyer,
                player_id=profile.player_id,
                side=OrderSide.BUY,
                quantity=quantity,
                max_price=trade_price,
            )
            seeded += 1
        return seeded

    def _seed_order_ladder_for_player(
        self,
        session: Session,
        *,
        profile: SimulationPlayerProfile,
        simulation_users: Sequence[User],
        order_service: OrderService,
        rng: random.Random,
    ) -> tuple[int, int]:
        bid_levels = 0
        ask_levels = 0
        for level_index, spread_step in enumerate(profile.spread_steps):
            bid_user = simulation_users[(level_index + 1) % len(simulation_users)]
            ask_user = simulation_users[(level_index + 2) % len(simulation_users)]
            bid_price = max(
                Decimal("1.0000"),
                self._normalize_amount(profile.reference_price - Decimal(spread_step)),
            )
            ask_price = self._normalize_amount(profile.reference_price + Decimal(spread_step))
            quantity = Decimal(profile.activity_intensity + level_index + rng.randint(0, profile.activity_intensity))

            order_service.place_order(
                session,
                user=bid_user,
                player_id=profile.player_id,
                side=OrderSide.BUY,
                quantity=quantity,
                max_price=bid_price,
            )
            order_service.place_order(
                session,
                user=ask_user,
                player_id=profile.player_id,
                side=OrderSide.SELL,
                quantity=quantity,
                max_price=ask_price,
            )
            bid_levels += 1
            ask_levels += 1
        return bid_levels, ask_levels

    def _rebalance_user_wallets(
        self,
        session: Session,
        *,
        wallet_service: WalletService,
        user: User,
        available_target: Decimal,
        escrow_target: Decimal,
    ) -> None:
        for unit in (LedgerUnit.COIN, LedgerUnit.CREDIT):
            available_account = wallet_service.get_user_account(session, user, unit)
            escrow_account = wallet_service.get_user_escrow_account(session, user, unit)
            self._rebalance_account(
                session,
                account=available_account,
                target_balance=available_target,
                wallet_service=wallet_service,
                actor=user,
            )
            self._rebalance_account(
                session,
                account=escrow_account,
                target_balance=escrow_target,
                wallet_service=wallet_service,
                actor=user,
            )

    def _rebalance_account(
        self,
        session: Session,
        *,
        account: LedgerAccount,
        target_balance: Decimal,
        wallet_service: WalletService,
        actor: User,
    ) -> None:
        current_balance = wallet_service.get_balance(session, account)
        delta = self._normalize_amount(target_balance - current_balance)
        if delta == Decimal("0.0000"):
            return
        platform_account = wallet_service.ensure_platform_account(session, account.unit)
        wallet_service.append_transaction(
            session,
            postings=[
                LedgerPosting(account=account, amount=delta),
                LedgerPosting(account=platform_account, amount=-delta),
            ],
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"simulation-rebalance-{account.code}",
            description="Simulation wallet rebalance",
            actor=actor,
        )

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    @staticmethod
    def _normalize_price(value: Decimal | int | float | str | None) -> Decimal:
        if value is None:
            return Decimal("1.0000")
        normalized = Decimal(str(value)).quantize(PRICE_QUANTUM, rounding=ROUND_HALF_UP)
        if normalized <= Decimal("0"):
            return Decimal("1.0000")
        return normalized.quantize(AMOUNT_QUANTUM)


__all__ = [
    "DEFAULT_ILLIQUID_PLAYER_COUNT",
    "DEFAULT_LIQUID_PLAYER_COUNT",
    "DEFAULT_SIMULATION_SEED",
    "DEFAULT_TICK_COUNT",
    "DemoLiquiditySeedSummary",
    "DemoMarketSimulationService",
    "SeededPlayerSummary",
    "SIMULATION_USER_SPECS",
    "SimulationPlayerProfile",
    "SimulationSeedError",
    "SimulationTickSummary",
]
