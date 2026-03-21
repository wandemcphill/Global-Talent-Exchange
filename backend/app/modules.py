from __future__ import annotations

from fastapi import APIRouter

from app.academy.api.router import router as academy_router
from app.analytics.router import admin_router as analytics_admin_router, router as analytics_router
from app.attachments.router import router as attachments_router
from app.calendar_engine.router import admin_router as calendar_engine_admin_router, router as calendar_engine_router
from app.admin.router import router as admin_router
from app.admin_access.router import router as admin_access_router
from app.admin_godmode.router import router as admin_godmode_router
from app.admin_engine.router import admin_router as admin_engine_admin_router, router as admin_engine_router
from app.economy.router import admin_router as admin_economy_router, router as economy_router
from app.gift_engine.router import router as gift_engine_router
from app.auth.router import router as auth_router
from app.champions_league.api.router import router as champions_league_router
from app.clubs.router import router as clubs_router
from app.club_identity.jerseys.router import router as club_identity_router
from app.routes.competitions import router as competitions_router
from app.routes.admin_referrals import router as admin_referrals_router
from app.routes.creators import router as creators_router
from app.routes.referrals import router as referrals_router
from app.routes.admin_clubs import router as admin_clubs_router
from app.routes.admin_club_ops import router as admin_club_ops_router
from app.routes.clubs import router as canonical_clubs_router
from app.routes.club_ops import router as club_ops_router
from app.core.health import router as health_router
from app.core.module import DomainModule
from app.observability.router import admin_router as ops_admin_router, router as observability_router
from app.fast_cups.api.router import router as fast_cups_router
from app.fan_predictions.router import admin_router as fan_predictions_admin_router, router as fan_predictions_router
from app.fan_wars.router import admin_router as fan_wars_admin_router, router as fan_wars_router
from app.football_events_engine.router import admin_router as football_events_admin_router, router as football_events_router
from app.ingestion.router import router as ingestion_router
from app.leagues.router import router as leagues_router
from app.market.router import router as market_router
from app.manager_market.router import router as manager_market_router
from app.match_engine.api.router import router as match_engine_router
from app.notifications.router import notifications_router
from app.player_cards.router import router as player_cards_router
from app.players.router import router as players_router
from app.policies.router import admin_router as admin_policies_router, router as policies_router
from app.routes.player_lifecycle import router as player_lifecycle_router
from app.portfolios.router import router as portfolios_router
from app.realtime.router import router as realtime_router
from app.reward_engine.router import admin_router as reward_engine_admin_router, router as reward_engine_router
from app.daily_challenge_engine.router import router as daily_challenge_router
from app.hosted_competition_engine.router import admin_router as hosted_competition_admin_router, router as hosted_competition_router
from app.moderation.router import admin_router as moderation_admin_router, router as moderation_router
from app.national_team_engine.router import admin_router as national_team_admin_router, router as national_team_router
from app.story_feed_engine.router import admin_router as story_feed_admin_router, router as story_feed_router
from app.integrity_engine.router import admin_router as integrity_admin_router, router as integrity_router
from app.replay_archive.router import router as replay_archive_router
from app.replay_archive.service import ensure_replay_archive
from app.surveillance.router import router as surveillance_router
from app.users.router import router as users_router
from app.value_engine.router import router as value_engine_router
from app.wallets.router import router as wallets_router
from app.media_engine.router import admin_router as media_engine_admin_router, router as media_engine_router
from app.club_infra_engine.router import admin_router as club_infra_admin_router, router as club_infra_router
from app.community_engine.router import router as community_engine_router
from app.club_social.router import router as club_social_router
from app.discovery_engine.router import admin_router as discovery_admin_router, router as discovery_router
from app.player_import_engine.router import admin_router as player_import_admin_router, router as player_import_router
from app.risk_ops_engine.router import admin_router as risk_ops_admin_router, router as risk_ops_router
from app.sponsorship_engine.router import admin_router as sponsorship_admin_router, router as sponsorship_router
from app.creator_campaign_engine.router import admin_router as creator_campaign_admin_router, router as creator_campaign_router
from app.governance_engine.router import admin_router as governance_admin_router, router as governance_router
from app.dispute_engine.router import admin_router as dispute_admin_router, router as dispute_router
from app.streamer_tournament_engine.router import admin_router as streamer_tournament_admin_router, router as streamer_tournament_router
from app.world_simulation.router import admin_router as world_simulation_admin_router, router as world_simulation_router
from app.world_super_cup.api.router import router as world_super_cup_router
from app.treasury.router import router as treasury_router
from app.integrations.payments.router import router as payments_router


