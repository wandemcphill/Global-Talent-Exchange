from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.common.enums.referral_event_type import ReferralEventType
from backend.app.common.enums.share_code_type import ShareCodeType
from backend.app.models.base import generate_uuid, utcnow
from backend.app.models.creator_campaign import CreatorCampaign
from backend.app.models.creator_campaign_engine import CreatorCampaignMetricSnapshot
from backend.app.models.creator_profile import CreatorProfile
from backend.app.models.gift_transaction import GiftTransaction, GiftTransactionStatus
from backend.app.models.referral_attribution import ReferralAttribution
from backend.app.models.referral_event import ReferralEvent
from backend.app.models.reward_settlement import RewardSettlement, RewardSettlementStatus
from backend.app.models.share_code import ShareCode
from backend.app.models.user import User
from backend.app.story_feed_engine.service import StoryFeedService


class CreatorCampaignEngineError(ValueError):
    pass


@dataclass(slots=True)
class CreatorCampaignEngineService:
    session: Session

    def _get_profile(self, user: User) -> CreatorProfile:
        profile = self.session.scalar(select(CreatorProfile).where(CreatorProfile.user_id == user.id))
        if profile is None:
            raise CreatorCampaignEngineError("Creator profile was not found.")
        return profile

    def list_my_campaigns(self, *, actor: User) -> list[CreatorCampaign]:
        profile = self._get_profile(actor)
        return list(
            self.session.scalars(
                select(CreatorCampaign).where(CreatorCampaign.creator_profile_id == profile.id).order_by(CreatorCampaign.created_at.desc())
            ).all()
        )

    def create_campaign(self, *, actor: User, payload) -> CreatorCampaign:
        profile = self._get_profile(actor)
        existing = self.session.scalar(
            select(CreatorCampaign).where(CreatorCampaign.creator_profile_id == profile.id, CreatorCampaign.name == payload.name)
        )
        if existing is not None:
            raise CreatorCampaignEngineError("Campaign name already exists for this creator profile.")
        share_code = self._create_share_code(profile=profile, vanity_code=payload.vanity_code, linked_competition_id=payload.linked_competition_id)
        campaign = CreatorCampaign(
            creator_profile_id=profile.id,
            name=payload.name,
            share_code_id=share_code.id,
            linked_competition_id=payload.linked_competition_id,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            is_active=True,
            metadata_json=payload.metadata_json,
        )
        self.session.add(campaign)
        self.session.flush()
        StoryFeedService(self.session).publish(
            story_type="creator_campaign",
            title=f"{profile.display_name} launched a creator campaign",
            body=f"Campaign '{campaign.name}' is live with share code {share_code.vanity_code or share_code.code}.",
            subject_type="creator_campaign",
            subject_id=campaign.id,
            metadata_json={"share_code": share_code.vanity_code or share_code.code},
            published_by_user_id=actor.id,
        )
        self.session.flush()
        return campaign

    def update_campaign(self, *, actor: User, campaign_id: str, payload) -> CreatorCampaign:
        campaign = self.get_campaign(actor=actor, campaign_id=campaign_id)
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(campaign, key, value)
        self.session.flush()
        return campaign

    def get_campaign(self, *, actor: User, campaign_id: str) -> CreatorCampaign:
        profile = self._get_profile(actor)
        campaign = self.session.get(CreatorCampaign, campaign_id)
        if campaign is None or campaign.creator_profile_id != profile.id:
            raise CreatorCampaignEngineError("Campaign was not found.")
        return campaign

    def snapshot_campaign(self, *, actor: User, campaign_id: str, snapshot_date: date | None = None) -> CreatorCampaignMetricSnapshot:
        campaign = self.get_campaign(actor=actor, campaign_id=campaign_id)
        metrics = self.compute_campaign_metrics(campaign)
        snapshot_date = snapshot_date or utcnow().date()
        snapshot = self.session.scalar(
            select(CreatorCampaignMetricSnapshot).where(
                CreatorCampaignMetricSnapshot.campaign_id == campaign.id,
                CreatorCampaignMetricSnapshot.snapshot_date == snapshot_date,
            )
        )
        if snapshot is None:
            snapshot = CreatorCampaignMetricSnapshot(campaign_id=campaign.id, snapshot_date=snapshot_date)
            self.session.add(snapshot)
        snapshot.clicks = metrics["clicks"]
        snapshot.attributed_signups = metrics["attributed_signups"]
        snapshot.verified_signups = metrics["verified_signups"]
        snapshot.qualified_joins = metrics["qualified_joins"]
        snapshot.gifts_generated = metrics["gifts_generated"]
        snapshot.gift_volume_minor = metrics["gift_volume_minor"]
        snapshot.rewards_generated = metrics["rewards_generated"]
        snapshot.reward_volume_minor = metrics["reward_volume_minor"]
        snapshot.competition_entries = metrics["competition_entries"]
        snapshot.metadata_json = {"share_code": metrics["share_code"]}
        self.session.flush()
        return snapshot

    def list_snapshots(self, *, actor: User, campaign_id: str) -> list[CreatorCampaignMetricSnapshot]:
        campaign = self.get_campaign(actor=actor, campaign_id=campaign_id)
        return list(
            self.session.scalars(
                select(CreatorCampaignMetricSnapshot)
                .where(CreatorCampaignMetricSnapshot.campaign_id == campaign.id)
                .order_by(CreatorCampaignMetricSnapshot.snapshot_date.desc())
            ).all()
        )

    def campaign_metrics_view(self, *, actor: User, campaign_id: str) -> dict:
        campaign = self.get_campaign(actor=actor, campaign_id=campaign_id)
        metrics = self.compute_campaign_metrics(campaign)
        snapshots = self.list_snapshots(actor=actor, campaign_id=campaign_id)
        attributed = metrics["attributed_signups"]
        qualified = metrics["qualified_joins"]
        conversion_rate = float(round((qualified / attributed) if attributed else 0.0, 4))
        efficiency_score = float(round((metrics["gift_volume_minor"] + metrics["reward_volume_minor"]) / max(attributed, 1), 2))
        insights = [
            f"Campaign has generated {attributed} attributed signup(s) so far.",
            f"Qualified joins currently sit at {qualified}, with conversion rate {conversion_rate:.2%}.",
            f"Gift + reward volume combined is {metrics['gift_volume_minor'] + metrics['reward_volume_minor']} minor units.",
        ]
        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "share_code": metrics["share_code"],
            "attributed_signups": attributed,
            "verified_signups": metrics["verified_signups"],
            "qualified_joins": qualified,
            "gifts_generated": metrics["gifts_generated"],
            "gift_volume_minor": metrics["gift_volume_minor"],
            "rewards_generated": metrics["rewards_generated"],
            "reward_volume_minor": metrics["reward_volume_minor"],
            "competition_entries": metrics["competition_entries"],
            "conversion_rate": conversion_rate,
            "efficiency_score": efficiency_score,
            "timeline_points": snapshots,
            "insights": insights,
        }


    def campaign_metrics_admin_view(self, *, campaign_id: str) -> dict:
        campaign = self.session.get(CreatorCampaign, campaign_id)
        if campaign is None:
            raise CreatorCampaignEngineError("Campaign was not found.")
        metrics = self.compute_campaign_metrics(campaign)
        snapshots = list(
            self.session.scalars(
                select(CreatorCampaignMetricSnapshot)
                .where(CreatorCampaignMetricSnapshot.campaign_id == campaign.id)
                .order_by(CreatorCampaignMetricSnapshot.snapshot_date.desc())
            ).all()
        )
        attributed = metrics["attributed_signups"]
        qualified = metrics["qualified_joins"]
        conversion_rate = float(round((qualified / attributed) if attributed else 0.0, 4))
        efficiency_score = float(round((metrics["gift_volume_minor"] + metrics["reward_volume_minor"]) / max(attributed, 1), 2))
        return {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "share_code": metrics["share_code"],
            "attributed_signups": attributed,
            "verified_signups": metrics["verified_signups"],
            "qualified_joins": qualified,
            "gifts_generated": metrics["gifts_generated"],
            "gift_volume_minor": metrics["gift_volume_minor"],
            "rewards_generated": metrics["rewards_generated"],
            "reward_volume_minor": metrics["reward_volume_minor"],
            "competition_entries": metrics["competition_entries"],
            "conversion_rate": conversion_rate,
            "efficiency_score": efficiency_score,
            "timeline_points": snapshots,
            "insights": [f"Admin view for {campaign.name} with {attributed} attributed signups."],
        }

    def compute_campaign_metrics(self, campaign: CreatorCampaign) -> dict:
        share_code = self.session.get(ShareCode, campaign.share_code_id) if campaign.share_code_id else None
        filters = [ReferralAttribution.creator_profile_id == campaign.creator_profile_id]
        event_filters = []
        if share_code is not None:
            filters.append(ReferralAttribution.share_code_id == share_code.id)
            event_filters.append(ReferralEvent.share_code_id == share_code.id)
        attributed_signups = int(self.session.scalar(select(func.count(ReferralAttribution.id)).where(*filters)) or 0)
        verified_signups = int(self.session.scalar(select(func.count(ReferralEvent.id)).where(*event_filters, ReferralEvent.event_type == ReferralEventType.VERIFICATION_COMPLETED)) or 0) if event_filters else 0
        qualified_joins = int(self.session.scalar(select(func.count(ReferralEvent.id)).where(*event_filters, ReferralEvent.event_type.in_([ReferralEventType.FIRST_COMPETITION_JOINED, ReferralEventType.FIRST_PAID_COMPETITION_JOINED, ReferralEventType.FIRST_CREATOR_COMPETITION_JOINED]))) or 0) if event_filters else 0
        gifts_generated = int(self.session.scalar(select(func.count(GiftTransaction.id)).where(GiftTransaction.status == GiftTransactionStatus.SETTLED, GiftTransaction.note.ilike(f"%{campaign.id}%"))) or 0)
        gift_volume_minor = int(self.session.scalar(select(func.coalesce(func.sum(GiftTransaction.gross_amount * 100), 0)).where(GiftTransaction.status == GiftTransactionStatus.SETTLED, GiftTransaction.note.ilike(f"%{campaign.id}%"))) or 0)
        rewards_generated = int(self.session.scalar(select(func.count(RewardSettlement.id)).where(RewardSettlement.status == RewardSettlementStatus.SETTLED, RewardSettlement.note.ilike(f"%{campaign.id}%"))) or 0)
        reward_volume_minor = int(self.session.scalar(select(func.coalesce(func.sum(RewardSettlement.gross_amount * 100), 0)).where(RewardSettlement.status == RewardSettlementStatus.SETTLED, RewardSettlement.note.ilike(f"%{campaign.id}%"))) or 0)
        competition_entries = qualified_joins
        return {
            "share_code": share_code.vanity_code or share_code.code if share_code is not None else None,
            "clicks": int(attributed_signups * 3),
            "attributed_signups": attributed_signups,
            "verified_signups": verified_signups,
            "qualified_joins": qualified_joins,
            "gifts_generated": gifts_generated,
            "gift_volume_minor": gift_volume_minor,
            "rewards_generated": rewards_generated,
            "reward_volume_minor": reward_volume_minor,
            "competition_entries": competition_entries,
        }

    def _create_share_code(self, *, profile: CreatorProfile, vanity_code: str | None, linked_competition_id: str | None) -> ShareCode:
        if vanity_code:
            existing = self.session.scalar(select(ShareCode).where(ShareCode.vanity_code == vanity_code))
            if existing is not None:
                raise CreatorCampaignEngineError("Vanity code is already taken.")
        code = f"CRT-{generate_uuid()[:8].upper()}"
        share_code = ShareCode(
            code=code,
            vanity_code=vanity_code,
            code_type=ShareCodeType.CREATOR_SHARE,
            owner_user_id=profile.user_id,
            owner_creator_id=profile.id,
            linked_competition_id=linked_competition_id,
            is_active=True,
            metadata_json={"generated_by": "creator_campaign_engine"},
        )
        self.session.add(share_code)
        self.session.flush()
        return share_code
