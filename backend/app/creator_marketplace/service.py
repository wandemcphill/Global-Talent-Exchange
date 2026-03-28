from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.trust_middleware import SharedTrustMiddleware
from app.creator_marketplace.matching import CampaignMatchResult, CreatorMarketplaceMatchingEngine
from app.feedback_engine.service import FeedbackEngine
from app.models.creator_marketplace import (
    CreatorMarketplaceCampaign,
    CreatorMarketplaceCampaignPayoutBasis,
    CreatorMarketplaceCampaignPayoutType,
    CreatorMarketplaceCampaignStatus,
    CreatorMarketplaceOffer,
    CreatorMarketplaceOfferStatus,
    CreatorMarketplaceParticipation,
    CreatorMarketplaceReputationScore,
)
from app.models.creator_profile import CreatorProfile
from app.models.notification_record import NotificationRecord
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.services.ads.schemas import MatchAdPlacementType
from app.viral.campaign_integration import CampaignViralIntegrationHook
from app.wallets.service import LedgerPosting, WalletService

AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_MATCH_NOTIFICATION_THRESHOLD = 60.0
DEFAULT_NEUTRAL_SCORE = 50.0


class CreatorMarketplaceError(ValueError):
    pass


class CreatorMarketplaceNotFoundError(CreatorMarketplaceError):
    pass


class CreatorMarketplacePermissionError(CreatorMarketplaceError):
    pass


class CreatorMarketplaceConflictError(CreatorMarketplaceError):
    pass


class CreatorMarketplaceValidationError(CreatorMarketplaceError):
    pass


