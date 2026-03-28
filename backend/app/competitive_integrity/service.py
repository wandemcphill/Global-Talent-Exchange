from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import pow
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.competitive_integrity.delivery import PushDeliveryGateway, SmsDeliveryGateway
from app.competitive_integrity.schemas import (
    CompetitiveMatchCreateRequest,
    CompetitiveMatchExecuteRequest,
    CompetitiveMatchExecutionView,
    CompetitiveMatchView,
    CompetitiveNotificationView,
    ControllerSummaryView,
    FastGamePlayRequest,
    FastGameResultView,
    FastGameRunStartRequest,
    FastGameRunView,
    ManagerCandidateView,
    ManagerCreateRequest,
    ManagerUpdateInstructionsRequest,
    ManagerView,
    MatchControlLogView,
    NotificationEventRequest,
    WorkerRunResultView,
)
from app.economy.economy_service import EconomyService
from app.football_universe.service import FootballUniverseService
from app.match_engine.schemas import (
    MatchCompetitionContextInput,
    MatchReplayPayloadView,
    MatchSimulationRequest,
    MatchTacticalAdjustmentInput,
    MatchTacticalChangeInput,
    MatchTeamInput,
)
from app.match_engine.services.match_simulation_service import MatchSimulationService
from app.match_engine.simulation.models import MatchCompetitionType as EngineCompetitionType
from app.match_engine.simulation.models import TacticalStyle
from app.models.competitive_integrity import (
    CompetitiveMatchCompetitionType,
    CompetitiveMatchStatus,
    CompetitiveNotificationChannel,
    CompetitiveNotificationStatus,
    FastGameRun,
    Manager,
    ManagerType,
    Match,
    MatchControllerType,
    MatchControlLog,
    MatchControlSide,
    Notification,
)
from app.models.user import User, UserRole
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerTransactionType, LedgerUnit
from app.wallets.service import LedgerPosting, WalletService

_REWARD_QUANTUM = Decimal("0.0001")
_UPSET_BONUS = 5.0
_REMINDER_OFFSETS_MINUTES = (30, 10, 2)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MatchSideResolution:
    is_user_online: bool
    manager: Manager | None = None


class CompetitiveIntegrityError(ValueError):
    pass


class AutomationRejectedError(CompetitiveIntegrityError):
    pass


class ManagerLockedError(CompetitiveIntegrityError):
    pass


def resolveController(side: MatchSideResolution) -> MatchControllerType:
    if side.is_user_online:
        return MatchControllerType.USER
    if side.manager is not None and side.manager.type is ManagerType.REAL_MANAGER:
        return MatchControllerType.MANAGER
    return MatchControllerType.FROZEN


def applyManagerInstructions(match_state: dict[str, Any], instructions: dict[str, Any]) -> list[dict[str, Any]]:
    applied: list[dict[str, Any]] = []
    current_minute = int(match_state.get("minute", 0))
    current_formation = str(match_state.get("formation") or "4-3-3")
    for rule in instructions.get("rules") or []:
        minute = int(rule.get("minute", 0))
        if minute > current_minute:
            continue
        if not _condition_met(rule.get("condition"), match_state):
            continue
        adjustment = _action_to_adjustment(rule.get("action"), current_formation=current_formation)
        if adjustment is None:
            continue
        payload = adjustment.model_dump(mode="json", exclude_none=True)
        payload["minute"] = minute
        payload["condition"] = rule.get("condition")
        applied.append(payload)
        if adjustment.formation:
            current_formation = adjustment.formation
    return applied


