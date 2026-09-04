"""Audit the regen newgen face bank against what is actually in Cloudinary.

Production seeds every national regen with ``portraitStatus:
portrait_asset_missing`` because ``RegenPortraitService._face_bank_assets()``
reads a local ``generated_media/regen_newgen_faces/manifest.json`` and that file
does not exist on the API host.  The portrait art may still live in Cloudinary,
but nothing in GTEX reads Cloudinary for it, so this script answers the two
questions needed before wiring the two together:

1. What regen face assets exist in Cloudinary, and how are their public_ids
   shaped relative to the ``regen_newgen_faces/script_skin_hair/<ethnicity>/
   <hair colour>/<file>`` storage keys the importer produces?
2. Would those assets actually satisfy portrait selection?  Selection filters on
   a normalized ``ethnicity`` label, so a bank missing a group means every regen
   resolving to that group stays portrait-less no matter how many files exist.

Read-only against Cloudinary.  Nothing is uploaded, renamed or deleted.

Credentials come from the same variables the app's Cloudinary helper uses:

    CLOUDINARY_CLOUD_NAME
    CLOUDINARY_API_KEY
    CLOUDINARY_API_SECRET

Run from the repo root:

    python backend/scripts/audit_regen_face_bank_cloudinary.py \
        --prefix gtex/regen_newgen_faces \
        --report cloudinary_face_bank_report.json

Add --emit-manifest PATH to write a manifest.json built from the Cloudinary
listing, which is what the portrait service needs in order to assign faces.
"""

from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path
import sys
from typing import Any, Iterator
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
for candidate in (str(ROOT_DIR), str(BACKEND_DIR)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import httpx

# `app.models` is the aggregate registry and must be imported before any
# individual model module, otherwise importing the portrait service re-enters it
# mid-initialization and raises a circular ImportError.
import app.models  # noqa: F401
from app.services.regen_portrait_service import (  # noqa: E402
    NEWGEN_FACE_BANK_COLLECTION,
    NEWGEN_FACE_BANK_PROVIDER,
    RegenPortraitService,
)

FACE_BANK_ROOT = "regen_newgen_faces"
SCRIPT_LAYOUT_DIR = "script_skin_hair"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
ADMIN_API = "https://api.cloudinary.com/v1_1/{cloud}/resources/image"
PAGE_SIZE = 500
REQUEST_TIMEOUT_SECONDS = 60.0


class AuditError(RuntimeError):
    """Raised when the audit cannot be completed."""


def _credentials_from_url() -> tuple[str, str, str] | None:
    """Parse the combined ``cloudinary://key:secret@cloud`` form, if set.

    The app's own helper reads the three split variables, but CLOUDINARY_URL is
    Cloudinary's canonical env var and is what the deployed workers are given,
    so accept either rather than forcing the caller to split it by hand.
    """
    raw = os.environ.get("CLOUDINARY_URL", "").strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "cloudinary":
        return None
    cloud = (parsed.hostname or "").strip()
    key = (parsed.username or "").strip()
    secret = (parsed.password or "").strip()
    if not (cloud and key and secret):
        return None
    return cloud, key, secret


def _credentials() -> tuple[str, str, str]:
    from_url = _credentials_from_url()
    if from_url is not None:
        return from_url
    cloud = os.environ.get("CLOUDINARY_CLOUD_NAME", "").strip()
    key = os.environ.get("CLOUDINARY_API_KEY", "").strip()
    secret = os.environ.get("CLOUDINARY_API_SECRET", "").strip()
    missing = [
        name
        for name, value in (
            ("CLOUDINARY_CLOUD_NAME", cloud),
            ("CLOUDINARY_API_KEY", key),
            ("CLOUDINARY_API_SECRET", secret),
        )
        if not value
    ]
    if missing:
        raise AuditError(
            "Missing Cloudinary credentials: "
            f"{', '.join(missing)} (or set CLOUDINARY_URL)"
        )
    return cloud, key, secret


def iter_cloudinary_images(
    *, prefix: str, delivery_type: str, max_assets: int | None
) -> Iterator[dict[str, Any]]:
    """Yield image resources from the Cloudinary Admin API, following cursors."""
    cloud, key, secret = _credentials()
    url = ADMIN_API.format(cloud=cloud)
    cursor: str | None = None
    seen = 0

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, auth=(key, secret)) as client:
        while True:
            params: dict[str, Any] = {"max_results": PAGE_SIZE, "type": delivery_type}
            if prefix:
                params["prefix"] = prefix
            if cursor:
                params["next_cursor"] = cursor

            response = client.get(url, params=params)
            if response.status_code == 401:
                raise AuditError("Cloudinary rejected the credentials (401).")
            if response.status_code == 404:
                raise AuditError(
                    f"Cloudinary returned 404 for cloud '{cloud}' -- check CLOUDINARY_CLOUD_NAME."
                )
            response.raise_for_status()
            payload = response.json()

            for resource in payload.get("resources") or []:
                if isinstance(resource, dict):
                    yield resource
                    seen += 1
                    if max_assets is not None and seen >= max_assets:
                        return

            cursor = payload.get("next_cursor")
            if not cursor:
                return