@dataclass(slots=True)
class CreatorMarketplaceService:
    session: Session
    wallet_service: WalletService | None = None
    matching_engine: CreatorMarketplaceMatchingEngine | None = None
    trust_middleware: SharedTrustMiddleware | None = None

    def __post_init__(self) -> None:
        if self.wallet_service is None:
            self.wallet_service = WalletService()
        if self.matching_engine is None:
            self.matching_engine = CreatorMarketplaceMatchingEngine()
        if self.trust_middleware is None:
            self.trust_middleware = SharedTrustMiddleware(session=self.session)

    def create_campaign(self, *, actor: User, payload) -> dict[str, Any]:
        campaign = CreatorMarketplaceCampaign(
            brand_id=actor.id,
            title=self._clean_required(payload.title, field_name="title"),
            budget=self._quantize(payload.budget),
            target_formats=self._normalize_formats(payload.target_formats),
            target_audience=self._normalize_target_audience(payload.target_audience),
            payout_type=payload.payout_type,
            payout_rate=self._quantize(payload.payout_rate),
            payout_basis=payload.payout_basis,
            platform_fee_bps=int(payload.platform_fee_bps),
            status=payload.status,
        )
        self.session.add(campaign)
        self.session.flush()
        self._notify_campaign_matches(campaign=campaign, actor=actor)
        return self._serialize_campaign(campaign)

    def list_campaigns(self, *, actor: User) -> list[dict[str, Any]]:
        creator_profile = self._get_creator_profile(actor=actor, required=False)
        campaigns = self.session.scalars(
            select(CreatorMarketplaceCampaign).order_by(
                CreatorMarketplaceCampaign.updated_at.desc(),
                CreatorMarketplaceCampaign.created_at.desc(),
            )
        ).all()
        offer_map = self._campaign_offer_map(creator_profile=creator_profile)
        return [
            self._serialize_campaign(campaign, offer=offer_map.get(campaign.id))
            for campaign in campaigns
        ]

    def apply_to_campaign(self, *, actor: User, campaign_id: str, payload) -> dict[str, Any]:
        creator_profile = self._get_creator_profile(actor=actor)
        campaign = self._get_campaign(campaign_id)
        if campaign.brand_id == actor.id:
            raise CreatorMarketplacePermissionError("Brands cannot apply to their own campaign.")
        if campaign.status not in {
            CreatorMarketplaceCampaignStatus.OPEN,
            CreatorMarketplaceCampaignStatus.ACTIVE,
        }:
            raise CreatorMarketplaceValidationError("Campaign is not accepting creator applications.")

        offer = self.session.scalar(
            select(CreatorMarketplaceOffer).where(
                CreatorMarketplaceOffer.campaign_id == campaign.id,
                CreatorMarketplaceOffer.creator_id == creator_profile.id,
            )
        )
        if offer is not None and offer.status == CreatorMarketplaceOfferStatus.ACCEPTED:
            raise CreatorMarketplaceConflictError("Offer has already been accepted for this campaign.")

        match = self.matching_engine.build_match(
            self.session,
            creator_profile=creator_profile,
            campaign=campaign,
        )
        if offer is None:
            offer = CreatorMarketplaceOffer(
                creator_id=creator_profile.id,
                campaign_id=campaign.id,
                proposed_price=self._quantize(payload.proposed_price),
                message=self._clean_required(payload.message, field_name="message"),
                status=CreatorMarketplaceOfferStatus.PENDING,
            )
            self.session.add(offer)
        else:
            offer.proposed_price = self._quantize(payload.proposed_price)
            offer.message = self._clean_required(payload.message, field_name="message")
            offer.status = CreatorMarketplaceOfferStatus.PENDING

        offer.match_score = match.match_score
        offer.match_factors = self._match_to_payload(match)
        self.session.flush()
        return self._serialize_offer(offer)

    def accept_offer(self, *, actor: User, campaign_id: str, payload) -> dict[str, Any]:
        campaign = self._get_campaign(campaign_id)
        self._ensure_brand_actor(campaign=campaign, actor=actor)
        offer = self.session.scalar(
            select(CreatorMarketplaceOffer).where(
                CreatorMarketplaceOffer.campaign_id == campaign.id,
                CreatorMarketplaceOffer.creator_id == payload.creator_id,
            )
        )
        if offer is None:
            raise CreatorMarketplaceNotFoundError("Creator offer was not found for this campaign.")
        if offer.status == CreatorMarketplaceOfferStatus.ACCEPTED:
            raise CreatorMarketplaceConflictError("Creator offer has already been accepted.")

        existing_participation = self.session.scalar(
            select(CreatorMarketplaceParticipation).where(
                CreatorMarketplaceParticipation.campaign_id == campaign.id,
                CreatorMarketplaceParticipation.creator_id == payload.creator_id,
            )
        )
        if existing_participation is not None:
            raise CreatorMarketplaceConflictError("Campaign participation already exists for this creator.")

        creator_profile = self.session.get(CreatorProfile, payload.creator_id)
        if creator_profile is None:
            raise CreatorMarketplaceNotFoundError("Creator profile was not found.")
        creator_user = self.session.get(User, creator_profile.user_id)
        if creator_user is None:
            raise CreatorMarketplaceNotFoundError("Creator user was not found.")
        trust_decision = self.trust_middleware.decision_for_user(creator_user)

        match = self.matching_engine.build_match(
            self.session,
            creator_profile=creator_profile,
            campaign=campaign,
        )
        remaining_budget = self._remaining_budget(campaign.id)
        clips_submitted = self._build_clip_payloads(
            campaign=campaign,
            creator_profile=creator_profile,
            clips=payload.clip_submissions,
            match=match,
        )
        raw_gross_payout = self._compute_gross_payout(
            campaign=campaign,
            offer=offer,
            agreed_price=payload.agreed_price,
            clips_submitted=clips_submitted,
            remaining_budget=remaining_budget,
        )
        raw_platform_fee = self._quantize((raw_gross_payout * Decimal(campaign.platform_fee_bps)) / Decimal("10000"))
        raw_payout_earned = self._quantize(max(Decimal("0.0000"), raw_gross_payout - raw_platform_fee))
        trust_weight = Decimal(str(trust_decision.weight))
        gross_payout = self._quantize(raw_gross_payout * trust_weight)
        platform_fee = self._quantize(raw_platform_fee * trust_weight)
        payout_earned = self._quantize(raw_payout_earned * trust_weight)

        performance_metrics = self._build_performance_metrics(
            campaign=campaign,
            clips_submitted=clips_submitted,
            gross_payout=gross_payout,
            payout_earned=payout_earned,
            platform_fee=platform_fee,
            match=match,
            trust_decision=trust_decision,
        )
        participation = CreatorMarketplaceParticipation(
            creator_id=creator_profile.id,
            campaign_id=campaign.id,
            offer_id=offer.id,
            clips_submitted=clips_submitted,
            performance_metrics=performance_metrics,
            gross_payout=gross_payout,
            payout_earned=payout_earned,
            platform_fee_amount=platform_fee,
            brand_feedback_score=(
                Decimal(str(payload.brand_feedback_score)).quantize(Decimal("0.01"))
                if payload.brand_feedback_score is not None
                else None
            ),
        )
        self.session.add(participation)
        self.session.flush()
        participation_id = participation.id
        wallet_transaction_id: str | None = None

        if gross_payout > Decimal("0.0000"):
            wallet_transaction_id = self._credit_creator_wallet(
                campaign=campaign,
                creator_user=creator_user,
                actor=actor,
                payout_earned=payout_earned,
                platform_fee=platform_fee,
            )
            if wallet_transaction_id is not None:
                self.session.execute(
                    update(CreatorMarketplaceParticipation)
                    .where(CreatorMarketplaceParticipation.id == participation_id)
                    .values(wallet_transaction_id=wallet_transaction_id)
                )
                set_committed_value(participation, "wallet_transaction_id", wallet_transaction_id)

        offer.status = CreatorMarketplaceOfferStatus.ACCEPTED
        campaign.status = (
            CreatorMarketplaceCampaignStatus.COMPLETED
            if self._remaining_budget(campaign.id) <= Decimal("0.0000")
            else CreatorMarketplaceCampaignStatus.ACTIVE
        )

        feedback_engine = FeedbackEngine(session=self.session)
        feedback_engine.record_campaign_success(
            creator_id=creator_profile.id,
            campaign_id=campaign.id,
            performance_metrics=performance_metrics,
        )
        CampaignViralIntegrationHook(
            session=self.session,
            feedback_engine=feedback_engine,
        ).publish_creator_marketplace_clips(
            campaign=campaign,
            creator_profile=creator_profile,
            clips=clips_submitted,
        )
        reputation = self._refresh_reputation(creator_profile=creator_profile)
        self.session.execute(
            update(CreatorMarketplaceParticipation)
            .where(CreatorMarketplaceParticipation.id == participation_id)
            .values(reputation_score_snapshot=reputation.reputation_score)
        )
        set_committed_value(participation, "reputation_score_snapshot", reputation.reputation_score)
        self._create_notification(
            user_id=creator_user.id,
            topic="creator_marketplace",
            template_key="creator_marketplace.offer_accepted",
            resource_type="campaign",
            resource_id=campaign.id,
            message=f"Your offer for '{campaign.title}' was accepted.",
            metadata={
                "campaign_id": campaign.id,
                "creator_id": creator_profile.id,
                "brand_id": actor.id,
            },
        )
        if wallet_transaction_id is not None:
            self._create_notification(
                user_id=creator_user.id,
                topic="creator_marketplace",
                template_key="creator_marketplace.payout_completed",
                resource_type="campaign",
                resource_id=campaign.id,
                message=f"Payout for '{campaign.title}' has been credited to your wallet.",
                metadata={
                    "campaign_id": campaign.id,
                    "creator_id": creator_profile.id,
                    "wallet_transaction_id": wallet_transaction_id,
                    "payout_earned": str(payout_earned),
                },
            )
        self.session.flush()
        return self._serialize_participation(participation)

    def list_creator_marketplace(self, *, actor: User) -> list[dict[str, Any]]:
        creator_profile = self._get_creator_profile(actor=actor)
        campaigns = self.session.scalars(
            select(CreatorMarketplaceCampaign)
            .where(
                CreatorMarketplaceCampaign.status.in_(
                    (
                        CreatorMarketplaceCampaignStatus.OPEN,
                        CreatorMarketplaceCampaignStatus.ACTIVE,
                    )
                ),
                CreatorMarketplaceCampaign.brand_id != actor.id,
            )
            .order_by(CreatorMarketplaceCampaign.updated_at.desc())
        ).all()
        offer_map = self._campaign_offer_map(creator_profile=creator_profile)
        items: list[dict[str, Any]] = []
        for campaign in campaigns:
            match = self.matching_engine.build_match(
                self.session,
                creator_profile=creator_profile,
                campaign=campaign,
            )
            offer = offer_map.get(campaign.id)
            items.append(
                {
                    "campaign": self._serialize_campaign(campaign, offer=offer),
                    "match_score": match.match_score,
                    "format_strength_score": match.format_strength_score,
                    "audience_match_score": match.audience_match_score,
                    "past_performance_score": match.past_performance_score,
                    "reasons": list(match.reasons),
                    "offer_status": offer.status if offer is not None else None,
                    "proposed_price": offer.proposed_price if offer is not None else None,
                }
            )
        items.sort(key=lambda item: (-item["match_score"], item["campaign"]["title"].lower()))
        return items

    def get_creator_reputation_view(self, *, actor: User) -> dict[str, Any]:
        creator_profile = self._get_creator_profile(actor=actor)
        reputation = self._refresh_reputation(creator_profile=creator_profile)
        return self._serialize_reputation(reputation)

    def get_campaign_performance(self, *, actor: User, campaign_id: str) -> dict[str, Any]:
        campaign = self._get_campaign(campaign_id)
        creator_profile = self._get_creator_profile(actor=actor, required=False)
        if campaign.brand_id != actor.id:
            if creator_profile is None:
                raise CreatorMarketplacePermissionError("You do not have access to this campaign performance.")
            participant = self.session.scalar(
                select(CreatorMarketplaceParticipation).where(
                    CreatorMarketplaceParticipation.campaign_id == campaign.id,
                    CreatorMarketplaceParticipation.creator_id == creator_profile.id,
                )
            )
            if participant is None:
                raise CreatorMarketplacePermissionError("You do not have access to this campaign performance.")

        rows = self.session.execute(
            select(CreatorMarketplaceParticipation, CreatorProfile)
            .join(CreatorProfile, CreatorProfile.id == CreatorMarketplaceParticipation.creator_id)
            .where(CreatorMarketplaceParticipation.campaign_id == campaign.id)
            .order_by(CreatorMarketplaceParticipation.created_at.asc())
        ).all()
        participants: list[dict[str, Any]] = []
        totals = {
            "views": 0,
            "engagement": 0,
            "conversions": 0,
            "gross_payout": Decimal("0.0000"),
            "payout_earned": Decimal("0.0000"),
            "platform_fee_amount": Decimal("0.0000"),
            "clips_submitted": 0,
            "sponsored_clips_injected": 0,
        }
        for participation, profile in rows:
            metrics = participation.performance_metrics or {}
            totals["views"] += int(metrics.get("views") or 0)
            totals["engagement"] += int(metrics.get("engagement") or 0)
            totals["conversions"] += int(metrics.get("conversions") or 0)
            totals["gross_payout"] += self._to_decimal(participation.gross_payout)
            totals["payout_earned"] += self._to_decimal(participation.payout_earned)
            totals["platform_fee_amount"] += self._to_decimal(participation.platform_fee_amount)
            totals["clips_submitted"] += len(participation.clips_submitted or [])
            totals["sponsored_clips_injected"] += int(metrics.get("sponsored_clips_injected") or 0)
            participants.append(
                {
                    "creator_id": profile.id,
                    "creator_handle": profile.handle,
                    "creator_display_name": profile.display_name,
                    "clips_submitted": participation.clips_submitted,
                    "performance_metrics": participation.performance_metrics,
                    "gross_payout": participation.gross_payout,
                    "payout_earned": participation.payout_earned,
                    "platform_fee_amount": participation.platform_fee_amount,
                    "wallet_transaction_id": participation.wallet_transaction_id,
                }
            )
        views = totals["views"]
        totals["engagement_rate"] = round((totals["engagement"] / views) if views else 0.0, 4)
        totals["conversion_rate"] = round((totals["conversions"] / views) if views else 0.0, 4)
        totals["gross_payout"] = self._quantize(totals["gross_payout"])
        totals["payout_earned"] = self._quantize(totals["payout_earned"])
        totals["platform_fee_amount"] = self._quantize(totals["platform_fee_amount"])
        return {
            "campaign": self._serialize_campaign(campaign),
            "totals": totals,
            "participants": participants,
        }

    def _refresh_reputation(self, *, creator_profile: CreatorProfile) -> CreatorMarketplaceReputationScore:
        participations = self.session.scalars(
            select(CreatorMarketplaceParticipation).where(
                CreatorMarketplaceParticipation.creator_id == creator_profile.id
            )
        ).all()
        completed = [item for item in participations if self._participation_has_delivery(item)]
        delivery_success_score = DEFAULT_NEUTRAL_SCORE
        campaign_performance_score = DEFAULT_NEUTRAL_SCORE
        brand_feedback_score = DEFAULT_NEUTRAL_SCORE
        if participations:
            delivered_count = sum(1 for item in participations if self._participation_has_delivery(item))
            delivery_success_score = round((delivered_count / len(participations)) * 100.0, 2)
        if completed:
            campaign_performance_score = round(
                sum(self._performance_score(item.performance_metrics) for item in completed) / len(completed),
                2,
            )
            brand_feedback_values = [
                float(item.brand_feedback_score)
                for item in completed
                if item.brand_feedback_score is not None
            ]
            if brand_feedback_values:
                brand_feedback_score = round((sum(brand_feedback_values) / len(brand_feedback_values)) * 20.0, 2)
        reputation_score = round(
            (delivery_success_score * 0.35)
            + (campaign_performance_score * 0.40)
            + (brand_feedback_score * 0.25),
            2,
        )
        reputation = self.session.get(CreatorMarketplaceReputationScore, creator_profile.id)
        if reputation is None:
            reputation = CreatorMarketplaceReputationScore(creator_id=creator_profile.id)
            self.session.add(reputation)
        reputation.delivery_success_score = delivery_success_score
        reputation.campaign_performance_score = campaign_performance_score
        reputation.brand_feedback_score = brand_feedback_score
        reputation.reputation_score = reputation_score
        reputation.completed_campaigns = len(completed)
        self.session.flush()
        return reputation

    def _notify_campaign_matches(self, *, campaign: CreatorMarketplaceCampaign, actor: User) -> None:
        creator_profiles = self.session.scalars(select(CreatorProfile)).all()
        ranked_profiles: list[tuple[float, CreatorProfile]] = []
        for creator_profile in creator_profiles:
            if creator_profile.user_id == actor.id:
                continue
            match = self.matching_engine.build_match(
                self.session,
                creator_profile=creator_profile,
                campaign=campaign,
            )
            if match.match_score < DEFAULT_MATCH_NOTIFICATION_THRESHOLD:
                continue
            ranked_profiles.append((match.match_score, creator_profile))
        ranked_profiles.sort(key=lambda item: (-item[0], item[1].display_name.lower()))
        for match_score, creator_profile in ranked_profiles[:10]:
            self._create_notification(
                user_id=creator_profile.user_id,
                topic="creator_marketplace",
                template_key="creator_marketplace.campaign_match",
                resource_type="campaign",
                resource_id=campaign.id,
                message=f"New campaign match: '{campaign.title}' fits your creator profile.",
                metadata={
                    "campaign_id": campaign.id,
                    "brand_id": actor.id,
                    "creator_id": creator_profile.id,
                    "match_score": match_score,
                },
            )

    def _credit_creator_wallet(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        creator_user: User,
        actor: User,
        payout_earned: Decimal,
        platform_fee: Decimal,
    ) -> str | None:
        if payout_earned <= Decimal("0.0000") and platform_fee <= Decimal("0.0000"):
            return None
        creator_account = self.wallet_service.get_user_account(self.session, creator_user, LedgerUnit.CREDIT)
        treasury_account = self.wallet_service.ensure_treasury_account(self.session, LedgerUnit.CREDIT)
        source_account = self.wallet_service.ensure_creator_clip_revenue_account(self.session, LedgerUnit.CREDIT)
        postings: list[LedgerPosting] = []
        if payout_earned > Decimal("0.0000"):
            postings.append(LedgerPosting(account=creator_account, amount=payout_earned))
        if platform_fee > Decimal("0.0000"):
            postings.append(LedgerPosting(account=treasury_account, amount=platform_fee))
        postings.append(LedgerPosting(account=source_account, amount=-(payout_earned + platform_fee)))
        entries = self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.CREATOR_CLIP_REVENUE,
            reference=f"creator-marketplace:{campaign.id}:{creator_user.id}",
            description=f"Creator marketplace payout for {campaign.title}",
            actor=actor,
            idempotency_key=f"creator-marketplace:{campaign.id}:{creator_user.id}",
            metadata={
                "campaign_id": campaign.id,
                "creator_user_id": creator_user.id,
                "payout_earned": str(payout_earned),
                "platform_fee": str(platform_fee),
            },
        )
        return entries[0].transaction_id if entries else None

    def _compute_gross_payout(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        offer: CreatorMarketplaceOffer,
        agreed_price: Decimal | None,
        clips_submitted: list[dict[str, Any]],
        remaining_budget: Decimal,
    ) -> Decimal:
        if remaining_budget <= Decimal("0.0000"):
            raise CreatorMarketplaceValidationError("Campaign budget has already been fully allocated.")
        if campaign.payout_type == CreatorMarketplaceCampaignPayoutType.FIXED:
            gross = self._quantize(agreed_price or offer.proposed_price)
            if gross > remaining_budget:
                raise CreatorMarketplaceValidationError("Fixed payout exceeds the remaining campaign budget.")
            return gross

        basis_total = self._performance_basis_total(campaign=campaign, clips_submitted=clips_submitted)
        gross = self._quantize(Decimal(basis_total) * self._to_decimal(campaign.payout_rate))
        if gross > remaining_budget:
            gross = remaining_budget
        return self._quantize(gross)

    def _build_performance_metrics(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        clips_submitted: list[dict[str, Any]],
        gross_payout: Decimal,
        payout_earned: Decimal,
        platform_fee: Decimal,
        match: CampaignMatchResult,
        trust_decision,
    ) -> dict[str, Any]:
        totals = {
            "views": sum(int(clip.get("views") or 0) for clip in clips_submitted),
            "engagement": sum(int(clip.get("engagement") or 0) for clip in clips_submitted),
            "conversions": sum(int(clip.get("conversions") or 0) for clip in clips_submitted),
        }
        views = totals["views"]
        basis_total = self._performance_basis_total(campaign=campaign, clips_submitted=clips_submitted)
        return {
            **totals,
            "engagement_rate": round((totals["engagement"] / views) if views else 0.0, 4),
            "conversion_rate": round((totals["conversions"] / views) if views else 0.0, 4),
            "payout_basis": campaign.payout_basis.value,
            "payout_basis_total": basis_total,
            "gross_payout": str(gross_payout),
            "payout_earned": str(payout_earned),
            "platform_fee_amount": str(platform_fee),
            "match_score": match.match_score,
            "match_reasons": list(match.reasons),
            "sponsored_clips_injected": len(clips_submitted),
            "boosted_distribution": bool(clips_submitted),
            "creator_trust_score": trust_decision.trust_score,
            "trust_weight": trust_decision.weight,
            "trust_blocked": trust_decision.blocked,
        }

    def _build_clip_payloads(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        creator_profile: CreatorProfile,
        clips,
        match: CampaignMatchResult,
    ) -> list[dict[str, Any]]:
        brand_label = self._display_name(self.session.get(User, campaign.brand_id))
        distribution_weight = round(1.0 + min(match.match_score, 100.0) / 100.0, 2)
        clip_payloads: list[dict[str, Any]] = []
        for clip in clips:
            clip_payloads.append(
                {
                    "clip_id": clip.clip_id,
                    "title": self._clean_optional(clip.title),
                    "clip_url": self._clean_optional(clip.clip_url),
                    "views": int(clip.views),
                    "engagement": int(clip.engagement),
                    "conversions": int(clip.conversions),
                    "metadata": dict(clip.metadata),
                    "creator_id": creator_profile.id,
                    "is_sponsored": True,
                    "sponsored_label": "Sponsored",
                    "ads_engine": {
                        "status": "queued",
                        "placement_type": MatchAdPlacementType.SPONSORED_HIGHLIGHT.value,
                        "placement": "creator_marketplace_feed",
                        "boosted_distribution": True,
                        "distribution_weight": distribution_weight,
                        "brand_label": brand_label,
                        "campaign_title": campaign.title,
                    },
                }
            )
        return clip_payloads

    def _campaign_offer_map(
        self,
        *,
        creator_profile: CreatorProfile | None,
    ) -> dict[str, CreatorMarketplaceOffer]:
        if creator_profile is None:
            return {}
        offers = self.session.scalars(
            select(CreatorMarketplaceOffer).where(CreatorMarketplaceOffer.creator_id == creator_profile.id)
        ).all()
        return {offer.campaign_id: offer for offer in offers}

    def _serialize_campaign(
        self,
        campaign: CreatorMarketplaceCampaign,
        *,
        offer: CreatorMarketplaceOffer | None = None,
    ) -> dict[str, Any]:
        return {
            "id": campaign.id,
            "brand_id": campaign.brand_id,
            "title": campaign.title,
            "budget": self._to_decimal(campaign.budget),
            "remaining_budget": self._remaining_budget(campaign.id),
            "target_formats": list(campaign.target_formats or []),
            "target_audience": dict(campaign.target_audience or {}),
            "payout_type": campaign.payout_type,
            "payout_rate": self._to_decimal(campaign.payout_rate),
            "payout_basis": campaign.payout_basis,
            "platform_fee_bps": campaign.platform_fee_bps,
            "status": campaign.status,
            "offer_count": self._campaign_offer_count(campaign.id),
            "accepted_creators": self._campaign_participant_count(campaign.id),
            "my_offer_status": offer.status if offer is not None else None,
            "created_at": campaign.created_at,
            "updated_at": campaign.updated_at,
        }

    @staticmethod
    def _serialize_offer(offer: CreatorMarketplaceOffer) -> dict[str, Any]:
        return {
            "id": offer.id,
            "creator_id": offer.creator_id,
            "campaign_id": offer.campaign_id,
            "proposed_price": offer.proposed_price,
            "message": offer.message,
            "status": offer.status,
            "match_score": offer.match_score,
            "match_factors": dict(offer.match_factors or {}),
            "created_at": offer.created_at,
            "updated_at": offer.updated_at,
        }

    @staticmethod
    def _serialize_participation(participation: CreatorMarketplaceParticipation) -> dict[str, Any]:
        return {
            "id": participation.id,
            "creator_id": participation.creator_id,
            "campaign_id": participation.campaign_id,
            "clips_submitted": list(participation.clips_submitted or []),
            "performance_metrics": dict(participation.performance_metrics or {}),
            "gross_payout": participation.gross_payout,
            "payout_earned": participation.payout_earned,
            "platform_fee_amount": participation.platform_fee_amount,
            "wallet_transaction_id": participation.wallet_transaction_id,
            "brand_feedback_score": participation.brand_feedback_score,
            "reputation_score_snapshot": participation.reputation_score_snapshot,
            "created_at": participation.created_at,
            "updated_at": participation.updated_at,
        }

    @staticmethod
    def _serialize_reputation(reputation: CreatorMarketplaceReputationScore) -> dict[str, Any]:
        return {
            "creator_id": reputation.creator_id,
            "creator_reputation_score": reputation.reputation_score,
            "delivery_success_score": reputation.delivery_success_score,
            "campaign_performance_score": reputation.campaign_performance_score,
            "brand_feedback_score": reputation.brand_feedback_score,
            "completed_campaigns": reputation.completed_campaigns,
            "updated_at": reputation.updated_at,
        }

    def _campaign_offer_count(self, campaign_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(CreatorMarketplaceOffer).where(
                    CreatorMarketplaceOffer.campaign_id == campaign_id
                )
            )
            or 0
        )

    def _campaign_participant_count(self, campaign_id: str) -> int:
        return int(
            self.session.scalar(
                select(func.count()).select_from(CreatorMarketplaceParticipation).where(
                    CreatorMarketplaceParticipation.campaign_id == campaign_id
                )
            )
            or 0
        )

    def _remaining_budget(self, campaign_id: str) -> Decimal:
        campaign = self.session.get(CreatorMarketplaceCampaign, campaign_id)
        if campaign is None:
            raise CreatorMarketplaceNotFoundError("Campaign was not found.")
        allocated = self.session.scalar(
            select(func.coalesce(func.sum(CreatorMarketplaceParticipation.gross_payout), 0)).where(
                CreatorMarketplaceParticipation.campaign_id == campaign_id
            )
        )
        return self._quantize(self._to_decimal(campaign.budget) - self._to_decimal(allocated))

    def _performance_basis_total(
        self,
        *,
        campaign: CreatorMarketplaceCampaign,
        clips_submitted: list[dict[str, Any]],
    ) -> int:
        basis_key = {
            CreatorMarketplaceCampaignPayoutBasis.VIEWS: "views",
            CreatorMarketplaceCampaignPayoutBasis.ENGAGEMENT: "engagement",
            CreatorMarketplaceCampaignPayoutBasis.CONVERSIONS: "conversions",
        }[campaign.payout_basis]
        return sum(int(clip.get(basis_key) or 0) for clip in clips_submitted)

    def _get_campaign(self, campaign_id: str) -> CreatorMarketplaceCampaign:
        campaign = self.session.get(CreatorMarketplaceCampaign, campaign_id)
        if campaign is None:
            raise CreatorMarketplaceNotFoundError("Campaign was not found.")
        return campaign

    def _get_creator_profile(self, *, actor: User, required: bool = True) -> CreatorProfile | None:
        profile = self.session.scalar(
            select(CreatorProfile).where(CreatorProfile.user_id == actor.id)
        )
        if profile is None and required:
            raise CreatorMarketplaceNotFoundError("Creator profile was not found.")
        return profile

    @staticmethod
    def _ensure_brand_actor(*, campaign: CreatorMarketplaceCampaign, actor: User) -> None:
        if campaign.brand_id != actor.id:
            raise CreatorMarketplacePermissionError("Only the campaign brand can accept creator offers.")

    def _create_notification(
        self,
        *,
        user_id: str,
        topic: str,
        template_key: str,
        resource_type: str,
        resource_id: str,
        message: str,
        metadata: dict[str, Any],
    ) -> None:
        self.session.add(
            NotificationRecord(
                user_id=user_id,
                topic=topic,
                template_key=template_key,
                resource_type=resource_type,
                resource_id=resource_id,
                message=message,
                metadata_json=metadata,
            )
        )

    def _performance_score(self, performance_metrics: dict[str, Any] | None) -> float:
        payload = performance_metrics or {}
        views = max(0, int(payload.get("views") or 0))
        engagement = max(0, int(payload.get("engagement") or 0))
        conversions = max(0, int(payload.get("conversions") or 0))
        engagement_rate = float(payload.get("engagement_rate") or ((engagement / views) if views else 0.0))
        conversion_rate = float(payload.get("conversion_rate") or ((conversions / views) if views else 0.0))
        engagement_score = min(100.0, engagement_rate * 400.0)
        conversion_score = min(100.0, conversion_rate * 1000.0)
        return round((engagement_score * 0.6) + (conversion_score * 0.4), 2)

    @staticmethod
    def _participation_has_delivery(participation: CreatorMarketplaceParticipation) -> bool:
        if participation.clips_submitted:
            return True
        metrics = participation.performance_metrics or {}
        return any(bool(metrics.get(key)) for key in ("views", "engagement", "conversions"))

    @staticmethod
    def _match_to_payload(match: CampaignMatchResult) -> dict[str, Any]:
        return {
            "match_score": match.match_score,
            "format_strength_score": match.format_strength_score,
            "audience_match_score": match.audience_match_score,
            "past_performance_score": match.past_performance_score,
            "reasons": list(match.reasons),
        }

    @classmethod
    def _normalize_formats(cls, formats: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for value in formats:
            cleaned = cls._clean_optional(value)
            if cleaned is None:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            normalized.append(key)
            seen.add(key)
        return normalized

    @classmethod
    def _normalize_target_audience(cls, payload: Any) -> dict[str, Any]:
        if payload is None:
            return {}
        if isinstance(payload, str):
            cleaned = cls._clean_optional(payload)
            return {"tags": [cleaned]} if cleaned is not None else {}
        if isinstance(payload, list):
            return {"tags": cls._normalize_formats([str(item) for item in payload if item is not None])}
        if isinstance(payload, dict):
            normalized: dict[str, Any] = {}
            for key, value in payload.items():
                if not isinstance(key, str):
                    continue
                if isinstance(value, str):
                    cleaned = cls._clean_optional(value)
                    if cleaned is not None:
                        normalized[key] = cleaned
                elif isinstance(value, list):
                    normalized[key] = cls._normalize_formats([str(item) for item in value if item is not None])
                elif isinstance(value, dict):
                    normalized[key] = cls._normalize_target_audience(value)
                else:
                    normalized[key] = value
            return normalized
        raise CreatorMarketplaceValidationError("target_audience must be an object, string, or list of tags.")

    @classmethod
    def _clean_required(cls, value: str | None, *, field_name: str) -> str:
        cleaned = cls._clean_optional(value)
        if cleaned is None:
            raise CreatorMarketplaceValidationError(f"{field_name} cannot be blank.")
        return cleaned

    @staticmethod
    def _clean_optional(value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @staticmethod
    def _display_name(user: User | None) -> str:
        if user is None:
            return "Unknown Brand"
        for value in (user.display_name, user.full_name, user.username, user.email):
            if value and value.strip():
                return value.strip()
        return user.id

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if value is None:
            return Decimal("0.0000")
        return Decimal(str(value))

    @classmethod
    def _quantize(cls, value: Any) -> Decimal:
        return cls._to_decimal(value).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)
