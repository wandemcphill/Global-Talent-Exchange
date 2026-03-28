from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_COUNTRY_BRANDS: dict[str, tuple[str, ...]] = {
    "NG": ("MTN", "BetKing", "Flutterwave"),
    "GB": ("Nike", "Adidas", "EA Sports"),
    "US": ("Nike", "Adidas", "FanDuel"),
    "GLOBAL": ("Nike", "Adidas", "EA Sports"),
}

_MARKET_HINTS: dict[str, str] = {
    "lagos": "NG",
    "abuja": "NG",
    "nigeria": "NG",
    "london": "GB",
    "manchester": "GB",
    "new york": "US",
    "los angeles": "US",
}


@dataclass(frozen=True, slots=True)
class AdTargetingProfile:
    country: str = "GLOBAL"
    coins: int = 0
    is_premium_user: bool = False
    favorite_clubs: tuple[str, ...] = ()
    interests: tuple[str, ...] = ()

    @property
    def normalized_country(self) -> str:
        raw = self.country.strip().upper()
        return raw or "GLOBAL"


def profile_from_input(user: AdTargetingProfile | dict[str, Any] | None) -> AdTargetingProfile:
    if isinstance(user, AdTargetingProfile):
        return user
    if not isinstance(user, dict):
        return AdTargetingProfile()

    def _as_tuple(value: object) -> tuple[str, ...]:
        if isinstance(value, (list, tuple, set)):
            return tuple(str(item).strip() for item in value if str(item).strip())
        return ()

    coins = user.get("coins", 0)
    try:
        normalized_coins = max(0, int(coins or 0))
    except (TypeError, ValueError):
        normalized_coins = 0

    return AdTargetingProfile(
        country=str(user.get("country", "GLOBAL") or "GLOBAL"),
        coins=normalized_coins,
        is_premium_user=bool(
            user.get("is_premium_user")
            or user.get("premium_ad_free")
            or user.get("premium")
        ),
        favorite_clubs=_as_tuple(user.get("favorite_clubs")),
        interests=_as_tuple(user.get("interests")),
    )


def infer_country_from_match(match: dict[str, Any] | None, *, fallback: str = "GLOBAL") -> str:
    if not isinstance(match, dict):
        return fallback
    explicit = str(match.get("country") or match.get("market_country") or "").strip()
    if explicit:
        return explicit.upper()
    haystacks = (
        str(match.get("home_team_name", "")).lower(),
        str(match.get("away_team_name", "")).lower(),
        str(match.get("competition_name", "")).lower(),
    )
    for haystack in haystacks:
        for token, country in _MARKET_HINTS.items():
            if token in haystack:
                return country
    return fallback


def match_user_to_ads(user: AdTargetingProfile | dict[str, Any] | None) -> list[str]:
    profile = profile_from_input(user)
    brands = _COUNTRY_BRANDS.get(profile.normalized_country, _COUNTRY_BRANDS["GLOBAL"])
    return list(brands)


def targeting_tags(
    user: AdTargetingProfile | dict[str, Any] | None,
    *,
    match: dict[str, Any] | None = None,
) -> list[str]:
    profile = profile_from_input(user)
    country = profile.normalized_country or infer_country_from_match(match, fallback="GLOBAL")
    tags = [
        f"country:{country}",
        "tier:premium" if profile.is_premium_user else "tier:standard",
        "wallet:low" if profile.coins < 50 else "wallet:ready",
    ]
    tags.extend(f"club:{club}" for club in profile.favorite_clubs[:2])
    tags.extend(f"interest:{interest}" for interest in profile.interests[:2])
    return tags


__all__ = [
    "AdTargetingProfile",
    "infer_country_from_match",
    "match_user_to_ads",
    "profile_from_input",
    "targeting_tags",
]
