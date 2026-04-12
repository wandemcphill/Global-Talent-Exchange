from __future__ import annotations

from dataclasses import replace
from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.common.enums.referral_event_type import ReferralEventType
from app.common.enums.referral_source_channel import ReferralSourceChannel
from app.models.referral_attribution import ReferralAttribution
from app.models.referral_event import ReferralEvent
from app.services.referral_orchestrator import (
    AttributionRecord,
    ReferralActionError,
    ReferralRuntimeStore,
    ShareCodeRecord,
    generate_id,
    utcnow,
)


class ReferralAttributionService:
    # TODO: Replace this temporary app-scoped attribution flow with Thread A's durable attribution models and validation services when available.
    def __init__(self, store: ReferralRuntimeStore, session: Session | None = None) -> None:
        self.store = store
        self.session = session

    def redeem_share_code(
        self,
        *,
        referred_user_id: str,
        share_code: ShareCodeRecord,
        source_channel: str,
        campaign_name: str | None,
        linked_competition_id: str | None,
        metadata: dict[str, str] | None = None,
    ) -> AttributionRecord:
        return self.capture(
            referred_user_id=referred_user_id,
            share_code=share_code,
            source_channel=source_channel,
            campaign_name=campaign_name,
            linked_competition_id=linked_competition_id or share_code.linked_competition_id,
            milestone="signup_completed",
            metadata=metadata,
        )

    def capture(
        self,
        *,
        referred_user_id: str,
        share_code: ShareCodeRecord,
        source_channel: str,
        campaign_name: str | None,
        linked_competition_id: str | None,
        milestone: str,
        metadata: dict[str, str] | None = None,
    ) -> AttributionRecord:
        if self.session is not None:
            attribution = self.session.scalar(
                select(ReferralAttribution).where(ReferralAttribution.referred_user_id == referred_user_id)
            )
            if attribution is None:
                attribution = ReferralAttribution(
                    id=generate_id("attr"),
                    referred_user_id=referred_user_id,
                    referrer_user_id=share_code.owner_user_id,
                    creator_profile_id=share_code.owner_creator_id,
                    share_code_id=share_code.share_code_id,
                    source_channel=ReferralSourceChannel(source_channel),
                    first_touch_at=utcnow(),
                    attribution_status=_status_for_milestone(milestone),
                    campaign_name=campaign_name,
                    linked_competition_id=linked_competition_id,
                    metadata_json={
                        "share_code": share_code.code,
                        **dict(metadata or {}),
                    },
                )
                self.session.add(attribution)
                self.session.flush()
            else:
                current_record = self._load_records((attribution,))[0]
                if milestone in current_record.milestones:
                    self._save(current_record)
                    return current_record
                attribution.attribution_status = _status_for_milestone(
                    milestone,
                    current=attribution.attribution_status,
                )
                attribution.linked_competition_id = linked_competition_id or attribution.linked_competition_id
                attribution.campaign_name = campaign_name or attribution.campaign_name
                merged_metadata = dict(attribution.metadata_json or {})
                merged_metadata.setdefault("share_code", share_code.code)
                attribution.metadata_json = {**merged_metadata, **dict(metadata or {})}
                self.session.flush()

            event_type = ReferralEventType(milestone)
            event = self.session.scalar(
                select(ReferralEvent).where(
                    ReferralEvent.referral_attribution_id == attribution.id,
                    ReferralEvent.event_type == event_type,
                )
            )
            if event is None:
                event = ReferralEvent(
                    id=generate_id("refevt"),
                    event_key=f"{attribution.id}:{event_type.value}"[:96],
                    referral_attribution_id=attribution.id,
                    referred_user_id=attribution.referred_user_id,
                    referrer_user_id=attribution.referrer_user_id,
                    creator_profile_id=attribution.creator_profile_id,
                    share_code_id=attribution.share_code_id,
                    event_type=event_type,
                    source_channel=ReferralSourceChannel(source_channel),
                    occurred_at=utcnow(),
                    event_payload_json={
                        "share_code": (attribution.metadata_json or {}).get("share_code", share_code.code),
                        "campaign_name": campaign_name,
                        "linked_competition_id": linked_competition_id,
                        **dict(metadata or {}),
                    },
                )
                self.session.add(event)
                self.session.flush()

            record = self._load_records((attribution,))[0]
            self._save(record)
            return record

        with self.store.lock:
            existing_id = self.store.attribution_ids_by_user.get(referred_user_id)
            if existing_id is None:
                attribution = AttributionRecord(
                    attribution_id=generate_id("attr"),
                    referred_user_id=referred_user_id,
                    referrer_user_id=share_code.owner_user_id,
                    creator_profile_id=share_code.owner_creator_id,
                    share_code_id=share_code.share_code_id,
                    share_code=share_code.code,
                    source_channel=source_channel,
                    attribution_status=_status_for_milestone(milestone),
                    campaign_name=campaign_name,
                    linked_competition_id=linked_competition_id,
                    first_touched_at=utcnow(),
                    metadata=dict(metadata or {}),
                    milestones=[milestone],
                )
                self.store.attribution_ids_by_user[referred_user_id] = attribution.attribution_id
                self.store.attributions_by_id[attribution.attribution_id] = attribution
                return attribution

            attribution = self.store.attributions_by_id[existing_id]
            if milestone in attribution.milestones:
                return attribution
            updated = replace(
                attribution,
                attribution_status=_status_for_milestone(milestone, current=attribution.attribution_status),
                linked_competition_id=linked_competition_id or attribution.linked_competition_id,
                campaign_name=campaign_name or attribution.campaign_name,
                metadata={**attribution.metadata, **dict(metadata or {})},
                milestones=[*attribution.milestones, milestone],
            )
            self.store.attributions_by_id[updated.attribution_id] = updated
            return updated

    def list_for_owner(self, *, user_id: str, creator_id: str | None) -> list[AttributionRecord]:
        if self.session is not None:
            query = select(ReferralAttribution)
            if creator_id is None:
                query = query.where(ReferralAttribution.referrer_user_id == user_id)
            else:
                query = query.where(
                    or_(
                        ReferralAttribution.referrer_user_id == user_id,
                        ReferralAttribution.creator_profile_id == creator_id,
                    )
                )
            attributions = tuple(
                self.session.scalars(
                    query.order_by(ReferralAttribution.first_touch_at.desc(), ReferralAttribution.id.desc())
                ).all()
            )
            records = sorted(
                self._load_records(attributions),
                key=lambda attribution: attribution.first_touched_at,
                reverse=True,
            )
            for record in records:
                self._save(record)
            return records
        with self.store.lock:
            return [
                record
                for record in self.store.attributions_by_id.values()
                if record.referrer_user_id == user_id or (creator_id is not None and record.creator_profile_id == creator_id)
            ]

    def get_for_user(self, referred_user_id: str) -> AttributionRecord | None:
        if self.session is not None:
            attribution = self.session.scalar(
                select(ReferralAttribution).where(ReferralAttribution.referred_user_id == referred_user_id)
            )
            if attribution is None:
                return None
            record = self._load_records((attribution,))[0]
            self._save(record)
            return record
        with self.store.lock:
            attribution_id = self.store.attribution_ids_by_user.get(referred_user_id)
            if attribution_id is None:
                return None
            return self.store.attributions_by_id[attribution_id]

    def get_by_id(self, attribution_id: str) -> AttributionRecord | None:
        if self.session is not None:
            attribution = self.session.get(ReferralAttribution, attribution_id)
            if attribution is None:
                return None
            record = self._load_records((attribution,))[0]
            self._save(record)
            return record
        with self.store.lock:
            return self.store.attributions_by_id.get(attribution_id)

    def list_all(self) -> tuple[AttributionRecord, ...]:
        if self.session is not None:
            attributions = tuple(
                self.session.scalars(
                    select(ReferralAttribution).order_by(ReferralAttribution.first_touch_at, ReferralAttribution.id)
                ).all()
            )
            records = self._load_records(attributions)
            for record in records:
                self._save(record)
            return records
        with self.store.lock:
            return tuple(self.store.attributions_by_id.values())

    def _load_records(self, attributions: tuple[ReferralAttribution, ...]) -> tuple[AttributionRecord, ...]:
        if not attributions:
            return tuple()
        attribution_ids = [attribution.id for attribution in attributions]
        events_by_attribution: dict[str, list[ReferralEvent]] = defaultdict(list)
        events = self.session.scalars(
            select(ReferralEvent)
            .where(ReferralEvent.referral_attribution_id.in_(attribution_ids))
            .order_by(ReferralEvent.occurred_at, ReferralEvent.created_at, ReferralEvent.id)
        ).all()
        for event in events:
            if event.referral_attribution_id is not None:
                events_by_attribution[event.referral_attribution_id].append(event)
        return tuple(self._from_model(attribution, events_by_attribution.get(attribution.id, [])) for attribution in attributions)

    @staticmethod
    def _from_model(attribution: ReferralAttribution, events: list[ReferralEvent]) -> AttributionRecord:
        source_channel = attribution.source_channel.value if hasattr(attribution.source_channel, "value") else str(attribution.source_channel)
        milestones = [
            event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            for event in events
        ]
        metadata = dict(attribution.metadata_json or {})
        return AttributionRecord(
            attribution_id=attribution.id,
            referred_user_id=attribution.referred_user_id,
            referrer_user_id=attribution.referrer_user_id,
            creator_profile_id=attribution.creator_profile_id,
            share_code_id=attribution.share_code_id,
            share_code=str(metadata.get("share_code", "")),
            source_channel=source_channel,
            attribution_status=attribution.attribution_status,
            campaign_name=attribution.campaign_name,
            linked_competition_id=attribution.linked_competition_id,
            first_touched_at=attribution.first_touch_at,
            metadata=metadata,
            milestones=milestones,
        )

    def _save(self, attribution: AttributionRecord) -> None:
        with self.store.lock:
            self.store.attribution_ids_by_user[attribution.referred_user_id] = attribution.attribution_id
            self.store.attributions_by_id[attribution.attribution_id] = attribution


def _status_for_milestone(milestone: str, *, current: str | None = None) -> str:
    if current == "blocked":
        return current
    if milestone in {
        "verification_completed",
        "wallet_funded",
        "first_competition_joined",
        "first_paid_competition_joined",
        "first_creator_competition_joined",
        "retained_day_7",
        "retained_day_30",
        "first_trade",
    }:
        return "qualified"
    return current or "attributed"