def _with_api_alias(router: APIRouter) -> APIRouter:
    wrapped_router = APIRouter()
    wrapped_router.include_router(router)
    wrapped_router.include_router(router, prefix="/api")
    return wrapped_router


def _initialize_replay_archive(app, _context) -> None:
    ensure_replay_archive(app)


def _seed_policy_documents(app, context) -> None:
    with context.database.session_factory() as session:
        from app.policies.service import PolicyService

        service = PolicyService(session)
        service.seed_defaults()
        session.commit()




def _seed_economy_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.economy.service import EconomyConfigService

        service = EconomyConfigService(session)
        service.seed_defaults()
        session.commit()




def _seed_calendar_engine_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.calendar_engine.service import CalendarEngineService

        service = CalendarEngineService(session)
        service.seed_defaults()
        session.commit()


def _seed_daily_challenges(app, context) -> None:
    with context.database.session_factory() as session:
        from app.daily_challenge_engine.service import DailyChallengeService

        service = DailyChallengeService(session)
        service.seed_defaults()
        session.commit()


def _seed_hosted_competitions(app, context) -> None:
    with context.database.session_factory() as session:
        from app.hosted_competition_engine.service import HostedCompetitionService

        service = HostedCompetitionService(session)
        service.seed_defaults()
        session.commit()

def _seed_discovery_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.discovery_engine.service import DiscoveryEngineService

        service = DiscoveryEngineService(session)
        service.seed_defaults()
        session.commit()




def _seed_sponsorship_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.sponsorship_engine.service import SponsorshipEngineService

        service = SponsorshipEngineService(session)
        service.seed_defaults()
        session.commit()

def _seed_admin_engine_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.admin_engine.service import AdminEngineService

        service = AdminEngineService(session)
        service.seed_defaults()
        session.commit()


def _seed_football_event_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.football_events_engine.service import RealWorldFootballEventService

        service = RealWorldFootballEventService(session)
        service.seed_defaults()
        session.commit()


def _seed_world_simulation_defaults(app, context) -> None:
    with context.database.session_factory() as session:
        from app.world_simulation.service import FootballWorldService

        service = FootballWorldService(session)
        service.seed_defaults()
        session.commit()


