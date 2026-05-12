from __future__ import annotations

import logging
from threading import RLock
from time import perf_counter

from fastapi import APIRouter, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.module import DomainModule, register_domain_modules

logger = logging.getLogger(__name__)
CORE_BOOT_PATHS = frozenset({"/health", "/ready", "/version", "/diagnostics", "/metrics"})
LAZY_HYDRATION_BYPASS_PREFIXES = (
    "/auth",
    "/api/auth",
    "/api/session",
    "/api/broadcast",
    "/api/competitions",
    "/api/admin/competitions",
    "/api/hosted-competitions",
    "/api/admin/hosted-competitions",
    "/api/match",
    "/api/match-viewer",
    "/api/matches",
    "/api/streamer-tournaments",
    "/api/admin/streamer-tournaments",
    "/api/v2/hosted-competitions",
    "/api/v2/admin/hosted-competitions",
    "/api/v2/streamer-tournaments",
    "/api/v2/admin/streamer-tournaments",
    "/hosted-competitions",
    "/match",
    "/matches",
    "/streamer-tournaments",
    "/admin/streamer-tournaments",
)
EAGER_MODULE_NAMES = frozenset(
    {
        "auth",
        "broadcast_network",
        "realtime",
        "competitions",
        "hosted_competition_engine",
        "live_matches",
        "matches",
        "broadcast",
        "manager_market",
        "match_viewer",
        "hosted_competition_engine_admin",
        "streamer_tournament_engine",
        "world_simulation",
    }
)


def _path_matches_prefix(path: str, prefix: str) -> bool:
    return path == prefix or path.startswith(f"{prefix}/")


def _should_bypass_lazy_hydration(path: str) -> bool:
    return any(_path_matches_prefix(path, prefix) for prefix in LAZY_HYDRATION_BYPASS_PREFIXES)


def _with_api_alias(router: APIRouter) -> APIRouter:
    wrapped_router = APIRouter()
    wrapped_router.include_router(router)
    wrapped_router.include_router(router, prefix="/api")
    return wrapped_router


def _with_api_only(router: APIRouter) -> APIRouter:
    wrapped_router = APIRouter()
    wrapped_router.include_router(router, prefix="/api")
    return wrapped_router


def _module(
    name: str,
    *,
    router_path: str | None = None,
    with_api_alias: bool = False,
    api_only: bool = False,
    on_startup: tuple[object, ...] = (),
    on_shutdown: tuple[object, ...] = (),
) -> DomainModule:
    if with_api_alias and api_only:
        raise ValueError(f"Module '{name}' cannot be both with_api_alias and api_only.")
    return DomainModule(
        name=name,
        router_path=router_path,
        router_transform=(_with_api_alias if with_api_alias else _with_api_only if api_only else None),
        on_startup=on_startup,
        on_shutdown=on_shutdown,
    )


def register_modules(app: FastAPI, modules: tuple[DomainModule, ...] | None = None) -> tuple[DomainModule, ...]:
    resolved_modules = DOMAIN_MODULES if modules is None else modules
    eager_modules = tuple(module for module in resolved_modules if module.name in EAGER_MODULE_NAMES)
    started_at = perf_counter()
    if eager_modules:
        register_domain_modules(app, eager_modules)
    duration_seconds = perf_counter() - started_at
    app.state.module_specs = resolved_modules
    app.state.eager_module_names = tuple(module.name for module in eager_modules)
    app.state.domain_modules = tuple(module.name for module in resolved_modules)
    app.state.module_load_seconds = duration_seconds
    app.state.module_hydration_seconds = 0.0
    app.state.modules_hydrated = False
    app.state.module_loader_lock = getattr(app.state, "module_loader_lock", RLock())
    if not getattr(app.state, "module_loader_middleware_added", False):
        app.add_middleware(LazyModuleMiddleware)
        app.state.module_loader_middleware_added = True
    _install_openapi_loader(app)
    logger.info(
        "app.modules.register.complete module_count=%s duration_ms=%.2f",
        len(resolved_modules),
        duration_seconds * 1000,
    )
    return resolved_modules


