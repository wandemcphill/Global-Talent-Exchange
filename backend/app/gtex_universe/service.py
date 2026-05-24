from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.gtex.service import GtexBaseService, SimulatedParticipant
from app.gtex_universe.schemas import (
    CareerCreateRequest,
    CareerRetireRequest,
    CareerTrainRequest,
    CareerTransferRequest,
    CeremonyTicketPurchaseRequest,
    CeremonyVoteRequest,
    FanProfileUpdateRequest,
    FanReactionCreateRequest,
    FanTicketPurchaseRequest,
    FullExperienceSimulationRequest,
    SyncClubInput,
    SyncCompetitionInput,
    SyncEventInput,
    SyncPlayerInput,
    SyncUpdateRequest,
)
from app.gtex_universe.fan_experience import GtexFanExperienceService
from app.gtex_universe.social_warfare import GtexSocialWarfareService
from app.ingestion.models import Player
from app.models.base import utcnow
from app.models.gtex_economy import GtexAIProfile, GtexLeague, GtexMatch, GtexMatchStatus, GtexParticipantType
from app.models.gtex_universe import (
    CareerDecision,
    CareerDecisionType,
    CareerLegacyRecord,
    CareerPlayer,
    CareerPlayerStatus,
    CareerTrainingSession,
    ManagerMatchHistory,
    ManagerVsManagerHistory,
    RealWorldEntityMapping,
    RealWorldEvent,
    RealWorldEventStatus,
    RealWorldMappingType,
)
from app.models.manager_marketplace import (
    ManagerControlMode,
    ManagerDisciplineStyle,
    ManagerPersonalityTacticalStyle,
    ManagerProfile,
)
from app.models.player_career_entry import PlayerCareerEntry
from app.models.player_contract import PlayerContract
from app.models.real_world_hub import (
    RealClub,
    RealCompetition,
    RealDataProvider,
    RealDataSyncJob,
    RealDataSyncStatus,
    RealPlayer,
)
from app.models.user import User

if TYPE_CHECKING:
    from app.core.events import EventPublisher
    from app.gtex.config import GtexSettings
    from app.gtex.service import AiLeagueService, CreatorMarketService, UnifiedEconomyService
    from app.wallets.service import WalletService


_TACTICAL_STYLE_FORMATIONS: dict[ManagerPersonalityTacticalStyle, tuple[str, ...]] = {
    ManagerPersonalityTacticalStyle.ATTACKING: ("4-3-3", "3-4-3"),
    ManagerPersonalityTacticalStyle.DEFENSIVE: ("4-5-1", "5-4-1"),
    ManagerPersonalityTacticalStyle.BALANCED: ("4-2-3-1", "4-4-2"),
}
_TACTICAL_STYLE_TEMPO: dict[ManagerPersonalityTacticalStyle, str] = {
    ManagerPersonalityTacticalStyle.ATTACKING: "high",
    ManagerPersonalityTacticalStyle.DEFENSIVE: "controlled",
    ManagerPersonalityTacticalStyle.BALANCED: "balanced",
}
_TACTICAL_STYLE_SUBSTITUTIONS: dict[ManagerPersonalityTacticalStyle, str] = {
    ManagerPersonalityTacticalStyle.ATTACKING: "aggressive_chase",
    ManagerPersonalityTacticalStyle.DEFENSIVE: "protect_lead",
    ManagerPersonalityTacticalStyle.BALANCED: "balanced_rotation",
}
_INTENSITY_BY_RIVALRY = (
    (0.80, "volatile"),
    (0.55, "heated"),
    (0.30, "growing"),
    (0.00, "fresh"),
)


class UniverseError(ValueError):
    pass


class UniverseNotFoundError(UniverseError):
    pass


class UniverseConflictError(UniverseError):
    pass


class UniverseValidationError(UniverseError):
    pass


