from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.viral.trust_metrics import LOW_CLIP_TRUST_THRESHOLD


AMOUNT_QUANTUM = Decimal("0.0001")
DEFAULT_RPM_PER_VIEW = Decimal("0.0020")
CREATOR_USER_SPLIT = Decimal("0.5000")
PLATFORM_SPLIT = Decimal("0.3000")
GROWTH_POOL_SPLIT = Decimal("0.2000")
VIRAL_CLIP_THRESHOLD_VIEWS = 100_000
VIRAL_GROWTH_POOL_BONUS_BPS = 2500
FULL_TRUST_SCORE = Decimal("1.0000")
LOW_CLIP_TRUST_THRESHOLD_DECIMAL = Decimal(str(LOW_CLIP_TRUST_THRESHOLD)).quantize(
    AMOUNT_QUANTUM,
    rounding=ROUND_HALF_UP,
)


def normalize_amount(value: Decimal | int | float | str) -> Decimal:
    return Decimal(str(value)).quantize(AMOUNT_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_earnings(views: Decimal | int | float | str, rpm: Decimal = DEFAULT_RPM_PER_VIEW) -> Decimal:
    return normalize_amount(max(_as_decimal(views), Decimal("0.0000")) * Decimal(rpm))


@dataclass(frozen=True, slots=True)
class CreatorClipSplit:
    views: int
    effective_views: Decimal
    rpm_per_view: Decimal
    avg_trust_score: Decimal
    clip_trust_score: Decimal
    derived_view_revenue_credit: Decimal
    platform_payout_revenue_credit: Decimal
    in_app_ad_revenue_credit: Decimal
    sponsored_clip_revenue_credit: Decimal
    gross_revenue_credit: Decimal
    creator_base_share_credit: Decimal
    platform_share_credit: Decimal
    growth_pool_share_credit: Decimal
    viral_bonus_credit: Decimal
    referral_bonus_credit: Decimal
    weekly_top_creator_bonus_credit: Decimal
    creator_payout_credit: Decimal
    growth_pool_retained_credit: Decimal
    is_viral: bool
    trust_rejected: bool
    revenue_mode: str


def calculate_creator_clip_split(
    *,
    views: int,
    platform_payout_revenue_credit: Decimal | int | float | str = Decimal("0.0000"),
    in_app_ad_revenue_credit: Decimal | int | float | str = Decimal("0.0000"),
    sponsored_clip_revenue_credit: Decimal | int | float | str = Decimal("0.0000"),
    rpm_per_view: Decimal = DEFAULT_RPM_PER_VIEW,
    referral_boost_bps: int = 0,
    weekly_top_creator_bonus_credit: Decimal | int | float | str = Decimal("0.0000"),
    force_viral_bonus: bool | None = None,
    avg_trust_score: Decimal | int | float | str | None = None,
    clip_trust_score: Decimal | int | float | str | None = None,
    user_trust_scores: list[Decimal | int | float | str] | None = None,
) -> CreatorClipSplit:
    normalized_views = max(0, int(views))
    normalized_rpm = normalize_amount(rpm_per_view)
    trust_weight_applied = (
        avg_trust_score is not None or clip_trust_score is not None or bool(user_trust_scores)
    )
    resolved_avg_trust = _resolve_avg_trust_score(avg_trust_score, user_trust_scores)
    resolved_clip_trust = _resolve_clip_trust_score(clip_trust_score, user_trust_scores, resolved_avg_trust)
    effective_views = normalize_amount(Decimal(normalized_views) * resolved_avg_trust)
    trust_rejected = resolved_clip_trust < LOW_CLIP_TRUST_THRESHOLD_DECIMAL

    if trust_rejected:
        zero = Decimal("0.0000")
        return CreatorClipSplit(
            views=normalized_views,
            effective_views=zero,
            rpm_per_view=normalized_rpm,
            avg_trust_score=resolved_avg_trust,
            clip_trust_score=resolved_clip_trust,
            derived_view_revenue_credit=zero,
            platform_payout_revenue_credit=zero,
            in_app_ad_revenue_credit=zero,
            sponsored_clip_revenue_credit=zero,
            gross_revenue_credit=zero,
            creator_base_share_credit=zero,
            platform_share_credit=zero,
            growth_pool_share_credit=zero,
            viral_bonus_credit=zero,
            referral_bonus_credit=zero,
            weekly_top_creator_bonus_credit=zero,
            creator_payout_credit=zero,
            growth_pool_retained_credit=zero,
            is_viral=False,
            trust_rejected=True,
            revenue_mode="trust_rejected",
        )

    derived_view_revenue_credit = calculate_earnings(effective_views, normalized_rpm)
    platform_payout = normalize_amount(normalize_amount(platform_payout_revenue_credit) * resolved_avg_trust)
    in_app_ad = normalize_amount(normalize_amount(in_app_ad_revenue_credit) * resolved_avg_trust)
    sponsored = normalize_amount(normalize_amount(sponsored_clip_revenue_credit) * resolved_avg_trust)
    direct_revenue = normalize_amount(platform_payout + in_app_ad + sponsored)

    gross_revenue = direct_revenue if direct_revenue > Decimal("0.0000") else derived_view_revenue_credit
    revenue_mode = "source_total" if direct_revenue > Decimal("0.0000") else "view_estimate"
    if trust_weight_applied and (resolved_avg_trust < FULL_TRUST_SCORE or resolved_clip_trust < FULL_TRUST_SCORE):
        revenue_mode = f"{revenue_mode}_trust_weighted"

    creator_base = normalize_amount(gross_revenue * CREATOR_USER_SPLIT)
    platform_share = normalize_amount(gross_revenue * PLATFORM_SPLIT)
    growth_pool_share = normalize_amount(gross_revenue - creator_base - platform_share)

    is_viral = (
        bool(force_viral_bonus)
        if force_viral_bonus is not None
        else effective_views >= Decimal(str(VIRAL_CLIP_THRESHOLD_VIEWS))
    )
    requested_viral_bonus = (
        normalize_amount(growth_pool_share * Decimal(VIRAL_GROWTH_POOL_BONUS_BPS) / Decimal(10_000))
        if is_viral
        else Decimal("0.0000")
    )
    requested_referral_bonus = normalize_amount(
        growth_pool_share * Decimal(max(0, referral_boost_bps)) / Decimal(10_000)
    )
    requested_weekly_bonus = max(Decimal("0.0000"), normalize_amount(weekly_top_creator_bonus_credit))

    remaining_growth_pool = growth_pool_share
    viral_bonus = min(remaining_growth_pool, requested_viral_bonus)
    remaining_growth_pool = normalize_amount(remaining_growth_pool - viral_bonus)
    referral_bonus = min(remaining_growth_pool, requested_referral_bonus)
    remaining_growth_pool = normalize_amount(remaining_growth_pool - referral_bonus)
    weekly_bonus = min(remaining_growth_pool, requested_weekly_bonus)
    remaining_growth_pool = normalize_amount(remaining_growth_pool - weekly_bonus)

    creator_payout = normalize_amount(creator_base + viral_bonus + referral_bonus + weekly_bonus)

    return CreatorClipSplit(
        views=normalized_views,
        effective_views=effective_views,
        rpm_per_view=normalized_rpm,
        avg_trust_score=resolved_avg_trust,
        clip_trust_score=resolved_clip_trust,
        derived_view_revenue_credit=derived_view_revenue_credit,
        platform_payout_revenue_credit=platform_payout,
        in_app_ad_revenue_credit=in_app_ad,
        sponsored_clip_revenue_credit=sponsored,
        gross_revenue_credit=gross_revenue,
        creator_base_share_credit=creator_base,
        platform_share_credit=platform_share,
        growth_pool_share_credit=growth_pool_share,
        viral_bonus_credit=viral_bonus,
        referral_bonus_credit=referral_bonus,
        weekly_top_creator_bonus_credit=weekly_bonus,
        creator_payout_credit=creator_payout,
        growth_pool_retained_credit=remaining_growth_pool,
        is_viral=is_viral,
        trust_rejected=False,
        revenue_mode=revenue_mode,
    )


def _as_decimal(value: Decimal | int | float | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _normalize_trust_score(value: Decimal | int | float | str | None, *, default: Decimal) -> Decimal:
    if value is None:
        return default
    try:
        score = _as_decimal(value)
    except Exception:
        return default
    return normalize_amount(min(max(score, Decimal("0.0000")), Decimal("1.0000")))


def _resolve_avg_trust_score(
    avg_trust_score: Decimal | int | float | str | None,
    user_trust_scores: list[Decimal | int | float | str] | None,
) -> Decimal:
    if avg_trust_score is not None:
        return _normalize_trust_score(avg_trust_score, default=FULL_TRUST_SCORE)
    if user_trust_scores:
        scores = [_normalize_trust_score(score, default=FULL_TRUST_SCORE) for score in user_trust_scores]
        if scores:
            return normalize_amount(sum(scores) / Decimal(len(scores)))
    return FULL_TRUST_SCORE


def _resolve_clip_trust_score(
    clip_trust_score: Decimal | int | float | str | None,
    user_trust_scores: list[Decimal | int | float | str] | None,
    fallback: Decimal,
) -> Decimal:
    if clip_trust_score is not None:
        return _normalize_trust_score(clip_trust_score, default=fallback)
    if user_trust_scores:
        scores = [_normalize_trust_score(score, default=fallback) for score in user_trust_scores]
        if scores:
            return normalize_amount(sum(scores) / Decimal(len(scores)))
    return fallback


__all__ = [
    "AMOUNT_QUANTUM",
    "CREATOR_USER_SPLIT",
    "CreatorClipSplit",
    "DEFAULT_RPM_PER_VIEW",
    "GROWTH_POOL_SPLIT",
    "PLATFORM_SPLIT",
    "VIRAL_CLIP_THRESHOLD_VIEWS",
    "calculate_creator_clip_split",
    "calculate_earnings",
    "normalize_amount",
]
