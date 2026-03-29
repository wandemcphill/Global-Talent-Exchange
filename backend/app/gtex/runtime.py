from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI
from sqlalchemy.orm import Session, sessionmaker

from app.core.container import ApplicationContext
from app.gtex.config import GtexSettings, load_gtex_settings
from app.gtex.service import AiLeagueService, CreatorMarketService, JackpotService, UnifiedEconomyService
from app.gtex.store import build_state_store
from app.wallets.service import WalletService


@dataclass(slots=True)
class GtexRuntime:
    settings: GtexSettings
    state_store: Any
    wallet_service: WalletService
    jackpot: JackpotService
    creator_market: CreatorMarketService
    economy: UnifiedEconomyService
    ai_leagues: AiLeagueService

    def shutdown(self) -> None:
        self.state_store.close()


def build_gtex_runtime(
    *,
    app_settings,
    session_factory: sessionmaker[Session] | None,
    event_publisher,
    redis_url: str | None,
    realtime_channel: str,
) -> GtexRuntime:
    del session_factory
    gtex_settings = load_gtex_settings()
    wallet_service = WalletService(event_publisher=event_publisher)
    state_store = build_state_store(redis_url=redis_url, realtime_channel=realtime_channel)
    jackpot = JackpotService(
        settings=gtex_settings,
        wallet_service=wallet_service,
        state_store=state_store,
        event_publisher=event_publisher,
        realtime_channel=realtime_channel,
    )
    creator_market = CreatorMarketService(
        settings=gtex_settings,
        wallet_service=wallet_service,
        state_store=state_store,
        event_publisher=event_publisher,
        realtime_channel=realtime_channel,
    )
    economy = UnifiedEconomyService(
        settings=gtex_settings,
        wallet_service=wallet_service,
        state_store=state_store,
        jackpot_service=jackpot,
        creator_market_service=creator_market,
        event_publisher=event_publisher,
        realtime_channel=realtime_channel,
    )
    ai_leagues = AiLeagueService(
        settings=gtex_settings,
        wallet_service=wallet_service,
        state_store=state_store,
        creator_market_service=creator_market,
        economy_service=economy,
        event_publisher=event_publisher,
        realtime_channel=realtime_channel,
    )
    return GtexRuntime(
        settings=gtex_settings,
        state_store=state_store,
        wallet_service=wallet_service,
        jackpot=jackpot,
        creator_market=creator_market,
        economy=economy,
        ai_leagues=ai_leagues,
    )


def ensure_gtex_runtime(app: FastAPI) -> GtexRuntime:
    runtime = getattr(app.state, "gtex_runtime", None)
    if runtime is None:
        runtime = build_gtex_runtime(
            app_settings=getattr(app.state, "settings", None),
            session_factory=getattr(app.state, "session_factory", None),
            event_publisher=getattr(app.state, "event_publisher", None),
            redis_url=getattr(getattr(app.state, "settings", None), "redis_url", None),
            realtime_channel=getattr(getattr(app.state, "settings", None), "redis_realtime_channel", "gtex.realtime"),
        )
        app.state.gtex_runtime = runtime
        _seed_runtime(app, runtime)
    return runtime


def bind_gtex_runtime(app: FastAPI, context: ApplicationContext) -> None:
    if getattr(app.state, "gtex_runtime", None) is not None:
        return
    app.state.gtex_runtime = build_gtex_runtime(
        app_settings=context.settings,
        session_factory=context.database.session_factory,
        event_publisher=context.event_publisher,
        redis_url=context.settings.redis_url,
        realtime_channel=context.settings.redis_realtime_channel,
    )
    _seed_runtime(app, app.state.gtex_runtime)


def shutdown_gtex_runtime(app: FastAPI, _context: ApplicationContext) -> None:
    runtime = getattr(app.state, "gtex_runtime", None)
    if runtime is not None:
        runtime.shutdown()
        app.state.gtex_runtime = None


def _seed_runtime(app: FastAPI, runtime: GtexRuntime) -> None:
    session_factory = getattr(app.state, "session_factory", None)
    if session_factory is None:
        return
    with session_factory() as session:
        runtime.jackpot.ensure_open_round(session)
        runtime.ai_leagues.seed_defaults(session)
        session.commit()
