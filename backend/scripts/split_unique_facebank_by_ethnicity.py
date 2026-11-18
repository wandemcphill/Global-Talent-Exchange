"""Give every regen ethnicity its own faces without duplicating files.

North european is divided across North european, South european, and Hispanic.
African is divided across African and Mixed. Files are moved, not copied.
Pixels are not edited. Cloudinary is not contacted.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "regen_facebank_v2" / "unique_cutouts"
MANIFEST = OUT / "manifest.json"

SPLITS = {
    "North european": ("North european", "South european", "Hispanic"),
    "African": ("African", "Mixed"),
}


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = manifest["assets"]
    by_folder: dict[tuple[str, str], list[dict]] = {}
    for asset in assets:
        by_folder.setdefault((asset["ethnicity"], asset["hair_colour"]), []).append(asset)

    moved = 0
    for (ethnicity, hair), group in by_folder.items():
        targets = SPLITS.get(ethnicity)
        if not targets:
            continue
        group.sort(key=lambda asset: asset["local_path"])
        for index, asset in enumerate(group):
            target = targets[index % len(targets)]
            if target == ethnicity:
                continue
            source = OUT / asset["local_path"]
            name = Path(asset["local_path"]).name
            relative = f"script_skin_hair/{target}/{hair}/{name}"
            destination = OUT / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise SystemExit(f"Refusing to overwrite {destination}")
            source.rename(destination)
            asset["ethnicity"] = target
            asset["local_path"] = relative
            asset["storage_key"] = f"regen_newgen_faces/{relative}"
            moved += 1

    counts: dict[str, int] = {}
    for asset in assets:
        counts[asset["ethnicity"]] = counts.get(asset["ethnicity"], 0) + 1
    manifest["asset_count"] = len(assets)
    manifest["usage"] = "unique regen cutouts divided across ethnicities; " "each file lives in one pool only"
    manifest["ethnicity_counts"] = dict(sorted(counts.items()))
    manifest["assets"] = sorted(assets, key=lambda asset: asset["local_path"])
    MANIFEST.write_text(json.dumps(manifest), encoding="utf-8")
    print(f"Moved {moved} files")
    for ethnicity, count in sorted(counts.items()):
        print(f"  {count:5}  {ethnicity}")


if __name__ == "__main__":
    main()
