from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from threading import RLock
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_session
from app.common.enums.share_code_type import ShareCodeType
from app.models.share_code import ShareCode

from app.schemas.creator_requests import CreatorProfileCreateRequest, CreatorProfileUpdateRequest
from app.schemas.creator_responses import CreatorSummaryView
from app.schemas.referral_requests import (
    AttributionCaptureRequest,
    ShareCodeCreateRequest,
    ShareCodeRedeemRequest,
    ShareCodeUpdateRequest,
)
from app.schemas.referral_responses import (
    AttributionView,
    ReferralInviteView,
    ReferralRewardView,
    ReferralSummaryView,
    ShareCodeRedeemResponse,
    ShareCodeView,
)


@dataclass(slots=True)
class CreatorProfileRecord:
    creator_id: str
    user_id: str
    handle: str
    display_name: str
    tier: str
    status: str
    default_share_code_id: str | None
    default_share_code: str | None
    default_competition_id: str | None
    revenue_share_percent: Decimal | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class ShareCodeRecord:
    share_code_id: str
    code: str
    share_code_type: str
    owner_user_id: str | None
    owner_creator_id: str | None
    linked_competition_id: str | None
    active: bool
    max_uses: int
    current_uses: int
    starts_at: datetime | None
    ends_at: datetime | None
    metadata: dict[str, str]
    vanity_code: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(slots=True)
class AttributionRecord:
    attribution_id: str
    referred_user_id: str
    referrer_user_id: str | None
    creator_profile_id: str | None
    share_code_id: str
    share_code: str
    source_channel: str
    attribution_status: str
    campaign_name: str | None
    linked_competition_id: str | None
    first_touched_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)
    milestones: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RewardRecord:
    reward_id: str
    attribution_id: str
    beneficiary_user_id: str | None
    beneficiary_creator_id: str | None
    reward_type: str
    status: str
    trigger_milestone: str
    amount: Decimal | None
    unit: str | None
    label: str
    hold_until: datetime | None
    review_reason: str | None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None
    blocked_at: datetime | None = None
    reversed_at: datetime | None = None
    paid_at: datetime | None = None


@dataclass(slots=True)
class RewardLedgerRecord:
    ledger_entry_id: str
    reward_id: str
    entry_key: str
    entry_type: str
    amount: Decimal | None
    unit: str | None
    status_after: str
    reference_id: str | None
    payload_json: dict[str, str]
    created_at: datetime


@dataclass(slots=True)
class BlockedActionRecord:
    blocked_action_id: str
    user_id: str
    share_code_id: str | None
    code: str | None
    reason_code: str
    occurred_at: datetime
    metadata: dict[str, str]


@dataclass(slots=True)
class CreatorCompetitionLinkRecord:
    competition_id: str
    title: str
    linked_share_code: str | None
    active_participants: int
    attributed_signups: int
    qualified_joins: int


@dataclass(slots=True)
class ReferralRuntimeStore:
    creators_by_user_id: dict[str, CreatorProfileRecord] = field(default_factory=dict)
    creator_ids_by_handle: dict[str, str] = field(default_factory=dict)
    creators_by_id: dict[str, CreatorProfileRecord] = field(default_factory=dict)
    share_codes_by_id: dict[str, ShareCodeRecord] = field(default_factory=dict)
    share_code_ids_by_code: dict[str, str] = field(default_factory=dict)
    attributions_by_id: dict[str, AttributionRecord] = field(default_factory=dict)
    attribution_ids_by_user: dict[str, str] = field(default_factory=dict)
    rewards_by_id: dict[str, RewardRecord] = field(default_factory=dict)
    reward_ledger_by_id: dict[str, RewardLedgerRecord] = field(default_factory=dict)
    blocked_actions: list[BlockedActionRecord] = field(default_factory=list)
    creator_competitions: dict[str, dict[str, CreatorCompetitionLinkRecord]] = field(default_factory=dict)
    lock: RLock = field(default_factory=RLock)


