from __future__ import annotations

from typing import Any, TYPE_CHECKING
from sqlalchemy import select
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    pass


def resolve_player_lifecycle_status(
    player: Any | None,
    share_market: Any | None = None,
) -> tuple[str, str]:
    """Returns (status_code, status_label) for a player.

    The 4 honest lifecycle states:
    1) "active_tradable" -> "Active / Tradable"
    2) "active_not_tradable" -> "Active / Not Tradable"
    3) "inactive_retired" -> "Inactive / Retired"
    4) "unknown_unavailable" -> "Unknown / Unavailable"
    """
    if player is None:
        return ("unknown_unavailable", "Unknown / Unavailable")

    status_attr = getattr(player, "status", None)
    dna_profile = getattr(player, "dna_profile", None) or {}
    metadata_json = getattr(player, "metadata_json", None) or {}

    is_retired_or_inactive = (
        status_attr in ("retired", "inactive")
        or dna_profile.get("retired") is True
        or dna_profile.get("status") in ("retired", "inactive")
        or metadata_json.get("status") in ("retired", "inactive")
        or metadata_json.get("retired") is True
    )

    if status_attr in ("unknown", "unavailable") or metadata_json.get("status") in ("unknown", "unavailable"):
        return ("unknown_unavailable", "Unknown / Unavailable")

    if is_retired_or_inactive:
        return ("inactive_retired", "Inactive / Retired")

    if not bool(getattr(player, "is_tradable", True)):
        return ("active_not_tradable", "Active / Not Tradable")

    # player.is_tradable is True
    market_obj = share_market if share_market is not None else getattr(player, "share_market", None)
    if market_obj is not None and getattr(market_obj, "status", None) == "active":
        return ("active_tradable", "Active / Tradable")

    return ("active_not_tradable", "Active / Not Tradable")


def sync_player_lifecycle_and_market_status(
    session: Session,
    player: Any,
    *,
    is_tradable: bool | None = None,
    is_retired: bool = False,
) -> None:
    """Synchronize Player.is_tradable and PlayerShareMarket.status.

    When a player is retired or marked untradable:
    - player.is_tradable is set to False
    - If is_retired is True, dna_profile['retired'] = True
    - Associated PlayerShareMarket.status is set to 'inactive' if currently 'active'
    """
    from app.models.player_token_market import PlayerShareMarket

    if is_tradable is not None:
        player.is_tradable = is_tradable
    if is_retired:
        player.is_tradable = False
        dna = dict(getattr(player, "dna_profile", None) or {})
        dna["retired"] = True
        player.dna_profile = dna

    if not bool(player.is_tradable):
        market = getattr(player, "share_market", None) or session.scalar(
            select(PlayerShareMarket).where(PlayerShareMarket.player_id == player.id)
        )
        if market is not None and market.status == "active":
            market.status = "inactive"


__all__ = [
    "resolve_player_lifecycle_status",
    "sync_player_lifecycle_and_market_status",
]