DOMAIN_MODULES = (
    DomainModule(name="health", router=health_router),
    DomainModule(name="observability", router=observability_router),
    DomainModule(name="admin_ops", router=ops_admin_router),
    DomainModule(name="admin", router=admin_router),
    DomainModule(name="admin_access", router=admin_access_router),
    DomainModule(name="admin_godmode", router=admin_godmode_router),
    DomainModule(name="admin_engine", router=admin_engine_router, on_startup=(_seed_admin_engine_defaults,)),
    DomainModule(name="admin_engine_admin", router=admin_engine_admin_router),
    DomainModule(name="economy", router=economy_router, on_startup=(_seed_economy_defaults,)),
    DomainModule(name="economy_admin", router=admin_economy_router),
    DomainModule(name="gift_engine", router=gift_engine_router),
    DomainModule(name="reward_engine", router=reward_engine_router),
    DomainModule(name="reward_engine_admin", router=reward_engine_admin_router),
    DomainModule(name="fan_predictions", router=fan_predictions_router),
    DomainModule(name="fan_predictions_admin", router=fan_predictions_admin_router),
    DomainModule(name="fan_wars", router=fan_wars_router),
    DomainModule(name="fan_wars_admin", router=fan_wars_admin_router),
    DomainModule(name="daily_challenge_engine", router=daily_challenge_router, on_startup=(_seed_daily_challenges,)),
    DomainModule(name="hosted_competition_engine", router=hosted_competition_router, on_startup=(_seed_hosted_competitions,)),
    DomainModule(name="hosted_competition_engine_admin", router=hosted_competition_admin_router),
    DomainModule(name="moderation", router=moderation_router),
    DomainModule(name="moderation_admin", router=moderation_admin_router),
    DomainModule(name="national_team_engine", router=national_team_router),
    DomainModule(name="national_team_engine_admin", router=national_team_admin_router),
    DomainModule(name="story_feed_engine", router=story_feed_router),
    DomainModule(name="story_feed_engine_admin", router=story_feed_admin_router),
    DomainModule(name="integrity_engine", router=integrity_router),
    DomainModule(name="integrity_engine_admin", router=integrity_admin_router),
    DomainModule(name="auth", router=auth_router),
    DomainModule(name="wallets", router=wallets_router),
    DomainModule(name="payments", router=payments_router),
    DomainModule(name="media_engine", router=media_engine_router),
    DomainModule(name="media_engine_admin", router=media_engine_admin_router),
    DomainModule(name="club_infra", router=club_infra_router),
    DomainModule(name="club_infra_admin", router=club_infra_admin_router),
    DomainModule(name="player_import", router=player_import_router),
    DomainModule(name="community_engine", router=community_engine_router),
    DomainModule(name="club_social", router=club_social_router),
    DomainModule(name="world_simulation", router=world_simulation_router, on_startup=(_seed_world_simulation_defaults,)),
    DomainModule(name="world_simulation_admin", router=world_simulation_admin_router),
    DomainModule(name="discovery_engine", router=discovery_router, on_startup=(_seed_discovery_defaults,)),
    DomainModule(name="discovery_engine_admin", router=discovery_admin_router),
    DomainModule(name="player_import_admin", router=player_import_admin_router),
    DomainModule(name="risk_ops_engine", router=risk_ops_router),
    DomainModule(name="risk_ops_engine_admin", router=risk_ops_admin_router),
    DomainModule(name="sponsorship_engine", router=sponsorship_router, on_startup=(_seed_sponsorship_defaults,)),
    DomainModule(name="sponsorship_engine_admin", router=sponsorship_admin_router),
    DomainModule(name="creator_campaign_engine", router=creator_campaign_router),
    DomainModule(name="creator_campaign_engine_admin", router=creator_campaign_admin_router),
    DomainModule(name="governance_engine", router=governance_router),
    DomainModule(name="governance_engine_admin", router=governance_admin_router),
    DomainModule(name="dispute_engine", router=dispute_router),
    DomainModule(name="dispute_engine_admin", router=dispute_admin_router),
    DomainModule(name="streamer_tournament_engine", router=streamer_tournament_router),
    DomainModule(name="streamer_tournament_engine_admin", router=streamer_tournament_admin_router),
    DomainModule(name="policies", router=policies_router, on_startup=(_seed_policy_documents,)),
    DomainModule(name="admin_policies", router=admin_policies_router),
    DomainModule(name="treasury", router=treasury_router),
    DomainModule(name="calendar_engine", router=calendar_engine_router, on_startup=(_seed_calendar_engine_defaults,)),
    DomainModule(name="calendar_engine_admin", router=calendar_engine_admin_router),
    DomainModule(name="attachments", router=attachments_router),
    DomainModule(name="analytics", router=analytics_router),
    DomainModule(name="admin_analytics", router=analytics_admin_router),
    DomainModule(name="players", router=players_router),
    DomainModule(name="player_lifecycle", router=player_lifecycle_router),
    DomainModule(name="football_events", router=football_events_router, on_startup=(_seed_football_event_defaults,)),
    DomainModule(name="football_events_admin", router=football_events_admin_router),
    DomainModule(name="clubs", router=clubs_router),
    DomainModule(name="canonical_clubs", router=canonical_clubs_router),
    DomainModule(name="admin_clubs", router=admin_clubs_router),
    DomainModule(name="club_ops", router=club_ops_router),
    DomainModule(name="competitions", router=competitions_router),
    DomainModule(name="creators", router=creators_router),
    DomainModule(name="referrals", router=referrals_router),
    DomainModule(name="admin_referrals", router=admin_referrals_router),
    DomainModule(name="market", router=market_router),
    DomainModule(name="manager_market", router=manager_market_router),
    DomainModule(name="player_cards", router=player_cards_router),
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