def ensure_modules_loaded(app: FastAPI) -> None:
    if getattr(app.state, "modules_hydrated", False):
        return
    lock = app.state.module_loader_lock
    with lock:
        if getattr(app.state, "modules_hydrated", False):
            return
        started_at = perf_counter()
        _install_lazy_dependency_overrides(app)
        eager_module_names = set(getattr(app.state, "eager_module_names", ()))
        lazy_modules = tuple(
            module
            for module in getattr(app.state, "module_specs", DOMAIN_MODULES)
            if getattr(module, "name", None) not in eager_module_names
        )
        register_domain_modules(app, lazy_modules)
        duration_seconds = perf_counter() - started_at
        app.state.modules_hydrated = True
        app.state.module_hydration_seconds = duration_seconds
        app.openapi_schema = None
        logger.info(
            "app.modules.hydrate.complete module_count=%s duration_ms=%.2f",
            len(getattr(app.state, "module_specs", DOMAIN_MODULES)),
            duration_seconds * 1000,
        )
        if duration_seconds > 2:
            logger.warning("app.modules.hydrate.slow duration_seconds=%.3f", duration_seconds)


def _install_openapi_loader(app: FastAPI) -> None:
    if getattr(app.state, "module_openapi_loader_installed", False):
        return
    original_openapi = app.openapi

    def _lazy_openapi():
        ensure_modules_loaded(app)
        return original_openapi()

    app.openapi = _lazy_openapi
    app.state.module_openapi_loader_installed = True


def _install_lazy_dependency_overrides(app: FastAPI) -> None:
    if getattr(app.state, "module_dependency_overrides_installed", False):
        return
    from app.auth.dependencies import get_session as auth_get_session

    app.dependency_overrides[auth_get_session] = app.state.container.database.get_session
    app.state.module_dependency_overrides_installed = True


class LazyModuleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if _should_bypass_lazy_hydration(path):
            logger.info(
                "auth.request.entry method=%s path=%s modules_hydrated=%s lazy_hydration_bypassed=true",
                request.method,
                path,
                getattr(request.app.state, "modules_hydrated", False),
            )
        elif path not in CORE_BOOT_PATHS and not path.startswith("/tts"):
            ensure_modules_loaded(request.app)
        return await call_next(request)


def _initialize_replay_archive(app, _context) -> None:
    from app.replay_archive.service import ensure_replay_archive

    ensure_replay_archive(app)


def _initialize_manager_market(app, context) -> None:
    from app.manager_market.seed_catalog import CATALOG_VERSION as MANAGER_MARKET_CATALOG_VERSION
    from app.manager_market.service import ManagerMarketService
    from app.wallets.service import WalletService

    if not context.settings.run_startup_seeding:
        logger.info("app.startup.seed.skipped seed=%s reason=disabled", "manager_market_catalog")
        return

    logger.info("app.startup.seed.begin seed=%s", "manager_market_catalog")
    service = ManagerMarketService(wallet_service=WalletService())
    with context.database.session_factory() as session:
        service._bootstrap_db(app, session)
        session.commit()
    app.state.manager_market_catalog_version = MANAGER_MARKET_CATALOG_VERSION
    logger.info("app.startup.seed.complete seed=%s", "manager_market_catalog")


def _run_startup_seed(context, *, seed_name: str, seed_action) -> None:
    if not context.settings.run_startup_seeding:
        logger.info("app.startup.seed.skipped seed=%s reason=disabled", seed_name)
        return
    environment = str(context.settings.environment).strip().lower()
    if environment != "local":
        logger.info(
            "app.startup.seed.skipped seed=%s environment=%s",
            seed_name,
            context.settings.environment,
        )
        return
    logger.info("app.startup.seed.begin seed=%s", seed_name)
    seed_action()
    logger.info("app.startup.seed.complete seed=%s", seed_name)


def _seed_policy_documents(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.policies.service import PolicyService

            service = PolicyService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="policy_documents", seed_action=_seed)


def _seed_economy_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.economy.service import EconomyConfigService

            service = EconomyConfigService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="economy_defaults", seed_action=_seed)


def _seed_calendar_engine_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.calendar_engine.service import CalendarEngineService

            service = CalendarEngineService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="calendar_engine_defaults", seed_action=_seed)


def _seed_daily_challenges(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.daily_challenge_engine.service import DailyChallengeService

            service = DailyChallengeService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="daily_challenges", seed_action=_seed)


def _seed_history_engagement_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.history_engagement.service import HistoryEngagementService

            service = HistoryEngagementService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="history_engagement_defaults", seed_action=_seed)


