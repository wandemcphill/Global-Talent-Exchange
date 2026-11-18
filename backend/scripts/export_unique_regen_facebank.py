"""Copy the unique regen cutouts into a local bank.

Reads the existing manifest and downloads public image URLs. Cloudinary is
not modified: no upload, rename, or delete.

Folders that the audit proved are byte-copies of another ethnicity are left
out. Middle east files nested a second time under Dark Brown/ are left out.
Hair folders on the remaining files stay as they are in the pack.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "backend" / "generated_media" / "regen_newgen_faces" / "manifest.json"
OUT = ROOT / "regen_facebank_v2" / "unique_cutouts"
COPIED_ETHNICITIES = {"Mixed", "South european", "Hispanic"}
WORKERS = 12
TIMEOUT = 60


def canonical(asset: dict) -> bool:
    key = str(asset.get("storage_key") or "")
    parts = key.split("/")
    # regen_newgen_faces / script_skin_hair / ethnicity / hair / file
    if len(parts) != 5 or parts[0] != "regen_newgen_faces" or parts[1] != "script_skin_hair":
        return False
    if parts[2] in COPIED_ETHNICITIES:
        return False
    url = asset.get("cloudinary_secure_url")
    return isinstance(url, str) and url.startswith("https://res.cloudinary.com/")


def destination(asset: dict) -> Path:
    parts = str(asset["storage_key"]).split("/")
    return OUT / Path(*parts[1:])


def download(asset: dict) -> str:
    path = destination(asset)
    expected = int(asset.get("bytes") or 0)
    if path.exists() and (expected == 0 or path.stat().st_size == expected):
        return "skip"
    path.parent.mkdir(parents=True, exist_ok=True)
    request = Request(asset["cloudinary_secure_url"], headers={"User-Agent": "gtex-readonly-facebank"})
    with urlopen(request, timeout=TIMEOUT) as response:
        payload = response.read()
    if expected and len(payload) != expected:
        raise OSError(f"size {len(payload)} != {expected} for {asset['storage_key']}")
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(path)
    return "ok"


def main() -> None:
    assets = [asset for asset in json.loads(MANIFEST.read_text(encoding="utf-8"))["assets"] if canonical(asset)]
    counts: dict[str, int] = {}
    for asset in assets:
        ethnicity = asset["storage_key"].split("/")[2]
        counts[ethnicity] = counts.get(ethnicity, 0) + 1
    print(f"Unique cutouts to copy: {len(assets)}")
    for ethnicity in sorted(counts):
        print(f"  {counts[ethnicity]:5}  {ethnicity}")

    saved = skipped = 0
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(download, asset): asset for asset in assets}
        done = 0
        for future in as_completed(futures):
            asset = futures[future]
            done += 1
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001 - report and continue
                failures.append(f"{asset['storage_key']}: {exc}")
            else:
                if result == "skip":
                    skipped += 1
                else:
                    saved += 1
            if done % 250 == 0 or done == len(assets):
                print(f"{done}/{len(assets)}  saved {saved}  skipped {skipped}  failed {len(failures)}", flush=True)

    # One retry for transient download errors.
    if failures:
        retry_keys = {line.split(":", 1)[0] for line in failures}
        failures = []
        retry_assets = [asset for asset in assets if asset["storage_key"] in retry_keys]
        print(f"Retrying {len(retry_assets)}")
        for asset in retry_assets:
            try:
                if download(asset) == "ok":
                    saved += 1
            except Exception as exc:  # noqa: BLE001
                failures.append(f"{asset['storage_key']}: {exc}")

    records = []
    for asset in assets:
        path = destination(asset)
        if not path.exists():
            continue
        relative = path.relative_to(OUT).as_posix()
        records.append(
            {
                "collection": asset.get("collection"),
                "source_pack": asset.get("source_pack"),
                "ethnicity": asset.get("ethnicity"),
                "hair_colour": asset.get("hair_colour"),
                "storage_key": asset.get("storage_key"),
                "source_url": asset.get("cloudinary_secure_url"),
                "local_path": relative,
                "bytes": path.stat().st_size,
                "width": asset.get("width"),
                "height": asset.get("height"),
            }
        )
    records.sort(key=lambda item: str(item["local_path"]))
    manifest = {
        "generated_from": "cloudinary_public_urls_readonly",
        "cloudinary_modified": False,
        "usage": "unique regen cutouts only; copied ethnicity folders omitted",
        "omitted_copied_ethnicities": sorted(COPIED_ETHNICITIES),
        "asset_count": len(records),
        "failed": failures,
        "assets": records,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    print(f"Local files: {len(records)}")
    print(f"Failed: {len(failures)}")
    for line in failures[:20]:
        print(f"  {line}")
    print(manifest_path)


if __name__ == "__main__":
    main()
