from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent.parent
BRANDING_DIR = ROOT / "assets" / "branding"
ICON_SOURCE = BRANDING_DIR / "gtex_icon.png"
LOGO_SOURCE = BRANDING_DIR / "gtex_logo.png"

WEB_DIR = ROOT / "web"
ANDROID_RES_DIR = ROOT / "android" / "app" / "src" / "main" / "res"
WINDOWS_ICON = ROOT / "windows" / "runner" / "resources" / "app_icon.ico"

BG = "#04070C"
SURFACE = "#0E1625"
TEXT = "#F5F8FC"
MUTED = "#AEB8C9"
ACCENT = "#9DFF68"
ACCENT_STRONG = "#35DFB2"
ACCENT_SKY = "#52A9FF"
ACCENT_WARM = "#FFC76B"
EDGE = "#20324C"

FONT_BOLD = [
    Path(r"C:\Windows\Fonts\bahnschrift.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
]
FONT_REGULAR = [
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate canonical GTEX branding assets and platform-specific icon outputs."
        )
    )
    parser.add_argument(
        "--bootstrap-sources",
        action="store_true",
        help=(
            "Create the canonical gtex_logo.png and gtex_icon.png sources if they "
            "are not present yet."
        ),
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_font(candidates: list[Path], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size=size)
    return ImageFont.load_default()


def lerp_color(start: str, end: str, t: float) -> tuple[int, int, int]:
    sr, sg, sb = ImageColor.getrgb(start)
    er, eg, eb = ImageColor.getrgb(end)
    return (
        int(sr + (er - sr) * t),
        int(sg + (eg - sg) * t),
        int(sb + (eb - sb) * t),
    )


def draw_diagonal_gradient(size: tuple[int, int], start: str, end: str) -> Image.Image:
    width, height = size
    gradient = Image.new("RGBA", size)
    pixels = gradient.load()
    denom = max(width + height - 2, 1)
    for y in range(height):
        for x in range(width):
            tone = (x + y) / denom
            r, g, b = lerp_color(start, end, tone)
            pixels[x, y] = (r, g, b, 255)
    return gradient


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def draw_bootstrap_icon(output: Path, size: int = 1024) -> None:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    card_size = int(size * 0.82)
    card_offset = (size - card_size) // 2
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_card = Image.new("RGBA", (card_size, card_size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow_card)
    shadow_draw.rounded_rectangle(
        (0, 0, card_size, card_size),
        radius=int(card_size * 0.24),
        fill=(0, 0, 0, 145),
    )
    shadow_card = shadow_card.filter(ImageFilter.GaussianBlur(size // 28))
    shadow.alpha_composite(shadow_card, (card_offset, card_offset + size // 34))
    canvas.alpha_composite(shadow)

    card = Image.new("RGBA", (card_size, card_size), (0, 0, 0, 0))
    gradient = draw_diagonal_gradient((card_size, card_size), "#1DD4B9", ACCENT_SKY)
    card_mask = rounded_mask((card_size, card_size), radius=int(card_size * 0.24))
    card.paste(gradient, (0, 0), card_mask)

    warm_band = Image.new("RGBA", (card_size, card_size), (0, 0, 0, 0))
    warm_draw = ImageDraw.Draw(warm_band)
    warm_draw.rounded_rectangle(
        (0, 0, card_size, int(card_size * 0.15)),
        radius=int(card_size * 0.2),
        fill=ImageColor.getrgb(ACCENT_WARM) + (235,),
    )
    warm_band = warm_band.filter(ImageFilter.GaussianBlur(card_size // 18))
    card.alpha_composite(warm_band)

    edge = Image.new("RGBA", (card_size, card_size), (0, 0, 0, 0))
    edge_draw = ImageDraw.Draw(edge)
    edge_draw.rounded_rectangle(
        (3, 3, card_size - 4, card_size - 4),
        radius=int(card_size * 0.24),
        outline=(255, 255, 255, 92),
        width=max(card_size // 80, 3),
    )
    card.alpha_composite(edge)

    inner_size = int(card_size * 0.66)
    inner_offset = (card_size - inner_size) // 2
    inner = Image.new("RGBA", (card_size, card_size), (0, 0, 0, 0))
    inner_draw = ImageDraw.Draw(inner)
    inner_draw.rounded_rectangle(
        (
            inner_offset,
            inner_offset,
            inner_offset + inner_size,
            inner_offset + inner_size,
        ),
        radius=int(inner_size * 0.22),
        fill=ImageColor.getrgb(SURFACE) + (242,),
    )
    inner_draw.rounded_rectangle(
        (
            inner_offset + 4,
            inner_offset + 4,
            inner_offset + inner_size - 5,
            inner_offset + inner_size - 5,
        ),
        radius=int(inner_size * 0.22),
        outline=(255, 255, 255, 30),
        width=max(inner_size // 90, 2),
    )
    inner = inner.rotate(-10, resample=Image.Resampling.BICUBIC)
    card.alpha_composite(inner)

    draw = ImageDraw.Draw(card)
    mono_font = load_font(FONT_BOLD, int(card_size * 0.235))
    label = "GT"
    bbox = draw.textbbox((0, 0), label, font=mono_font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (card_size - text_width) / 2
    text_y = (card_size - text_height) / 2 - card_size * 0.01
    draw.text(
        (text_x + card_size * 0.01, text_y + card_size * 0.02),
        label,
        font=mono_font,
        fill=(0, 0, 0, 110),
    )
    draw.text((text_x, text_y), label, font=mono_font, fill=TEXT)

    canvas.alpha_composite(card, (card_offset, card_offset))
    ensure_parent(output)
    canvas.save(output)


def draw_bootstrap_logo(output: Path, width: int = 2400, height: int = 840) -> None:
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    icon_size = int(height * 0.72)
    icon_path = output.parent / "_tmp_icon.png"
    draw_bootstrap_icon(icon_path, size=icon_size)
    icon = Image.open(icon_path).convert("RGBA")
    icon_y = (height - icon.height) // 2
    canvas.alpha_composite(icon, (0, icon_y))
    icon_path.unlink(missing_ok=True)

    draw = ImageDraw.Draw(canvas)
    title_font = load_font(FONT_BOLD, int(height * 0.31))
    subtitle_font = load_font(FONT_REGULAR, int(height * 0.115))

    text_x = int(icon_size + height * 0.12)
    title = "GTEX"
    subtitle = "GLOBAL TALENT EXCHANGE"
    title_box = draw.textbbox((0, 0), title, font=title_font)
    subtitle_box = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    total_height = (title_box[3] - title_box[1]) + (subtitle_box[3] - subtitle_box[1]) + int(height * 0.07)
    start_y = (height - total_height) // 2

    draw.text((text_x, start_y), title, font=title_font, fill=TEXT)
    rule_y = start_y + (title_box[3] - title_box[1]) + int(height * 0.03)
    draw.rounded_rectangle(
        (
            text_x,
            rule_y,
            text_x + int(width * 0.1),
            rule_y + int(height * 0.012),
        ),
        radius=int(height * 0.01),
        fill=ImageColor.getrgb(ACCENT_WARM) + (255,),
    )
    subtitle_y = rule_y + int(height * 0.05)
    draw.text((text_x, subtitle_y), subtitle, font=subtitle_font, fill=MUTED)

    ensure_parent(output)
    canvas.save(output)


def paste_centered(canvas: Image.Image, image: Image.Image, scale: float) -> Image.Image:
    icon_size = max(int(min(canvas.size) * scale), 1)
    fitted = image.copy()
    fitted.thumbnail((icon_size, icon_size), Image.Resampling.LANCZOS)
    x = (canvas.width - fitted.width) // 2
    y = (canvas.height - fitted.height) // 2
    canvas.alpha_composite(fitted, (x, y))
    return canvas


def save_resized_icon(source: Image.Image, output: Path, size: int, scale: float = 1.0) -> None:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    paste_centered(canvas, source, scale=scale)
    ensure_parent(output)
    canvas.save(output)


def create_sources_if_needed(force: bool = False) -> None:
    if force or not ICON_SOURCE.exists():
        draw_bootstrap_icon(ICON_SOURCE)
    if force or not LOGO_SOURCE.exists():
        draw_bootstrap_logo(LOGO_SOURCE)


def validate_sources() -> None:
    missing = [path for path in (ICON_SOURCE, LOGO_SOURCE) if not path.exists()]
    if missing:
        missing_text = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(
            f"Missing canonical brand source assets: {missing_text}. "
            "Run with --bootstrap-sources or add the approved files first."
        )


def generate_outputs() -> None:
    icon = Image.open(ICON_SOURCE).convert("RGBA")

    save_resized_icon(icon, WEB_DIR / "favicon.png", 32)
    save_resized_icon(icon, WEB_DIR / "icons" / "Icon-192.png", 192)
    save_resized_icon(icon, WEB_DIR / "icons" / "Icon-512.png", 512)

    maskable_192 = Image.new("RGBA", (192, 192), ImageColor.getrgb(BG) + (255,))
    paste_centered(maskable_192, icon, scale=0.8)
    ensure_parent(WEB_DIR / "icons" / "Icon-maskable-192.png")
    maskable_192.save(WEB_DIR / "icons" / "Icon-maskable-192.png")

    maskable_512 = Image.new("RGBA", (512, 512), ImageColor.getrgb(BG) + (255,))
    paste_centered(maskable_512, icon, scale=0.8)
    ensure_parent(WEB_DIR / "icons" / "Icon-maskable-512.png")
    maskable_512.save(WEB_DIR / "icons" / "Icon-maskable-512.png")

    launcher_sizes = {
        "mdpi": 48,
        "hdpi": 72,
        "xhdpi": 96,
        "xxhdpi": 144,
        "xxxhdpi": 192,
    }
    adaptive_sizes = {
        "mdpi": 108,
        "hdpi": 162,
        "xhdpi": 216,
        "xxhdpi": 324,
        "xxxhdpi": 432,
    }

    for density, size in launcher_sizes.items():
        save_resized_icon(
            icon,
            ANDROID_RES_DIR / f"mipmap-{density}" / "ic_launcher.png",
            size,
        )
        save_resized_icon(
            icon,
            ANDROID_RES_DIR / f"mipmap-{density}" / "ic_launcher_round.png",
            size,
        )

    for density, size in adaptive_sizes.items():
        save_resized_icon(
            icon,
            ANDROID_RES_DIR / f"mipmap-{density}" / "gtex_foreground.png",
            size,
            scale=0.78,
        )

    ensure_parent(WINDOWS_ICON)
    icon.save(
        WINDOWS_ICON,
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def main() -> None:
    args = parse_args()
    if args.bootstrap_sources:
        create_sources_if_needed(force=True)
    validate_sources()
    generate_outputs()


if __name__ == "__main__":
    main()