class ReferralActionError(ValueError):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


def generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class ReferralOrchestrator:
    """GTEX creator profiles, share codes, invite attribution, and referral rewards are community-growth features tied to qualified participation milestones in creator competitions and other skill-based platform activity. They are not betting affiliate flows, house-banked wagering products, or cash-settled prediction mechanics."""

    def __init__(self, store: ReferralRuntimeStore | None = None, session: Session | None = None) -> None:
        from app.services.creator_competition_link_service import CreatorCompetitionLinkService
        from app.services.creator_profile_service import CreatorProfileService
        from app.services.referral_attribution_service import ReferralAttributionService
        from app.services.referral_reward_service import ReferralRewardService

        self.store = store or ReferralRuntimeStore()
        self.session = session
        self.creator_profiles = CreatorProfileService(self.store, session=session)
        self.creator_competitions = CreatorCompetitionLinkService(self.store, session=session)
        self.attributions = ReferralAttributionService(self.store, session=session)
        self.rewards = ReferralRewardService(self.store, session=session)

    def create_creator_profile(self, *, current_user, payload: CreatorProfileCreateRequest):
        creator = self.creator_profiles.create_profile(
            user_id=current_user.id,
            username=getattr(current_user, "username", current_user.id),
            handle=payload.handle,
            display_name=payload.display_name,
            tier=payload.tier,
            status=payload.status,
            default_competition_id=payload.default_competition_id,
            revenue_share_percent=payload.revenue_share_percent,
        )
        default_code = self._create_share_code_record(
            current_user=current_user,
            share_code_type="creator_share",
            vanity_code=payload.handle,
            linked_competition_id=payload.default_competition_id,
            max_uses=100_000,
            starts_at=None,
            ends_at=None,
            metadata={"origin": "creator_profile_default"},
            use_as_default=True,
        )
        self.creator_profiles.attach_default_share_code(user_id=current_user.id, share_code=default_code)
        if payload.default_competition_id is not None:
            self.creator_competitions.link_competition(
                creator_id=creator.creator_id,
                competition_id=payload.default_competition_id,
                linked_share_code=default_code.code,
            )
        return self.creator_profiles.get_me(current_user.id)

    def update_creator_profile(self, *, current_user, payload: CreatorProfileUpdateRequest):
        creator = self.creator_profiles.update_profile(
            user_id=current_user.id,
            display_name=payload.display_name,
            tier=payload.tier,
            status=payload.status,
            default_competition_id=payload.default_competition_id,
            revenue_share_percent=payload.revenue_share_percent,
        )
        if creator.default_competition_id is not None:
            self.creator_competitions.link_competition(
                creator_id=creator.creator_id,
                competition_id=creator.default_competition_id,
                linked_share_code=creator.default_share_code,
            )
        return creator

    def get_my_creator_profile(self, *, current_user):
        return self.creator_profiles.get_me(current_user.id)

    def get_creator_by_handle(self, handle: str):
        return self.creator_profiles.get_by_handle(handle)

    def get_creator_summary(self, *, current_user) -> CreatorSummaryView:
        creator = self.creator_profiles.get_me(current_user.id)
        invites = self.attributions.list_for_owner(user_id=current_user.id, creator_id=creator.creator_id)
        rewards = self.rewards.list_for_owner(user_id=current_user.id, creator_id=creator.creator_id)
        competitions = self._ordered_creator_competitions(creator.creator_id, creator.default_competition_id)
        return CreatorSummaryView(
            profile=creator,
            total_signups=len(invites),
            qualified_joins=sum(1 for invite in invites if invite.attribution_status == "qualified"),
            active_participants=sum(
                1
                for invite in invites
                if "first_creator_competition_joined" in invite.milestones or "first_competition_joined" in invite.milestones
            ),
            pending_rewards=sum(1 for reward in rewards if reward.status == "pending"),
            approved_rewards=sum(1 for reward in rewards if reward.status == "approved"),
            featured_competitions=competitions,
        )

    def get_creator_competitions(self, *, current_user):
        creator = self.creator_profiles.get_me(current_user.id)
        return self._ordered_creator_competitions(creator.creator_id, creator.default_competition_id)

    def create_share_code(self, *, current_user, payload: ShareCodeCreateRequest):
        share_code = self._create_share_code_record(
            current_user=current_user,
            share_code_type=payload.share_code_type,
            vanity_code=payload.vanity_code,
            linked_competition_id=payload.linked_competition_id,
            max_uses=payload.max_uses,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            metadata=payload.metadata,
            use_as_default=payload.use_as_default,
        )
        return share_code

    def list_my_share_codes(self, *, current_user):
        creator = self.creator_profiles.get_optional(current_user.id)
        if self.session is not None:
            filters = [ShareCode.owner_user_id == current_user.id]
            if creator is not None:
                filters.append(ShareCode.owner_creator_id == creator.creator_id)
            share_codes = tuple(
                self.session.scalars(
                    select(ShareCode)
                    .where(or_(*filters))
                    .order_by(ShareCode.created_at.desc(), ShareCode.id.desc())
                ).all()
            )
            records = tuple(self._share_code_from_model(share_code) for share_code in share_codes)
            for record in records:
                self._cache_share_code(record)
            return list(records)
        with self.store.lock:
            return [
                share_code
                for share_code in self.store.share_codes_by_id.values()
                if share_code.owner_user_id == current_user.id
                or (creator is not None and share_code.owner_creator_id == creator.creator_id)
            ]

    def update_share_code(self, *, current_user, share_code_id: str, payload: ShareCodeUpdateRequest):
        creator = self.creator_profiles.get_optional(current_user.id)
        if self.session is not None:
            share_code = self.session.get(ShareCode, share_code_id)
            if share_code is None:
                raise ReferralActionError("share_code_not_found")
            if share_code.owner_user_id != current_user.id and (
                creator is None or share_code.owner_creator_id != creator.creator_id
            ):
                raise ReferralActionError("share_code_forbidden")
            if payload.linked_competition_id is not None:
                share_code.linked_competition_id = payload.linked_competition_id
            if payload.active is not None:
                share_code.is_active = payload.active
            if payload.max_uses is not None:
                share_code.max_uses = payload.max_uses
            if payload.ends_at is not None:
                share_code.ends_at = payload.ends_at
            if payload.metadata is not None:
                share_code.metadata_json = payload.metadata
            self.session.flush()
            updated = self._share_code_from_model(share_code)
            self._cache_share_code(updated)
            if updated.owner_creator_id is not None and updated.linked_competition_id is not None:
                self.creator_competitions.link_competition(
                    creator_id=updated.owner_creator_id,
                    competition_id=updated.linked_competition_id,
                    linked_share_code=updated.code,
                )
            if payload.use_as_default and updated.owner_creator_id is not None:
                creator = self.creator_profiles.get_by_id(updated.owner_creator_id)
                self.creator_profiles.attach_default_share_code(user_id=creator.user_id, share_code=updated)
            return updated
        with self.store.lock:
            share_code = self.store.share_codes_by_id.get(share_code_id)
            if share_code is None:
                raise ReferralActionError("share_code_not_found")
            if share_code.owner_user_id != current_user.id and (
                creator is None or share_code.owner_creator_id != creator.creator_id
            ):
                raise ReferralActionError("share_code_forbidden")
            updated = ShareCodeRecord(
                share_code_id=share_code.share_code_id,
                code=share_code.code,
                share_code_type=share_code.share_code_type,
                owner_user_id=share_code.owner_user_id,
                owner_creator_id=share_code.owner_creator_id,
                linked_competition_id=payload.linked_competition_id if payload.linked_competition_id is not None else share_code.linked_competition_id,
                active=payload.active if payload.active is not None else share_code.active,
                max_uses=payload.max_uses if payload.max_uses is not None else share_code.max_uses,
                current_uses=share_code.current_uses,
                starts_at=share_code.starts_at,
                ends_at=payload.ends_at if payload.ends_at is not None else share_code.ends_at,
                metadata=payload.metadata if payload.metadata is not None else share_code.metadata,
                vanity_code=share_code.vanity_code,
                created_at=share_code.created_at,
                updated_at=utcnow(),
            )
            self.store.share_codes_by_id[share_code_id] = updated
        if updated.owner_creator_id is not None and updated.linked_competition_id is not None:
            self.creator_competitions.link_competition(
                creator_id=updated.owner_creator_id,
                competition_id=updated.linked_competition_id,
                linked_share_code=updated.code,
            )
        if payload.use_as_default and updated.owner_creator_id is not None:
            creator = self.creator_profiles.get_by_id(updated.owner_creator_id)
            self.creator_profiles.attach_default_share_code(user_id=creator.user_id, share_code=updated)
        return updated

    def redeem_share_code(self, *, current_user, code: str, payload: ShareCodeRedeemRequest) -> ShareCodeRedeemResponse:
        share_code = self._get_share_code_by_code(code)
        self._ensure_redemption_allowed(
            current_user=current_user,
            share_code=share_code,
            metadata=payload.metadata,
        )
        attribution = self.attributions.redeem_share_code(
            referred_user_id=current_user.id,
            share_code=share_code,
            source_channel=payload.source_channel,
            campaign_name=payload.campaign_name,
            linked_competition_id=payload.linked_competition_id,
            metadata=payload.metadata,
        )
        if self.session is not None:
            persisted_share_code = self.session.get(ShareCode, share_code.share_code_id)
            if persisted_share_code is None:
                raise ReferralActionError("share_code_not_found")
            persisted_share_code.current_uses += 1
            self.session.flush()
            refreshed = self._share_code_from_model(persisted_share_code)
            self._cache_share_code(refreshed)
        else:
            with self.store.lock:
                refreshed = self.store.share_codes_by_id[share_code.share_code_id]
                refreshed.current_uses += 1
                refreshed.updated_at = utcnow()
        if attribution.creator_profile_id is not None:
            self.creator_competitions.record_signup(
                creator_id=attribution.creator_profile_id,
                competition_id=attribution.linked_competition_id,
            )
        rewards = self.rewards.evaluate(attribution, milestone="signup_completed")
        return ShareCodeRedeemResponse(
            share_code=ShareCodeView.model_validate(refreshed),
            attribution=AttributionView.model_validate(attribution),
            pending_rewards=sum(1 for reward in rewards if reward.status == "pending"),
        )

    def capture_attribution(self, *, current_user, payload: AttributionCaptureRequest):
        share_code = self._resolve_share_code_for_user(current_user_id=current_user.id, requested_code=payload.share_code)
        self._ensure_redemption_allowed(
            current_user=current_user,
            share_code=share_code,
            metadata=payload.metadata,
        )
        attribution = self.attributions.capture(
            referred_user_id=current_user.id,
            share_code=share_code,
            source_channel=payload.source_channel,
            campaign_name=payload.campaign_name,
            linked_competition_id=payload.linked_competition_id,
            milestone=payload.milestone,
            metadata=payload.metadata,
        )
        if payload.milestone in {"first_competition_joined", "first_paid_competition_joined", "first_creator_competition_joined"}:
            self.creator_competitions.record_qualified_join(
                creator_id=attribution.creator_profile_id,
                competition_id=attribution.linked_competition_id,
            )
        self.rewards.evaluate(attribution, milestone=payload.milestone)
        return AttributionView.model_validate(attribution)

    def get_my_referral_summary(self, *, current_user) -> ReferralSummaryView:
        creator = self.creator_profiles.get_optional(current_user.id)
        share_codes = self.list_my_share_codes(current_user=current_user)
        invites = self.attributions.list_for_owner(
            user_id=current_user.id,
            creator_id=creator.creator_id if creator is not None else None,
        )
        rewards = self.rewards.list_for_owner(
            user_id=current_user.id,
            creator_id=creator.creator_id if creator is not None else None,
        )
        return ReferralSummaryView(
            generated_share_codes=len(share_codes),
            total_invites=len(invites),
            total_signups=len(invites),
            qualified_users=sum(1 for invite in invites if invite.attribution_status == "qualified"),
            active_participants=sum(
                1
                for invite in invites
                if "first_competition_joined" in invite.milestones or "first_creator_competition_joined" in invite.milestones
            ),
            pending_rewards=sum(1 for reward in rewards if reward.status == "pending"),
            approved_rewards=sum(1 for reward in rewards if reward.status == "approved"),
            paid_rewards=sum(1 for reward in rewards if reward.status == "paid"),
            blocked_rewards=sum(1 for reward in rewards if reward.status == "blocked"),
            default_share_code=creator.default_share_code if creator is not None else None,
        )

    def get_my_rewards(self, *, current_user):
        creator = self.creator_profiles.get_optional(current_user.id)
        rewards = self.rewards.list_for_owner(
            user_id=current_user.id,
            creator_id=creator.creator_id if creator is not None else None,
        )
        return [ReferralRewardView.model_validate(reward) for reward in rewards]

    def get_my_invites(self, *, current_user):
        creator = self.creator_profiles.get_optional(current_user.id)
        invites = self.attributions.list_for_owner(
            user_id=current_user.id,
            creator_id=creator.creator_id if creator is not None else None,
        )
        return [ReferralInviteView.model_validate(
            {
                "share_code": invite.share_code,
                "referred_user_id": invite.referred_user_id,
                "source_channel": invite.source_channel,
                "linked_competition_id": invite.linked_competition_id,
                "campaign_name": invite.campaign_name,
                "attribution_status": invite.attribution_status,
                "milestones": invite.milestones,
                "first_touched_at": invite.first_touched_at,
            }
        ) for invite in invites]

    def _create_share_code_record(
        self,
        *,
        current_user,
        share_code_type: str,
        vanity_code: str | None,
        linked_competition_id: str | None,
        max_uses: int,
        starts_at: datetime | None,
        ends_at: datetime | None,
        metadata: dict[str, str],
        use_as_default: bool,
    ) -> ShareCodeRecord:
        creator = self.creator_profiles.get_optional(current_user.id)
        if share_code_type == "creator_share" and creator is None:
            raise ReferralActionError("creator_profile_required")
        code = self._generate_share_code(
            preferred=vanity_code,
            fallback_seed=creator.handle if creator is not None else getattr(current_user, "username", current_user.id),
        )
        now = utcnow()
        if self.session is not None:
            share_code_model = ShareCode(
                id=generate_id("code"),
                code=code,
                vanity_code=vanity_code,
                code_type=ShareCodeType(share_code_type),
                owner_user_id=current_user.id,
                owner_creator_id=creator.creator_id if share_code_type == "creator_share" and creator is not None else None,
                linked_competition_id=linked_competition_id,
                is_active=True,
                max_uses=max_uses,
                current_uses=0,
                starts_at=starts_at,
                ends_at=ends_at,
                metadata_json=metadata,
            )
            self.session.add(share_code_model)
            self.session.flush()
            share_code = self._share_code_from_model(share_code_model)
            self._cache_share_code(share_code)
            if share_code.owner_creator_id is not None and linked_competition_id is not None:
                self.creator_competitions.link_competition(
                    creator_id=share_code.owner_creator_id,
                    competition_id=linked_competition_id,
                    linked_share_code=share_code.code,
                )
            if use_as_default and creator is not None:
                self.creator_profiles.attach_default_share_code(user_id=current_user.id, share_code=share_code)
            return share_code
        share_code = ShareCodeRecord(
            share_code_id=generate_id("code"),
            code=code,
            share_code_type=share_code_type,
            owner_user_id=current_user.id,
            owner_creator_id=creator.creator_id if share_code_type == "creator_share" and creator is not None else None,
            linked_competition_id=linked_competition_id,
            active=True,
            max_uses=max_uses,
            current_uses=0,
            starts_at=starts_at,
            ends_at=ends_at,
            metadata=metadata,
            vanity_code=vanity_code,
            created_at=now,
            updated_at=now,
        )
        with self.store.lock:
            self.store.share_codes_by_id[share_code.share_code_id] = share_code
            self.store.share_code_ids_by_code[share_code.code] = share_code.share_code_id
        if share_code.owner_creator_id is not None and linked_competition_id is not None:
            self.creator_competitions.link_competition(
                creator_id=share_code.owner_creator_id,
                competition_id=linked_competition_id,
                linked_share_code=share_code.code,
            )
        if use_as_default and creator is not None:
            self.creator_profiles.attach_default_share_code(user_id=current_user.id, share_code=share_code)
        return share_code

    def _generate_share_code(self, *, preferred: str | None, fallback_seed: str) -> str:
        base = (preferred or fallback_seed).strip().lower()
        normalized = "".join(character for character in base if character.isalnum())
        if not normalized:
            normalized = "community"
        candidate = normalized[:16]
        if self.session is not None:
            if self.session.scalar(select(ShareCode.id).where(ShareCode.code == candidate)) is None:
                return candidate
            suffix = 2
            while True:
                attempt = f"{candidate[:13]}{suffix}"
                if self.session.scalar(select(ShareCode.id).where(ShareCode.code == attempt)) is None:
                    return attempt
                suffix += 1
        with self.store.lock:
            if candidate not in self.store.share_code_ids_by_code:
                return candidate
            suffix = 2
            while True:
                attempt = f"{candidate[:13]}{suffix}"
                if attempt not in self.store.share_code_ids_by_code:
                    return attempt
                suffix += 1

    def _get_share_code_by_code(self, code: str) -> ShareCodeRecord:
        if self.session is not None:
            share_code = self.session.scalar(select(ShareCode).where(ShareCode.code == code.lower()))
            if share_code is None:
                raise ReferralActionError("share_code_not_found")
            record = self._share_code_from_model(share_code)
            self._cache_share_code(record)
            return record
        with self.store.lock:
            share_code_id = self.store.share_code_ids_by_code.get(code.lower())
            if share_code_id is None:
                raise ReferralActionError("share_code_not_found")
            return self.store.share_codes_by_id[share_code_id]

    def _resolve_share_code_for_user(self, *, current_user_id: str, requested_code: str | None) -> ShareCodeRecord:
        if requested_code is not None:
            return self._get_share_code_by_code(requested_code)
        attribution = self.attributions.get_for_user(current_user_id)
        if attribution is None:
            raise ReferralActionError("attribution_not_found")
        if self.session is not None and attribution.share_code_id is not None:
            share_code = self.session.get(ShareCode, attribution.share_code_id)
            if share_code is not None:
                record = self._share_code_from_model(share_code)
                self._cache_share_code(record)
                return record
        with self.store.lock:
            cached = self.store.share_codes_by_id.get(attribution.share_code_id or "")
            if cached is not None:
                return cached
        return ShareCodeRecord(
            share_code_id=attribution.share_code_id or generate_id("code"),
            code=attribution.share_code,
            share_code_type="creator_share" if attribution.creator_profile_id is not None else "user_referral",
            owner_user_id=attribution.referrer_user_id,
            owner_creator_id=attribution.creator_profile_id,
            linked_competition_id=attribution.linked_competition_id,
            active=True,
            max_uses=0,
            current_uses=0,
            starts_at=attribution.first_touched_at,
            ends_at=None,
            metadata=attribution.metadata,
            vanity_code=None,
            created_at=attribution.first_touched_at,
            updated_at=attribution.first_touched_at,
        )

    def list_all_share_codes(self) -> tuple[ShareCodeRecord, ...]:
        if self.session is not None:
            share_codes = tuple(
                self.session.scalars(select(ShareCode).order_by(ShareCode.created_at, ShareCode.id)).all()
            )
            records = tuple(self._share_code_from_model(share_code) for share_code in share_codes)
            for record in records:
                self._cache_share_code(record)
            return records
        with self.store.lock:
            return tuple(self.store.share_codes_by_id.values())

    @staticmethod
    def _share_code_from_model(share_code: ShareCode) -> ShareCodeRecord:
        code_type = share_code.code_type.value if hasattr(share_code.code_type, "value") else str(share_code.code_type)
        return ShareCodeRecord(
            share_code_id=share_code.id,
            code=share_code.code,
            share_code_type=code_type,
            owner_user_id=share_code.owner_user_id,
            owner_creator_id=share_code.owner_creator_id,
            linked_competition_id=share_code.linked_competition_id,
            active=share_code.is_active,
            max_uses=share_code.max_uses or 0,
            current_uses=share_code.current_uses,
            starts_at=share_code.starts_at,
            ends_at=share_code.ends_at,
            metadata=dict(share_code.metadata_json or {}),
            vanity_code=share_code.vanity_code,
            created_at=share_code.created_at,
            updated_at=share_code.updated_at,
        )

    def _cache_share_code(self, share_code: ShareCodeRecord) -> None:
        with self.store.lock:
            self.store.share_codes_by_id[share_code.share_code_id] = share_code
            self.store.share_code_ids_by_code[share_code.code] = share_code.share_code_id

    def _ensure_redemption_allowed(
        self,
        *,
        current_user,
        share_code: ShareCodeRecord,
        metadata: dict[str, str] | None,
    ) -> None:
        now = utcnow()
        reason: str | None = None
        if not share_code.active:
            reason = "share_code_inactive"
        elif share_code.starts_at is not None and now < share_code.starts_at:
            reason = "share_code_not_started"
        elif share_code.ends_at is not None and now >= share_code.ends_at:
            reason = "share_code_expired"
        elif share_code.current_uses >= share_code.max_uses:
            reason = "share_code_exhausted"
        elif share_code.owner_user_id == current_user.id:
            reason = "self_referral_blocked"

        if reason is None:
            return

        with self.store.lock:
            self.store.blocked_actions.append(
                BlockedActionRecord(
                    blocked_action_id=generate_id("blocked"),
                    user_id=current_user.id,
                    share_code_id=share_code.share_code_id,
                    code=share_code.code,
                    reason_code=reason,
                    occurred_at=now,
                    metadata=dict(metadata or {}),
                )
            )
        raise ReferralActionError(reason)

    def _ordered_creator_competitions(
        self,
        creator_id: str,
        default_competition_id: str | None,
    ) -> list[CreatorCompetitionLinkRecord]:
        competitions = self.creator_competitions.list_for_creator(creator_id)
        return sorted(
            competitions,
            key=lambda competition: (
                competition.competition_id != default_competition_id,
                competition.competition_id,
            ),
        )


def get_referral_orchestrator(
    request: Request,
    session: Session = Depends(get_session),
) -> ReferralOrchestrator:
    orchestrator = getattr(request.app.state, "referral_orchestrator", None)
    if orchestrator is None:
        store = getattr(request.app.state, "referral_runtime_store", None)
        if store is None:
            store = getattr(request.app.state, "referral_store", None)
        if store is None:
            store = ReferralRuntimeStore()
        request.app.state.referral_runtime_store = store
        orchestrator = ReferralOrchestrator(store=store, session=session)
    return orchestrator
