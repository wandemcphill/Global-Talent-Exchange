from __future__ import annotations

import argparse
from collections.abc import Iterable, Sequence
import csv
from dataclasses import asdict, dataclass
import hashlib
from io import BytesIO
import os
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

import requests
from requests import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.core.database import create_database_engine, create_session_factory
from app.ingestion.models import Player, PlayerImageMetadata
from app.models.base import utcnow
from app.models.player_token_market import PlayerShareEvent, PlayerShareHolding, PlayerShareMarket
from app.models.regen import RegenVisualProfile

# Imported for SQLAlchemy relationship mapper resolution in this focused script.
_MAPPER_IMPORTS = (PlayerShareEvent, PlayerShareHolding, PlayerShareMarket, RegenVisualProfile)

SOURCE_PROVIDER = "gtex_player_image_import"
IMAGE_ROLE = "portrait"
IMAGE_SIZE = 512
DEFAULT_QUALITY = 82
DEFAULT_MAX_BYTES = 5 * 1024 * 1024
DEFAULT_BATCH_SIZE = 50
DEFAULT_CDN_BASE_URL = "https://cdn.gtex.com"


@dataclass(slots=True)
class ImportStats:
    apply: bool
    rows_seen: int = 0
    valid: int = 0
    success: int = 0
    skipped: int = 0
    failed: int = 0
    already_imported: int = 0


