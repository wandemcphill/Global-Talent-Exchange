from __future__ import annotations


CPM: dict[str, float] = {
    "goal_highlight": 15.0,
    "highlight": 12.0,
    "preroll": 8.0,
    "live_banner": 10.0,
    "rewarded": 20.0,
}


def pricing_key(ad_type: str, *, event_type: str | None = None) -> str:
    normalized_type = ad_type.strip().lower()
    normalized_event = (event_type or "").strip().lower()
    if normalized_type == "sponsored_highlight":
        if normalized_event in {"goal", "goals", "penalty", "penalties"}:
            return "goal_highlight"
        return "highlight"
    if normalized_type == "pre_roll":
        return "preroll"
    if normalized_type == "live_banner":
        return "live_banner"
    if normalized_type == "rewarded_ad":
        return "rewarded"
    return "highlight"


def resolve_cpm(
    ad_type: str,
    *,
    event_type: str | None = None,
    is_final: bool = False,
    is_major_match: bool = False,
    popularity_multiplier: float = 1.0,
) -> float:
    key = pricing_key(ad_type, event_type=event_type)
    base = CPM.get(key, 10.0)
    multiplier = max(0.5, popularity_multiplier)
    if is_major_match:
        multiplier *= 1.15
    if is_final:
        multiplier *= 1.2
    return round(base * multiplier, 2)


def estimate_value_usd(
    ad_type: str,
    *,
    event_type: str | None = None,
    impressions: int = 1,
    is_final: bool = False,
    is_major_match: bool = False,
) -> float:
    cpm = resolve_cpm(
        ad_type,
        event_type=event_type,
        is_final=is_final,
        is_major_match=is_major_match,
    )
    return round((cpm / 1000.0) * max(1, impressions), 4)


__all__ = ["CPM", "estimate_value_usd", "pricing_key", "resolve_cpm"]
