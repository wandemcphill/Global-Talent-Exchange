"""Backfill regen staff portraits and gender metadata on club_staff_profiles.

Revision ID: 20261122_0275_regen_staff_facebank_and_starter_squad_sync
Revises: 20261121_0274_optional_unfiled_club_scores
"""

from __future__ import annotations

import json
import zlib
from typing import Any

import sqlalchemy as sa
from alembic import op

revision = "20261122_0275_regen_staff_facebank_and_starter_squad_sync"
down_revision = "20261121_0274_optional_unfiled_club_scores"
branch_labels = None
depends_on = None

_FEMALE_GIVEN_NAMES = frozenset(
    {
        "Adaeze",
        "Ifeoma",
        "Ngozi",
        "Yewande",
        "Amara",
        "Abena",
        "Lerato",
        "Amina",
        "Lucia",
        "Camila",
        "Ines",
        "Anika",
        "Mei",
        "Priya",
        "Leila",
        "Noor",
        "Elena",
        "Helena",
        "Clara",
        "Sofia",
    }
)

_FACE_GROUPS = (
    "west_african",
    "north_european",
    "east_asian",
    "south_european",
    "middle_eastern",
    "latino",
    "mixed_braids",
    "blonde",
)
_MALE_PORTRAITS = ("41", "54", "bald", "beard", "glasses")
_FEMALE_PORTRAITS = ("42", "glasses", "long", "cropped")


def _face_group_for_nation(nation: str, index: int) -> str:
    lower = (nation or "").lower()
    if any(k in lower for k in ("nigeria", "ghana", "senegal", "south africa", "kenya", "cameroon", "ivory", "mali")):
        return "west_african"
    if any(k in lower for k in ("morocco", "egypt", "turkey", "saudi")):
        return "middle_eastern"
    if any(k in lower for k in ("brazil", "argentina", "colombia", "mexico")):
        return "latino"
    if any(k in lower for k in ("portugal", "spain", "italy", "greece")):
        return "south_european"
    if any(k in lower for k in ("japan", "south korea", "korea", "china", "india")):
        return "east_asian"
    if any(k in lower for k in ("sweden", "norway", "denmark", "finland")):
        return "blonde"
    if "france" in lower and index % 2 == 1:
        return "mixed_braids"
    return "north_european"


def _portrait_filename(group: str, gender: str, index: int) -> str:
    kind = "f" if gender == "female" else "m"
    variants = _FEMALE_PORTRAITS if gender == "female" else _MALE_PORTRAITS
    slot = (index // len(_FACE_GROUPS)) % len(variants)
    return f"mature_{kind}_{group}_{variants[slot]}.jpg"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("club_staff_profiles"):
        return

    rows = bind.execute(sa.text("SELECT id, display_name, metadata_json FROM club_staff_profiles")).fetchall()

    for row in rows:
        profile_id = str(row[0])
        display_name = str(row[1] or "").strip()
        raw_meta = row[2]
        if isinstance(raw_meta, str):
            try:
                meta: dict[str, Any] = json.loads(raw_meta) if raw_meta.strip() else {}
            except Exception:
                meta = {}
        elif isinstance(raw_meta, dict):
            meta = dict(raw_meta)
        else:
            meta = {}

        changed = False
        first_name = display_name.split(" ", 1)[0] if display_name else ""
        gender = str(meta.get("gender") or "").strip().lower()
        if gender not in {"female", "male"}:
            gender = "female" if first_name in _FEMALE_GIVEN_NAMES else "male"
            meta["gender"] = gender
            changed = True

        nation = str(meta.get("nation") or "")
        seed_idx = zlib.crc32(f"{profile_id}:{display_name}".encode("utf-8")) & 0xFFFFFFFF
        face_group = str(meta.get("face_group") or "").strip()
        if not face_group:
            face_group = (
                _face_group_for_nation(nation, seed_idx) if nation else _FACE_GROUPS[seed_idx % len(_FACE_GROUPS)]
            )
            meta["face_group"] = face_group
            changed = True

        portrait_url = str(meta.get("portrait_url") or "").strip()
        if not portrait_url:
            meta["portrait_url"] = f"/staff-portraits/{_portrait_filename(face_group, gender, seed_idx)}"
            changed = True

        if changed:
            bind.execute(
                sa.text("UPDATE club_staff_profiles SET metadata_json = :meta WHERE id = :id"),
                {"meta": json.dumps(meta), "id": profile_id},
            )


def downgrade() -> None:
    pass
