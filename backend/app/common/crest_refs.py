from __future__ import annotations

_IMAGE_KINDS = ("png", "jpeg", "jpg", "webp", "gif", "svg+xml")


def is_safe_crest_ref(value: str | None) -> bool:
    """Allow site paths, http(s) URLs, and raster or SVG data images."""
    if not value:
        return False
    ref = value.strip()
    lowered = ref.lower()
    if lowered.startswith(("javascript:", "vbscript:")):
        return False
    if lowered.startswith("data:"):
        header = lowered.split(",", 1)[0]
        return header.startswith("data:image/") and any(kind in header for kind in _IMAGE_KINDS)
    return lowered.startswith(("https://", "http://", "/"))
