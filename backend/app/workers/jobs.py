from __future__ import annotations

import logging
from typing import Any

try:
    from rq import get_current_job
except ModuleNotFoundError:  # pragma: no cover - exercised in lightweight test/runtime environments

    def get_current_job() -> Any | None:
        return None


from app.core.cache_namespaces import REGEN_UNIVERSE_CACHE_NAMESPACE
from app.core.config import get_settings
from app.core.container import build_application_context
from app.core.response_cache import NamespacedResponseCache
from app.admin_finance.service import AdminFinanceService
from app.models.user import User
from app.regen_universe.expansion_service import RegenUniverseExpansionService
from app.treasury.service import TreasuryService
from app.wallets.funding_service import WalletFundingService
from app.wallets.service import WalletService

logger = logging.getLogger(__name__)

_TASK_CONTEXT = None


def _context():
    global _TASK_CONTEXT
    if _TASK_CONTEXT is None:
        settings = get_settings()
        _TASK_CONTEXT = build_application_context(
            settings=settings,
        )
    return _TASK_CONTEXT


def _job_id() -> str | None:
    job = get_current_job()
    return job.id if job is not None else None


def _invalidate_regen_universe_cache(context) -> None:
    NamespacedResponseCache(backend=context.cache_backend).invalidate(REGEN_UNIVERSE_CACHE_NAMESPACE)


def verify_wallet_top_up_job(*, user_id: str, reference: str) -> dict[str, Any]:
    job_id = _job_id()
    context = _context()
    logger.info("worker.wallet_top_up_verify.started job_id=%s user_id=%s reference=%s", job_id, user_id, reference)
    try:
        wallet_service = WalletService(
            event_publisher=context.event_publisher,
            cache_backend=context.cache_backend,
        )
        funding_service = WalletFundingService(
            wallet_service=wallet_service,
            treasury_service=TreasuryService(wallet_service=wallet_service),
        )
        with context.database.session_factory() as session:
            user = session.get(User, user_id)
            if user is None:
                raise ValueError(f"User {user_id} was not found.")
            result = funding_service.verify_top_up(session, user, reference=reference)
            session.commit()
            payload = {
                "wallet_id": result.wallet.id,
                "transaction_id": result.transaction.id,
                "transaction_status": result.transaction.status,
                "reference": reference,
            }
        logger.info("worker.wallet_top_up_verify.completed job_id=%s", job_id)
        return payload
    except Exception:
        logger.exception(
            "worker.wallet_top_up_verify.failed job_id=%s user_id=%s reference=%s", job_id, user_id, reference
        )
        raise


def admin_finance_export_job(*, export_id: str, actor_user_id: str) -> dict[str, Any]:
    job_id = _job_id()
    context = _context()
    logger.info(
        "worker.admin_finance_export.started job_id=%s export_id=%s actor_user_id=%s",
        job_id,
        export_id,
        actor_user_id,
    )
    try:
        with context.database.session_factory() as session:
            actor = session.get(User, actor_user_id)
            if actor is None:
                raise ValueError(f"Admin export actor {actor_user_id} was not found.")
            payload = AdminFinanceService(session=session).complete_admin_export(
                actor=actor,
                export_id=export_id,
            )
            session.commit()
        logger.info("worker.admin_finance_export.completed job_id=%s export_id=%s", job_id, export_id)
        return payload
    except Exception:
        logger.exception(
            "worker.admin_finance_export.failed job_id=%s export_id=%s actor_user_id=%s",
            job_id,
            export_id,
            actor_user_id,
        )
        raise


def regen_story_regeneration_job(*, player_id: str | None = None) -> dict[str, Any]:
    job_id = _job_id()
    context = _context()
    logger.info("worker.regen_story_regeneration.started job_id=%s player_id=%s", job_id, player_id)
    try:
        with context.database.session_factory() as session:
            payload = RegenUniverseExpansionService(session).regenerate_stories(player_id=player_id)
            session.commit()
        _invalidate_regen_universe_cache(context)
        logger.info("worker.regen_story_regeneration.completed job_id=%s", job_id)
        return payload
    except Exception:
        logger.exception("worker.regen_story_regeneration.failed job_id=%s player_id=%s", job_id, player_id)
        raise


def regen_rivalry_detection_job(*, player_id: str | None = None) -> dict[str, Any]:
    job_id = _job_id()
    context = _context()
    logger.info("worker.regen_rivalry_detection.started job_id=%s player_id=%s", job_id, player_id)
    try:
        with context.database.session_factory() as session:
            payload = RegenUniverseExpansionService(session).detect_rivalries(player_id=player_id)
            session.commit()
        _invalidate_regen_universe_cache(context)
        logger.info("worker.regen_rivalry_detection.completed job_id=%s", job_id)
        return payload
    except Exception:
        logger.exception("worker.regen_rivalry_detection.failed job_id=%s player_id=%s", job_id, player_id)
        raise


def regen_dna_evolution_job(*, player_id: str | None = None) -> dict[str, Any]:
    job_id = _job_id()
    context = _context()
    logger.info("worker.regen_dna_evolution.started job_id=%s player_id=%s", job_id, player_id)
    try:
        with context.database.session_factory() as session:
            payload = RegenUniverseExpansionService(session).evolve_dna_profiles(player_id=player_id)
            session.commit()
        _invalidate_regen_universe_cache(context)
        logger.info("worker.regen_dna_evolution.completed job_id=%s", job_id)
        return payload
    except Exception:
        logger.exception("worker.regen_dna_evolution.failed job_id=%s player_id=%s", job_id, player_id)
        raise


def regen_tournament_scheduling_job(*, days_ahead: int) -> dict[str, Any]:
    job_id = _job_id()
    context = _context()
    logger.info("worker.regen_tournament_scheduling.started job_id=%s days_ahead=%s", job_id, days_ahead)
    try:
        with context.database.session_factory() as session:
            payload = RegenUniverseExpansionService(session).schedule_youth_tournaments(days_ahead=days_ahead)
            session.commit()
        _invalidate_regen_universe_cache(context)
        logger.info("worker.regen_tournament_scheduling.completed job_id=%s", job_id)
        return payload
    except Exception:
        logger.exception("worker.regen_tournament_scheduling.failed job_id=%s days_ahead=%s", job_id, days_ahead)
        raise


__all__ = [
    "admin_finance_export_job",
    "regen_dna_evolution_job",
    "regen_rivalry_detection_job",
    "regen_story_regeneration_job",
    "regen_tournament_scheduling_job",
    "verify_wallet_top_up_job",
]