def storage_key_for(public_id: str, fmt: str | None) -> str | None:
    """Map a Cloudinary public_id onto the importer's storage_key shape.

    Cloudinary strips the file extension from public_id, so the extension is
    restored from the resource's `format` to line the key up with the manifest.
    """
    normalized = public_id.replace("\\", "/").strip("/")
    marker = f"{FACE_BANK_ROOT}/"
    if marker in normalized:
        key = normalized[normalized.index(marker) :]
    else:
        return None
    if not key.lower().endswith(IMAGE_EXTENSIONS) and fmt:
        key = f"{key}.{fmt.lstrip('.')}"
    return key


def labels_from_storage_key(storage_key: str) -> tuple[str, str] | None:
    """Recover (ethnicity, hair_colour) from a face-bank storage key.

    Mirrors `_labels`/`_relative_output_path` in import_regen_newgen_face_pack:
    regen_newgen_faces/script_skin_hair/<ethnicity>/<hair...>/<file>
    """
    parts = storage_key.split("/")
    if len(parts) < 5 or parts[0] != FACE_BANK_ROOT or parts[1] != SCRIPT_LAYOUT_DIR:
        return None
    ethnicity = parts[2]
    hair_colour = " / ".join(parts[3:-1])
    return ethnicity, hair_colour


def load_manifest_assets(manifest_path: Path) -> list[dict[str, Any]]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    assets = manifest.get("assets")
    return [asset for asset in assets if isinstance(asset, dict)] if isinstance(assets, list) else []


def _strip_extension(key: str) -> str:
    lowered = key.lower()
    for extension in IMAGE_EXTENSIONS:
        if lowered.endswith(extension):
            return key[: -len(extension)]
    return key


def required_ethnicity_groups() -> set[str]:
    """Every normalized ethnicity group portrait selection can ask for.

    Uses the service's own country->group mapping so the audit reflects real
    selection behaviour rather than a second copy of the rules.
    """
    groups: set[str] = set()
    # The mapping is keyed by country code; probe it with the codes the seeder
    # can produce plus the "Mixed" default the recipe falls back to.
    for code in sorted(_candidate_country_codes()):
        for group in RegenPortraitService._portrait_ethnicity_groups(code):
            groups.add(RegenPortraitService._normalize_ethnicity_label(group))
    groups.add(RegenPortraitService._normalize_ethnicity_label("Mixed"))
    return {group for group in groups if group}


def _candidate_country_codes() -> set[str]:
    codes: set[str] = {""}
    for first in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        for second in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            codes.add(f"{first}{second}")
    return codes


def build_report(
    *, resources: list[dict[str, Any]], manifest_assets: list[dict[str, Any]]
) -> dict[str, Any]:
    cloud_by_key: dict[str, dict[str, Any]] = {}
    unmatched_public_ids: list[str] = []
    ethnicity_counts: collections.Counter[str] = collections.Counter()
    hair_counts: collections.Counter[str] = collections.Counter()

    for resource in resources:
        public_id = str(resource.get("public_id") or "")
        key = storage_key_for(public_id, resource.get("format"))
        if key is None:
            unmatched_public_ids.append(public_id)
            continue
        cloud_by_key[_strip_extension(key)] = {
            "storage_key": key,
            "public_id": public_id,
            "secure_url": resource.get("secure_url"),
            "bytes": resource.get("bytes"),
            "width": resource.get("width"),
            "height": resource.get("height"),
            "format": resource.get("format"),
        }
        labels = labels_from_storage_key(key)
        if labels is not None:
            ethnicity_counts[labels[0]] += 1
            hair_counts[labels[1]] += 1

    manifest_by_key = {
        _strip_extension(str(asset.get("storage_key") or "")): asset
        for asset in manifest_assets
        if asset.get("storage_key")
    }

    matched = sorted(set(cloud_by_key) & set(manifest_by_key))
    manifest_only = sorted(set(manifest_by_key) - set(cloud_by_key))
    cloudinary_only = sorted(set(cloud_by_key) - set(manifest_by_key))

    required = required_ethnicity_groups()
    present = {
        RegenPortraitService._normalize_ethnicity_label(label) for label in ethnicity_counts
    }
    return {
        "cloudinary_image_count": len(resources),
        "face_bank_shaped": len(cloud_by_key),
        "not_face_bank_shaped": len(unmatched_public_ids),
        "not_face_bank_shaped_samples": unmatched_public_ids[:15],
        "manifest_asset_count": len(manifest_assets),
        "matched": len(matched),
        "manifest_only_missing_in_cloudinary": len(manifest_only),
        "manifest_only_samples": manifest_only[:15],
        "cloudinary_only_not_in_manifest": len(cloudinary_only),
        "cloudinary_only_samples": cloudinary_only[:15],
        "ethnicity_breakdown": dict(ethnicity_counts.most_common()),
        "hair_colour_breakdown": dict(hair_counts.most_common(25)),
        "required_ethnicity_groups": sorted(required),
        "ethnicity_groups_present": sorted(present),
        "ethnicity_groups_missing": sorted(required - present),
        "_cloud_assets": cloud_by_key,
    }


