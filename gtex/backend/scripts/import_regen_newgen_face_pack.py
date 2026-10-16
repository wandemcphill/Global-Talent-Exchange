from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE = REPO_ROOT / "backend" / "media_dropzones" / "regen_newgen_pack"
DEFAULT_OUTPUT = REPO_ROOT / "backend" / "generated_media" / "regen_newgen_faces"
SCRIPT_PACK_ROOT = "Faces ethnic script"
SCRIPT_SOURCE_PACK = "Free to use Regen Faces - SCRIPT SKIN TONE + HAIR COLOUR"
DISABLED_LAYOUTS = {"fm_ai", "fm_ai_flat", "fm_ai_examples"}


def _reject_disabled_layout(layout: str) -> None:
    if layout in DISABLED_LAYOUTS:
        raise SystemExit(
            "FM-AI/procedural regen fallback imports are disabled. "
            "GTEX regens must use the approved 8k+ scripted skin/hair portrait "
            "bank only."
        )


def _detect_layout(source: Path, requested: str) -> str:
    _reject_disabled_layout(requested)
    if requested != "auto":
        return requested
    if (source / SCRIPT_PACK_ROOT).exists():
        return "script_skin_hair"
    raise SystemExit(
        "Could not detect a supported regen/newgen face source. "
        f"Expected '{SCRIPT_PACK_ROOT}/' for the approved scripted skin/hair "
        "portrait bank."
    )


def _asset_files(source: Path, layout: str) -> tuple[Path, list[Path]]:
    if layout == "script_skin_hair":
        root = source / SCRIPT_PACK_ROOT
        if not root.exists():
            raise SystemExit(
                f"Expected '{SCRIPT_PACK_ROOT}' under {source}. "
                "Unzip the skin/hair regen pack into the dropzone first."
            )
        return root, sorted(
            path
            for path in root.rglob("*.png")
            if "IN GAME Faces Regens" not in path.parts
        )
    _reject_disabled_layout(layout)
    raise SystemExit(f"Unsupported layout: {layout}")


def _source_pack(layout: str) -> str:
    _reject_disabled_layout(layout)
    return SCRIPT_SOURCE_PACK


def _collection(layout: str) -> str:
    _reject_disabled_layout(layout)
    return "script_skin_tone_hair_colour"


def _relative_output_path(layout: str, relative: Path) -> Path:
    _reject_disabled_layout(layout)
    return Path("script_skin_hair") / relative


def _labels(layout: str, relative: Path) -> tuple[str, str]:
    parts = relative.parts
    if layout == "script_skin_hair":
        if len(parts) < 3:
            raise SystemExit(f"Unexpected scripted face path: {relative}")
        return parts[0], " / ".join(parts[1:-1])
    _reject_disabled_layout(layout)
    raise SystemExit(f"Unsupported scripted face layout: {layout}")


def _ensure_assets_present(assets: list[Path], source: Path) -> None:
    if not assets:
        raise SystemExit(
            f"No PNG portraits found under {source}. "
            "Generate or unzip regen/newgen portraits before importing."
        )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_record(
    root: Path,
    output: Path,
    asset: Path,
    *,
    layout: str,
    copy: bool,
) -> dict[str, object]:
    relative = asset.relative_to(root)
    ethnicity, hair_colour = _labels(layout, relative)
    output_relative = _relative_output_path(layout, relative)
    output_path = output / output_relative
    storage_key = f"regen_newgen_faces/{output_relative.as_posix()}"
    if copy:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, output_path)
    return {
        "collection": _collection(layout),
        "source_pack": _source_pack(layout),
        "ethnicity": ethnicity,
        "hair_colour": hair_colour,
        "source_path": relative.as_posix(),
        "storage_key": storage_key,
        "bytes": asset.stat().st_size,
        "sha256": _sha256(asset),
    }


def _summarize(records: list[dict[str, object]]) -> dict[str, int]:
    summary: dict[str, int] = {}
    for record in records:
        key = f"{record['ethnicity']} / {record['hair_colour']}"
        summary[key] = summary.get(key, 0) + 1
    return dict(sorted(summary.items()))


def _existing_assets(manifest_path: Path, replacing_collection: str) -> list[dict[str, object]]:
    if not manifest_path.exists():
        return []
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    assets = manifest.get("assets")
    if not isinstance(assets, list):
        return []
    return [
        asset
        for asset in assets
        if isinstance(asset, dict)
        and str(asset.get("collection") or "") != replacing_collection
    ]


def _source_packs(records: list[dict[str, object]], current_source_pack: str) -> list[str]:
    packs = {current_source_pack}
    for record in records:
        value = record.get("source_pack")
        if isinstance(value, str) and value.strip():
            packs.add(value.strip())
    return sorted(packs)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import GTEX regen/newgen PNG face pack assets."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--layout",
        choices=("auto", "script_skin_hair"),
        default="auto",
        help=(
            "Source layout. Only script_skin_hair is supported for production "
            "regen/newgen portraits."
        ),
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Copy PNG assets into backend/generated_media/regen_newgen_faces.",
    )
    args = parser.parse_args()

    source = args.source.resolve()
    output = args.output.resolve()
    layout = _detect_layout(source, args.layout)
    root, assets = _asset_files(source, layout)
    _ensure_assets_present(assets, root)
    current_collection = _collection(layout)
    imported_records = [
        _manifest_record(root, output, asset, layout=layout, copy=args.copy)
        for asset in assets
    ]
    manifest_path = output / "manifest.json"
    records = _existing_assets(manifest_path, current_collection) + imported_records
    current_source_pack = _source_pack(layout)
    manifest = {
        "version": 1,
        "usage": "regen_newgen_only",
        "source_pack": current_source_pack,
        "source_packs": _source_packs(records, current_source_pack),
        "source_layout": layout,
        "real_player_policy": "do_not_use_for_real_players",
        "fallback_policy": "no_fallbacks_use_ethnicity_matched_script_skin_hair_only",
        "asset_count": len(records),
        "groups": _summarize(records),
        "assets": records,
    }
    output.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    mode = "copied" if args.copy else "scanned"
    print(f"{mode} {len(imported_records)} regen/newgen PNG portraits")
    print(f"manifest total: {len(records)} portraits")
    print(f"manifest: {manifest_path}")


if __name__ == "__main__":
    main()
