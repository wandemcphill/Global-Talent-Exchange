from __future__ import annotations

from enum import StrEnum


class ReferralSourceChannel(StrEnum):
    DIRECT_LINK = "direct_link"
    DIRECT_SHARE = "direct_share"
    COMMUNITY_POST = "community_post"
    COMMUNITY_INVITE = "community_invite"
    CREATOR_PROFILE = "creator_profile"
    COMPETITION_LOBBY = "competition_lobby"
    COMPETITION_PAGE = "competition_page"
    DM = "dm"
    QR = "qr"
    PROMO_CAMPAIGN = "promo_campaign"
    MANUAL_ENTRY = "manual_entry"


__all__ = ["ReferralSourceChannel"]
