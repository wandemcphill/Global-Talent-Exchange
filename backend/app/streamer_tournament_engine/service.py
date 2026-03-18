from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import re

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.common.enums.creator_profile_status import CreatorProfileStatus
from backend.app.models.base import utcnow
from backend.app.models.club_profile import ClubProfile
from backend.app.models.competition import Competition
from backend.app.models.competition_entry import CompetitionEntry
from backend.app.models.competition_participant import CompetitionParticipant
from backend.app.models.creator_league import CreatorLeagueSeason
from backend.app.models.creator_monetization import CreatorMatchGiftEvent, CreatorSeasonPass
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.creator_provisioning import CreatorSquad
from backend.app.models.creator_share_market import CreatorClubShareHolding
from backend.app.models.streamer_tournament import (
    StreamerTournament,
    StreamerTournamentApprovalStatus,
    StreamerTournamentEntry,
    StreamerTournamentEntryStatus,
    StreamerTournamentInvite,
    StreamerTournamentInviteStatus,
    StreamerTournamentPolicy,
    StreamerTournamentQualificationType,
    StreamerTournamentReward,
    StreamerTournamentRewardGrant,
    StreamerTournamentRewardGrantStatus,
    StreamerTournamentRewardType,
    StreamerTournamentRiskSignal,
    StreamerTournamentRiskStatus,
    StreamerTournamentStatus,
    StreamerTournamentType,
)
from backend.app.models.user import User, UserRole
from backend.app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from backend.app.reward_engine.service import RewardEngineService
from backend.app.wallets.service import InsufficientBalanceError, LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_POLICY_KEY = "default"
SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


