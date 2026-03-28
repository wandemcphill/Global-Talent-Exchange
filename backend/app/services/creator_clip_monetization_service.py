from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.trust_middleware import SharedTrustMiddleware
from app.models.base import generate_uuid
from app.models.creator_clip_monetization import CreatorClipRevenueAttribution
from app.models.highlight_share import HighlightShareExport
from app.models.user import User
from app.models.wallet import LedgerEntryReason, LedgerSourceTag, LedgerUnit
from app.services.earnings import CreatorClipSplit, calculate_creator_clip_split, normalize_amount
from app.viral.trust import TrustScoreService, build_trust_score_service
from app.viral.trust_metrics import ClipTrustMetricsReader, build_clip_trust_metrics_reader
from app.wallets.service import LedgerPosting, WalletService


class CreatorClipMonetizationError(ValueError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


@dataclass(frozen=True, slots=True)
class CreatorClipEarningsSummary:
    generated_clip_count: int
    monetized_clip_count: int
    total_views: int
    total_gross_revenue_credit: Decimal
    total_creator_payout_credit: Decimal
    total_platform_share_credit: Decimal
    total_growth_pool_retained_credit: Decimal
    total_viral_bonus_credit: Decimal
    total_referral_bonus_credit: Decimal
    total_weekly_top_creator_bonus_credit: Decimal
    viral_clip_count: int
    wallet_balance_credit: Decimal
    wallet_available_credit: Decimal
    wallet_currency: str


class CreatorClipMonetizationService:
    def __init__(
        self,
        session: Session,
        *,
        wallet_service: WalletService | None = None,
        trust_service: TrustScoreService | None = None,
        trust_reader: ClipTrustMetricsReader | None = None,
    ) -> None:
        self.session = session
        self.wallet_service = wallet_service or WalletService()
        self.trust_service = trust_service or build_trust_score_service()
        self.trust_reader = trust_reader or build_clip_trust_metrics_reader()
        self.trust_middleware = SharedTrustMiddleware(session=session, trust_service=self.trust_service)

    def attribute_revenue(
        self,
        *,
        export_id: str,
        payload,
        actor: User | None = None,
    ) -> CreatorClipRevenueAttribution:
        export = self.session.get(HighlightShareExport, export_id)
        if export is None:
            raise CreatorClipMonetizationError("Highlight share export was not found.")

        creator = self.session.get(User, export.user_id)
        if creator is None:
            raise CreatorClipMonetizationError("Creator wallet owner for this clip was not found.")
        creator_trust = self.trust_middleware.decision_for_user(creator)
        if creator_trust.blocked or creator_trust.shadow_banned or not creator_trust.monetization_eligible:
            raise CreatorClipMonetizationError("Creator trust score is too low for clip monetization eligibility.")

        source_reference = payload.source_reference or f"clip-attribution:{export.id}:{generate_uuid()}"
        existing = self.session.scalar(
            select(CreatorClipRevenueAttribution).where(
                CreatorClipRevenueAttribution.export_id == export.id,
                CreatorClipRevenueAttribution.source_reference == source_reference,
            )
        )
        if existing is not None:
            return existing

        attribution_metadata = dict(payload.metadata_json or {})
        trust_summary = self.trust_reader.resolve(
            clip_id=payload.clip_id,
            metadata={
                **attribution_metadata,
                "avg_trust_score": payload.avg_trust_score,
                "clip_trust_score": payload.clip_trust_score,
                "user_trust_scores": list(payload.user_trust_scores or []),
            },
        )
        split = calculate_creator_clip_split(
            views=payload.views,
            platform_payout_revenue_credit=payload.platform_payout_revenue_credit,
            in_app_ad_revenue_credit=payload.in_app_ad_revenue_credit,
            sponsored_clip_revenue_credit=payload.sponsored_clip_revenue_credit,
            rpm_per_view=payload.rpm_per_view,
            referral_boost_bps=payload.referral_boost_bps,
            weekly_top_creator_bonus_credit=payload.weekly_top_creator_bonus_credit,
            force_viral_bonus=payload.force_viral_bonus,
            avg_trust_score=trust_summary.avg_trust_score,
            clip_trust_score=trust_summary.clip_trust_score,
            user_trust_scores=list(payload.user_trust_scores or []),
        )
        if split.gross_revenue_credit <= Decimal("0.0000") and not split.trust_rejected:
            raise CreatorClipMonetizationError("Clip revenue attribution requires views or positive revenue.")

        reference = f"creator-clip-attribution:{generate_uuid()}"
        attribution = CreatorClipRevenueAttribution(
            export_id=export.id,
            creator_user_id=creator.id,
            match_key=export.match_key,
            source_reference=source_reference,
            views=split.views,
            rpm_per_view=split.rpm_per_view,
            platform_payout_revenue_credit=split.platform_payout_revenue_credit,
            in_app_ad_revenue_credit=split.in_app_ad_revenue_credit,
            sponsored_clip_revenue_credit=split.sponsored_clip_revenue_credit,
            gross_revenue_credit=split.gross_revenue_credit,
            creator_base_share_credit=split.creator_base_share_credit,
            platform_share_credit=split.platform_share_credit,
            growth_pool_share_credit=split.growth_pool_share_credit,
            viral_bonus_credit=split.viral_bonus_credit,
            referral_bonus_credit=split.referral_bonus_credit,
            weekly_top_creator_bonus_credit=split.weekly_top_creator_bonus_credit,
            creator_payout_credit=split.creator_payout_credit,
            growth_pool_retained_credit=split.growth_pool_retained_credit,
            is_viral=split.is_viral,
            wallet_reference=reference,
            metadata_json={
                "revenue_mode": split.revenue_mode,
                "share_title": export.share_title,
                "aspect_ratio": export.aspect_ratio,
                "clip_id": payload.clip_id,
                "effective_views": str(split.effective_views),
                "avg_trust_score": str(split.avg_trust_score),
                "clip_trust_score": str(split.clip_trust_score),
                "trust_rejected": split.trust_rejected,
                "payout_eligible": trust_summary.payout_eligible,
                "viral_boost_eligible": trust_summary.viral_boost_eligible,
                "creator_trust_score": creator_trust.trust_score,
                "creator_trust_shadow_banned": creator_trust.shadow_banned,
                "creator_trust_flags": list(creator_trust.suspicious_flags),
                **attribution_metadata,
            },
        )
        self.session.add(attribution)
        self.session.flush()

        self._post_wallet_allocation(
            creator=creator,
            split=split,
            reference=reference,
            actor=actor,
            export=export,
        )
        return attribution

    def list_attributions_for_creator(self, *, actor: User, limit: int = 100) -> list[CreatorClipRevenueAttribution]:
        stmt = (
            select(CreatorClipRevenueAttribution)
            .where(CreatorClipRevenueAttribution.creator_user_id == actor.id)
            .order_by(CreatorClipRevenueAttribution.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    def build_creator_summary(self, *, actor: User) -> CreatorClipEarningsSummary:
        attributions = list(
            self.session.scalars(
                select(CreatorClipRevenueAttribution)
                .where(CreatorClipRevenueAttribution.creator_user_id == actor.id)
                .order_by(CreatorClipRevenueAttribution.created_at.desc())
            ).all()
        )
        generated_clip_count = int(
            self.session.scalar(
                select(func.count())
                .select_from(HighlightShareExport)
                .where(HighlightShareExport.user_id == actor.id)
            )
            or 0
        )
        monetized_clip_ids = {item.export_id for item in attributions}
        viral_clip_ids = {item.export_id for item in attributions if item.is_viral}
        wallet_summary = self.wallet_service.get_wallet_summary(self.session, actor, currency=LedgerUnit.CREDIT)
        return CreatorClipEarningsSummary(
            generated_clip_count=generated_clip_count,
            monetized_clip_count=len(monetized_clip_ids),
            total_views=sum(int(item.views) for item in attributions),
            total_gross_revenue_credit=normalize_amount(sum((item.gross_revenue_credit for item in attributions), Decimal("0.0000"))),
            total_creator_payout_credit=normalize_amount(sum((item.creator_payout_credit for item in attributions), Decimal("0.0000"))),
            total_platform_share_credit=normalize_amount(sum((item.platform_share_credit for item in attributions), Decimal("0.0000"))),
            total_growth_pool_retained_credit=normalize_amount(sum((item.growth_pool_retained_credit for item in attributions), Decimal("0.0000"))),
            total_viral_bonus_credit=normalize_amount(sum((item.viral_bonus_credit for item in attributions), Decimal("0.0000"))),
            total_referral_bonus_credit=normalize_amount(sum((item.referral_bonus_credit for item in attributions), Decimal("0.0000"))),
            total_weekly_top_creator_bonus_credit=normalize_amount(
                sum((item.weekly_top_creator_bonus_credit for item in attributions), Decimal("0.0000"))
            ),
            viral_clip_count=len(viral_clip_ids),
            wallet_balance_credit=wallet_summary.total_balance,
            wallet_available_credit=wallet_summary.available_balance,
            wallet_currency=wallet_summary.currency.value,
        )

    def _post_wallet_allocation(
        self,
        *,
        creator: User,
        split: CreatorClipSplit,
        reference: str,
        actor: User | None,
        export: HighlightShareExport,
    ) -> None:
        if (
            split.gross_revenue_credit <= Decimal("0.0000")
            and split.creator_payout_credit <= Decimal("0.0000")
            and split.platform_share_credit <= Decimal("0.0000")
            and split.growth_pool_retained_credit <= Decimal("0.0000")
        ):
            return
        revenue_account = self.wallet_service.ensure_creator_clip_revenue_account(self.session, LedgerUnit.CREDIT)
        creator_account = self.wallet_service.get_user_account(self.session, creator, LedgerUnit.CREDIT)
        treasury_account = self.wallet_service.ensure_treasury_account(self.session, LedgerUnit.CREDIT)
        growth_pool_account = self.wallet_service.ensure_rewards_pool_account(self.session, LedgerUnit.CREDIT)

        postings = [
            LedgerPosting(
                account=revenue_account,
                amount=-split.gross_revenue_credit,
                source_tag=LedgerSourceTag.CREATOR_CLIP_REVENUE,
            ),
            LedgerPosting(
                account=creator_account,
                amount=split.creator_payout_credit,
                source_tag=LedgerSourceTag.CREATOR_CLIP_REVENUE,
            ),
        ]
        if split.platform_share_credit > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=treasury_account,
                    amount=split.platform_share_credit,
                    source_tag=LedgerSourceTag.CREATOR_CLIP_REVENUE,
                )
            )
        if split.growth_pool_retained_credit > Decimal("0.0000"):
            postings.append(
                LedgerPosting(
                    account=growth_pool_account,
                    amount=split.growth_pool_retained_credit,
                    source_tag=LedgerSourceTag.CREATOR_CLIP_REVENUE,
                )
            )
        self.wallet_service.append_transaction(
            self.session,
            postings=postings,
            reason=LedgerEntryReason.ADJUSTMENT,
            source_tag=LedgerSourceTag.CREATOR_CLIP_REVENUE,
            reference=reference,
            description=f"Creator clip revenue attribution for export {export.id}",
            actor=actor,
            metadata={
                "export_id": export.id,
                "match_key": export.match_key,
                "creator_user_id": creator.id,
            },
        )


__all__ = [
    "CreatorClipEarningsSummary",
    "CreatorClipMonetizationError",
    "CreatorClipMonetizationService",
]