def _seed_hosted_competitions(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.hosted_competition_engine.service import HostedCompetitionService

            service = HostedCompetitionService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="hosted_competitions", seed_action=_seed)


def _seed_discovery_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.discovery_engine.service import DiscoveryEngineService

            service = DiscoveryEngineService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="discovery_defaults", seed_action=_seed)


def _seed_sponsorship_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.sponsorship_engine.service import SponsorshipEngineService

            service = SponsorshipEngineService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="sponsorship_defaults", seed_action=_seed)


def _seed_club_growth_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.club_growth.service import ClubGrowthService

            service = ClubGrowthService(session)
            service.seed_staff_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="club_growth_defaults", seed_action=_seed)


def _seed_engagement_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.club_finance.service import ClubFinanceService
            from app.live_ops.service import LiveOpsService

            ClubFinanceService(session).seed_defaults()
            LiveOpsService(session).seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="engagement_defaults", seed_action=_seed)


def _seed_commentary_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.commentary.service import CommentaryService

            service = CommentaryService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="commentary_defaults", seed_action=_seed)


def _seed_admin_engine_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.admin_engine.service import AdminEngineService

            service = AdminEngineService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="admin_engine_defaults", seed_action=_seed)


def _seed_football_event_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.football_events_engine.service import RealWorldFootballEventService

            service = RealWorldFootballEventService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="football_event_defaults", seed_action=_seed)


def _seed_world_simulation_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.world_simulation.service import FootballWorldService

            service = FootballWorldService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="world_simulation_defaults", seed_action=_seed)


