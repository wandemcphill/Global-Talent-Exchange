from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import sessionmaker

from app.broadcast_rights.service import BroadcastRightsService
from app.core.config import Settings
from app.highlights.ffmpeg_builder import FFmpegHighlightRenderer
from app.highlights.queue import FileHighlightRenderQueue
from app.highlights.worker import HighlightRenderWorker
from app.club_sale_market.service import ClubSaleMarketService
from app.club_finance.service import ClubFinanceService
from app.football_universe.service import FootballUniverseService
from app.live_ops.service import LiveOpsService
from app.market.service import MarketEngine
from app.national_team_engine.tournament_service import NationalTeamTournamentService
from app.ownership_groups.service import OwnershipGroupService
from app.services.regen_ecosystem_service import RegenEcosystemService
from app.services.storage_media_service import MediaStorageService
from app.storage import LocalObjectStorage
from app.workers.integrity_scan_worker import IntegrityScanWorker
from app.workers.media_retention_worker import MediaRetentionWorker
from app.workers.trader_payment_window_worker import TraderPaymentWindowWorker


@dataclass(slots=True)
class OpsJobRunner:
    session_factory: sessionmaker
    settings: Settings
    market_engine: MarketEngine | None = None

    def run_media_retention(self) -> dict[str, Any]:
        storage_service = MediaStorageService(
            storage=LocalObjectStorage(self.settings.media_storage.storage_root),
            config=self.settings.media_storage,
        )
        with self.session_factory() as session:
            worker = MediaRetentionWorker(session=session, storage_service=storage_service)
            archived = worker.archive_expired_highlights()
            purged = worker.purge_expired_archives()
            session.commit()
        return {"archive": archived, "purge": purged}

    def run_highlight_render_cycle(self, *, limit: int = 10) -> dict[str, Any]:
        worker = HighlightRenderWorker(
            queue=FileHighlightRenderQueue(self.settings.media_storage.storage_root),
            storage=LocalObjectStorage(self.settings.media_storage.storage_root),
            renderer=FFmpegHighlightRenderer(),
        )
        outcomes: list[dict[str, Any]] = []
        for _ in range(max(0, limit)):
            outcome = worker.process_next()
            if outcome is None:
                break
            outcomes.append(outcome)
        return {
            "processed_count": len(outcomes),
            "succeeded_count": sum(1 for outcome in outcomes if outcome["status"] == "succeeded"),
            "failed_count": sum(1 for outcome in outcomes if outcome["status"] == "failed"),
            "outcomes": outcomes,
        }

    def run_integrity_scan(self) -> dict[str, Any]:
        with self.session_factory() as session:
            worker = IntegrityScanWorker(session=session, settings=self.settings, market_engine=self.market_engine)
            results = {
                "integrity_scan": worker.run_integrity_scan(),
                "cluster_scan": worker.run_suspicious_cluster_scan(),
            }
            session.commit()
        return results

    def run_trader_payment_window_maintenance(self, *, limit: int = 200) -> dict[str, Any]:
        with self.session_factory() as session:
            results = TraderPaymentWindowWorker(session=session).expire_payment_windows(limit=limit)
            session.commit()
        return results

    def run_weekly_finance_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = ClubFinanceService(session).run_weekly_cycle()
            session.commit()
        return results

    def run_broadcast_revenue_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = BroadcastRightsService(session).run_revenue_distribution_cycle()
            session.commit()
        return results

    def run_broadcast_expiration_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = BroadcastRightsService(session).expire_rights_and_relist()
            session.commit()
        return results

    def run_ownership_group_reputation_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = OwnershipGroupService(session).run_reputation_cycle()
            session.commit()
        return results

    def run_live_ops_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = LiveOpsService(session).run_live_event_cycle()
            session.commit()
        return results

    def run_regen_weekly_academy_generation(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = RegenEcosystemService(session, settings=self.settings).run_weekly_academy_generation()
            session.commit()
        return results

    def run_regen_scouting_discovery(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = RegenEcosystemService(session, settings=self.settings).run_scouting_discovery_jobs()
            session.commit()
        return results

    def run_regen_potential_updates(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = RegenEcosystemService(session, settings=self.settings).run_potential_update_jobs()
            session.commit()
        return results

    def run_regen_career_events(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = RegenEcosystemService(session, settings=self.settings).run_career_event_jobs()
            session.commit()
        return results

    def run_fan_update_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = FootballUniverseService(session).run_fan_update_cycle()
            session.commit()
        return results

    def run_media_generation_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = FootballUniverseService(session).run_media_generation_cycle()
            session.commit()
        return results

    def run_identity_evolution_cycle(self) -> dict[str, Any]:
        with self.session_factory() as session:
            results = FootballUniverseService(session).run_identity_evolution_cycle()
            session.commit()
        return results

    def run_club_market_valuation_refresh(self, *, limit: int = 250) -> dict[str, Any]:
        with self.session_factory() as session:
            results = ClubSaleMarketService(session).refresh_market_valuations(limit=limit)
            session.commit()
        return results

    def run_national_team_rental_cleanup(self, *, competition_id: str | None = None) -> dict[str, Any]:
        with self.session_factory() as session:
            results = NationalTeamTournamentService(session).cleanup_expired_rentals(competition_id=competition_id)
            session.commit()
        return results

    def run_tournament_storyline_generation(self, *, competition_id: str | None = None) -> dict[str, Any]:
        with self.session_factory() as session:
            results = NationalTeamTournamentService(session).generate_story_events(competition_id=competition_id)
            session.commit()
        return results

    def run_stadium_ad_rotation(self, *, competition_id: str | None = None) -> dict[str, Any]:
        with self.session_factory() as session:
            results = NationalTeamTournamentService(session).rotate_ads(competition_id=competition_id)
            session.commit()
        return results


__all__ = ["OpsJobRunner"]