class StreamerTournamentError(ValueError):
    def __init__(self, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.reason = reason or detail


class StreamerTournamentNotFoundError(StreamerTournamentError):
    pass


class StreamerTournamentPermissionError(StreamerTournamentError):
    pass


class StreamerTournamentValidationError(StreamerTournamentError):
    pass


@dataclass(slots=True)
class StreamerTournamentService:
    session: Session
    wallet_service: WalletService | None = None
    reward_engine_service: RewardEngineService | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.reward_engine_service is None:
            self.reward_engine_service = RewardEngineService(self.session, wallet_service=self.wallet_service)

    def get_policy(self) -> StreamerTournamentPolicy:
        policy = self.session.scalar(
            select(StreamerTournamentPolicy).where(
                StreamerTournamentPolicy.policy_key == DEFAULT_POLICY_KEY,
            )
        )
        if policy is None:
            policy = StreamerTournamentPolicy(policy_key=DEFAULT_POLICY_KEY)
            self.session.add(policy)
            self.session.flush()
        return policy

    def upsert_policy(self, *, actor: User, payload) -> StreamerTournamentPolicy:
        policy = self.get_policy()
        policy.reward_coin_approval_limit = self._normalize_amount(payload.reward_coin_approval_limit)
        policy.reward_credit_approval_limit = self._normalize_amount(payload.reward_credit_approval_limit)
        policy.max_cosmetic_rewards_without_review = payload.max_cosmetic_rewards_without_review
        policy.max_reward_slots = payload.max_reward_slots
        policy.max_invites_per_tournament = payload.max_invites_per_tournament
        policy.top_gifter_rank_limit = payload.top_gifter_rank_limit
        policy.active = payload.active
        policy.config_json = dict(payload.config_json)
        policy.updated_by_user_id = actor.id
        self.session.flush()
        return policy

    def list_tournaments(self, *, actor: User | None = None, mine_only: bool = False) -> list[dict[str, object]]:
        stmt = select(StreamerTournament).order_by(StreamerTournament.created_at.desc())
        if mine_only:
            if actor is None:
                return []
            stmt = stmt.where(StreamerTournament.host_user_id == actor.id)
        else:
            stmt = stmt.where(
                StreamerTournament.status.in_(
                    (
                        StreamerTournamentStatus.PUBLISHED,
                        StreamerTournamentStatus.LIVE,
                        StreamerTournamentStatus.COMPLETED,
                    )
                )
            )
        return [self.serialize_tournament(item) for item in self.session.scalars(stmt).all()]

    def get_tournament(self, tournament_id: str) -> dict[str, object]:
        return self.serialize_tournament(self._require_tournament(tournament_id))

    def create_tournament(self, *, actor: User, payload) -> dict[str, object]:
        creator_profile, creator_club = self._require_hosting_creator(actor)
        self._validate_payload(
            tournament_type=payload.tournament_type,
            season_id=payload.season_id,
            playoff_source_competition_id=payload.playoff_source_competition_id,
            qualification_methods=payload.qualification_methods,
            top_gifter_rank_limit=payload.top_gifter_rank_limit,
            rewards=payload.rewards,
        )
        if payload.linked_competition_id:
            self._require_competition(payload.linked_competition_id)
        if payload.playoff_source_competition_id:
            self._require_competition(payload.playoff_source_competition_id)
        if payload.season_id:
            self._require_season(payload.season_id)

        tournament = StreamerTournament(
            host_user_id=actor.id,
            creator_profile_id=creator_profile.id,
            creator_club_id=creator_club.id,
            season_id=payload.season_id,
            linked_competition_id=payload.linked_competition_id,
            playoff_source_competition_id=payload.playoff_source_competition_id,
            slug=self._unique_slug(creator_profile.id, payload.slug or payload.title),
            title=payload.title.strip(),
            description=payload.description,
            tournament_type=payload.tournament_type,
            status=StreamerTournamentStatus.DRAFT,
            max_participants=payload.max_participants,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            entry_rules_json=self._build_entry_rules(
                qualification_methods=payload.qualification_methods,
                top_gifter_rank_limit=payload.top_gifter_rank_limit,
                entry_rules_json=payload.entry_rules_json,
            ),
            metadata_json=dict(payload.metadata_json),
        )
        self.session.add(tournament)
        self.session.flush()
        self._replace_rewards(tournament=tournament, rewards=payload.rewards)
        for user_id in payload.invite_user_ids:
            self._create_invite_record(
                tournament=tournament,
                invited_user_id=user_id,
                invited_by_user_id=actor.id,
                note=None,
                metadata_json={},
            )
        if tournament.tournament_type is StreamerTournamentType.CREATOR_VS_FAN:
            self._ensure_creator_host_entry(tournament=tournament, actor=actor)
        self._refresh_state(tournament=tournament, force_pending=True)
        self.session.flush()
        return self.serialize_tournament(tournament)

    def update_tournament(self, *, actor: User, tournament_id: str, payload) -> dict[str, object]:
        tournament = self._require_host_owned_tournament(actor, tournament_id)
        self._assert_mutable(tournament)
        qualification_methods = payload.qualification_methods
        top_gifter_rank_limit = payload.top_gifter_rank_limit
        if qualification_methods is None:
            qualification_methods = self._qualification_methods_for(tournament)
            top_gifter_rank_limit = self._top_gifter_rank_limit_for(tournament)
        self._validate_payload(
            tournament_type=tournament.tournament_type,
            season_id=payload.season_id if payload.season_id is not None else tournament.season_id,
            playoff_source_competition_id=(
                payload.playoff_source_competition_id
                if payload.playoff_source_competition_id is not None
                else tournament.playoff_source_competition_id
            ),
            qualification_methods=qualification_methods,
            top_gifter_rank_limit=top_gifter_rank_limit,
            rewards=None,
        )
        if payload.title is not None:
            tournament.title = payload.title.strip()
        if payload.description is not None:
            tournament.description = payload.description
        if payload.max_participants is not None:
            tournament.max_participants = payload.max_participants
        if payload.season_id is not None:
            if payload.season_id:
                self._require_season(payload.season_id)
            tournament.season_id = payload.season_id
        if payload.linked_competition_id is not None:
            if payload.linked_competition_id:
                self._require_competition(payload.linked_competition_id)
            tournament.linked_competition_id = payload.linked_competition_id
        if payload.playoff_source_competition_id is not None:
            if payload.playoff_source_competition_id:
                self._require_competition(payload.playoff_source_competition_id)
            tournament.playoff_source_competition_id = payload.playoff_source_competition_id
        if payload.starts_at is not None:
            tournament.starts_at = payload.starts_at
        if payload.ends_at is not None:
            tournament.ends_at = payload.ends_at
        if payload.metadata_json is not None:
            tournament.metadata_json = dict(payload.metadata_json)
        if payload.qualification_methods is not None or payload.top_gifter_rank_limit is not None or payload.entry_rules_json is not None:
            tournament.entry_rules_json = self._build_entry_rules(
                qualification_methods=qualification_methods,
                top_gifter_rank_limit=top_gifter_rank_limit,
                entry_rules_json=payload.entry_rules_json or {},
            )
        self._refresh_state(tournament=tournament, force_pending=False)
        self.session.flush()
        return self.serialize_tournament(tournament)

    def replace_rewards(self, *, actor: User, tournament_id: str, rewards: list) -> dict[str, object]:
        tournament = self._require_host_owned_tournament(actor, tournament_id)
        self._assert_mutable(tournament)
        self._validate_payload(
            tournament_type=tournament.tournament_type,
            season_id=tournament.season_id,
            playoff_source_competition_id=tournament.playoff_source_competition_id,
            qualification_methods=self._qualification_methods_for(tournament),
            top_gifter_rank_limit=self._top_gifter_rank_limit_for(tournament),
            rewards=rewards,
        )
        self._replace_rewards(tournament=tournament, rewards=rewards)
        self._refresh_state(tournament=tournament, force_pending=True)
        self.session.flush()
        return self.serialize_tournament(tournament)

    def create_invite(self, *, actor: User, tournament_id: str, payload) -> dict[str, object]:
        tournament = self._require_host_owned_tournament(actor, tournament_id)
        self._assert_mutable(tournament)
        invite = self._create_invite_record(
            tournament=tournament,
            invited_user_id=payload.user_id,
            invited_by_user_id=actor.id,
            note=payload.note,
            metadata_json=payload.metadata_json,
        )
        self._refresh_state(tournament=tournament, force_pending=False)
        self.session.flush()
        return self.serialize_invite(invite)

    def join_tournament(self, *, actor: User, tournament_id: str, payload) -> dict[str, object]:
        tournament = self._require_tournament(tournament_id)
        if tournament.status not in {StreamerTournamentStatus.PUBLISHED, StreamerTournamentStatus.LIVE}:
            raise StreamerTournamentValidationError("Tournament registration is not open.", reason="registration_closed")
        current_participants = int(
            self.session.scalar(
                select(func.count())
                .select_from(StreamerTournamentEntry)
                .where(StreamerTournamentEntry.tournament_id == tournament.id)
            )
            or 0
        )
        if current_participants >= tournament.max_participants:
            raise StreamerTournamentValidationError("Tournament is already full.", reason="tournament_full")
        existing = self.session.scalar(
            select(StreamerTournamentEntry).where(
                StreamerTournamentEntry.tournament_id == tournament.id,
                StreamerTournamentEntry.user_id == actor.id,
            )
        )
        if existing is not None:
            return self.serialize_tournament(tournament)

        qualification_source, snapshot, invite = self._resolve_join_eligibility(
            actor=actor,
            tournament=tournament,
            source_hint=payload.qualification_source_hint,
        )
        entry = StreamerTournamentEntry(
            tournament_id=tournament.id,
            user_id=actor.id,
            invite_id=invite.id if invite is not None else None,
            entry_role="qualified_fan" if qualification_source is not StreamerTournamentQualificationType.INVITE else "invited_player",
            qualification_source=qualification_source,
            qualification_snapshot_json=snapshot,
            status=StreamerTournamentEntryStatus.CONFIRMED,
            joined_at=utcnow(),
            metadata_json=dict(payload.metadata_json),
        )
        self.session.add(entry)
        if invite is not None:
            invite.status = StreamerTournamentInviteStatus.ACCEPTED
            invite.responded_at = utcnow()
        self.session.flush()
        return self.serialize_tournament(tournament)

    def publish_tournament(self, *, actor: User, tournament_id: str, submission_notes: str | None) -> dict[str, object]:
        tournament = self._require_host_owned_tournament(actor, tournament_id)
        rewards = self._list_rewards(tournament.id)
        if not rewards:
            raise StreamerTournamentValidationError("Tournament rewards must be configured before publishing.", reason="missing_rewards")
        self._refresh_state(tournament=tournament, force_pending=False)
        tournament.submission_notes = submission_notes
        tournament.submitted_at = utcnow()
        if tournament.approval_status is StreamerTournamentApprovalStatus.REJECTED:
            raise StreamerTournamentValidationError("Rejected tournaments must be updated before republishing.", reason="approval_rejected")
        if tournament.requires_admin_approval and tournament.approval_status is not StreamerTournamentApprovalStatus.APPROVED:
            tournament.status = StreamerTournamentStatus.PENDING_APPROVAL
            tournament.approval_status = StreamerTournamentApprovalStatus.PENDING
        else:
            tournament.status = StreamerTournamentStatus.PUBLISHED
            if tournament.approval_status is StreamerTournamentApprovalStatus.NOT_REQUIRED:
                tournament.requires_admin_approval = False
        self.session.flush()
        return self.serialize_tournament(tournament)

    def review_tournament(self, *, actor: User, tournament_id: str, approve: bool, notes: str | None) -> dict[str, object]:
        tournament = self._require_tournament(tournament_id)
        if approve:
            tournament.approval_status = StreamerTournamentApprovalStatus.APPROVED
            tournament.status = StreamerTournamentStatus.PUBLISHED
            tournament.approved_at = utcnow()
            tournament.approved_by_user_id = actor.id
            tournament.rejected_at = None
            tournament.rejected_by_user_id = None
        else:
            tournament.approval_status = StreamerTournamentApprovalStatus.REJECTED
            tournament.status = StreamerTournamentStatus.DRAFT
            tournament.rejected_at = utcnow()
            tournament.rejected_by_user_id = actor.id
        tournament.approval_notes = notes
        self.session.flush()
        return self.serialize_tournament(tournament)

    def list_risk_signals(self, *, status_filter: StreamerTournamentRiskStatus | None = None) -> list[StreamerTournamentRiskSignal]:
        stmt = select(StreamerTournamentRiskSignal).order_by(
            StreamerTournamentRiskSignal.detected_at.desc(),
            StreamerTournamentRiskSignal.created_at.desc(),
        )
        if status_filter is not None:
            stmt = stmt.where(StreamerTournamentRiskSignal.status == status_filter)
        return list(self.session.scalars(stmt).all())

    def review_risk_signal(
        self,
        *,
        actor: User,
        signal_id: str,
        status_value: StreamerTournamentRiskStatus,
        notes: str | None,
    ) -> StreamerTournamentRiskSignal:
        signal = self.session.get(StreamerTournamentRiskSignal, signal_id)
        if signal is None:
            raise StreamerTournamentNotFoundError("Tournament risk signal was not found.", reason="risk_signal_not_found")
        signal.status = status_value
        signal.reviewed_at = utcnow()
        signal.reviewed_by_user_id = actor.id
        if notes:
            signal.metadata_json = {**(signal.metadata_json or {}), "review_notes": notes}
        self.session.flush()
        return signal

    def settle_tournament(self, *, actor: User, tournament_id: str, placements: list, note: str | None) -> dict[str, object]:
        tournament = self._require_tournament(tournament_id)
        rewards = self._list_rewards(tournament.id)
        if not rewards:
            raise StreamerTournamentValidationError("Tournament has no rewards to settle.", reason="missing_rewards")
        entries_by_user = {
            item.user_id: item
            for item in self.session.scalars(
                select(StreamerTournamentEntry).where(StreamerTournamentEntry.tournament_id == tournament.id)
            ).all()
        }
        if not entries_by_user:
            raise StreamerTournamentValidationError("Tournament has no entries to settle.", reason="missing_entries")

        grants: list[StreamerTournamentRewardGrant] = []
        seen_users: set[str] = set()
        for placement in placements:
            if placement.user_id in seen_users:
                raise StreamerTournamentValidationError("Placement users must be unique.", reason="duplicate_placement_user")
            seen_users.add(placement.user_id)
            entry = entries_by_user.get(placement.user_id)
            if entry is None:
                raise StreamerTournamentValidationError(
                    "All placements must reference a registered tournament entry.",
                    reason="entry_not_found",
                )
            entry.placement = placement.placement
            entry.status = StreamerTournamentEntryStatus.COMPLETED
            for reward in rewards:
                if reward.placement_start <= placement.placement <= reward.placement_end:
                    grants.append(
                        self._grant_reward(
                            actor=actor,
                            tournament=tournament,
                            reward=reward,
                            entry=entry,
                            placement=placement.placement,
                            note=placement.note or note,
                        )
                    )
        tournament.status = StreamerTournamentStatus.COMPLETED
        tournament.completed_at = utcnow()
        self.session.flush()
        return {
            "tournament": self.serialize_tournament(tournament),
            "grants": [self.serialize_grant(item) for item in grants],
        }

    def serialize_tournament(self, tournament: StreamerTournament) -> dict[str, object]:
        return {
            "id": tournament.id,
            "host_user_id": tournament.host_user_id,
            "creator_profile_id": tournament.creator_profile_id,
            "creator_club_id": tournament.creator_club_id,
            "season_id": tournament.season_id,
            "linked_competition_id": tournament.linked_competition_id,
            "playoff_source_competition_id": tournament.playoff_source_competition_id,
            "slug": tournament.slug,
            "title": tournament.title,
            "description": tournament.description,
            "tournament_type": tournament.tournament_type,
            "status": tournament.status,
            "approval_status": tournament.approval_status,
            "max_participants": tournament.max_participants,
            "requires_admin_approval": tournament.requires_admin_approval,
            "high_reward_flag": tournament.high_reward_flag,
            "starts_at": tournament.starts_at,
            "ends_at": tournament.ends_at,
            "submitted_at": tournament.submitted_at,
            "approved_at": tournament.approved_at,
            "rejected_at": tournament.rejected_at,
            "completed_at": tournament.completed_at,
            "approved_by_user_id": tournament.approved_by_user_id,
            "rejected_by_user_id": tournament.rejected_by_user_id,
            "submission_notes": tournament.submission_notes,
            "approval_notes": tournament.approval_notes,
            "entry_rules_json": tournament.entry_rules_json or {},
            "metadata_json": tournament.metadata_json or {},
            "created_at": tournament.created_at,
            "updated_at": tournament.updated_at,
            "rewards": [self.serialize_reward(item) for item in self._list_rewards(tournament.id)],
            "invites": [self.serialize_invite(item) for item in self._list_invites(tournament.id)],
            "entries": [self.serialize_entry(item) for item in self._list_entries(tournament.id)],
            "open_risk_signals": [
                self.serialize_risk_signal(item)
                for item in self._list_risk_signals_for_tournament(tournament.id)
                if item.status is StreamerTournamentRiskStatus.OPEN
            ],
        }

    @staticmethod
    def serialize_reward(reward: StreamerTournamentReward) -> dict[str, object]:
        return {
            "id": reward.id,
            "tournament_id": reward.tournament_id,
            "title": reward.title,
            "reward_type": reward.reward_type,
            "placement_start": reward.placement_start,
            "placement_end": reward.placement_end,
            "amount": reward.amount,
            "cosmetic_sku": reward.cosmetic_sku,
            "metadata_json": reward.metadata_json or {},
            "created_at": reward.created_at,
            "updated_at": reward.updated_at,
        }

    @staticmethod
    def serialize_invite(invite: StreamerTournamentInvite) -> dict[str, object]:
        return {
            "id": invite.id,
            "tournament_id": invite.tournament_id,
            "invited_user_id": invite.invited_user_id,
            "invited_by_user_id": invite.invited_by_user_id,
            "status": invite.status,
            "note": invite.note,
            "responded_at": invite.responded_at,
            "metadata_json": invite.metadata_json or {},
            "created_at": invite.created_at,
            "updated_at": invite.updated_at,
        }

    @staticmethod
    def serialize_entry(entry: StreamerTournamentEntry) -> dict[str, object]:
        return {
            "id": entry.id,
            "tournament_id": entry.tournament_id,
            "user_id": entry.user_id,
            "invite_id": entry.invite_id,
            "entry_role": entry.entry_role,
            "qualification_source": entry.qualification_source,
            "qualification_snapshot_json": entry.qualification_snapshot_json or {},
            "status": entry.status,
            "seed": entry.seed,
            "placement": entry.placement,
            "joined_at": entry.joined_at,
            "metadata_json": entry.metadata_json or {},
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
        }

    @staticmethod
    def serialize_risk_signal(signal: StreamerTournamentRiskSignal) -> dict[str, object]:
        return {
            "id": signal.id,
            "tournament_id": signal.tournament_id,
            "signal_key": signal.signal_key,
            "severity": signal.severity,
            "status": signal.status,
            "summary": signal.summary,
            "detail": signal.detail,
            "detected_at": signal.detected_at,
            "reviewed_at": signal.reviewed_at,
            "reviewed_by_user_id": signal.reviewed_by_user_id,
            "metadata_json": signal.metadata_json or {},
            "created_at": signal.created_at,
            "updated_at": signal.updated_at,
        }

    @staticmethod
    def serialize_grant(grant: StreamerTournamentRewardGrant) -> dict[str, object]:
        return {
            "id": grant.id,
            "tournament_id": grant.tournament_id,
            "reward_id": grant.reward_id,
            "entry_id": grant.entry_id,
            "recipient_user_id": grant.recipient_user_id,
            "placement": grant.placement,
            "reward_type": grant.reward_type,
            "amount": grant.amount,
            "cosmetic_sku": grant.cosmetic_sku,
            "settlement_status": grant.settlement_status,
            "reward_settlement_id": grant.reward_settlement_id,
            "ledger_transaction_id": grant.ledger_transaction_id,
            "settled_by_user_id": grant.settled_by_user_id,
            "settled_at": grant.settled_at,
            "note": grant.note,
            "metadata_json": grant.metadata_json or {},
            "created_at": grant.created_at,
            "updated_at": grant.updated_at,
        }

    def _require_tournament(self, tournament_id: str) -> StreamerTournament:
        tournament = self.session.get(StreamerTournament, tournament_id)
        if tournament is None:
            raise StreamerTournamentNotFoundError("Streamer tournament was not found.", reason="tournament_not_found")
        return tournament

    def _require_host_owned_tournament(self, actor: User, tournament_id: str) -> StreamerTournament:
        tournament = self._require_tournament(tournament_id)
        if tournament.host_user_id != actor.id and actor.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
            raise StreamerTournamentPermissionError("Only the hosting creator can modify this tournament.", reason="host_required")
        return tournament

    def _require_hosting_creator(self, actor: User) -> tuple[CreatorProfile, ClubProfile]:
        creator_profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == actor.id))
        if creator_profile is None or creator_profile.status != CreatorProfileStatus.ACTIVE:
            raise StreamerTournamentPermissionError("Creator access is required to host tournaments.", reason="creator_access_required")
        creator_club = self.session.scalar(
            select(ClubProfile)
            .join(CreatorSquad, CreatorSquad.club_id == ClubProfile.id)
            .where(CreatorSquad.creator_profile_id == creator_profile.id)
        )
        if creator_club is None:
            raise StreamerTournamentPermissionError("Creator club provisioning is required to host tournaments.", reason="creator_club_required")
        return creator_profile, creator_club

    def _assert_mutable(self, tournament: StreamerTournament) -> None:
        if tournament.status in {StreamerTournamentStatus.COMPLETED, StreamerTournamentStatus.CANCELLED}:
            raise StreamerTournamentValidationError("Completed or cancelled tournaments are immutable.", reason="immutable_tournament")

    def _validate_payload(
        self,
        *,
        tournament_type: StreamerTournamentType,
        season_id: str | None,
        playoff_source_competition_id: str | None,
        qualification_methods: list[StreamerTournamentQualificationType],
        top_gifter_rank_limit: int | None,
        rewards: list | None,
    ) -> None:
        methods = list(dict.fromkeys(qualification_methods))
        if tournament_type is StreamerTournamentType.FAN_QUALIFIER and not methods:
            raise StreamerTournamentValidationError("Fan qualifier tournaments require at least one fan qualification method.", reason="missing_qualification_method")
        if StreamerTournamentQualificationType.SEASON_PASS in methods and not season_id:
            raise StreamerTournamentValidationError("Season-pass qualification requires a creator season.", reason="season_required")
        if StreamerTournamentQualificationType.PLAYOFFS in methods and not playoff_source_competition_id:
            raise StreamerTournamentValidationError("Playoff qualification requires a source competition.", reason="playoff_source_required")
        if StreamerTournamentQualificationType.TOP_GIFTER in methods and top_gifter_rank_limit is None:
            raise StreamerTournamentValidationError("Top-gifter qualification requires a rank limit.", reason="top_gifter_rank_required")
        if rewards is not None:
            for reward in rewards:
                if reward.reward_type in {StreamerTournamentRewardType.GTEX_COIN, StreamerTournamentRewardType.FAN_COIN}:
                    if self._normalize_amount(reward.amount or 0) <= Decimal("0.0000"):
                        raise StreamerTournamentValidationError("Coin rewards must be positive.", reason="invalid_reward_amount")

    def _unique_slug(self, creator_profile_id: str, raw_value: str) -> str:
        slug = self._slugify(raw_value)
        if not slug:
            raise StreamerTournamentValidationError("Tournament slug cannot be empty.", reason="invalid_slug")
        existing = self.session.scalar(
            select(StreamerTournament).where(
                StreamerTournament.creator_profile_id == creator_profile_id,
                StreamerTournament.slug == slug,
            )
        )
        if existing is not None:
            raise StreamerTournamentValidationError("Tournament slug is already in use.", reason="duplicate_slug")
        return slug

    @staticmethod
    def _slugify(raw_value: str) -> str:
        return SLUG_PATTERN.sub("-", (raw_value or "").strip().lower()).strip("-")[:120]

    @staticmethod
    def _normalize_amount(value: Decimal | int | float | str) -> Decimal:
        return Decimal(str(value)).quantize(AMOUNT_QUANTUM)

    def _require_competition(self, competition_id: str) -> Competition:
        competition = self.session.get(Competition, competition_id)
        if competition is None:
            raise StreamerTournamentValidationError("Referenced competition was not found.", reason="competition_not_found")
        return competition

    def _require_season(self, season_id: str) -> CreatorLeagueSeason:
        season = self.session.get(CreatorLeagueSeason, season_id)
        if season is None:
            raise StreamerTournamentValidationError("Referenced creator season was not found.", reason="season_not_found")
        return season

    def _build_entry_rules(
        self,
        *,
        qualification_methods: list[StreamerTournamentQualificationType],
        top_gifter_rank_limit: int | None,
        entry_rules_json: dict[str, object],
    ) -> dict[str, object]:
        payload = dict(entry_rules_json)
        payload["qualification_methods"] = [item.value for item in qualification_methods]
        if top_gifter_rank_limit is not None:
            payload["top_gifter_rank_limit"] = top_gifter_rank_limit
        else:
            payload.pop("top_gifter_rank_limit", None)
        return payload

    def _qualification_methods_for(self, tournament: StreamerTournament) -> list[StreamerTournamentQualificationType]:
        values = tournament.entry_rules_json.get("qualification_methods", []) if tournament.entry_rules_json else []
        return [StreamerTournamentQualificationType(value) for value in values]

    def _top_gifter_rank_limit_for(self, tournament: StreamerTournament) -> int | None:
        raw_value = (tournament.entry_rules_json or {}).get("top_gifter_rank_limit")
        return int(raw_value) if raw_value is not None else None

    def _replace_rewards(self, *, tournament: StreamerTournament, rewards: list) -> None:
        for item in self._list_rewards(tournament.id):
            self.session.delete(item)
        self.session.flush()
        for reward in rewards:
            self.session.add(
                StreamerTournamentReward(
                    tournament_id=tournament.id,
                    title=reward.title.strip(),
                    reward_type=reward.reward_type,
                    placement_start=reward.placement_start,
                    placement_end=reward.placement_end,
                    amount=self._normalize_amount(reward.amount) if reward.amount is not None else None,
                    cosmetic_sku=reward.cosmetic_sku,
                    metadata_json=dict(reward.metadata_json),
                )
            )
        self.session.flush()

    def _create_invite_record(
        self,
        *,
        tournament: StreamerTournament,
        invited_user_id: str,
        invited_by_user_id: str,
        note: str | None,
        metadata_json: dict[str, object],
    ) -> StreamerTournamentInvite:
        if invited_user_id == tournament.host_user_id:
            raise StreamerTournamentValidationError("Creators cannot invite themselves.", reason="self_invite_forbidden")
        policy = self.get_policy()
        current_invites = int(
            self.session.scalar(
                select(func.count())
                .select_from(StreamerTournamentInvite)
                .where(StreamerTournamentInvite.tournament_id == tournament.id)
            )
            or 0
        )
        if current_invites >= policy.max_invites_per_tournament:
            raise StreamerTournamentValidationError("Invite limit for this tournament has been reached.", reason="invite_limit_reached")
        if self.session.get(User, invited_user_id) is None:
            raise StreamerTournamentValidationError("Invited user was not found.", reason="user_not_found")
        invite = StreamerTournamentInvite(
            tournament_id=tournament.id,
            invited_user_id=invited_user_id,
            invited_by_user_id=invited_by_user_id,
            note=note,
            metadata_json=dict(metadata_json),
        )
        self.session.add(invite)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise StreamerTournamentValidationError("User is already invited to this tournament.", reason="duplicate_invite") from exc
        return invite

    def _ensure_creator_host_entry(self, *, tournament: StreamerTournament, actor: User) -> None:
        existing = self.session.scalar(
            select(StreamerTournamentEntry).where(
                StreamerTournamentEntry.tournament_id == tournament.id,
                StreamerTournamentEntry.user_id == actor.id,
            )
        )
        if existing is None:
            self.session.add(
                StreamerTournamentEntry(
                    tournament_id=tournament.id,
                    user_id=actor.id,
                    entry_role="creator_host",
                    qualification_source=StreamerTournamentQualificationType.INVITE,
                    qualification_snapshot_json={"source": "creator_host"},
                    status=StreamerTournamentEntryStatus.CONFIRMED,
                    joined_at=utcnow(),
                    metadata_json={},
                )
            )
            self.session.flush()

    def _resolve_join_eligibility(
        self,
        *,
        actor: User,
        tournament: StreamerTournament,
        source_hint: StreamerTournamentQualificationType | None,
    ) -> tuple[StreamerTournamentQualificationType, dict[str, object], StreamerTournamentInvite | None]:
        invite = self.session.scalar(
            select(StreamerTournamentInvite).where(
                StreamerTournamentInvite.tournament_id == tournament.id,
                StreamerTournamentInvite.invited_user_id == actor.id,
                StreamerTournamentInvite.status.in_(
                    (
                        StreamerTournamentInviteStatus.PENDING,
                        StreamerTournamentInviteStatus.ACCEPTED,
                    )
                ),
            )
        )
        if tournament.tournament_type is StreamerTournamentType.CREATOR_INVITATION:
            if invite is None:
                raise StreamerTournamentValidationError("This tournament is invitation-only.", reason="invite_required")
            return StreamerTournamentQualificationType.INVITE, {"source": "invite"}, invite

        if invite is not None and source_hint in {None, StreamerTournamentQualificationType.INVITE}:
            return StreamerTournamentQualificationType.INVITE, {"source": "invite"}, invite

        methods = self._qualification_methods_for(tournament)
        if source_hint is not None:
            methods = [item for item in methods if item == source_hint]
        for method in methods:
            if method is StreamerTournamentQualificationType.SEASON_PASS:
                snapshot = self._season_pass_snapshot(actor=actor, tournament=tournament)
                if snapshot is not None:
                    return method, snapshot, None
            if method is StreamerTournamentQualificationType.SHAREHOLDER:
                snapshot = self._shareholder_snapshot(actor=actor, tournament=tournament)
                if snapshot is not None:
                    return method, snapshot, None
            if method is StreamerTournamentQualificationType.TOP_GIFTER:
                snapshot = self._top_gifter_snapshot(actor=actor, tournament=tournament)
                if snapshot is not None:
                    return method, snapshot, None
            if method is StreamerTournamentQualificationType.PLAYOFFS:
                snapshot = self._playoff_snapshot(actor=actor, tournament=tournament)
                if snapshot is not None:
                    return method, snapshot, None
        raise StreamerTournamentValidationError("User is not eligible to join this tournament.", reason="not_eligible")

    def _season_pass_snapshot(self, *, actor: User, tournament: StreamerTournament) -> dict[str, object] | None:
        if not tournament.season_id:
            return None
        season_pass = self.session.scalar(
            select(CreatorSeasonPass).where(
                CreatorSeasonPass.user_id == actor.id,
                CreatorSeasonPass.season_id == tournament.season_id,
                CreatorSeasonPass.club_id == tournament.creator_club_id,
            )
        )
        if season_pass is None:
            return None
        return {
            "season_pass_id": season_pass.id,
            "club_id": season_pass.club_id,
            "season_id": season_pass.season_id,
            "price_coin": str(season_pass.price_coin),
        }

    def _shareholder_snapshot(self, *, actor: User, tournament: StreamerTournament) -> dict[str, object] | None:
        holding = self.session.scalar(
            select(CreatorClubShareHolding).where(
                CreatorClubShareHolding.user_id == actor.id,
                CreatorClubShareHolding.club_id == tournament.creator_club_id,
                CreatorClubShareHolding.share_count > 0,
            )
        )
        if holding is None:
            return None
        return {
            "share_holding_id": holding.id,
            "club_id": holding.club_id,
            "share_count": int(holding.share_count),
            "revenue_earned_coin": str(self._normalize_amount(holding.revenue_earned_coin)),
        }

    def _top_gifter_snapshot(self, *, actor: User, tournament: StreamerTournament) -> dict[str, object] | None:
        stmt = (
            select(
                CreatorMatchGiftEvent.sender_user_id,
                func.coalesce(func.sum(CreatorMatchGiftEvent.gross_amount_coin), 0),
            )
            .where(CreatorMatchGiftEvent.club_id == tournament.creator_club_id)
            .group_by(CreatorMatchGiftEvent.sender_user_id)
            .order_by(func.sum(CreatorMatchGiftEvent.gross_amount_coin).desc())
        )
        if tournament.season_id:
            stmt = stmt.where(CreatorMatchGiftEvent.season_id == tournament.season_id)
        ranking = list(self.session.execute(stmt).all())
        limit = self._top_gifter_rank_limit_for(tournament) or self.get_policy().top_gifter_rank_limit
        for index, (sender_user_id, total_gifts) in enumerate(ranking, start=1):
            if sender_user_id == actor.id and index <= limit:
                return {
                    "rank": index,
                    "gross_amount_coin": str(self._normalize_amount(total_gifts)),
                    "season_id": tournament.season_id,
                    "club_id": tournament.creator_club_id,
                }
        return None

    def _playoff_snapshot(self, *, actor: User, tournament: StreamerTournament) -> dict[str, object] | None:
        if not tournament.playoff_source_competition_id:
            return None
        row = self.session.execute(
            select(CompetitionEntry, CompetitionParticipant)
            .join(
                CompetitionParticipant,
                (CompetitionParticipant.competition_id == CompetitionEntry.competition_id)
                & (CompetitionParticipant.club_id == CompetitionEntry.club_id),
            )
            .where(
                CompetitionEntry.competition_id == tournament.playoff_source_competition_id,
                CompetitionEntry.user_id == actor.id,
                CompetitionParticipant.advanced.is_(True),
            )
        ).first()
        if row is None:
            return None
        entry, participant = row
        return {
            "source_competition_id": entry.competition_id,
            "club_id": entry.club_id,
            "seed": participant.seed,
            "points": participant.points,
            "advanced": participant.advanced,
        }

    def _refresh_state(self, *, tournament: StreamerTournament, force_pending: bool) -> None:
        policy = self.get_policy()
        rewards = self._list_rewards(tournament.id)
        totals = self._reward_totals(rewards)
        requires_approval = (
            totals["gtex_coin"] > policy.reward_coin_approval_limit
            or totals["fan_coin"] > policy.reward_credit_approval_limit
            or totals["cosmetics"] > policy.max_cosmetic_rewards_without_review
        )
        tournament.requires_admin_approval = requires_approval
        tournament.high_reward_flag = requires_approval
        if requires_approval:
            if force_pending or tournament.approval_status is not StreamerTournamentApprovalStatus.APPROVED:
                tournament.approval_status = StreamerTournamentApprovalStatus.PENDING
        else:
            tournament.approval_status = StreamerTournamentApprovalStatus.NOT_REQUIRED
            tournament.approved_at = None
            tournament.approved_by_user_id = None
        self._sync_risk_signals(tournament=tournament, policy=policy, totals=totals)

    def _reward_totals(self, rewards: list[StreamerTournamentReward]) -> dict[str, Decimal | int]:
        gtex_coin = Decimal("0.0000")
        fan_coin = Decimal("0.0000")
        cosmetics = 0
        for reward in rewards:
            if reward.reward_type is StreamerTournamentRewardType.GTEX_COIN:
                gtex_coin += self._normalize_amount(reward.amount or 0)
            elif reward.reward_type is StreamerTournamentRewardType.FAN_COIN:
                fan_coin += self._normalize_amount(reward.amount or 0)
            else:
                cosmetics += max(1, reward.placement_end - reward.placement_start + 1)
        return {
            "gtex_coin": gtex_coin.quantize(AMOUNT_QUANTUM),
            "fan_coin": fan_coin.quantize(AMOUNT_QUANTUM),
            "cosmetics": cosmetics,
            "reward_slots": len(rewards),
        }

    def _sync_risk_signals(
        self,
        *,
        tournament: StreamerTournament,
        policy: StreamerTournamentPolicy,
        totals: dict[str, Decimal | int],
    ) -> None:
        active: dict[str, tuple[str, str, str]] = {}
        if totals["gtex_coin"] > policy.reward_coin_approval_limit or totals["fan_coin"] > policy.reward_credit_approval_limit:
            active["reward_limit_exceeded"] = (
                "high",
                "Reward plan exceeds the auto-approval limits.",
                "Admin approval is required before the tournament can be published.",
            )
        if totals["reward_slots"] > policy.max_reward_slots:
            active["reward_slots_exceeded"] = (
                "medium",
                "Reward plan has more slots than the current admin policy allows.",
                "This should be reviewed for reward sprawl or payout complexity.",
            )
        invite_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(StreamerTournamentInvite)
                .where(StreamerTournamentInvite.tournament_id == tournament.id)
            )
            or 0
        )
        if invite_count > policy.max_invites_per_tournament:
            active["invite_count_exceeded"] = (
                "medium",
                "Invite volume exceeds the tournament invite threshold.",
                "Review for spam or over-broad manual enrollment.",
            )
        top_gifter_limit = self._top_gifter_rank_limit_for(tournament)
        if top_gifter_limit is not None and top_gifter_limit > policy.top_gifter_rank_limit:
            active["top_gifter_rank_exceeded"] = (
                "medium",
                "Top-gifter rank window exceeds the admin policy.",
                "Narrow the rank window or keep the tournament under review.",
            )

        existing = {item.signal_key: item for item in self._list_risk_signals_for_tournament(tournament.id)}
        for signal_key, (severity, summary, detail) in active.items():
            signal = existing.get(signal_key)
            if signal is None:
                signal = StreamerTournamentRiskSignal(tournament_id=tournament.id, signal_key=signal_key)
                self.session.add(signal)
            signal.severity = severity
            signal.summary = summary
            signal.detail = detail
            signal.status = StreamerTournamentRiskStatus.OPEN
            signal.detected_at = utcnow()
        for signal_key, signal in existing.items():
            if signal_key not in active and signal.status is StreamerTournamentRiskStatus.OPEN:
                signal.status = StreamerTournamentRiskStatus.RESOLVED
                signal.reviewed_at = utcnow()
                signal.metadata_json = {**(signal.metadata_json or {}), "auto_resolved": True}
        self.session.flush()

    def _grant_reward(
        self,
        *,
        actor: User,
        tournament: StreamerTournament,
        reward: StreamerTournamentReward,
        entry: StreamerTournamentEntry,
        placement: int,
        note: str | None,
    ) -> StreamerTournamentRewardGrant:
        existing = self.session.scalar(
            select(StreamerTournamentRewardGrant).where(
                StreamerTournamentRewardGrant.reward_id == reward.id,
                StreamerTournamentRewardGrant.recipient_user_id == entry.user_id,
                StreamerTournamentRewardGrant.placement == placement,
            )
        )
        if existing is not None:
            return existing
        grant = StreamerTournamentRewardGrant(
            tournament_id=tournament.id,
            reward_id=reward.id,
            entry_id=entry.id,
            recipient_user_id=entry.user_id,
            placement=placement,
            reward_type=reward.reward_type,
            amount=reward.amount,
            cosmetic_sku=reward.cosmetic_sku,
            note=note,
            metadata_json={},
        )
        self.session.add(grant)
        self.session.flush()
        try:
            if reward.reward_type is StreamerTournamentRewardType.GTEX_COIN:
                settlement = self.reward_engine_service.settle_reward(
                    actor=actor,
                    user_id=entry.user_id,
                    competition_key=f"streamer-tournament:{tournament.id}",
                    title=reward.title,
                    gross_amount=self._normalize_amount(reward.amount or 0),
                    reward_source="streamer_tournament",
                    note=note,
                )
                grant.reward_settlement_id = settlement.id
                grant.ledger_transaction_id = settlement.ledger_transaction_id
            elif reward.reward_type is StreamerTournamentRewardType.FAN_COIN:
                grant.ledger_transaction_id = self._settle_fancoin_reward(
                    actor=actor,
                    recipient_user_id=entry.user_id,
                    amount=self._normalize_amount(reward.amount or 0),
                    tournament=tournament,
                    reward=reward,
                )
            else:
                grant.metadata_json = {
                    "fulfillment_status": "pending_delivery",
                    "cosmetic_sku": reward.cosmetic_sku,
                }
            grant.settlement_status = StreamerTournamentRewardGrantStatus.SETTLED
            grant.settled_at = utcnow()
            grant.settled_by_user_id = actor.id
        except (StreamerTournamentError, InsufficientBalanceError, ValueError):
            grant.settlement_status = StreamerTournamentRewardGrantStatus.FAILED
            grant.settled_at = utcnow()
            grant.settled_by_user_id = actor.id
            raise
        self.session.flush()
        return grant

    def _settle_fancoin_reward(
        self,
        *,
        actor: User,
        recipient_user_id: str,
        amount: Decimal,
        tournament: StreamerTournament,
        reward: StreamerTournamentReward,
    ) -> str | None:
        recipient = self.session.get(User, recipient_user_id)
        if recipient is None or not recipient.is_active:
            raise StreamerTournamentValidationError("Reward recipient user was not found.", reason="user_not_found")
        promo_pool = self.wallet_service.ensure_promo_pool_account(self.session, LedgerUnit.CREDIT)
        if self.wallet_service.get_balance(self.session, promo_pool) < amount:
            raise StreamerTournamentValidationError("FanCoin promo pool balance is too low for this reward.", reason="promo_pool_low")
        recipient_account = self.wallet_service.get_user_account(self.session, recipient, LedgerUnit.CREDIT)
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=[
                LedgerPosting(account=recipient_account, amount=amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
                LedgerPosting(account=promo_pool, amount=-amount, source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT),
            ],
            reason=LedgerEntryReason.COMPETITION_REWARD,
            source_tag=LedgerSourceTag.ADMIN_ADJUSTMENT,
            reference=f"streamer-tournament:{tournament.id}:reward:{reward.id}:{recipient.id}",
            description=f"FanCoin tournament reward for {reward.title}",
            external_reference=f"streamer-tournament:{tournament.id}:reward:{reward.id}:{recipient.id}",
            actor=actor,
        )
        return entries[0].transaction_id if entries else None

    def _list_rewards(self, tournament_id: str) -> list[StreamerTournamentReward]:
        return list(
            self.session.scalars(
                select(StreamerTournamentReward)
                .where(StreamerTournamentReward.tournament_id == tournament_id)
                .order_by(StreamerTournamentReward.placement_start.asc(), StreamerTournamentReward.created_at.asc())
            ).all()
        )

    def _list_invites(self, tournament_id: str) -> list[StreamerTournamentInvite]:
        return list(
            self.session.scalars(
                select(StreamerTournamentInvite)
                .where(StreamerTournamentInvite.tournament_id == tournament_id)
                .order_by(StreamerTournamentInvite.created_at.asc())
            ).all()
        )

    def _list_entries(self, tournament_id: str) -> list[StreamerTournamentEntry]:
        return list(
            self.session.scalars(
                select(StreamerTournamentEntry)
                .where(StreamerTournamentEntry.tournament_id == tournament_id)
                .order_by(StreamerTournamentEntry.joined_at.asc(), StreamerTournamentEntry.created_at.asc())
            ).all()
        )

    def _list_risk_signals_for_tournament(self, tournament_id: str) -> list[StreamerTournamentRiskSignal]:
        return list(
            self.session.scalars(
                select(StreamerTournamentRiskSignal)
                .where(StreamerTournamentRiskSignal.tournament_id == tournament_id)
                .order_by(StreamerTournamentRiskSignal.created_at.asc())
            ).all()
        )


__all__ = [
    "StreamerTournamentError",
    "StreamerTournamentNotFoundError",
    "StreamerTournamentPermissionError",
    "StreamerTournamentService",
    "StreamerTournamentValidationError",
]