def _seed_regen_universe_defaults(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.regen_universe.service import RegenUniverseService

            service = RegenUniverseService(session)
            service.seed_defaults()
            session.commit()

    _run_startup_seed(context, seed_name="regen_universe_defaults", seed_action=_seed)


def _seed_regen_universe_preseeded_national_pool(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.regen_universe.expansion_service import (
                RegenUniverseExpansionService,
                RegenUniverseExpansionValidationError,
            )

            service = RegenUniverseExpansionService(session)
            try:
                service.seed_preseeded_national_regens(age_band="senior", preseed_batch="system_start")
            except RegenUniverseExpansionValidationError as exc:
                if str(exc) != "preseed_countries_not_found":
                    raise
            session.commit()

    _run_startup_seed(context, seed_name="regen_universe_preseeded_national_pool", seed_action=_seed)


def _seed_regen_universe_preseeded_national_u17_pool(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.regen_universe.expansion_service import (
                RegenUniverseExpansionService,
                RegenUniverseExpansionValidationError,
            )

            service = RegenUniverseExpansionService(session)
            try:
                service.seed_preseeded_national_regens(
                    age_band="u17",
                    preseed_batch="u17_batch",
                )
            except RegenUniverseExpansionValidationError as exc:
                if str(exc) != "preseed_countries_not_found":
                    raise
            session.commit()

    _run_startup_seed(context, seed_name="regen_universe_preseeded_national_u17_pool", seed_action=_seed)


def _seed_regen_universe_preseeded_national_u20_pool(app, context) -> None:
    def _seed() -> None:
        with context.database.session_factory() as session:
            from app.regen_universe.expansion_service import (
                RegenUniverseExpansionService,
                RegenUniverseExpansionValidationError,
            )

            service = RegenUniverseExpansionService(session)
            try:
                service.seed_preseeded_national_regens(
                    age_band="u20",
                    preseed_batch="u20_batch",
                )
            except RegenUniverseExpansionValidationError as exc:
                if str(exc) != "preseed_countries_not_found":
                    raise
            session.commit()

    _run_startup_seed(context, seed_name="regen_universe_preseeded_national_u20_pool", seed_action=_seed)


DOMAIN_MODULES = (
    _module("health"),
    _module("observability", router_path="app.observability.router:router"),
    _module("admin_ops", router_path="app.observability.router:admin_router"),
    _module("admin", router_path="app.admin.router:router"),
    _module("admin_access", router_path="app.admin_access.router:router"),
    _module("admin_finance", router_path="app.admin_finance.router:router"),
    _module("admin_godmode", router_path="app.admin_godmode.router:router"),
    _module(
        "admin_engine",
        router_path="app.admin_engine.router:router",
        on_startup=(_seed_admin_engine_defaults,),
    ),
    _module("admin_engine_admin", router_path="app.admin_engine.router:admin_router"),
    _module("launch_control", router_path="app.launch_control.router:router", api_only=True),
    _module("runtime_config", router_path="app.runtime_config.router:router"),
    _module("ai_manager", router_path="app.ai_manager.router:router"),
    _module(
        "economy",
        router_path="app.economy.router:router",
        on_startup=(_seed_economy_defaults,),
    ),
    _module("economy_admin", router_path="app.economy.router:admin_router"),
    _module("gift_engine", router_path="app.gift_engine.router:router", api_only=True),
    _module("reward_engine", router_path="app.reward_engine.router:router", api_only=True),
    _module(
        "reward_engine_admin",
        router_path="app.reward_engine.router:admin_router",
        api_only=True,
    ),
    _module("fan_predictions", router_path="app.fan_predictions.router:router"),
    _module("fan_predictions_admin", router_path="app.fan_predictions.router:admin_router"),
    _module("predictions", router_path="app.predictions.router:router", with_api_alias=True),
    _module("fan_wars", router_path="app.fan_wars.router:router", api_only=True),
    _module("fan_wars_admin", router_path="app.fan_wars.router:admin_router", api_only=True),
    _module(
        "daily_challenge_engine",
        router_path="app.daily_challenge_engine.router:router",
        api_only=True,
        on_startup=(_seed_daily_challenges,),
    ),
    _module(
        "hosted_competition_engine",
        router_path="app.hosted_competition_engine.router:router",
        api_only=True,
        on_startup=(_seed_hosted_competitions,),
    ),
    _module(
        "hosted_competition_engine_admin",
        router_path="app.hosted_competition_engine.router:admin_router",
        api_only=True,
    ),
    _module("moderation", router_path="app.moderation.router:router", api_only=True),
    _module("moderation_admin", router_path="app.moderation.router:admin_router", api_only=True),
    _module(
        "national_team_engine",
        router_path="app.national_team_engine.router:router",
        api_only=True,
    ),
    _module(
        "national_team_engine_admin",
        router_path="app.national_team_engine.router:admin_router",
        api_only=True,
    ),
    _module(
        "story_feed_engine",
        router_path="app.story_feed_engine.router:router",
        api_only=True,
    ),
    _module(
        "story_feed_engine_admin",
        router_path="app.story_feed_engine.router:admin_router",
        api_only=True,
    ),
    _module(
        "ai_reporter",
        router_path="app.ai_reporter.router:router",
        api_only=True,
        on_startup=("app.ai_reporter.worker:bind_ai_reporter_scheduler",),
        on_shutdown=("app.ai_reporter.worker:shutdown_ai_reporter_scheduler",),
    ),
    _module(
        "gtex_news_engine",
        router_path="app.news_engine.router:router",
        api_only=True,
        on_startup=("app.news_engine.worker:bind_gtex_news_scheduler",),
        on_shutdown=("app.news_engine.worker:shutdown_gtex_news_scheduler",),
    ),
    _module("legend_layer", router_path="app.legend_layer.router:router"),
    _module(
        "viral",
        router_path="app.viral.router:router",
        on_startup=("app.viral.router:startup",),
        on_shutdown=("app.viral.router:shutdown",),
    ),
    _module("attention_orchestrator", router_path="app.orchestrator.router:router"),
    _module(
        "agents",
        router_path="app.agents.router:router",
        on_startup=("app.agents.agent_manager:bind_creator_agent_manager",),
        on_shutdown=("app.agents.agent_manager:shutdown_creator_agent_manager",),
    ),
    _module("pundits", router_path="app.pundits.router:router"),
    _module("betting", router_path="app.betting.router:router"),
    _module("integrity_engine", router_path="app.integrity_engine.router:router", api_only=True),
    _module(
        "integrity_engine_admin",
        router_path="app.integrity_engine.router:admin_router",
        api_only=True,
    ),
    _module("auth", router_path="app.auth.router:router"),
    _module(
        "api_v1",
        router_path="app.api_v1.router:router",
        on_startup=("app.api_v1.router:install_exception_handlers",),
    ),
    _module("jobs_api", router_path="app.jobs.router:router"),
    _module("organizations", router_path="app.access_control.router:router"),
    _module("wallets", router_path="app.wallets.router:router"),
    _module("coin_traders", router_path="app.coin_traders.router:router"),
    _module("admin_coin_traders", router_path="app.coin_traders.router:admin_router"),
    _module("paystack_webhooks", router_path="app.admin_finance.router:webhook_router"),
    _module("payments", router_path="app.integrations.payments.router:router"),
    _module("media_engine", router_path="app.media_engine.router:router"),
    _module("media_engine_admin", router_path="app.media_engine.router:admin_router"),
    _module("broadcast_rights", router_path="app.broadcast_rights.router:router", with_api_alias=True),
    _module("broadcast_rights_admin", router_path="app.broadcast_rights.router:admin_router"),
    _module("club_infra", router_path="app.club_infra_engine.router:router"),
    _module("club_infra_admin", router_path="app.club_infra_engine.router:admin_router"),
    _module("club_ownership", router_path="app.club_ownership.router:router"),
    _module("player_import", router_path="app.player_import_engine.router:router"),
    _module("community_engine", router_path="app.community_engine.router:router", api_only=True),
    _module(
        "history_engagement",
        router_path="app.history_engagement.router:router",
        on_startup=(
            _seed_history_engagement_defaults,
            "app.history_engagement.worker:bind_history_engagement_scheduler",
        ),
        on_shutdown=("app.history_engagement.worker:shutdown_history_engagement_scheduler",),
    ),
    _module("history_engagement_admin", router_path="app.history_engagement.router:admin_router"),
    _module("club_social", router_path="app.club_social.router:router"),
    _module(
        "leaderboards",
        router_path="app.leaderboards.router:router",
        on_startup=("app.leaderboards.leaderboard_worker:bind_leaderboard_worker",),
        on_shutdown=("app.leaderboards.leaderboard_worker:shutdown_leaderboard_worker",),
    ),
    _module("leaderboards_admin", router_path="app.leaderboards.router:admin_router"),
    _module(
        "world_simulation",
        router_path="app.world_simulation.router:router",
        on_startup=(_seed_world_simulation_defaults,),
    ),
    _module(
        "world_simulation_admin",
        router_path="app.world_simulation.router:admin_router",
        api_only=True,
    ),
    _module(
        "discovery_engine",
        router_path="app.discovery_engine.router:router",
        api_only=True,
        on_startup=(_seed_discovery_defaults,),
    ),
    _module(
        "discovery_engine_admin",
        router_path="app.discovery_engine.router:admin_router",
        api_only=True,
    ),
    _module("global_search", router_path="app.global_search.router:router", api_only=True),
    _module("matchday_economy", router_path="app.matchday_economy.router:router", api_only=True),
    _module("operations_readiness", router_path="app.operations_readiness.router:router", api_only=True),
    _module("player_import_admin", router_path="app.player_import_engine.router:admin_router"),
    _module("risk_ops_engine", router_path="app.risk_ops_engine.router:router"),
    _module("risk_ops_engine_admin", router_path="app.risk_ops_engine.router:admin_router"),
    _module(
        "sponsorship_engine",
        router_path="app.sponsorship_engine.router:router",
        api_only=True,
        on_startup=(_seed_sponsorship_defaults,),
    ),
    _module(
        "sponsorship_engine_admin",
        router_path="app.sponsorship_engine.router:admin_router",
        api_only=True,
    ),
    _module("ads_engine", router_path="app.ads_engine.router:router"),
    _module(
        "club_finance",
        router_path="app.club_finance.router:router",
        with_api_alias=True,
        on_startup=(_seed_engagement_defaults,),
    ),
    _module("ownership_groups", router_path="app.ownership_groups.router:router", with_api_alias=True),
    _module("ownership_groups_admin", router_path="app.ownership_groups.router:admin_router"),
    _module("live_ops", router_path="app.live_ops.router:router", with_api_alias=True),
    _module("creator_campaign_engine", router_path="app.creator_campaign_engine.router:router"),
    _module("creator_campaign_engine_admin", router_path="app.creator_campaign_engine.router:admin_router"),
    _module("creator_marketplace", router_path="app.creator_marketplace.router:router", with_api_alias=True),
    _module("governance_engine", router_path="app.governance_engine.router:router", api_only=True),
    _module("governance_engine_admin", router_path="app.governance_engine.router:admin_router", api_only=True),
    _module(
        "real_world_hub",
        router_path="app.real_world_hub.router:router",
        on_startup=("app.real_world_hub.worker:bind_real_world_hub_scheduler",),
        on_shutdown=("app.real_world_hub.worker:shutdown_real_world_hub_scheduler",),
    ),
    _module("real_world_hub_admin", router_path="app.real_world_hub.router:admin_router"),
    _module(
        "federations",
        router_path="app.federations.router:router",
        api_only=True,
        on_startup=("app.federations.worker:bind_federation_scheduler",),
        on_shutdown=("app.federations.worker:shutdown_federation_scheduler",),
    ),
    _module(
        "federations_admin",
        router_path="app.federations.router:admin_router",
        api_only=True,
    ),
    _module("dispute_engine", router_path="app.dispute_engine.router:router"),
    _module("dispute_engine_admin", router_path="app.dispute_engine.router:admin_router"),
    _module(
        "streamer_tournament_engine",
        router_path="app.streamer_tournament_engine.router:router",
        api_only=True,
    ),
    _module(
        "streamer_tournament_engine_admin",
        router_path="app.streamer_tournament_engine.router:admin_router",
        api_only=True,
    ),
    _module("policies", router_path="app.policies.router:router", on_startup=(_seed_policy_documents,)),
    _module("admin_policies", router_path="app.policies.router:admin_router"),
    _module("treasury", router_path="app.treasury.router:router"),
    _module(
        "calendar_engine",
        router_path="app.calendar_engine.router:router",
        api_only=True,
        on_startup=(_seed_calendar_engine_defaults,),
    ),
    _module(
        "calendar_engine_admin",
        router_path="app.calendar_engine.router:admin_router",
        api_only=True,
    ),
    _module("attachments", router_path="app.attachments.router:router"),
    _module("analytics", router_path="app.analytics.router:router"),
    _module("admin_analytics", router_path="app.analytics.router:admin_router"),
    _module("public_analytics", router_path="app.analytics.router:public_router"),
    _module("players", router_path="app.players.router:router"),
    _module("global_memory", router_path="app.global_memory.router:router"),
    _module("awards", router_path="app.awards.router:router", with_api_alias=True),
    _module("platform_experience", router_path="app.platform_experience.router:router"),
    _module("regen_ecosystem", router_path="app.regen_ecosystem.router:router", with_api_alias=True),
    _module("regen_creation", router_path="app.regen_creation.router:router", with_api_alias=True),
    _module(
        "regen_universe",
        router_path="app.regen_universe.router:router",
        with_api_alias=True,
        on_startup=(
            _seed_regen_universe_defaults,
            _seed_regen_universe_preseeded_national_pool,
            _seed_regen_universe_preseeded_national_u17_pool,
            _seed_regen_universe_preseeded_national_u20_pool,
        ),
    ),
    _module("regen_universe_admin", router_path="app.regen_universe.router:admin_router"),
    _module("player_lifecycle", router_path="app.routes.player_lifecycle:router"),
    _module("player_agency", router_path="app.routes.player_agency:router"),
    _module("transfer_market", router_path="app.transfer_market.router:router"),
    _module(
        "football_events",
        router_path="app.football_events_engine.router:router",
        on_startup=(_seed_football_event_defaults,),
    ),
    _module("football_events_admin", router_path="app.football_events_engine.router:admin_router"),
    _module(
        "broadcast_network",
        router_path="app.broadcast_network.router:router",
        on_startup=("app.broadcast_network.service:bind_broadcast_network_runtime",),
        on_shutdown=("app.broadcast_network.service:shutdown_broadcast_network_runtime",),
    ),
    _module("football_universe", router_path="app.football_universe.router:router", with_api_alias=True),
    _module("clubs", router_path="app.clubs.router:router"),
    _module("canonical_clubs", router_path="app.routes.clubs:router"),
    _module("club_lifecycle", router_path="app.club_lifecycle.router:router", api_only=True),
    _module(
        "club_growth",
        router_path="app.club_growth.router:router",
        api_only=True,
        on_startup=(_seed_club_growth_defaults,),
    ),
    _module("admin_clubs", router_path="app.routes.admin_clubs:router"),
    _module("club_ops", router_path="app.routes.club_ops:router"),
    _module("competitions", router_path="app.routes.competitions:router"),
    _module("tournaments", router_path="app.tournaments.router:router"),
    _module("creators", router_path="app.routes.creators:router"),
    _module("referrals", router_path="app.routes.referrals:router"),
    _module("admin_referrals", router_path="app.routes.admin_referrals:router"),
    _module("market", router_path="app.market.router:router"),
    _module("marketplace", router_path="app.marketplace.router:router"),
    _module("manager_duels", router_path="app.manager_duels.router:router"),
    _module(
        "manager_market",
        router_path="app.manager_market.router:router",
        on_startup=(_initialize_manager_market,),
    ),
    _module("manager_marketplace", router_path="app.manager_marketplace.router:router"),
    _module("player_cards", router_path="app.player_cards.router:router"),
    _module("ingestion", router_path="app.ingestion.router:router"),
    _module("value_engine", router_path="app.value_engine.router:router"),
    _module("surveillance", router_path="app.surveillance.router:router"),
    _module("portfolios", router_path="app.portfolios.router:router"),
    _module("leagues", router_path="app.leagues.router:router"),
    _module("champions_league", router_path="app.champions_league.api.router:router", with_api_alias=True),
    _module("academy", router_path="app.academy.api.router:router", with_api_alias=True),
    _module("world_super_cup", router_path="app.world_super_cup.api.router:router", with_api_alias=True),
    _module("fast_cups", router_path="app.fast_cups.api.router:router", with_api_alias=True),
    _module(
        "commentary",
        router_path="app.commentary.router:router",
        on_startup=(_seed_commentary_defaults,),
    ),
    _module("live_matches", router_path="app.live_matches.router:router"),
    _module(
        "ticketing",
        router_path="app.ticketing.router:router",
        with_api_alias=True,
        on_startup=("app.ticketing.runtime:bind_ticketing_runtime",),
    ),
    _module(
        "infinite_league",
        router_path="app.infinite_league.router:router",
        with_api_alias=True,
        on_startup=("app.infinite_league.service:bind_infinite_league_runtime",),
        on_shutdown=("app.infinite_league.service:shutdown_infinite_league_runtime",),
    ),
    _module("match_engine", router_path="app.match_engine.api.router:router"),
    _module(
        "highlight_render",
        on_startup=("app.highlights.worker:bind_highlight_render_worker",),
        on_shutdown=("app.highlights.worker:shutdown_highlight_render_worker",),
    ),
    _module(
        "moments",
        router_path="app.moments.router:router",
        on_startup=("app.moments.service:bind_moments_engine",),
        on_shutdown=("app.moments.service:shutdown_moments_engine",),
    ),
    _module("matches", router_path="app.matches.router:router", with_api_alias=True),
    _module("simulation_matchmaking", router_path="app.simulation_matchmaking.router:router"),
    _module("ultimate_league", router_path="app.ultimate_league.router:router"),
    _module(
        "competitive_integrity",
        router_path="app.competitive_integrity.router:router",
        on_startup=("app.competitive_integrity.worker:bind_competitive_integrity_scheduler",),
        on_shutdown=("app.competitive_integrity.worker:shutdown_competitive_integrity_scheduler",),
    ),
    _module("match_viewer", router_path="app.routes.match_viewer:router", api_only=True),
    _module("club_identity", router_path="app.club_identity.jerseys.router:router"),
    _module("club_ops_admin", router_path="app.routes.admin_club_ops:router"),
    _module(
        "replay_archive",
        router_path="app.replay_archive.router:router",
        with_api_alias=True,
        on_startup=(_initialize_replay_archive,),
    ),
    _module("notifications", router_path="app.notifications.router:notifications_router", api_only=True),
    _module(
        "notifications_admin",
        router_path="app.notifications.router:admin_router",
        api_only=True,
    ),
    _module(
        "broadcast",
        router_path="app.broadcast.spectator_gateway:router",
        on_startup=("app.broadcast.spectator_gateway:install_broadcast_runtime",),
        on_shutdown=("app.broadcast.spectator_gateway:shutdown_broadcast_runtime",),
    ),
    _module(
        "gtex",
        router_path="app.gtex.router:router",
        on_startup=("app.gtex.runtime:bind_gtex_runtime",),
        on_shutdown=("app.gtex.runtime:shutdown_gtex_runtime",),
    ),
    _module("gtex_universe", router_path="app.gtex_universe.router:router"),
    _module("realtime", router_path="app.realtime.router:router"),
    _module("users", router_path="app.users.router:router"),
)


__all__ = ["DOMAIN_MODULES", "register_modules"]
