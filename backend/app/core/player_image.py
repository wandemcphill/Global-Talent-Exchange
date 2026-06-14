"""
Canonical player image resolver.

All player image URL generation must go through this module.
Images are already stored in Cloudinary under gtex/players/{sportmonks_player_id}.
No uploads, no migrations, no downloads.
"""
from __future__ import annotations

import os
from functools import lru_cache


def _cloud_name() -> str:
    return os.environ.get("CLOUDINARY_CLOUD_NAME", "")


def get_player_public_id(sportmonks_player_id: int | str) -> str:
    """Return the canonical Cloudinary public_id for a player."""
    return f"gtex/players/{sportmonks_player_id}"


def get_player_image_url(
    sportmonks_player_id: int | str,
    *,
    width: int | None = None,
    height: int | None = None,
    format: str = "auto",
    quality: str = "auto",
    cloud_name: str | None = None,
) -> str | None:
    """
    Return a Cloudinary delivery URL for a player image.

    Returns None when CLOUDINARY_CLOUD_NAME is not configured so callers
    can fall back gracefully rather than serving a broken URL.
    """
    resolved_cloud = cloud_name or _cloud_name()
    if not resolved_cloud:
        return None

    public_id = get_player_public_id(sportmonks_player_id)

    transforms: list[str] = [f"f_{format}", f"q_{quality}"]
    if width:
        transforms.append(f"w_{width}")
    if height:
        transforms.append(f"h_{height}")

    transform_str = ",".join(transforms)
    return f"https://res.cloudinary.com/{resolved_cloud}/image/upload/{transform_str}/{public_id}"


def get_player_image_url_for_card(sportmonks_player_id: int | str) -> str | None:
    """Standard card portrait: 200×200, auto quality/format."""
    return get_player_image_url(sportmonks_player_id, width=200, height=200)


def get_player_image_url_for_thumbnail(sportmonks_player_id: int | str) -> str | None:
    """Small thumbnail: 80×80."""
    return get_player_image_url(sportmonks_player_id, width=80, height=80)
