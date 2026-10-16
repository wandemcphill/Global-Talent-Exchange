from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas.creator_core import CreatorProfileCore
from app.schemas.referral_core import ReferralValidationResult
from app.schemas.share_code_core import ShareCodeCore


@dataclass(slots=True)
class ReferralValidationService:
    def validate_attribution(
        self,
        *,
        referred_user_id: str,
        share_code: ShareCodeCore,
        referrer_user_id: str | None = None,
        creator_profile: CreatorProfileCore | None = None,
        occurred_at: datetime | None = None,
    ) -> ReferralValidationResult:
        check_time = occurred_at or datetime.now(timezone.utc)
        reasons: list[str] = []

        resolved_referrer_user_id = referrer_user_id or share_code.owner_user_id
        resolved_creator_profile_id = creator_profile.creator_profile_id if creator_profile is not None else share_code.owner_creator_id
        creator_owner_user_id = creator_profile.user_id if creator_profile is not None else None

        if not share_code.is_active:
            reasons.append("share_code_inactive")
        if share_code.starts_at is not None and check_time < share_code.starts_at:
            reasons.append("share_code_not_started")
        if share_code.ends_at is not None and check_time > share_code.ends_at:
            reasons.append("share_code_expired")
        if share_code.max_uses is not None and share_code.current_uses >= share_code.max_uses:
            reasons.append("share_code_exhausted")
        if resolved_referrer_user_id is not None and referred_user_id == resolved_referrer_user_id:
            reasons.append("self_referral_blocked")
        if share_code.owner_user_id is not None and referred_user_id == share_code.owner_user_id:
            reasons.append("owner_self_referral_blocked")
        if creator_owner_user_id is not None and referred_user_id == creator_owner_user_id:
            reasons.append("creator_self_referral_blocked")
        if referrer_user_id is not None and share_code.owner_user_id is not None and referrer_user_id != share_code.owner_user_id:
            reasons.append("share_code_owner_mismatch")
        if creator_profile is not None and share_code.owner_creator_id is not None:
            if creator_profile.creator_profile_id != share_code.owner_creator_id:
                reasons.append("creator_profile_mismatch")

        return ReferralValidationResult(
            is_valid=not reasons,
            attribution_status="qualified" if not reasons else "blocked",
            resolved_referrer_user_id=resolved_referrer_user_id,
            resolved_creator_profile_id=resolved_creator_profile_id,
            reason_codes=tuple(reasons),
        )
