from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.scale_backbone import CreatorClipEarningsProjectionRecord
from app.models.user import User
from app.services.creator_clip_monetization_service import CreatorClipEarningsSummary, CreatorClipMonetizationService


@dataclass(slots=True)
class CreatorClipEarningsProjectionService:
    session: Session

    def load(self, *, creator_user_id: str) -> CreatorClipEarningsSummary | None:
        record = self.session.get(CreatorClipEarningsProjectionRecord, creator_user_id)
        if record is None:
            return None
        return CreatorClipEarningsSummary(
            generated_clip_count=int(record.generated_clip_count or 0),
            monetized_clip_count=int(record.monetized_clip_count or 0),
            total_views=int(record.total_views or 0),
            total_gross_revenue_credit=record.total_gross_revenue_credit,
            total_creator_payout_credit=record.total_creator_payout_credit,
            total_platform_share_credit=record.total_platform_share_credit,
            total_growth_pool_retained_credit=record.total_growth_pool_retained_credit,
            total_viral_bonus_credit=record.total_viral_bonus_credit,
            total_referral_bonus_credit=record.total_referral_bonus_credit,
            total_weekly_top_creator_bonus_credit=record.total_weekly_top_creator_bonus_credit,
            viral_clip_count=int(record.viral_clip_count or 0),
            wallet_balance_credit=record.wallet_balance_credit,
            wallet_available_credit=record.wallet_available_credit,
            wallet_currency=record.wallet_currency,
        )

    def refresh(self, *, creator_user_id: str) -> CreatorClipEarningsProjectionRecord:
        creator = self.session.get(User, creator_user_id)
        if creator is None:
            raise ValueError("Creator was not found for earnings projection refresh.")
        summary = CreatorClipMonetizationService(self.session).build_creator_summary(actor=creator)
        record = self.session.get(CreatorClipEarningsProjectionRecord, creator_user_id)
        if record is None:
            record = CreatorClipEarningsProjectionRecord(user_id=creator_user_id)
            self.session.add(record)
        record.generated_clip_count = int(summary.generated_clip_count)
        record.monetized_clip_count = int(summary.monetized_clip_count)
        record.total_views = int(summary.total_views)
        record.total_gross_revenue_credit = summary.total_gross_revenue_credit
        record.total_creator_payout_credit = summary.total_creator_payout_credit
        record.total_platform_share_credit = summary.total_platform_share_credit
        record.total_growth_pool_retained_credit = summary.total_growth_pool_retained_credit
        record.total_viral_bonus_credit = summary.total_viral_bonus_credit
        record.total_referral_bonus_credit = summary.total_referral_bonus_credit
        record.total_weekly_top_creator_bonus_credit = summary.total_weekly_top_creator_bonus_credit
        record.viral_clip_count = int(summary.viral_clip_count)
        record.wallet_balance_credit = summary.wallet_balance_credit
        record.wallet_available_credit = summary.wallet_available_credit
        record.wallet_currency = summary.wallet_currency
        record.metadata_json = {}
        record.last_error = None
        self.session.flush()
        return record


__all__ = ["CreatorClipEarningsProjectionService"]
