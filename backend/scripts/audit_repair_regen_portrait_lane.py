from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import sys
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

SCRIPT_PATH = Path(__file__).resolve()
BACKEND_ROOT = SCRIPT_PATH.parents[1]
REPO_ROOT = BACKEND_ROOT.parent
for candidate in (REPO_ROOT, BACKEND_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from app.core.database import create_database_engine, create_session_factory, load_model_modules
from app.ingestion.models import Player
from app.models.regen import RegenProfile
from app.models.regen_ecosystem import NationalRegenSeed
from app.services.regen_portrait_service import (
    NEWGEN_FACE_BANK_COLLECTION,
    NEWGEN_FACE_BANK_PROVIDER,
    RegenPortraitService,
)

APPROVED_FACE_BANK_PATH = "/generated-media/regen_newgen_faces/script_skin_hair/"
APPROVED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
DISALLOWED_REGEN_PATH_MARKERS = (
    ".svg",
    "/regen_portraits/",
    "/national_regen_portraits/",
    "/regen_newgen_faces/fm_ai/",
    "/portrait_overrides/",
    "/regen_portrait_overrides/",
)


@dataclass(slots=True)
class RegenPortraitLaneStats:
    apply: bool
    player_regens_scanned: int = 0
    player_regens_current: int = 0
    player_regens_repaired: int = 0
    player_regens_missing_asset: int = 0
    national_seeds_scanned: int = 0
    national_seeds_current: int = 0
    national_seeds_repaired: int = 0
    national_seeds_missing_asset: int = 0
    skipped_banned: int = 0
    repair_needed_samples: list[dict[str, object]] = field(default_factory=list)
    missing_asset_samples: list[dict[str, object]] = field(default_factory=list)
    error_samples: list[dict[str, object]] = field(default_factory=list)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit and optionally repair GTEX regen portraits so every regen uses "
            "the approved regen_newgen_faces/script_skin_hair bank."
        )
    )
    parser.add_argument("--database-url", default=os.environ.get("GTE_DATABASE_URL"))
    parser.add_argument("--apply", action="store_true", help="Write repairs. Default is audit-only.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sample-size", type=int, default=25)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.database_url:
        raise SystemExit("--database-url or GTE_DATABASE_URL is required.")

    load_model_modules()
    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        stats = audit_or_repair(
            session,
            apply=bool(args.apply),
            limit=args.limit,
            sample_size=args.sample_size,
        )
        if args.apply:
            session.commit()
        else:
            session.rollback()
    print(json.dumps(asdict(stats), sort_keys=True, default=str))
    return 0 if not stats.error_samples else 2


def audit_or_repair(
    session: Session,
    *,
    apply: bool,
    limit: int | None = None,
    sample_size: int = 25,
) -> RegenPortraitLaneStats:
    stats = RegenPortraitLaneStats(apply=apply)
    service = RegenPortraitService(session)
    _audit_or_repair_player_regens(
        session,
        service=service,
        stats=stats,
        apply=apply,
        limit=limit,
        sample_size=sample_size,
    )
    _audit_or_repair_national_seeds(
        session,
        service=service,
        stats=stats,
        apply=apply,
        limit=limit,
        sample_size=sample_size,
    )
    return stats