@dataclass(slots=True)
class GtexUniverseService(GtexBaseService):
    creator_market_service: "CreatorMarketService"
    economy_service: "UnifiedEconomyService"
    ai_leagues: "AiLeagueService"

    def __init__(
        self,
        *,
        settings: "GtexSettings",
        wallet_service: "WalletService",
        state_store,
        creator_market_service: "CreatorMarketService",
        economy_service: "UnifiedEconomyService",
        ai_leagues: "AiLeagueService",
        event_publisher: "EventPublisher | None" = None,
        realtime_channel: str = "gtex.realtime",
    ) -> None:
        super().__init__(
            settings=settings,
            wallet_service=wallet_service,
            state_store=state_store,
            event_publisher=event_publisher,
            realtime_channel=realtime_channel,
        )
        self.creator_market_service = creator_market_service
        self.economy_service = economy_service
        self.ai_leagues = ai_leagues

    def seed_defaults(self, session: Session) -> None:
        for ai in session.scalars(select(GtexAIProfile).where(GtexAIProfile.is_active.is_(True))).all():
            self._ensure_manager_profile_for_ai(session, ai)

    def get_manager_history(
        self, session: Session, *, manager_profile_id: str, limit: int = 20
    ) -> list[dict[str, Any]]:
        profile = session.get(ManagerProfile, manager_profile_id)
        if profile is None:
            raise UniverseNotFoundError("Manager profile was not found.")
        history_rows = session.scalars(
            select(ManagerMatchHistory)
            .where(ManagerMatchHistory.manager_profile_id == manager_profile_id)
            .order_by(ManagerMatchHistory.created_at.desc())
            .limit(limit)
        ).all()
        items: list[dict[str, Any]] = []
        for row in history_rows:
            opponent = (
                session.get(ManagerProfile, row.opponent_manager_profile_id)
                if row.opponent_manager_profile_id
                else None
            )
            rivalry = self._manager_rivalry(session, profile, opponent) if opponent is not None else None
            items.append(
                {
                    "id": row.id,
                    "source_match_id": row.source_match_id,
                    "source_match_type": row.source_match_type,
                    "team_side": row.team_side,
                    "result": row.result,
                    "intensity_score": round(float(row.intensity_score), 4),
                    "rivalry_score": round(float(row.rivalry_score), 4),
                    "opponent_manager_id": opponent.id if opponent is not None else None,
                    "opponent_name": self._manager_name(opponent) if opponent is not None else None,
                    "tactical_snapshot": dict(row.tactical_snapshot_json or {}),
                    "narrative_summary": row.narrative_summary,
                    "rivalry": (
                        None
                        if rivalry is None
                        else {
                            "meetings": rivalry.meetings,
                            "rivalry_score": round(float(rivalry.rivalry_score), 4),
                            "narrative_tag": rivalry.narrative_tag,
                        }
                    ),
                    "metadata_json": dict(row.metadata_json or {}),
                    "created_at": row.created_at,
                }
            )
        return items

    def create_career_player(self, session: Session, *, user: User, payload: CareerCreateRequest) -> CareerPlayer:
        existing = self._career_player_by_user_id(session, user.id)
        if existing is not None:
            raise UniverseConflictError("Career mode is already active for this user.")
        player = self._resolve_or_create_career_player_record(session, user=user, payload=payload)
        career_player = CareerPlayer(
            user_id=user.id,
            player_id=player.id,
            current_club=payload.current_club or player.real_world_club_name or self._current_club_name(player),
            current_club_id=player.current_club_id,
            career_stats=self._default_career_stats(),
            growth_rate=round(payload.growth_rate, 4),
            xp=0,
            level=1,
            training_focus="balanced",
            current_form=0.5,
            marketability_score=0.5,
            prestige_score=0,
            status=CareerPlayerStatus.ACTIVE,
            legacy_summary_json={},
        )
        session.add(career_player)
        session.flush()
        self._create_or_roll_forward_career_tenure(
            session,
            career_player=career_player,
            club_name=career_player.current_club,
            wage_amount=Decimal("0.00"),
            contract_days=365,
            notes="Career mode activated.",
        )
        self.creator_market_service.ensure_asset_for_user(session, user)
        self._stage_event(
            session,
            name="CAREER_MODE_STARTED",
            payload={"user_id": user.id, "career_player_id": career_player.id, "player_id": player.id},
            aggregate_id=career_player.id,
            aggregate_type="career_player",
            partition_key=user.id,
            realtime_topic="career.created",
        )
        return career_player

    def get_career_player(self, session: Session, *, user_id: str) -> CareerPlayer:
        career_player = self._career_player_by_user_id(session, user_id)
        if career_player is None:
            raise UniverseNotFoundError("Career player was not found for this user.")
        return career_player

    def train_career_player(self, session: Session, *, user: User, payload: CareerTrainRequest) -> CareerPlayer:
        career_player = self.get_career_player(session, user_id=user.id)
        self._ensure_career_active(career_player)
        intensity = payload.intensity.strip().lower()
        if intensity not in {"low", "normal", "high"}:
            raise UniverseValidationError("Training intensity must be low, normal, or high.")
        intensity_factor = {"low": 0.75, "normal": 1.0, "high": 1.25}[intensity]
        focus_weight = 6 + (len(payload.focus.strip()) % 5)
        xp_gain = int(
            round((32 + (career_player.level * 4) + focus_weight) * intensity_factor * (1 + career_player.growth_rate))
        )
        form_gain = round(min(0.18, (0.035 * intensity_factor) + (career_player.growth_rate * 0.22)), 4)
        career_player.xp += xp_gain
        career_player.level = max(1, 1 + (career_player.xp // 250))
        career_player.training_focus = payload.focus.strip().lower()
        career_player.current_form = self._clamp(career_player.current_form + form_gain, minimum=0.1, maximum=1.0)
        career_player.marketability_score = self._clamp(
            career_player.marketability_score + (form_gain / 2),
            minimum=0.0,
            maximum=1.0,
        )
        career_player.prestige_score += max(1, xp_gain // 40)
        stats = self._career_stats(career_player)
        stats["training_sessions"] += 1
        stats["xp_gained"] += xp_gain
        stats["last_training_focus"] = career_player.training_focus
        career_player.career_stats = stats
        session.add(
            CareerTrainingSession(
                career_player_id=career_player.id,
                focus=career_player.training_focus,
                intensity=intensity,
                xp_gained=xp_gain,
                form_gain=form_gain,
                growth_delta=round(min(0.03, career_player.growth_rate * 0.045 * intensity_factor), 4),
                metadata_json={"level_after": career_player.level},
            )
        )
        self._apply_career_market_reaction(
            session,
            user=user,
            career_player=career_player,
            won=None,
            reason="career_training",
            boost=form_gain + (xp_gain / 500.0),
        )
        self._stage_event(
            session,
            name="CAREER_PLAYER_TRAINED",
            payload={
                "user_id": user.id,
                "career_player_id": career_player.id,
                "focus": career_player.training_focus,
                "intensity": intensity,
                "xp_gain": xp_gain,
                "level": career_player.level,
            },
            aggregate_id=career_player.id,
            aggregate_type="career_player",
            partition_key=user.id,
            realtime_topic="career.training",
        )
        return career_player

    def transfer_career_player(self, session: Session, *, user: User, payload: CareerTransferRequest) -> CareerPlayer:
        career_player = self.get_career_player(session, user_id=user.id)
        self._ensure_career_active(career_player)
        previous_club = career_player.current_club
        next_club = payload.current_club.strip()
        if previous_club and previous_club.lower() == next_club.lower():
            raise UniverseConflictError("Career player is already registered with that club.")
        career_player.current_club = next_club
        stats = self._career_stats(career_player)
        stats["transfers"] += 1
        stats["last_transfer_to"] = next_club
        career_player.career_stats = stats
        career_player.marketability_score = self._clamp(
            career_player.marketability_score + 0.08, minimum=0.0, maximum=1.0
        )
        career_player.prestige_score += 8
        self._create_or_roll_forward_career_tenure(
            session,
            career_player=career_player,
            club_name=next_club,
            wage_amount=Decimal(str(payload.wage_amount)).quantize(Decimal("0.01")),
            contract_days=payload.contract_days,
            notes=payload.notes,
        )
        session.add(
            CareerDecision(
                career_player_id=career_player.id,
                decision_type=CareerDecisionType.TRANSFER,
                from_value=previous_club,
                to_value=next_club,
                accepted=True,
                decision_payload_json={
                    "wage_amount": payload.wage_amount,
                    "contract_days": payload.contract_days,
                    "notes": payload.notes,
                },
            )
        )
        self._apply_career_market_reaction(
            session,
            user=user,
            career_player=career_player,
            won=None,
            reason="career_transfer",
            boost=0.12,
        )
        self._stage_event(
            session,
            name="CAREER_PLAYER_TRANSFERRED",
            payload={
                "user_id": user.id,
                "career_player_id": career_player.id,
                "from_club": previous_club,
                "to_club": next_club,
            },
            aggregate_id=career_player.id,
            aggregate_type="career_player",
            partition_key=user.id,
            realtime_topic="career.transfer",
        )
        return career_player

    def retire_career_player(self, session: Session, *, user: User, payload: CareerRetireRequest) -> CareerPlayer:
        career_player = self.get_career_player(session, user_id=user.id)
        self._ensure_career_active(career_player)
        self._close_active_career_commitments(session, career_player=career_player, end_on=date.today())
        legacy_role = payload.legacy_role.strip().lower()
        player = session.get(Player, career_player.player_id)
        stats = self._career_stats(career_player)
        career_player.status = CareerPlayerStatus.RETIRED
        career_player.retired_at = utcnow()
        career_player.legacy_summary_json = {
            "legacy_role": legacy_role,
            "legacy_headline": payload.legacy_headline
            or f"{player.full_name if player is not None else career_player.player_id} retires into the GTEX hall of fame.",
            "hall_of_fame": True,
            "ai_player": True,
            "final_club": career_player.current_club,
            "level": career_player.level,
            "xp": career_player.xp,
            "prestige_score": career_player.prestige_score,
            "career_stats": stats,
        }
        if player is not None:
            player.dna_profile = {
                **dict(player.dna_profile or {}),
                "post_career_role": "ai_player",
                "hall_of_fame": True,
                "career_mode_retired_at": career_player.retired_at.isoformat(),
            }
            player.last_synced_at = utcnow()
        legacy = session.scalar(
            select(CareerLegacyRecord).where(CareerLegacyRecord.career_player_id == career_player.id)
        )
        if legacy is None:
            legacy = CareerLegacyRecord(
                career_player_id=career_player.id,
                user_id=career_player.user_id,
                player_id=career_player.player_id,
                legacy_role=legacy_role,
                summary_json=dict(career_player.legacy_summary_json or {}),
            )
            session.add(legacy)
        else:
            legacy.user_id = career_player.user_id
            legacy.player_id = career_player.player_id
            legacy.legacy_role = legacy_role
            legacy.summary_json = dict(career_player.legacy_summary_json or {})
        session.add(
            CareerDecision(
                career_player_id=career_player.id,
                decision_type=CareerDecisionType.RETIREMENT,
                from_value=career_player.current_club,
                to_value=legacy_role,
                accepted=True,
                decision_payload_json=dict(career_player.legacy_summary_json or {}),
            )
        )
        self._apply_career_market_reaction(
            session,
            user=user,
            career_player=career_player,
            won=None,
            reason="career_retirement",
            boost=0.16,
        )
        self._stage_event(
            session,
            name="CAREER_PLAYER_RETIRED",
            payload={
                "user_id": user.id,
                "career_player_id": career_player.id,
                "legacy_role": legacy_role,
            },
            aggregate_id=career_player.id,
            aggregate_type="career_player",
            partition_key=user.id,
            realtime_topic="career.retired",
        )
        return career_player

    def list_real_world_events(self, session: Session, *, limit: int = 20) -> list[RealWorldEvent]:
        return list(
            session.scalars(
                select(RealWorldEvent)
                .order_by(RealWorldEvent.scheduled_at.desc(), RealWorldEvent.updated_at.desc())
                .limit(limit)
            ).all()
        )

    def sync_update(self, session: Session, *, actor: User, payload: SyncUpdateRequest) -> dict[str, Any]:
        provider = self._get_or_create_provider(
            session,
            name=payload.provider_name.strip(),
            endpoint=payload.provider_endpoint.strip(),
        )
        job = RealDataSyncJob(
            provider_id=provider.id,
            status=RealDataSyncStatus.RUNNING.value,
            started_at=utcnow(),
            summary_json={"optional_sync": payload.optional_sync},
        )
        session.add(job)
        session.flush()
        mirrored_match_ids: list[str] = []
        try:
            competitions = self._upsert_competitions(session, provider=provider, inputs=payload.competitions)
            clubs = self._upsert_clubs(session, provider=provider, competitions=competitions, inputs=payload.clubs)
            players = self._upsert_players(
                session, provider=provider, competitions=competitions, clubs=clubs, inputs=payload.players
            )
            events = self._upsert_events(
                session, provider=provider, competitions=competitions, clubs=clubs, inputs=payload.events
            )
            if payload.mirror_into_gtex:
                for event in events.values():
                    match = self._mirror_real_world_event(
                        session,
                        actor=actor,
                        event=event,
                        career_user_id=payload.career_user_id,
                    )
                    if match is not None:
                        mirrored_match_ids.append(match.id)
            provider.last_sync_at = utcnow()
            job.status = RealDataSyncStatus.COMPLETED.value
            job.completed_at = utcnow()
            job.entities_seen = (
                len(payload.competitions) + len(payload.clubs) + len(payload.players) + len(payload.events)
            )
            job.entities_upserted = len(competitions) + len(clubs) + len(players) + len(events)
            job.summary_json = {
                "optional_sync": payload.optional_sync,
                "mirror_into_gtex": payload.mirror_into_gtex,
                "mirrored_match_ids": list(mirrored_match_ids),
            }
            self._stage_event(
                session,
                name="REAL_WORLD_SYNC_UPDATED",
                payload={
                    "provider_id": provider.id,
                    "sync_job_id": job.id,
                    "mirrored_match_ids": list(mirrored_match_ids),
                },
                aggregate_id=job.id,
                aggregate_type="real_world_sync_job",
                partition_key=provider.id,
                realtime_topic="real_world.sync",
            )
            return {
                "provider_id": provider.id,
                "sync_job_id": job.id,
                "competitions_upserted": len(competitions),
                "clubs_upserted": len(clubs),
                "players_upserted": len(players),
                "events_upserted": len(events),
                "mirrored_match_ids": mirrored_match_ids,
                "optional_sync": payload.optional_sync,
            }
        except Exception as exc:
            job.status = RealDataSyncStatus.FAILED.value
            job.completed_at = utcnow()
            job.entities_failed = 1
            job.error_message = str(exc)
            raise

    def get_fan_profile(self, session: Session, *, actor: User) -> dict[str, Any]:
        helper = GtexFanExperienceService(session)
        profile = helper.get_or_create_profile(actor=actor)
        return helper.profile_payload(profile)

    def update_fan_profile(self, session: Session, *, actor: User, payload: FanProfileUpdateRequest) -> dict[str, Any]:
        helper = GtexFanExperienceService(session)
        profile = helper.update_profile(
            actor=actor,
            favorite_club_id=payload.favorite_club_id,
            favorite_player_id=payload.favorite_player_id,
            rival_club_ids=list(payload.rival_club_ids or []),
        )
        return helper.profile_payload(profile)

    def get_match_fan_experience(
        self,
        session: Session,
        *,
        match_id: str,
        current_user: User | None,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        return GtexFanExperienceService(session).match_experience(match=match, current_user=current_user)

    def purchase_match_ticket(
        self,
        session: Session,
        *,
        actor: User,
        match_id: str,
        payload: FanTicketPurchaseRequest,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        try:
            ticket = GtexFanExperienceService(session).purchase_match_ticket(
                actor=actor,
                match=match,
                ticket_tier=payload.ticket_tier,
            )
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc
        return GtexFanExperienceService(session).ticket_payload(ticket)

    def create_match_reaction(
        self,
        session: Session,
        *,
        actor: User,
        match_id: str,
        payload: FanReactionCreateRequest,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        try:
            reaction = GtexFanExperienceService(session).submit_match_reaction(
                actor=actor,
                match=match,
                reaction_type=payload.reaction_type,
                supported_side=payload.supported_side,
            )
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc
        return GtexFanExperienceService(session).reaction_payload(reaction)

    def join_fan_tribe(
        self,
        session: Session,
        *,
        actor: User,
        match_id: str | None,
        club_id: str | None,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id) if match_id else None
        if match_id is not None and match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        try:
            tribe = GtexSocialWarfareService(session).join_tribe(actor=actor, club_id=club_id, match=match)
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc
        return GtexSocialWarfareService(session).tribe_payload(tribe) or {}

    def get_match_social_warfare(
        self,
        session: Session,
        *,
        match_id: str,
        current_user: User | None,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        offer = GtexFanExperienceService(session)._match_offer(match=match, current_user=current_user)
        return GtexSocialWarfareService(session).match_social_warfare(
            match=match, current_user=current_user, offer=offer
        )

    def post_match_chat_message(
        self,
        session: Session,
        *,
        actor: User,
        match_id: str,
        message: str | None,
        emoji: str | None,
        intensity: float,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, match_id)
        if match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        try:
            return GtexSocialWarfareService(session).post_chat_message(
                actor=actor,
                match=match,
                message=message,
                emoji=emoji,
                intensity=intensity,
            )
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc

    def get_legacy_board(self, session: Session, *, limit: int = 5) -> dict[str, Any]:
        return GtexSocialWarfareService(session).legacy_board(limit=limit)

    def purchase_ceremony_ticket(
        self,
        session: Session,
        *,
        actor: User,
        season_id: str,
        payload: CeremonyTicketPurchaseRequest,
    ) -> dict[str, Any]:
        try:
            ticket = GtexFanExperienceService(session).purchase_ceremony_ticket(
                actor=actor,
                season_id=season_id,
                ticket_tier=payload.ticket_tier,
            )
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc
        return GtexFanExperienceService(session).ticket_payload(ticket)

    def cast_ceremony_vote(
        self,
        session: Session,
        *,
        actor: User,
        payload: CeremonyVoteRequest,
    ) -> dict[str, Any]:
        try:
            return GtexFanExperienceService(session).cast_ceremony_vote(
                actor=actor,
                award_id=payload.award_id,
                player_id=payload.player_id,
                season_id=payload.season_id,
            )
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc

    def get_regen_hype(self, session: Session, *, season_id: str | None = None) -> dict[str, Any]:
        return GtexFanExperienceService(session).regen_hype_board(season_id=season_id)

    def simulate_full_experience(
        self,
        session: Session,
        *,
        actor: User,
        payload: FullExperienceSimulationRequest,
    ) -> dict[str, Any]:
        match = session.get(GtexMatch, payload.match_id)
        if match is None:
            raise UniverseNotFoundError("GTEX match was not found.")
        if not hasattr(self.ai_leagues, "simulate_match") or not hasattr(self.ai_leagues, "get_match_view"):
            raise UniverseValidationError("GTEX simulation service is unavailable.")
        try:
            return GtexFanExperienceService(session).simulate_full_experience(
                actor=actor,
                match=match,
                simulate_match=lambda match_id: self.ai_leagues.simulate_match(session, match_id=match_id),
                read_match_view=lambda match_id: self.ai_leagues.get_match_view(session, match_id=match_id),
                season_id=payload.season_id,
            )
        except ValueError as exc:
            raise UniverseValidationError(str(exc)) from exc

    def prepare_match_context(
        self,
        session: Session,
        *,
        match: GtexMatch,
        home: SimulatedParticipant,
        away: SimulatedParticipant,
    ) -> dict[str, Any]:
        home_manager = self._resolve_manager_for_participant(session, home)
        away_manager = self._resolve_manager_for_participant(session, away)
        rivalry = self._manager_rivalry(session, home_manager, away_manager)
        rivalry_score = float(rivalry.rivalry_score) if rivalry is not None else 0.0
        real_event = self._real_world_event_for_match(session, match)
        career_context = self._career_participation_context(session, match=match, real_event=real_event)
        home_multiplier = 1.0 + self._manager_strength_bonus(home_manager)
        away_multiplier = 1.0 + self._manager_strength_bonus(away_manager)
        fan_helper = GtexFanExperienceService(session)
        fan_experience = fan_helper.match_experience(match=match, current_user=None)
        fan_atmosphere = dict(fan_experience.get("atmosphere") or {})
        aggression_overrides = {
            home.subject_key: self._manager_aggression_bonus(home_manager),
            away.subject_key: self._manager_aggression_bonus(away_manager),
        }
        if career_context["side"] == "home":
            home_multiplier += career_context["strength_bonus"]
        elif career_context["side"] == "away":
            away_multiplier += career_context["strength_bonus"]
        if real_event is not None:
            event_boosts = self._real_world_event_strength_boost(real_event)
            home_multiplier += event_boosts["home"]
            away_multiplier += event_boosts["away"]
        home_multiplier *= float(fan_atmosphere.get("home_strength_multiplier") or 1.0)
        away_multiplier *= float(fan_atmosphere.get("away_strength_multiplier") or 1.0)
        intensity_bonus_events = min(
            8,
            int(round((rivalry_score + career_context["intensity_bonus"]) * 3))
            + int(fan_atmosphere.get("intensity_bonus_events") or 0),
        )
        return {
            "seed_material": "|".join(
                item
                for item in (
                    match.id,
                    home_manager.id if home_manager is not None else "",
                    away_manager.id if away_manager is not None else "",
                    real_event.id if real_event is not None else "",
                    career_context["career_player_id"] or "",
                    str(fan_experience.get("event_key") or ""),
                    str(fan_experience.get("tickets_sold") or 0),
                )
                if item
            ),
            "home_strength_multiplier": round(home_multiplier, 4),
            "away_strength_multiplier": round(away_multiplier, 4),
            "aggression_overrides": aggression_overrides,
            "intensity_bonus_events": intensity_bonus_events,
            "home_manager_id": home_manager.id if home_manager is not None else None,
            "away_manager_id": away_manager.id if away_manager is not None else None,
            "career_context": career_context,
            "rivalry_score": rivalry_score,
            "real_world_event_id": real_event.id if real_event is not None else None,
            "fan_experience": fan_experience,
            "fan_atmosphere": fan_atmosphere,
        }

    def finalize_match_context(
        self,
        session: Session,
        *,
        match: GtexMatch,
        home: SimulatedParticipant,
        away: SimulatedParticipant,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        home_manager = (
            session.get(ManagerProfile, context.get("home_manager_id")) if context.get("home_manager_id") else None
        )
        away_manager = (
            session.get(ManagerProfile, context.get("away_manager_id")) if context.get("away_manager_id") else None
        )
        rivalry = self._manager_rivalry(session, home_manager, away_manager)
        fan_helper = GtexFanExperienceService(session)
        fan_experience = dict(context.get("fan_experience") or {})
        fan_atmosphere = dict(context.get("fan_atmosphere") or {})
        fan_crowd_intensity = float(fan_atmosphere.get("crowd_intensity_boost") or 0.0)
        fan_commentary_tone = str(fan_atmosphere.get("commentary_tone") or "charged")
        intensity_score = round(
            min(
                1.0,
                0.25
                + float(context.get("rivalry_score") or 0.0)
                + (float(context.get("intensity_bonus_events") or 0) * 0.08)
                + (fan_crowd_intensity * 0.25),
            ),
            4,
        )
        self._update_manager_records(
            session,
            match=match,
            home_manager=home_manager,
            away_manager=away_manager,
            intensity_score=intensity_score,
            rivalry=rivalry,
        )
        career_summary = self._apply_career_match_impact(session, match=match, context=context)
        real_event = (
            session.get(RealWorldEvent, context.get("real_world_event_id"))
            if context.get("real_world_event_id")
            else None
        )
        if real_event is not None:
            real_event.influence_applied_at = utcnow()
            real_event.influence_summary_json = {
                **dict(real_event.influence_summary_json or {}),
                "mirror_match_id": match.id,
                "career_summary": dict(career_summary or {}),
                "intensity_score": intensity_score,
            }
        rivalry_level = self._rivalry_level(
            float(rivalry.rivalry_score) if rivalry is not None else float(context.get("rivalry_score") or 0.0)
        )
        home_manager_name = self._manager_name(home_manager) if home_manager is not None else home.label
        away_manager_name = self._manager_name(away_manager) if away_manager is not None else away.label
        winner_side = (
            "home" if match.home_score > match.away_score else "away" if match.away_score > match.home_score else "draw"
        )
        winner_manager_name = (
            home_manager_name
            if winner_side == "home"
            else away_manager_name if winner_side == "away" else "Neither dugout"
        )
        tickets_sold = int(fan_experience.get("tickets_sold") or 0)
        sell_out_triggered = bool(
            fan_atmosphere.get("sell_out_triggered") or dict(fan_experience.get("sell_out_hype") or {}).get("triggered")
        )
        priority_stream = bool(fan_atmosphere.get("priority_stream") or tickets_sold > 0)
        fan_narrative_tag = str(fan_atmosphere.get("match_narrative_tag") or "anthemic_rise")
        exclusive_commentary_lines = list(
            dict.fromkeys(
                item
                for item in (
                    list(fan_atmosphere.get("exclusive_commentary_lines") or [])
                    + list(fan_experience.get("exclusive_commentary_lines") or [])
                )
                if item
            )
        )
        fan_rewards = fan_helper.finalize_match_rewards(
            match=match,
            fan_context={
                "winner_side": winner_side,
                "sell_out_triggered": sell_out_triggered,
                "commentary_tone": fan_commentary_tone,
                "match_narrative_tag": fan_narrative_tag,
                "tickets_sold": tickets_sold,
                "home_manager_id": home_manager.id if home_manager is not None else None,
                "away_manager_id": away_manager.id if away_manager is not None else None,
            },
        )
        final_fan_experience = fan_helper.match_experience(match=match, current_user=None)
        social_warfare = dict(final_fan_experience.get("social_warfare") or fan_rewards.get("social_warfare") or {})
        live_chat = dict(social_warfare.get("live_chat") or {})
        fan_war = dict(social_warfare.get("fan_war") or {})
        mega_event = dict(social_warfare.get("mega_event") or {})
        commentary = [
            f"{home_manager_name} opened with {self._manager_primary_formation(home_manager)} and {self._manager_tempo(home_manager)} tempo.",
            f"{away_manager_name} answered with {self._manager_primary_formation(away_manager)} and {self._manager_tempo(away_manager)} control.",
            f"The touchline duel carried {rivalry_level} rivalry energy across the mirror fixture.",
        ]
        if career_summary:
            commentary.append(
                f"{career_summary['player_name']} injected a career-mode surge with {career_summary['xp_gain']} XP worth of influence."
            )
        if tickets_sold > 0:
            commentary.append(
                f"The crowd noise bent the commentary into a {fan_commentary_tone.replace('_', ' ')} register with {tickets_sold} tickets in play."
            )
        if fan_war:
            commentary.append(
                f"Fan tribes pushed the rivalry heat to {round(float(fan_war.get('rivalry_heat') or 0.0), 2)} and tilted the tone toward {str(dict(fan_war.get('impact') or {}).get('commentary_tone') or 'charged').replace('_', ' ')}."
            )
        if float(live_chat.get("moment_spike_score") or 0.0) >= 1.5:
            commentary.append(
                f"Live chat storms generated a {live_chat.get('dominant_emoji') or 'viral'} spike with {int(live_chat.get('total_messages') or 0)} crowd messages."
            )
        if mega_event:
            commentary.append(
                f"{mega_event.get('title') or 'Mega event'} framing elevated this match into a peak broadcast moment."
            )
        commentary.extend(exclusive_commentary_lines)
        broadcast_package = {
            "headline": (
                f"{winner_manager_name} wins the mirror broadcast."
                if winner_side != "draw"
                else "Mirror broadcast ends without a winner."
            ),
            "panel_take": (
                f"Pundits framed this as a {rivalry_level} chess match between {home_manager_name} and {away_manager_name}, "
                f"then leaned into the {fan_commentary_tone.replace('_', ' ')} crowd tone once the stands kicked in."
            ),
            "intensity_score": intensity_score,
            "ticketed_access": True,
            "priority_stream": priority_stream,
            "tickets_sold": tickets_sold,
            "sell_out_triggered": sell_out_triggered,
            "exclusive_commentary_lines": exclusive_commentary_lines,
            "viral_reaction_highlight": (
                f"{live_chat.get('dominant_emoji')} storm" if live_chat.get("dominant_emoji") else None
            ),
            "mega_event": mega_event,
        }
        news_article = {
            "title": f"{winner_manager_name} shapes the GTEX mirror narrative",
            "body": " ".join(
                [
                    f"{home.label} and {away.label} collided in a mirrored GTEX fixture seeded by real-world context.",
                    f"The managers steered the game through {rivalry_level} tactical pressure.",
                    f"Fan traffic pushed the night into a {fan_narrative_tag.replace('_', ' ')} atmosphere with {tickets_sold} tickets active.",
                    f"Fan tribes and chat storms kept the rivalry at {round(float(fan_war.get('rivalry_heat') or 0.0), 2)} heat.",
                    commentary[-1],
                ]
            ),
            "tags": ["fan-experience", fan_narrative_tag, "sell-out" if sell_out_triggered else "ticketed"],
        }
        return self._json_safe(
            {
                "home_manager": self._manager_snapshot(home_manager),
                "away_manager": self._manager_snapshot(away_manager),
                "commentary": commentary,
                "broadcast_package": broadcast_package,
                "news_article": news_article,
                "career_summary": career_summary,
                "fan_experience": {**final_fan_experience, "rewards": fan_rewards},
                "social_warfare": social_warfare,
                "real_world_sync": self._real_world_snapshot(real_event),
                "match_context": {
                    "manager_intensity_score": intensity_score,
                    "manager_rivalry_level": rivalry_level,
                    "career_side": context.get("career_context", {}).get("side"),
                    "fan_crowd_intensity": round(fan_crowd_intensity, 4),
                    "fan_commentary_tone": fan_commentary_tone,
                    "fan_narrative_tag": fan_narrative_tag,
                    "tickets_sold": tickets_sold,
                    "priority_stream": priority_stream,
                    "fan_war_pressure": fan_atmosphere.get("fan_war_pressure"),
                    "live_chat_pressure": fan_atmosphere.get("live_chat_pressure"),
                },
                "rivalry": {
                    "manager_rivalry_score": (
                        float(rivalry.rivalry_score)
                        if rivalry is not None
                        else float(context.get("rivalry_score") or 0.0)
                    ),
                    "manager_rivalry_level": rivalry_level,
                },
                "narrative_output": {
                    "match_storyline": (
                        f"{winner_manager_name} dictated a {rivalry_level} mirror duel."
                        if winner_side != "draw"
                        else f"{home_manager_name} and {away_manager_name} cancelled each other out in a {rivalry_level} mirror duel."
                    ),
                    "fan_narrative": (
                        f"The stands generated a {fan_commentary_tone.replace('_', ' ')} reaction arc and tilted the night into {fan_narrative_tag.replace('_', ' ')}."
                    ),
                },
            }
        )

    def _resolve_or_create_career_player_record(
        self,
        session: Session,
        *,
        user: User,
        payload: CareerCreateRequest,
    ) -> Player:
        if payload.player_id:
            player = session.get(Player, payload.player_id)
            if player is None:
                raise UniverseNotFoundError("Requested player was not found.")
            return player
        display_name = (
            payload.player_name or user.display_name or user.full_name or user.username or user.email
        ).strip()
        if not display_name:
            raise UniverseValidationError("Career player creation requires a displayable player name.")
        player = Player(
            source_provider="career-mode",
            provider_external_id=f"career:{user.id}",
            full_name=display_name,
            position=payload.position,
            normalized_position=(payload.position or "").strip().upper() or None,
            current_club_id=None,
            current_competition_id=None,
            current_club_profile_id=None,
            first_name=display_name.split(" ")[0] if " " in display_name else display_name,
            last_name=display_name.split(" ")[-1] if " " in display_name else None,
            short_name=display_name,
            is_tradable=True,
            is_real_player=False,
            morale=55.0,
            canonical_display_name=display_name,
            dna_profile={"career_mode_user_id": user.id},
            last_synced_at=utcnow(),
        )
        session.add(player)
        session.flush()
        return player

    def _career_player_by_user_id(self, session: Session, user_id: str) -> CareerPlayer | None:
        return session.scalar(select(CareerPlayer).where(CareerPlayer.user_id == user_id))

    def _ensure_career_active(self, career_player: CareerPlayer) -> None:
        if career_player.status != CareerPlayerStatus.ACTIVE:
            raise UniverseConflictError("Career player is no longer active.")

    def _default_career_stats(self) -> dict[str, Any]:
        return {
            "appearances": 0,
            "goals": 0,
            "assists": 0,
            "wins": 0,
            "losses": 0,
            "training_sessions": 0,
            "transfers": 0,
            "xp_gained": 0,
            "real_world_sync_hits": 0,
        }

    def _career_stats(self, career_player: CareerPlayer) -> dict[str, Any]:
        stats = dict(career_player.career_stats or {})
        for key, value in self._default_career_stats().items():
            stats.setdefault(key, value)
        return stats

    def _create_or_roll_forward_career_tenure(
        self,
        session: Session,
        *,
        career_player: CareerPlayer,
        club_name: str | None,
        wage_amount: Decimal,
        contract_days: int,
        notes: str | None,
    ) -> None:
        today = date.today()
        self._close_active_career_commitments(session, career_player=career_player, end_on=today)
        session.add(
            PlayerCareerEntry(
                player_id=career_player.player_id,
                club_id=career_player.current_club_id,
                club_name=club_name or "Independent",
                season_label=self._season_label(today),
                squad_role="career_mode",
                appearances=0,
                goals=0,
                assists=0,
                honours_json=[],
                notes=notes,
                start_on=today,
                end_on=None,
            )
        )
        session.add(
            PlayerContract(
                player_id=career_player.player_id,
                club_id=career_player.current_club_id,
                status="active",
                wage_amount=wage_amount,
                bonus_terms="career_mode",
                release_clause_amount=None,
                signed_on=today,
                starts_on=today,
                ends_on=today + timedelta(days=contract_days),
                extension_option_until=None,
            )
        )

    def _close_active_career_commitments(self, session: Session, *, career_player: CareerPlayer, end_on: date) -> None:
        active_entries = session.scalars(
            select(PlayerCareerEntry).where(
                PlayerCareerEntry.player_id == career_player.player_id, PlayerCareerEntry.end_on.is_(None)
            )
        ).all()
        for entry in active_entries:
            entry.end_on = end_on
        active_contracts = session.scalars(
            select(PlayerContract).where(
                PlayerContract.player_id == career_player.player_id, PlayerContract.status == "active"
            )
        ).all()
        for contract in active_contracts:
            contract.status = "ended"
            contract.ends_on = end_on

    def _apply_career_market_reaction(
        self,
        session: Session,
        *,
        user: User,
        career_player: CareerPlayer,
        won: bool | None,
        reason: str,
        boost: float,
    ) -> None:
        asset = self.creator_market_service.ensure_asset_for_user(session, user)
        asset.demand_score = self._amount(asset.demand_score + Decimal(str(max(0.2, boost * 4.0))))
        asset.momentum_score = self._amount(asset.momentum_score + Decimal(str(max(0.1, boost * 2.0))))
        if won is True:
            asset.total_matches += 1
            asset.total_wins += 1
        elif won is False:
            asset.total_matches += 1
        self.creator_market_service.recalculate_asset_price(session, player_id=asset.id, reason=reason)
        career_player.marketability_score = self._clamp(
            career_player.marketability_score + min(0.15, boost / 3),
            minimum=0.0,
            maximum=1.0,
        )

    def _get_or_create_provider(self, session: Session, *, name: str, endpoint: str) -> RealDataProvider:
        provider = session.scalar(select(RealDataProvider).where(RealDataProvider.name == name))
        if provider is None:
            provider = RealDataProvider(
                name=name,
                api_endpoint=endpoint,
                refresh_interval=3600,
                normalization_profile_version="real_player_v1",
                is_active=True,
                metadata_json={"created_by": "gtex_universe"},
            )
            session.add(provider)
            session.flush()
        else:
            provider.api_endpoint = endpoint
        return provider

    def _upsert_competitions(
        self,
        session: Session,
        *,
        provider: RealDataProvider,
        inputs: list[SyncCompetitionInput],
    ) -> dict[str, RealCompetition]:
        items: dict[str, RealCompetition] = {}
        for payload in inputs:
            competition = session.scalar(
                select(RealCompetition).where(
                    RealCompetition.provider_id == provider.id,
                    RealCompetition.external_key == payload.external_key,
                )
            )
            if competition is None:
                competition = RealCompetition(
                    provider_id=provider.id, external_key=payload.external_key, name=payload.name
                )
                session.add(competition)
            competition.name = payload.name
            competition.country_name = payload.country_name
            competition.competition_type = payload.competition_type
            competition.last_updated = utcnow()
            competition.metadata_json = {"synced_by": "gtex_universe"}
            session.flush()
            items[payload.external_key] = competition
        return items

    def _upsert_clubs(
        self,
        session: Session,
        *,
        provider: RealDataProvider,
        competitions: dict[str, RealCompetition],
        inputs: list[SyncClubInput],
    ) -> dict[str, RealClub]:
        items: dict[str, RealClub] = {}
        for payload in inputs:
            club = session.scalar(
                select(RealClub).where(
                    RealClub.provider_id == provider.id,
                    RealClub.external_key == payload.external_key,
                )
            )
            if club is None:
                club = RealClub(provider_id=provider.id, external_key=payload.external_key, name=payload.name)
                session.add(club)
            club.name = payload.name
            club.country_name = payload.country_name
            club.competition_id = (
                competitions.get(payload.competition_external_key).id
                if payload.competition_external_key in competitions
                else None
            )
            club.last_updated = utcnow()
            club.metadata_json = {"gtex_team_type": payload.gtex_team_type}
            session.flush()
            items[payload.external_key] = club
            if payload.gtex_team_id:
                self._upsert_entity_mapping(
                    session,
                    mapping_type=RealWorldMappingType.TEAM,
                    real_entity_id=club.id,
                    real_entity_key=payload.external_key,
                    gtex_entity_id=payload.gtex_team_id,
                    gtex_entity_type=payload.gtex_team_type,
                    confidence_score=0.95,
                    mapping_source="explicit",
                )
        return items

    def _upsert_players(
        self,
        session: Session,
        *,
        provider: RealDataProvider,
        competitions: dict[str, RealCompetition],
        clubs: dict[str, RealClub],
        inputs: list[SyncPlayerInput],
    ) -> dict[str, RealPlayer]:
        items: dict[str, RealPlayer] = {}
        for payload in inputs:
            player = session.scalar(
                select(RealPlayer).where(
                    RealPlayer.provider_id == provider.id,
                    RealPlayer.external_key == payload.external_key,
                )
            )
            if player is None:
                player = RealPlayer(provider_id=provider.id, external_key=payload.external_key, name=payload.name)
                session.add(player)
            mapped_player = self._resolve_gtex_player(session, payload)
            player.name = payload.name
            player.gtex_player_id = mapped_player.id if mapped_player is not None else payload.gtex_player_id
            player.real_club_id = (
                clubs.get(payload.club_external_key).id if payload.club_external_key in clubs else None
            )
            player.real_competition_id = (
                competitions.get(payload.competition_external_key).id
                if payload.competition_external_key in competitions
                else None
            )
            player.nationality = payload.nationality
            player.position = payload.position
            player.real_world_rating = payload.real_world_rating
            player.normalized_rating = self._clamp(payload.real_world_rating, minimum=0.0, maximum=100.0)
            player.attributes_json = dict(payload.stats_json or {})
            player.injury_status = payload.injury_status
            player.soft_injury_impact = self._soft_injury_impact(payload.injury_status)
            player.metadata_json = {"market_value": payload.market_value}
            player.last_updated = utcnow()
            session.flush()
            items[payload.external_key] = player
            if player.gtex_player_id:
                self._upsert_entity_mapping(
                    session,
                    mapping_type=RealWorldMappingType.PLAYER,
                    real_entity_id=player.id,
                    real_entity_key=payload.external_key,
                    gtex_entity_id=player.gtex_player_id,
                    gtex_entity_type="player",
                    confidence_score=0.92 if payload.gtex_player_id else 0.75,
                    mapping_source="explicit" if payload.gtex_player_id else "heuristic",
                )
            self._apply_real_player_influence(session, payload=payload, mapped_player=mapped_player)
        return items

    def _upsert_events(
        self,
        session: Session,
        *,
        provider: RealDataProvider,
        competitions: dict[str, RealCompetition],
        clubs: dict[str, RealClub],
        inputs: list[SyncEventInput],
    ) -> dict[str, RealWorldEvent]:
        items: dict[str, RealWorldEvent] = {}
        for payload in inputs:
            event = session.scalar(
                select(RealWorldEvent).where(
                    RealWorldEvent.provider_id == provider.id,
                    RealWorldEvent.external_key == payload.external_key,
                )
            )
            if event is None:
                event = RealWorldEvent(
                    provider_id=provider.id,
                    external_key=payload.external_key,
                    headline=payload.headline or payload.external_key,
                    scheduled_at=payload.scheduled_at,
                )
                session.add(event)
            event.competition_id = (
                competitions.get(payload.competition_external_key).id
                if payload.competition_external_key in competitions
                else None
            )
            event.home_club_id = (
                clubs.get(payload.home_club_external_key).id if payload.home_club_external_key in clubs else None
            )
            event.away_club_id = (
                clubs.get(payload.away_club_external_key).id if payload.away_club_external_key in clubs else None
            )
            event.headline = payload.headline or self._event_headline(payload, clubs)
            event.event_type = payload.event_type
            event.status = RealWorldEventStatus(payload.status)
            event.scheduled_at = payload.scheduled_at
            event.started_at = (
                payload.scheduled_at
                if payload.status in {RealWorldEventStatus.LIVE.value, RealWorldEventStatus.COMPLETED.value}
                else None
            )
            event.completed_at = utcnow() if payload.status == RealWorldEventStatus.COMPLETED.value else None
            event.home_score = payload.home_score
            event.away_score = payload.away_score
            event.magnitude_score = round(
                min(1.0, payload.importance + (0.15 if payload.status == "completed" else 0.0)), 4
            )
            event.metadata_json = {"featured_player_keys": list(payload.featured_player_keys)}
            event.influence_summary_json = dict(event.influence_summary_json or {})
            session.flush()
            items[payload.external_key] = event
        return items

    def _mirror_real_world_event(
        self,
        session: Session,
        *,
        actor: User,
        event: RealWorldEvent,
        career_user_id: str | None,
    ) -> GtexMatch | None:
        existing = session.get(GtexMatch, event.mirror_match_id) if event.mirror_match_id else None
        if existing is not None:
            return existing
        league = session.scalar(select(GtexLeague).where(GtexLeague.code == "elite"))
        if league is None:
            raise UniverseNotFoundError("GTEX elite league was not found while mirroring a real-world event.")
        home_club = session.get(RealClub, event.home_club_id) if event.home_club_id else None
        away_club = session.get(RealClub, event.away_club_id) if event.away_club_id else None
        home_ai = self._resolve_ai_for_real_club(session, club=home_club, league=league)
        away_ai = self._resolve_ai_for_real_club(
            session, club=away_club, league=league, exclude_ai_id=home_ai.id if home_ai else None
        )
        if home_ai is None or away_ai is None:
            return None
        career_player = self._career_player_by_user_id(session, career_user_id) if career_user_id else None
        career_side = self._career_side(career_player, home_club, away_club)
        match = GtexMatch(
            league_id=league.id,
            requested_by_user_id=actor.id,
            status=GtexMatchStatus.MATCHED,
            home_participant_type=GtexParticipantType.AI,
            home_user_id=None,
            home_ai_id=home_ai.id,
            away_participant_type=GtexParticipantType.AI,
            away_user_id=None,
            away_ai_id=away_ai.id,
            entry_fee=Decimal("0.0000"),
            effective_pot=Decimal("0.0000"),
            jackpot_contribution=Decimal("0.0000"),
            home_score=0,
            away_score=0,
            queued_at=utcnow(),
            started_at=utcnow(),
            metadata_json={
                "real_world_event_id": event.id,
                "mirror_source": "real_world_sync",
                "real_world_headline": event.headline,
                "home_real_club": home_club.name if home_club is not None else None,
                "away_real_club": away_club.name if away_club is not None else None,
                "career_player_id": career_player.id if career_player is not None else None,
                "career_user_id": career_player.user_id if career_player is not None else None,
                "career_side": career_side,
            },
        )
        session.add(match)
        session.flush()
        event.mirror_match_id = match.id
        if event.status in {RealWorldEventStatus.LIVE, RealWorldEventStatus.COMPLETED}:
            self.ai_leagues.simulate_match(session, match_id=match.id)
        return match

    def _resolve_ai_for_real_club(
        self,
        session: Session,
        *,
        club: RealClub | None,
        league: GtexLeague,
        exclude_ai_id: str | None = None,
    ) -> GtexAIProfile | None:
        if club is not None:
            mapping = session.scalar(
                select(RealWorldEntityMapping).where(
                    RealWorldEntityMapping.mapping_type == RealWorldMappingType.TEAM,
                    RealWorldEntityMapping.real_entity_id == club.id,
                    RealWorldEntityMapping.gtex_entity_type == "ai_profile",
                )
            )
            if mapping is not None:
                ai = session.get(GtexAIProfile, mapping.gtex_entity_id)
                if ai is not None and ai.id != exclude_ai_id:
                    self._ensure_manager_profile_for_ai(session, ai)
                    return ai
        ai_profiles = session.scalars(
            select(GtexAIProfile)
            .where(GtexAIProfile.league_id == league.id, GtexAIProfile.is_active.is_(True))
            .order_by(GtexAIProfile.elo.desc(), GtexAIProfile.name.asc())
        ).all()
        candidates = [item for item in ai_profiles if item.id != exclude_ai_id]
        if not candidates:
            return None
        if club is None:
            ai = candidates[0]
        else:
            index = self._stable_int(club.external_key, modulo=len(candidates))
            ai = candidates[index]
            self._upsert_entity_mapping(
                session,
                mapping_type=RealWorldMappingType.TEAM,
                real_entity_id=club.id,
                real_entity_key=club.external_key,
                gtex_entity_id=ai.id,
                gtex_entity_type="ai_profile",
                confidence_score=0.64,
                mapping_source="mirror_allocator",
            )
        self._ensure_manager_profile_for_ai(session, ai)
        return ai

    def _resolve_gtex_player(self, session: Session, payload: SyncPlayerInput) -> Player | None:
        if payload.gtex_player_id:
            direct = session.get(Player, payload.gtex_player_id)
            if direct is not None:
                return direct
        lowered_name = payload.name.strip().lower()
        for player in session.scalars(
            select(Player).where(or_(Player.full_name == payload.name, Player.canonical_display_name == payload.name))
        ).all():
            if (player.full_name or "").strip().lower() == lowered_name or (
                player.canonical_display_name or ""
            ).strip().lower() == lowered_name:
                return player
        career = session.scalar(
            select(CareerPlayer)
            .join(Player, Player.id == CareerPlayer.player_id)
            .where(Player.full_name == payload.name)
        )
        return session.get(Player, career.player_id) if career is not None else None

    def _apply_real_player_influence(
        self, session: Session, *, payload: SyncPlayerInput, mapped_player: Player | None
    ) -> None:
        performance_index = self._performance_index(payload.stats_json, payload.real_world_rating)
        if mapped_player is not None:
            mapped_player.morale = self._clamp(
                mapped_player.morale + (performance_index * 12.0), minimum=0.0, maximum=100.0
            )
            market_reference = (
                mapped_player.current_market_reference_value
                or mapped_player.market_value_eur
                or payload.market_value
                or 0.0
            )
            if market_reference:
                mapped_player.current_market_reference_value = round(
                    max(0.0, market_reference * (1 + (performance_index * 0.08))), 2
                )
            mapped_player.dna_profile = {
                **dict(mapped_player.dna_profile or {}),
                "real_world_form": round(performance_index, 4),
                "real_world_rating": payload.real_world_rating,
            }
            mapped_player.last_synced_at = utcnow()
        if mapped_player is None:
            return
        career = session.scalar(select(CareerPlayer).where(CareerPlayer.player_id == mapped_player.id))
        if career is None:
            return
        career.current_form = self._clamp(career.current_form + (performance_index * 0.18), minimum=0.1, maximum=1.0)
        career.marketability_score = self._clamp(
            career.marketability_score + (performance_index * 0.12), minimum=0.0, maximum=1.0
        )
        stats = self._career_stats(career)
        stats["real_world_sync_hits"] += 1
        career.career_stats = stats
        owner = session.get(User, career.user_id)
        if owner is not None:
            self._apply_career_market_reaction(
                session,
                user=owner,
                career_player=career,
                won=performance_index > 0.05,
                reason="real_world_sync",
                boost=abs(performance_index),
            )

    def _resolve_manager_for_participant(
        self, session: Session, participant: SimulatedParticipant
    ) -> ManagerProfile | None:
        if participant.ai is not None:
            return self._ensure_manager_profile_for_ai(session, participant.ai)
        if participant.user is None:
            return None
        return session.scalar(
            select(ManagerProfile).where(
                ManagerProfile.manager_id == participant.user.id,
                ManagerProfile.gtex_ai_id.is_(None),
            )
        )

    def _ensure_manager_profile_for_ai(self, session: Session, ai: GtexAIProfile) -> ManagerProfile:
        profile = session.scalar(select(ManagerProfile).where(ManagerProfile.gtex_ai_id == ai.id))
        if profile is not None:
            return profile
        tactical_style = self._manager_style_from_ai(ai)
        profile = ManagerProfile(
            manager_id=None,
            gtex_ai_id=ai.id,
            name=ai.name,
            bio=f"{ai.name} is a GTEX AI manager built around {tactical_style.value} football.",
            preferred_style=tactical_style.value,
            tactical_style=tactical_style,
            risk_tolerance=round(self._clamp(float(ai.aggression) * 0.95, minimum=0.1, maximum=0.95), 4),
            adaptability=round(self._clamp(float(ai.adaptation_rate), minimum=0.1, maximum=0.99), 4),
            ego_level=round(self._clamp(float(ai.skill_level) * 0.9, minimum=0.2, maximum=0.95), 4),
            youth_preference=round(0.2 + (self._stable_ratio(ai.id, "youth") * 0.6), 4),
            discipline_style=self._manager_discipline_from_ai(ai),
            formation_preferences_json=list(_TACTICAL_STYLE_FORMATIONS[tactical_style]),
            substitution_logic=_TACTICAL_STYLE_SUBSTITUTIONS[tactical_style],
            tempo_control=_TACTICAL_STYLE_TEMPO[tactical_style],
            control_mode=ManagerControlMode.REAL_MANAGER,
            matches_managed=0,
            wins=0,
            losses=0,
            reputation_score=max(0, ai.elo - 950),
            hourly_fee=Decimal("0.00"),
            is_available=False,
            current_losing_streak=0,
        )
        session.add(profile)
        session.flush()
        return profile

    def _update_manager_records(
        self,
        session: Session,
        *,
        match: GtexMatch,
        home_manager: ManagerProfile | None,
        away_manager: ManagerProfile | None,
        intensity_score: float,
        rivalry: ManagerVsManagerHistory | None,
    ) -> None:
        if home_manager is None and away_manager is None:
            return
        if match.home_score > match.away_score:
            home_result, away_result = "win", "loss"
        elif match.home_score < match.away_score:
            home_result, away_result = "loss", "win"
        else:
            home_result = away_result = "draw"
        updated_rivalry: ManagerVsManagerHistory | None = None
        rivalry_payload: dict[str, Any] = {}
        if home_manager is not None and away_manager is not None:
            updated_rivalry = self._upsert_manager_rivalry(
                session, home_manager, away_manager, home_result, intensity_score
            )
            updated_rivalry.last_match_at = utcnow()
            rivalry_payload = {
                "meetings": updated_rivalry.meetings,
                "rivalry_score": round(float(updated_rivalry.rivalry_score), 4),
                "narrative_tag": updated_rivalry.narrative_tag,
            }
        if home_manager is not None:
            self._apply_manager_result(home_manager, home_result)
            session.add(
                ManagerMatchHistory(
                    manager_profile_id=home_manager.id,
                    opponent_manager_profile_id=away_manager.id if away_manager is not None else None,
                    source_match_id=match.id,
                    source_match_type="gtex",
                    team_side="home",
                    result=home_result,
                    intensity_score=intensity_score,
                    rivalry_score=float(updated_rivalry.rivalry_score) if updated_rivalry is not None else 0.0,
                    tactical_snapshot_json=self._manager_snapshot(home_manager),
                    narrative_summary=f"{self._manager_name(home_manager)} finished {home_result} after a {match.home_score}-{match.away_score} result.",
                    metadata_json={"match_id": match.id, "rivalry": rivalry_payload},
                )
            )
        if away_manager is not None:
            self._apply_manager_result(away_manager, away_result)
            session.add(
                ManagerMatchHistory(
                    manager_profile_id=away_manager.id,
                    opponent_manager_profile_id=home_manager.id if home_manager is not None else None,
                    source_match_id=match.id,
                    source_match_type="gtex",
                    team_side="away",
                    result=away_result,
                    intensity_score=intensity_score,
                    rivalry_score=float(updated_rivalry.rivalry_score) if updated_rivalry is not None else 0.0,
                    tactical_snapshot_json=self._manager_snapshot(away_manager),
                    narrative_summary=f"{self._manager_name(away_manager)} finished {away_result} after a {match.away_score}-{match.home_score} result.",
                    metadata_json={"match_id": match.id, "rivalry": rivalry_payload},
                )
            )

    def _apply_career_match_impact(
        self, session: Session, *, match: GtexMatch, context: dict[str, Any]
    ) -> dict[str, Any]:
        career_context = dict(context.get("career_context") or {})
        career_player_id = career_context.get("career_player_id")
        if not career_player_id:
            return {}
        career_player = session.get(CareerPlayer, career_player_id)
        if career_player is None:
            return {}
        owner = session.get(User, career_player.user_id)
        player = session.get(Player, career_player.player_id)
        if owner is None or player is None:
            return {}
        side = career_context.get("side")
        side_scored = match.home_score if side == "home" else match.away_score
        conceded = match.away_score if side == "home" else match.home_score
        won = side_scored > conceded
        contribution_roll = self._stable_ratio(match.id, career_player.id)
        goals = 1 if side_scored > 0 and contribution_roll >= 0.66 else 0
        assists = 1 if side_scored > goals and contribution_roll <= 0.74 else 0
        xp_gain = 24 + (career_player.level * 4) + (14 if won else 6)
        career_player.xp += xp_gain
        career_player.level = max(1, 1 + (career_player.xp // 250))
        career_player.current_form = self._clamp(
            career_player.current_form + (0.08 if won else 0.03), minimum=0.1, maximum=1.0
        )
        career_player.prestige_score += 12 if won else 4
        stats = self._career_stats(career_player)
        stats["appearances"] += 1
        stats["goals"] += goals
        stats["assists"] += assists
        if won:
            stats["wins"] += 1
        else:
            stats["losses"] += 1
        stats["xp_gained"] += xp_gain
        career_player.career_stats = stats
        self._apply_career_market_reaction(
            session,
            user=owner,
            career_player=career_player,
            won=won,
            reason="career_match_participation",
            boost=0.18 if won else 0.08,
        )
        return {
            "career_player_id": career_player.id,
            "player_name": player.full_name,
            "side": side,
            "won": won,
            "goals": goals,
            "assists": assists,
            "xp_gain": xp_gain,
            "level": career_player.level,
            "prestige_score": career_player.prestige_score,
        }

    def _career_participation_context(
        self,
        session: Session,
        *,
        match: GtexMatch,
        real_event: RealWorldEvent | None,
    ) -> dict[str, Any]:
        metadata = dict(match.metadata_json or {})
        career_player = (
            session.get(CareerPlayer, metadata.get("career_player_id")) if metadata.get("career_player_id") else None
        )
        side = str(metadata.get("career_side") or "")
        if career_player is None and metadata.get("career_user_id"):
            career_player = self._career_player_by_user_id(session, str(metadata["career_user_id"]))
            side = side or "home"
        if career_player is None and real_event is not None:
            home_club = session.get(RealClub, real_event.home_club_id) if real_event.home_club_id else None
            away_club = session.get(RealClub, real_event.away_club_id) if real_event.away_club_id else None
            candidates = session.scalars(
                select(CareerPlayer).where(CareerPlayer.status == CareerPlayerStatus.ACTIVE)
            ).all()
            for candidate in candidates:
                if (
                    home_club is not None
                    and candidate.current_club
                    and candidate.current_club.lower() == home_club.name.lower()
                ):
                    career_player = candidate
                    side = "home"
                    break
                if (
                    away_club is not None
                    and candidate.current_club
                    and candidate.current_club.lower() == away_club.name.lower()
                ):
                    career_player = candidate
                    side = "away"
                    break
        if career_player is None or side not in {"home", "away"}:
            return {"career_player_id": None, "side": None, "strength_bonus": 0.0, "intensity_bonus": 0.0}
        strength_bonus = round(
            min(
                0.18,
                (career_player.current_form * 0.08) + (career_player.level * 0.01) + (career_player.growth_rate * 0.22),
            ),
            4,
        )
        intensity_bonus = round(min(0.18, career_player.marketability_score * 0.12), 4)
        return {
            "career_player_id": career_player.id,
            "career_user_id": career_player.user_id,
            "side": side,
            "strength_bonus": strength_bonus,
            "intensity_bonus": intensity_bonus,
        }

    def _real_world_event_for_match(self, session: Session, match: GtexMatch) -> RealWorldEvent | None:
        metadata = dict(match.metadata_json or {})
        event_id = metadata.get("real_world_event_id")
        return session.get(RealWorldEvent, event_id) if event_id else None

    def _real_world_event_strength_boost(self, event: RealWorldEvent) -> dict[str, float]:
        if event.home_score is None or event.away_score is None or event.status != RealWorldEventStatus.COMPLETED:
            return {"home": 0.0, "away": 0.0}
        delta = max(-0.08, min(0.08, (event.home_score - event.away_score) * 0.02))
        return {"home": max(0.0, delta), "away": max(0.0, -delta)}

    def _manager_style_from_ai(self, ai: GtexAIProfile) -> ManagerPersonalityTacticalStyle:
        playstyle = (ai.playstyle or "").strip().lower()
        if playstyle in {"pressing", "aggressive"}:
            return ManagerPersonalityTacticalStyle.ATTACKING
        if playstyle in {"counter", "contain", "low_block"}:
            return ManagerPersonalityTacticalStyle.DEFENSIVE
        return ManagerPersonalityTacticalStyle.BALANCED

    def _manager_discipline_from_ai(self, ai: GtexAIProfile) -> ManagerDisciplineStyle:
        aggression = float(ai.aggression)
        if aggression >= 0.72:
            return ManagerDisciplineStyle.STRICT
        if aggression <= 0.42:
            return ManagerDisciplineStyle.EMPOWERING
        return ManagerDisciplineStyle.BALANCED

    def _manager_strength_bonus(self, profile: ManagerProfile | None) -> float:
        if profile is None:
            return 0.0
        style_bonus = {
            ManagerPersonalityTacticalStyle.ATTACKING: 0.08,
            ManagerPersonalityTacticalStyle.DEFENSIVE: 0.04,
            ManagerPersonalityTacticalStyle.BALANCED: 0.06,
        }[profile.tactical_style]
        return round(
            min(0.22, style_bonus + (float(profile.adaptability) * 0.07) + (float(profile.risk_tolerance) * 0.05)),
            4,
        )

    def _manager_aggression_bonus(self, profile: ManagerProfile | None) -> float:
        if profile is None:
            return 0.0
        style_bias = {
            ManagerPersonalityTacticalStyle.ATTACKING: 0.12,
            ManagerPersonalityTacticalStyle.DEFENSIVE: -0.05,
            ManagerPersonalityTacticalStyle.BALANCED: 0.02,
        }[profile.tactical_style]
        return round(style_bias + (float(profile.ego_level) * 0.05), 4)

    def _manager_rivalry(
        self,
        session: Session,
        first: ManagerProfile | None,
        second: ManagerProfile | None,
    ) -> ManagerVsManagerHistory | None:
        if first is None or second is None:
            return None
        manager_a_id, manager_b_id = sorted((first.id, second.id))
        return session.scalar(
            select(ManagerVsManagerHistory).where(
                ManagerVsManagerHistory.manager_a_id == manager_a_id,
                ManagerVsManagerHistory.manager_b_id == manager_b_id,
            )
        )

    def _upsert_manager_rivalry(
        self,
        session: Session,
        first: ManagerProfile,
        second: ManagerProfile,
        first_result: str,
        intensity_score: float,
    ) -> ManagerVsManagerHistory:
        manager_a_id, manager_b_id = sorted((first.id, second.id))
        rivalry = self._manager_rivalry(session, first, second)
        if rivalry is None:
            rivalry = ManagerVsManagerHistory(
                manager_a_id=manager_a_id,
                manager_b_id=manager_b_id,
                meetings=0,
                manager_a_wins=0,
                manager_b_wins=0,
                draws=0,
                rivalry_score=0.0,
                narrative_tag="fresh",
                metadata_json={},
            )
            session.add(rivalry)
            session.flush()
        rivalry.meetings += 1
        if first_result == "draw":
            rivalry.draws += 1
        elif first_result == "win":
            if first.id == manager_a_id:
                rivalry.manager_a_wins += 1
            else:
                rivalry.manager_b_wins += 1
        else:
            if first.id == manager_a_id:
                rivalry.manager_b_wins += 1
            else:
                rivalry.manager_a_wins += 1
        rivalry.rivalry_score = round(min(1.0, float(rivalry.rivalry_score) + 0.10 + (intensity_score * 0.12)), 4)
        rivalry.narrative_tag = self._rivalry_level(float(rivalry.rivalry_score))
        return rivalry

    def _apply_manager_result(self, profile: ManagerProfile, result: str) -> None:
        profile.matches_managed += 1
        if result == "win":
            profile.wins += 1
            profile.reputation_score += 12
            profile.current_losing_streak = 0
        elif result == "loss":
            profile.losses += 1
            profile.reputation_score -= 4
            profile.current_losing_streak += 1
        else:
            profile.reputation_score += 1
            profile.current_losing_streak = 0

    def _event_headline(self, payload: SyncEventInput, clubs: dict[str, RealClub]) -> str:
        home = clubs.get(payload.home_club_external_key)
        away = clubs.get(payload.away_club_external_key)
        if home is not None and away is not None:
            return f"{home.name} vs {away.name}"
        return payload.external_key

    def _upsert_entity_mapping(
        self,
        session: Session,
        *,
        mapping_type: RealWorldMappingType,
        real_entity_id: str,
        real_entity_key: str,
        gtex_entity_id: str,
        gtex_entity_type: str,
        confidence_score: float,
        mapping_source: str,
    ) -> RealWorldEntityMapping:
        mapping = session.scalar(
            select(RealWorldEntityMapping).where(
                RealWorldEntityMapping.mapping_type == mapping_type,
                RealWorldEntityMapping.real_entity_id == real_entity_id,
                RealWorldEntityMapping.gtex_entity_id == gtex_entity_id,
            )
        )
        if mapping is None:
            mapping = RealWorldEntityMapping(
                mapping_type=mapping_type,
                real_entity_id=real_entity_id,
                real_entity_key=real_entity_key,
                gtex_entity_id=gtex_entity_id,
                gtex_entity_type=gtex_entity_type,
                confidence_score=confidence_score,
                mapping_source=mapping_source,
                metadata_json={},
            )
            session.add(mapping)
        else:
            mapping.real_entity_key = real_entity_key
            mapping.gtex_entity_type = gtex_entity_type
            mapping.confidence_score = confidence_score
            mapping.mapping_source = mapping_source
        session.flush()
        return mapping

    def _manager_name(self, profile: ManagerProfile | None) -> str:
        if profile is None:
            return "Unknown Manager"
        if profile.name:
            return profile.name
        if profile.manager_id:
            return profile.manager_id
        return f"Manager {profile.id[:8]}"

    def _manager_snapshot(self, profile: ManagerProfile | None) -> dict[str, Any]:
        if profile is None:
            return {}
        return {
            "id": profile.id,
            "name": self._manager_name(profile),
            "tactical_style": profile.tactical_style.value,
            "risk_tolerance": round(float(profile.risk_tolerance), 4),
            "adaptability": round(float(profile.adaptability), 4),
            "ego_level": round(float(profile.ego_level), 4),
            "youth_preference": round(float(profile.youth_preference), 4),
            "discipline_style": profile.discipline_style.value,
            "formation_preferences": list(profile.formation_preferences_json or []),
            "substitution_logic": profile.substitution_logic,
            "tempo_control": profile.tempo_control,
        }

    def _manager_primary_formation(self, profile: ManagerProfile | None) -> str:
        formations = list((profile.formation_preferences_json if profile is not None else []) or [])
        return formations[0] if formations else "4-2-3-1"

    def _manager_tempo(self, profile: ManagerProfile | None) -> str:
        return profile.tempo_control if profile is not None else "balanced"

    def _real_world_snapshot(self, event: RealWorldEvent | None) -> dict[str, Any]:
        if event is None:
            return {}
        return {
            "event_id": event.id,
            "headline": event.headline,
            "status": event.status.value,
            "mirror_match_id": event.mirror_match_id,
            "magnitude_score": round(float(event.magnitude_score), 4),
        }

    def _performance_index(self, stats_json: dict[str, Any], real_world_rating: float) -> float:
        goals = float(stats_json.get("goals") or 0.0)
        assists = float(stats_json.get("assists") or 0.0)
        clean_sheets = float(stats_json.get("clean_sheets") or 0.0)
        rating = float(stats_json.get("match_rating") or real_world_rating or 50.0)
        minutes = max(1.0, float(stats_json.get("minutes") or 90.0))
        raw = ((goals * 0.18) + (assists * 0.12) + (clean_sheets * 0.08) + ((rating - 50.0) / 100.0)) * min(
            1.0, minutes / 90.0
        )
        return round(max(-0.35, min(0.35, raw)), 4)

    def _soft_injury_impact(self, injury_status: str | None) -> float:
        if not injury_status:
            return 0.0
        lowered = injury_status.strip().lower()
        if lowered in {"out", "major", "serious"}:
            return 0.18
        if lowered in {"doubtful", "minor"}:
            return 0.08
        return 0.02

    def _current_club_name(self, player: Player) -> str | None:
        return player.real_world_club_name or (
            player.current_club.name if getattr(player, "current_club", None) is not None else None
        )

    def _season_label(self, today: date) -> str:
        return f"{today.year}-{today.year + 1}"

    @classmethod
    def _json_safe(cls, value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {str(key): cls._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._json_safe(item) for item in value]
        if isinstance(value, StrEnum):
            return value.value
        return value

    @staticmethod
    def _clamp(value: float, *, minimum: float, maximum: float) -> float:
        return round(max(minimum, min(maximum, value)), 4)

    @staticmethod
    def _rivalry_level(score: float) -> str:
        for threshold, label in _INTENSITY_BY_RIVALRY:
            if score >= threshold:
                return label
        return "fresh"

    @staticmethod
    def _stable_int(seed: str, *, modulo: int) -> int:
        digest = sha256(seed.encode("utf-8")).hexdigest()
        return int(digest[:12], 16) % max(1, modulo)

    @staticmethod
    def _stable_ratio(seed: str, salt: str) -> float:
        digest = sha256(f"{seed}:{salt}".encode("utf-8")).hexdigest()
        return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)

    def _career_side(
        self, career_player: CareerPlayer | None, home_club: RealClub | None, away_club: RealClub | None
    ) -> str | None:
        if career_player is None or not career_player.current_club:
            return None
        lowered_club = career_player.current_club.strip().lower()
        if home_club is not None and home_club.name.strip().lower() == lowered_club:
            return "home"
        if away_club is not None and away_club.name.strip().lower() == lowered_club:
            return "away"
        return None
