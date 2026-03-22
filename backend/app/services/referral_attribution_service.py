from __future__ import annotations

from dataclasses import replace

from app.services.referral_orchestrator import (
    AttributionRecord,
    ReferralActionError,
    ReferralStore,
    ShareCodeRecord,
    generate_id,
    utcnow,
)


class ReferralAttributionService:
    # TODO: Replace this temporary app-scoped attribution flow with Thread A's durable attribution models and validation services when available.
    def __init__(self, store: ReferralStore) -> None:
        self.store = store

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
        with self.store.lock:
            return [
                record
                for record in self.store.attributions_by_id.values()
                if record.referrer_user_id == user_id or (creator_id is not None and record.creator_profile_id == creator_id)
            ]

    def get_for_user(self, referred_user_id: str) -> AttributionRecord | None:
        with self.store.lock:
            attribution_id = self.store.attribution_ids_by_user.get(referred_user_id)
            if attribution_id is None:
                return None
            return self.store.attributions_by_id[attribution_id]


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