@dataclass(slots=True)
class CompetitiveIntegrityService:
    session: Session
    match_simulation_service: MatchSimulationService | None = None
    wallet_service: WalletService | None = None
    push_gateway: PushDeliveryGateway | None = None
    sms_gateway: SmsDeliveryGateway | None = None

    def __post_init__(self) -> None:
        if self.match_simulation_service is None:
            self.match_simulation_service = MatchSimulationService()
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.push_gateway is None:
            self.push_gateway = PushDeliveryGateway()
        if self.sms_gateway is None:
            self.sms_gateway = SmsDeliveryGateway()

    def list_managers(self, *, actor: User) -> list[ManagerView]:
        managers = list(
            self.session.scalars(
                select(Manager).where(Manager.user_id == actor.id).order_by(Manager.created_at.desc())
            ).all()
        )
        return [self._manager_view(item) for item in managers]

    def list_manager_candidates(self, *, actor: User) -> list[ManagerCandidateView]:
        users = list(
            self.session.scalars(
                select(User).where(User.id != actor.id, User.is_active.is_(True)).order_by(User.username.asc())
            ).all()
        )
        appointments = list(
            self.session.scalars(
                select(Manager).where(Manager.type == ManagerType.REAL_MANAGER, Manager.appointed_user_id.is_not(None))
            ).all()
        )
        aggregate: dict[str, list[float]] = {}
        for item in appointments:
            if item.appointed_user_id is None:
                continue
            aggregate.setdefault(item.appointed_user_id, []).append(float(item.reputation_score))
        views: list[ManagerCandidateView] = []
        for user in users:
            samples = aggregate.get(user.id, [])
            average = round(sum(samples) / len(samples), 2) if samples else 1000.0
            views.append(
                ManagerCandidateView(
                    user_id=user.id,
                    username=user.username,
                    display_name=user.display_name or user.full_name or user.username,
                    average_reputation=average,
                    prior_appointments=len(samples),
                )
            )
        return views

    def upsert_manager(self, *, actor: User, payload: ManagerCreateRequest) -> ManagerView:
        appointed_user = None
        if payload.type is ManagerType.REAL_MANAGER:
            appointed_user = self.session.get(User, payload.appointed_user_id)
            if appointed_user is None or not appointed_user.is_active:
                raise CompetitiveIntegrityError("The appointed real manager could not be found.")
            if appointed_user.id == actor.id:
                raise CompetitiveIntegrityError("Use type='user' when managing your own matches.")
        existing = self.session.scalar(
            select(Manager).where(
                Manager.user_id == actor.id,
                Manager.type == payload.type,
                Manager.appointed_user_id == payload.appointed_user_id,
            )
        )
        manager = existing or Manager(
            user_id=actor.id,
            type=payload.type,
            appointed_user_id=payload.appointed_user_id,
        )
        manager.instructions = payload.instructions.model_dump(mode="json", exclude_none=True)
        manager.tactical_profile = payload.tactical_profile.model_dump(mode="json", exclude_none=True)
        if existing is None:
            self.session.add(manager)
        self.session.flush()
        return self._manager_view(manager)

    def update_manager_instructions(self, *, actor: User, manager_id: str, payload: ManagerUpdateInstructionsRequest) -> ManagerView:
        manager = self._manager_for_owner(manager_id, actor.id)
        manager.instructions = payload.instructions.model_dump(mode="json", exclude_none=True)
        if payload.tactical_profile is not None:
            manager.tactical_profile = payload.tactical_profile.model_dump(mode="json", exclude_none=True)
        self.session.flush()
        return self._manager_view(manager)

    def schedule_match(self, *, actor: User, payload: CompetitiveMatchCreateRequest) -> CompetitiveMatchView:
        self._authorize_actor_for_users(actor, payload.home_user_id, payload.away_user_id)
        self._enforce_human_only(
            competition_type=payload.competition_type,
            ai_detected=payload.ai_detected,
            automation_detected=payload.automation_detected,
        )
        home_manager = self._manager_optional(payload.home_manager_id, owner_user_id=payload.home_user_id)
        away_manager = self._manager_optional(payload.away_manager_id, owner_user_id=payload.away_user_id)
        match = Match(
            competition_type=payload.competition_type,
            home_user_id=payload.home_user_id,
            away_user_id=payload.away_user_id,
            home_manager_id=home_manager.id if home_manager is not None else None,
            away_manager_id=away_manager.id if away_manager is not None else None,
            is_user_online_home=payload.is_user_online_home,
            is_user_online_away=payload.is_user_online_away,
            locked_lineup_home=payload.locked_lineup_home.model_dump(mode="json"),
            locked_lineup_away=payload.locked_lineup_away.model_dump(mode="json"),
            kickoff_at=payload.kickoff_at,
        )
        self.session.add(match)
        self.session.flush()
        self._queue_match_scheduled_notifications(match)
        return self._match_view(match)

    def get_match(self, *, actor: User, match_id: str) -> CompetitiveMatchView:
        return self._match_view(self._match_for_actor(match_id, actor))

    def execute_match(self, *, actor: User, match_id: str, payload: CompetitiveMatchExecuteRequest) -> CompetitiveMatchExecutionView:
        match = self._match_for_actor(match_id, actor)
        self._enforce_human_only(
            competition_type=match.competition_type,
            ai_detected=payload.ai_detected,
            automation_detected=payload.automation_detected,
        )
        if payload.is_user_online_home is not None:
            match.is_user_online_home = payload.is_user_online_home
        if payload.is_user_online_away is not None:
            match.is_user_online_away = payload.is_user_online_away
        home_manager = self._manager_optional(match.home_manager_id, owner_user_id=match.home_user_id)
        away_manager = self._manager_optional(match.away_manager_id, owner_user_id=match.away_user_id)
        controller_home = resolveController(
            MatchSideResolution(is_user_online=match.is_user_online_home, manager=home_manager)
        )
        controller_away = resolveController(
            MatchSideResolution(is_user_online=match.is_user_online_away, manager=away_manager)
        )
        if match.competition_type is CompetitiveMatchCompetitionType.GTEX_HOSTED and (
            controller_home is MatchControllerType.FROZEN or controller_away is MatchControllerType.FROZEN
        ):
            raise CompetitiveIntegrityError(
                "GTEX hosted matches require either the user or an appointed real manager on both sides."
            )
        self._log_controller(match, MatchControlSide.HOME, controller_home)
        self._log_controller(match, MatchControlSide.AWAY, controller_away)
        request = self._build_simulation_request(
            match=match,
            home_controller=controller_home,
            away_controller=controller_away,
            home_manager=home_manager,
            away_manager=away_manager,
            simulation_seed=payload.simulation_seed,
        )
        match.status = CompetitiveMatchStatus.IN_PROGRESS
        match.started_at = utcnow()
        replay = self.match_simulation_service.build_replay_payload(request)
        FootballUniverseService(self.session).persist_match_universe(request=request, replay_payload=replay)
        match.status = CompetitiveMatchStatus.COMPLETED
        match.completed_at = utcnow()
        match.result_payload = replay.model_dump(mode="json")
        self._update_manager_reputation(
            replay=replay,
            home_controller=controller_home,
            away_controller=controller_away,
            home_manager=home_manager,
            away_manager=away_manager,
            home_team_id=request.home_team.team_id,
            away_team_id=request.away_team.team_id,
        )
        self._queue_match_result_notifications(match, replay)
        self.session.flush()
        return CompetitiveMatchExecutionView(
            match=self._match_view(match),
            controllers=ControllerSummaryView(home=controller_home, away=controller_away),
            control_logs=self._control_log_views(match),
            replay=replay,
        )

    def start_run(self, *, actor: User, payload: FastGameRunStartRequest) -> FastGameRunView:
        self._enforce_human_only(
            competition_type=CompetitiveMatchCompetitionType.FAST_GAME,
            ai_detected=payload.ai_detected,
            automation_detected=payload.automation_detected,
        )
        manager = self._resolve_locked_run_manager(actor.id, payload.manager_id)
        run = FastGameRun(
            user_id=actor.id,
            manager_locked_id=manager.id if manager is not None else None,
            entry_fee_amount=self._quantize(payload.entry_fee_amount),
            base_reward_amount=self._quantize(payload.base_reward_amount),
            base_rating=payload.base_rating,
            scaling_factor=payload.scaling_factor,
            started_at=utcnow(),
        )
        self.session.add(run)
        self.session.flush()
        self._charge_entry_fee(actor=actor, run=run)
        self.session.flush()
        return self._run_view(run)

    def play_fast_game(self, *, actor: User, run_id: str, payload: FastGamePlayRequest) -> FastGameResultView:
        run = self._run_for_actor(run_id, actor)
        self._enforce_human_only(
            competition_type=CompetitiveMatchCompetitionType.FAST_GAME,
            ai_detected=payload.ai_detected,
            automation_detected=payload.automation_detected,
        )
        if payload.home_manager_id != run.manager_locked_id:
            raise ManagerLockedError("Fast game manager changes are locked for the duration of the run.")
        match = Match(
            competition_type=CompetitiveMatchCompetitionType.FAST_GAME,
            home_user_id=actor.id,
            away_user_id=payload.away_user_id,
            home_manager_id=run.manager_locked_id,
            away_manager_id=payload.away_manager_id,
            fast_game_run_id=run.id,
            is_user_online_home=payload.is_user_online_home,
            is_user_online_away=payload.is_user_online_away,
            locked_lineup_home=payload.locked_lineup_home.model_dump(mode="json"),
            locked_lineup_away=payload.locked_lineup_away.model_dump(mode="json"),
            kickoff_at=payload.kickoff_at or utcnow(),
        )
        self.session.add(match)
        self.session.flush()
        execution = self.execute_match(
            actor=actor,
            match_id=match.id,
            payload=CompetitiveMatchExecuteRequest(
                is_user_online_home=payload.is_user_online_home,
                is_user_online_away=payload.is_user_online_away,
                simulation_seed=payload.simulation_seed,
                ai_detected=payload.ai_detected,
                automation_detected=payload.automation_detected,
            ),
        )
        winner_team_id = execution.replay.summary.winner_team_id if execution.replay is not None else None
        result = "win" if winner_team_id == payload.locked_lineup_home.team_id else "loss"
        if result == "win":
            run.wins += 1
        else:
            run.losses += 1
            run.is_active = False
            run.ended_at = utcnow()
        max_reward_triggered = False
        if run.wins >= 10:
            run.is_active = False
            run.ended_at = utcnow()
            max_reward_triggered = True
        reward_amount = Decimal("0.0000")
        if not run.is_active and run.reward_paid_at is None and run.wins > 0:
            reward_amount = self._reward_amount(run)
            self._credit_fast_game_reward(actor=actor, run=run, reward_amount=reward_amount)
        matchmaking_rating = run.base_rating + (run.wins * run.scaling_factor)
        self.session.flush()
        return FastGameResultView(
            run=self._run_view(run),
            match=execution,
            result=result,
            reward_amount=reward_amount,
            max_reward_triggered=max_reward_triggered,
            matchmaking_rating=matchmaking_rating,
        )

    def get_run(self, *, actor: User, run_id: str) -> FastGameRunView:
        return self._run_view(self._owned_run_for_actor(run_id, actor))

    def create_notification_event(self, *, actor: User, payload: NotificationEventRequest) -> CompetitiveNotificationView:
        self._authorize_actor_for_users(actor, payload.user_id)
        notification = self._queue_notification(
            user_id=payload.user_id,
            event_type=payload.type,
            payload=payload.payload,
            scheduled_for=utcnow(),
        )
        self.session.flush()
        return self._notification_view(notification)

    def list_notifications(self, *, actor: User) -> list[CompetitiveNotificationView]:
        rows = list(
            self.session.scalars(
                select(Notification).where(Notification.user_id == actor.id).order_by(Notification.created_at.desc())
            ).all()
        )
        return [self._notification_view(item) for item in rows]

    def run_workers_once(self) -> WorkerRunResultView:
        return WorkerRunResultView(
            executed_matches=self.execute_due_matches(),
            delivered_notifications=self.deliver_due_notifications(),
        )

    def execute_due_matches(self) -> int:
        due_matches = list(
            self.session.scalars(
                select(Match).where(
                    Match.status == CompetitiveMatchStatus.SCHEDULED,
                    Match.kickoff_at.is_not(None),
                    Match.kickoff_at <= utcnow(),
                )
            ).all()
        )
        count = 0
        for match in due_matches:
            actor = self.session.get(User, match.home_user_id)
            if actor is None:
                continue
            self.execute_match(actor=actor, match_id=match.id, payload=CompetitiveMatchExecuteRequest())
            count += 1
        return count

    def deliver_due_notifications(self) -> int:
        notifications = list(
            self.session.scalars(
                select(Notification).where(
                    Notification.status == CompetitiveNotificationStatus.PENDING,
                    Notification.scheduled_for <= utcnow(),
                ).order_by(Notification.scheduled_for.asc(), Notification.created_at.asc())
            ).all()
        )
        delivered = 0
        for item in notifications:
            user = self.session.get(User, item.user_id)
            if user is None:
                item.status = CompetitiveNotificationStatus.FAILED
                item.failure_reason = "user_not_found"
                continue
            if item.channel is CompetitiveNotificationChannel.PUSH:
                attempt = self.push_gateway.send(self.session, user=user, payload=item.payload)
                if attempt.success:
                    item.status = CompetitiveNotificationStatus.SENT
                    item.provider_message_id = attempt.provider_message_id
                    item.sent_at = utcnow()
                    delivered += 1
                else:
                    item.status = CompetitiveNotificationStatus.FAILED
                    item.failure_reason = attempt.failure_reason
                    self._queue_notification(
                        user_id=user.id,
                        event_type=item.type,
                        payload=dict(item.payload or {}),
                        scheduled_for=utcnow(),
                        channel=CompetitiveNotificationChannel.SMS,
                    )
                    self.session.flush()
                continue
            attempt = self.sms_gateway.send(self.session, user=user, payload=item.payload)
            if attempt.success:
                item.status = CompetitiveNotificationStatus.SENT
                item.provider_message_id = attempt.provider_message_id
                item.sent_at = utcnow()
                delivered += 1
            else:
                item.status = CompetitiveNotificationStatus.FAILED
                item.failure_reason = attempt.failure_reason
        return delivered

    def _build_simulation_request(
        self,
        *,
        match: Match,
        home_controller: MatchControllerType,
        away_controller: MatchControllerType,
        home_manager: Manager | None,
        away_manager: Manager | None,
        simulation_seed: int | None,
    ) -> MatchSimulationRequest:
        home_team = MatchTeamInput.model_validate(match.locked_lineup_home)
        away_team = MatchTeamInput.model_validate(match.locked_lineup_away)
        tactical_changes: list[MatchTacticalChangeInput] = []
        home_team = self._prepare_team_for_controller(home_team, home_controller, home_manager, tactical_changes)
        away_team = self._prepare_team_for_controller(away_team, away_controller, away_manager, tactical_changes)
        competition = MatchCompetitionContextInput(
            competition_type=self._engine_competition_type(match.competition_type),
            stage=match.competition_type.value,
            requires_winner=match.competition_type is CompetitiveMatchCompetitionType.FAST_GAME,
        )
        return MatchSimulationRequest(
            match_id=match.id,
            seed=simulation_seed,
            kickoff_at=match.kickoff_at,
            competition=competition,
            home_team=home_team,
            away_team=away_team,
            tactical_changes=tactical_changes,
        )

    def _prepare_team_for_controller(
        self,
        team: MatchTeamInput,
        controller: MatchControllerType,
        manager: Manager | None,
        tactical_changes: list[MatchTacticalChangeInput],
    ) -> MatchTeamInput:
        resolved = team.model_copy(deep=True)
        if controller is MatchControllerType.MANAGER and manager is not None:
            resolved = self._apply_manager_baseline(team=resolved, manager=manager)
            tactical_changes.extend(self._compile_manager_changes(manager=manager, team=resolved))
            return resolved
        if controller is MatchControllerType.FROZEN:
            return self._apply_frozen_mode(resolved)
        return self._enable_live_control(resolved)

    def _apply_manager_baseline(self, *, team: MatchTeamInput, manager: Manager) -> MatchTeamInput:
        instructions = manager.instructions or {}
        profile = manager.tactical_profile or {}
        formation = str(instructions.get("formation") or team.formation)
        style = str(instructions.get("style") or profile.get("style") or "")
        pressing = _coerce_slider(
            instructions.get("pressing") or profile.get("pressing"),
            low=35,
            medium=55,
            high=80,
            fallback=team.tactics.pressing,
        )
        tempo = _coerce_slider(
            instructions.get("tempo") or profile.get("tempo"),
            low=40,
            medium=55,
            high=75,
            fallback=team.tactics.tempo,
        )
        tactics = team.tactics.model_copy(
            update={
                "style": _style_to_tactical_style(style, fallback=team.tactics.style),
                "mentality": _style_to_tactical_style(
                    profile.get("mentality") or style,
                    fallback=team.tactics.mentality,
                ),
                "pressing": pressing,
                "tempo": tempo,
                "allow_substitutions": True,
                "allow_tactical_changes": True,
            }
        )
        manager_profile = {
            **(team.manager_profile or {}),
            "controller": "real_manager",
            "manager_type": manager.type.value,
            "appointed_user_id": manager.appointed_user_id,
            "reputation_score": manager.reputation_score,
            "style": style or None,
            "instructions": instructions,
        }
        return team.model_copy(update={"formation": formation, "tactics": tactics, "manager_profile": manager_profile})

    def _apply_frozen_mode(self, team: MatchTeamInput) -> MatchTeamInput:
        tactics = team.tactics.model_copy(
            update={
                "allow_substitutions": False,
                "allow_tactical_changes": False,
                "injury_auto_substitution": False,
            }
        )
        return team.model_copy(update={"tactics": tactics, "manager_profile": {**(team.manager_profile or {}), "controller": "frozen"}})

    def _enable_live_control(self, team: MatchTeamInput) -> MatchTeamInput:
        tactics = team.tactics.model_copy(update={"allow_substitutions": True, "allow_tactical_changes": True})
        return team.model_copy(update={"tactics": tactics, "manager_profile": {**(team.manager_profile or {}), "controller": "user"}})

    def _compile_manager_changes(self, *, manager: Manager, team: MatchTeamInput) -> list[MatchTacticalChangeInput]:
        instructions = manager.instructions or {}
        changes: list[MatchTacticalChangeInput] = []
        current_formation = team.formation
        for index, rule in enumerate(instructions.get("rules") or [], start=1):
            adjustment = _action_to_adjustment(rule.get("action"), current_formation=current_formation)
            if adjustment is None:
                continue
            if adjustment.formation:
                current_formation = adjustment.formation
            changes.append(
                MatchTacticalChangeInput(
                    team_id=team.team_id,
                    change_id=f"{team.team_id}:manager:{index}",
                    requested_minute=int(rule.get("minute", 0)),
                    requested_second=0,
                    urgency="normal",
                    condition=str(rule.get("condition")) if rule.get("condition") is not None else None,
                    adjustment=adjustment,
                    notes="manager_instruction",
                )
            )
        return changes

    def _update_manager_reputation(
        self,
        *,
        replay: MatchReplayPayloadView,
        home_controller: MatchControllerType,
        away_controller: MatchControllerType,
        home_manager: Manager | None,
        away_manager: Manager | None,
        home_team_id: str,
        away_team_id: str,
    ) -> None:
        winner_team_id = replay.summary.winner_team_id
        if home_controller is MatchControllerType.MANAGER and home_manager is not None:
            home_manager.reputation_score = round(
                float(home_manager.reputation_score)
                + self._manager_reputation_delta(
                    winner_team_id=winner_team_id,
                    managed_team_id=home_team_id,
                    upset=bool(replay.summary.upset),
                ),
                2,
            )
        if away_controller is MatchControllerType.MANAGER and away_manager is not None:
            away_manager.reputation_score = round(
                float(away_manager.reputation_score)
                + self._manager_reputation_delta(
                    winner_team_id=winner_team_id,
                    managed_team_id=away_team_id,
                    upset=bool(replay.summary.upset),
                ),
                2,
            )

    @staticmethod
    def _manager_reputation_delta(*, winner_team_id: str | None, managed_team_id: str, upset: bool) -> float:
        if winner_team_id is None:
            return 0.0
        if winner_team_id == managed_team_id:
            return 10.0 + (_UPSET_BONUS if upset else 0.0)
        return -5.0

    def _charge_entry_fee(self, *, actor: User, run: FastGameRun) -> None:
        amount = self._quantize(run.entry_fee_amount)
        if amount <= Decimal("0.0000"):
            return
        EconomyService(self.session, wallet_service=self.wallet_service).collect_match_entry(
            user=actor,
            payment_unit=LedgerUnit.COIN,
            gross_amount=amount,
            fee_bps=0,
            treasury_account=self.wallet_service.ensure_treasury_account(self.session, LedgerUnit.COIN),
            treasury_share_bps=2000,
            reference=f"fast-game-run:{run.id}:entry",
            external_reference=f"fast-game-run:{run.id}:entry",
            description="Fast game entry fee",
            source_tag=LedgerSourceTag.USER_COMPETITION_ENTRY_SPEND,
            actor=actor,
            metadata={"fast_game_run_id": run.id},
        )

    def _credit_fast_game_reward(self, *, actor: User, run: FastGameRun, reward_amount: Decimal) -> None:
        amount = self._quantize(reward_amount)
        if amount <= Decimal("0.0000"):
            return
        user_account = self.wallet_service.get_user_account(self.session, actor, LedgerUnit.COIN)
        platform_account = self.wallet_service.ensure_promo_pool_account(self.session, LedgerUnit.COIN)
        self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=user_account, amount=amount, transaction_type=LedgerTransactionType.MATCH_REWARD),
                LedgerPosting(account=platform_account, amount=-amount, transaction_type=LedgerTransactionType.MATCH_REWARD),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=LedgerSourceTag.PLATFORM_COMPETITION_REWARD,
            reference=f"fast-game-run:{run.id}:reward",
            external_reference=f"fast-game-run:{run.id}:reward",
            description="Fast game reward payout",
            actor=actor,
            transaction_type=LedgerTransactionType.MATCH_REWARD,
        )
        run.reward_amount_paid = amount
        run.reward_paid_at = utcnow()

    def _reward_amount(self, run: FastGameRun) -> Decimal:
        multiplier = Decimal(str(pow(run.wins, 1.3))) if run.wins > 0 else Decimal("0")
        return self._quantize(run.base_reward_amount * multiplier)

    def _queue_match_scheduled_notifications(self, match: Match) -> None:
        for user_id in (match.home_user_id, match.away_user_id):
            self._queue_notification(
                user_id=user_id,
                event_type="MATCH_SCHEDULED",
                payload={"match_id": match.id, "competition_type": match.competition_type.value},
                scheduled_for=utcnow(),
            )
            if match.kickoff_at is None:
                continue
            for offset in _REMINDER_OFFSETS_MINUTES:
                self._queue_notification(
                    user_id=user_id,
                    event_type="MATCH_REMINDER",
                    payload={
                        "match_id": match.id,
                        "competition_type": match.competition_type.value,
                        "offset_minutes": offset,
                    },
                    scheduled_for=match.kickoff_at - timedelta(minutes=offset),
                )

    def _queue_match_result_notifications(self, match: Match, replay: MatchReplayPayloadView) -> None:
        for user_id in (match.home_user_id, match.away_user_id):
            self._queue_notification(
                user_id=user_id,
                event_type="MATCH_START",
                payload={"match_id": match.id, "competition_type": match.competition_type.value},
                scheduled_for=utcnow(),
            )
            self._queue_notification(
                user_id=user_id,
                event_type="MATCH_RESULT",
                payload={
                    "match_id": match.id,
                    "competition_type": match.competition_type.value,
                    "winner_team_id": replay.summary.winner_team_id,
                    "home_score": replay.summary.home_score,
                    "away_score": replay.summary.away_score,
                },
                scheduled_for=utcnow(),
            )

    def _queue_notification(
        self,
        *,
        user_id: str,
        event_type: str,
        payload: dict[str, Any],
        scheduled_for: datetime,
        channel: CompetitiveNotificationChannel = CompetitiveNotificationChannel.PUSH,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=event_type,
            payload=payload,
            status=CompetitiveNotificationStatus.PENDING,
            channel=channel,
            scheduled_for=scheduled_for,
        )
        self.session.add(notification)
        return notification

    def _log_controller(self, match: Match, side: MatchControlSide, controller: MatchControllerType) -> None:
        self.session.add(
            MatchControlLog(
                match_id=match.id,
                side=side,
                controller_type=controller,
                timestamp=utcnow(),
            )
        )

    def _control_log_views(self, match: Match) -> list[MatchControlLogView]:
        items = list(
            self.session.scalars(
                select(MatchControlLog)
                .where(MatchControlLog.match_id == match.id)
                .order_by(MatchControlLog.timestamp.asc())
            ).all()
        )
        return [
            MatchControlLogView(
                side=item.side.value,
                controller_type=item.controller_type,
                timestamp=item.timestamp,
            )
            for item in items
        ]

    def _manager_view(self, manager: Manager) -> ManagerView:
        return ManagerView(
            id=manager.id,
            user_id=manager.user_id,
            type=manager.type,
            appointed_user_id=manager.appointed_user_id,
            instructions=dict(manager.instructions or {}),
            tactical_profile=dict(manager.tactical_profile or {}),
            reputation_score=float(manager.reputation_score),
            created_at=manager.created_at,
        )

    def _match_view(self, match: Match) -> CompetitiveMatchView:
        return CompetitiveMatchView(
            id=match.id,
            competition_type=match.competition_type,
            home_user_id=match.home_user_id,
            away_user_id=match.away_user_id,
            home_manager_id=match.home_manager_id,
            away_manager_id=match.away_manager_id,
            fast_game_run_id=match.fast_game_run_id,
            is_user_online_home=match.is_user_online_home,
            is_user_online_away=match.is_user_online_away,
            kickoff_at=match.kickoff_at,
            status=match.status,
            result_payload=dict(match.result_payload or {}),
            created_at=match.created_at,
            updated_at=match.updated_at,
        )

    def _run_view(self, run: FastGameRun) -> FastGameRunView:
        return FastGameRunView(
            id=run.id,
            user_id=run.user_id,
            wins=run.wins,
            losses=run.losses,
            is_active=run.is_active,
            manager_locked_id=run.manager_locked_id,
            entry_fee_amount=run.entry_fee_amount,
            base_reward_amount=run.base_reward_amount,
            base_rating=run.base_rating,
            scaling_factor=run.scaling_factor,
            reward_amount_paid=run.reward_amount_paid,
            started_at=run.started_at,
            ended_at=run.ended_at,
        )

    def _notification_view(self, notification: Notification) -> CompetitiveNotificationView:
        return CompetitiveNotificationView(
            id=notification.id,
            user_id=notification.user_id,
            type=notification.type,
            payload=dict(notification.payload or {}),
            status=notification.status,
            channel=notification.channel,
            scheduled_for=notification.scheduled_for,
            provider_message_id=notification.provider_message_id,
            failure_reason=notification.failure_reason,
            sent_at=notification.sent_at,
            created_at=notification.created_at,
        )

    def _authorize_actor_for_users(self, actor: User, *user_ids: str) -> None:
        if actor.role in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            return
        if actor.id not in set(user_ids):
            raise CompetitiveIntegrityError("You cannot operate on another user's GTEX integrity resources.")

    def _enforce_human_only(
        self,
        *,
        competition_type: CompetitiveMatchCompetitionType,
        ai_detected: bool,
        automation_detected: bool,
    ) -> None:
        if competition_type in {
            CompetitiveMatchCompetitionType.GTEX_HOSTED,
            CompetitiveMatchCompetitionType.FAST_GAME,
        } and ai_detected:
            raise AutomationRejectedError(
                "AI participation is not permitted in GTEX hosted competitions or fast game."
            )
        if competition_type is CompetitiveMatchCompetitionType.FAST_GAME and automation_detected:
            raise AutomationRejectedError("Automation is not permitted in fast game.")

    def _manager_optional(self, manager_id: str | None, *, owner_user_id: str) -> Manager | None:
        if manager_id is None:
            return None
        return self._manager_for_owner(manager_id, owner_user_id)

    def _manager_for_owner(self, manager_id: str, owner_user_id: str) -> Manager:
        manager = self.session.get(Manager, manager_id)
        if manager is None or manager.user_id != owner_user_id:
            raise CompetitiveIntegrityError("Manager not found for the selected side.")
        return manager

    def _resolve_locked_run_manager(self, owner_user_id: str, manager_id: str | None) -> Manager | None:
        if manager_id is not None:
            return self._manager_for_owner(manager_id, owner_user_id)
        return self.session.scalar(
            select(Manager).where(Manager.user_id == owner_user_id).order_by(Manager.created_at.desc())
        )

    def _match_for_actor(self, match_id: str, actor: User) -> Match:
        match = self.session.get(Match, match_id)
        if match is None:
            raise CompetitiveIntegrityError("Match not found.")
        self._authorize_actor_for_users(actor, match.home_user_id, match.away_user_id)
        return match

    def _run_for_actor(self, run_id: str, actor: User) -> FastGameRun:
        run = self._owned_run_for_actor(run_id, actor)
        if not run.is_active:
            raise CompetitiveIntegrityError("Fast game run is no longer active.")
        return run

    def _owned_run_for_actor(self, run_id: str, actor: User) -> FastGameRun:
        run = self.session.get(FastGameRun, run_id)
        if run is None or run.user_id != actor.id:
            raise CompetitiveIntegrityError("Fast game run not found.")
        return run

    @staticmethod
    def _engine_competition_type(competition_type: CompetitiveMatchCompetitionType) -> EngineCompetitionType:
        if competition_type is CompetitiveMatchCompetitionType.FAST_GAME:
            return EngineCompetitionType.CUP
        return EngineCompetitionType.LEAGUE

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return Decimal(value).quantize(_REWARD_QUANTUM, rounding=ROUND_HALF_UP)