def emit_manifest(report: dict[str, Any], destination: Path) -> int:
    """Write a face-bank manifest built from the Cloudinary listing."""
    assets: list[dict[str, Any]] = []
    for entry in report["_cloud_assets"].values():
        labels = labels_from_storage_key(entry["storage_key"])
        if labels is None:
            continue
        ethnicity, hair_colour = labels
        assets.append(
            {
                "collection": NEWGEN_FACE_BANK_COLLECTION,
                "source_pack": "Free to use Regen Faces - SCRIPT SKIN TONE + HAIR COLOUR",
                "ethnicity": ethnicity,
                "hair_colour": hair_colour,
                "source_path": entry["storage_key"],
                "storage_key": entry["storage_key"],
                "bytes": entry.get("bytes") or 0,
                "width": entry.get("width"),
                "height": entry.get("height"),
                "sha256": "",
                "cloudinary_public_id": entry["public_id"],
                "cloudinary_secure_url": entry.get("secure_url"),
            }
        )
    assets.sort(key=lambda item: str(item["storage_key"]))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            {
                "provider": NEWGEN_FACE_BANK_PROVIDER,
                "collections": [NEWGEN_FACE_BANK_COLLECTION],
                "generated_from": "cloudinary_admin_api",
                "assets": assets,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return len(assets)


def _print_report(report: dict[str, Any]) -> None:
    print(f"Cloudinary images scanned      : {report['cloudinary_image_count']}")
    print(f"  face-bank shaped keys        : {report['face_bank_shaped']}")
    print(f"  not face-bank shaped         : {report['not_face_bank_shaped']}")
    for sample in report["not_face_bank_shaped_samples"]:
        print(f"      e.g. {sample}")
    print(f"Local manifest assets          : {report['manifest_asset_count']}")
    print(f"  matched in Cloudinary        : {report['matched']}")
    print(f"  in manifest, not Cloudinary  : {report['manifest_only_missing_in_cloudinary']}")
    for sample in report["manifest_only_samples"]:
        print(f"      missing: {sample}")
    print(f"  in Cloudinary, not manifest  : {report['cloudinary_only_not_in_manifest']}")
    for sample in report["cloudinary_only_samples"]:
        print(f"      extra:   {sample}")

    print("\nEthnicity coverage (drives portrait selection):")
    if report["ethnicity_breakdown"]:
        for label, count in report["ethnicity_breakdown"].items():
            print(f"  {count:6}  {label}")
    else:
        print("  (none -- no face-bank shaped assets found)")

    missing = report["ethnicity_groups_missing"]
    if missing:
        print("\nMissing ethnicity groups -- regens resolving to these get NO portrait:")
        for label in missing:
            print(f"  - {label}")
    else:
        print("\nAll required ethnicity groups are represented.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix",
        default="",
        help="Cloudinary public_id prefix to scan (e.g. 'gtex/regen_newgen_faces'). Default: all images.",
    )
    parser.add_argument(
        "--delivery-type",
        default="upload",
        help="Cloudinary delivery type to list (default: upload).",
    )
    parser.add_argument(
        "--manifest",
        default=None,
        help="Face bank manifest to compare against. Defaults to the path the portrait service resolves.",
    )
    parser.add_argument("--report", default=None, help="Write the full JSON report to this path.")
    parser.add_argument(
        "--emit-manifest",
        default=None,
        help="Write a manifest.json built from the Cloudinary listing to this path.",
    )
    parser.add_argument(
        "--max-assets",
        type=int,
        default=None,
        help="Stop after listing this many Cloudinary images (safety cap).",
    )
    args = parser.parse_args(argv)

    if args.manifest:
        manifest_path = Path(args.manifest)
    else:
        manifest_path = RegenPortraitService._media_root() / "regen_newgen_faces" / "manifest.json"

    manifest_assets = load_manifest_assets(manifest_path)
    if not manifest_assets:
        print(f"NOTE: no usable manifest at {manifest_path} -- comparing against an empty bank.\n")

    try:
        resources = list(
            iter_cloudinary_images(
                prefix=args.prefix,
                delivery_type=args.delivery_type,
                max_assets=args.max_assets,
            )
        )
    except AuditError as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2

    report = build_report(resources=resources, manifest_assets=manifest_assets)
    _print_report(report)

    if args.emit_manifest:
        written = emit_manifest(report, Path(args.emit_manifest))
        print(f"\nWrote {written} assets to {args.emit_manifest}")

    if args.report:
        serializable = {k: v for k, v in report.items() if not k.startswith("_")}
        Path(args.report).write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        print(f"Wrote JSON report to {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