def _audit_or_repair_player_regens(
    session: Session,
    *,
    service: RegenPortraitService,
    stats: RegenPortraitLaneStats,
    apply: bool,
    limit: int | None,
    sample_size: int,
) -> None:
    statement = (
        select(RegenProfile, Player)
        .join(Player, Player.id == RegenProfile.player_id)
        .where(Player.is_real_player.is_(False))
        .order_by(RegenProfile.created_at.desc())
    )
    if limit is not None:
        statement = statement.limit(limit)
    for regen, player in session.execute(statement).all():
        stats.player_regens_scanned += 1
        metadata = _metadata(player.dna_profile)
        if metadata.get("portraitStatus") == "banned":
            stats.skipped_banned += 1
            continue
        needs_repair = not _is_approved_bank_metadata(metadata)
        if not needs_repair:
            stats.player_regens_current += 1
            continue
        _append_sample(
            stats.repair_needed_samples,
            {
                "kind": "player_regen",
                "player_id": player.id,
                "regen_id": regen.id,
                "portrait_url": _first_string(metadata, "portraitUrl", "portrait_url", "image_url"),
                "portrait_status": metadata.get("portraitStatus"),
                "portrait_source_provider": metadata.get("portraitSourceProvider"),
                "portrait_source_collection": metadata.get("portraitSourceCollection"),
            },
            sample_size,
        )
        if not apply:
            continue
        try:
            result = service.ensure_player_portrait(player, regen=regen, force=True)
        except Exception as exc:  # pragma: no cover - sample path is asserted indirectly by exit code.
            _append_sample(
                stats.error_samples,
                {"kind": "player_regen", "player_id": player.id, "error": str(exc)},
                sample_size,
            )
            continue
        if result.portrait_url:
            stats.player_regens_repaired += 1
        else:
            stats.player_regens_missing_asset += 1
            _append_sample(
                stats.missing_asset_samples,
                {"kind": "player_regen", "player_id": player.id, "status": result.status},
                sample_size,
            )


def _audit_or_repair_national_seeds(
    session: Session,
    *,
    service: RegenPortraitService,
    stats: RegenPortraitLaneStats,
    apply: bool,
    limit: int | None,
    sample_size: int,
) -> None:
    statement = select(NationalRegenSeed).order_by(NationalRegenSeed.created_at.desc())
    if limit is not None:
        statement = statement.limit(limit)
    for seed in session.scalars(statement).all():
        stats.national_seeds_scanned += 1
        metadata = _metadata(seed.metadata_json)
        if metadata.get("portraitStatus") == "banned":
            stats.skipped_banned += 1
            continue
        needs_repair = not _is_approved_bank_metadata(metadata)
        if not needs_repair:
            stats.national_seeds_current += 1
            continue
        _append_sample(
            stats.repair_needed_samples,
            {
                "kind": "national_seed",
                "seed_id": seed.id,
                "seed_key": seed.seed_key,
                "portrait_url": _first_string(metadata, "portraitUrl", "portrait_url", "image_url"),
                "portrait_status": metadata.get("portraitStatus"),
                "portrait_source_provider": metadata.get("portraitSourceProvider"),
                "portrait_source_collection": metadata.get("portraitSourceCollection"),
            },
            sample_size,
        )
        if not apply:
            continue
        try:
            repaired = service.ensure_national_seed_portrait(seed, force=True)
        except Exception as exc:  # pragma: no cover - sample path is asserted indirectly by exit code.
            _append_sample(
                stats.error_samples,
                {"kind": "national_seed", "seed_id": seed.id, "error": str(exc)},
                sample_size,
            )
            continue
        if _is_approved_bank_metadata(repaired):
            stats.national_seeds_repaired += 1
        else:
            stats.national_seeds_missing_asset += 1
            _append_sample(
                stats.missing_asset_samples,
                {
                    "kind": "national_seed",
                    "seed_id": seed.id,
                    "status": repaired.get("portraitStatus"),
                },
                sample_size,
            )


def _is_approved_bank_metadata(metadata: dict[str, Any]) -> bool:
    portrait_url = _first_string(metadata, "portraitUrl", "portrait_url", "image_url")
    if not _is_approved_bank_url(portrait_url):
        return False
    return (
        metadata.get("portraitStatus") == "ready_newgen_face_bank"
        and metadata.get("portraitSourceProvider") == NEWGEN_FACE_BANK_PROVIDER
        and metadata.get("portraitSourceCollection") == NEWGEN_FACE_BANK_COLLECTION
    )


def _is_approved_bank_url(url: str | None) -> bool:
    if not url:
        return False
    lowered = url.replace("\\", "/").lower()
    if any(marker in lowered for marker in DISALLOWED_REGEN_PATH_MARKERS):
        return False
    return APPROVED_FACE_BANK_PATH in lowered and lowered.endswith(APPROVED_EXTENSIONS)


def _metadata(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _first_string(values: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _append_sample(samples: list[dict[str, object]], sample: dict[str, object], sample_size: int) -> None:
    if len(samples) < sample_size:
        samples.append(sample)


if __name__ == "__main__":
    raise SystemExit(main())
