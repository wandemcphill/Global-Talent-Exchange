"""Build a unique regen face bank guided by the Cloudinary cutout pack.

The original bank is 250x250 transparent PNG cutouts. Several ethnicity
folders in that pack are copies of another folder. This generator keeps
that frame, gives every ethnicity its own faces, and varies hairstyle
as well as hair colour.

Nothing is uploaded. Output lands in regen_facebank_v2/ at the repo root.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = ROOT / "regen_facebank_v2"
CANVAS = 250

SHARED_STYLES = (
    "Buzz",
    "Crop",
    "Fade",
    "Waves",
    "Fringe",
    "Side part",
    "Quiff",
    "Curls",
)
SIGNATURE_STYLES = {
    "African": ("Coils", "Twists"),
    "East asian": ("Straight", "Spiky"),
    "Hispanic": ("Textured", "Curtain"),
    "Indian": ("Swept", "Layered"),
    "Middle east": ("Tapered", "Curly top"),
    "Mixed": ("Locs", "Twists"),
    "North european": ("Messy", "Slick"),
    "South european": ("Curtain", "Slick"),
}

HAIR_RGB = {
    "Black": np.array([28, 22, 18], dtype=np.float32),
    "Dark Brown": np.array([62, 40, 28], dtype=np.float32),
    "Brown": np.array([108, 70, 42], dtype=np.float32),
    "Light Brown": np.array([154, 106, 64], dtype=np.float32),
    "Blonde": np.array([214, 178, 112], dtype=np.float32),
    "Red": np.array([164, 74, 46], dtype=np.float32),
}

SKIN = {
    "African": [(62, 38, 28), (84, 52, 36), (104, 66, 46), (126, 82, 56), (148, 98, 68), (50, 32, 24)],
    "East asian": [(236, 206, 180), (226, 190, 162), (214, 174, 146), (242, 216, 194), (204, 162, 134)],
    "Hispanic": [(198, 142, 102), (184, 126, 88), (168, 112, 76), (214, 160, 118), (152, 100, 68)],
    "Indian": [(170, 114, 76), (152, 98, 64), (188, 130, 88), (134, 86, 54), (114, 74, 48)],
    "Middle east": [(206, 160, 120), (188, 140, 100), (172, 124, 88), (218, 174, 134), (156, 112, 80)],
    "North european": [(244, 214, 196), (232, 198, 176), (248, 222, 206), (220, 180, 158), (236, 204, 184)],
    "South european": [(214, 164, 124), (196, 144, 104), (180, 128, 92), (224, 176, 136), (164, 114, 82)],
    "Mixed": [
        (98, 64, 46),
        (142, 98, 70),
        (176, 126, 92),
        (210, 166, 128),
        (228, 190, 160),
        (236, 206, 180),
        (122, 80, 56),
        (188, 136, 98),
    ],
}

HAIR_WEIGHTS = {
    "African": (("Black", 52), ("Dark Brown", 34), ("Brown", 9), ("Blonde", 3), ("Red", 2)),
    "East asian": (("Black", 72), ("Dark Brown", 20), ("Brown", 5), ("Blonde", 2), ("Red", 1)),
    "Hispanic": (("Dark Brown", 34), ("Black", 28), ("Brown", 18), ("Light Brown", 12), ("Blonde", 5), ("Red", 3)),
    "Indian": (("Black", 58), ("Dark Brown", 30), ("Brown", 9), ("Light Brown", 2), ("Red", 1)),
    "Middle east": (("Black", 42), ("Dark Brown", 36), ("Brown", 14), ("Light Brown", 6), ("Blonde", 1), ("Red", 1)),
    "North european": (
        ("Dark Brown", 24),
        ("Light Brown", 22),
        ("Blonde", 22),
        ("Brown", 14),
        ("Black", 12),
        ("Red", 6),
    ),
    "South european": (
        ("Dark Brown", 36),
        ("Black", 24),
        ("Brown", 20),
        ("Light Brown", 12),
        ("Blonde", 5),
        ("Red", 3),
    ),
    "Mixed": (("Black", 28), ("Dark Brown", 24), ("Brown", 16), ("Light Brown", 14), ("Blonde", 12), ("Red", 6)),
}

IRIS = {
    "African": ((58, 38, 26), (42, 30, 22), (74, 50, 32)),
    "East asian": ((64, 44, 30), (50, 36, 26), (88, 60, 38)),
    "Hispanic": ((74, 50, 32), (60, 42, 28), (98, 66, 38)),
    "Indian": ((64, 44, 30), (50, 34, 24), (86, 58, 36)),
    "Middle east": ((72, 50, 32), (56, 40, 28), (98, 70, 42), (72, 96, 64)),
    "North european": ((80, 120, 158), (90, 126, 96), (96, 68, 42), (66, 100, 80), (72, 52, 36)),
    "South european": ((80, 56, 36), (98, 70, 42), (74, 104, 76), (62, 44, 32)),
    "Mixed": ((52, 36, 26), (88, 60, 38), (80, 116, 152), (84, 114, 84), (98, 68, 44)),
}


def _styles_for(ethnicity: str) -> tuple[str, ...]:
    return SHARED_STYLES + SIGNATURE_STYLES[ethnicity]


def _seed(ethnicity: str, style: str, index: int) -> int:
    digest = hashlib.sha256(f"gtex-face-v2|{ethnicity}|{style}|{index}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _weighted(rng: random.Random, pairs: tuple[tuple[str, int], ...]) -> str:
    roll = rng.randrange(sum(weight for _, weight in pairs))
    for name, weight in pairs:
        roll -= weight
        if roll < 0:
            return name
    return pairs[-1][0]


def _tint(rgb: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(max(0, min(255, int(channel * factor))) for channel in rgb)


def _spec(ethnicity: str, style: str, index: int) -> dict[str, object]:
    rng = random.Random(_seed(ethnicity, style, index))
    skin = _tint(rng.choice(SKIN[ethnicity]), rng.uniform(0.95, 1.05))
    hair_name = _weighted(rng, HAIR_WEIGHTS[ethnicity])
    cheek = rng.randint(68, 80)
    top = rng.randint(52, 64)
    chin = rng.randint(228, 242)
    return {
        "ethnicity": ethnicity,
        "style": style,
        "index": index,
        "rng": rng,
        "skin": skin,
        "hair_name": hair_name,
        "hair": _tint(tuple(int(v) for v in HAIR_RGB[hair_name]), rng.uniform(0.92, 1.08)),
        "cx": 125 + rng.randint(-2, 2),
        "top": top,
        "chin": chin,
        "rx": cheek,
        "ry": int((chin - top) * rng.uniform(0.50, 0.56)),
        "part": rng.choice((-1, 1)),
        "eye_w": rng.randint(12, 15),
        "eye_h": rng.randint(6, 8),
        "iris": rng.choice(IRIS[ethnicity]),
        "mouth_w": rng.randint(14, 20),
        "nose_w": rng.randint(4, 7),
    }


def _head_box(spec: dict[str, object]) -> tuple[int, int, int, int]:
    cx = int(spec["cx"])
    top = int(spec["top"])
    chin = int(spec["chin"])
    ry = int(spec["ry"])
    cy = chin - ry
    rx = int(spec["rx"])
    # Keep the stored top as the forehead skin line. The ellipse top can sit higher.
    box_top = min(top, cy - ry)
    return cx, cy, rx, box_top


def _skin_layer(spec: dict[str, object]) -> Image.Image:
    cx, cy, rx, _box_top = _head_box(spec)
    chin = int(spec["chin"])
    skin = np.array(spec["skin"], dtype=np.float32)
    shadow = skin * 0.72
    highlight = np.minimum(skin * 1.18 + 8, 255)
    ys, xs = np.mgrid[0:CANVAS, 0:CANVAS]
    head = ((xs - cx) / rx) ** 2 + ((ys - cy) / max(1, int(spec["ry"]))) ** 2 <= 1.0
    neck_rx = int(rx * 0.58)
    neck = ((xs - cx) / neck_rx) ** 2 + ((ys - (chin + 8)) / 36) ** 2 <= 1.0
    neck &= ys > cy
    ear = np.zeros((CANVAS, CANVAS), dtype=bool)
    ear_y = cy + 4
    for side in (-1, 1):
        ex = cx + side * (rx - 2)
        ear |= ((xs - ex) / 13) ** 2 + ((ys - ear_y) / 18) ** 2 <= 1.0
    mask = head | neck | ear
    light = np.clip(1.05 - np.hypot(xs - (cx - rx * 0.28), ys - (cy - int(spec["ry"]) * 0.35)) / (rx * 2.5), 0.0, 1.0)
    color = shadow + (highlight - shadow) * light[..., None]
    blush = np.exp(-((np.abs(xs - cx) - rx * 0.42) ** 2) / 180 - ((ys - cy) ** 2) / 420)
    color = np.clip(color + np.array([18, 6, 4], dtype=np.float32) * blush[..., None], 0, 255)
    # Soft shade under the cheek bones.
    under = np.clip((ys - (cy + 8)) / 70, 0, 1) * 0.16
    color *= 1 - under[..., None]
    rgba = np.zeros((CANVAS, CANVAS, 4), dtype=np.uint8)
    rgba[..., :3] = color.astype(np.uint8)
    alpha = Image.fromarray((mask.astype(np.uint8) * 255), mode="L").filter(ImageFilter.GaussianBlur(radius=0.8))
    rgba[..., 3] = np.array(alpha)
    return Image.fromarray(rgba, mode="RGBA")


def _features(spec: dict[str, object], image: Image.Image) -> None:
    draw = ImageDraw.Draw(image)
    cx, cy, rx, _box_top = _head_box(spec)
    skin = spec["skin"]
    assert isinstance(skin, tuple)
    iris = spec["iris"]
    assert isinstance(iris, tuple)
    eye_y = cy - int(int(spec["ry"]) * 0.12)
    eye_dx = int(rx * 0.38)
    eye_w = int(spec["eye_w"])
    eye_h = int(spec["eye_h"])
    for side in (-1, 1):
        x = cx + side * eye_dx
        _eye(draw, x, eye_y, eye_w, eye_h, iris, skin)
        draw.arc(
            [x - eye_w - 1, eye_y - eye_h - 8, x + eye_w + 1, eye_y - 1],
            200,
            345,
            fill=(*_tint(spec["hair"], 0.8), 255),  # type: ignore[arg-type]
            width=2,
        )
    nose_y = cy + int(int(spec["ry"]) * 0.22)
    nose_w = int(spec["nose_w"])
    draw.ellipse([cx - 2, nose_y - 16, cx + 3, nose_y + 2], fill=(*_tint(skin, 0.9), 90))
    draw.ellipse([cx - nose_w, nose_y - 2, cx + nose_w, nose_y + 5], fill=(*_tint(skin, 0.86), 255))
    nostril = (*_tint(skin, 0.62), 220)
    draw.ellipse([cx - nose_w - 2, nose_y + 1, cx - 1, nose_y + 5], fill=nostril)
    draw.ellipse([cx + 1, nose_y + 1, cx + nose_w + 2, nose_y + 5], fill=nostril)
    mouth_y = cy + int(int(spec["ry"]) * 0.48)
    mouth_w = int(spec["mouth_w"])
    lip = (
        min(255, int(skin[0] * 0.75 + 48)),
        int(skin[1] * 0.48),
        int(skin[2] * 0.46),
        255,
    )
    draw.ellipse([cx - mouth_w, mouth_y - 3, cx + mouth_w, mouth_y + 7], fill=lip)
    draw.arc(
        [cx - mouth_w, mouth_y - 6, cx + mouth_w, mouth_y + 4],
        200,
        340,
        fill=(*_tint(skin, 0.5), 255),
        width=2,
    )


def _eye(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    iris: tuple[int, int, int],
    skin: tuple[int, int, int],
) -> None:
    draw.ellipse([x - w, y - h, x + w, y + h], fill=(246, 242, 236, 255))
    draw.chord([x - w, y - h, x + w, y + h], 200, 340, fill=(*_tint(skin, 0.78), 170))
    iw, ih = max(3, int(w * 0.46)), max(3, int(h * 0.78))
    draw.ellipse([x - iw, y - ih + 1, x + iw, y + ih], fill=(*iris, 255))
    draw.ellipse([x - iw // 2, y - 1, x + iw // 2, y + ih], fill=(24, 18, 16, 255))
    draw.ellipse([x - 2, y - ih // 2, x + 1, y - 1], fill=(255, 255, 255, 230))
    draw.arc([x - w, y - h, x + w, y + h], 200, 350, fill=(36, 28, 24, 255), width=2)


def _hair_mask(spec: dict[str, object]) -> Image.Image:
    cx, cy, rx, _box_top = _head_box(spec)
    ry = int(spec["ry"])
    style = str(spec["style"])
    part = int(spec["part"])
    rng = spec["rng"]
    assert isinstance(rng, random.Random)
    mask = Image.new("L", (CANVAS, CANVAS), 0)
    draw = ImageDraw.Draw(mask)
    hairline = cy - int(ry * 0.55)
    cap_top = cy - ry - 16
    if style == "Buzz":
        cap_top = cy - ry - 4
        hairline = cy - int(ry * 0.62)
    elif style in {"Fade", "Tapered", "Slick"}:
        cap_top = cy - ry - 6
        hairline = cy - int(ry * 0.42)
        rx = int(rx * 0.82)
    elif style in {"Fringe", "Straight"}:
        hairline = cy - int(ry * 0.18)
    elif style == "Quiff":
        cap_top = cy - ry - 28
        hairline = cy - int(ry * 0.34)
    elif style in {"Curls", "Coils", "Curly top", "Twists", "Locs"}:
        cap_top = cy - ry - 18
        hairline = cy - int(ry * 0.4)
    draw.ellipse([cx - rx - 8, cap_top, cx + rx + 8, hairline + 28], fill=255)
    if style == "Side part":
        draw.ellipse([cx + part * 6 - rx, cap_top - 4, cx + part * 18 + rx, hairline + 20], fill=255)
    if style == "Quiff":
        draw.polygon(
            [(cx - 16, hairline), (cx + 24, cap_top - 8), (cx + 36, hairline + 6)],
            fill=255,
        )
    if style == "Spiky":
        for index in range(-3, 4):
            x = cx + index * 16
            draw.polygon([(x - 7, hairline), (x, cap_top - 8), (x + 7, hairline)], fill=255)
    if style in {"Curls", "Coils", "Curly top"}:
        radius = 7 if style == "Coils" else 10
        count = 16 if style == "Coils" else 11
        for index in range(count):
            x = cx - rx + int((2 * rx) * index / (count - 1))
            y = cap_top + 16 + abs(index - count // 2)
            if style == "Curly top" and abs(x - cx) > rx * 0.65:
                continue
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill=255)
    if style in {"Twists", "Locs"}:
        length = 26 if style == "Twists" else 40
        for index in range(-4, 5):
            x = cx + index * 13
            y0 = cap_top + 10 + abs(index) * 2
            draw.rounded_rectangle([x - 4, y0, x + 4, y0 + length], radius=4, fill=255)
    if style in {"Messy", "Textured"}:
        for _ in range(6):
            x = cx + rng.randint(-rx, rx)
            draw.polygon([(x - 8, hairline), (x, cap_top + rng.randint(0, 12)), (x + 8, hairline + 4)], fill=255)
    if style == "Swept":
        draw.ellipse([cx + part * 8, cap_top, cx + part * (rx + 18), hairline + 16], fill=255)
    if style == "Curtain":
        draw.rectangle([cx - 5, cap_top, cx + 5, hairline + 8], fill=0)
    # Open the face below the hairline so eyes stay clear.
    cut = Image.new("L", (CANVAS, CANVAS), 0)
    ImageDraw.Draw(cut).ellipse([cx - rx + 6, hairline, cx + rx - 6, chin_bottom(spec)], fill=255)
    hair = np.array(mask)
    opening = np.array(cut)
    kept = hair.astype(np.int16) - opening.astype(np.int16)
    kept = np.clip(kept, 0, 255).astype(np.uint8)
    return Image.fromarray(kept, mode="L").filter(ImageFilter.GaussianBlur(radius=0.6))


def chin_bottom(spec: dict[str, object]) -> int:
    return int(spec["chin"]) + 8


def _paint_hair(spec: dict[str, object], image: Image.Image) -> None:
    mask = _hair_mask(spec)
    hair = np.array(spec["hair"], dtype=np.float32)
    ys, xs = np.mgrid[0:CANVAS, 0:CANVAS]
    cx = int(spec["cx"])
    streak = 0.82 + 0.18 * ((np.sin((xs - cx) * 0.45) + 1) / 2)
    if str(spec["style"]) in {"Crop", "Waves", "Textured", "Layered"}:
        streak *= 0.9 + 0.1 * ((np.sin(ys * 0.8) + 1) / 2)
    color = np.clip(hair * streak[..., None], 0, 255).astype(np.uint8)
    rgba = np.zeros((CANVAS, CANVAS, 4), dtype=np.uint8)
    rgba[..., :3] = color
    rgba[..., 3] = np.array(mask)
    layer = Image.fromarray(rgba, mode="RGBA")
    image.alpha_composite(layer)


def render(spec: dict[str, object]) -> Image.Image:
    image = _skin_layer(spec)
    _features(spec, image)
    _paint_hair(spec, image)
    # Eyes are painted before hair. Repaint them so every style keeps a visible face.
    _features(spec, image)
    return image


def _asset_record(path: Path, spec: dict[str, object], digest: str) -> dict[str, object]:
    ethnicity = str(spec["ethnicity"])
    style = str(spec["style"])
    relative = Path("script_skin_hair") / ethnicity / style / path.name
    return {
        "collection": "script_skin_tone_hair_colour",
        "source_pack": "GTEX regen facebank v2",
        "ethnicity": ethnicity,
        "hair_colour": f"{style} / {spec['hair_name']}",
        "hairstyle": style,
        "hair_color": spec["hair_name"],
        "source_path": relative.as_posix(),
        "storage_key": f"regen_newgen_faces/{relative.as_posix()}",
        "bytes": path.stat().st_size,
        "width": CANVAS,
        "height": CANVAS,
        "sha256": digest,
    }


def _preview_jobs() -> list[tuple[str, str, int]]:
    jobs: list[tuple[str, str, int]] = []
    for style in _styles_for("African"):
        jobs.append(("African", style, 1))
    for style in _styles_for("North european"):
        jobs.append(("North european", style, 1))
    for ethnicity in SIGNATURE_STYLES:
        if ethnicity not in {"African", "North european"}:
            jobs.append((ethnicity, "Fringe", 1))
            jobs.append((ethnicity, SIGNATURE_STYLES[ethnicity][0], 1))
    return jobs


def _write_sheet(out: Path) -> None:
    files = sorted((out / "script_skin_hair").rglob("*.png"))
    if not files:
        return
    columns = 8
    thumb = 125
    rows = (len(files) + columns - 1) // columns
    sheet = Image.new("RGBA", (columns * thumb, rows * thumb), (4, 18, 14, 255))
    for index, path in enumerate(files):
        face = Image.open(path).convert("RGBA").resize((thumb, thumb), Image.Resampling.LANCZOS)
        sheet.alpha_composite(face, ((index % columns) * thumb, (index // columns) * thumb))
    sheet.convert("RGB").save(out / "preview_sheet.jpg", quality=90)


def generate(*, out: Path, per_style: int, preview: bool) -> None:
    if not preview:
        raise SystemExit(
            "Full procedural output is disabled. The drawn faces do not match "
            "the painted Cloudinary cutouts. Generate from the real bank style "
            "instead of running this renderer across 5,000 files."
        )
    out.mkdir(parents=True, exist_ok=True)
    if preview:
        jobs = _preview_jobs()
    else:
        jobs = [
            (ethnicity, style, index)
            for ethnicity in SIGNATURE_STYLES
            for style in _styles_for(ethnicity)
            for index in range(1, per_style + 1)
        ]
    seen: set[str] = set()
    records: list[dict[str, object]] = []
    for number, (ethnicity, style, index) in enumerate(jobs, start=1):
        spec = _spec(ethnicity, style, index)
        image = render(spec)
        destination = out / "script_skin_hair" / ethnicity / style / f"{index:04d}.png"
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, format="PNG", optimize=True)
        digest = hashlib.sha256(destination.read_bytes()).hexdigest()
        if digest in seen:
            raise SystemExit(f"Duplicate render: {destination}")
        seen.add(digest)
        records.append(_asset_record(destination, spec, digest))
        if number % 250 == 0 or number == len(jobs):
            print(f"{number}/{len(jobs)}", flush=True)
    if preview:
        _write_sheet(out)
        print(f"Preview wrote {len(records)} faces to {out}")
        return
    manifest = {
        "provider": "gtex_regen_newgen_face_bank",
        "collections": ["script_skin_tone_hair_colour"],
        "generated_from": "gtex_facebank_v2",
        "usage": "regen_newgen_only",
        "frame": {"width": CANVAS, "height": CANVAS, "background": "transparent"},
        "asset_count": len(records),
        "unique_sha256": len(seen),
        "note": "Unique faces per ethnicity. Hairstyles are shared. Folders are not copies of each other.",
        "assets": records,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    print(f"Wrote {len(records)} unique faces")
    print(manifest_path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--per-style", type=int, default=65)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    destination = ROOT / "tmp" / "facebank_v2_preview" if args.preview and args.out == DEFAULT_OUT else args.out
    generate(out=destination, per_style=args.per_style, preview=args.preview)


if __name__ == "__main__":
    main()
