from __future__ import annotations

from fastapi import APIRouter

from backend.app.academy.api.router import router as academy_router
from backend.app.admin.router import router as admin_router
from backend.app.auth.router import router as auth_router
from backend.app.champions_league.api.router import router as champions_league_router
from backend.app.clubs.router import router as clubs_router
from backend.app.club_identity.dynasty.api.router import router as dynasty_router
from backend.app.club_identity.jerseys.router import router as club_identity_router
from backend.app.club_identity.reputation.router import router as club_reputation_router
from backend.app.routes.competitions import router as competitions_router
from backend.app.routes.admin_referrals import router as admin_referrals_router
from backend.app.routes.creators import router as creators_router
from backend.app.routes.referrals import router as referrals_router
from backend.app.routes.admin_clubs import router as admin_clubs_router
from backend.app.routes.admin_club_ops import router as admin_club_ops_router
from backend.app.routes.clubs import router as canonical_clubs_router
from backend.app.routes.club_ops import router as club_ops_router
from backend.app.core.health import router as health_router
from backend.app.core.module import DomainModule
from backend.app.fast_cups.api.router import router as fast_cups_router
from backend.app.ingestion.router import router as ingestion_router
from backend.app.leagues.router import router as leagues_router
from backend.app.market.router import router as market_router
from backend.app.match_engine.api.router import router as match_engine_router
from backend.app.notifications.router import notifications_router
from backend.app.players.router import router as players_router
from backend.app.routes.player_lifecycle import router as player_lifecycle_router
from backend.app.portfolios.router import router as portfolios_router
from backend.app.realtime.router import router as realtime_router
from backend.app.replay_archive.router import router as replay_archive_router
from backend.app.replay_archive.service import ensure_replay_archive
from backend.app.surveillance.router import router as surveillance_router
from backend.app.users.router import router as users_router
from backend.app.value_engine.router import router as value_engine_router
from backend.app.wallets.router import router as wallets_router
from backend.app.world_super_cup.api.router import router as world_super_cup_router


def _with_api_alias(router: APIRouter) -> APIRouter:
    wrapped_router = APIRouter()
    wrapped_router.include_router(router)
    wrapped_router.include_router(router, prefix="/api")
    return wrapped_router


def _initialize_replay_archive(app, _context) -> None:
    ensure_replay_archive(app)


DOMAIN_MODULES = (
    DomainModule(name="health", router=health_router),
    DomainModule(name="admin", router=admin_router),
    DomainModule(name="auth", router=auth_router),
    DomainModule(name="wallets", router=wallets_router),
    DomainModule(name="players", router=players_router),
    DomainModule(name="player_lifecycle", router=player_lifecycle_router),
    DomainModule(name="clubs", router=clubs_router),
    DomainModule(name="canonical_clubs", router=canonical_clubs_router),
    DomainModule(name="admin_clubs", router=admin_clubs_router),
    DomainModule(name="club_ops", router=club_ops_router),
    DomainModule(name="competitions", router=competitions_router),
    DomainModule(name="creators", router=creators_router),
    DomainModule(name="referrals", router=referrals_router),
    DomainModule(name="admin_referrals", router=admin_referrals_router),
    DomainModule(name="market", router=market_router),
    DomainModule(name="ingestion", router=ingestion_router),
    DomainModule(name="value_engine", router=value_engine_router),
    DomainModule(name="surveillance", router=surveillance_router),
    DomainModule(name="portfolios", router=portfolios_router),
    DomainModule(name="leagues", router=leagues_router),
    DomainModule(name="champions_league", router=_with_api_alias(champions_league_router)),
    DomainModule(name="academy", router=_with_api_alias(academy_router)),
    DomainModule(name="world_super_cup", router=_with_api_alias(world_super_cup_router)),
    DomainModule(name="fast_cups", router=_with_api_alias(fast_cups_router)),
    DomainModule(name="match_engine", router=match_engine_router),
    # legacy club_identity routers provide compatibility endpoints while /api/clubs/... remains canonical
    DomainModule(name="club_reputation", router=club_reputation_router),
    DomainModule(name="dynasty", router=dynasty_router),
    DomainModule(name="club_identity", router=club_identity_router),
    DomainModule(name="club_ops_admin", router=admin_club_ops_router),
    DomainModule(
        name="replay_archive",
        router=_with_api_alias(replay_archive_router),
        on_startup=(_initialize_replay_archive,),
    ),
    DomainModule(name="notifications", router=_with_api_alias(notifications_router)),
    DomainModule(name="realtime", router=realtime_router),
    DomainModule(name="users", router=users_router),
)

__all__ = ["DOMAIN_MODULES"]