@dataclass(slots=True)
class PreparedImage:
    player_id: str
    cdn_url: str
    storage_key: str
    webp_bytes: bytes
    checksum_sha256: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import licensed player portraits from CSV image_url values.")
    parser.add_argument("--csv", type=Path, required=True, help="CSV with player_id, image_url, rights_cleared.")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("GTE_DATABASE_URL") or os.environ.get("DATABASE_URL"),
        help="Target database URL. Defaults to GTE_DATABASE_URL or DATABASE_URL.",
    )
    parser.add_argument("--apply", action="store_true", help="Write WEBP files and update player image metadata.")
    parser.add_argument("--force", action="store_true", help="Overwrite an existing approved portrait.")
    parser.add_argument("--limit", type=int, default=0, help="Limit rows processed for a smoke run.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Rows per commit batch when --apply is used. Defaults to 50.",
    )
    parser.add_argument(
        "--storage-root",
        type=Path,
        default=_default_storage_root(),
        help="Root folder for normalized media. Defaults to GTE_PLAYER_IMAGE_STORAGE_ROOT, "
        "GTE_GENERATED_MEDIA_ROOT, or backend/generated_media.",
    )
    parser.add_argument(
        "--cdn-base-url",
        default=(
            os.environ.get("GTE_PLAYER_IMAGE_CDN_BASE_URL")
            or os.environ.get("GTE_MEDIA_CDN_BASE_URL")
            or DEFAULT_CDN_BASE_URL
        ),
        help="Public CDN base URL. Defaults to https://cdn.gtex.com.",
    )
    parser.add_argument(
        "--resume-file",
        type=Path,
        default=BACKEND_DIR / "tmp" / "player_image_import_resume.txt",
        help="One player_id per successful import; used to resume interrupted runs.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--quality", type=int, default=DEFAULT_QUALITY)
    parser.add_argument(
        "--request-delay-seconds",
        type=float,
        default=0.0,
        help="Optional delay between image requests to avoid source rate limits.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.csv.exists():
        raise SystemExit(f"CSV not found: {args.csv}")
    if not args.database_url:
        raise SystemExit("--database-url, GTE_DATABASE_URL, or DATABASE_URL is required.")
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1.")
    if args.max_bytes < 1:
        raise SystemExit("--max-bytes must be at least 1.")
    if not 1 <= args.quality <= 100:
        raise SystemExit("--quality must be between 1 and 100.")

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    stats = ImportStats(apply=bool(args.apply))
    resume_ids = _load_resume_ids(args.resume_file)
    http_session = requests.Session()
    cdn_base_url = _normalize_base_url(args.cdn_base_url)
    rows = _iter_rows(args.csv, limit=args.limit)

    with session_factory() as db_session:
        batch: list[PreparedImage] = []
        for row_number, row in rows:
            stats.rows_seen += 1
            prepared = _prepare_row(
                db_session,
                http_session,
                row=row,
                row_number=row_number,
                args=args,
                cdn_base_url=cdn_base_url,
                resume_ids=resume_ids,
                stats=stats,
            )
            if prepared is not None:
                batch.append(prepared)
            if len(batch) >= args.batch_size:
                _commit_batch(db_session, batch, args=args, stats=stats, resume_ids=resume_ids)
                batch.clear()
            if args.request_delay_seconds > 0:
                time.sleep(args.request_delay_seconds)
        if batch:
            _commit_batch(db_session, batch, args=args, stats=stats, resume_ids=resume_ids)

    print(f"[IMG SUMMARY] {asdict(stats)}")
    if not args.apply:
        print("[IMG SUMMARY] dry-run only; rerun with --apply to write files and update DB")
    return 0 if stats.failed == 0 else 1


def _default_storage_root() -> Path:
    configured = os.environ.get("GTE_PLAYER_IMAGE_STORAGE_ROOT") or os.environ.get("GTE_GENERATED_MEDIA_ROOT")
    if configured:
        return Path(configured)
    return BACKEND_DIR / "generated_media"


def _iter_rows(path: Path, *, limit: int) -> Iterable[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=2):
            if limit and index - 1 > limit:
                break
            yield index, row


def _prepare_row(
    db_session: Session,
    http_session: requests.Session,
    *,
    row: dict[str, str],
    row_number: int,
    args: argparse.Namespace,
    cdn_base_url: str,
    resume_ids: set[str],
    stats: ImportStats,
) -> PreparedImage | None:
    player_id = (row.get("player_id") or "").strip()
    if not player_id:
        stats.skipped += 1
        print(f"[IMG SKIP] row={row_number} player_id missing")
        return None

    if not _is_true(row.get("rights_cleared")):
        stats.skipped += 1
        print(f"[IMG SKIP] player={player_id} rights not cleared")
        return None

    image_url = (row.get("image_url") or "").strip()
    if not image_url:
        stats.skipped += 1
        print(f"[IMG SKIP] player={player_id} image_url missing")
        return None

    if not _is_valid_http_url(image_url):
        stats.skipped += 1
        print(f"[IMG SKIP] player={player_id} invalid URL")
        return None

    if not args.force and player_id in resume_ids:
        stats.skipped += 1
        stats.already_imported += 1
        print(f"[IMG SKIP] player={player_id} already imported")
        return None

    player = db_session.get(Player, player_id)
    if player is None:
        stats.skipped += 1
        print(f"[IMG SKIP] player={player_id} player not found")
        return None

    if not args.force and _has_approved_portrait(db_session, player_id):
        stats.skipped += 1
        stats.already_imported += 1
        print(f"[IMG SKIP] player={player_id} already imported")
        return None

    try:
        raw_bytes = _download_image(
            http_session,
            image_url,
            timeout_seconds=args.timeout_seconds,
            max_bytes=args.max_bytes,
        )
        print(f"[IMG VALID] player={player_id} OK")
        webp_bytes = _normalize_image(raw_bytes, quality=args.quality)
    except ImageValidationError as exc:
        stats.skipped += 1
        print(f"[IMG SKIP] player={player_id} invalid URL")
        return None
    except ImageImportError as exc:
        stats.failed += 1
        print(f"[IMG FAIL] player={player_id} reason={exc}")
        return None

    storage_key = f"players/{player_id}.webp"
    cdn_url = f"{cdn_base_url}/{storage_key}"
    stats.valid += 1
    return PreparedImage(
        player_id=player_id,
        cdn_url=cdn_url,
        storage_key=storage_key,
        webp_bytes=webp_bytes,
        checksum_sha256=hashlib.sha256(webp_bytes).hexdigest(),
    )


def _commit_batch(
    db_session: Session,
    batch: list[PreparedImage],
    *,
    args: argparse.Namespace,
    stats: ImportStats,
    resume_ids: set[str],
) -> None:
    if not batch:
        return
    if not args.apply:
        return

    written_paths: list[Path] = []
    try:
        for image in batch:
            output_path = args.storage_root / image.storage_key
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(image.webp_bytes)
            written_paths.append(output_path)
            _upsert_image_metadata(db_session, image)
        db_session.commit()
    except Exception as exc:
        db_session.rollback()
        for path in written_paths:
            path.unlink(missing_ok=True)
        for image in batch:
            stats.failed += 1
            print(f"[IMG FAIL] player={image.player_id} reason={exc}")
        return

    for image in batch:
        stats.success += 1
        resume_ids.add(image.player_id)
        _append_resume_id(args.resume_file, image.player_id)
        print(f"[IMG SUCCESS] player={image.player_id}")


def _upsert_image_metadata(db_session: Session, image: PreparedImage) -> None:
    record = db_session.scalar(
        select(PlayerImageMetadata).where(
            PlayerImageMetadata.player_id == image.player_id,
            PlayerImageMetadata.image_role == IMAGE_ROLE,
        )
    )
    if record is None:
        record = PlayerImageMetadata(
            source_provider=SOURCE_PROVIDER,
            provider_external_id=f"{SOURCE_PROVIDER}:{image.player_id}:portrait",
            player_id=image.player_id,
            image_role=IMAGE_ROLE,
        )
        db_session.add(record)

    record.source_provider = SOURCE_PROVIDER
    record.provider_external_id = f"{SOURCE_PROVIDER}:{image.player_id}:portrait"
    record.source_url = image.cdn_url
    record.storage_key = image.storage_key
    record.width = IMAGE_SIZE
    record.height = IMAGE_SIZE
    record.mime_type = "image/webp"
    record.file_size_bytes = len(image.webp_bytes)
    record.checksum_sha256 = image.checksum_sha256
    record.moderation_status = "approved"
    record.rights_cleared = True
    record.is_primary = True
    record.last_processed_at = utcnow()


def _download_image(
    session: requests.Session,
    url: str,
    *,
    timeout_seconds: float,
    max_bytes: int,
) -> bytes:
    try:
        response = session.get(url, stream=True, timeout=timeout_seconds)
    except requests.Timeout as exc:
        raise ImageImportError("timeout") from exc
    except requests.RequestException as exc:
        raise ImageImportError(type(exc).__name__) from exc

    with response:
        _validate_response(response, max_bytes=max_bytes)
        raw = bytearray()
        try:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                raw.extend(chunk)
                if len(raw) >= max_bytes:
                    raise ImageValidationError("image too large")
        except requests.RequestException as exc:
            raise ImageImportError(type(exc).__name__) from exc
    return bytes(raw)


def _validate_response(response: Response, *, max_bytes: int) -> None:
    if response.status_code != 200:
        raise ImageValidationError(f"http {response.status_code}")
    content_type = (response.headers.get("Content-Type") or "").split(";", maxsplit=1)[0].strip().lower()
    if not content_type.startswith("image/"):
        raise ImageValidationError("not an image")
    content_length = (response.headers.get("Content-Length") or "").strip()
    if content_length:
        try:
            size = int(content_length)
        except ValueError:
            size = 0
        if size >= max_bytes:
            raise ImageValidationError("image too large")


def _normalize_image(raw_bytes: bytes, *, quality: int) -> bytes:
    try:
        from PIL import Image, ImageOps, UnidentifiedImageError
    except ImportError as exc:
        raise ImageImportError("Pillow not installed") from exc

    try:
        with Image.open(BytesIO(raw_bytes)) as source:
            image = ImageOps.exif_transpose(source)
            image = image.convert("RGB")
            cropped = ImageOps.fit(
                image,
                (IMAGE_SIZE, IMAGE_SIZE),
                method=Image.Resampling.LANCZOS,
                centering=(0.5, 0.5),
            )
            output = BytesIO()
            cropped.save(output, format="WEBP", quality=quality, method=6)
            return output.getvalue()
    except UnidentifiedImageError as exc:
        raise ImageImportError("invalid image") from exc
    except OSError as exc:
        raise ImageImportError("processing error") from exc


def _has_approved_portrait(db_session: Session, player_id: str) -> bool:
    image = db_session.scalar(
        select(PlayerImageMetadata).where(
            PlayerImageMetadata.player_id == player_id,
            PlayerImageMetadata.image_role == IMAGE_ROLE,
            PlayerImageMetadata.moderation_status == "approved",
            PlayerImageMetadata.rights_cleared.is_(True),
        )
    )
    return image is not None and bool((image.source_url or image.storage_key or "").strip())


def _load_resume_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _append_resume_id(path: Path, player_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"{player_id}\n")


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y"}


def _is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _normalize_base_url(value: str) -> str:
    return (value or DEFAULT_CDN_BASE_URL).strip().rstrip("/")


class ImageImportError(Exception):
    """A transient or processing failure that should not update the DB."""


class ImageValidationError(ImageImportError):
    """A row-level URL validation failure."""


if __name__ == "__main__":
    raise SystemExit(main())