def _condition_met(condition: Any, match_state: dict[str, Any]) -> bool:
    if condition is None:
        return True
    normalized = str(condition).strip().lower()
    score_for = int(match_state.get("score_for", match_state.get("goals_for", 0)))
    score_against = int(match_state.get("score_against", match_state.get("goals_against", 0)))
    minute = int(match_state.get("minute", 0))
    if normalized in {"always", "any"}:
        return True
    if normalized in {"losing", "behind"}:
        return score_for < score_against
    if normalized in {"winning", "leading"}:
        return score_for > score_against
    if normalized in {"drawing", "draw", "tied"}:
        return score_for == score_against
    if normalized == "not_winning":
        return score_for <= score_against
    if normalized == "not_losing":
        return score_for >= score_against
    if normalized.startswith("minute>="):
        return minute >= int(normalized.split(">=", 1)[1])
    return False


def _action_to_adjustment(action: Any, *, current_formation: str) -> MatchTacticalAdjustmentInput | None:
    if isinstance(action, dict):
        payload = dict(action)
        if "mentality" in payload:
            payload["mentality"] = _style_to_tactical_style(payload["mentality"], fallback=TacticalStyle.BALANCED)
        return MatchTacticalAdjustmentInput(**payload)
    if not isinstance(action, str):
        return None
    normalized = action.strip().lower()
    presets: dict[str, dict[str, Any]] = {
        "add_striker": {
            "formation": "4-2-4",
            "tempo": 72,
            "pressing": 78,
            "aggression": 68,
            "mentality": TacticalStyle.ATTACKING,
        },
        "protect_lead": {
            "formation": "5-4-1",
            "tempo": 38,
            "pressing": 42,
            "defensive_line": 34,
            "mentality": TacticalStyle.DEFENSIVE,
        },
        "high_press": {
            "pressing": 85,
            "aggression": 74,
            "mentality": TacticalStyle.ATTACKING,
        },
        "slow_game": {
            "tempo": 35,
            "pressing": 40,
            "mentality": TacticalStyle.DEFENSIVE,
        },
        "add_midfielder": {
            "formation": "4-5-1",
            "tempo": 52,
            "pressing": 58,
            "mentality": TacticalStyle.BALANCED,
        },
        "hold_shape": {
            "formation": current_formation,
            "tempo": 50,
            "pressing": 52,
            "mentality": TacticalStyle.BALANCED,
        },
    }
    preset = presets.get(normalized)
    if preset is None:
        return None
    return MatchTacticalAdjustmentInput(**preset)


def _style_to_tactical_style(value: Any, *, fallback: TacticalStyle) -> TacticalStyle:
    normalized = str(value or "").strip().lower()
    if normalized in {"defensive", "low_block", "park_the_bus", "park_bus"}:
        return TacticalStyle.DEFENSIVE
    if normalized in {"attacking", "counter", "counter_attack", "direct", "long_ball"}:
        return TacticalStyle.ATTACKING
    if normalized in {"balanced", "possession"}:
        return TacticalStyle.BALANCED
    return fallback


def _coerce_slider(raw: Any, *, low: int, medium: int, high: int, fallback: int) -> int:
    if raw is None:
        return fallback
    if isinstance(raw, (int, float)):
        return max(0, min(100, int(raw)))
    normalized = str(raw).strip().lower()
    if normalized in {"low", "slow"}:
        return low
    if normalized in {"medium", "normal", "balanced"}:
        return medium
    if normalized in {"high", "fast"}:
        return high
    try:
        return max(0, min(100, int(float(normalized))))
    except ValueError:
        return fallback


__all__ = [
    "AutomationRejectedError",
    "CompetitiveIntegrityError",
    "CompetitiveIntegrityService",
    "ManagerLockedError",
    "applyManagerInstructions",
    "resolveController",
]
