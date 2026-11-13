"""Portraits for staff who are real people.

Regen staff keep a face from the staff bank. These helpers only point at a
downloaded photograph, or at a bank face for an invented GTEX character.
"""

from __future__ import annotations

import json
import zlib
from functools import lru_cache
from pathlib import Path

MANIFEST_PATH = Path(__file__).with_name("real_staff_portraits.json")

# Original characters. They are not photographed people.
FICTIONAL_STAFF = {
    "dayo adeleke": "male",
    "tunde bakare": "male",
    "tunde mcphill": "male",
    "marcelo vance": "male",
    "carlo castiglione": "male",
    "femi ogunleye": "male",
    "piet de visser jr": "male",
    "carles font": "male",
    "kelechi nwosu": "male",
    "dr. amaka eze": "female",
    "amaka eze": "female",
}


@lru_cache(maxsize=1)
def portrait_map() -> dict[str, str]:
    if not MANIFEST_PATH.is_file():
        return {}
    loaded = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return {}
    return {str(key): str(value) for key, value in loaded.items() if isinstance(value, str)}


def real_staff_portrait_url(folded_name: str) -> str | None:
    return portrait_map().get(folded_name)


def fictional_staff_portrait_url(folded_name: str, gender: str) -> str | None:
    if folded_name not in FICTIONAL_STAFF:
        return None
    from app.owner_console.regen_staff_catalog import FACE_GROUPS, PORTRAIT_PUBLIC_PREFIX, portrait_filename

    kind = gender if gender in {"female", "male"} else FICTIONAL_STAFF[folded_name]
    group = FACE_GROUPS[zlib.crc32(folded_name.encode()) % len(FACE_GROUPS)]
    index = zlib.crc32(f"{folded_name}:{kind}".encode()) & 0xFFFFFFFF
    return f"{PORTRAIT_PUBLIC_PREFIX}/{portrait_filename(group, kind, index)}"
