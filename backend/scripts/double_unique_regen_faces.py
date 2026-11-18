"""Add one new regen face beside each unique cutout.

Each new face is an eye-aligned mix of two cutouts in the same ethnicity and
hair folder. The original file is not changed. Cloudinary is not contacted.
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(r"C:\Users\ayomc\Desktop\GLOBAL TALENT EXCHANGE\regen_facebank_v2\unique_cutouts")
BANK = ROOT / "script_skin_hair"
MANIFEST = ROOT / "manifest.json"
FACE = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
EYES = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")


def load_rgba(path: Path) -> np.ndarray:
    image = Image.open(path).convert("RGBA")
    array = np.array(image)
    image.close()
    return array


def face_box(alpha: np.ndarray) -> tuple[int, int, int, int]:
    ys, xs = np.where(alpha > 40)
    if len(xs) == 0:
        return 40, 20, 210, 248
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def eye_pair(image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_RGB2GRAY)
    x0, y0, x1, y1 = face_box(image[:, :, 3])
    face_w = max(1, x1 - x0)
    face_h = max(1, y1 - y0)
    hits = FACE.detectMultiScale(gray, 1.08, 4, minSize=(80, 80))
    boxes: list[tuple[int, int, int, int]] = []
    if len(hits):
        x, y, w, h = max(hits, key=lambda item: int(item[2] * item[3]))
        roi = gray[y : y + int(h * 0.60), x : x + w]
        found = EYES.detectMultiScale(roi, 1.05, 3, minSize=(16, 16))
        boxes = [(int(x + ex), int(y + ey), int(ew), int(eh)) for ex, ey, ew, eh in found]
    limit = y0 + 0.56 * face_h
    boxes = [box for box in boxes if box[1] + box[3] / 2 < limit]
    center_x = (x0 + x1) / 2.0
    left = [box for box in boxes if box[0] + box[2] / 2 < center_x]
    right = [box for box in boxes if box[0] + box[2] / 2 >= center_x]

    def center(box: tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = box
        return np.array([x + w / 2.0, y + h / 2.0], dtype=np.float32)

    if left and right:
        return (
            center(max(left, key=lambda box: box[2] * box[3])),
            center(max(right, key=lambda box: box[2] * box[3])),
        )
    eye_y = y0 + 0.42 * face_h
    return (
        np.array([x0 + 0.34 * face_w, eye_y], dtype=np.float32),
        np.array([x0 + 0.66 * face_w, eye_y], dtype=np.float32),
    )


def align(
    donor: np.ndarray, host_eyes: tuple[np.ndarray, np.ndarray], donor_eyes: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
    host_left, host_right = host_eyes
    donor_left, donor_right = donor_eyes
    host_gap = max(8.0, float(np.linalg.norm(host_right - host_left)))
    donor_gap = max(8.0, float(np.linalg.norm(donor_right - donor_left)))
    scale = float(np.clip(host_gap / donor_gap, 0.92, 1.08))
    host_mid = (host_left + host_right) / 2.0
    donor_mid = (donor_left + donor_right) / 2.0
    height, width = donor.shape[:2]
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    src_x = donor_mid[0] + (xx - host_mid[0]) / scale
    src_y = donor_mid[1] + (yy - host_mid[1]) / scale
    x0 = np.floor(src_x).astype(np.int32)
    y0 = np.floor(src_y).astype(np.int32)
    wx = (src_x - x0)[:, :, None]
    wy = (src_y - y0)[:, :, None]
    x0c = np.clip(x0, 0, width - 1)
    y0c = np.clip(y0, 0, height - 1)
    x1c = np.clip(x0 + 1, 0, width - 1)
    y1c = np.clip(y0 + 1, 0, height - 1)
    donor_f = donor.astype(np.float32)
    mixed = (
        donor_f[y0c, x0c] * (1 - wx) * (1 - wy)
        + donor_f[y0c, x1c] * wx * (1 - wy)
        + donor_f[y1c, x0c] * (1 - wx) * wy
        + donor_f[y1c, x1c] * wx * wy
    )
    valid = (src_x >= 0) & (src_x <= width - 1) & (src_y >= 0) & (src_y <= height - 1)
    mixed[~valid] = 0
    return mixed


def mix_faces(
    host: np.ndarray,
    donor: np.ndarray,
    host_eyes: tuple[np.ndarray, np.ndarray],
    donor_eyes: tuple[np.ndarray, np.ndarray],
) -> np.ndarray:
    aligned = align(donor, host_eyes, donor_eyes)
    alpha = host[:, :, 3]
    x0, _y0, x1, y1 = face_box(alpha)
    eye_y = float((host_eyes[0][1] + host_eyes[1][1]) / 2.0)
    rows = np.arange(host.shape[0])[:, None].astype(np.float32)
    cols = np.arange(host.shape[1])[None, :].astype(np.float32)
    fade_in = np.clip((rows - (eye_y - 28)) / 24.0, 0.0, 1.0)
    fade_out = np.clip(((y1 - 6) - rows) / 22.0, 0.0, 1.0)
    vertical = fade_in * fade_in * (3.0 - 2.0 * fade_in) * fade_out
    half = max(1.0, (x1 - x0) / 2.0)
    radial = np.abs(cols - ((x0 + x1) / 2.0)) / half
    side = np.clip((0.92 - radial) / 0.28, 0.0, 1.0)
    side = side * side * (3.0 - 2.0 * side)
    mask = vertical * side * (alpha > 40) * np.clip(aligned[:, :, 3] / 255.0, 0.0, 1.0)
    soft = (
        np.array(
            Image.fromarray(np.clip(mask * 255.0, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3))
        ).astype(np.float32)
        / 255.0
    )
    weight = soft[:, :, None] * 0.5
    mixed = host.astype(np.float32) * (1.0 - weight) + aligned * weight
    mixed[:, :, 3] = alpha
    return np.clip(mixed, 0, 255).astype(np.uint8)


def originals() -> dict[str, dict[str, list[Path]]]:
    grouped: dict[str, dict[str, list[Path]]] = {}
    for ethnicity_dir in sorted(path for path in BANK.iterdir() if path.is_dir()):
        grouped[ethnicity_dir.name] = {}
        for hair_dir in sorted(path for path in ethnicity_dir.iterdir() if path.is_dir()):
            files = sorted(path for path in hair_dir.glob("*.png") if not path.stem.endswith("_v2"))
            grouped[ethnicity_dir.name][hair_dir.name] = files
    return grouped


def partner_for(files: list[Path], index: int, pool: list[Path]) -> Path | None:
    if len(files) >= 2:
        other = files[(index + len(files) // 2) % len(files)]
        if other != files[index]:
            return other
    for candidate in pool:
        if candidate != files[index]:
            return candidate
    return None


def write_manifest(created: list[dict[str, object]]) -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = data["assets"]
    known = {item["local_path"] for item in assets}
    assets.extend(item for item in created if item["local_path"] not in known)
    counts: dict[str, int] = {}
    for item in assets:
        counts[item["ethnicity"]] = counts.get(item["ethnicity"], 0) + 1
    data["assets"] = assets
    data["asset_count"] = len(assets)
    data["ethnicity_counts"] = counts
    data["cloudinary_modified"] = False
    data["derived_face_count"] = sum(1 for item in assets if str(item["local_path"]).endswith("_v2.png"))
    data["usage"] = (
        "unique regen cutouts divided across ethnicities, with one derived face beside each cutout; "
        "Cloudinary was not modified"
    )
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    grouped = originals()
    created: list[dict[str, object]] = []
    eyes_cache: dict[Path, tuple[np.ndarray, np.ndarray]] = {}
    image_cache: dict[Path, np.ndarray] = {}
    written = 0
    skipped = 0
    for ethnicity, hairs in grouped.items():
        pool = [path for files in hairs.values() for path in files]
        for hair, files in hairs.items():
            for index, host_path in enumerate(files):
                destination = host_path.with_name(f"{host_path.stem}_v2.png")
                if destination.exists() and destination.stat().st_size > 0:
                    skipped += 1
                    continue
                donor_path = partner_for(files, index, pool)
                if donor_path is None:
                    continue
                host = image_cache.setdefault(host_path, load_rgba(host_path))
                donor = image_cache.setdefault(donor_path, load_rgba(donor_path))
                host_eyes = eyes_cache.setdefault(host_path, eye_pair(host))
                donor_eyes = eyes_cache.setdefault(donor_path, eye_pair(donor))
                mixed = mix_faces(host, donor, host_eyes, donor_eyes)
                Image.fromarray(mixed).save(destination)
                relative = destination.relative_to(ROOT).as_posix()
                created.append(
                    {
                        "collection": "script_skin_tone_hair_colour",
                        "source_pack": "Free to use Regen Faces - SCRIPT SKIN TONE + HAIR COLOUR",
                        "ethnicity": ethnicity,
                        "hair_colour": hair,
                        "storage_key": f"regen_newgen_faces/{relative}",
                        "source_url": "",
                        "local_path": relative,
                        "bytes": destination.stat().st_size,
                        "width": 250,
                        "height": 250,
                        "derived_from": host_path.relative_to(ROOT).as_posix(),
                        "derived_with": donor_path.relative_to(ROOT).as_posix(),
                    }
                )
                written += 1
                if written % 200 == 0:
                    print(f"wrote {written}", flush=True)
        image_cache.clear()
        eyes_cache.clear()
    write_manifest(created)
    print(f"wrote {written} skipped {skipped}")


if __name__ == "__main__":
    main()
