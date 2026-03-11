from __future__ import annotations

from backend.app.admin.router import router as admin_router
from backend.app.auth.router import router as auth_router
from backend.app.clubs.router import router as clubs_router
from backend.app.competitions.router import router as competitions_router
from backend.app.core.health import router as health_router
from backend.app.core.module import DomainModule
from backend.app.ingestion.router import router as ingestion_router
from backend.app.market.router import router as market_router
from backend.app.notifications.router import router as notifications_router
from backend.app.players.router import router as players_router
from backend.app.portfolios.router import router as portfolios_router
from backend.app.realtime.router import router as realtime_router
from backend.app.surveillance.router import router as surveillance_router
from backend.app.users.router import router as users_router
from backend.app.value_engine.router import router as value_engine_router
from backend.app.wallets.router import router as wallets_router

DOMAIN_MODULES = (
    DomainModule(name="health", router=health_router),
    DomainModule(name="admin", router=admin_router),
    DomainModule(name="auth", router=auth_router),
    DomainModule(name="wallets", router=wallets_router),
    DomainModule(name="players", router=players_router),
    DomainModule(name="clubs", router=clubs_router),
    DomainModule(name="competitions", router=competitions_router),
    DomainModule(name="market", router=market_router),
    DomainModule(name="ingestion", router=ingestion_router),
    DomainModule(name="value_engine", router=value_engine_router),
    DomainModule(name="surveillance", router=surveillance_router),
    DomainModule(name="portfolios", router=portfolios_router),
    DomainModule(name="notifications", router=notifications_router),
    DomainModule(name="realtime", router=realtime_router),
    DomainModule(name="users", router=users_router),
)

__all__ = ["DOMAIN_MODULES"]
